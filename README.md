# VCCE - Collaborative C Code Editor

A modern, real-time collaborative C programming environment with integrated exercises, memory analysis, and comprehensive project management.

## 🚀 Features

### 💻 Collaborative Development
- **Real-time collaborative editing** with live cursor tracking
- **Project sharing** with granular permissions
- **Integrated chat** for team communication
- **Live user presence** indicators

### 🔧 Code Development Tools
- **Syntax highlighting** with modern C11 standard support
- **Real-time compilation** with detailed error reporting
- **Code execution** with input/output handling
- **Memory analysis** using Valgrind integration
- **Security sandboxing** with resource limits

### 📚 Educational Features
- **Interactive coding exercises** with automatic testing
- **Progress tracking** and attempt history
- **Difficulty-based categorization** (Easy, Medium, Hard)
- **Solution reveal** system for learning

### 👑 Administration
- **User management** with detailed analytics
- **Exercise creation** and management tools
- **System statistics** with visual charts
- **Compilation history** tracking

### 🎨 Modern UI/UX
- **ABYSS PRO theme** - Professional dark interface with biomorphic elements
- **Fully responsive** design for all devices
- **Accessibility compliant** with proper contrast and navigation
- **Advanced animations** and micro-interactions

## 🛠️ Technology Stack

- **Backend**: Flask, Socket.IO, SQLAlchemy
- **Frontend**: HTML5, CSS3, JavaScript, CodeMirror
- **Database**: PostgreSQL (production) / SQLite (development)
- **Code Execution**: GCC compiler with security sandboxing
- **Memory Analysis**: Valgrind
- **Deployment**: Docker, Docker Compose
- **Security**: SSL/TLS encryption, bcrypt password hashing

## 📋 Prerequisites

- Python 3.9+
- GCC compiler
- Valgrind (for memory analysis)
- Docker & Docker Compose (recommended)
- PostgreSQL (for production)

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd vcce
   ```

2. **Start with Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - HTTPS: https://localhost:5001
   - HTTP: http://localhost:5001

### Option 2: Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install system dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install gcc valgrind

   # macOS
   brew install gcc valgrind
   ```

3. **Set environment variables**
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export DATABASE_URL="sqlite:///site.db"  # or PostgreSQL URL
   ```

4. **Initialize the database**
   ```bash
   python -c "from models import db, app; from exercise_manager import create_sample_exercises; app.app_context().push(); db.create_all(); create_sample_exercises()"
   ```

5. **Run the application**
   ```bash
   python server.py
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret | `INSECURE_DEFAULT_KEY` |
| `DATABASE_URL` | Database connection string | `sqlite:///site.db` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `*` |

### SSL Configuration

The application supports SSL/TLS encryption. Place your certificates in:
- `certs/cert.pem` (certificate)
- `certs/key.pem` (private key)

Or in the root directory as `cert.pem` and `key.pem`.

## 📖 Usage Guide

### Getting Started

1. **Register an account** at `/register`
2. **Login** at `/login`
3. **Create your first project** from the dashboard
4. **Start coding** collaboratively!

### Creating Projects

1. Click "New Project" on the dashboard
2. Enter a project name
3. Start coding in the collaborative editor
4. Invite collaborators using their username

### Working with Exercises

1. Navigate to "Coding Exercises"
2. Filter by difficulty or status
3. Start an exercise and write your solution
4. Test against provided test cases
5. View solutions after completion

### Admin Features (admin user)

1. **User Management**: View and manage registered users
2. **Exercise Management**: Create, edit, and delete exercises
3. **Statistics**: Monitor system usage and performance
4. **Compilation History**: Track code execution patterns

## 🔒 Security Features

- **Code Sandboxing**: Resource limits prevent system abuse
- **Input Validation**: Dangerous code patterns are blocked
- **Secure Authentication**: bcrypt password hashing
- **SSL/TLS Support**: Encrypted communications
- **CORS Protection**: Configurable origin restrictions

## 🧪 Testing Code

The system provides multiple ways to test your C code:

1. **Compile Only**: Check for syntax errors
2. **Run Code**: Execute with optional input
3. **Memory Analysis**: Use Valgrind for leak detection
4. **Exercise Testing**: Automatic test case validation

## 📚 Exercise System

### Creating Exercises (Admin)

1. Navigate to Admin Panel → Exercises
2. Click "New Exercise"
3. Fill in the exercise details:
   - Title and description
   - Difficulty level
   - Category
   - Initial code template
   - Solution code
   - Test cases in JSON format

### Test Case Format

```json
[
  {
    "input": "5 7",
    "expected_output": "12"
  },
  {
    "input": "10 20",
    "expected_output": "30"
  }
]
```

## 🎨 Customization

### Themes

The application uses the ABYSS PRO theme with:
- Dark color scheme with purple accents
- Biomorphic design elements
- Smooth animations and transitions
- Professional code editor styling

### Code Editor

Built on CodeMirror with:
- C/C++ syntax highlighting
- Auto-completion
- Bracket matching
- Line numbering
- Multiple cursors support

## 🚀 Deployment

### Production Deployment

1. **Use Docker Compose** for easy deployment
2. **Configure SSL certificates** for HTTPS
3. **Set up PostgreSQL** for the database
4. **Configure environment variables**
5. **Set up reverse proxy** (nginx recommended)

### Docker Production Setup

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "443:5001"
    volumes:
      - ./certs:/app/certs
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/vcce
      - SECRET_KEY=your-production-secret-key
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=vcce
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**: Change the port in `server.py` and `docker-compose.yml`
2. **SSL certificate errors**: Ensure certificates are properly placed and valid
3. **Database connection issues**: Check DATABASE_URL configuration
4. **Compilation errors**: Ensure GCC is installed and accessible

### Debug Mode

For development, set `debug=True` in `server.py` to enable:
- Auto-reload on file changes
- Detailed error messages
- Development toolbar

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the configuration guide
3. Check system requirements
4. Submit an issue with detailed information

## 🔮 Future Enhancements

- Multiple programming language support
- Advanced collaboration features
- Integrated debugger
- Code review system
- Version control integration
- Mobile app development

---

