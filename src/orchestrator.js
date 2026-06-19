const vscode = require("vscode");
const fs = require("fs");
const path = require("path");

/**
 * CrewAI-Style Advanced Orchestrator for 11 Intelligent Agents
 * This orchestrator manages a sophisticated multi-agent system with:
 * - Large-scale project context management (1M+ files)
 * - Dynamic task allocation based on agent capabilities
 * - Real-time performance monitoring and optimization
 * - Hierarchical decision making with fallback mechanisms
 * - Cross-agent communication and knowledge sharing
 * - Adaptive learning from past executions
 * - Project indexing for dependency tracking
 * - Task breaking for complex operations
 * - Sub-agent delegation system
 * - Long-term project memory
 * - Change tracking and rollback
 */
class AdvancedOrchestrator {
    constructor(context) {
        this.context = context;
        this.storageDir = context.globalStorageUri.fsPath;
        
        // Create storage directory if it doesn't exist
        if (!fs.existsSync(this.storageDir)) {
            fs.mkdirSync(this.storageDir, { recursive: true });
        }
        
        this.agents = new Map();
        this.subAgents = new Map();
        this.taskQueue = [];
        this.activeTasks = new Map();
        this.performanceMetrics = new Map();
        this.knowledgeBase = new Map();
        this.executionHistory = [];
        this.maxConcurrentTasks = 10;
        this.taskTimeout = 600000; // 10 minutes for large projects
        
        // Large-scale project management
        this.projectIndex = new Map();
        this.dependencyGraph = new Map();
        this.callGraph = new Map();
        this.fileContextCache = new Map();
        this.projectState = new Map();
        this.changeHistory = [];
        
        // CrewAI-style task management
        this.taskHierarchy = new Map();
        this.taskDependencies = new Map();
        this.activeCrews = new Map();
        
        this.initializeAgents();
        this.initializeProjectIndex();
    }

    /**
     * Initialize all 11 specialized agents with their capabilities
     */
    initializeAgents() {
        const agentConfigs = [
            {
                id: "architect",
                name: "System Architect",
                capability: "architecture_analysis",
                priority: 1,
                specialties: ["system_design", "dependency_analysis", "refactoring_planning"],
                maxConcurrency: 3
            },
            {
                id: "programmer",
                name: "Master Programmer", 
                capability: "code_generation",
                priority: 2,
                specialties: ["full_stack", "optimization", "best_practices"],
                maxConcurrency: 5
            },
            {
                id: "debugger",
                name: "Expert Debugger",
                capability: "error_resolution",
                priority: 1,
                specialties: ["root_cause_analysis", "fix_generation", "testing"],
                maxConcurrency: 2
            },
            {
                id: "optimizer",
                name: "Performance Optimizer",
                capability: "performance_tuning",
                priority: 2,
                specialties: ["bottleneck_analysis", "memory_optimization", "algorithm_improvement"],
                maxConcurrency: 3
            },
            {
                id: "security",
                name: "Security Specialist",
                capability: "security_analysis",
                priority: 1,
                specialties: ["vulnerability_detection", "secure_coding", "compliance"],
                maxConcurrency: 2
            },
            {
                id: "tester",
                name: "Quality Assurance Engineer",
                capability: "testing_strategy",
                priority: 2,
                specialties: ["unit_testing", "integration_testing", "test_coverage"],
                maxConcurrency: 4
            },
            {
                id: "documenter",
                name: "Technical Writer",
                capability: "documentation",
                priority: 3,
                specialties: ["api_docs", "code_comments", "user_guides"],
                maxConcurrency: 3
            },
            {
                id: "analyzer",
                name: "Code Analyst",
                capability: "static_analysis",
                priority: 2,
                specialties: ["code_smell_detection", "complexity_analysis", "duplication_detection"],
                maxConcurrency: 4
            },
            {
                id: "integrator",
                name: "Integration Specialist",
                capability: "system_integration",
                priority: 2,
                specialties: ["api_integration", "service_mesh", "data_flow"],
                maxConcurrency: 3
            },
            {
                id: "deployer",
                name: "DevOps Engineer",
                capability: "deployment",
                priority: 2,
                specialties: ["ci_cd", "containerization", "cloud_deployment"],
                maxConcurrency: 2
            },
            {
                id: "guardian",
                name: "System Guardian",
                capability: "health_monitoring",
                priority: 1,
                specialties: ["error_prevention", "resource_monitoring", "auto_recovery"],
                maxConcurrency: 2
            },
            {
                id: "indexer",
                name: "Project Indexer",
                capability: "project_indexing",
                priority: 1,
                specialties: ["file_discovery", "dependency_analysis", "real_time_tracking"],
                maxConcurrency: 2
            },
            {
                id: "sandbox_executor",
                name: "Sandbox Executor",
                capability: "code_execution",
                priority: 1,
                specialties: ["terminal_execution", "library_installation", "server_launching"],
                maxConcurrency: 3
            },
            {
                id: "realtime_tester",
                name: "Real-time Tester",
                capability: "live_testing",
                priority: 1,
                specialties: ["error_detection", "automatic_correction", "iterative_retry"],
                maxConcurrency: 2
            }
        ];

        agentConfigs.forEach(config => {
            this.agents.set(config.id, {
                ...config,
                status: "idle",
                completedTasks: 0,
                averageExecutionTime: 0,
                successRate: 1.0,
                currentTask: null,
                activeSubTasks: 0
            });
        });

        this.initializeSubAgents();
        this.loadKnowledgeBase();
    }

