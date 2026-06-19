// Antigravity AI Chat - Webview JavaScript
// This file contains all JavaScript logic for the webview interface

// Acquire VSCode API at the very beginning
const vscode = acquireVsCodeApi();

// DOM elements
const chat = document.getElementById('chat');
const input = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');
const statusBar = document.getElementById('statusBar');
const statusText = document.getElementById('statusText');
const modeSelect = document.getElementById('modeSelect');
const providerSelect = document.getElementById('providerSelect');
const modelSelect = document.getElementById('modelSelect');
const settingsPanel = document.getElementById('settingsPanel');
const rawCodePanel = document.getElementById('rawCodePanel');
const rawCodeTextarea = document.getElementById('rawCodeTextarea');
const modelIndicator = document.getElementById('modelIndicator');
const modelIndicatorText = document.getElementById('modelIndicatorText');
const tokenUsageFill = document.getElementById('tokenUsageFill');
const tokenUsageCount = document.getElementById('tokenUsageCount');
const retryBtn = document.getElementById('retryBtn');

// State variables
let conversationHistory = [];
let tokenCount = 0;
const maxTokens = 10000;
let lastCommand = null;

// Load settings from localStorage
function loadSettings() {
    const settings = JSON.parse(localStorage.getItem('antigravitySettings') || '{}');
    
    if (settings.smartRouting !== undefined) document.getElementById('smartRouting').checked = settings.smartRouting;
    if (settings.preferFreeModels !== undefined) document.getElementById('preferFreeModels').checked = settings.preferFreeModels;
    if (settings.taskBreaking !== undefined) document.getElementById('taskBreaking').checked = settings.taskBreaking;
    if (settings.crewExecution !== undefined) document.getElementById('crewExecution').checked = settings.crewExecution;
    if (settings.changeTracking !== undefined) document.getElementById('changeTracking').checked = settings.changeTracking;
    if (settings.showTodoList !== undefined) document.getElementById('showTodoList').checked = settings.showTodoList;
    if (settings.showActiveAgent !== undefined) document.getElementById('showActiveAgent').checked = settings.showActiveAgent;
    if (settings.projectIndexing !== undefined) document.getElementById('projectIndexing').checked = settings.projectIndexing;
    if (settings.dependencyAnalysis !== undefined) document.getElementById('dependencyAnalysis').checked = settings.dependencyAnalysis;
    if (settings.autoOptimization !== undefined) document.getElementById('autoOptimization').checked = settings.autoOptimization;
    if (settings.predictiveAnalysis !== undefined) document.getElementById('predictiveAnalysis').checked = settings.predictiveAnalysis;
    if (settings.securityScan !== undefined) document.getElementById('securityScan').checked = settings.securityScan;
    if (settings.githubToken) document.getElementById('githubToken').value = settings.githubToken;
}

// Save settings to localStorage
function saveSettings() {
    const settings = {
        smartRouting: document.getElementById('smartRouting').checked,
        preferFreeModels: document.getElementById('preferFreeModels').checked,
        taskBreaking: document.getElementById('taskBreaking').checked,
        crewExecution: document.getElementById('crewExecution').checked,
        changeTracking: document.getElementById('changeTracking').checked,
        showTodoList: document.getElementById('showTodoList').checked,
        showActiveAgent: document.getElementById('showActiveAgent').checked,
        projectIndexing: document.getElementById('projectIndexing').checked,
        dependencyAnalysis: document.getElementById('dependencyAnalysis').checked
    };
    localStorage.setItem('antigravitySettings', JSON.stringify(settings));
}

// Toggle settings panel
function toggleSettings() {
    settingsPanel.classList.toggle('open');
}

// Toggle DevTools
function toggleDevTools() {
    vscode.postMessage({ type: 'toggleDevTools' });
}

// Toggle raw code panel
function toggleRawCode() {
    rawCodePanel.classList.toggle('open');
    if (rawCodePanel.classList.contains('open')) {
        // Load console logs
        loadConsoleLogs();
    }
}

// Load console logs
function loadConsoleLogs() {
    vscode.postMessage({ type: 'getConsoleLogs' });
}

// Show only errors
function showErrors() {
    vscode.postMessage({ type: 'getErrorsOnly' });
}

// Show only debug logs
function showDebug() {
    vscode.postMessage({ type: 'getDebugLogs' });
}

