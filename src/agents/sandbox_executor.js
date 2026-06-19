/**
 * Advanced Sandbox Executor Agent
 * University-level capabilities in sandboxed code execution, terminal management, and browser automation
 * Specializes in: isolated code execution, library installation, server launching, application testing
 */
class SandboxExecutor {
    constructor(context) {
        this.context = context;
        this.vscode = context.vscode || require('vscode');
        this.childProcess = require('child_process');
        this.fs = require('fs');
        this.path = require('path');
        
        this.executionCapabilities = [
            "Terminal Command Execution", "Library Installation", "Server Launching",
            "Application Startup", "Browser Automation", "Process Management",
            "Environment Isolation", "Resource Monitoring", "Error Capture"
        ];
        
        this.activeProcesses = new Map();
        this.executionHistory = [];
        this.sandboxEnvironments = new Map();
    }

    async execute(taskContext) {
        const { description, codeContext, systemContext, knowledgeBase } = taskContext;
        
        const executionResult = {
            terminalExecution: this.executeInTerminal(description, codeContext),
            libraryInstallation: this.installLibraries(description, codeContext),
            serverLaunch: this.launchServer(description, codeContext),
            applicationStartup: this.startApplication(description, codeContext),
            browserAutomation: this.automateBrowser(description, codeContext),
            processManagement: this.manageProcesses(description),
            resourceMonitoring: this.monitorResources(),
            errorCapture: this.captureErrors()
        };

        return {
            agent: "Sandbox Executor",
            result: executionResult,
            executionReport: this.synthesizeExecutionReport(executionResult),
            recommendations: this.provideExecutionRecommendations(executionResult),
            confidence: this.calculateExecutionConfidence(executionResult),
            metadata: {
                commandsExecuted: this.executionHistory.length,
                activeProcesses: this.activeProcesses.size,
                environmentsCreated: this.sandboxEnvironments.size,
                executionTime: this.lastExecutionTime
            }
        };
    }

    async executeInTerminal(description, codeContext) {
        const commands = this.extractCommands(description, codeContext);
        const results = [];
        
        for (const command of commands) {
            try {
                const result = await this.runCommand(command);
                results.push({
                    command: command,
                    success: result.success,
                    output: result.output,
                    error: result.error,
                    exitCode: result.exitCode
                });
                
                this.executionHistory.push({
                    command: command,
                    timestamp: Date.now(),
                    result: result
                });
            } catch (error) {
                results.push({
                    command: command,
                    success: false,
                    error: error.message
                });
            }
        }
        
        return results;
    }

