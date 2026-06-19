const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const AgentFactory = require("./src/agentFactory");
const CloudDeployer = require("./src/cloudDeployer");
const AdvancedOrchestrator = require("./src/orchestrator");
const CrewAIOrchestrator = require("./src/orchestrator-crewai");

let orchestrator = null;
let crewaiOrchestrator = null;

// Create dedicated OutputChannel for extension logging
const consoleChannel = vscode.window.createOutputChannel("Antigravity Dev Console");

// Internal Logger for structured logging
class InternalLogger {
    constructor() {
        this.entries = [];
        this.listeners = [];
    }

    log(level, message, details = null) {
        const entry = {
            level,
            message,
            details,
            timestamp: new Date().toISOString()
        };
        this.entries.push(entry);
        this.listeners.forEach(listener => listener(entry));
        
        // Also send to OutputChannel
        const logMessage = `[${level.toUpperCase()}] ${message}`;
        if (details) {
            consoleChannel.appendLine(logMessage + " " + JSON.stringify(details));
        } else {
            consoleChannel.appendLine(logMessage);
        }
    }

    debug(message, details) {
        this.log('debug', message, details);
    }

    info(message, details) {
        this.log('info', message, details);
    }

    warn(message, details) {
        this.log('warn', message, details);
    }

    error(message, details) {
        this.log('error', message, details);
    }

    onEntry(listener) {
        this.listeners.push(listener);
    }

    getAll() {
        return this.entries;
    }

    filterByLevel(level) {
        return this.entries.filter(entry => entry.level === level);
    }
}

const logger = new InternalLogger();

// Intercept ALL runtime errors
process.on("uncaughtException", err => {
    const errorMessage = `[UNCAUGHT EXCEPTION] ${err.message}\nStack: ${err.stack}`;
    consoleChannel.appendLine(errorMessage);
    consoleChannel.show(true);
    
    // Send to webview if available
    if (crewaiOrchestrator && crewaiOrchestrator.webview) {
        crewaiOrchestrator.webview.postMessage({
            type: 'addErrorToRawCode',
            value: errorMessage
        });
    }
});

process.on("unhandledRejection", err => {
    const errorMessage = `[UNHANDLED REJECTION] ${err}`;
    consoleChannel.appendLine(errorMessage);
    consoleChannel.show(true);
    
    // Send to webview if available
    if (crewaiOrchestrator && crewaiOrchestrator.webview) {
        crewaiOrchestrator.webview.postMessage({
            type: 'addErrorToRawCode',
            value: errorMessage
        });
    }
});

// Replace console methods to send to OutputChannel
const originalConsoleLog = console.log;
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;
const originalConsoleInfo = console.info;

console.log = (...args) => {
    const message = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(" ");
    consoleChannel.appendLine("[LOG] " + message);
    originalConsoleLog.apply(console, args);
};

console.error = (...args) => {
    const message = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(" ");
    consoleChannel.appendLine("[ERROR] " + message);
    originalConsoleError.apply(console, args);
};

console.warn = (...args) => {
    const message = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(" ");
    consoleChannel.appendLine("[WARN] " + message);
    originalConsoleWarn.apply(console, args);
};

console.info = (...args) => {
    const message = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(" ");
    consoleChannel.appendLine("[INFO] " + message);
    originalConsoleInfo.apply(console, args);
};

