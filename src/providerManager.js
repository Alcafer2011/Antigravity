const vscode = require("vscode");
const https = require("https");

/**
 * Multi-Provider AI Model Manager
 * Manages multiple AI providers with automatic model discovery,
 * intelligent routing based on prompt complexity, and fallback handling
 */
class ProviderManager {
    constructor(context) {
        this.context = context;
        this.providers = new Map();
        this.availableModels = new Map();
        this.modelCapabilities = new Map();
        this.lastDiscovery = 0;
        this.discoveryInterval = 2 * 24 * 60 * 60 * 1000; // 2 days
        this.currentRouting = null;
        this.autoUpdateScheduler = null;
        this.providerStatus = new Map(); // Track provider health and limits
        
        this.initializeProviders();
        this.startAutoUpdateScheduler();
    }

    /**
     * Start automatic model update scheduler
     */
    startAutoUpdateScheduler() {
        // Update models every 2 days
        this.autoUpdateScheduler = setInterval(async () => {
            console.log('[ProviderManager] Auto-updating models...');
            try {
                await this.discoverModels();
                console.log('[ProviderManager] Model update completed');
            } catch (error) {
                console.error('[ProviderManager] Auto-update failed:', error);
            }
        }, this.discoveryInterval);
        
        // Initial discovery
        this.discoverModels().catch(error => {
            console.error('[ProviderManager] Initial discovery failed:', error);
        });
    }

    /**
     * Stop auto-update scheduler
     */
    stopAutoUpdateScheduler() {
        if (this.autoUpdateScheduler) {
            clearInterval(this.autoUpdateScheduler);
            this.autoUpdateScheduler = null;
        }
    }

    /**
     * Initialize all supported providers
     */
    initializeProviders() {
        this.providers.set("openrouter", {
            name: "OpenRouter",
            baseUrl: "https://openrouter.ai/api/v1",
            modelsEndpoint: "/models",
            chatEndpoint: "/chat/completions",
            hasFreeTier: true,
            status: "unknown"
        });

        this.providers.set("google", {
            name: "Google AI Studio",
            baseUrl: "https://generativelanguage.googleapis.com/v1beta",
            modelsEndpoint: "/models",
            chatEndpoint: "/generateContent",
            hasFreeTier: true,
            status: "unknown"
        });

        this.providers.set("groq", {
            name: "Groq",
            baseUrl: "https://api.groq.com/openai/v1",
            modelsEndpoint: "/models",
            chatEndpoint: "/chat/completions",
            hasFreeTier: true,
            status: "unknown"
        });

        this.providers.set("huggingface", {
            name: "Hugging Face",
            baseUrl: "https://api-inference.huggingface.co",
            modelsEndpoint: "/models",
            chatEndpoint: "/models/{model}/chat-completions",
            hasFreeTier: true,
            status: "unknown"
        });

        this.providers.set("cloudflare", {
            name: "Cloudflare Workers AI",
            baseUrl: "https://api.cloudflare.com/client/v4/accounts/{accountId}/ai/run",
            modelsEndpoint: "/models",
            chatEndpoint: "/{model}",
            hasFreeTier: true,
            status: "unknown"
        });
    }

    /**
     * Load API keys from VSCode secrets
     */
    async loadApiKeys() {
        const keys = {};
        
        try {
            keys.openrouter = await this.context.secrets.get("openrouterApiKey");
            keys.google = await this.context.secrets.get("googleApiKey");
            keys.groq = await this.context.secrets.get("groqApiKey");
            keys.huggingface = await this.context.secrets.get("huggingfaceApiKey");
            keys.cloudflareAccountId = await this.context.secrets.get("cloudflareAccountId");
            keys.cloudflareToken = await this.context.secrets.get("cloudflareToken");
        } catch (error) {
            console.error("Error loading API keys:", error);
        }
        
        return keys;
    }

    /**
     * Save API keys to VSCode secrets
     */
    async saveApiKeys(keys) {
        try {
            if (keys.openrouter) await this.context.secrets.store("openrouterApiKey", keys.openrouter);
            if (keys.google) await this.context.secrets.store("googleApiKey", keys.google);
            if (keys.groq) await this.context.secrets.store("groqApiKey", keys.groq);
            if (keys.huggingface) await this.context.secrets.store("huggingfaceApiKey", keys.huggingface);
            if (keys.cloudflareAccountId) await this.context.secrets.store("cloudflareAccountId", keys.cloudflareAccountId);
            if (keys.cloudflareToken) await this.context.secrets.store("cloudflareToken", keys.cloudflareToken);
        } catch (error) {
            console.error("Error saving API keys:", error);
            throw error;
        }
    }