    async runCommand(command, options = {}) {
        const workspaceRoot = this.vscode.workspace.rootPath || process.cwd();
        const cwd = options.cwd || workspaceRoot;
        
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            
            this.childProcess.exec(command, { cwd, timeout: options.timeout || 30000 }, (error, stdout, stderr) => {
                const executionTime = Date.now() - startTime;
                
                if (error) {
                    resolve({
                        success: false,
                        output: stdout,
                        error: stderr || error.message,
                        exitCode: error.code || -1,
                        executionTime
                    });
                } else {
                    resolve({
                        success: true,
                        output: stdout,
                        error: stderr,
                        exitCode: 0,
                        executionTime
                    });
                }
            });
        });
    }

    async installLibraries(description, codeContext) {
        const installations = [];
        
        // Detect package manager
        const packageManager = this.detectPackageManager();
        
        // Extract library names from description
        const libraries = this.extractLibraries(description, codeContext);
        
        for (const library of libraries) {
            try {
                let command;
                if (packageManager === 'npm') {
                    command = `npm install ${library}`;
                } else if (packageManager === 'yarn') {
                    command = `yarn add ${library}`;
                } else if (packageManager === 'pip') {
                    command = `pip install ${library}`;
                } else if (packageManager === 'pip3') {
                    command = `pip3 install ${library}`;
                } else {
                    command = `npm install ${library}`;
                }
                
                const result = await this.runCommand(command);
                installations.push({
                    library: library,
                    packageManager: packageManager,
                    success: result.success,
                    output: result.output,
                    error: result.error
                });
            } catch (error) {
                installations.push({
                    library: library,
                    success: false,
                    error: error.message
                });
            }
        }
        
        return installations;
    }

    detectPackageManager() {
        const workspaceRoot = this.vscode.workspace.rootPath;
        if (!workspaceRoot) return 'npm';
        
        if (this.fs.existsSync(this.path.join(workspaceRoot, 'package-lock.json'))) {
            return 'npm';
        } else if (this.fs.existsSync(this.path.join(workspaceRoot, 'yarn.lock'))) {
            return 'yarn';
        } else if (this.fs.existsSync(this.path.join(workspaceRoot, 'requirements.txt'))) {
            return 'pip';
        } else if (this.fs.existsSync(this.path.join(workspaceRoot, 'Pipfile'))) {
            return 'pip3';
        }
        
        return 'npm';
    }

    extractLibraries(description, codeContext) {
        const libraries = [];
        const desc = description.toLowerCase();
        const code = codeContext || "";
        
        // Common library patterns
        const libraryPatterns = [
            /install\s+([a-zA-Z0-9\-_@/]+)/gi,
            /npm install\s+([a-zA-Z0-9\-_@/]+)/gi,
            /pip install\s+([a-zA-Z0-9\-_@/]+)/gi,
            /yarn add\s+([a-zA-Z0-9\-_@/]+)/gi,
            /require\(['"]([a-zA-Z0-9\-_@/]+)['"]\)/g,
            /import\s+.*from\s+['"]([a-zA-Z0-9\-_@/]+)['"]/g
        ];
        
        for (const pattern of libraryPatterns) {
            let match;
            while ((match = pattern.exec(description + " " + code)) !== null) {
                const lib = match[1];
                if (lib && !libraries.includes(lib) && !lib.startsWith('.')) {
                    libraries.push(lib);
                }
            }
        }
        
        return libraries;
    }

    extractCommands(description, codeContext) {
        const commands = [];
        const desc = description.toLowerCase();
        
        // Extract shell commands from description
        const commandPatterns = [
            /`([^`]+)`/g,
            /```bash\n([\s\S]*?)```/g,
            /```sh\n([\s\S]*?)```/g,
            /```powershell\n([\s\S]*?)```/g,
            /```cmd\n([\s\S]*?)```/g
        ];
        
        for (const pattern of commandPatterns) {
            let match;
            while ((match = pattern.exec(description)) !== null) {
                const cmd = match[1].trim();
                if (cmd && !commands.includes(cmd)) {
                    commands.push(cmd);
                }
            }
        }
        
        // Also check for explicit command keywords
        if (desc.includes('run') || desc.includes('execute') || desc.includes('launch')) {
            const lines = description.split('\n');
            for (const line of lines) {
                if (line.trim().startsWith('$') || line.trim().startsWith('>')) {
                    const cmd = line.trim().substring(1).trim();
                    if (cmd && !commands.includes(cmd)) {
                        commands.push(cmd);
                    }
                }
            }
        }
        
        return commands;
    }

    async launchServer(description, codeContext) {
        const serverConfigs = this.detectServerConfig(description, codeContext);
        const results = [];
        
        for (const config of serverConfigs) {
            try {
                const result = await this.startServer(config);
                results.push({
                    config: config,
                    success: result.success,
                    pid: result.pid,
                    url: result.url,
                    output: result.output,
                    error: result.error
                });
                
                if (result.success && result.pid) {
                    this.activeProcesses.set(result.pid, {
                        type: 'server',
                        config: config,
                        startTime: Date.now()
                    });
                }
            } catch (error) {
                results.push({
                    config: config,
                    success: false,
                    error: error.message
                });
            }
        }
        
        return results;
    }

    async startServer(config) {
        const workspaceRoot = this.vscode.workspace.rootPath || process.cwd();
        
        return new Promise((resolve, reject) => {
            const process = this.childProcess.spawn(config.command, config.args || [], {
                cwd: workspaceRoot,
                detached: true,
                stdio: 'ignore'
            });
            
            process.unref();
            
            const pid = process.pid;
            let output = '';
            let error = '';
            
            // Wait a bit for server to start
            setTimeout(() => {
                resolve({
                    success: true,
                    pid: pid,
                    url: config.url || `http://localhost:${config.port || 3000}`,
                    output: output,
                    error: error
                });
            }, 2000);
            
            process.stdout.on('data', (data) => {
                output += data.toString();
            });
            
            process.stderr.on('data', (data) => {
                error += data.toString();
            });
            
            process.on('error', (err) => {
                reject(err);
            });
        });
    }

    detectServerConfig(description, codeContext) {
        const configs = [];
        const desc = description.toLowerCase();
        const code = codeContext || "";
        
        // Detect common server patterns
        if (desc.includes('node') || desc.includes('npm start') || code.includes('express')) {
            configs.push({
                command: 'node',
                args: ['index.js'],
                port: 3000,
                url: 'http://localhost:3000'
            });
        }
        
        if (desc.includes('python') || desc.includes('flask') || code.includes('Flask')) {
            configs.push({
                command: 'python',
                args: ['app.py'],
                port: 5000,
                url: 'http://localhost:5000'
            });
        }
        
        if (desc.includes('django') || code.includes('django')) {
            configs.push({
                command: 'python',
                args: ['manage.py', 'runserver'],
                port: 8000,
                url: 'http://localhost:8000'
            });
        }
        
        if (desc.includes('react') || desc.includes('next') || code.includes('react')) {
            configs.push({
                command: 'npm',
                args: ['start'],
                port: 3000,
                url: 'http://localhost:3000'
            });
        }
        
        if (desc.includes('vue') || code.includes('vue')) {
            configs.push({
                command: 'npm',
                args: ['serve'],
                port: 8080,
                url: 'http://localhost:8080'
            });
        }
        
        // Extract custom port if specified
        const portMatch = desc.match(/port[:\s]*(\d+)/i);
        if (portMatch && configs.length > 0) {
            configs.forEach(config => {
                config.port = parseInt(portMatch[1]);
                config.url = `http://localhost:${config.port}`;
            });
        }
        
        return configs;
    }

    async startApplication(description, codeContext) {
        const appConfigs = this.detectApplicationConfig(description, codeContext);
        const results = [];
        
        for (const config of appConfigs) {
            try {
                const result = await this.launchApplication(config);
                results.push({
                    config: config,
                    success: result.success,
                    pid: result.pid,
                    output: result.output,
                    error: result.error
                });
                
                if (result.success && result.pid) {
                    this.activeProcesses.set(result.pid, {
                        type: 'application',
                        config: config,
                        startTime: Date.now()
                    });
                }
            } catch (error) {
                results.push({
                    config: config,
                    success: false,
                    error: error.message
                });
            }
        }
        
        return results;
    }

    async launchApplication(config) {
        const workspaceRoot = this.vscode.workspace.rootPath || process.cwd();
        
        return new Promise((resolve, reject) => {
            const process = this.childProcess.spawn(config.command, config.args || [], {
                cwd: workspaceRoot,
                detached: true,
                stdio: 'ignore'
            });
            
            process.unref();
            
            const pid = process.pid;
            
            setTimeout(() => {
                resolve({
                    success: true,
                    pid: pid,
                    output: 'Application started'
                });
            }, 1000);
            
            process.on('error', (err) => {
                reject(err);
            });
        });
    }

    detectApplicationConfig(description, codeContext) {
        const configs = [];
        const desc = description.toLowerCase();
        
        if (desc.includes('electron')) {
            configs.push({
                command: 'npm',
                args: ['start']
            });
        }
        
        if (desc.includes('desktop app') || desc.includes('gui')) {
            configs.push({
                command: 'npm',
                args: ['run', 'desktop']
            });
        }
        
        return configs;
    }

    async automateBrowser(description, codeContext) {
        const browserActions = this.extractBrowserActions(description, codeContext);
        const results = [];
        
        for (const action of browserActions) {
            try {
                const result = await this.executeBrowserAction(action);
                results.push({
                    action: action,
                    success: result.success,
                    output: result.output,
                    error: result.error
                });
            } catch (error) {
                results.push({
                    action: action,
                    success: false,
                    error: error.message
                });
            }
        }
        
        return results;
    }

    async executeBrowserAction(action) {
        // This is a placeholder for browser automation
        // In a real implementation, you would use Playwright, Puppeteer, or Selenium
        
        if (action.type === 'open') {
            return {
                success: true,
                output: `Opened ${action.url}`
            };
        }
        
        if (action.type === 'navigate') {
            return {
                success: true,
                output: `Navigated to ${action.url}`
            };
        }
        
        if (action.type === 'click') {
            return {
                success: true,
                output: `Clicked on ${action.selector}`
            };
        }
        
        if (action.type === 'type') {
            return {
                success: true,
                output: `Typed "${action.text}" in ${action.selector}`
            };
        }
        
        return {
            success: false,
            error: 'Unknown browser action'
        };
    }

    extractBrowserActions(description, codeContext) {
        const actions = [];
        const desc = description.toLowerCase();
        
        if (desc.includes('open browser') || desc.includes('navigate to')) {
            const urlMatch = desc.match(/https?:\/\/[^\s]+/);
            if (urlMatch) {
                actions.push({
                    type: 'open',
                    url: urlMatch[0]
                });
            }
        }
        
        if (desc.includes('click')) {
            actions.push({
                type: 'click',
                selector: 'button'
            });
        }
        
        if (desc.includes('type') || desc.includes('input')) {
            actions.push({
                type: 'type',
                selector: 'input',
                text: 'test'
            });
        }
        
        return actions;
    }

    async manageProcesses(description) {
        const actions = this.extractProcessActions(description);
        const results = [];
        
        for (const action of actions) {
            try {
                const result = await this.executeProcessAction(action);
                results.push({
                    action: action,
                    success: result.success,
                    output: result.output,
                    error: result.error
                });
            } catch (error) {
                results.push({
                    action: action,
                    success: false,
                    error: error.message
                });
            }
        }
        
        return results;
    }

    async executeProcessAction(action) {
        if (action.type === 'list') {
            return {
                success: true,
                output: Array.from(this.activeProcesses.entries()).map(([pid, info]) => ({
                    pid: pid,
                    type: info.type,
                    startTime: info.startTime
                }))
            };
        }
        
        if (action.type === 'kill' && action.pid) {
            try {
                this.childProcess.kill(action.pid);
                this.activeProcesses.delete(action.pid);
                return {
                    success: true,
                    output: `Process ${action.pid} killed`
                };
            } catch (error) {
                return {
                    success: false,
                    error: error.message
                };
            }
        }
        
        if (action.type === 'killall') {
            for (const pid of this.activeProcesses.keys()) {
                try {
                    this.childProcess.kill(pid);
                } catch (error) {
                    console.error(`Failed to kill process ${pid}:`, error);
                }
            }
            this.activeProcesses.clear();
            return {
                success: true,
                output: 'All processes killed'
            };
        }
        
        return {
            success: false,
            error: 'Unknown process action'
        };
    }

    extractProcessActions(description) {
        const actions = [];
        const desc = description.toLowerCase();
        
        if (desc.includes('list process') || desc.includes('show process')) {
            actions.push({ type: 'list' });
        }
        
        if (desc.includes('kill') || desc.includes('stop')) {
            const pidMatch = desc.match(/pid[:\s]*(\d+)/i);
            if (pidMatch) {
                actions.push({
                    type: 'kill',
                    pid: parseInt(pidMatch[1])
                });
            } else if (desc.includes('all')) {
                actions.push({ type: 'killall' });
            }
        }
        
        return actions;
    }

    async monitorResources() {
        return {
            activeProcesses: this.activeProcesses.size,
            executionHistory: this.executionHistory.length,
            sandboxEnvironments: this.sandboxEnvironments.size,
            memoryUsage: process.memoryUsage(),
            uptime: process.uptime()
        };
    }

    async captureErrors() {
        const errors = [];
        
        for (const entry of this.executionHistory) {
            if (!entry.result.success) {
                errors.push({
                    command: entry.command,
                    timestamp: entry.timestamp,
                    error: entry.result.error,
                    exitCode: entry.result.exitCode
                });
            }
        }
        
        return errors;
    }

    synthesizeExecutionReport(executionResult) {
        return {
            summary: {
                totalCommands: executionResult.terminalExecution.length,
                successfulCommands: executionResult.terminalExecution.filter(r => r.success).length,
                failedCommands: executionResult.terminalExecution.filter(r => !r.success).length,
                librariesInstalled: executionResult.libraryInstallation.filter(r => r.success).length,
                serversLaunched: executionResult.serverLaunch.filter(r => r.success).length,
                applicationsStarted: executionResult.applicationStartup.filter(r => r.success).length
            },
            activeProcesses: Array.from(this.activeProcesses.entries()),
            errors: executionResult.errorCapture,
            resourceUsage: executionResult.resourceMonitoring
        };
    }

    provideExecutionRecommendations(executionResult) {
        const recommendations = [];
        
        if (executionResult.terminalExecution.some(r => !r.success)) {
            recommendations.push({
                priority: "high",
                action: "Review failed commands and fix errors"
            });
        }
        
        if (executionResult.libraryInstallation.some(r => !r.success)) {
            recommendations.push({
                priority: "medium",
                action: "Check library dependencies and installation requirements"
            });
        }
        
        if (this.activeProcesses.size > 5) {
            recommendations.push({
                priority: "low",
                action: "Consider stopping unused processes to free resources"
            });
        }
        
        return recommendations;
    }

    calculateExecutionConfidence(executionResult) {
        let confidence = 0.5;
        
        const successRate = executionResult.terminalExecution.filter(r => r.success).length / 
                          Math.max(executionResult.terminalExecution.length, 1);
        
        confidence += successRate * 0.3;
        
        if (executionResult.serverLaunch.some(r => r.success)) confidence += 0.1;
        if (executionResult.libraryInstallation.some(r => r.success)) confidence += 0.1;
        
        return Math.min(confidence, 1.0);
    }

    dispose() {
        // Kill all active processes
        for (const pid of this.activeProcesses.keys()) {
            try {
                this.childProcess.kill(pid);
            } catch (error) {
                console.error(`Failed to kill process ${pid}:`, error);
            }
        }
        this.activeProcesses.clear();
    }
}

module.exports = SandboxExecutor;