    /**
     * Initialize sub-agents for specialized tasks
     */
    initializeSubAgents() {
        const subAgentConfigs = [
            { id: "file_scanner", name: "File Scanner", capability: "file_indexing", parent: "analyzer" },
            { id: "dependency_tracker", name: "Dependency Tracker", capability: "dependency_analysis", parent: "architect" },
            { id: "code_parser", name: "Code Parser", capability: "code_parsing", parent: "analyzer" },
            { id: "change_detector", name: "Change Detector", capability: "change_detection", parent: "guardian" },
            { id: "context_builder", name: "Context Builder", capability: "context_building", parent: "architect" },
            { id: "task_breaker", name: "Task Breaker", capability: "task_breakdown", parent: "architect" },
            { id: "file_modifier", name: "File Modifier", capability: "file_modification", parent: "programmer" },
            { id: "test_runner", name: "Test Runner", capability: "test_execution", parent: "tester" },
            { id: "file_watcher", name: "File Watcher", capability: "real_time_tracking", parent: "indexer" },
            { id: "terminal_manager", name: "Terminal Manager", capability: "terminal_execution", parent: "sandbox_executor" },
            { id: "browser_automator", name: "Browser Automator", capability: "browser_automation", parent: "sandbox_executor" },
            { id: "error_analyzer", name: "Error Analyzer", capability: "error_detection", parent: "realtime_tester" },
            { id: "auto_corrector", name: "Auto Corrector", capability: "automatic_correction", parent: "realtime_tester" }
        ];

        subAgentConfigs.forEach(config => {
            this.subAgents.set(config.id, {
                ...config,
                status: "idle",
                completedTasks: 0
            });
        });
    }

    /**
     * Initialize project index for large-scale file management
     */
    initializeProjectIndex() {
        const workspaceRoot = vscode.workspace.rootPath;
        if (!workspaceRoot) return;

        this.indexProject(workspaceRoot);
    }

    /**
     * Index entire project for large-scale management
     */
    async indexProject(workspaceRoot) {
        try {
            const indexPath = path.join(this.context.globalStorageUri.fsPath, "project_index.json");
            
            // Try to load existing index
            if (fs.existsSync(indexPath)) {
                try {
                    const data = fs.readFileSync(indexPath, "utf8");
                    const savedIndex = JSON.parse(data);
                    this.projectIndex = new Map(savedIndex.projectIndex);
                    this.dependencyGraph = new Map(savedIndex.dependencyGraph);
                    this.callGraph = new Map(savedIndex.callGraph);
                    this.projectState = new Map(savedIndex.projectState);
                    return;
                } catch (error) {
                    console.error("Failed to load project index, rebuilding:", error);
                }
            }

            // Build fresh index
            await this.buildProjectIndex(workspaceRoot);
            
        } catch (error) {
            console.error("Project indexing failed:", error);
        }
    }

