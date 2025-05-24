# models.py
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", 'sqlite:///site.db')
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "INSECURE_DEFAULT_KEY")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Association table for project collaborators
project_collaborators = db.Table('project_collaborators',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('permission', db.String(20), default='read-write')  # read-only, read-write, admin
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    owned_projects = db.relationship('Project', backref='owner', lazy=True)
    collaborated_projects = db.relationship('Project', 
                                          secondary=project_collaborators,
                                          lazy='subquery',
                                          backref=db.backref('collaborators', lazy=True))
    exercise_progress = db.relationship('ExerciseProgress', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f"Project('{self.name}', owner_id: {self.owner_id})"

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = db.relationship('Project', backref=db.backref('documents', lazy=True))
    
    def __repr__(self):
        return f"Document('{self.name}', project_id: {self.project_id}, owner_id: {self.user_id})"

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # easy, medium, hard
    category = db.Column(db.String(50), nullable=False)
    initial_code = db.Column(db.Text, nullable=True)
    solution_code = db.Column(db.Text, nullable=False)
    test_cases = db.Column(db.Text, nullable=False)  # JSON serialized test cases
    
    progress = db.relationship('ExerciseProgress', backref='exercise', lazy=True)
    
    def __repr__(self):
        return f"Exercise('{self.title}', difficulty: {self.difficulty})"

class ExerciseProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    status = db.Column(db.String(20), default='not_started')  # not_started, in_progress, completed
    user_code = db.Column(db.Text, nullable=True)
    attempts = db.Column(db.Integer, default=0)
    last_attempt = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"ExerciseProgress(user_id: {self.user_id}, exercise_id: {self.exercise_id}, status: {self.status})"

class CompilationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=True)
    code = db.Column(db.Text, nullable=False)
    compiled_at = db.Column(db.DateTime, default=datetime.utcnow)
    compilation_output = db.Column(db.Text, nullable=True)
    execution_output = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False)  # success, compilation_error, runtime_error
    
    def __repr__(self):
        return f"CompilationHistory(user_id: {self.user_id}, status: {self.status})"

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('messages', lazy=True))
    project = db.relationship('Project', backref=db.backref('messages', lazy=True))
    
    def __repr__(self):
        return f"ChatMessage(user_id: {self.user_id}, project_id: {self.project_id})"

if __name__ == '__main__':
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
    print("Database tables created successfully!")