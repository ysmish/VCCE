# VCCE – Collaborative C Code Editor

A modern, full-featured web platform for collaborative C programming, real-time code editing, project management, and coding exercises. Built with Flask, Flask-SocketIO, SQLAlchemy, and a beautiful custom dark UI.

---

## Features

- **Real-Time Collaborative Code Editing**  
  Work together on C code projects with live updates, user presence, and chat.

- **Project & Document Management**  
  Create, edit, and manage multiple projects and files. Invite collaborators with granular permissions.

- **Code Compilation & Execution**  
  Compile and run C code securely in the browser. Input handling, output, and error display included.

- **Coding Exercises & Progress Tracking**  
  Solve curated C exercises with test cases, auto-grading, and personal progress tracking.

- **Admin Dashboard**  
  Manage users, exercises, and view system statistics with beautiful admin interfaces.

- **Modern UI/UX**  
  Custom dark theme, responsive layouts, advanced syntax highlighting, and smooth user experience.

---

## Tech Stack

- **Backend:** Python, Flask, Flask-SocketIO, SQLAlchemy, Flask-Bcrypt
- **Frontend:** HTML5, CSS3 (custom dark theme), JavaScript, CodeMirror, FontAwesome
- **Database:** SQLite (default), PostgreSQL (Docker)
- **Containerization:** Docker, Docker Compose

---

## Quick Start

### 1. Local Development

#### Prerequisites
- Python 3.9+
- (Optional) [Docker](https://www.docker.com/) for containerized setup

#### Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Set up environment variables

Create a `.env` file in the project root:

```
SECRET_KEY=your_secure_secret_key
DATABASE_URL=sqlite:///site.db
ALLOWED_ORIGINS=*
```

#### Initialize the database

```bash
python models.py
```

#### Run the server

```bash
python server.py
```

Visit [http://localhost:5001](http://localhost:5001) in your browser.

---

### 2. Docker Deployment

#### Build and run with Docker Compose

```bash
docker-compose up --build
```

- The web app will be available at [http://localhost:5001](http://localhost:5001)
- PostgreSQL database runs in a separate container

---

## Project Structure

```
.
├── server.py                # Main Flask app and SocketIO server
├── models.py                # SQLAlchemy models (User, Project, Exercise, etc.)
├── exercise_manager.py      # Exercise creation, retrieval, and progress logic
├── admin.py                 # Admin routes and logic
├── static/
│   ├── style.css            # Custom dark theme and UI styles
│   └── script.js            # Frontend logic (editor, chat, collaboration)
├── templates/
│   ├── *.html               # Jinja2 templates for all pages
│   └── admin/               # Admin dashboard templates
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker build instructions
├── docker-compose.yml       # Multi-container orchestration
└── README.md                # Project documentation
```

---

## Key Components

### Real-Time Collaboration

- Powered by Flask-SocketIO
- Live code editing, user cursors, and chat
- Project-based rooms and user presence

### Code Compilation & Security

- C code compiled and executed in a sandboxed environment
- Resource limits and dangerous code detection for safety
- Input/output handling for interactive programs

### Coding Exercises

- Admins can create, edit, and manage exercises with test cases
- Users can solve exercises, get instant feedback, and track progress
- Auto-grading with detailed results and solution reveal

### Admin Dashboard

- User management (view, search, reset password)
- Exercise management (CRUD, test cases, difficulty, category)
- System statistics (user count, exercise stats, compilation stats with charts)

### Modern UI/UX

- Custom dark theme with CSS variables and modern fonts
- Responsive layouts for desktop and mobile
- Advanced syntax highlighting (CodeMirror, purple-themed)
- Smooth transitions, notifications, and accessibility

---

## Customization

- **Theming:**  
  Edit `static/style.css` to adjust colors, fonts, and layout.

- **Exercise Content:**  
  Use the admin dashboard to add or edit exercises, or modify `exercise_manager.py` for bulk operations.

- **Database:**  
  Default is SQLite for local use. For production, configure `DATABASE_URL` for PostgreSQL or another supported DB.

---

## Security Notes

- Code execution is sandboxed, but always review and test before deploying in production.
- Use strong secrets and secure your deployment (HTTPS, firewall, etc.) for public use.

---

## License

MIT License.  
See [LICENSE](LICENSE) for details.

---

## Credits

- Built with [Flask](https://flask.palletsprojects.com/), [Flask-SocketIO](https://flask-socketio.readthedocs.io/), [CodeMirror](https://codemirror.net/), and open-source love.
- UI inspired by modern code editors and collaborative platforms.

---