    /**
     * Discover available free models from all providers
     */
    async discoverModels() {
        const keys = await this.loadApiKeys();
        const allModels = [];

        for (const [providerId, provider] of this.providers) {
            try {
                const models = await this.discoverProviderModels(providerId, provider, keys);
                allModels.push(...models);
                provider.status = "online";
            } catch (error) {
                console.error(`Error discovering models for ${provider.name}:`, error);
                provider.status = "offline";
            }
        }

        this.availableModels = new Map(allModels.map(m => [m.id, m]));
        this.lastDiscovery = Date.now();
        this.saveModelCache();

        return allModels;
    }

    /**
     * Discover models from a specific provider
     */
    async discoverProviderModels(providerId, provider, keys) {
        const models = [];
        const apiKey = keys[providerId] || keys[`${providerId}ApiKey`] || keys[`${providerId}Token`];

        if (!apiKey) {
            console.log(`No API key for ${provider.name}`);
            return models;
        }

        try {
            const providerModels = await this.fetchProviderModels(providerId, provider, apiKey, keys);
            
            for (const model of providerModels) {
                const modelInfo = {
                    id: `${providerId}:${model.id}`,
                    providerId: providerId,
                    providerName: provider.name,
                    name: model.name || model.id,
                    description: model.description || "",
                    isFree: this.isModelFree(model),
                    capabilities: this.assessModelCapabilities(model),
                    contextLength: model.context_length || 4096,
                    pricing: model.pricing || null
                };
                
                models.push(modelInfo);
                this.modelCapabilities.set(modelInfo.id, modelInfo.capabilities);
            }
        } catch (error) {
            console.error(`Error fetching models from ${provider.name}:`, error);
        }

        return models;
    }

    /**
     * Fetch models from provider API
     */
    async fetchProviderModels(providerId, provider, apiKey, keys) {
        return new Promise((resolve, reject) => {
            let url = provider.baseUrl + provider.modelsEndpoint;
            
            // Add API key to URL for Google
            if (providerId === "google") {
                url += `?key=${apiKey}`;
            }

            const options = {
                method: "GET",
                headers: {
                    "Content-Type": "application/json"
                }
            };

            // Add authorization header for providers that need it
            if (providerId === "openrouter" || providerId === "groq") {
                options.headers["Authorization"] = `Bearer ${apiKey}`;
            } else if (providerId === "huggingface") {
                options.headers["Authorization"] = `Bearer ${apiKey}`;
            } else if (providerId === "cloudflare") {
                options.headers["Authorization"] = `Bearer ${keys.cloudflareToken}`;
            }

            https.get(url, options, (res) => {
                let data = "";
                res.on("data", chunk => data += chunk);
                res.on("end", () => {
                    try {
                        const json = JSON.parse(data);
                        const models = this.parseModelsResponse(providerId, json);
                        resolve(models);
                    } catch (error) {
                        reject(error);
                    }
                });
            }).on("error", reject);
        });
    }

    /**
     * Parse models response from different providers
     */
    parseModelsResponse(providerId, response) {
        switch (providerId) {
            case "openrouter":
                return response.data || [];
            case "google":
                return response.models || [];
            case "groq":
                return response.data || [];
            case "huggingface":
                return Array.isArray(response) ? response : [];
            case "cloudflare":
                return response.success ? response.result || [] : [];
            default:
                return [];
        }
    }

    /**
     * Check if model is free
     */
    isModelFree(model) {
        // Check pricing information
        if (model.pricing) {
            const promptPrice = parseFloat(model.pricing.prompt || "0");
            const completionPrice = parseFloat(model.pricing.completion || "0");
            return promptPrice === 0 && completionPrice === 0;
        }

        // Check model name for free tier indicators
        const name = (model.name || model.id || "").toLowerCase();
        return name.includes("free") || name.includes("open") || name.includes("beta");
    }

