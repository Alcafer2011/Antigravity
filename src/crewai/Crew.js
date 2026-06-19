/**
 * CrewAI-Style Crew Class
 * Based on CrewAI Crew architecture with agents, tasks, process, verbose, memory
 */
const Process = require('./Process');

class Crew {
    constructor(config) {
        this.agents = config.agents || [];
        this.tasks = config.tasks || [];
        this.process = config.process || new Process("sequential");
        this.verbose = config.verbose !== false;
        this.memory = config.memory || false;
        this.cache = config.cache !== false;
        this.maxRpm = config.maxRpm || null;
        this.shareCrew = config.shareCrew !== false;
        
        // Crew state
        this.kickoffResults = null;
        this.usageMetrics = {
            totalTokensUsed: 0,
            totalCost: 0,
            totalExecutionTime: 0
        };
        this.callbacks = {
            onCrewStart: null,
            onCrewComplete: null,
            onCrewFail: null,
            onAgentStart: null,
            onAgentComplete: null,
            onAgentFail: null
        };
        
        // Initialize process with tasks
        this._initializeProcess();
    }

    /**
     * Initialize process with tasks
     */
    _initializeProcess() {
        this.process.tasks = this.tasks;
        this.process.agents = this.agents;
        
        // Set up process callbacks
        this.process.on('onTaskStart', async (task, step, context) => {
            if (this.callbacks.onAgentStart) {
                const agent = task.agent || this._findAgentForTask(task);
                await this.callbacks.onAgentStart(agent, task, context);
            }
        });
        
        this.process.on('onTaskComplete', async (task, result, context) => {
            if (this.callbacks.onAgentComplete) {
                const agent = task.agent || this._findAgentForTask(task);
                await this.callbacks.onAgentComplete(agent, task, result, context);
            }
        });
        
        this.process.on('onTaskFail', async (task, error, context) => {
            if (this.callbacks.onAgentFail) {
                const agent = task.agent || this._findAgentForTask(task);
                await this.callbacks.onAgentFail(agent, task, error, context);
            }
        });
    }

    /**
     * Add agent to crew
     */
    addAgent(agent) {
        this.agents.push(agent);
        this.process.agents = this.agents;
        return this;
    }

    /**
     * Add task to crew
     */
    addTask(task) {
        this.tasks.push(task);
        this.process.tasks = this.tasks;
        return this;
    }

    /**
     * Set process type
     */
    setProcess(type) {
        this.process = new Process(type);
        this._initializeProcess();
        return this;
    }

    /**
     * Set callback for event
     */
    on(event, callback) {
        if (this.callbacks.hasOwnProperty(event)) {
            this.callbacks[event] = callback;
        }
        return this;
    }

    /**
     * Kick off crew execution
     */
    async kickoff(context = {}) {
        const startTime = Date.now();
        
        if (this.verbose) {
            console.log(`[Crew] Starting execution with ${this.agents.length} agents and ${this.tasks.length} tasks`);
        }

        if (this.callbacks.onCrewStart) {
            await this.callbacks.onCrewStart(this, context);
        }

        try {
            // Prepare context with crew information
            const crewContext = {
                ...context,
                crew: this,
                agents: this.agents,
                tasks: this.tasks,
                memory: this.memory ? this._createMemory() : null
            };

            // Execute process
            this.kickoffResults = await this.process.execute(crewContext);
            
            const executionTime = Date.now() - startTime;
            this.usageMetrics.totalExecutionTime += executionTime;

            if (this.verbose) {
                console.log(`[Crew] Execution completed in ${executionTime}ms`);
            }

            if (this.callbacks.onCrewComplete) {
                await this.callbacks.onCrewComplete(this.kickoffResults, context);
            }

            return this.kickoffResults;
        } catch (error) {
            if (this.verbose) {
                console.error(`[Crew] Execution failed: ${error.message}`);
            }

            if (this.callbacks.onCrewFail) {
                await this.callbacks.onCrewFail(error, context);
            }

            throw error;
        }
    }

    /**
     * Find agent for task
     */
    _findAgentForTask(task) {
        if (task.agent) {
            return task.agent;
        }
        
        // Simple heuristic: find agent with matching goal
        for (const agent of this.agents) {
            if (agent.goal && task.description && 
                agent.goal.toLowerCase().includes(task.description.toLowerCase().split(' ')[0])) {
                return agent;
            }
        }
        
        return this.agents[0]; // Default to first agent
    }

    /**
     * Create memory for crew
     */
    _createMemory() {
        return {
            shortTerm: new Map(),
            longTerm: new Map(),
            
            set: function(key, value, type = 'short') {
                if (type === 'short') {
                    this.shortTerm.set(key, { value, timestamp: Date.now() });
                } else {
                    this.longTerm.set(key, { value, timestamp: Date.now() });
                }
            },
            
            get: function(key, type = 'short') {
                const memory = type === 'short' ? this.shortTerm : this.longTerm;
                return memory.get(key)?.value;
            },
            
            getAll: function(type = 'short') {
                const memory = type === 'short' ? this.shortTerm : this.longTerm;
                return Array.from(memory.entries()).map(([key, data]) => ({ key, value: data.value, timestamp: data.timestamp }));
            },
            
            clear: function(type = 'short') {
                if (type === 'short') {
                    this.shortTerm.clear();
                } else {
                    this.longTerm.clear();
                }
            }
        };
    }

    /**
     * Get crew status
     */
    getStatus() {
        return {
            agentsCount: this.agents.length,
            tasksCount: this.tasks.length,
            processType: this.process.type,
            processStatus: this.process.getStatus(),
            hasResults: this.kickoffResults !== null,
            usageMetrics: this.usageMetrics,
            memoryEnabled: this.memory,
            cacheEnabled: this.cache
        };
    }

    /**
     * Get agent by role
     */
    getAgentByRole(role) {
        return this.agents.find(agent => agent.role === role);
    }

    /**
     * Get task by ID
     */
    getTaskById(taskId) {
        return this.tasks.find(task => task.id === taskId);
    }

    /**
     * Reset crew state
     */
    reset() {
        this.kickoffResults = null;
        this.process.reset();
        this.tasks.forEach(task => task.reset());
        this.agents.forEach(agent => agent.reset());
    }

    /**
     * Clone crew
     */
    clone() {
        const cloned = new Crew({
            agents: this.agents, // Agents are shared
            tasks: this.tasks.map(t => t.clone()),
            process: this.process.clone(),
            verbose: this.verbose,
            memory: this.memory,
            cache: this.cache,
            maxRpm: this.maxRpm,
            shareCrew: this.shareCrew
        });
        cloned.callbacks = { ...this.callbacks };
        return cloned;
    }

    /**
     * Export crew configuration
     */
    exportConfig() {
        return {
            agents: this.agents.map(agent => ({
                role: agent.role,
                goal: agent.goal,
                backstory: agent.backstory,
                verbose: agent.verbose,
                allowDelegation: agent.allowDelegation,
                tools: agent.tools.map(tool => tool.name)
            })),
            tasks: this.tasks.map(task => ({
                description: task.description,
                expectedOutput: task.expectedOutput,
                agent: task.agent?.role,
                tools: task.tools.map(tool => tool.name),
                asyncExecution: task.asyncExecution
            })),
            process: this.process.type,
            verbose: this.verbose,
            memory: this.memory,
            cache: this.cache
        };
    }
}

module.exports = Crew;
