from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import logging
import subprocess
import tempfile
import json
import resource
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from models import User, Project, Document, Exercise, ExerciseProgress, CompilationHistory, ChatMessage, db, app
from exercise_manager import create_sample_exercises
from admin import admin_bp

load_dotenv()

logging.basicConfig(level=logging.INFO)

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "INSECURE_DEFAULT_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.register_blueprint(admin_bp)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")

bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins=allowed_origins)

# Track connected users by session ID
connected_users = {}
active_projects = {}  # Project ID -> Document Content

# Set resource limits for child processes
def set_resource_limits():
    """Set resource limits for child processes"""
    # Limit memory usage (32MB)
    resource.setrlimit(resource.RLIMIT_AS, (32 * 1024 * 1024, 32 * 1024 * 1024))
    # Limit CPU time (2 seconds)
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    # Limit file size creation (1MB)
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))

# Add this function to detect potentially dangerous code
def check_for_dangerous_code(code):
    """
    Check for potentially dangerous code patterns that could be used maliciously.
    Returns True if dangerous patterns are detected, False otherwise.
    """
    dangerous_patterns = [
        r'system\s*\(',       # system() calls to execute shell commands
        r'popen\s*\(',        # popen() calls for creating processes
        r'fopen\s*\(',        # File operations that could write to the filesystem
        r'fwrite\s*\(',       # File write operations
        r'fprintf\s*\(',      # File write operations
        r'exec[lv][pe]\s*\(', # exec family of functions
        r'fork\s*\(',         # Process creation
        r'unlink\s*\(',       # File deletion
        r'remove\s*\(',       # File deletion
        r'rename\s*\(',       # File renaming
        r'mkdir\s*\(',        # Directory creation
        r'rmdir\s*\('         # Directory removal
    ]
    
    import re
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            return True
    return False

# The implementation function for executing code
def execute_code_impl(code, project_id=None, document_id=None, exercise_id=None, user_input="", compile_only=False):
    """
    Execute C code with enhanced support for standard includes and memory safety.
    
    Args:
        code (str): The C code to compile and execute
        project_id (int, optional): Project ID if code is from a project
        document_id (int, optional): Document ID if code is from a document
        exercise_id (int, optional): Exercise ID if code is from an exercise
        user_input (str, optional): Input to provide to the program
        compile_only (bool, optional): Whether to only compile the code
        
    Returns:
        dict: Result of compilation and/or execution
    """
    # Create temporary directory and files
    temp_dir = tempfile.mkdtemp()
    source_path = os.path.join(temp_dir, "source.c")
    exec_path = os.path.join(temp_dir, "executable")
    
    try:
        # Write code to file
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Check for potentially dangerous code
        if check_for_dangerous_code(code):
            return {
                "success": False,
                "stage": "security_check",
                "output": "Your code contains potentially dangerous system or file operations that are not allowed for security reasons. Please avoid using system(), popen(), file I/O operations, and other similar functions."
            }
        
        # Compile the code with standard library paths
        compile_command = [
            "gcc", 
            source_path, 
            "-o", exec_path,
            "-std=c11",      # Use C11 standard for modern features
            "-Wall",         # Enable all warnings
            "-I/usr/include",  # Standard include directory
            "-I/usr/local/include",  # Local include directory
            "-lm"            # Link with the math library
        ]
        
        compile_result = subprocess.run(
            compile_command,
            capture_output=True,
            text=True,
            timeout=5
        )

        if compile_result.returncode != 0:
            # Compilation failed
            if 'user_id' in session:
                compilation_history = CompilationHistory(
                    user_id=session['user_id'],
                    project_id=project_id,
                    document_id=document_id,
                    exercise_id=exercise_id,
                    code=code,
                    compilation_output=compile_result.stderr,
                    status='compilation_error'
                )
                db.session.add(compilation_history)
                db.session.commit()
            
            return {
                "success": False,
                "stage": "compilation",
                "output": compile_result.stderr
            }
            
        # If compile_only is True, return success without executing
        if compile_only:
            return {
                "success": True,
                "stage": "compilation",
                "output": "Compilation successful"
            }

        # Check if the program expects input
        input_functions = ["scanf", "gets", "fgets", "getchar", "getc", "read", "fscanf"]
        needs_input = any(func in code for func in input_functions)
        
        # If program needs input but no input is provided
        if needs_input and not user_input:
            return {
                "success": True,
                "stage": "needs_input",
                "stdout": "This program requires input. Please provide input below.",
                "needs_input": True
            }

        # Execute the program with the provided input
        try:
            process = subprocess.Popen(
                [exec_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=set_resource_limits  # Apply resource limits
            )
            
            # Ensure input ends with a newline
            if user_input and not user_input.endswith('\n'):
                user_input += '\n'
                
            # Use communicate with a timeout to prevent deadlocks
            stdout, stderr = process.communicate(input=user_input, timeout=5)
            returncode = process.returncode
            
            # Save compilation history
            if 'user_id' in session:
                status = 'success' if returncode == 0 else 'runtime_error'
                compilation_history = CompilationHistory(
                    user_id=session['user_id'],
                    project_id=project_id,
                    document_id=document_id,
                    exercise_id=exercise_id,
                    code=code,
                    compilation_output="Compilation successful",
                    execution_output=stdout + stderr,
                    status=status
                )
                db.session.add(compilation_history)
                db.session.commit()

            return {
                "success": True,
                "stage": "execution",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode,
                "needs_input": needs_input
            }

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return {
                "success": False,
                "stage": "execution",
                "output": "Execution timed out after 5 seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "stage": "execution",
                "output": f"Error during execution: {str(e)}"
            }
    except Exception as e:
        return {
            "success": False,
            "stage": "error",
            "output": f"Error: {str(e)}"
        }
    finally:
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

# User Authentication Routes
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error="Username already exists")
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return render_template('register.html', error="Email already in use")

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')