// Make stacktraces clickable
function makeStacktraceClickable(log) {
    // Match file paths with line numbers like /path/to/file.js:123:45
    return log.replace(/([a-zA-Z]:\\[^:]+|\/[^:]+):(\d+):(\d+)/g, (match, filePath, line, column) => {
        return `[FILE:${filePath}:${line}:${column}]`;
    });
}

// Handle clickable stacktrace
rawCodeTextarea.addEventListener('click', function(e) {
    const text = this.value.substring(this.selectionStart, this.selectionEnd);
    const match = text.match(/\[FILE:([^\]]+)\]/);
    if (match) {
        const parts = match[1].split(':');
        const filePath = parts.slice(0, -2).join(':');
        const line = parseInt(parts[parts.length - 2]);
        const column = parseInt(parts[parts.length - 1]);
        vscode.postMessage({
            type: 'openFile',
            path: filePath,
            line: line,
            column: column
        });
    }
});

// Format log entries for display
function formatLogEntries(entries) {
    if (!entries || entries.length === 0) return '';
    
    return entries.map(entry => {
        const timestamp = new Date(entry.timestamp).toLocaleTimeString();
        const level = entry.level.toUpperCase().padEnd(6);
        const message = entry.message;
        let details = '';
        
        if (entry.details) {
            details = '\n' + JSON.stringify(entry.details, null, 2);
        }
        
        return `[${timestamp}] [${level}] ${message}${details}`;
    }).join('\n\n');
}

// Add event listeners for settings toggles
document.querySelectorAll('.toggle-switch input').forEach(toggle => {
    toggle.addEventListener('change', saveSettings);
});

// Load settings on page load
loadSettings();

// Console log capture - Internal webview console (like F12 in browser)
let consoleLogs = [];
let debugLogs = [];

// Override console methods to capture logs with DEBUG tag
const originalConsoleLog = console.log;
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;
const originalConsoleInfo = console.info;
const originalConsoleDebug = console.debug;

console.log = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [LOG] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    consoleLogs.push(logEntry);
    debugLogs.push(logEntry);
    originalConsoleLog.apply(console, args);
};

console.error = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [ERROR] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    consoleLogs.push(logEntry);
    debugLogs.push(logEntry);
    originalConsoleError.apply(console, args);
};

console.warn = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [WARN] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    consoleLogs.push(logEntry);
    debugLogs.push(logEntry);
    originalConsoleWarn.apply(console, args);
};

console.info = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [INFO] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    consoleLogs.push(logEntry);
    debugLogs.push(logEntry);
    originalConsoleInfo.apply(console, args);
};

console.debug = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [DEBUG] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    consoleLogs.push(logEntry);
    debugLogs.push(logEntry);
    originalConsoleDebug.apply(console, args);
};

// Custom debug function following GitHub guidelines
function debug(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [DEBUG] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    consoleLogs.push(logEntry);
    debugLogs.push(logEntry);
    originalConsoleDebug.apply(console, args);
}

// Provider-specific models
const providerModels = {
    auto: ['⚡ Auto (Selezione Intelligente)'],
    openrouter: [
        '⚡ Auto (Intelligente)',
        '🧠 deepseek/deepseek-r1:free',
        '🦙 meta-llama/llama-3.3-70b-instruct:free',
        '⚡ qwen/qwen-2.5-72b-instruct:free',
        '🌟 mistralai/mistral-7b-instruct:free',
        '🔥 meta-llama/llama-3.1-8b-instruct:free'
    ],
    google: [
        '⚡ Auto (Intelligente)',
        '🧠 gemini-1.5-flash',
        '🦙 gemini-1.5-pro',
        '⚡ gemini-1.0-pro'
    ],
    groq: [
        '⚡ Auto (Intelligente)',
        '⚡ llama-3.3-70b-versatile',
        '🦙 llama-3.1-8b-instant',
        '🧠 mixtral-8x7b-32768'
    ],
    huggingface: [
        '⚡ Auto (Intelligente)',
        '🧠 meta-llama/Llama-3.3-70B-Instruct',
        '🦙 meta-llama/Llama-3.1-8B-Instruct',
        '⚡ mistralai/Mistral-7B-Instruct-v0.3'
    ],
    cloudflare: [
        '⚡ Auto (Intelligente)',
        '🧠 @cf/meta/llama-3.3-70b-instruct',
        '🦙 @cf/meta/llama-3.1-8b-instruct',
        '⚡ @cf/mistral/mistral-7b-instruct-v0.2'
    ]
};