    /**
     * Assess model capabilities based on name and metadata
     */
    assessModelCapabilities(model) {
        const name = (model.name || model.id || "").toLowerCase();
        const capabilities = {
            reasoning: 0,
            coding: 0,
            math: 0,
            context: 0,
            speed: 0
        };

        // Reasoning capability
        if (name.includes("gpt-4") || name.includes("claude-3") || name.includes("gemini-pro")) {
            capabilities.reasoning = 0.9;
        } else if (name.includes("gpt-3.5") || name.includes("claude-2")) {
            capabilities.reasoning = 0.7;
        }

        // Coding capability
        if (name.includes("coder") || name.includes("code") || name.includes("instruct")) {
            capabilities.coding = 0.9;
        } else if (name.includes("chat")) {
            capabilities.coding = 0.6;
        }

        // Math capability
        if (name.includes("math") || name.includes("reasoning")) {
            capabilities.math = 0.8;
        }

        // Context capability
        const contextLength = model.context_length || 4096;
        capabilities.context = Math.min(contextLength / 128000, 1);

        // Speed capability (inverse of model size)
        if (name.includes("7b") || name.includes("8b")) {
            capabilities.speed = 0.9;
        } else if (name.includes("13b") || name.includes("14b")) {
            capabilities.speed = 0.7;
        } else if (name.includes("70b") || name.includes("72b")) {
            capabilities.speed = 0.4;
        }

        return capabilities;
    }

    /**
     * Estimate prompt complexity (1-10 scale)
     */
    estimatePromptComplexity(prompt) {
        let complexity = 1;

        // Length factor
        complexity += Math.min(prompt.length / 500, 3);

        // Code presence
        if (prompt.includes("```") || prompt.includes("function") || prompt.includes("class")) {
            complexity += 2;
        }

        // Technical terms
        const technicalTerms = ["refactor", "architecture", "optimize", "debug", "deploy", "integration", "api", "database"];
        const termCount = technicalTerms.filter(term => prompt.toLowerCase().includes(term)).length;
        complexity += termCount * 0.5;

        // Complexity indicators
        if (prompt.toLowerCase().includes("massive") || prompt.toLowerCase().includes("complex") || prompt.toLowerCase().includes("large scale")) {
            complexity += 2;
        }

        return Math.min(Math.max(complexity, 1), 10);
    }

    /**
     * Intelligent routing based on prompt complexity and provider health
     */
    async routePrompt(prompt, preferredProvider = "auto", preferredModel = "auto") {
        // If specific provider and model are selected, use them
        if (preferredProvider !== "auto" && preferredModel !== "auto") {
            return await this.selectProviderModel(preferredProvider, preferredModel);
        }

        // If only provider is selected, auto-select model
        if (preferredProvider !== "auto") {
            const complexity = this.estimatePromptComplexity(prompt);
            return await this.selectBestModelForProvider(preferredProvider, complexity);
        }

        // If only model is selected, use it with best available provider
        if (preferredModel !== "auto") {
            return await this.selectBestProviderForModel(preferredModel);
        }

        // Full auto routing based on complexity and provider health
        const complexity = this.estimatePromptComplexity(prompt);
        
        // Refresh models if needed
        if (Date.now() - this.lastDiscovery > this.discoveryInterval) {
            await this.discoverModels();
        }

        // Select best provider and model based on complexity and health
        const selectedRoute = await this.selectBestRouteForComplexity(complexity);
        this.currentRouting = selectedRoute;

        return selectedRoute;
    }

    /**
     * Select best model for given complexity
     */
    selectBestModelForComplexity(complexity) {
        const freeModels = Array.from(this.availableModels.values()).filter(m => m.isFree);
        
        if (freeModels.length === 0) {
            // Fallback to any available model
            const allModels = Array.from(this.availableModels.values());
            if (allModels.length === 0) {
                throw new Error("No models available");
            }
            return allModels[0];
        }

        // Sort models by capability match for complexity and provider health
        freeModels.sort((a, b) => {
            const scoreA = this.calculateModelScore(a, complexity);
            const scoreB = this.calculateModelScore(b, complexity);
            const healthA = this.getProviderHealth(a.providerId);
            const healthB = this.getProviderHealth(b.providerId);
            
            // Combine model score with provider health
            const finalScoreA = scoreA * 0.7 + healthA * 0.3;
            const finalScoreB = scoreB * 0.7 + healthB * 0.3;
            
            return finalScoreB - finalScoreA;
        });

        return freeModels[0];
    }

