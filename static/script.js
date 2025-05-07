// =============================
// Collaborative C Code Editor - Main Client Script
// =============================
// This file contains all client-side logic for the collaborative code editor, including
// real-time editing, code execution, and user interaction.

const socket = io();
let editor;
let activeUsers = new Map();
let executionInProgress = false;

document.addEventListener('DOMContentLoaded', function() {
    const editorElement = document.getElementById('editor');
    const runButton = document.getElementById('run-button');
    const compileButton = document.getElementById('compile-button');
    const resultPanel = document.getElementById('result-panel');
    const resultContent = document.getElementById('result-content');
    const outputTabs = document.getElementById('output-tabs');
    const outputContent = document.querySelectorAll('.output-content');
    const usersList = document.getElementById('users-list');

    // Toggle results panel visibility
    document.getElementById('toggle-results').addEventListener('click', function() {
        const resultsContainer = document.querySelector('.results-container');
        const editorContainer = document.querySelector('.editor-container');
        if (resultsContainer.style.display === 'none') {
            resultsContainer.style.display = 'flex';
            editorContainer.style.width = '60%';
            this.textContent = 'Hide Results';
        } else {
            resultsContainer.style.display = 'none';
            editorContainer.style.width = '100%';
            this.textContent = 'Show Results';
        }
    });

    // Initialize CodeMirror editor
    editor = CodeMirror.fromTextArea(editorElement, {
        lineNumbers: true,
        mode: 'text/x-csrc',
        theme: 'default',
        indentUnit: 4,
        indentWithTabs: true,
        lineWrapping: true,
        autoCloseBrackets: true,
        matchBrackets: true,
        extraKeys: {
            "Ctrl-Enter": function() {
                runCode();
            }
        }
    });

    editor.setSize(null, "80vh");

    // Handle editor changes and emit to server
    editor.on('change', function(instance, changeObj) {
        if (changeObj.origin !== 'setValue' && changeObj.origin !== 'socket') {
            let operation;
            if (changeObj.origin === '+input' || changeObj.origin === 'paste') {
                operation = {
                    type: 'insert',
                    position: editor.indexFromPos(changeObj.from),
                    text: changeObj.text.join('\n')
                };
            } else if (changeObj.origin === '+delete' || changeObj.origin === 'cut') {
                operation = {
                    type: 'delete',
                    position: editor.indexFromPos(changeObj.from),
                    text: changeObj.removed.join('\n')
                };
            } else if (changeObj.origin === 'complete-reset') {
                operation = {
                    type: 'replace',
                    text: editor.getValue()
                };
            }

            if (operation) {
                socket.emit('edit', operation);
            }
        }
    });

    runButton.addEventListener('click', runCode);
    compileButton.addEventListener('click', compileCode);

    // Handle output tab switching
    outputTabs.addEventListener('click', function(e) {
        if (e.target.classList.contains('tab')) {
            const tabId = e.target.getAttribute('data-tab');
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            e.target.classList.add('active');
            outputContent.forEach(content => {
                content.style.display = 'none';
                if (content.id === tabId) {
                    content.style.display = 'block';
                }
            });
        }
    });

    if (document.querySelector('.tab')) {
        document.querySelector('.tab').classList.add('active');
        outputContent[0].style.display = 'block';
    }

    // Function to run code and handle execution
    function runCode() {
        if (executionInProgress) return;
        executionInProgress = true;
        const code = editor.getValue();
        const userInput = document.getElementById('user-input') ? document.getElementById('user-input').value : "";
        if (document.querySelector('.results-container').style.display === 'none') {
            document.getElementById('toggle-results').click();
        }
        document.getElementById('compile-output').textContent = '';
        document.getElementById('stdout-output').textContent = '';
        document.getElementById('stderr-output').textContent = '';
        const runButton = document.getElementById('run-button');
        const compileButton = document.getElementById('compile-button');
        runButton.disabled = true;
        compileButton.disabled = true;
        runButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
        document.getElementById('loading-spinner').style.display = 'block';
        fetch('/execute_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                code: code,
                project_id: projectId,
                input: userInput
            }),
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading-spinner').style.display = 'none';
            if (data.success) {
                if (data.stage === "needs_input") {
                    document.getElementById('stdout-output').textContent = data.stdout || 'Program is waiting for input. Please provide input below:';
                    createInputArea();
                    switchTab('stdout-output');
                    showNotification('Program requires input. Please provide input and click "Run with Input"', 'info');
                } else {
                    document.getElementById('stdout-output').textContent = data.stdout || 'Program executed with no output.';
                    document.getElementById('stderr-output').textContent = data.stderr || '';
                    if (document.getElementById('input-container')) {
                        if (data.needs_input) {
                            document.getElementById('input-container').style.display = 'block';
                        } else {
                            document.getElementById('input-container').style.display = 'none';
                        }
                    }
                    switchTab('stdout-output');
                    showNotification('Code executed successfully', 'success');
                }
            } else {
                if (data.stage === 'compilation') {
                    document.getElementById('compile-output').textContent = data.output || 'Compilation failed with no output.';
                    switchTab('compile-output');
                    showNotification('Compilation failed', 'error');
                } else {
                    document.getElementById('stderr-output').textContent = data.output || 'Execution failed with no output.';
                    switchTab('stderr-output');
                    showNotification('Execution failed', 'error');
                }
            }
        })
        .catch(error => {
            document.getElementById('loading-spinner').style.display = 'none';
            document.getElementById('stderr-output').textContent = 'Error: ' + error.message;
            switchTab('stderr-output');
            showNotification('Request failed', 'error');
        })
        .finally(() => {
            runButton.disabled = false;
            compileButton.disabled = false;
            runButton.innerHTML = '<i class="fas fa-play"></i> Run';
            executionInProgress = false;
        });
    }

    // Function to create input area for user input
    function createInputArea() {
        console.log("Creating input area...");
        let inputContainer = document.getElementById('input-container');
        if (inputContainer) {
            console.log("Input container already exists, making visible");
            inputContainer.style.display = 'block';
            return inputContainer;
        }
        inputContainer = document.createElement('div');
        inputContainer.id = 'input-container';
        inputContainer.className = 'input-container';
        inputContainer.style.display = 'block';
        inputContainer.style.backgroundColor = '#f7f9fc';
        inputContainer.style.padding = '15px';
        inputContainer.style.borderTop = '1px solid #e0e0e0';
        inputContainer.style.marginTop = '10px';
        inputContainer.style.marginBottom = '10px';
        const inputLabel = document.createElement('label');
        inputLabel.htmlFor = 'user-input';
        inputLabel.textContent = 'Program Input:';
        inputLabel.style.display = 'block';
        inputLabel.style.marginBottom = '8px';
        inputLabel.style.fontWeight = '500';
        inputLabel.style.color = '#2c3e50';
        const inputArea = document.createElement('textarea');
        inputArea.id = 'user-input';
        inputArea.placeholder = 'Enter input for your program here...';
        inputArea.rows = 3;
        inputArea.style.width = '100%';
        inputArea.style.padding = '10px';
        inputArea.style.border = '1px solid #ddd';
        inputArea.style.borderRadius = '5px';
        inputArea.style.fontFamily = "'Consolas', 'Monaco', monospace";
        inputArea.style.marginBottom = '10px';
        inputArea.style.resize = 'vertical';
        inputContainer.appendChild(inputLabel);
        inputContainer.appendChild(inputArea);
        document.getElementById('result-panel').appendChild(inputContainer);
        return inputContainer;
    }

    // Function to switch active tab
    function switchTab(tabId) {
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
        document.querySelectorAll('.output-content').forEach(content => {
            content.style.display = 'none';
        });
        document.getElementById(tabId).style.display = 'block';
    }

    // Function to toggle results panel
    function toggleResults() {
        const resultsContainer = document.querySelector('.results-container');
        const editorContainer = document.querySelector('.editor-container');
        if (resultsContainer.style.display === 'none') {
            resultsContainer.style.display = 'flex';
            editorContainer.style.width = '60%';
        } else {
            resultsContainer.style.display = 'none';
            editorContainer.style.width = '100%';
        }
    }

    // Function to show input area
    function showInputArea() {
        createInputArea();
    }

    // Function to run code with user input
    function runWithInput() {
        const userInput = document.getElementById('user-input').value;
        runCode(userInput);
    }

    // Function to compile code
    function compileCode() {
        if (executionInProgress) return;
        executionInProgress = true;
        const code = editor.getValue();
        const compileButton = document.getElementById('compile-button');
        compileButton.disabled = true;
        compileButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Compiling...';
        document.getElementById('loading-spinner').style.display = 'block';
        fetch('/compile_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                code: code,
                project_id: projectId
            }),
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading-spinner').style.display = 'none';
            if (data.success) {
                document.getElementById('compile-output').textContent = data.output || 'Compilation successful.';
                switchTab('compile-output');
                showNotification('Compilation successful', 'success');
            } else {
                document.getElementById('compile-output').textContent = data.output || 'Compilation failed with no output.';
                switchTab('compile-output');
                showNotification('Compilation failed', 'error');
            }
        })
        .catch(error => {
            document.getElementById('loading-spinner').style.display = 'none';
            document.getElementById('compile-output').textContent = 'Error: ' + error.message;
            switchTab('compile-output');
            showNotification('Request failed', 'error');
        })
        .finally(() => {
            compileButton.disabled = false;
            compileButton.innerHTML = '<i class="fas fa-cog"></i> Compile';
            executionInProgress = false;
        });
    }

    // Function to show notification
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Function to update users list
    function updateUsersList() {
        const usersList = document.getElementById('users-list');
        usersList.innerHTML = '';
        activeUsers.forEach((user, id) => {
            const userElement = document.createElement('div');
            userElement.className = 'user';
            userElement.textContent = user.username;
            usersList.appendChild(userElement);
        });
    }

    // Function to generate temporary ID
    function generateTempId() {
        return Math.random().toString(36).substr(2, 9);
    }

    // Function to update users list
    function updateUsersList() {
        const usersList = document.getElementById('users-list');
        usersList.innerHTML = '';
        activeUsers.forEach((user, id) => {
            const userElement = document.createElement('div');
            userElement.className = 'user';
            userElement.textContent = user.username;
            usersList.appendChild(userElement);
        });
    }

    // Function to show notification
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
});