// Update model options based on provider selection
function updateModelOptions() {
    const provider = providerSelect.value;
    const modelSelect = document.getElementById('modelSelect');
    
    // Clear current options
    modelSelect.innerHTML = '';
    
    // Add models for selected provider
    const models = providerModels[provider] || providerModels['auto'];
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
    });
}

// Initialize model options
updateModelOptions();

// Update models when provider changes
providerSelect.addEventListener('change', () => {
    const provider = providerSelect.value;
    const models = providerModels[provider] || providerModels.auto;
    
    modelSelect.innerHTML = '';
    models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.includes('Auto') ? 'auto' : model.split(' ')[1] || model;
        option.textContent = model;
        modelSelect.appendChild(option);
    });

    if (provider === 'auto') {
        modelIndicator.classList.add('active');
        modelIndicatorText.textContent = 'Modello: Auto (Selezione Intelligente)';
    } else {
        modelIndicator.classList.remove('active');
    }
});

// Update token usage
function updateTokenUsage(usedTokens) {
    tokenCount = usedTokens;
    const percentage = Math.min((tokenCount / maxTokens) * 100, 100);
    tokenUsageFill.style.width = percentage + '%';
    tokenUsageCount.textContent = `${tokenCount} / ${maxTokens}`;
    
    // Change color based on usage
    if (percentage > 80) {
        tokenUsageFill.style.background = 'linear-gradient(90deg, #ff6b6b 0%, #ee5a5a 100%)';
    } else if (percentage > 50) {
        tokenUsageFill.style.background = 'linear-gradient(90deg, #feca57 0%, #ff9f43 100%)';
    } else {
        tokenUsageFill.style.background = 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)';
    }
}

// Update model indicator with selected model
function updateModelIndicator(modelName) {
    if (providerSelect.value === 'auto') {
        modelIndicator.classList.add('active');
        modelIndicatorText.textContent = `Modello: ${modelName}`;
    }
}

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && input.value.trim() !== '') {
        e.preventDefault();
        sendMessage();
    }
});

function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    // Rimuovi welcome message se presente
    const welcome = chat.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Aggiungi messaggio utente
    addMessage(text, 'user');
    conversationHistory.push({ role: 'user', content: text });

    // Reset input
    input.value = '';
    input.style.height = '80px';

    // Mostra stato
    showStatus('🔍 Analisi del contesto in corso...');
    sendBtn.disabled = true;

    // Invia a extension con nuovi parametri
    vscode.postMessage({
        type: 'sendMessage',
        value: text,
        mode: modeSelect.value,
        provider: providerSelect.value,
        model: modelSelect.value,
        history: conversationHistory
    });
}

function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = type === 'user' ? '👤' : '🤖';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = formatMessage(content);
    
    messageContent.appendChild(bubble);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    
    chat.appendChild(messageDiv);
    chat.scrollTop = chat.scrollHeight;
}

