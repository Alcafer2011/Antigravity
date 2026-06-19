/**
 * CrewAI-Style Orchestrator
 * This orchestrator follows the exact CrewAI architecture with Agent, Task, Process, Crew classes
 * Fully compatible with CrewAI patterns but customizable for the project needs
 */
const vscode = require("vscode");
const fs = require("fs");
const path = require("path");

const { Agent, Task, Process, Crew, Tool, LLM, OutputParser } = require("./crewai");

class CrewAIOrchestrator {
    constructor(context) {
        this.context = context;
        this.storageDir = context.globalStorageUri.fsPath;
        
        // Create storage directory if it doesn't exist
        if (!fs.existsSync(this.storageDir)) {
            fs.mkdirSync(this.storageDir, { recursive: true });
        }
        
        // CrewAI components
        this.agents = new Map();
        this.tasks = new Map();
        this.crews = new Map();
        this.activeCrew = null;
        
        // Project management
        this.projectIndex = new Map();
        this.dependencyGraph = new Map();
        this.callGraph = new Map();
        
        // LLM configuration
        this.llm = null;
        this.llmConfig = {
            model: "default",
            temperature: 0.7,
            maxTokens: 2000
        };
        
        // Tools
        this.tools = new Map();
        
        // Memory
        this.memory = {
            shortTerm: new Map(),
            longTerm: new Map()
        };
        
        // Webview reference and message queue
        this.webview = null;
        this.messageQueue = [];
        
        // Callbacks
        this.callbacks = {
            onAgentStart: null,
            onAgentComplete: null,
            onAgentFail: null,
            onCrewStart: null,
            onCrewComplete: null,
            onCrewFail: null
        };
        
        this.initializeAgents();
        this.initializeTools();
        this.initializeProjectIndex();
    }

