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

    function runCode() {
        if (executionInProgress) return;
        executionInProgress = true;

        const code = editor.getValue();
        compileButton.disabled = true;
        runButton.disabled = true;
        runButton.textContent = 'Running...';

        document.getElementById('compile-output').textContent = '';
        document.getElementById('stdout-output').textContent = '';
        document.getElementById('stderr-output').textContent = '';

        document.getElementById('loading-spinner').style.display = 'block';

        fetch('/execute_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ code: code }),
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading-spinner').style.display = 'none';

            if (data.success) {
                document.getElementById('stdout-output').textContent = data.stdout || 'Program executed with no output.';
                document.getElementById('stderr-output').textContent = data.stderr || '';

                document.querySelector('[data-tab="stdout-output"]').click();

                showNotification('Code executed successfully', 'success');
            } else {
                if (data.stage === 'compilation') {
                    document.getElementById('compile-output').textContent = data.output || 'Compilation failed with no output.';
                    document.querySelector('[data-tab="compile-output"]').click();
                    showNotification('Compilation failed', 'error');
                } else {
                    document.getElementById('stderr-output').textContent = data.output || 'Execution failed with no output.';
                    document.querySelector('[data-tab="stderr-output"]').click();
                    showNotification('Execution failed', 'error');
                }
            }
        })
        .catch(error => {
            document.getElementById('loading-spinner').style.display = 'none';
            document.getElementById('stderr-output').textContent = 'Error: ' + error.message;
            document.querySelector('[data-tab="stderr-output"]').click();
            showNotification('Request failed', 'error');
        })
        .finally(() => {
            compileButton.disabled = false;
            runButton.disabled = false;
            runButton.textContent = 'Run';
            executionInProgress = false;
        });
    }

    function compileCode() {
        if (executionInProgress) return;
        executionInProgress = true;

        const code = editor.getValue();
        compileButton.disabled = true;
        runButton.disabled = true;
        compileButton.textContent = 'Compiling...';
        document.getElementById('compile-output').textContent = '';
        document.getElementById('loading-spinner').style.display = 'block';

        fetch('/execute_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ code: code, compile_only: true }),
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading-spinner').style.display = 'none';
            if (data.success || data.stage === 'execution') {
                document.getElementById('compile-output').textContent = 'Compilation successful.';
                document.querySelector('[data-tab="compile-output"]').click();
                showNotification('Compilation successful', 'success');
            } else {
                document.getElementById('compile-output').textContent = data.output || 'Compilation failed with no output.';
                document.querySelector('[data-tab="compile-output"]').click();
                showNotification('Compilation failed', 'error');
            }
        })
        .catch(error => {
            document.getElementById('loading-spinner').style.display = 'none';
            document.getElementById('compile-output').textContent = 'Error: ' + error.message;
            document.querySelector('[data-tab="compile-output"]').click();
            showNotification('Request failed', 'error');
        })
        .finally(() => {
            compileButton.disabled = false;
            runButton.disabled = false;
            compileButton.textContent = 'Compile';
            executionInProgress = false;
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
    function updateUsersList() {
        usersList.innerHTML = '';
        activeUsers.forEach((user, sid) => {
            const li = document.createElement('li');
            li.textContent = user.username + (user.isYou ? ' (you)' : '');
            li.className = user.isYou ? 'current-user' : '';
            usersList.appendChild(li);
        });
    }
    const currentUsername = document.getElementById('current-username').textContent;
    const currentSid = socket.id;
    activeUsers.set(currentSid, { username: currentUsername, isYou: true });
    updateUsersList();
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