function formatMessage(text) {
    // Remove code blocks completely - keep only clean text
    let formatted = text
        .replace(/```[\s\S]*?```/g, '') // Remove code blocks
        .replace(/`[^`]+`/g, '') // Remove inline code
        .replace(/\*\*([^*]+)\*\*/g, '$1') // Remove bold formatting but keep text
        .replace(/\*([^*]+)\*/g, '$1') // Remove italic formatting but keep text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

function highlightSyntax(code, language) {
    // Basic syntax highlighting
    let highlighted = code;
    
    // Comments
    highlighted = highlighted.replace(/(\/\/.*$)/gm, '<span class="comment">$1</span>');
    highlighted = highlighted.replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="comment">$1</span>');
    highlighted = highlighted.replace(/(#.*$)/gm, '<span class="comment">$1</span>');
    
    // Strings
    highlighted = highlighted.replace(/(".*?"|'.*?'|`.*?`)/g, '<span class="string">$1</span>');
    
    // Keywords (basic)
    const keywords = ['function', 'const', 'let', 'var', 'if', 'else', 'for', 'while', 'return', 'class', 'import', 'export', 'from', 'async', 'await', 'try', 'catch', 'throw'];
    keywords.forEach(kw => {
        const regex = new RegExp(`\\b(${kw})\\b`, 'g');
        highlighted = highlighted.replace(regex, '<span class="keyword">$1</span>');
    });
    
    // Numbers
    highlighted = highlighted.replace(/\b(\d+)\b/g, '<span class="number">$1</span>');
    
    // Functions
    highlighted = highlighted.replace(/\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/g, '<span class="function">$1</span>(');
    
    return highlighted;
}

function copyCode(button) {
    const codeBlock = button.closest('.code-block').querySelector('pre');
    const code = codeBlock.textContent;
    navigator.clipboard.writeText(code).then(() => {
        button.textContent = '✓ Copied!';
        setTimeout(() => {
            button.textContent = '📋 Copy';
        }, 2000);
    });
}

function showStatus(text) {
    statusBar.classList.add('active');
    statusText.textContent = text;
}

function hideStatus() {
    statusBar.classList.remove('active');
}

function clearChat() {
    chat.innerHTML = '';
    conversationHistory = [];
    tokenCount = 0;
    updateTokenUsage(0);
}

function showSettings() {
    vscode.postMessage({ type: 'openSettings' });
}

// Import repository from GitHub
function importFromGitHub() {
    const githubToken = document.getElementById('githubToken').value;
    if (!githubToken) {
        showStatus('⚠️ Inserisci un GitHub Token prima di importare');
        setTimeout(hideStatus, 3000);
        return;
    }
    
    showStatus('🔗 Connessione a GitHub in corso...');
    vscode.postMessage({
        type: 'importFromGitHub',
        githubToken: githubToken
    });
}

// Auto-resize textarea
input.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

// Listen for messages from extension
window.addEventListener('message', event => {
    const data = event.data;
    
    if (data.type === 'updateStatus') {
        showStatus(data.value);
    }
    
    if (data.type === 'addResponse') {
        hideStatus();
        addMessage(data.value, 'ai');
        conversationHistory.push({ role: 'assistant', content: data.value });
    }
    
    if (data.type === 'consoleLogs') {
        rawCodePanel.classList.add('open');
        rawCodeTextarea.value = formatLogEntries(data.entries) || 'Nessun log disponibile nella console interna';
    }
    
    if (data.type === 'errorLogs') {
        rawCodePanel.classList.add('open');
        rawCodeTextarea.value = formatLogEntries(data.entries) || 'Nessun errore disponibile nella console interna';
    }
    
    if (data.type === 'debugLogs') {
        rawCodePanel.classList.add('open');
        rawCodeTextarea.value = formatLogEntries(data.entries) || 'Nessun log debug disponibile nella console interna';
    }
    
    if (data.type === 'addErrorToRawCode') {
        rawCodePanel.classList.add('open');
        const currentContent = rawCodeTextarea.value || '';
        rawCodeTextarea.value = currentContent + '\n\n' + data.value;
    }

    if (data.rawCode) {
        rawCodeTextarea.value = data.rawCode;
    } else if (data.value) {
        rawCodeTextarea.value = data.value;
    }
    
    // Update token usage if provided
    if (data.tokens) {
        updateTokenUsage(data.tokens);
    }
    
    // Update model indicator if in auto mode
    if (data.model && providerSelect.value === 'auto') {
        updateModelIndicator(data.model);
    }
    
    sendBtn.disabled = false;
    
    if (data.type === 'error') {
        hideStatus();
        showStatus('❌ ' + data.value);
        setTimeout(hideStatus, 3000);
        sendBtn.disabled = false;
        retryBtn.classList.add('active');
    }

    if (data.type === 'toggleDevTools') {
        // DevTools toggled by extension
    }

    if (data.type === 'githubImportSuccess') {
        hideStatus();
        showStatus('✅ Repository importato con successo!');
        setTimeout(hideStatus, 3000);
    }

    if (data.type === 'githubImportError') {
        hideStatus();
        showStatus('❌ Errore importazione: ' + data.value);
        setTimeout(hideStatus, 5000);
    }

    if (data.type === 'consoleLogs') {
        rawCodeTextarea.value = data.value;
    }

    if (data.type === 'addErrorToRawCode') {
        const timestamp = new Date().toISOString();
        const errorEntry = `[${timestamp}] [DEBUG] ORCHESTRATOR ERROR: ${data.value}`;
        debugLogs.push(errorEntry);
        
        // Auto-open raw code panel on error
        if (!rawCodePanel.classList.contains('open')) {
            rawCodePanel.classList.add('open');
            loadConsoleLogs();
        }
    }
});