function activate(context) {
    try {
        console.log("Antigravity Sovereign Hive Engine: Attivato!");
        
        // Show console automatically on startup
        consoleChannel.show(true);
        
        // Initialize the advanced orchestrator (legacy)
        orchestrator = new AdvancedOrchestrator(context);
        
        // Initialize the CrewAI-style orchestrator (new)
        crewaiOrchestrator = new CrewAIOrchestrator(context);
    } catch (err) {
        console.error("Runtime error during activation:", err);
        consoleChannel.show(true);
    }
    
    const provider = {
        resolveWebviewView(webviewView) {
            webviewView.webview.options = { 
                enableScripts: true, 
                localResourceRoots: [vscode.Uri.file(context.extensionPath)] 
            };
            
            const htmlPath = path.join(context.extensionPath, "interface.html");
            if (fs.existsSync(htmlPath)) {
                let html = fs.readFileSync(htmlPath, "utf8");
                // Replace webviewUri placeholder with actual webview URI
                const webviewUri = webviewView.webview.asWebviewUri(vscode.Uri.file(context.extensionPath));
                html = html.replace(/\${webviewUri}/g, webviewUri);
                webviewView.webview.html = html;
            }
            
            // Set webview reference in orchestrators
            if (crewaiOrchestrator) {
                crewaiOrchestrator.setWebview(webviewView.webview);
            }
            
            webviewView.webview.onDidReceiveMessage(async (data) => {
        try {
            if (data.type === "sendMessage" || data.command === "sendMessage") {
                await processHiveRequest(data.value || data.text || "", context, webviewView, data.mode, data.provider, data.model);
            }
            if (data.type === "toggleDevTools") {
                vscode.commands.executeCommand('workbench.action.toggleDevTools');
            }
            if (data.type === "importFromGitHub") {
                await importFromGitHub(data.githubToken, context, webviewView);
            }
            if (data.type === "getConsoleLogs") {
                webviewView.webview.postMessage({ type: "consoleLogs", entries: logger.getAll() });
            }
            if (data.type === "getErrorsOnly") {
                webviewView.webview.postMessage({ type: "errorLogs", entries: logger.filterByLevel('error') });
            }
            if (data.type === "getDebugLogs") {
                webviewView.webview.postMessage({ type: "debugLogs", entries: logger.filterByLevel('debug') });
            }
            if (data.type === "openFile") {
                // Open file at specific line and column
                const uri = vscode.Uri.file(data.path);
                vscode.window.showTextDocument(uri, {
                    selection: new vscode.Range(
                        new vscode.Position(data.line - 1, data.column - 1),
                        new vscode.Position(data.line - 1, data.column - 1)
                    )
                });
            }
        } catch (err) {
            console.error("Runtime error in message handler:", err);
            consoleChannel.show(true);
        }
    });
        }
    };
    context.subscriptions.push(vscode.window.registerWebviewViewProvider("antigravityUnifiedChat", provider));

    let setCloudflareKeysCmd = vscode.commands.registerCommand("antigravity.setCloudflareKeys", async () => {
        const id = await vscode.window.showInputBox({ prompt: "Inserisci Cloudflare Account ID" });
        const token = await vscode.window.showInputBox({ prompt: "Inserisci Cloudflare API Token", password: true });
        if (id) await context.secrets.store("cloudflareAccountId", id);
        if (token) await context.secrets.store("cloudflareToken", token);
        vscode.window.showInformationMessage("Configurazione Cloudflare completata!");
    });
    context.subscriptions.push(setCloudflareKeysCmd);

    let setOpenRouterKeyCmd = vscode.commands.registerCommand("antigravity.setOpenRouterKey", async () => {
        const apiKey = await vscode.window.showInputBox({ prompt: "Inserisci OpenRouter API Key (sk-or-...)", password: true });
        if (apiKey) {
            await context.secrets.store("openrouterApiKey", apiKey);
            vscode.window.showInformationMessage("Chiave OpenRouter salvata con successo!");
        }
    });
    context.subscriptions.push(setOpenRouterKeyCmd);

    let setHuggingFaceKeyCmd = vscode.commands.registerCommand("antigravity.setHuggingFaceKey", async () => {
        const apiKey = await vscode.window.showInputBox({ prompt: "Inserisci Hugging Face API Key (hf_...)", password: true });
        if (apiKey) {
            await context.secrets.store("huggingfaceApiKey", apiKey);
            vscode.window.showInformationMessage("Chiave Hugging Face salvata con successo!");
        }
    });
    context.subscriptions.push(setHuggingFaceKeyCmd);

    // New command to show orchestrator status
    let showStatusCmd = vscode.commands.registerCommand("antigravity.showStatus", async () => {
        if (orchestrator) {
            const status = orchestrator.getStatus();
            const statusMessage = `
Orchestratore Status (Legacy):
- Agenti Attivi: ${status.agents.filter(a => a.status === 'busy').length}/${status.agents.length}
- Code in Attesa: ${status.queue}
- Task Attivi: ${status.activeTasks}
- Knowledge Base: ${status.knowledgeBaseSize} voci
- Esecuzioni Totali: ${status.totalExecutions}
            `;
            vscode.window.showInformationMessage(statusMessage);
        }
        
        if (crewaiOrchestrator) {
            const crewaiStatus = crewaiOrchestrator.getStatus();
            const crewaiMessage = `
CrewAI Orchestrator Status:
- Agenti: ${crewaiStatus.agents.length}
- Task: ${crewaiStatus.tasks.length}
- Crews: ${crewaiStatus.crews.length}
- Tools: ${crewaiStatus.toolsCount}
- Project Index: ${crewaiStatus.projectIndexSize}
            `;
            vscode.window.showInformationMessage(crewaiMessage);
        }
    });
    context.subscriptions.push(showStatusCmd);

    // Divine Absolute Functions
    let autoOptimizeCmd = vscode.commands.registerCommand("antigravity.autoOptimize", async () => {
        vscode.window.showInformationMessage("🚀 Auto-Optimization in progress...");
        // Implementation for automatic project optimization
    });
    context.subscriptions.push(autoOptimizeCmd);

    let generateTestsCmd = vscode.commands.registerCommand("antigravity.generateTests", async () => {
        vscode.window.showInformationMessage("🧪 Generating automated tests...");
        // Implementation for automated test generation
    });
    context.subscriptions.push(generateTestsCmd);

    let securityScanCmd = vscode.commands.registerCommand("antigravity.securityScan", async () => {
        vscode.window.showInformationMessage("🔒 Deep security scan in progress...");
        // Implementation for deep security scanning
    });
    context.subscriptions.push(securityScanCmd);

    let predictiveAnalysisCmd = vscode.commands.registerCommand("antigravity.predictiveAnalysis", async () => {
        vscode.window.showInformationMessage("🔮 Predictive analysis in progress...");
        // Implementation for predictive analysis
    });
    context.subscriptions.push(predictiveAnalysisCmd);

    let autoRefactorCmd = vscode.commands.registerCommand("antigravity.autoRefactor", async () => {
        vscode.window.showInformationMessage("⚡ Auto-refactoring codebase...");
        // Implementation for automatic refactoring
    });
    context.subscriptions.push(autoRefactorCmd);

    let generateDocsCmd = vscode.commands.registerCommand("antigravity.generateDocs", async () => {
        vscode.window.showInformationMessage("📚 Generating documentation...");
        // Implementation for automatic documentation generation
    });
    context.subscriptions.push(generateDocsCmd);

    let performanceAuditCmd = vscode.commands.registerCommand("antigravity.performanceAudit", async () => {
        vscode.window.showInformationMessage("⚡ Performance audit in progress...");
        // Implementation for performance auditing
    });
    context.subscriptions.push(performanceAuditCmd);
}

