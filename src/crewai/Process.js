/**
 * CrewAI-Style Process Class
 * Based on CrewAI Process architecture with sequential and hierarchical execution
 */
class Process {
    constructor(type = "sequential") {
        this.type = type; // "sequential" or "hierarchical"
        this.tasks = [];
        this.agents = [];
        this.currentStep = 0;
        this.status = "idle";
        this.executionHistory = [];
        this.callbacks = {
            onTaskStart: null,
            onTaskComplete: null,
            onTaskFail: null,
            onProcessStart: null,
            onProcessComplete: null,
            onProcessFail: null
        };
    }

    /**
     * Set callback for event
     */
    on(event, callback) {
        if (this.callbacks.hasOwnProperty(event)) {
            this.callbacks[event] = callback;
        }
    }

    /**
     * Add task to process
     */
    addTask(task) {
        this.tasks.push(task);
        return this;
    }

    /**
     * Add agent to process
     */
    addAgent(agent) {
        this.agents.push(agent);
        return this;
    }

    /**
     * Execute the process
     */
    async execute(context = {}) {
        this.status = "running";
        this.currentStep = 0;
        
        if (this.callbacks.onProcessStart) {
            await this.callbacks.onProcessStart(this, context);
        }

        try {
            let results;
            
            if (this.type === "sequential") {
                results = await this._executeSequential(context);
            } else if (this.type === "hierarchical") {
                results = await this._executeHierarchical(context);
            } else {
                throw new Error(`Unknown process type: ${this.type}`);
            }

            this.status = "completed";
            
            if (this.callbacks.onProcessComplete) {
                await this.callbacks.onProcessComplete(results, context);
            }

            return results;
        } catch (error) {
            this.status = "failed";
            
            if (this.callbacks.onProcessFail) {
                await this.callbacks.onProcessFail(error, context);
            }

            throw error;
        }
    }

    /**
     * Execute tasks sequentially
     */
    async _executeSequential(context) {
        const results = [];
        
        for (let i = 0; i < this.tasks.length; i++) {
            this.currentStep = i;
            const task = this.tasks[i];
            
            try {
                if (this.callbacks.onTaskStart) {
                    await this.callbacks.onTaskStart(task, i, context);
                }

                const result = await task.execute(context);
                results.push({ task: task.id, result, status: "completed" });
                
                if (this.callbacks.onTaskComplete) {
                    await this.callbacks.onTaskComplete(task, result, context);
                }
            } catch (error) {
                results.push({ task: task.id, error: error.message, status: "failed" });
                
                if (this.callbacks.onTaskFail) {
                    await this.callbacks.onTaskFail(task, error, context);
                }
                
                // Stop execution on failure
                throw error;
            }
        }
        
        return results;
    }

    /**
     * Execute tasks hierarchically
     */
    async _executeHierarchical(context) {
        // Hierarchical process uses a manager agent to coordinate
        const managerAgent = this.agents[0];
        const workerAgents = this.agents.slice(1);
        
        if (!managerAgent) {
            throw new Error("Hierarchical process requires a manager agent");
        }

        const results = [];
        
        // Manager creates execution plan
        const executionPlan = await this._createExecutionPlan(managerAgent, this.tasks, context);
        
        // Execute tasks according to plan
        for (const planItem of executionPlan) {
            const task = this.tasks.find(t => t.id === planItem.taskId);
            const agent = workerAgents.find(a => a.role === planItem.agentRole) || managerAgent;
            
            if (task && agent) {
                try {
                    if (this.callbacks.onTaskStart) {
                        await this.callbacks.onTaskStart(task, this.currentStep, context);
                    }

                    task.agent = agent;
                    const result = await task.execute(context);
                    results.push({ task: task.id, agent: agent.role, result, status: "completed" });
                    
                    if (this.callbacks.onTaskComplete) {
                        await this.callbacks.onTaskComplete(task, result, context);
                    }
                    
                    this.currentStep++;
                } catch (error) {
                    results.push({ task: task.id, agent: agent.role, error: error.message, status: "failed" });
                    
                    if (this.callbacks.onTaskFail) {
                        await this.callbacks.onTaskFail(task, error, context);
                    }
                }
            }
        }
        
        return results;
    }

    /**
     * Create execution plan using manager agent
     */
    async _createExecutionPlan(managerAgent, tasks, context) {
        // Simple plan: assign tasks to agents based on capabilities
        const plan = [];
        
        for (const task of tasks) {
            const suitableAgent = this._findSuitableAgent(task, this.agents);
            plan.push({
                taskId: task.id,
                agentRole: suitableAgent ? suitableAgent.role : "manager"
            });
        }
        
        return plan;
    }

    /**
     * Find suitable agent for task
     */
    _findSuitableAgent(task, agents) {
        // Simple heuristic: find agent with matching capability
        for (const agent of agents) {
            if (agent.goal && task.description && agent.goal.toLowerCase().includes(task.description.toLowerCase().split(' ')[0])) {
                return agent;
            }
        }
        return agents[0]; // Default to first agent
    }

    /**
     * Get process status
     */
    getStatus() {
        return {
            type: this.type,
            status: this.status,
            currentStep: this.currentStep,
            totalSteps: this.tasks.length,
            tasksCompleted: this.currentStep,
            progress: this.tasks.length > 0 ? (this.currentStep / this.tasks.length) * 100 : 0
        };
    }

    /**
     * Reset process state
     */
    reset() {
        this.currentStep = 0;
        this.status = "idle";
        this.tasks.forEach(task => task.reset());
        this.executionHistory = [];
    }

    /**
     * Clone process
     */
    clone() {
        const cloned = new Process(this.type);
        cloned.tasks = this.tasks.map(t => t.clone());
        cloned.agents = this.agents; // Agents are shared
        cloned.callbacks = { ...this.callbacks };
        return cloned;
    }
}

module.exports = Process;