    /**
     * Select best model for specific provider
     */
    async selectBestModelForProvider(providerId, complexity) {
        const providerModels = Array.from(this.availableModels.values())
            .filter(m => m.providerId === providerId && m.isFree);
        
        if (providerModels.length === 0) {
            // Fallback to any model from provider
            const allProviderModels = Array.from(this.availableModels.values())
                .filter(m => m.providerId === providerId);
            if (allProviderModels.length === 0) {
                throw new Error(`No models available for provider ${providerId}`);
            }
            return allProviderModels[0];
        }

        // Sort by capability match
        providerModels.sort((a, b) => {
            const scoreA = this.calculateModelScore(a, complexity);
            const scoreB = this.calculateModelScore(b, complexity);
            return scoreB - scoreA;
        });

        return providerModels[0];
    }

    /**
     * Select best provider for specific model
     */
    async selectBestProviderForModel(modelId) {
        const model = this.availableModels.get(modelId);
        if (!model) {
            throw new Error(`Model ${modelId} not found`);
        }

        // Check if model's provider is healthy
        const providerHealth = this.getProviderHealth(model.providerId);
        
        if (providerHealth > 0.5) {
            return model;
        }

        // Find alternative provider with similar model
        const alternativeModels = Array.from(this.availableModels.values())
            .filter(m => m.isFree && m.providerId !== model.providerId)
            .filter(m => this.areModelsSimilar(m, model));

        if (alternativeModels.length > 0) {
            // Select healthiest alternative
            alternativeModels.sort((a, b) => {
                const healthA = this.getProviderHealth(a.providerId);
                const healthB = this.getProviderHealth(b.providerId);
                return healthB - healthA;
            });
            return alternativeModels[0];
        }

        // Fallback to original model
        return model;
    }

    /**
     * Select specific provider and model
     */
    async selectProviderModel(providerId, modelId) {
        const model = this.availableModels.get(`${providerId}:${modelId}`);
        if (!model) {
            throw new Error(`Model ${modelId} not found for provider ${providerId}`);
        }

        // Check provider health and failover if needed
        const providerHealth = this.getProviderHealth(providerId);
        if (providerHealth < 0.3) {
            console.warn(`[ProviderManager] Provider ${providerId} unhealthy, attempting failover`);
            return await this.selectBestProviderForModel(`${providerId}:${modelId}`);
        }

        return model;
    }

    /**
     * Select best route (provider + model) for complexity
     */
    async selectBestRouteForComplexity(complexity) {
        const freeModels = Array.from(this.availableModels.values()).filter(m => m.isFree);
        
        if (freeModels.length === 0) {
            throw new Error("No free models available");
        }

        // Sort by combined score (model capability + provider health)
        freeModels.sort((a, b) => {
            const scoreA = this.calculateModelScore(a, complexity);
            const scoreB = this.calculateModelScore(b, complexity);
            const healthA = this.getProviderHealth(a.providerId);
            const healthB = this.getProviderHealth(b.providerId);
            
            // Weight model capability higher than provider health
            const finalScoreA = scoreA * 0.8 + healthA * 0.2;
            const finalScoreB = scoreB * 0.8 + healthB * 0.2;
            
            return finalScoreB - finalScoreA;
        });

        return freeModels[0];
    }

    /**
     * Get provider health score (0-1)
     */
    getProviderHealth(providerId) {
        const status = this.providerStatus.get(providerId);
        if (!status) {
            return 1.0; // Assume healthy if no status
        }

        // Calculate health based on recent errors and rate limits
        const errorRate = status.recentErrors / Math.max(status.totalRequests, 1);
        const rateLimitRemaining = status.rateLimitRemaining || 1;
        
        const healthScore = (1 - errorRate) * rateLimitRemaining;
        return Math.max(0, Math.min(1, healthScore));
    }

    /**
     * Update provider status
     */
    updateProviderStatus(providerId, status) {
        const currentStatus = this.providerStatus.get(providerId) || {
            totalRequests: 0,
            recentErrors: 0,
            rateLimitRemaining: 1,
            lastError: null
        };

        this.providerStatus.set(providerId, {
            ...currentStatus,
            ...status,
            totalRequests: (currentStatus.totalRequests || 0) + 1,
            recentErrors: status.error ? (currentStatus.recentErrors || 0) + 1 : 0,
            lastError: status.error || null,
            lastUpdate: Date.now()
        });
    }