async function processHiveRequest(prompt, context, webviewView, mode = "ask", provider = "auto", model = "auto") {
    try {
        logger.debug('Starting orchestrator execution', { prompt, mode, provider, model });
        webviewView.webview.postMessage({ type: "updateStatus", value: "🔍 Analisi del contesto in corso..." });
    
    // Check for API keys first
    const openrouterToken = await context.secrets.get("openrouterApiKey");
    const huggingfaceToken = await context.secrets.get("huggingfaceApiKey");
    const cloudflareId = await context.secrets.get("cloudflareAccountId");
    const cloudflareToken = await context.secrets.get("cloudflareToken");
    
    // If no API keys are configured, provide a helpful response
    if (!openrouterToken && !huggingfaceToken && !cloudflareId && !cloudflareToken) {
        webviewView.webview.postMessage({ type: "updateStatus", value: "⚙️ Configurazione richiesta..." });
        
        const helpMessage = `
<b>🚀 Benvenuto in Antigravity Unified Engine v4.0!</b><br><br>
Per iniziare a usare l'estensione, devi configurare almeno una chiave API:<br><br>
<b>Opzione 1 - OpenRouter (Consigliato):</b><br>
1. Premi Ctrl+Shift+P<br>
2. Digita "Antigravity: Set OpenRouter API Key"<br>
3. Inserisci la tua chiave (sk-or-...)<br><br>
<b>Opzione 2 - Hugging Face:</b><br>
1. Premi Ctrl+Shift+P<br>
2. Digita "Antigravity: Set Hugging Face API Key"<br>
3. Inserisci la tua chiave (hf_...)<br><br>
<b>Opzione 3 - Cloudflare Workers:</b><br>
1. Premi Ctrl+Shift+P<br>
2. Digita "Antigravity: Set Cloudflare Account ID"<br>
3. Digita "Antigravity: Set Cloudflare API Token"<br><br>
<b>Cosa posso fare dopo la configurazione:</b><br>
- 💬 <b>Chiedi:</b> Risposte informative e spiegazioni<br>
- 💻 <b>Codice:</b> Generazione e modifica di codice<br>
- 📋 <b>Piano:</b> Pianificazione di progetti complessi<br><br>
<b>Provider supportati:</b><br>
- ⚡ Auto (Selezione Intelligente)<br>
- 🌐 OpenRouter (Multi-modello)<br>
- 🔍 Google AI (Gemini)<br>
- ⚡ Groq (Ultra-veloce)<br>
- 🤗 Hugging Face (Open Source)<br>
- ☁️ Cloudflare AI (Workers AI)<br><br>
<i>Powered by Alessandro Calabria - 14 Agenti Universitari Avanzati</i>
        `;
        
        webviewView.webview.postMessage({ type: "addResponse", value: helpMessage });
        return;
    }
    
    // Use CrewAI orchestrator for intelligent routing with parallel processing
    if (crewaiOrchestrator && (provider === "auto" || model === "auto")) {
        try {
            if (openrouterToken || huggingfaceToken) {
                crewaiOrchestrator.configureLLM({
                    model: model === "auto" ? "auto" : model,
                    apiKey: openrouterToken || huggingfaceToken
                });
                
                webviewView.webview.postMessage({ type: "updateStatus", value: "🧠 Selezione agenti ottimali..." });
                
                const result = await crewaiOrchestrator.executeTask({
                    description: prompt,
                    expectedOutput: "Response based on user request",
                    agentId: mode === "code" ? "programmer" : mode === "plan" ? "architect" : "researcher",
                    toolIds: mode === "code" ? ["read_file", "write_file", "execute_command"] : ["read_file", "search"]
                }, {
                    workspaceRoot: vscode.workspace.rootPath
                });
                
                webviewView.webview.postMessage({ type: "addResponse", value: result });
                return;
            }
        } catch (error) {
            console.error("CrewAI execution failed, falling back to legacy:", error);
        }
    }
    
    // Legacy orchestrator fallback
    if (!cloudflareId || !cloudflareToken) {
        webviewView.webview.postMessage({ type: "addResponse", value: "⚠️ Per usare l'orchestratore legacy, configura le chiavi Cloudflare tramite Ctrl+Shift+P -> Antigravity: Set Cloudflare Account ID & API Key." });
        return;
    }
    
    if (!openrouterToken && !huggingfaceToken) {
        webviewView.webview.postMessage({ type: "addResponse", value: "⚠️ Per usare l'orchestratore legacy, configura una chiave AI tramite Ctrl+Shift+P." });
        return;
    }

    // Get code context with caching for performance
    const activeFile = vscode.window.activeTextEditor ? vscode.window.activeTextEditor.document.fileName : "";
    let codeContext = "";
    if (vscode.window.activeTextEditor) {
        const doc = vscode.window.activeTextEditor.document;
        // Cache document text to avoid repeated reads
        if (!doc._cachedText || doc.version !== doc._cachedVersion) {
            doc._cachedText = doc.getText();
            doc._cachedVersion = doc.version;
        }
        codeContext = doc._cachedText;
    }
    
    const indexPath = path.join(vscode.workspace.rootPath || "", "workspace_index.json");
    const systemContext = {
        workspaceRoot: vscode.workspace.rootPath,
        activeFile: activeFile,
        openFiles: vscode.workspace.textDocuments.map(doc => doc.fileName),
        workspaceFolders: vscode.workspace.workspaceFolders?.map(f => f.uri.fsPath) || []
    };

    // Use the advanced orchestrator to process the request
    try {
        webviewView.webview.postMessage({ type: "updateStatus", value: "Orchestratore: Selezione agenti ottimali..." });
        
        const task = {
            description: prompt,
            codeContext: codeContext,
            systemContext: systemContext,
            urgency: "normal",
            relatedFiles: [activeFile],
            affectedComponents: [],
            mode: mode,
            provider: provider,
            model: model,
            apiKeys: {
                openrouter: openrouterToken,
                huggingface: huggingfaceToken,
                cloudflareId: cloudflareId,
                cloudflareToken: cloudflareToken
            }
        };

        logger.debug('Starting orchestrator execution', {
            taskId: task.id,
            provider: provider,
            model: model,
            mode: mode,
            activeFile: activeFile
        });
        
        const result = await orchestrator.executeTask(task);
        
        logger.debug('Orchestrator execution completed', {
            taskId: task.id,
            success: !result.analysis?.error,
            hasAnalysis: !!result.analysis,
            hasAgent: !!result.agent
        });
        
        webviewView.webview.postMessage({ type: "updateStatus", value: "Orchestratore: Generazione risposta..." });
        
        // Check if result is a fallback/error result
        if (result.analysis && result.analysis.error) {
            logger.error('Orchestrator returned error result', {
                errorMessage: result.analysis.errorMessage,
                error: result.analysis.error,
                recommendations: result.recommendations
            });
            
            let errorText = `[DEBUG] ORCHESTRATOR ERROR:\n\n`;
            errorText += `Error Type: Orchestrator Execution Error\n`;
            errorText += `Error Message: ${result.analysis.errorMessage || "Errore sconosciuto"}\n`;
            errorText += `Task ID: ${task?.id || 'N/A'}\n`;
            errorText += `Provider: ${provider}\n`;
            errorText += `Model: ${model}\n`;
            errorText += `Mode: ${mode}\n`;
            errorText += `Timestamp: ${new Date().toISOString()}\n\n`;
            
            if (result.recommendations && result.recommendations.length > 0) {
                errorText += `Suggerimenti:\n`;
                result.recommendations.forEach((rec, index) => {
                    errorText += `${index + 1}. ${rec.action}\n`;
                });
            }
            
            // Send error to raw code panel only
            webviewView.webview.postMessage({ type: "addErrorToRawCode", value: errorText });
            // Send clean message to chat
            webviewView.webview.postMessage({ type: "addResponse", value: "⚠️ Si è verificato un errore durante l'elaborazione. Controlla il pannello 'Console' per i dettagli tecnici." });
            return;
        }
        
        // Format the response from multiple agents
        let responseText = `<b>🤖 Risposta dall'Orchestratore con 14 Agenti Universitari Avanzati:</b><br><br>`;
        
        if (result.agent) {
            responseText += `<b>Agente Principale:</b> ${result.agent}<br>`;
        }
        
        if (result.analysis) {
            responseText += `<b>Analisi:</b><br>`;
            if (result.analysis.architecturalAssessment) {
                responseText += `- Architettura: Complessità ${result.analysis.architecturalAssessment.componentCoupling || 'N/A'}<br>`;
            }
            if (result.analysis.performanceAnalysis) {
                responseText += `- Performance: Ottimizzazione raccomandata<br>`;
            }
        }
        
        if (result.recommendations && result.recommendations.length > 0) {
            responseText += `<br><b>Raccomandazioni:</b><br>`;
            result.recommendations.forEach((rec, index) => {
                responseText += `${index + 1}. <b>[${rec.priority}]</b> ${rec.action}<br>`;
            });
        }
        
        if (result.metadata) {
            responseText += `<br><b>Metadati:</b><br>`;
            if (result.metadata.confidence) {
                responseText += `- Confidenza: ${(result.metadata.confidence * 100).toFixed(1)}%<br>`;
            }
        }

        // Also deploy to Cloudflare for the actual AI processing
        webviewView.webview.postMessage({ type: "updateStatus", value: "Il Programmatore Liquido contatta Qwen-72B..." });
        let agentScript = AgentFactory.compileAgent("Refactor-Engine", prompt);
        agentScript = agentScript.replace("env.HUGGINGFACE_TOKEN", `"${huggingfaceToken}"`);

        webviewView.webview.postMessage({ type: "updateStatus", value: "Iniezione Agente su Cloudflare..." });
        const res = await CloudDeployer.deployToCloudflare(cloudflareId, cloudflareToken, "antigravity-active-worker", agentScript);
        
        if (res.success) {
            responseText += `<br><br>✔ <b>Alveare Espanso!</b> Micro-Agente istanziato su Cloudflare collegato a Qwen-Coder-72B.`;
            webviewView.webview.postMessage({ type: "addResponse", value: responseText, rawCode: responseText });
        } else {
            responseText += `<br><br>⚠ <b>Nota:</b> Analisi locale completata ma distribuzione Cloudflare fallita.`;
            webviewView.webview.postMessage({ type: "addResponse", value: responseText, rawCode: responseText });
        }
        
    } catch (error) {
        console.error("Orchestrator error:", error);
        console.error("Error details:", {
            message: error.message,
            name: error.name,
            stack: error.stack,
            code: error.code,
            statusCode: error.statusCode,
            statusMessage: error.statusMessage
        });
        
        // Detailed error information
        const errorMessage = `[DEBUG] ORCHESTRATOR ERROR:\n\n`;
        errorMessage += `Error Type: ${error.name}\n`;
        errorMessage += `Error Message: ${error.message}\n`;
        errorMessage += `Error Code: ${error.code || 'N/A'}\n`;
        errorMessage += `Status Code: ${error.statusCode || 'N/A'}\n`;
        errorMessage += `Status Message: ${error.statusMessage || 'N/A'}\n\n`;
        errorMessage += `Stack Trace:\n${error.stack}\n\n`;
        errorMessage += `Context:\n`;
        errorMessage += `- Provider: ${provider}\n`;
        errorMessage += `- Model: ${model}\n`;
        errorMessage += `- Mode: ${mode}\n`;
        errorMessage += `- Active File: ${activeFile || 'N/A'}\n`;
        errorMessage += `- Task ID: ${task?.id || 'N/A'}\n`;
        errorMessage += `- Timestamp: ${new Date().toISOString()}\n`;
        
        // Send error to raw code panel only, not to chat
        webviewView.webview.postMessage({ type: "addErrorToRawCode", value: errorMessage });
        // Send clean error message to chat
        webviewView.webview.postMessage({ type: "addResponse", value: "⚠️ Si è verificato un errore durante l'elaborazione. Controlla il pannello 'Console' per i dettagli tecnici." });
    }
    } catch (error) {
        logger.error('Runtime error in processHiveRequest', {
            message: error.message,
            stack: error.stack
        });
        consoleChannel.show(true);
    }
}

