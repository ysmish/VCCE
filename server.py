from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit
import os
import logging
import subprocess
import tempfile
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from models import User

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder="templates")
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "INSECURE_DEFAULT_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins=allowed_origins)

document = ""


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
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/execute_code", methods=["POST"])
def execute_code():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    code = request.json.get("code", "")
    if not code:
        return jsonify({"error": "No code provided"}), 400

    with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as source_file:
        source_path = source_file.name
        source_file.write(code.encode())

    exec_path = source_path[:-2]  # Remove .c extension

    try:
        compile_result = subprocess.run(
            ["gcc", source_path, "-o", exec_path],
            capture_output=True,
            text=True,
            timeout=5
        )

        if compile_result.returncode != 0:
            os.unlink(source_path)
            try:
                os.unlink(exec_path)
            except:
                pass
            return jsonify({
                "success": False,
                "stage": "compilation",
                "output": compile_result.stderr
            })

        try:
            execution_result = subprocess.run(
                [exec_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            return jsonify({
                "success": True,
                "stage": "execution",
                "stdout": execution_result.stdout,
                "stderr": execution_result.stderr,
                "returncode": execution_result.returncode
            })

        except subprocess.TimeoutExpired:
            return jsonify({
                "success": False,
                "stage": "execution",
                "output": "Execution timed out after 5 seconds"
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "stage": "execution",
                "output": f"Error during execution: {str(e)}"
            })
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "stage": "compilation",
            "output": "Compilation timed out after 5 seconds"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "stage": "compilation",
            "output": f"Error during compilation: {str(e)}"
        })
    finally:
        try:
            os.unlink(source_path)
            os.unlink(exec_path)
        except:
            pass


connected_users = {}

@socketio.on("connect")
def handle_connect():
    """Sends the initial document state to the new user and all connected users info."""
    global connected_users

    print(f"User connected: {request.sid}")
    username = session.get('username', 'Anonymous')
    connected_users[request.sid] = {'username': username}
    emit("user_connected", {"username": username, "sid": request.sid}, broadcast=True)
    emit("document", {"text": document})
    emit("all_users", {"users": list(connected_users.values())})


@socketio.on("disconnect")
def handle_disconnect():
    global connected_users

    username = session.get('username', 'Anonymous')
    print(f"User disconnected: {request.sid} ({username})")
    if request.sid in connected_users:
        del connected_users[request.sid]

    emit("user_disconnected", {"sid": request.sid, "username": username}, broadcast=True)


@socketio.on("edit")
def handle_edit(operation):
    """Handles edit operations and syncs them with all clients."""
    global document
    try:
        if operation["type"] == "insert":
            text = operation["text"]  # Don't sanitize for code editor
            position = min(max(0, operation["position"]), len(document))
            document = document[:position] + text + document[position:]

        elif operation["type"] == "delete":
            position = min(max(0, operation["position"]), len(document))
            length = len(operation["text"])
            if position + length <= len(document):
                document = document[:position] + document[position + length:]
            else:
                document = document[:position]
        elif operation["type"] == "replace":
            document = operation["text"]
        else:
            logging.warning(f"Unknown operation type: {operation['type']}")
            return

        emit("document", {"text": document}, broadcast=True, include_self=False)

    except Exception as e:
        logging.error(f"Error handling edit: {e}", exc_info=True)
        emit("edit_error", {"message": "Failed to apply edit"}, to=request.sid)


@app.route("/")
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", username=session.get('username'))


if __name__ == "__main__":
    print("Starting Collaborative Code Editor server...")
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)