    /**
     * Check if two models are similar
     */
    areModelsSimilar(model1, model2) {
        // Compare capabilities
        const caps1 = model1.capabilities;
        const caps2 = model2.capabilities;
        
        const capabilityDiff = 
            Math.abs(caps1.reasoning - caps2.reasoning) +
            Math.abs(caps1.coding - caps2.coding) +
            Math.abs(caps1.context - caps2.context);
        
        return capabilityDiff < 0.5; // Threshold for similarity
    }

    /**
     * Calculate model score for given complexity
     */
    calculateModelScore(model, complexity) {
        const caps = model.capabilities;
        
        // For low complexity, prefer speed
        if (complexity <= 3) {
            return caps.speed * 0.6 + caps.reasoning * 0.2 + caps.coding * 0.2;
        }
        // For medium complexity, balance all
        else if (complexity <= 7) {
            return caps.speed * 0.3 + caps.reasoning * 0.4 + caps.coding * 0.3;
        }
        // For high complexity, prefer reasoning and coding
        else {
            return caps.speed * 0.1 + caps.reasoning * 0.5 + caps.coding * 0.4;
        }
    }

    /**
     * Select specific model
     */
    selectModel(modelId) {
        const model = this.availableModels.get(modelId);
        if (!model) {
            throw new Error(`Model ${modelId} not found`);
        }
        this.currentRouting = model;
        return model;
    }

    /**
     * Get current routing info
     */
    getCurrentRouting() {
        return this.currentRouting;
    }

    /**
     * Get all available models
     */
    getAvailableModels() {
        return Array.from(this.availableModels.values());
    }

    /**
     * Get models grouped by provider
     */
    getModelsByProvider() {
        const grouped = {};
        for (const [modelId, model] of this.availableModels) {
            if (!grouped[model.providerId]) {
                grouped[model.providerId] = [];
            }
            grouped[model.providerId].push(model);
        }
        return grouped;
    }

    /**
     * Save model cache to disk
     */
    saveModelCache() {
        const cachePath = require("path").join(this.context.globalStorageUri.fsPath, "model_cache.json");
        try {
            const fs = require("fs");
            fs.writeFileSync(cachePath, JSON.stringify({
                models: Array.from(this.availableModels.entries()),
                lastDiscovery: this.lastDiscovery
            }));
        } catch (error) {
            console.error("Error saving model cache:", error);
        }
    }

    /**
     * Load model cache from disk
     */
    loadModelCache() {
        const cachePath = require("path").join(this.context.globalStorageUri.fsPath, "model_cache.json");
        try {
            const fs = require("fs");
            if (fs.existsSync(cachePath)) {
                const data = fs.readFileSync(cachePath, "utf8");
                const parsed = JSON.parse(data);
                this.availableModels = new Map(parsed.models);
                this.lastDiscovery = parsed.lastDiscovery || 0;
            }
        } catch (error) {
            console.error("Error loading model cache:", error);
        }
    }