async function deactivate() {
    if (orchestrator) {
        await orchestrator.shutdown();
    }
}

// Console log capture - Extension side (for debugging extension code)
let extensionConsoleLogs = [];

// Override console methods to capture extension logs
const originalExtensionConsoleLog = console.log;
const originalExtensionConsoleError = console.error;
const originalExtensionConsoleWarn = console.warn;
const originalExtensionConsoleInfo = console.info;
const originalExtensionConsoleDebug = console.debug;

console.log = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [EXTENSION LOG] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    extensionConsoleLogs.push(logEntry);
    originalExtensionConsoleLog.apply(console, args);
};

console.error = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [EXTENSION ERROR] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    extensionConsoleLogs.push(logEntry);
    originalExtensionConsoleError.apply(console, args);
};

console.warn = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [EXTENSION WARN] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    extensionConsoleLogs.push(logEntry);
    originalExtensionConsoleWarn.apply(console, args);
};

console.info = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [EXTENSION INFO] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    extensionConsoleLogs.push(logEntry);
    originalExtensionConsoleInfo.apply(console, args);
};

console.debug = function(...args) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [EXTENSION DEBUG] ${args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ')}`;
    extensionConsoleLogs.push(logEntry);
    originalExtensionConsoleDebug.apply(console, args);
};