@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out!', 'info')
    return redirect(url_for('login'))


# Main application routes
@app.route("/")
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get user's projects
    owned_projects = Project.query.filter_by(owner_id=user_id).all()
    collaborated_projects = user.collaborated_projects
    
    # Get exercise progress
    in_progress_exercises = ExerciseProgress.query.filter_by(
        user_id=user_id, 
        status='in_progress'
    ).join(Exercise).all()
    
    # Get owner usernames for all projects
    project_owners = {}
    for project in owned_projects + collaborated_projects:
        if project.owner_id not in project_owners:
            owner = User.query.get(project.owner_id)
            project_owners[project.owner_id] = owner.username if owner else "Unknown"
    
    return render_template(
        'dashboard.html',
        username=user.username,
        owned_projects=owned_projects,
        collaborated_projects=collaborated_projects,
        in_progress_exercises=in_progress_exercises,
        project_owners=project_owners  # Pass owner usernames
    )

@app.route("/project/new", methods=['GET', 'POST'])
def new_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Project name is required!', 'error')
            return redirect(url_for('new_project'))
        
        user_id = session['user_id']
        project = Project(name=name, owner_id=user_id)
        db.session.add(project)
        db.session.commit()
        
        flash(f'Project "{name}" created successfully!', 'success')
        return redirect(url_for('project', project_id=project.id))
    
    return render_template('new_project.html')


@app.route("/project/<int:project_id>")
def project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    project = Project.query.get_or_404(project_id)
    
    # Get the owner's username directly
    owner = User.query.get(project.owner_id)
    
    # Check if user has access to this project
    if project.owner_id != user_id and user_id not in [u.id for u in project.collaborators]:
        flash('You do not have access to this project!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template(
        'editor.html',
        username=session.get('username'),
        project=project,
        owner_username=owner.username  # Pass the owner's username directly
    )