    /**
     * Set webview reference and flush message queue
     */
    setWebview(webview) {
        this.webview = webview;
        // Flush queued messages
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.sendMessageToWebview(message.type, message.data);
        }
    }

    /**
     * Send message to webview with queue fallback
     */
    sendMessageToWebview(type, data) {
        const message = { type, ...data };
        if (this.webview) {
            try {
                this.webview.postMessage(message);
            } catch (error) {
                console.error("Failed to send message to webview:", error);
            }
        } else {
            // Queue message if webview not ready
            this.messageQueue.push({ type, data });
        }
    }

    /**
     * Initialize CrewAI-style agents
     */
    initializeAgents() {
        const agentConfigs = [
            {
                id: "architect",
                role: "System Architect",
                goal: "Design robust software architectures and analyze system dependencies",
                backstory: "You are an expert software architect with 20 years of experience in designing large-scale systems. You specialize in microservices, monolithic architectures, and hybrid approaches.",
                verbose: true,
                allowDelegation: true,
                maxIter: 25
            },
            {
                id: "programmer",
                role: "Master Programmer",
                goal: "Write clean, efficient, and well-documented code following best practices",
                backstory: "You are a senior software engineer with expertise in multiple programming languages and frameworks. You focus on code quality, performance, and maintainability.",
                verbose: true,
                allowDelegation: true,
                maxIter: 25
            },
            {
                id: "debugger",
                role: "Expert Debugger",
                goal: "Identify, analyze, and fix software bugs and errors efficiently",
                backstory: "You are a debugging specialist with deep knowledge of common software issues and their solutions. You excel at root cause analysis and systematic problem-solving.",
                verbose: true,
                allowDelegation: false,
                maxIter: 15
            },
            {
                id: "optimizer",
                role: "Performance Optimizer",
                goal: "Optimize software performance and identify bottlenecks",
                backstory: "You are a performance engineering expert with experience in profiling, optimization, and scalability. You focus on making software faster and more efficient.",
                verbose: true,
                allowDelegation: true,
                maxIter: 20
            },
            {
                id: "security",
                role: "Security Specialist",
                goal: "Identify vulnerabilities and implement security best practices",
                backstory: "You are a cybersecurity expert with knowledge of OWASP, security standards, and common attack vectors. You ensure software is secure and compliant.",
                verbose: true,
                allowDelegation: false,
                maxIter: 15
            },
            {
                id: "tester",
                role: "Quality Assurance Engineer",
                goal: "Design and execute comprehensive testing strategies",
                backstory: "You are a QA specialist with expertise in unit testing, integration testing, and end-to-end testing. You ensure software quality and reliability.",
                verbose: true,
                allowDelegation: true,
                maxIter: 20
            },
            {
                id: "documenter",
                role: "Technical Writer",
                goal: "Create clear and comprehensive documentation",
                backstory: "You are a technical documentation expert with experience in API docs, user guides, and developer documentation. You make complex concepts accessible.",
                verbose: true,
                allowDelegation: true,
                maxIter: 15
            },
            {
                id: "analyzer",
                role: "Code Analyst",
                goal: "Analyze code quality, complexity, and maintainability",
                backstory: "You are a code analysis specialist with expertise in static analysis, code metrics, and technical debt assessment. You provide actionable insights for code improvement.",
                verbose: true,
                allowDelegation: true,
                maxIter: 20
            },
            {
                id: "integrator",
                role: "Integration Specialist",
                goal: "Design and implement system integrations and data flows",
                backstory: "You are an integration expert with experience in APIs, message queues, and service meshes. You ensure seamless communication between system components.",
                verbose: true,
                allowDelegation: true,
                maxIter: 20
            },
            {
                id: "deployer",
                role: "DevOps Engineer",
                goal: "Design and implement deployment pipelines and infrastructure",
                backstory: "You are a DevOps specialist with expertise in CI/CD, containerization, and cloud infrastructure. You ensure reliable and automated deployments.",
                verbose: true,
                allowDelegation: true,
                maxIter: 20
            },
            {
                id: "guardian",
                role: "System Guardian",
                goal: "Monitor system health and prevent errors",
                backstory: "You are a system monitoring specialist with expertise in health checks, error prevention, and auto-recovery mechanisms. You ensure system stability.",
                verbose: true,
                allowDelegation: false,
                maxIter: 15
            },
            {
                id: "indexer",
                role: "Project Indexer",
                goal: "Index and analyze project structure and dependencies",
                backstory: "You are a project indexing specialist with expertise in code navigation, dependency analysis, and project structure understanding. You make large codebases navigable.",
                verbose: true,
                allowDelegation: false,
                maxIter: 15
            },
            {
                id: "sandbox_executor",
                role: "Sandbox Executor",
                goal: "Execute code in isolated environments with terminal and browser capabilities",
                backstory: "You are a code execution specialist with expertise in sandboxing, process management, and browser automation. You enable safe code testing and execution.",
                verbose: true,
                allowDelegation: false,
                maxIter: 20
            },
            {
                id: "realtime_tester",
                role: "Real-time Tester",
                goal: "Test code in real-time and automatically correct errors",
                backstory: "You are a real-time testing specialist with expertise in live testing, error detection, and automatic correction. You ensure code quality during development.",
                verbose: true,
                allowDelegation: false,
                maxIter: 25
            }
        ];

        agentConfigs.forEach(config => {
            const agent = new Agent({
                role: config.role,
                goal: config.goal,
                backstory: config.backstory,
                verbose: config.verbose,
                allowDelegation: config.allowDelegation,
                maxIter: config.maxIter,
                tools: [],
                llm: null // Will be set when LLM is configured
            });
            
            this.agents.set(config.id, agent);
        });
    }

    /**
     * Initialize CrewAI-style tools
     */
    initializeTools() {
        // File system tools
        this.tools.set('read_file', new Tool({
            name: 'read_file',
            description: 'Read a file from the file system',
            func: async (args, context) => {
                const filePath = args.path;
                try {
                    const content = fs.readFileSync(filePath, 'utf8');
                    return { content, success: true };
                } catch (error) {
                    return { error: error.message, success: false };
                }
            },
            argsSchema: {
                path: { type: 'string', required: true }
            }
        }));

        this.tools.set('write_file', new Tool({
            name: 'write_file',
            description: 'Write content to a file',
            func: async (args, context) => {
                const filePath = args.path;
                const content = args.content;
                try {
                    fs.writeFileSync(filePath, content, 'utf8');
                    return { success: true };
                } catch (error) {
                    return { error: error.message, success: false };
                }
            },
            argsSchema: {
                path: { type: 'string', required: true },
                content: { type: 'string', required: true }
            }
        }));

        this.tools.set('list_directory', new Tool({
            name: 'list_directory',
            description: 'List files in a directory',
            func: async (args, context) => {
                const dirPath = args.path;
                try {
                    const files = fs.readdirSync(dirPath);
                    return { files, success: true };
                } catch (error) {
                    return { error: error.message, success: false };
                }
            },
            argsSchema: {
                path: { type: 'string', required: true }
            }
        }));

        // Terminal tools
        this.tools.set('execute_command', new Tool({
            name: 'execute_command',
            description: 'Execute a shell command',
            func: async (args, context) => {
                const command = args.command;
                try {
                    const { execSync } = require('child_process');
                    const output = execSync(command, { encoding: 'utf8', timeout: 30000 });
                    return { output, success: true };
                } catch (error) {
                    return { error: error.message, success: false };
                }
            },
            argsSchema: {
                command: { type: 'string', required: true }
            }
        }));

        // Search tools
        this.tools.set('search_files', new Tool({
            name: 'search_files',
            description: 'Search for text in files',
            func: async (args, context) => {
                const pattern = args.pattern;
                const directory = args.directory || vscode.workspace.rootPath;
                try {
                    const { execSync } = require('child_process');
                    const output = execSync(`grep -r "${pattern}" ${directory}`, { encoding: 'utf8' });
                    return { results: output, success: true };
                } catch (error) {
                    return { error: error.message, success: false };
                }
            },
            argsSchema: {
                pattern: { type: 'string', required: true },
                directory: { type: 'string', required: false }
            }
        }));
    }

    /**
     * Configure LLM
     */
    configureLLM(config) {
        this.llmConfig = { ...this.llmConfig, ...config };
        this.llm = new LLM(this.llmConfig);
        
        // Update all agents with the LLM
        for (const agent of this.agents.values()) {
            agent.llm = this.llm;
        }
    }

    /**
     * Set callback
     */
    on(event, callback) {
        if (this.callbacks.hasOwnProperty(event)) {
            this.callbacks[event] = callback;
        }
    }

    /**
     * Create a CrewAI-style task
     */
    createTask(config) {
        const task = new Task({
            description: config.description,
            expectedOutput: config.expectedOutput,
            agent: config.agentId ? this.agents.get(config.agentId) : null,
            tools: config.toolIds ? config.toolIds.map(id => this.tools.get(id)).filter(t => t) : [],
            asyncExecution: config.asyncExecution || false,
            context: config.context || [],
            outputFormat: config.outputFormat || null,
            callback: config.callback || null,
            priority: config.priority || "normal",
            dependencies: config.dependencies || [],
            maxRetries: config.maxRetries || 3
        });
        
        this.tasks.set(task.id, task);
        return task;
    }

    /**
     * Create a CrewAI-style crew
     */
    createCrew(config) {
        const crew = new Crew({
            agents: config.agentIds ? config.agentIds.map(id => this.agents.get(id)).filter(a => a) : Array.from(this.agents.values()),
            tasks: config.taskIds ? config.taskIds.map(id => this.tasks.get(id)).filter(t => t) : [],
            process: config.processType ? new Process(config.processType) : new Process("sequential"),
            verbose: config.verbose !== false,
            memory: config.memory || false,
            cache: config.cache !== false,
            maxRpm: config.maxRpm || null,
            shareCrew: config.shareCrew !== false
        });
        
        // Set callbacks
        crew.on('onCrewStart', this.callbacks.onCrewStart);
        crew.on('onCrewComplete', this.callbacks.onCrewComplete);
        crew.on('onCrewFail', this.callbacks.onCrewFail);
        crew.on('onAgentStart', this.callbacks.onAgentStart);
        crew.on('onAgentComplete', this.callbacks.onAgentComplete);
        crew.on('onAgentFail', this.callbacks.onAgentFail);
        
        this.crews.set(crew.id || `crew_${Date.now()}`, crew);
        return crew;
    }

    /**
     * Execute a task (CrewAI-style)
     */
    async executeTask(taskConfig, context = {}) {
        const task = this.createTask(taskConfig);
        
        const crewContext = {
            ...context,
            crew: this.activeCrew,
            agents: this.agents,
            tasks: this.tasks,
            tools: this.tools,
            memory: this.memory,
            projectIndex: this.projectIndex,
            dependencyGraph: this.dependencyGraph
        };
        
        return await task.execute(crewContext);
    }

    /**
     * Execute a crew (CrewAI-style)
     */
    async executeCrew(crewConfig, context = {}) {
        const crew = this.createCrew(crewConfig);
        this.activeCrew = crew;
        
        const crewContext = {
            ...context,
            crew: crew,
            agents: this.agents,
            tasks: this.tasks,
            tools: this.tools,
            memory: this.memory,
            projectIndex: this.projectIndex,
            dependencyGraph: this.dependencyGraph
        };
        
        return await crew.kickoff(crewContext);
    }

    /**
     * Initialize project index
     */
    initializeProjectIndex() {
        const workspaceRoot = vscode.workspace.rootPath;
        if (!workspaceRoot) return;

        this.indexProject(workspaceRoot);
    }

    /**
     * Index project
     */
    async indexProject(workspaceRoot) {
        try {
            const startTime = Date.now();
            let fileCount = 0;

            const indexDirectory = (dir, relativePath = "") => {
                try {
                    const items = fs.readdirSync(dir);
                    
                    for (const item of items) {
                        const fullPath = path.join(dir, item);
                        const relativeItemPath = path.join(relativePath, item);
                        const stats = fs.statSync(fullPath);

                        if (stats.isDirectory()) {
                            if (!["node_modules", ".git", "dist", "build", "coverage"].includes(item)) {
                                indexDirectory(fullPath, relativeItemPath);
                            }
                        } else if (stats.isFile()) {
                            const ext = path.extname(item).toLowerCase();
                            const codeExtensions = [".js", ".ts", ".jsx", ".tsx", ".py", ".java", ".cpp", ".c", ".cs", ".go", ".rs", ".php", ".rb"];
                            
                            if (codeExtensions.includes(ext)) {
                                this.projectIndex.set(relativeItemPath, {
                                    path: fullPath,
                                    relativePath: relativeItemPath,
                                    extension: ext,
                                    size: stats.size,
                                    modified: stats.mtime,
                                    indexed: Date.now()
                                });
                                fileCount++;
                            }
                        }
                    }
                } catch (error) {
                    console.error(`Error indexing ${dir}:`, error);
                }
            };

            indexDirectory(workspaceRoot);
            
            console.log(`Indexed ${fileCount} files in ${Date.now() - startTime}ms`);
            
        } catch (error) {
            console.error("Project indexing error:", error);
        }
    }

    /**
     * Get orchestrator status
     */
    getStatus() {
        return {
            agents: Array.from(this.agents.values()).map(agent => agent.getStatus()),
            tasks: Array.from(this.tasks.values()).map(task => task.getStatus()),
            crews: Array.from(this.crews.values()).map(crew => crew.getStatus()),
            activeCrew: this.activeCrew ? this.activeCrew.getStatus() : null,
            toolsCount: this.tools.size,
            projectIndexSize: this.projectIndex.size,
            memory: {
                shortTermSize: this.memory.shortTerm.size,
                longTermSize: this.memory.longTerm.size
            }
        };
    }

    /**
     * Get agent by ID
     */
    getAgent(agentId) {
        return this.agents.get(agentId);
    }

    /**
     * Get task by ID
     */
    getTask(taskId) {
        return this.tasks.get(taskId);
    }

    /**
     * Get crew by ID
     */
    getCrew(crewId) {
        return this.crews.get(crewId);
    }

    /**
     * Reset orchestrator state
     */
    reset() {
        this.tasks.forEach(task => task.reset());
        this.crews.forEach(crew => crew.reset());
        this.agents.forEach(agent => agent.reset());
        this.activeCrew = null;
        this.memory.shortTerm.clear();
    }

    /**
     * Dispose orchestrator
     */
    dispose() {
        this.reset();
        this.agents.clear();
        this.tasks.clear();
        this.crews.clear();
        this.tools.clear();
        this.projectIndex.clear();
        this.dependencyGraph.clear();
        this.callGraph.clear();
    }
}

module.exports = CrewAIOrchestrator;
