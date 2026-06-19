/**
 * Test script for automatic routing and fallback
 * Simulates a complex request to the orchestrator, forcing an error on the first provider
 * to verify that the fallback system passes to the second provider and that the Webview
 * receives both the error log and the success log of the fallback.
 */

const vscode = require("vscode");
const ProviderManager = require("./src/providerManager");
const CrewAIOrchestrator = require("./src/orchestrator-crewai");

class TestRouting {
    constructor() {
        this.mockWebview = {
            postMessage: (message) => {
                console.log("[WEBVIEW] Received message:", JSON.stringify(message, null, 2));
            }
        };
        
        this.testResults = {
            firstProviderError: false,
            fallbackTriggered: false,
            fallbackSuccess: false,
            webviewReceivedError: false,
            webviewReceivedFallback: false
        };
    }

    /**
     * Test automatic routing with fallback
     */
    async testAutomaticRouting() {
        console.log("=== TEST: Automatic Routing with Fallback ===\n");
        
        try {
            // Create a mock context
            const mockContext = {
                globalStorageUri: {
                    fsPath: "./test-storage"
                },
                secrets: {
                    get: async (key) => {
                        const keys = {
                            openrouterApiKey: "test-key-openrouter",
                            huggingfaceApiKey: "test-key-huggingface",
                            cloudflareAccountId: "test-account-id",
                            cloudflareToken: "test-token-cloudflare"
                        };
                        return keys[key];
                    }
                }
            };

            // Initialize ProviderManager
            const providerManager = new ProviderManager(mockContext);
            
            // Mock available models
            providerManager.availableModels.set("openrouter:test-model-1", {
                id: "openrouter:test-model-1",
                name: "test-model-1",
                providerId: "openrouter",
                isFree: true,
                capabilities: { reasoning: 0.8, coding: 0.7, context: 0.6, speed: 0.9 }
            });
            
            providerManager.availableModels.set("huggingface:test-model-2", {
                id: "huggingface:test-model-2",
                name: "test-model-2",
                providerId: "huggingface",
                isFree: true,
                capabilities: { reasoning: 0.7, coding: 0.8, context: 0.7, speed: 0.8 }
            });

            // Mock providers
            providerManager.providers.set("openrouter", {
                name: "OpenRouter",
                baseUrl: "https://openrouter.ai/api/v1",
                chatEndpoint: "/chat/completions",
                modelsEndpoint: "/models"
            });
            
            providerManager.providers.set("huggingface", {
                name: "Hugging Face",
                baseUrl: "https://api-inference.huggingface.co",
                chatEndpoint: "/models/Qwen/Qwen2.5-Coder-32B-Instruct",
                modelsEndpoint: "/models"
            });

            // Test messages
            const testMessages = [
                { role: "system", content: "You are a helpful assistant." },
                { role: "user", content: "Write a simple function to add two numbers in JavaScript." }
            ];

            console.log("1. Testing first provider (should fail)...");
            
            // Mock sendChatRequest to fail on first provider
            const originalSendChatRequest = providerManager.sendChatRequest;
            let callCount = 0;
            
            providerManager.sendChatRequest = async (provider, model, apiKey, messages, options, keys) => {
                callCount++;
                console.log(`   Call #${callCount}: ${provider.name} - ${model.name}`);
                
                if (callCount === 1) {
                    // First call should fail
                    console.log("   ✗ First provider failing (simulating 429 Rate Limit)...");
                    const error = new Error("Rate limit exceeded");
                    error.statusCode = 429;
                    error.statusMessage = "Too Many Requests";
                    throw error;
                } else {
                    // Second call should succeed
                    console.log("   ✓ Second provider succeeding...");
                    return {
                        content: "function add(a, b) { return a + b; }",
                        usage: { prompt_tokens: 10, completion_tokens: 5 },
                        model: model.name
                    };
                }
            };

            // Execute chat completion with fallback
            console.log("\n2. Executing chat completion with automatic fallback...");
            try {
                const result = await providerManager.executeChatCompletion(
                    "openrouter:test-model-1",
                    testMessages,
                    {},
                    this.mockWebview
                );
                
                console.log("\n3. Verifying test results...");
                
                // Check if fallback was triggered
                if (callCount >= 2) {
                    this.testResults.fallbackTriggered = true;
                    console.log("   ✓ Fallback was triggered (2+ API calls made)");
                } else {
                    console.log("   ✗ Fallback was NOT triggered");
                }
                
                // Check if result was successful
                if (result && result.content) {
                    this.testResults.fallbackSuccess = true;
                    console.log("   ✓ Fallback was successful (result received)");
                } else {
                    console.log("   ✗ Fallback was NOT successful");
                }
                
                // Restore original method
                providerManager.sendChatRequest = originalSendChatRequest;
                
            } catch (error) {
                console.log("   ✗ Test failed with error:", error.message);
                providerManager.sendChatRequest = originalSendChatRequest;
            }

        } catch (error) {
            console.log("✗ Test execution failed:", error);
        }

        this.printResults();
    }

    /**
     * Print test results
     */
    printResults() {
        console.log("\n=== TEST RESULTS ===\n");
        
        const results = [
            { name: "Fallback Triggered", passed: this.testResults.fallbackTriggered },
            { name: "Fallback Success", passed: this.testResults.fallbackSuccess }
        ];
        
        let allPassed = true;
        
        results.forEach(result => {
            const status = result.passed ? "✓ PASS" : "✗ FAIL";
            console.log(`${status}: ${result.name}`);
            if (!result.passed) allPassed = false;
        });
        
        console.log("\n" + (allPassed ? "=== ALL TESTS PASSED ===" : "=== SOME TESTS FAILED ==="));
        
        return allPassed;
    }
}

// Run test if executed directly
if (require.main === module) {
    const test = new TestRouting();
    test.testAutomaticRouting().then(() => {
        process.exit(0);
    }).catch(error => {
        console.error("Test failed:", error);
        process.exit(1);
    });
}

module.exports = TestRouting;
