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
        
        // Get input if the input field exists
        const userInput = document.getElementById('user-input') ? document.getElementById('user-input').value : "";
        
        // Show results if hidden
        if (document.querySelector('.results-container').style.display === 'none') {
            document.getElementById('toggle-results').click();
        }
        
        // Clear output areas
        document.getElementById('compile-output').textContent = '';
        document.getElementById('stdout-output').textContent = '';
        document.getElementById('stderr-output').textContent = '';
        
        // Update UI
        const runButton = document.getElementById('run-button');
        const compileButton = document.getElementById('compile-button');
        runButton.disabled = true;
        compileButton.disabled = true;
        runButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
        document.getElementById('loading-spinner').style.display = 'block';
    
        // Send to server
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
                // In the runCode function, where it handles needs_input:
                if (data.stage === "needs_input") {
                    // Program needs input - show the prompt and input area
                    document.getElementById('stdout-output').textContent = data.stdout || 'Program is waiting for input. Please provide input below:';
                    
                    console.log("Program needs input, creating input area");
                    // IMPORTANT: Create input area and ensure it's visible
                    createInputArea();
                    
                    // Make sure stdout tab is active
                    switchTab('stdout-output');
                    
                    // Show notification prompting for input
                    showNotification('Program requires input. Please provide input and click "Run with Input"', 'info');
                } else {
                    // Normal execution with results
                    document.getElementById('stdout-output').textContent = data.stdout || 'Program executed with no output.';
                    document.getElementById('stderr-output').textContent = data.stderr || '';
                    
                    // If there was already input, keep it visible if needed
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
    
    // Improved createInputArea function with debug output and inline styles
    function createInputArea() {
        console.log("Creating input area...");
        
        // Check if input container already exists
        let inputContainer = document.getElementById('input-container');
        if (inputContainer) {
            console.log("Input container already exists, making visible");
            inputContainer.style.display = 'block';
            return inputContainer;
        }
        
        // Create new input container with inline styles for visibility
        inputContainer = document.createElement('div');
        inputContainer.id = 'input-container';
        inputContainer.className = 'input-container';
        
        // Add inline styles to ensure visibility
        inputContainer.style.display = 'block';
        inputContainer.style.backgroundColor = '#f7f9fc';
        inputContainer.style.padding = '15px';
        inputContainer.style.borderTop = '1px solid #e0e0e0';
        inputContainer.style.marginTop = '10px';
        inputContainer.style.marginBottom = '10px';
        
        // Create label
        const inputLabel = document.createElement('label');
        inputLabel.htmlFor = 'user-input';
        inputLabel.textContent = 'Program Input:';
        inputLabel.style.display = 'block';
        inputLabel.style.marginBottom = '8px';
        inputLabel.style.fontWeight = '500';
        inputLabel.style.color = '#2c3e50';
        
        // Create textarea
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
        
        // Create run button
        const runWithInputButton = document.createElement('button');
        runWithInputButton.id = 'run-with-input-button';
        runWithInputButton.className = 'btn action-btn run-btn';
        runWithInputButton.innerHTML = '<i class="fas fa-play"></i> Run with Input';
        runWithInputButton.style.marginTop = '5px';
        runWithInputButton.style.backgroundColor = '#2ecc71';
        runWithInputButton.style.color = 'white';
        runWithInputButton.style.border = 'none';
        runWithInputButton.style.borderRadius = '6px';
        runWithInputButton.style.padding = '8px 16px';
        runWithInputButton.style.cursor = 'pointer';
        
        // Add event listener
        runWithInputButton.addEventListener('click', function() {
            runCode();
        });
        
        // Assemble the container
        inputContainer.appendChild(inputLabel);
        inputContainer.appendChild(inputArea);
        inputContainer.appendChild(runWithInputButton);
        
        // Try multiple insertion strategies to ensure it's added to the DOM
        // Strategy 1: Insert before result panel
        const resultPanel = document.getElementById('result-panel');
        if (resultPanel && resultPanel.parentNode) {
            console.log("Inserting before result panel");
            resultPanel.parentNode.insertBefore(inputContainer, resultPanel);
            return inputContainer;
        }
        
        // Strategy 2: Append to results container
        const resultsContainer = document.querySelector('.results-container');
        if (resultsContainer) {
            console.log("Appending to results container");
            resultsContainer.appendChild(inputContainer);
            return inputContainer;
        }
        
        // Strategy 3: Append to output tabs
        const outputTabs = document.getElementById('output-tabs');
        if (outputTabs && outputTabs.parentNode) {
            console.log("Inserting after output tabs");
            if (outputTabs.nextSibling) {
                outputTabs.parentNode.insertBefore(inputContainer, outputTabs.nextSibling);
            } else {
                outputTabs.parentNode.appendChild(inputContainer);
            }
            return inputContainer;
        }
        
        console.error("Could not find a place to insert input container!");
        return null;
    }
    
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
    

    // Add this function to toggle results
    function toggleResults() {
        const resultsContainer = document.querySelector('.results-container');
        const editorContainer = document.querySelector('.editor-container');
        const toggleButton = document.getElementById('toggle-results');
        
        if (resultsContainer.style.display === 'none') {
            resultsContainer.style.display = 'flex';
            editorContainer.style.width = '60%';
            toggleButton.innerHTML = '<i class="fas fa-columns"></i> Hide Results';
        } else {
            resultsContainer.style.display = 'none';
            editorContainer.style.width = '100%';
            toggleButton.innerHTML = '<i class="fas fa-columns"></i> Show Results';
        }
    }

    // Function to show input area - add this at the end of your script.js file
    function showInputArea() {
        // Create input area if it doesn't exist
        let inputContainer = document.getElementById('input-container');
        if (!inputContainer) {
            inputContainer = document.createElement('div');
            inputContainer.id = 'input-container';
            inputContainer.className = 'input-container';
            
            const inputLabel = document.createElement('label');
            inputLabel.htmlFor = 'user-input';
            inputLabel.textContent = 'Program Input:';
            
            const inputArea = document.createElement('textarea');
            inputArea.id = 'user-input';
            inputArea.placeholder = 'Enter input for your program here...';
            inputArea.rows = 3;
            
            const runWithInputButton = document.createElement('button');
            runWithInputButton.id = 'run-with-input-button';
            runWithInputButton.className = 'btn action-btn run-btn';
            runWithInputButton.innerHTML = '<i class="fas fa-play"></i> Run with Input';
            runWithInputButton.onclick = runCode;
            
            inputContainer.appendChild(inputLabel);
            inputContainer.appendChild(inputArea);
            inputContainer.appendChild(runWithInputButton);
            
            // Insert before the result panel
            const resultPanel = document.getElementById('result-panel');
            resultPanel.parentNode.insertBefore(inputContainer, resultPanel);
        }
        
        // Show the input area
        inputContainer.style.display = 'block';
    }

    // Add an input area directly to the results panel as soon as the page loads
    document.addEventListener('DOMContentLoaded', function() {
        // Add this after your other event listeners
        setTimeout(function() {
            const standardOutputTab = document.getElementById('stdout-output');
            if (standardOutputTab) {
                // Create input container
                const inputDiv = document.createElement('div');
                inputDiv.style.marginTop = '20px';
                inputDiv.style.padding = '10px';
                inputDiv.style.backgroundColor = '#2c3e50';
                inputDiv.style.borderRadius = '5px';
                
                // Create heading
                const heading = document.createElement('h4');
                heading.textContent = 'Program Input';
                heading.style.color = 'white';
                heading.style.marginBottom = '10px';
                
                // Create textarea
                const textarea = document.createElement('textarea');
                textarea.id = 'user-input';
                textarea.placeholder = 'Type your input here...';
                textarea.style.width = '100%';
                textarea.style.height = '80px';
                textarea.style.padding = '8px';
                textarea.style.marginBottom = '10px';
                textarea.style.borderRadius = '4px';
                textarea.style.border = 'none';
                textarea.style.fontFamily = 'monospace';
                
                // Create button
                const button = document.createElement('button');
                button.textContent = 'Run With Input';
                button.style.backgroundColor = '#2ecc71';
                button.style.color = 'white';
                button.style.border = 'none';
                button.style.padding = '8px 16px';
                button.style.borderRadius = '4px';
                button.style.cursor = 'pointer';
                button.style.fontWeight = 'bold';
                
                // Add event listener to the button
                button.addEventListener('click', function() {
                    runWithInput();
                });
                
                // Assemble the container
                inputDiv.appendChild(heading);
                inputDiv.appendChild(textarea);
                inputDiv.appendChild(button);
                
                // Append to standard output tab
                standardOutputTab.appendChild(inputDiv);
            }
        }, 1000); // Wait 1 second for the DOM to be fully loaded
    });

    // Function to run code with input
    function runWithInput() {
        const inputText = document.getElementById('user-input').value;
        
        // Get the editor value
        const code = editor.getValue();
        
        // Show loading indicator
        const runButton = document.getElementById('run-button');
        if (runButton) {
            runButton.disabled = true;
            runButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
        }
        
        document.getElementById('loading-spinner').style.display = 'block';
        
        // Send to server
        fetch('/execute_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code: code,
                project_id: projectId,
                input: inputText
            })
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading-spinner').style.display = 'none';
            
            // Display results
            document.getElementById('stdout-output').textContent = data.stdout || 'No output';
            document.getElementById('stderr-output').textContent = data.stderr || '';
            
            // Re-add input area after updating content
            const standardOutputTab = document.getElementById('stdout-output');
            if (standardOutputTab) {
                // Get existing input div if it exists
                let inputDiv = document.querySelector('#stdout-output > div');
                
                // If it doesn't exist, create a new one
                if (!inputDiv) {
                    // Create new input area (same code as above)
                    // Copy the code from above to recreate the input area
                    inputDiv = document.createElement('div');
                    // ... (add all the same styling and elements)
                    standardOutputTab.appendChild(inputDiv);
                }
            }
            
            // Show notification
            showNotification('Code executed successfully', 'success');
            
            // Make sure the stdout tab is active
            document.querySelector('[data-tab="stdout-output"]').click();
        })
        .catch(error => {
            document.getElementById('loading-spinner').style.display = 'none';
            document.getElementById('stderr-output').textContent = 'Error: ' + error.message;
            showNotification('Request failed', 'error');
        })
        .finally(() => {
            // Re-enable run button
            if (runButton) {
                runButton.disabled = false;
                runButton.innerHTML = '<i class="fas fa-play"></i> Run';
            }
        });
    }
    
    function compileCode() {
        if (executionInProgress) return;
        executionInProgress = true;
    
        const code = editor.getValue();
        const compileButton = document.getElementById('compile-button');
        const runButton = document.getElementById('run-button');
        
        // Show results if hidden
        if (document.querySelector('.results-container').style.display === 'none') {
            toggleResults();
        }
        
        // Clear output areas
        document.getElementById('compile-output').textContent = '';
        
        // Update UI
        compileButton.disabled = true;
        runButton.disabled = true;
        compileButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Compiling...';
        document.getElementById('loading-spinner').style.display = 'block';
    
        // Send to server
        fetch('/execute_code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                code: code,
                project_id: projectId,
                compile_only: true  // Add this flag
            }),
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading-spinner').style.display = 'none';
            
            if (data.success || data.stage === 'execution') {
                document.getElementById('compile-output').textContent = 'Compilation successful.';
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
            runButton.disabled = false;
            compileButton.innerHTML = '<i class="fas fa-cogs"></i> Compile';
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