    /**
     * Execute chat completion with selected model and automatic fallback
     */
    async executeChatCompletion(modelId, messages, options = {}, webview = null) {
        const model = this.availableModels.get(modelId);
        if (!model) {
            throw new Error(`Model ${modelId} not found`);
        }

        const provider = this.providers.get(model.providerId);
        const keys = await this.loadApiKeys();
        const apiKey = keys[model.providerId] || keys[`${model.providerId}ApiKey`] || keys[`${model.providerId}Token`];

        if (!apiKey) {
            throw new Error(`No API key for ${provider.name}`);
        }

        try {
            return await this.sendChatRequest(provider, model, apiKey, messages, options, keys);
        } catch (error) {
            // Log error to webview if available
            if (webview) {
                webview.postMessage({
                    type: 'addErrorToRawCode',
                    value: `[PROVIDER ERROR] Failed to call ${provider.name} with model ${model.name}: ${error.message}`
                });
            }
            
            console.error(`[ProviderManager] Error calling ${provider.name}:`, error);
            
            // Update provider status
            this.updateProviderStatus(model.providerId, {
                error: error.message,
                rateLimitRemaining: error.statusCode === 429 ? 0 : 1
            });

            // Try fallback to next best model
            const fallbackModel = await this.selectBestRouteForComplexity(5);
            if (fallbackModel && fallbackModel.id !== modelId) {
                console.log(`[ProviderManager] Fallback to ${fallbackModel.providerId}:${fallbackModel.name}`);
                
                if (webview) {
                    webview.postMessage({
                        type: 'addErrorToRawCode',
                        value: `[FALLBACK] Switching to ${fallbackModel.providerId}:${fallbackModel.name}`
                    });
                }
                
                const fallbackProvider = this.providers.get(fallbackModel.providerId);
                const fallbackApiKey = keys[fallbackModel.providerId] || keys[`${fallbackModel.providerId}ApiKey`] || keys[`${fallbackModel.providerId}Token`];
                
                if (fallbackApiKey) {
                    try {
                        return await this.sendChatRequest(fallbackProvider, fallbackModel, fallbackApiKey, messages, options, keys);
                    } catch (fallbackError) {
                        console.error(`[ProviderManager] Fallback also failed:`, fallbackError);
                        if (webview) {
                            webview.postMessage({
                                type: 'addErrorToRawCode',
                                value: `[FALLBACK ERROR] ${fallbackModel.providerId}:${fallbackModel.name} also failed: ${fallbackError.message}`
                            });
                        }
                        throw fallbackError;
                    }
                }
            }
            
            throw error;
        }
    }

    /**
     * Send chat request to provider
     */
    async sendChatRequest(provider, model, apiKey, messages, options, keys) {
        return new Promise((resolve, reject) => {
            let url = provider.baseUrl + provider.chatEndpoint;
            
            // Replace placeholders
            url = url.replace("{model}", model.name);
            url = url.replace("{accountId}", keys.cloudflareAccountId || "");

            // Add API key to URL for Google
            if (model.providerId === "google") {
                url += `?key=${apiKey}`;
            }

            const requestBody = {
                model: model.name,
                messages: messages,
                ...options
            };

            const requestOptions = {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            };

            // Add authorization header
            if (model.providerId === "openrouter" || model.providerId === "groq") {
                requestOptions.headers["Authorization"] = `Bearer ${apiKey}`;
            } else if (model.providerId === "huggingface") {
                requestOptions.headers["Authorization"] = `Bearer ${apiKey}`;
            } else if (model.providerId === "cloudflare") {
                requestOptions.headers["Authorization"] = `Bearer ${keys.cloudflareToken}`;
            }

            const req = https.request(url, requestOptions, (res) => {
                let data = "";
                
                // Handle HTTP errors
                if (res.statusCode >= 400) {
                    const error = new Error(`HTTP ${res.statusCode}: ${res.statusMessage}`);
                    error.statusCode = res.statusCode;
                    error.statusMessage = res.statusMessage;
                    reject(error);
                    return;
                }
                
                res.on("data", chunk => data += chunk);
                res.on("end", () => {
                    try {
                        const response = JSON.parse(data);
                        resolve(this.parseChatResponse(response, model.providerId));
                    } catch (error) {
                        reject(error);
                    }
                });
            });

            req.on("error", reject);
            req.write(JSON.stringify(requestBody));
            req.end();
        });
    }

    /**
     * Parse chat response from different providers
     */
    parseChatResponse(response, providerId) {
        switch (providerId) {
            case "openrouter":
            case "groq":
                return {
                    content: response.choices?.[0]?.message?.content || "",
                    usage: response.usage,
                    model: response.model
                };
            case "google":
                return {
                    content: response.candidates?.[0]?.content?.parts?.[0]?.text || "",
                    usage: response.usageMetadata,
                    model: response.model
                };
            case "huggingface":
                return {
                    content: Array.isArray(response) ? response[0]?.generated_text || "" : response.generated_text || "",
                    usage: null,
                    model: response.model
                };
            case "cloudflare":
                return {
                    content: response.result?.response || "",
                    usage: response.usage,
                    model: response.model
                };
            default:
                return {
                    content: "",
                    usage: null,
                    model: ""
                };
        }
    }

    /**
     * Get provider status
     */
    getProviderStatus() {
        const status = {};
        for (const [providerId, provider] of this.providers) {
            status[providerId] = {
                name: provider.name,
                status: provider.status,
                hasFreeTier: provider.hasFreeTier
            };
        }
        return status;
    }
}

module.exports = ProviderManager;