@app.route("/project/<int:project_id>/invite", methods=['POST'])
def invite_collaborator(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    project = Project.query.get_or_404(project_id)
    
    # Check if user is the owner
    if project.owner_id != user_id:
        flash('Only the project owner can invite collaborators!', 'error')
        return redirect(url_for('project', project_id=project_id))
    
    collaborator_username = request.form.get('username')
    permission = request.form.get('permission', 'read-write')
    
    if not collaborator_username:
        flash('Username is required!', 'error')
        return redirect(url_for('project', project_id=project_id))
    
    collaborator = User.query.filter_by(username=collaborator_username).first()
    if not collaborator:
        flash(f'User "{collaborator_username}" not found!', 'error')
        return redirect(url_for('project', project_id=project_id))
    
    # Check if already a collaborator
    if collaborator in project.collaborators:
        flash(f'User "{collaborator_username}" is already a collaborator!', 'info')
        return redirect(url_for('project', project_id=project_id))
    
    # Add collaborator
    project.collaborators.append(collaborator)
    db.session.commit()
    
    flash(f'User "{collaborator_username}" added as a collaborator!', 'success')
    return redirect(url_for('project', project_id=project_id))


@app.route("/execute_code", methods=["POST"])
def execute_code():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    code = request.json.get("code", "")
    project_id = request.json.get("project_id")
    document_id = request.json.get("document_id")
    exercise_id = request.json.get("exercise_id")
    user_input = request.json.get("input", "")
    compile_only = request.json.get("compile_only", False)
    
    if not code:
        return jsonify({"error": "No code provided"}), 400

    # Call implementation function
    result = execute_code_impl(
        code=code,
        project_id=project_id,
        document_id=document_id,
        exercise_id=exercise_id,
        user_input=user_input,
        compile_only=compile_only
    )
    
    return jsonify(result)


@app.route("/analyze_memory", methods=["POST"])
def analyze_memory():
    """Analyze memory usage and leaks in C code using Valgrind"""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    code = request.json.get("code", "")
    project_id = request.json.get("project_id")
    
    if not code:
        return jsonify({"error": "No code provided"}), 400

    # Create temporary directory and files
    temp_dir = tempfile.mkdtemp()
    source_path = os.path.join(temp_dir, "source.c")
    exec_path = os.path.join(temp_dir, "executable")
    
    try:
        # Write code to file
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Check for potentially dangerous code
        if check_for_dangerous_code(code):
            return jsonify({
                "success": False,
                "stage": "security_check",
                "output": "Your code contains potentially dangerous system or file operations that are not allowed for security reasons. Please avoid using system(), popen(), file I/O operations, and other similar functions."
            })
        
        # Compile the code with debug info
        compile_result = subprocess.run(
            ["gcc", source_path, "-o", exec_path, "-g", "-std=c11", "-I/usr/include", "-I/usr/local/include", "-lm"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if compile_result.returncode != 0:
            return jsonify({
                "success": False,
                "stage": "compilation",
                "output": compile_result.stderr
            })
        
        # Run with Valgrind for memory analysis
        try:
            valgrind_result = subprocess.run(
                ["valgrind", "--leak-check=full", "--show-leak-kinds=all", 
                 "--track-origins=yes", "--log-file=valgrind.log", exec_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_dir
            )
            
            # Parse Valgrind output
            valgrind_log = os.path.join(temp_dir, "valgrind.log")
            memory_issues = []
            
            if os.path.exists(valgrind_log):
                with open(valgrind_log, 'r') as f:
                    log_content = f.read()
                
                # Simple parsing for memory leak summary
                leaks = {
                    "definitely_lost": 0,
                    "indirectly_lost": 0,
                    "possibly_lost": 0,
                    "still_reachable": 0
                }
                
                import re
                # Extract "definitely lost" bytes
                definitely_match = re.search(r'definitely lost: ([0-9,]+) bytes', log_content)
                if definitely_match:
                    leaks["definitely_lost"] = int(definitely_match.group(1).replace(',', ''))
                
                # Extract "indirectly lost" bytes
                indirectly_match = re.search(r'indirectly lost: ([0-9,]+) bytes', log_content)
                if indirectly_match:
                    leaks["indirectly_lost"] = int(indirectly_match.group(1).replace(',', ''))
                
                # Extract "possibly lost" bytes
                possibly_match = re.search(r'possibly lost: ([0-9,]+) bytes', log_content)
                if possibly_match:
                    leaks["possibly_lost"] = int(possibly_match.group(1).replace(',', ''))
                
                # Extract "still reachable" bytes
                reachable_match = re.search(r'still reachable: ([0-9,]+) bytes', log_content)
                if reachable_match:
                    leaks["still_reachable"] = int(reachable_match.group(1).replace(',', ''))
                
                # Extract detailed leak reports
                leak_details = re.findall(r'(==\d+== [0-9,]+ bytes in \d+ blocks are (?:definitely|indirectly|possibly) lost.*?(?:==\d+==\s+){1,3}.*?(?:malloc|calloc|realloc).*?)(?===\d+==)', log_content, re.DOTALL)
                for detail in leak_details:
                    lines = detail.strip().split('\n')
                    memory_issues.append(lines[0].replace('==', '').split('==')[0].strip())
            
            return jsonify({
                "success": True,
                "memory_analysis": {
                    "leaks": leaks,
                    "issues": memory_issues,
                    "stdout": valgrind_result.stdout,
                    "stderr": valgrind_result.stderr
                }
            })
                
        except subprocess.TimeoutExpired:
            return jsonify({
                "success": False,
                "stage": "memory_analysis",
                "output": "Memory analysis timed out after 10 seconds"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "stage": "error",
            "output": f"Error during memory analysis: {str(e)}"
        })
    finally:
        # Clean up
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

# Updated execute_test_cases to use our implementation
def execute_test_cases(code, test_cases_json):
    test_cases = json.loads(test_cases_json)
    results = []
    
    # Check for potentially dangerous code first
    if check_for_dangerous_code(code):
        return {
            "success": False,
            "stage": "security_check",
            "output": "Your code contains potentially dangerous system or file operations that are not allowed for security reasons. Please avoid using system(), popen(), file I/O operations, and other similar functions.",
            "results": []
        }
    
    # Compile the code using our implementation function
    compile_result = execute_code_impl(code, compile_only=True)
    
    if not compile_result.get("success", False):
        return {
            "success": False,
            "stage": "compilation",
            "output": compile_result.get("output", "Compilation failed"),
            "results": []
        }
    
    # Execute test cases
    all_passed = True
    
    # Create a temporary directory for the executable
    temp_dir = tempfile.mkdtemp()
    source_path = os.path.join(temp_dir, "source.c")
    exec_path = os.path.join(temp_dir, "executable")
    
    try:
        # Write code to file
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Compile with the same options
        compile_command = [
            "gcc", 
            source_path, 
            "-o", exec_path,
            "-std=c11",
            "-Wall",
            "-I/usr/include",
            "-I/usr/local/include",
            "-lm"            # Link with the math library
        ]
        
        subprocess.run(compile_command, check=True, capture_output=True)
        
        # Execute test cases
        for i, test_case in enumerate(test_cases):
            input_data = test_case.get("input", "")
            expected_output = test_case.get("expected_output", "").strip()
            
            try:
                execution_result = subprocess.run(
                    [exec_path],
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    preexec_fn=set_resource_limits
                )
                
                actual_output = execution_result.stdout.strip()
                
                if actual_output == expected_output:
                    results.append({
                        "test_case": i + 1,
                        "status": "passed",
                        "input": input_data,
                        "expected": expected_output,
                        "actual": actual_output
                    })
                else:
                    all_passed = False
                    results.append({
                        "test_case": i + 1,
                        "status": "failed",
                        "input": input_data,
                        "expected": expected_output,
                        "actual": actual_output
                    })
            except subprocess.TimeoutExpired:
                all_passed = False
                results.append({
                    "test_case": i + 1,
                    "status": "timeout",
                    "input": input_data,
                    "expected": expected_output,
                    "actual": "Execution timed out after 5 seconds"
                })
    except Exception as e:
        return {
            "success": False,
            "stage": "error",
            "output": f"Error: {str(e)}",
            "results": []
        }
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
    
    return {
        "success": all_passed,
        "stage": "execution",
        "results": results
    }

# Exercise routes
@app.route("/exercises")
def exercises():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    exercises = Exercise.query.all()
    
    # Get user's progress for each exercise
    progress_dict = {}
    for progress in ExerciseProgress.query.filter_by(user_id=user_id).all():
        progress_dict[progress.exercise_id] = progress
    
    return render_template(
        'exercises.html',
        exercises=exercises,
        progress_dict=progress_dict
    )


@app.route("/exercise/<int:exercise_id>")
def exercise(exercise_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    exercise = Exercise.query.get_or_404(exercise_id)
    
    # Get or create user progress
    progress = ExerciseProgress.query.filter_by(
        user_id=user_id, 
        exercise_id=exercise_id
    ).first()
    
    if not progress:
        progress = ExerciseProgress(
            user_id=user_id,
            exercise_id=exercise_id,
            status='not_started',
            user_code=exercise.initial_code
        )
        db.session.add(progress)
        db.session.commit()
    
    return render_template(
        'exercise.html',
        exercise=exercise,
        progress=progress
    )


@app.route("/exercise/<int:exercise_id>/submit", methods=["POST"])
def submit_exercise(exercise_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    code = request.json.get("code", "")
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    exercise = Exercise.query.get_or_404(exercise_id)
    progress = ExerciseProgress.query.filter_by(
        user_id=user_id, 
        exercise_id=exercise_id
    ).first()
    
    if not progress:
        return jsonify({"error": "Exercise progress not found"}), 404
    
    # Update progress
    progress.user_code = code
    progress.attempts += 1
    progress.last_attempt = datetime.utcnow()
    progress.status = 'in_progress'
    
    # Compile and execute the code with test cases
    result = execute_test_cases(code, exercise.test_cases)
    
    if result["success"]:
        progress.status = 'completed'
        progress.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify(result)

# Socket.IO event handlers
@socketio.on("connect")
def handle_connect():
    """Sends the initial document state to the new user and all connected users info."""
    if 'user_id' not in session:
        return False
    
    user_id = session['user_id']
    username = session.get('username', 'Anonymous')
    
    # Add user to connected users
    connected_users[request.sid] = {
        'user_id': user_id,
        'username': username
    }
    
    logging.info(f"User connected: {username} ({request.sid})")
    
    # Check if there's a project_id in the query string
    project_id = request.args.get('project_id')
    if project_id:
        join_room(f"project_{project_id}")
        
        # Send current document state if available
        if project_id in active_projects:
            emit("document", {"text": active_projects[project_id]})
        else:
            # Load from database if not in memory
            project = Project.query.get(project_id)
            if project:
                active_projects[project_id] = project.content or ""
                emit("document", {"text": active_projects[project_id]})
        
        # Notify everyone in the room about the new user
        emit("user_connected", {
            "username": username,
            "user_id": user_id,
            "sid": request.sid
        }, to=f"project_{project_id}")
        
        # Send list of all users in the room to the new user
        room_users = [
            {
                'username': connected_users[sid]['username'],
                'user_id': connected_users[sid]['user_id'],
                'sid': sid
            }
            for sid in connected_users
            if sid in socketio.server.manager.rooms.get(f"project_{project_id}", set())
        ]
        emit("all_users", {"users": room_users})


@socketio.on("disconnect")
def handle_disconnect():
    if request.sid in connected_users:
        username = connected_users[request.sid]['username']
        logging.info(f"User disconnected: {request.sid} ({username})")
        
        # Add the namespace parameter '/' here too
        for room in socketio.server.manager.get_rooms(request.sid, '/'):
            if room.startswith("project_"):
                project_id = room[8:]  # Remove "project_" prefix
                
                # Notify others in the room
                emit("user_disconnected", {
                    "sid": request.sid,
                    "username": username
                }, to=room)
        
        # Remove user from connected users
        del connected_users[request.sid]


@socketio.on("join_project")
def handle_join_project(data):
    if 'user_id' not in session:
        return
    
    project_id = data.get('project_id')
    if not project_id:
        return
    
    # Leave current rooms (if any)
    # Add the namespace parameter '/' here
    for room in socketio.server.manager.get_rooms(request.sid, '/'):
        if room.startswith("project_"):
            leave_room(room)
    
    # Join new project room
    join_room(f"project_{project_id}")
    
    # Load project from database if not already in memory
    if project_id not in active_projects:
        project = Project.query.get(project_id)
        if project:
            active_projects[project_id] = project.content or ""
    
    # Send current document state
    emit("document", {"text": active_projects.get(project_id, "")})
    
    # Notify others in the room
    emit("user_joined", {
        "username": connected_users[request.sid]['username'],
        "user_id": connected_users[request.sid]['user_id'],
        "sid": request.sid
    }, to=f"project_{project_id}", include_self=False)
    
    # Send list of all users in the room
    room_users = [
        {
            'username': connected_users[sid]['username'],
            'user_id': connected_users[sid]['user_id'],
            'sid': sid
        }
        for sid in connected_users
        if sid in socketio.server.manager.rooms.get(f"project_{project_id}", set())
    ]
    emit("all_users", {"users": room_users})


@socketio.on("edit")
def handle_edit(operation):
    """Handles edit operations and syncs them with all clients."""
    if 'user_id' not in session:
        return
    
    project_id = operation.get('project_id')
    if not project_id:
        return
    
    try:
        # Load project content if not in memory
        if project_id not in active_projects:
            project = Project.query.get(project_id)
            if project:
                active_projects[project_id] = project.content or ""
            else:
                active_projects[project_id] = ""
        
        document = active_projects[project_id]
        
        if operation["type"] == "insert":
            text = operation["text"]
            position = min(max(0, operation["position"]), len(document))
            active_projects[project_id] = document[:position] + text + document[position:]

        elif operation["type"] == "delete":
            position = min(max(0, operation["position"]), len(document))
            length = len(operation["text"])
            if position + length <= len(document):
                active_projects[project_id] = document[:position] + document[position + length:]
            else:
                active_projects[project_id] = document[:position]
        
        elif operation["type"] == "replace":
            active_projects[project_id] = operation["text"]
        
        else:
            logging.warning(f"Unknown operation type: {operation['type']}")
            return

        # Save changes to database periodically
        if operation.get('save', False) or operation["type"] == "replace":
            project = Project.query.get(project_id)
            if project:
                project.content = active_projects[project_id]
                project.updated_at = datetime.utcnow()
                db.session.commit()

        # Send updated document to all clients in the room except sender
        emit("document", {"text": active_projects[project_id]}, 
             to=f"project_{project_id}", 
             include_self=False)

    except Exception as e:
        logging.error(f"Error handling edit: {e}", exc_info=True)
        emit("edit_error", {"message": "Failed to apply edit"}, to=request.sid)

@socketio.on("chat_message")
def handle_chat_message(data):
    if 'user_id' not in session:
        return
    
    user_id = session['user_id']
    project_id = data.get('project_id')
    message = data.get('message')
    
    if not project_id or not message:
        return
    
    # Create new chat message
    chat_message = ChatMessage(
        user_id=user_id,
        project_id=project_id,
        message=message
    )
    db.session.add(chat_message)
    db.session.commit()
    
    # Broadcast message to all clients in the room
    emit("new_chat_message", {
        "id": chat_message.id,
        "user_id": user_id,
        "username": session.get('username'),
        "message": message,
        "timestamp": chat_message.sent_at.isoformat()
    }, to=f"project_{project_id}")

@app.route("/api/projects/<int:project_id>", methods=["GET", "PUT", "DELETE"])
def api_project(project_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    project = Project.query.get_or_404(project_id)
    
    # Check if user has access
    if project.owner_id != user_id and user_id not in [u.id for u in project.collaborators]:
        return jsonify({"error": "Access denied"}), 403
    
    if request.method == "GET":
        return jsonify({
            "id": project.id,
            "name": project.name,
            "content": project.content,
            "owner_id": project.owner_id,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        })
    
    elif request.method == "PUT":
        # Only owner or collaborators with write permission can update
        if project.owner_id != user_id:
            # Check collaborator permissions
            # (This would need a more sophisticated permission system)
            pass
        
        data = request.json
        if 'name' in data:
            project.name = data['name']
        if 'content' in data:
            project.content = data['content']
            # Update in-memory version
            if project_id in active_projects:
                active_projects[project_id] = data['content']
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "id": project.id,
            "name": project.name,
            "updated_at": project.updated_at.isoformat()
        })
    
    elif request.method == "DELETE":
        # Only owner can delete
        if project.owner_id != user_id:
            return jsonify({"error": "Only the owner can delete a project"}), 403
        
        # Remove from active projects
        if project_id in active_projects:
            del active_projects[project_id]
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({"message": "Project deleted successfully"})

@socketio.on("cursor_move")
def handle_cursor_move(data):
    """Handles cursor movement and syncs with other clients."""
    if 'user_id' not in session:
        return
    
    user_id = session['user_id']
    project_id = data.get('project_id')
    position = data.get('position')
    
    if not project_id or not position:
        return
    
    # Broadcast cursor position to other clients in the room
    emit("cursor_update", {
        "user_id": user_id,
        "username": session.get('username'),
        "sid": request.sid,
        "position": position
    }, to=f"project_{project_id}", include_self=False)

@socketio.on("request_sync")
def handle_request_sync():
    """Handles request for document sync."""
    if 'user_id' not in session:
        return
    
    # Find the project room this user is in
    project_id = None
    for room in socketio.server.manager.get_rooms(request.sid, '/'):
        if room.startswith("project_"):
            project_id = room[8:]  # Remove "project_" prefix
            break
    
    if project_id and project_id in active_projects:
        emit("document", {"text": active_projects[project_id]})
    
if __name__ == "__main__":
    print("Starting Collaborative Code Editor server...")
    with app.app_context():
        db.create_all()
        create_sample_exercises()
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)