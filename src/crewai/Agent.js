/**
 * CrewAI-Style Agent Class
 * Based on CrewAI Agent architecture with role, goal, backstory, tools, verbose, allow_delegation
 */
class Agent {
    constructor(config) {
        this.role = config.role;
        this.goal = config.goal;
        this.backstory = config.backstory || "";
        this.verbose = config.verbose !== false;
        this.allowDelegation = config.allowDelegation !== false;
        this.tools = config.tools || [];
        this.llm = config.llm || null;
        this.maxIter = config.maxIter || 25;
        this.maxRpm = config.maxRpm || null;
        this.maxExecutionTime = config.maxExecutionTime || null;
        this.memory = config.memory || false;
        this.cache = config.cache !== false;
        
        // Internal state
        this.tasks = [];
        this.delegatedTasks = [];
        this.executionHistory = [];
        this.performanceMetrics = {
            completedTasks: 0,
            averageExecutionTime: 0,
            successRate: 1.0,
            delegationCount: 0
        };
    }

    /**
     * Execute a task with this agent
     */
    async executeTask(task, context = {}) {
        const startTime = Date.now();
        
        try {
            // Prepare task context
            const taskContext = {
                ...context,
                agent: this,
                tools: this.tools,
                memory: this.memory ? context.memory : null
            };

            // Execute the task
            const result = await this._executeTaskImplementation(task, taskContext);
            
            // Update metrics
            const executionTime = Date.now() - startTime;
            this.performanceMetrics.completedTasks++;
            this.performanceMetrics.averageExecutionTime = 
                (this.performanceMetrics.averageExecutionTime * (this.performanceMetrics.completedTasks - 1) + executionTime) / 
                this.performanceMetrics.completedTasks;
            this.performanceMetrics.successRate = 
                (this.performanceMetrics.successRate * (this.performanceMetrics.completedTasks - 1) + 1) / 
                this.performanceMetrics.completedTasks;
            
            this.executionHistory.push({
                task: task.id,
                startTime,
                endTime: Date.now(),
                executionTime,
                success: true,
                result: result
            });

            if (this.verbose) {
                console.log(`[Agent ${this.role}] Task ${task.id} completed in ${executionTime}ms`);
            }

            return result;
        } catch (error) {
            const executionTime = Date.now() - startTime;
            this.performanceMetrics.completedTasks++;
            this.performanceMetrics.successRate = 
                (this.performanceMetrics.successRate * (this.performanceMetrics.completedTasks - 1) + 0) / 
                this.performanceMetrics.completedTasks;
            
            this.executionHistory.push({
                task: task.id,
                startTime,
                endTime: Date.now(),
                executionTime,
                success: false,
                error: error.message
            });

            if (this.verbose) {
                console.error(`[Agent ${this.role}] Task ${task.id} failed: ${error.message}`);
            }

            throw error;
        }
    }

    /**
     * Internal task execution implementation
     */
    async _executeTaskImplementation(task, context) {
        // Check if task should be delegated
        if (this.allowDelegation && this._shouldDelegate(task)) {
            return await this._delegateTask(task, context);
        }

        // Execute task with tools
        const toolsResults = await this._executeTools(task, context);
        
        // Generate response using LLM
        const response = await this._generateResponse(task, context, toolsResults);
        
        return response;
    }

    /**
     * Determine if task should be delegated
     */
    _shouldDelegate(task) {
        // Simple heuristic: delegate if task complexity is high
        return task.complexity > 7 || task.description.length > 500;
    }

    /**
     * Delegate task to another agent
     */
    async _delegateTask(task, context) {
        this.performanceMetrics.delegationCount++;
        
        if (this.verbose) {
            console.log(`[Agent ${this.role}] Delegating task ${task.id}`);
        }

        // Find appropriate agent for delegation
        const delegateAgent = this._findDelegateAgent(task, context);
        
        if (delegateAgent) {
            return await delegateAgent.executeTask(task, context);
        }

        // If no suitable delegate, execute ourselves
        return await this._executeTaskImplementation(task, context);
    }

    /**
     * Find appropriate agent for delegation
     */
    _findDelegateAgent(task, context) {
        // This would be implemented by the Crew to find appropriate delegate
        return context.crew?.findAgentForTask(task) || null;
    }

    /**
     * Execute tools for the task
     */
    async _executeTools(task, context) {
        const results = [];
        
        for (const tool of this.tools) {
            try {
                const result = await tool.execute(task, context);
                results.push({ tool: tool.name, result });
                
                if (this.verbose) {
                    console.log(`[Agent ${this.role}] Tool ${tool.name} executed`);
                }
            } catch (error) {
                if (this.verbose) {
                    console.error(`[Agent ${this.role}] Tool ${tool.name} failed: ${error.message}`);
                }
                results.push({ tool: tool.name, error: error.message });
            }
        }
        
        return results;
    }

    /**
     * Generate response using LLM
     */
    async _generateResponse(task, context, toolsResults) {
        if (!this.llm) {
            throw new Error('No LLM configured for agent');
        }

        const prompt = this._buildPrompt(task, context, toolsResults);
        
        const response = await this.llm.complete(prompt, {
            temperature: 0.7,
            maxTokens: 2000
        });

        return response;
    }

    /**
     * Build prompt for LLM
     */
    _buildPrompt(task, context, toolsResults) {
        let prompt = `Role: ${this.role}\n`;
        prompt += `Goal: ${this.goal}\n`;
        prompt += `Backstory: ${this.backstory}\n\n`;
        
        prompt += `Task: ${task.description}\n`;
        if (task.expectedOutput) {
            prompt += `Expected Output: ${task.expectedOutput}\n`;
        }
        
        if (toolsResults.length > 0) {
            prompt += `\nTool Results:\n`;
            for (const toolResult of toolsResults) {
                prompt += `- ${toolResult.tool}: ${JSON.stringify(toolResult.result || toolResult.error)}\n`;
            }
        }
        
        return prompt;
    }

    /**
     * Get agent status
     */
    getStatus() {
        return {
            role: this.role,
            goal: this.goal,
            tasksCompleted: this.performanceMetrics.completedTasks,
            averageExecutionTime: this.performanceMetrics.averageExecutionTime,
            successRate: this.performanceMetrics.successRate,
            delegationCount: this.performanceMetrics.delegationCount,
            currentTasks: this.tasks.length,
            delegatedTasks: this.delegatedTasks.length
        };
    }

    /**
     * Reset agent state
     */
    reset() {
        this.tasks = [];
        this.delegatedTasks = [];
        this.executionHistory = [];
        this.performanceMetrics = {
            completedTasks: 0,
            averageExecutionTime: 0,
            successRate: 1.0,
            delegationCount: 0
        };
    }
}

module.exports = Agent;