socket.on('connect', () => {
    console.log('Connected to server');
    setTimeout(() => {
        socket.emit('request_sync');
    }, 500);
});

socket.on('document', (data) => {
    if (editor) {
        const cursor = editor.getCursor();
        const scrollInfo = editor.getScrollInfo();

        editor.operation(() => {
            editor.setValue(data.text);
            editor.changeGeneration(true);
        });

        editor.setCursor(cursor);
        editor.scrollTo(scrollInfo.left, scrollInfo.top);
    }
});

socket.on('user_connected', (data) => {
    console.log('User connected:', data.username);
    activeUsers.set(data.sid, { username: data.username, isYou: false });
    updateUsersList();
});

socket.on('user_disconnected', (data) => {
    console.log('User disconnected:', data.username);
    activeUsers.delete(data.sid);
    updateUsersList();
});

socket.on('edit_error', (data) => {
    console.error('Edit error:', data.message);
    showNotification('Synchronization error: ' + data.message, 'error');
});

socket.on('force_sync', (data) => {
    editor.setValue(data.text);
});

socket.on('all_users', (data) => {
    console.log('Received all users:', data.users);

    const currentUser = Array.from(activeUsers.values()).find(user => user.isYou);
    activeUsers.clear();

    if (currentUser) {
        activeUsers.set(socket.id, currentUser);
    }

    data.users.forEach(user => {
        if (user.username !== currentUser.username) {
            activeUsers.set(user.sid || generateTempId(), {
                username: user.username,
                isYou: false
            });
        }
    });

    updateUsersList();
});

function generateTempId() {
    return 'temp-' + Math.random().toString(36).substr(2, 9);
}

function updateUsersList() {
    const usersList = document.getElementById('users-list');
    if (!usersList) return;

    usersList.innerHTML = '';
    activeUsers.forEach((user, sid) => {
        const li = document.createElement('li');
        li.textContent = user.username + (user.isYou ? ' (you)' : '');
        li.className = user.isYou ? 'current-user' : '';
        usersList.appendChild(li);
    });
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}