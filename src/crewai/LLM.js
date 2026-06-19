/**
 * CrewAI-Style LLM Class
 * Based on CrewAI LLM architecture for language model interactions
 */
class LLM {
    constructor(config) {
        this.model = config.model;
        this.temperature = config.temperature || 0.7;
        this.maxTokens = config.maxTokens || 2000;
        this.topP = config.topP || 1.0;
        this.frequencyPenalty = config.frequencyPenalty || 0;
        this.presencePenalty = config.presencePenalty || 0;
        this.stop = config.stop || null;
        this.apiKey = config.apiKey || null;
        this.apiBase = config.apiBase || null;
        
        // Usage tracking
        this.totalTokensUsed = 0;
        this.totalCost = 0;
        this.requestCount = 0;
    }

    /**
     * Complete a prompt
     */
    async complete(prompt, options = {}) {
        const opts = {
            temperature: options.temperature !== undefined ? options.temperature : this.temperature,
            maxTokens: options.maxTokens !== undefined ? options.maxTokens : this.maxTokens,
            topP: options.topP !== undefined ? options.topP : this.topP,
            frequencyPenalty: options.frequencyPenalty !== undefined ? options.frequencyPenalty : this.frequencyPenalty,
            presencePenalty: options.presencePenalty !== undefined ? options.presencePenalty : this.presencePenalty,
            stop: options.stop !== undefined ? options.stop : this.stop
        };

        try {
            const response = await this._makeRequest(prompt, opts);
            
            // Track usage
            this.totalTokensUsed += response.tokensUsed || 0;
            this.totalCost += response.cost || 0;
            this.requestCount++;
            
            return response.text;
        } catch (error) {
            throw new Error(`LLM completion failed: ${error.message}`);
        }
    }

    /**
     * Make request to LLM API
     */
    async _makeRequest(prompt, options) {
        // This is a placeholder - actual implementation depends on the LLM provider
        // For now, return a mock response
        return {
            text: "Mock LLM response - implement actual API call",
            tokensUsed: prompt.length + 100,
            cost: 0.001
        };
    }

    /**
     * Chat completion
     */
    async chat(messages, options = {}) {
        const prompt = this._messagesToString(messages);
        return await this.complete(prompt, options);
    }

    /**
     * Convert messages to string
     */
    _messagesToString(messages) {
        return messages.map(msg => `${msg.role}: ${msg.content}`).join('\n');
    }

    /**
     * Get usage statistics
     */
    getUsage() {
        return {
            totalTokensUsed: this.totalTokensUsed,
            totalCost: this.totalCost,
            requestCount: this.requestCount,
            averageTokensPerRequest: this.requestCount > 0 ? this.totalTokensUsed / this.requestCount : 0
        };
    }

    /**
     * Reset usage statistics
     */
    resetUsage() {
        this.totalTokensUsed = 0;
        this.totalCost = 0;
        this.requestCount = 0;
    }

    /**
     * Clone LLM
     */
    clone() {
        return new LLM({
            model: this.model,
            temperature: this.temperature,
            maxTokens: this.maxTokens,
            topP: this.topP,
            frequencyPenalty: this.frequencyPenalty,
            presencePenalty: this.presencePenalty,
            stop: this.stop,
            apiKey: this.apiKey,
            apiBase: this.apiBase
        });
    }
}

module.exports = LLM;
