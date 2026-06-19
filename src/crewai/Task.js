/**
 * CrewAI-Style Task Class
 * Based on CrewAI Task architecture with description, expected_output, agent, tools, async_execution
 */
class Task {
    constructor(config) {
        this.id = config.id || this._generateId();
        this.description = config.description;
        this.expectedOutput = config.expectedOutput || "";
        this.agent = config.agent || null;
        this.tools = config.tools || [];
        this.asyncExecution = config.asyncExecution || false;
        this.context = config.context || [];
        this.outputFormat = config.outputFormat || null;
        this.callback = config.callback || null;
        
        // Task metadata
        this.complexity = this._estimateComplexity();
        this.priority = config.priority || "normal";
        this.dependencies = config.dependencies || [];
        this.status = "pending";
        this.result = null;
        this.error = null;
        this.startTime = null;
        this.endTime = null;
        this.executionTime = null;
        this.retries = 0;
        this.maxRetries = config.maxRetries || 3;
    }

    /**
     * Generate unique task ID
     */
    _generateId() {
        return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Estimate task complexity
     */
    _estimateComplexity() {
        let complexity = 1;
        
        if (this.description) {
            complexity += Math.min(this.description.length / 100, 5);
        }
        
        if (this.expectedOutput) {
            complexity += Math.min(this.expectedOutput.length / 100, 3);
        }
        
        if (this.tools && this.tools.length > 0) {
            complexity += this.tools.length * 0.5;
        }
        
        if (this.dependencies && this.dependencies.length > 0) {
            complexity += this.dependencies.length * 0.3;
        }
        
        return Math.min(Math.max(complexity, 1), 10);
    }

    /**
     * Execute the task
     */
    async execute(context = {}) {
        this.status = "in_progress";
        this.startTime = Date.now();
        
        try {
            // Check dependencies
            await this._checkDependencies(context);
            
            // Execute task
            if (this.agent) {
                this.result = await this.agent.executeTask(this, context);
            } else {
                this.result = await this._executeWithoutAgent(context);
            }
            
            this.status = "completed";
            this.endTime = Date.now();
            this.executionTime = this.endTime - this.startTime;
            
            // Execute callback if provided
            if (this.callback) {
                await this.callback(this, context);
            }
            
            return this.result;
        } catch (error) {
            this.error = error.message;
            this.status = "failed";
            this.endTime = Date.now();
            this.executionTime = this.endTime - this.startTime;
            
            // Retry logic
            if (this.retries < this.maxRetries) {
                this.retries++;
                this.status = "retrying";
                await new Promise(resolve => setTimeout(resolve, 1000 * this.retries));
                return await this.execute(context);
            }
            
            throw error;
        }
    }

    /**
     * Check task dependencies
     */
    async _checkDependencies(context) {
        for (const depId of this.dependencies) {
            const depTask = context.tasks?.get(depId);
            if (!depTask) {
                throw new Error(`Dependency task ${depId} not found`);
            }
            
            if (depTask.status !== "completed") {
                throw new Error(`Dependency task ${depId} not completed`);
            }
        }
    }

    /**
     * Execute task without agent (fallback)
     */
    async _executeWithoutAgent(context) {
        // Simple execution using tools
        const results = [];
        
        for (const tool of this.tools) {
            try {
                const result = await tool.execute(this, context);
                results.push({ tool: tool.name, result });
            } catch (error) {
                results.push({ tool: tool.name, error: error.message });
            }
        }
        
        return {
            description: this.description,
            toolsResults: results,
            context: this.context
        };
    }

    /**
     * Add dependency
     */
    addDependency(taskId) {
        if (!this.dependencies.includes(taskId)) {
            this.dependencies.push(taskId);
            this.complexity = this._estimateComplexity();
        }
    }

    /**
     * Remove dependency
     */
    removeDependency(taskId) {
        this.dependencies = this.dependencies.filter(id => id !== taskId);
        this.complexity = this._estimateComplexity();
    }

    /**
     * Get task status
     */
    getStatus() {
        return {
            id: this.id,
            description: this.description,
            status: this.status,
            complexity: this.complexity,
            priority: this.priority,
            dependencies: this.dependencies,
            executionTime: this.executionTime,
            retries: this.retries,
            hasResult: this.result !== null,
            hasError: this.error !== null
        };
    }

    /**
     * Reset task state
     */
    reset() {
        this.status = "pending";
        this.result = null;
        this.error = null;
        this.startTime = null;
        this.endTime = null;
        this.executionTime = null;
        this.retries = 0;
    }

    /**
     * Clone task
     */
    clone() {
        return new Task({
            id: this.id + "_clone",
            description: this.description,
            expectedOutput: this.expectedOutput,
            agent: this.agent,
            tools: this.tools,
            asyncExecution: this.asyncExecution,
            context: this.context,
            outputFormat: this.outputFormat,
            callback: this.callback,
            priority: this.priority,
            dependencies: [...this.dependencies],
            maxRetries: this.maxRetries
        });
    }
}

module.exports = Task;