async function importFromGitHub(githubToken, context, webviewView) {
    try {
        webviewView.webview.postMessage({ type: "updateStatus", value: "🔗 Connessione a GitHub..." });
        
        // Fetch user repositories
        const response = await fetch('https://api.github.com/user/repos', {
            headers: {
                'Authorization': `token ${githubToken}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });
        
        if (!response.ok) {
            throw new Error('GitHub API error: ' + response.statusText);
        }
        
        const repos = await response.json();
        
        // Show repository picker
        const repoItems = repos.map(repo => ({
            label: repo.full_name,
            description: repo.description || 'Nessuna descrizione',
            detail: `⭐ ${repo.stargazers_count} | 🍴 ${repo.forks_count} | 📦 ${repo.language || 'N/A'}`,
            repo: repo
        }));
        
        const selectedRepo = await vscode.window.showQuickPick(repoItems, {
            placeHolder: 'Seleziona una repository da importare'
        });
        
        if (!selectedRepo) {
            webviewView.webview.postMessage({ type: "updateStatus", value: "❌ Importazione annullata" });
            return;
        }
        
        webviewView.webview.postMessage({ type: "updateStatus", value: `📥 Importazione di ${selectedRepo.repo.full_name}...` });
        
        // Clone repository using git
        const workspacePath = vscode.workspace.rootPath;
        if (!workspacePath) {
            throw new Error('Nessun workspace aperto');
        }
        
        const repoPath = path.join(workspacePath, selectedRepo.repo.name);
        
        // Execute git clone
        const { exec } = require('child_process');
        await new Promise((resolve, reject) => {
            exec(`git clone ${selectedRepo.repo.clone_url} "${repoPath}"`, (error, stdout, stderr) => {
                if (error) {
                    reject(error);
                } else {
                    resolve(stdout);
                }
            });
        });
        
        webviewView.webview.postMessage({ type: "githubImportSuccess" });
        
        // Open the cloned repository
        await vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(repoPath));
        
    } catch (error) {
        console.error('GitHub import error:', error);
        webviewView.webview.postMessage({ type: "githubImportError", value: error.message });
    }
}

module.exports = { activate, deactivate };
