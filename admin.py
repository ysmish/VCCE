# admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, Exercise, CompilationHistory
from exercise_manager import create_exercise, get_all_exercises, get_exercise_by_id
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def check_admin():
    """Check if the user is an admin"""
    if 'user_id' not in session:
        flash('You must be logged in to access this page', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user or user.username != 'admin':  # Simple admin check, improve in production
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))

@admin_bp.route('/')
def index():
    """Admin dashboard"""
    user_count = User.query.count()
    exercise_count = Exercise.query.count()
    compilation_count = CompilationHistory.query.count()
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_compilations = CompilationHistory.query.order_by(CompilationHistory.compiled_at.desc()).limit(5).all()
    
    recent_user_ids = [c.user_id for c in recent_compilations]
    user_map = {u.id: u.username for u in User.query.filter(User.id.in_(recent_user_ids)).all()}
    
    return render_template(
        'admin/index.html',
        user_count=user_count,
        exercise_count=exercise_count,
        compilation_count=compilation_count,
        recent_users=recent_users,
        recent_compilations=recent_compilations,
        user_map=user_map
    )

@admin_bp.route('/users')
def users():
    """User management"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/exercises')
def exercises():
    """Exercise management"""
    exercises = get_all_exercises()
    return render_template('admin/exercises.html', exercises=exercises)

@admin_bp.route('/exercises/new', methods=['GET', 'POST'])
def new_exercise():
    """Create a new exercise"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        difficulty = request.form.get('difficulty')
        category = request.form.get('category')
        initial_code = request.form.get('initial_code')
        solution_code = request.form.get('solution_code')
        test_cases_json = request.form.get('test_cases')
        
        try:
            test_cases = json.loads(test_cases_json)
            
            exercise = create_exercise(
                title=title,
                description=description,
                difficulty=difficulty,
                category=category,
                initial_code=initial_code,
                solution_code=solution_code,
                test_cases=test_cases
            )
            
            flash(f'Exercise "{title}" created successfully', 'success')
            return redirect(url_for('admin.exercises'))
        except Exception as e:
            flash(f'Error creating exercise: {str(e)}', 'error')
    
    return render_template('admin/new_exercise.html')

@admin_bp.route('/exercises/<int:exercise_id>', methods=['GET', 'POST'])
def edit_exercise(exercise_id):
    """Edit an exercise"""
    exercise = get_exercise_by_id(exercise_id)
    if not exercise:
        flash('Exercise not found', 'error')
        return redirect(url_for('admin.exercises'))
    
    if request.method == 'POST':
        exercise.title = request.form.get('title')
        exercise.description = request.form.get('description')
        exercise.difficulty = request.form.get('difficulty')
        exercise.category = request.form.get('category')
        exercise.initial_code = request.form.get('initial_code')
        exercise.solution_code = request.form.get('solution_code')
        
        test_cases_json = request.form.get('test_cases')
        try:
            test_cases = json.loads(test_cases_json)
            exercise.test_cases = json.dumps(test_cases)
            
            db.session.commit()
            flash(f'Exercise "{exercise.title}" updated successfully', 'success')
            return redirect(url_for('admin.exercises'))
        except Exception as e:
            flash(f'Error updating exercise: {str(e)}', 'error')
    
    # Convert test_cases JSON string to Python object for the template
    test_cases = json.loads(exercise.test_cases)
    
    return render_template(
        'admin/edit_exercise.html',
        exercise=exercise,
        test_cases=json.dumps(test_cases, indent=2)
    )

@admin_bp.route('/exercises/<int:exercise_id>/delete', methods=['POST'])
def delete_exercise(exercise_id):
    """Delete an exercise"""
    exercise = get_exercise_by_id(exercise_id)
    if not exercise:
        flash('Exercise not found', 'error')
        return redirect(url_for('admin.exercises'))
    
    title = exercise.title
    db.session.delete(exercise)
    db.session.commit()
    
    flash(f'Exercise "{title}" deleted successfully', 'success')
    return redirect(url_for('admin.exercises'))

@admin_bp.route('/stats')
def stats():
    """View system statistics"""
    # User statistics
    total_users = User.query.count()
    # You can add more statistics here
    
    # Exercise statistics
    exercises_by_difficulty = db.session.query(
        Exercise.difficulty, db.func.count(Exercise.id)
    ).group_by(Exercise.difficulty).all()
    
    # Compilation statistics
    successful_compilations = CompilationHistory.query.filter_by(status='success').count()
    failed_compilations = CompilationHistory.query.filter(CompilationHistory.status != 'success').count()
    
    return render_template(
        'admin/stats.html',
        total_users=total_users,
        exercises_by_difficulty=exercises_by_difficulty,
        successful_compilations=successful_compilations,
        failed_compilations=failed_compilations
    )