    /**
     * Build project index from scratch
     */
    async buildProjectIndex(workspaceRoot) {
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
                        // Skip node_modules and other common directories
                        if (!["node_modules", ".git", "dist", "build", "coverage"].includes(item)) {
                            indexDirectory(fullPath, relativeItemPath);
                        }
                    } else if (stats.isFile()) {
                        // Index file
                        const ext = path.extname(item).toLowerCase();
                        const codeExtensions = [".js", ".ts", ".jsx", ".tsx", ".py", ".java", ".cpp", ".c", ".cs", ".go", ".rs", ".php", ".rb"];
                        
                        if (codeExtensions.includes(ext)) {
                            this.projectIndex.set(relativeItemPath, {
                                path: fullPath,
                                relativePath: relativeItemPath,
                                extension: ext,
                                size: stats.size,
                                modified: stats.mtime,
                                indexed: Date.now(),
                                dependencies: [],
                                imports: [],
                                exports: []
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
        
        // Analyze dependencies for indexed files
        await this.analyzeDependencies();
        
        // Save index
        this.saveProjectIndex();
    }

    /**
     * Analyze dependencies between files
     */
    async analyzeDependencies() {
        const importPatterns = {
            javascript: [
                /require\(['"]([^'"]+)['"]\)/g,
                /import.*from\s+['"]([^'"]+)['"]/g,
                /import\(['"]([^'"]+)['"]\)/g
            ],
            typescript: [
                /import.*from\s+['"]([^'"]+)['"]/g,
                /import\(['"]([^'"]+)['"]\)/g,
                /require\(['"]([^'"]+)['"]\)/g
            ],
            python: [/^from\s+(\S+)\s+import/gm, /^import\s+(\S+)/gm]
        };

        for (const [filePath, fileInfo] of this.projectIndex) {
            try {
                const content = fs.readFileSync(fileInfo.path, "utf8");
                const dependencies = [];
                const imports = [];

                let patterns = importPatterns.javascript;
                if (fileInfo.extension === ".ts" || fileInfo.extension === ".tsx") {
                    patterns = importPatterns.typescript;
                } else if (fileInfo.extension === ".py") {
                    patterns = importPatterns.python;
                }

                for (const pattern of patterns) {
                    let match;
                    while ((match = pattern.exec(content)) !== null) {
                        const dep = match[1];
                        dependencies.push(dep);
                        imports.push(dep);
                    }
                }

                fileInfo.dependencies = [...new Set(dependencies)];
                fileInfo.imports = [...new Set(imports)];

                // Build dependency graph
                for (const dep of fileInfo.dependencies) {
                    if (!this.dependencyGraph.has(dep)) {
                        this.dependencyGraph.set(dep, []);
                    }
                    this.dependencyGraph.get(dep).push(filePath);
                }

            } catch (error) {
                console.error(`Error analyzing dependencies for ${filePath}:`, error);
            }
        }
    }

    /**
     * Save project index to disk
     */
    saveProjectIndex() {
        const indexPath = path.join(this.context.globalStorageUri.fsPath, "project_index.json");
        try {
            fs.writeFileSync(indexPath, JSON.stringify({
                projectIndex: Array.from(this.projectIndex.entries()),
                dependencyGraph: Array.from(this.dependencyGraph.entries()),
                callGraph: Array.from(this.callGraph.entries()),
                projectState: Array.from(this.projectState.entries()),
                lastUpdated: Date.now()
            }));
        } catch (error) {
            console.error("Failed to save project index:", error);
        }
    }

    /**
     * Break down complex task into sub-tasks (CrewAI-style)
     */
    async breakDownTask(task) {
        const complexity = this.estimateComplexity(task);
        
        if (complexity < 3) {
            return [task]; // Simple task, no breakdown needed
        }

        const subTasks = [];
        const taskBreaker = this.subAgents.get("task_breaker");
        
        if (taskBreaker) {
            // Use task breaker agent to intelligently break down the task
            const breakdown = await this.executeSubAgent(taskBreaker, {
                ...task,
                operation: "breakdown",
                complexity: complexity
            });
            
            if (breakdown && breakdown.subTasks) {
                subTasks.push(...breakdown.subTasks);
            }
        } else {
            // Fallback: simple breakdown based on task type
            subTasks.push(...this.simpleTaskBreakdown(task, complexity));
        }

        // Set up task hierarchy
        this.taskHierarchy.set(task.id, {
            parent: null,
            children: subTasks.map(st => st.id),
            status: "in_progress"
        });

        subTasks.forEach((subTask, index) => {
            this.taskHierarchy.set(subTask.id, {
                parent: task.id,
                children: [],
                status: "pending",
                order: index
            });
        });

        return subTasks;
    }

    /**
     * Simple task breakdown fallback
     */
    simpleTaskBreakdown(task, complexity) {
        const subTasks = [];
        const taskLower = task.description.toLowerCase();

        if (taskLower.includes("refactor")) {
            subTasks.push(
                { id: this.generateTaskId(), description: "Analyze current code structure", type: "analysis", parentTask: task },
                { id: this.generateTaskId(), description: "Identify refactoring opportunities", type: "analysis", parentTask: task },
                { id: this.generateTaskId(), description: "Plan refactoring strategy", type: "planning", parentTask: task },
                { id: this.generateTaskId(), description: "Implement refactoring changes", type: "implementation", parentTask: task },
                { id: this.generateTaskId(), description: "Test refactored code", type: "testing", parentTask: task }
            );
        } else if (taskLower.includes("feature") || taskLower.includes("add")) {
            subTasks.push(
                { id: this.generateTaskId(), description: "Analyze requirements", type: "analysis", parentTask: task },
                { id: this.generateTaskId(), description: "Design implementation", type: "design", parentTask: task },
                { id: this.generateTaskId(), description: "Implement feature", type: "implementation", parentTask: task },
                { id: this.generateTaskId(), description: "Write tests", type: "testing", parentTask: task },
                { id: this.generateTaskId(), description: "Update documentation", type: "documentation", parentTask: task }
            );
        } else if (taskLower.includes("bug") || taskLower.includes("fix")) {
            subTasks.push(
                { id: this.generateTaskId(), description: "Analyze the bug", type: "analysis", parentTask: task },
                { id: this.generateTaskId(), description: "Identify root cause", type: "analysis", parentTask: task },
                { id: this.generateTaskId(), description: "Develop fix", type: "implementation", parentTask: task },
                { id: this.generateTaskId(), description: "Test fix", type: "testing", parentTask: task },
                { id: this.generateTaskId(), description: "Verify fix resolves issue", type: "verification", parentTask: task }
            );
        } else {
            // Generic breakdown
            const steps = Math.min(Math.ceil(complexity / 2), 5);
            for (let i = 0; i < steps; i++) {
                subTasks.push({
                    id: this.generateTaskId(),
                    description: `Step ${i + 1}: ${task.description}`,
                    type: "implementation",
                    parentTask: task
                });
            }
        }

        return subTasks;
    }

    /**
     * Execute sub-agent task
     */
    async executeSubAgent(subAgent, task) {
        subAgent.status = "busy";
        subAgent.currentTask = task;

        try {
            // Simulate sub-agent execution (in real implementation, would call actual sub-agent logic)
            const result = {
                subTasks: this.generateSubTasksForTask(task),
                analysis: this.performSubAgentAnalysis(subAgent, task)
            };
            
            subAgent.completedTasks++;
            subAgent.status = "idle";
            subAgent.currentTask = null;
            
            return result;
        } catch (error) {
            subAgent.status = "idle";
            subAgent.currentTask = null;
            throw error;
        }
    }

    /**
     * Generate sub-tasks for a given task
     */
    generateSubTasksForTask(task) {
        const subTasks = [];
        const taskLower = task.description.toLowerCase();
        
        if (taskLower.includes("large") || taskLower.includes("many files")) {
            // For large-scale operations, create file-level sub-tasks
            const filesToProcess = this.getRelevantFiles(task);
            const batchSize = 50; // Process 50 files at a time
            
            for (let i = 0; i < filesToProcess.length; i += batchSize) {
                const batch = filesToProcess.slice(i, i + batchSize);
                subTasks.push({
                    id: this.generateTaskId(),
                    description: `Process batch ${Math.floor(i / batchSize) + 1} (${batch.length} files)`,
                    type: "batch_processing",
                    files: batch,
                    parentTask: task
                });
            }
        }

        return subTasks;
    }

    /**
     * Get relevant files for a task
     */
    getRelevantFiles(task) {
        const relevantFiles = [];
        const taskLower = task.description.toLowerCase();
        
        for (const [filePath, fileInfo] of this.projectIndex) {
            let isRelevant = false;
            
            // Check if file path matches task context
            if (task.relatedFiles && task.relatedFiles.some(f => filePath.includes(f))) {
                isRelevant = true;
            }
            
            // Check if file extension matches task requirements
            if (taskLower.includes("javascript") && fileInfo.extension === ".js") {
                isRelevant = true;
            }
            
            if (isRelevant) {
                relevantFiles.push(filePath);
            }
        }
        
        return relevantFiles;
    }

    /**
     * Perform sub-agent analysis
     */
    performSubAgentAnalysis(subAgent, task) {
        return {
            subAgent: subAgent.name,
            capability: subAgent.capability,
            analysisType: task.operation || "general",
            confidence: 0.8,
            recommendations: []
        };
    }

    /**
     * Load persistent knowledge base from previous executions
     */
    loadKnowledgeBase() {
        const kbPath = path.join(this.context.globalStorageUri.fsPath, "knowledge_base.json");
        if (fs.existsSync(kbPath)) {
            try {
                const data = fs.readFileSync(kbPath, "utf8");
                this.knowledgeBase = new Map(JSON.parse(data));
            } catch (error) {
                console.error("Failed to load knowledge base:", error);
            }
        }
    }

    /**
     * Save knowledge base for future use
     */
    saveKnowledgeBase() {
        const kbPath = path.join(this.context.globalStorageUri.fsPath, "knowledge_base.json");
        try {
            fs.writeFileSync(kbPath, JSON.stringify(Array.from(this.knowledgeBase.entries())));
        } catch (error) {
            console.error("Failed to save knowledge base:", error);
        }
    }

    /**
     * Analyze task requirements and determine optimal agent allocation
     */
    analyzeTaskRequirements(task) {
        const requirements = {
            complexity: this.estimateComplexity(task),
            urgency: task.urgency || "normal",
            dependencies: this.identifyDependencies(task),
            requiredCapabilities: this.identifyRequiredCapabilities(task)
        };

        const agentScores = new Map();
        
        for (const [agentId, agent] of this.agents) {
            let score = 0;
            
            // Capability match
            if (agent.specialties.some(s => requirements.requiredCapabilities.includes(s))) {
                score += 40;
            }
            
            // Priority consideration
            score += (4 - agent.priority) * 10;
            
            // Performance history
            score += agent.successRate * 20;
            
            // Current load
            if (agent.status === "idle") {
                score += 30;
            } else if (agent.status === "busy") {
                score -= 20;
            }
            
            agentScores.set(agentId, score);
        }

        // Sort agents by score and return top candidates
        return Array.from(agentScores.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([id]) => id);
    }

    /**
     * Estimate task complexity based on various factors
     */
    estimateComplexity(task) {
        let complexity = 1;
        
        if (task.description) {
            complexity += task.description.length / 100;
        }
        
        if (task.codeContext) {
            complexity += task.codeContext.length / 500;
        }
        
        if (task.dependencies && task.dependencies.length > 0) {
            complexity += task.dependencies.length * 0.5;
        }
        
        return Math.min(Math.max(complexity, 1), 10);
    }

    /**
     * Identify task dependencies
     */
    identifyDependencies(task) {
        const dependencies = [];
        
        if (task.relatedFiles) {
            dependencies.push(...task.relatedFiles);
        }
        
        if (task.affectedComponents) {
            dependencies.push(...task.affectedComponents);
        }
        
        return dependencies;
    }

    /**
     * Identify required capabilities for the task
     */
    identifyRequiredCapabilities(task) {
        const capabilities = [];
        
        const taskLower = task.description.toLowerCase();
        
        if (taskLower.includes("bug") || taskLower.includes("error") || taskLower.includes("fix")) {
            capabilities.push("error_resolution");
        }
        
        if (taskLower.includes("performance") || taskLower.includes("optimize") || taskLower.includes("slow")) {
            capabilities.push("performance_tuning");
        }
        
        if (taskLower.includes("security") || taskLower.includes("vulnerability") || taskLower.includes("auth")) {
            capabilities.push("security_analysis");
        }
        
        if (taskLower.includes("test") || taskLower.includes("coverage") || taskLower.includes("spec")) {
            capabilities.push("testing_strategy");
        }
        
        if (taskLower.includes("document") || taskLower.includes("comment") || taskLower.includes("readme")) {
            capabilities.push("documentation");
        }
        
        if (taskLower.includes("architecture") || taskLower.includes("design") || taskLower.includes("structure")) {
            capabilities.push("architecture_analysis");
        }
        
        if (taskLower.includes("deploy") || taskLower.includes("build") || taskLower.includes("ci")) {
            capabilities.push("deployment");
        }
        
        if (taskLower.includes("index") || taskLower.includes("scan") || taskLower.includes("discover")) {
            capabilities.push("project_indexing");
        }
        
        if (taskLower.includes("execute") || taskLower.includes("run") || taskLower.includes("launch") || taskLower.includes("install")) {
            capabilities.push("code_execution");
        }
        
        if (taskLower.includes("test") || taskLower.includes("check") || taskLower.includes("verify")) {
            capabilities.push("live_testing");
        }
        
        // Default to code generation for general tasks
        if (capabilities.length === 0) {
            capabilities.push("code_generation");
        }
        
        return capabilities;
    }

    /**
     * Execute task with optimal agent allocation (CrewAI-style)
     */
    async executeTask(task) {
        const taskId = this.generateTaskId();
        
        const taskWithMetadata = {
            ...task,
            id: taskId,
            status: "queued",
            createdAt: Date.now(),
            attempts: 0,
            logs: [],
            mode: task.mode || 'ask'
        };

        // Break down complex tasks
        const subTasks = await this.breakDownTask(taskWithMetadata);
        
        if (subTasks.length > 1) {
            // Create a crew for this complex task
            return await this.executeCrewTask(taskWithMetadata, subTasks);
        } else {
            // Simple task, execute directly
            this.taskQueue.push(taskWithMetadata);
            this.executionHistory.push(taskWithMetadata);

            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    // Instead of rejecting, return a timeout result
                    resolve({
                        agent: "Orchestrator",
                        error: "Task timed out",
                        analysis: {
                            error: true,
                            errorMessage: `Task ${taskId} timed out after ${this.taskTimeout}ms`,
                            timeout: true
                        },
                        recommendations: [
                            {
                                priority: "high",
                                action: "Task timed out - consider increasing timeout or breaking down task"
                            }
                        ],
                        metadata: {
                            confidence: 0.0,
                            error: true,
                            timeout: true
                        }
                    });
                }, this.taskTimeout);

                this.processQueue().then(() => {
                    clearTimeout(timeout);
                    const completedTask = this.activeTasks.get(taskId);
                    if (completedTask && completedTask.status === "completed") {
                        resolve(completedTask);
                    } else if (completedTask && completedTask.status === "failed") {
                        // Return the failed task with error information instead of rejecting
                        resolve({
                            agent: "Orchestrator",
                            error: completedTask.error,
                            analysis: {
                                error: true,
                                errorMessage: completedTask.error,
                                failed: true
                            },
                            recommendations: [
                                {
                                    priority: "high",
                                    action: `Task failed: ${completedTask.error}`
                                }
                            ],
                            metadata: {
                                confidence: 0.0,
                                error: true,
                                failed: true
                            }
                        });
                    } else {
                        // Task didn't complete but didn't fail either - return incomplete result
                        resolve({
                            agent: "Orchestrator",
                            error: "Task did not complete",
                            analysis: {
                                error: true,
                                errorMessage: `Task ${taskId} did not complete`,
                                incomplete: true
                            },
                            recommendations: [
                                {
                                    priority: "high",
                                    action: "Task did not complete - check agent execution"
                                }
                            ],
                            metadata: {
                                confidence: 0.0,
                                error: true,
                                incomplete: true
                            }
                        });
                    }
                }).catch(error => {
                    clearTimeout(timeout);
                    // Catch any errors in processQueue itself
                    resolve({
                        agent: "Orchestrator",
                        error: error.message,
                        analysis: {
                            error: true,
                            errorMessage: error.message,
                            processError: true
                        },
                        recommendations: [
                            {
                                priority: "high",
                                action: `Process queue error: ${error.message}`
                            }
                        ],
                        metadata: {
                            confidence: 0.0,
                            error: true,
                            processError: true
                        }
                    });
                });
            });
        }
    }

    /**
     * Execute crew task with multiple agents (CrewAI-style)
     */
    async executeCrewTask(parentTask, subTasks) {
        const crewId = `crew_${parentTask.id}`;
        
        // Create crew configuration
        const crew = {
            id: crewId,
            parentTask: parentTask,
            subTasks: subTasks,
            agents: [],
            status: "initializing",
            startTime: Date.now(),
            results: []
        };

        // Assign optimal agents to each sub-task
        for (const subTask of subTasks) {
            const optimalAgents = this.analyzeTaskRequirements(subTask);
            const assignedAgent = this.assignAgentToSubTask(subTask, optimalAgents);
            if (assignedAgent) {
                crew.agents.push({
                    agentId: assignedAgent.id,
                    subTaskId: subTask.id,
                    status: "pending"
                });
            }
        }

        this.activeCrews.set(crewId, crew);
        crew.status = "active";

        // Execute sub-tasks in dependency order
        const results = [];
        for (let i = 0; i < subTasks.length; i++) {
            const subTask = subTasks[i];
            const crewAgent = crew.agents.find(ca => ca.subTaskId === subTask.id);
            
            if (crewAgent) {
                crewAgent.status = "active";
                const agent = this.agents.get(crewAgent.agentId);
                
                try {
                    const result = await this.executeAgentTask(agent, subTask);
                    results.push({ subTaskId: subTask.id, result, status: "completed" });
                    crewAgent.status = "completed";
                    
                    // Update task hierarchy
                    const hierarchy = this.taskHierarchy.get(subTask.id);
                    if (hierarchy) {
                        hierarchy.status = "completed";
                    }
                    
                } catch (error) {
                    results.push({ subTaskId: subTask.id, error: error.message, status: "failed" });
                    crewAgent.status = "failed";
                    
                    // Retry logic
                    if (subTask.attempts < 2) {
                        subTask.attempts = (subTask.attempts || 0) + 1;
                        i--; // Retry this sub-task
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        continue;
                    }
                }
            }
        }

        crew.status = "completed";
        crew.endTime = Date.now();
        crew.results = results;

        // Combine results into final result
        const finalResult = this.combineCrewResults(parentTask, results);
        
        // Update parent task
        parentTask.status = "completed";
        parentTask.result = finalResult;
        parentTask.completedAt = Date.now();
        parentTask.crewResults = results;

        this.activeCrews.delete(crewId);
        
        return finalResult;
    }

    /**
     * Assign agent to sub-task considering current load and capabilities
     */
    assignAgentToSubTask(subTask, optimalAgents) {
        for (const agentId of optimalAgents) {
            const agent = this.agents.get(agentId);
            if (agent && agent.status === "idle" && agent.activeSubTasks < agent.maxConcurrency) {
                agent.activeSubTasks++;
                return agent;
            }
        }
        
        // If all optimal agents are busy, use the best one anyway
        if (optimalAgents.length > 0) {
            const agent = this.agents.get(optimalAgents[0]);
            if (agent) {
                agent.activeSubTasks++;
                return agent;
            }
        }
        
        return null;
    }

    /**
     * Combine results from crew execution
     */
    combineCrewResults(parentTask, results) {
        const successfulResults = results.filter(r => r.status === "completed");
        const failedResults = results.filter(r => r.status === "failed");

        return {
            agent: "Crew Orchestrator",
            analysis: {
                totalSubTasks: results.length,
                completed: successfulResults.length,
                failed: failedResults.length,
                successRate: successfulResults.length / results.length
            },
            results: successfulResults.map(r => r.result),
            errors: failedResults.map(r => r.error),
            recommendations: this.generateCrewRecommendations(parentTask, results),
            metadata: {
                confidence: successfulResults.length / results.length,
                executionTime: Date.now() - parentTask.createdAt,
                crewSize: results.length
            }
        };
    }

    /**
     * Generate recommendations based on crew execution
     */
    generateCrewRecommendations(parentTask, results) {
        const recommendations = [];
        const failedResults = results.filter(r => r.status === "failed");
        
        if (failedResults.length > 0) {
            recommendations.push({
                priority: "high",
                action: "Review failed sub-tasks and implement fallback strategies"
            });
        }
        
        const successfulResults = results.filter(r => r.status === "completed");
        if (successfulResults.length === results.length) {
            recommendations.push({
                priority: "low",
                action: "All sub-tasks completed successfully, task is ready for deployment"
            });
        }
        
        return recommendations;
    }

    /**
     * Process task queue with intelligent scheduling
     */
    async processQueue() {
        while (this.taskQueue.length > 0 && this.activeTasks.size < this.maxConcurrentTasks) {
            const task = this.taskQueue.shift();
            await this.assignTaskToAgent(task);
        }
    }

    /**
     * Assign task to optimal agent and monitor execution
     */
    async assignTaskToAgent(task) {
        const optimalAgents = this.analyzeTaskRequirements(task);
        let assignedAgent = null;

        for (const agentId of optimalAgents) {
            const agent = this.agents.get(agentId);
            if (agent.status === "idle") {
                assignedAgent = agent;
                break;
            }
        }

        if (!assignedAgent && optimalAgents.length > 0) {
            // Use best available agent even if busy
            assignedAgent = this.agents.get(optimalAgents[0]);
        }

        if (!assignedAgent) {
            this.taskQueue.unshift(task);
            return;
        }

        // Create change tracking snapshot before execution
        const beforeSnapshot = await this.createProjectSnapshot(task);

        task.status = "assigned";
        task.assignedAgent = assignedAgent.id;
        assignedAgent.status = "busy";
        assignedAgent.currentTask = task;
        this.activeTasks.set(task.id, task);

        try {
            const result = await this.executeAgentTask(assignedAgent, task);
            
            // Create change tracking snapshot after execution
            const afterSnapshot = await this.createProjectSnapshot(task);
            
            // Track changes
            const changes = this.detectChanges(beforeSnapshot, afterSnapshot);
            if (changes.length > 0) {
                this.recordChanges(task, changes);
            }

            task.status = "completed";
            task.result = result;
            task.completedAt = Date.now();
            task.changes = changes;
            
            // Update agent performance metrics
            assignedAgent.completedTasks++;
            assignedAgent.averageExecutionTime = 
                (assignedAgent.averageExecutionTime * (assignedAgent.completedTasks - 1) + 
                 (task.completedAt - task.createdAt)) / assignedAgent.completedTasks;
            assignedAgent.successRate = 
                (assignedAgent.successRate * (assignedAgent.completedTasks - 1) + 1) / 
                assignedAgent.completedTasks;
            
            // Update knowledge base
            this.updateKnowledgeBase(task, result);
            
            // Update project state
            this.updateProjectState(task, result);
            
        } catch (error) {
            task.status = "failed";
            task.error = error.message;
            task.failedAt = Date.now();
            
            assignedAgent.successRate = 
                (assignedAgent.successRate * (assignedAgent.completedTasks - 1) + 0) / 
                (assignedAgent.completedTasks + 1);
            
            // Attempt rollback if changes were made
            if (beforeSnapshot) {
                await this.rollbackChanges(task, beforeSnapshot);
            }
            
            // Retry with fallback agent
            if (task.attempts < 2) {
                task.attempts++;
                task.status = "retrying";
                this.taskQueue.unshift(task);
            }
        } finally {
            assignedAgent.status = "idle";
            assignedAgent.currentTask = null;
            assignedAgent.activeSubTasks = Math.max(0, assignedAgent.activeSubTasks - 1);
            this.activeTasks.delete(task.id);
            
            // Process next task in queue
            this.processQueue();
        }
    }

    /**
     * Execute specific agent task with context and capabilities
     */
    async executeAgentTask(agent, task) {
        try {
            const AgentClass = this.getAgentClass(agent.id);
            if (!AgentClass) {
                throw new Error(`Agent class not found for ${agent.id}`);
            }

            const agentInstance = new AgentClass(this.context);
            
            // Prepare enhanced context for the agent
            const enhancedContext = {
                ...task,
                knowledgeBase: this.getRelevantKnowledge(task),
                agentCapabilities: agent.specialties,
                performanceHistory: this.getAgentPerformanceHistory(agent.id),
                systemContext: this.getSystemContext()
            };

            return await agentInstance.execute(enhancedContext);
        } catch (error) {
            console.error(`Error executing agent task for ${agent.id}:`, error);
            console.error(`Task details:`, task);
            
            // Return a fallback result instead of throwing
            return {
                agent: agent.name,
                error: error.message,
                analysis: {
                    error: true,
                    errorMessage: error.message,
                    fallback: true
                },
                recommendations: [
                    {
                        priority: "high",
                        action: "Agent execution failed - using fallback response"
                    }
                ],
                metadata: {
                    confidence: 0.1,
                    error: true
                }
            };
        }
    }

    /**
     * Get agent class by ID
     */
    getAgentClass(agentId) {
        const agentClasses = {
            architect: require("./agents/subsystem_architect"),
            programmer: require("./agents/liquid_programmer"),
            guardian: require("./agents/immune_guardian"),
            debugger: require("./agents/debugger"),
            optimizer: require("./agents/optimizer"),
            security: require("./agents/security"),
            tester: require("./agents/tester"),
            documenter: require("./agents/documenter"),
            analyzer: require("./agents/analyzer"),
            integrator: require("./agents/integrator"),
            deployer: require("./agents/deployer"),
            indexer: require("./agents/indexer"),
            sandbox_executor: require("./agents/sandbox_executor"),
            realtime_tester: require("./agents/realtime_tester")
        };
        
        return agentClasses[agentId];
    }

    /**
     * Get relevant knowledge from knowledge base
     */
    getRelevantKnowledge(task) {
        const relevant = [];
        
        for (const [key, value] of this.knowledgeBase) {
            if (task.description && key.includes(task.description.substring(0, 20))) {
                relevant.push({ key, value });
            }
        }
        
        return relevant;
    }

    /**
     * Get agent performance history
     */
    getAgentPerformanceHistory(agentId) {
        return this.executionHistory
            .filter(t => t.assignedAgent === agentId)
            .slice(-10);
    }

    /**
     * Get current system context
     */
    getSystemContext() {
        const activeEditor = vscode.window.activeTextEditor;
        return {
            workspaceRoot: vscode.workspace.rootPath,
            activeFile: activeEditor ? activeEditor.document.fileName : null,
            openFiles: vscode.workspace.textDocuments.map(doc => doc.fileName),
            workspaceFolders: vscode.workspace.workspaceFolders?.map(f => f.uri.fsPath) || []
        };
    }

    /**
     * Update knowledge base with new learnings
     */
    updateKnowledgeBase(task, result) {
        const key = `${task.description.substring(0, 50)}_${task.requiredCapabilities?.join("_")}`;
        this.knowledgeBase.set(key, {
            task: task.description,
            result: result,
            timestamp: Date.now(),
            success: task.status === "completed"
        });
        
        this.saveKnowledgeBase();
    }

    /**
     * Generate unique task ID
     */
    generateTaskId() {
        return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Get orchestrator status
     */
    getStatus() {
        return {
            agents: Array.from(this.agents.entries()).map(([id, agent]) => ({
                id,
                name: agent.name,
                status: agent.status,
                completedTasks: agent.completedTasks,
                successRate: agent.successRate,
                averageExecutionTime: agent.averageExecutionTime
            })),
            queue: this.taskQueue.length,
            activeTasks: this.activeTasks.size,
            knowledgeBaseSize: this.knowledgeBase.size,
            totalExecutions: this.executionHistory.length
        };
    }

    /**
     * Shutdown orchestrator gracefully
     */
    async shutdown() {
        // Wait for active tasks to complete
        while (this.activeTasks.size > 0) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        this.saveKnowledgeBase();
        this.saveProjectIndex();
        this.saveChangeHistory();
    }

    /**
     * Create project snapshot for change tracking
     */
    async createProjectSnapshot(task) {
        const snapshot = {
            timestamp: Date.now(),
            taskId: task.id,
            files: new Map()
        };

        // Snapshot relevant files
        const relevantFiles = this.getRelevantFiles(task);
        for (const filePath of relevantFiles.slice(0, 100)) { // Limit to 100 files for performance
            const fileInfo = this.projectIndex.get(filePath);
            if (fileInfo) {
                try {
                    const content = fs.readFileSync(fileInfo.path, "utf8");
                    snapshot.files.set(filePath, {
                        content: content,
                        hash: this.hashContent(content),
                        modified: fileInfo.modified
                    });
                } catch (error) {
                    console.error(`Error snapshotting ${filePath}:`, error);
                }
            }
        }

        return snapshot;
    }

    /**
     * Hash content for change detection
     */
    hashContent(content) {
        let hash = 0;
        for (let i = 0; i < content.length; i++) {
            const char = content.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return hash.toString(36);
    }

    /**
     * Detect changes between snapshots
     */
    detectChanges(beforeSnapshot, afterSnapshot) {
        const changes = [];

        if (!beforeSnapshot || !afterSnapshot) {
            return changes;
        }

        // Detect modified files
        for (const [filePath, afterFile] of afterSnapshot.files) {
            const beforeFile = beforeSnapshot.files.get(filePath);
            
            if (!beforeFile) {
                // New file
                changes.push({
                    type: "created",
                    path: filePath,
                    timestamp: afterSnapshot.timestamp
                });
            } else if (beforeFile.hash !== afterFile.hash) {
                // Modified file
                changes.push({
                    type: "modified",
                    path: filePath,
                    timestamp: afterSnapshot.timestamp,
                    previousHash: beforeFile.hash,
                    newHash: afterFile.hash
                });
            }
        }

        // Detect deleted files
        for (const [filePath, beforeFile] of beforeSnapshot.files) {
            if (!afterSnapshot.files.has(filePath)) {
                changes.push({
                    type: "deleted",
                    path: filePath,
                    timestamp: afterSnapshot.timestamp
                });
            }
        }

        return changes;
    }

    /**
     * Record changes in change history
     */
    recordChanges(task, changes) {
        const changeRecord = {
            taskId: task.id,
            taskDescription: task.description,
            changes: changes,
            timestamp: Date.now(),
            agent: task.assignedAgent
        };

        this.changeHistory.push(changeRecord);

        // Limit change history to prevent memory issues
        if (this.changeHistory.length > 1000) {
            this.changeHistory = this.changeHistory.slice(-500);
        }

        this.saveChangeHistory();
    }

    /**
     * Save change history to disk
     */
    saveChangeHistory() {
        const changeHistoryPath = path.join(this.context.globalStorageUri.fsPath, "change_history.json");
        try {
            fs.writeFileSync(changeHistoryPath, JSON.stringify(this.changeHistory.slice(-100)));
        } catch (error) {
            console.error("Failed to save change history:", error);
        }
    }

    /**
     * Rollback changes to previous state
     */
    async rollbackChanges(task, snapshot) {
        try {
            for (const [filePath, fileData] of snapshot.files) {
                const fileInfo = this.projectIndex.get(filePath);
                if (fileInfo) {
                    fs.writeFileSync(fileInfo.path, fileData.content, "utf8");
                }
            }
            
            console.log(`Rolled back changes for task ${task.id}`);
        } catch (error) {
            console.error(`Rollback failed for task ${task.id}:`, error);
        }
    }

    /**
     * Update project state based on task results
     */
    updateProjectState(task, result) {
        const stateKey = `${task.mode}_${task.description.substring(0, 30)}`;
        
        this.projectState.set(stateKey, {
            lastExecution: Date.now(),
            lastResult: result,
            executionCount: (this.projectState.get(stateKey)?.executionCount || 0) + 1,
            successRate: result ? 1.0 : 0.0
        });

        this.saveProjectIndex();
    }

    /**
     * Get project context for large-scale operations
     */
    async getProjectContext(task) {
        const context = {
            files: [],
            dependencies: new Map(),
            callGraph: new Map(),
            recentChanges: [],
            projectHealth: {}
        };

        // Get relevant files with context
        const relevantFiles = this.getRelevantFiles(task);
        for (const filePath of relevantFiles.slice(0, 50)) { // Limit for performance
            const fileInfo = this.projectIndex.get(filePath);
            if (fileInfo) {
                try {
                    const content = fs.readFileSync(fileInfo.path, "utf8");
                    context.files.push({
                        path: filePath,
                        content: content.substring(0, 5000), // Limit content size
                        dependencies: fileInfo.dependencies,
                        imports: fileInfo.imports
                    });
                } catch (error) {
                    console.error(`Error reading ${filePath}:`, error);
                }
            }
        }

        // Get dependency information
        for (const [dep, dependents] of this.dependencyGraph) {
            if (dependents.length > 0) {
                context.dependencies.set(dep, dependents.slice(0, 10)); // Limit
            }
        }

        // Get recent changes
        context.recentChanges = this.changeHistory.slice(-20);

        // Calculate project health metrics
        context.projectHealth = {
            totalFiles: this.projectIndex.size,
            totalDependencies: this.dependencyGraph.size,
            recentChangeRate: this.calculateChangeRate(),
            agentSuccessRate: this.calculateOverallAgentSuccessRate()
        };

        return context;
    }

    /**
     * Calculate recent change rate
     */
    calculateChangeRate() {
        if (this.changeHistory.length < 2) return 0;

        const recent = this.changeHistory.slice(-10);
        const timeSpan = recent[recent.length - 1].timestamp - recent[0].timestamp;
        const changeCount = recent.reduce((sum, record) => sum + record.changes.length, 0);

        return timeSpan > 0 ? changeCount / (timeSpan / 1000 / 60) : 0; // Changes per minute
    }

    /**
     * Calculate overall agent success rate
     */
    calculateOverallAgentSuccessRate() {
        let totalTasks = 0;
        let successfulTasks = 0;

        for (const [agentId, agent] of this.agents) {
            totalTasks += agent.completedTasks;
            successfulTasks += agent.completedTasks * agent.successRate;
        }

        return totalTasks > 0 ? successfulTasks / totalTasks : 1.0;
    }
}

module.exports = AdvancedOrchestrator;
