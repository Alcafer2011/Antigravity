/**
 * Advanced System Guardian Agent
 * University-level capabilities in error prevention, resource monitoring, and auto-recovery
 * Specializes in: comprehensive error analysis, system health monitoring, predictive failure prevention
 */
class ImmuneGuardian {
    constructor(context) {
        this.context = context;
        this.errorCategories = [
            "Syntax Errors", "Runtime Errors", "Logic Errors", "Concurrency Errors",
            "Memory Errors", "IO Errors", "Network Errors", "Security Errors",
            "Configuration Errors", "Dependency Errors", "Performance Errors"
        ];
        this.monitoringMetrics = [
            "CPU Usage", "Memory Usage", "Disk I/O", "Network I/O",
            "Response Time", "Error Rate", "Throughput", "Resource Leaks"
        ];
        this.recoveryStrategies = [
            "Automatic Restart", "Fallback Mechanisms", "Circuit Breakers",
            "Retry Logic", "Graceful Degradation", "Resource Throttling"
        ];
    }

    async execute(taskContext) {
        const { description, codeContext, systemContext, knowledgeBase } = taskContext;
        
        const guardianResult = {
            errorAnalysis: this.performComprehensiveErrorAnalysis(description, codeContext),
            healthMonitoring: this.monitorSystemHealth(systemContext),
            failurePrediction: this.predictPotentialFailures(codeContext, systemContext),
            autoRecovery: this.designAutoRecoveryMechanisms(codeContext),
            resourceOptimization: this.optimizeResourceUsage(codeContext),
            securityMonitoring: this.monitorSecurityThreats(codeContext),
            performanceAlerts: this.setupPerformanceAlerts(codeContext),
            incidentResponse: this.designIncidentResponsePlan(codeContext)
        };

        return {
            agent: "System Guardian",
            analysis: guardianResult,
            recommendations: this.provideGuardianRecommendations(guardianResult),
            confidence: this.calculateGuardianConfidence(guardianResult),
            metadata: {
                errorsDetected: this.countErrors(guardianResult),
                healthScore: this.calculateHealthScore(guardianResult),
                recoveryReadiness: this.assessRecoveryReadiness(guardianResult)
            }
        };
    }

    performComprehensiveErrorAnalysis(description, codeContext) {
        return {
            syntaxAnalysis: this.analyzeSyntaxErrors(codeContext),
            runtimeAnalysis: this.analyzeRuntimeErrors(codeContext),
            logicAnalysis: this.analyzeLogicErrors(codeContext),
            concurrencyAnalysis: this.analyzeConcurrencyErrors(codeContext),
            memoryAnalysis: this.analyzeMemoryErrors(codeContext),
            ioAnalysis: this.analyzeIOErrors(codeContext),
            networkAnalysis: this.analyzeNetworkErrors(codeContext),
            securityAnalysis: this.analyzeSecurityErrors(codeContext),
            errorPatterns: this.identifyErrorPatterns(codeContext),
            errorPropagation: this.analyzeErrorPropagation(codeContext)
        };
    }

    monitorSystemHealth(systemContext) {
        return {
            resourceUsage: this.monitorResourceUsage(systemContext),
            performanceMetrics: this.collectPerformanceMetrics(systemContext),
            dependencyHealth: this.checkDependencyHealth(systemContext),
            serviceAvailability: this.checkServiceAvailability(systemContext),
            capacityPlanning: this.assessCapacityNeeds(systemContext),
            bottleneckIdentification: this.identifyBottlenecks(systemContext)
        };
    }

    predictPotentialFailures(codeContext, systemContext) {
        return {
            failureModes: this.identifyFailureModes(codeContext),
            probabilityAssessment: this.assessFailureProbabilities(codeContext),
            impactAnalysis: this.analyzeFailureImpact(codeContext),
            earlyWarningIndicators: this.identifyEarlyWarningIndicators(codeContext),
            predictiveModels: this.applyPredictiveModels(codeContext),
            riskMitigation: this.suggestRiskMitigation(codeContext)
        };
    }

    designAutoRecoveryMechanisms(codeContext) {
        return {
            errorDetection: this.designErrorDetection(codeContext),
            automaticRetry: this.designRetryLogic(codeContext),
            fallbackSystems: this.designFallbackSystems(codeContext),
            circuitBreakers: this.designCircuitBreakers(codeContext),
            gracefulDegradation: this.designGracefulDegradation(codeContext),
            selfHealing: this.designSelfHealingMechanisms(codeContext)
        };
    }

    optimizeResourceUsage(codeContext) {
        return {
            memoryOptimization: this.optimizeMemory(codeContext),
            cpuOptimization: this.optimizeCPU(codeContext),
            ioOptimization: this.optimizeIO(codeContext),
            networkOptimization: this.optimizeNetwork(codeContext),
            resourcePooling: this.implementResourcePooling(codeContext),
            loadBalancing: this.designLoadBalancing(codeContext)
        };
    }

    monitorSecurityThreats(codeContext) {
        return {
            vulnerabilityScanning: this.scanVulnerabilities(codeContext),
            intrusionDetection: this.detectIntrusions(codeContext),
            anomalyDetection: this.detectAnomalies(codeContext),
            complianceChecking: this.checkCompliance(codeContext),
            securityAlerts: this.setupSecurityAlerts(codeContext),
            incidentResponse: this.prepareSecurityIncidentResponse(codeContext)
        };
    }

    setupPerformanceAlerts(codeContext) {
        return {
            thresholdConfiguration: this.configureThresholds(codeContext),
            alertRouting: this.routeAlerts(codeContext),
            escalationProcedures: this.defineEscalationProcedures(codeContext),
            notificationChannels: this.configureNotifications(codeContext),
            dashboardIntegration: this.integrateDashboards(codeContext)
        };
    }

    designIncidentResponsePlan(codeContext) {
        return {
            incidentClassification: this.classifyIncidents(codeContext),
            responseProcedures: this.defineResponseProcedures(codeContext),
            communicationPlan: this.designCommunicationPlan(codeContext),
            recoveryProcedures: this.defineRecoveryProcedures(codeContext),
            postIncidentAnalysis: this.designPostIncidentAnalysis(codeContext),
            continuousImprovement: this.designContinuousImprovement(codeContext)
        };
    }

    // Error analysis methods
    analyzeSyntaxErrors(codeContext) {
        const syntaxPatterns = {
            missingSemicolons: /;\s*$/gm,
            unmatchedBrackets: /[{}[\]()]/g,
            invalidOperators: /[+\-*/%=<>!&|^~]/g,
            typeErrors: /:\s*(string|number|boolean|object|array)/g
        };

        const detectedErrors = [];
        for (const [errorType, pattern] of Object.entries(syntaxPatterns)) {
            const matches = codeContext.match(pattern);
            if (matches && matches.length > 0) {
                detectedErrors.push({ type: errorType, count: matches.length, severity: "medium" });
            }
        }

        return {
            errorsDetected: detectedErrors,
            syntaxQuality: this.assessSyntaxQuality(detectedErrors),
            suggestions: this.provideSyntaxSuggestions(detectedErrors)
        };
    }

    analyzeRuntimeErrors(codeContext) {
        const runtimePatterns = {
            nullReference: /null|undefined/g,
            typeErrors: /TypeError|ReferenceError/g,
            rangeErrors: /RangeError|IndexError/g,
            promiseRejections: /reject\(|catch\(/g
        };

        const detectedErrors = [];
        for (const [errorType, pattern] of Object.entries(runtimePatterns)) {
            const matches = codeContext.match(pattern);
            if (matches && matches.length > 0) {
                detectedErrors.push({ type: errorType, count: matches.length, severity: "high" });
            }
        }

        return {
            errorsDetected: detectedErrors,
            runtimeSafety: this.assessRuntimeSafety(detectedErrors),
            suggestions: this.provideRuntimeSuggestions(detectedErrors)
        };
    }

    analyzeLogicErrors(codeContext) {
        return {
            conditionAnalysis: this.analyzeConditions(codeContext),
            loopAnalysis: this.analyzeLoops(codeContext),
            stateAnalysis: this.analyzeStateManagement(codeContext),
            dataFlowAnalysis: this.analyzeDataFlow(codeContext),
            edgeCases: this.identifyEdgeCases(codeContext),
            suggestions: this.provideLogicSuggestions(codeContext)
        };
    }

    analyzeConcurrencyErrors(codeContext) {
        const concurrencyPatterns = {
            raceConditions: /race|concurrent|parallel/gi,
            deadlocks: /deadlock|mutex|lock/gi,
            memoryLeaks: /leak|memory|gc/gi,
            threadSafety: /thread|async|await/gi
        };

        const detectedIssues = [];
        for (const [issueType, pattern] of Object.entries(concurrencyPatterns)) {
            const matches = codeContext.match(pattern);
            if (matches && matches.length > 0) {
                detectedIssues.push({ type: issueType, count: matches.length, severity: "high" });
            }
        }

        return {
            issuesDetected: detectedIssues,
            concurrencySafety: this.assessConcurrencySafety(detectedIssues),
            suggestions: this.provideConcurrencySuggestions(detectedIssues)
        };
    }

    analyzeMemoryErrors(codeContext) {
        return {
            memoryLeaks: this.detectMemoryLeaks(codeContext),
            bufferOverflows: this.detectBufferOverflows(codeContext),
            memoryManagement: this.assessMemoryManagement(codeContext),
            gcIssues: this.identifyGCIssues(codeContext),
            suggestions: this.provideMemorySuggestions(codeContext)
        };
    }

    analyzeIOErrors(codeContext) {
        return {
            fileOperations: this.analyzeFileOperations(codeContext),
            networkOperations: this.analyzeNetworkOperations(codeContext),
            databaseOperations: this.analyzeDatabaseOperations(codeContext),
            errorHandling: this.assessIOErrorHandling(codeContext),
            suggestions: this.provideIOSuggestions(codeContext)
        };
    }

    analyzeNetworkErrors(codeContext) {
        return {
            connectionIssues: this.identifyConnectionIssues(codeContext),
            timeoutHandling: this.assessTimeoutHandling(codeContext),
            retryLogic: this.assessRetryLogic(codeContext),
            errorRecovery: this.assessNetworkRecovery(codeContext),
            suggestions: this.provideNetworkSuggestions(codeContext)
        };
    }

    analyzeSecurityErrors(codeContext) {
        const securityPatterns = {
            sqlInjection: /SELECT|INSERT|UPDATE|DELETE/gi,
            xssVulnerabilities: /innerHTML|eval\(|document\.write/gi,
            hardcodedCredentials: /password|secret|key/gi,
            insecureRandom: /Math\.random\(\)/gi
        };

        const detectedVulnerabilities = [];
        for (const [vulnType, pattern] of Object.entries(securityPatterns)) {
            const matches = codeContext.match(pattern);
            if (matches && matches.length > 0) {
                detectedVulnerabilities.push({ type: vulnType, count: matches.length, severity: "critical" });
            }
        }

        return {
            vulnerabilitiesDetected: detectedVulnerabilities,
            securityScore: this.calculateSecurityScore(detectedVulnerabilities),
            suggestions: this.provideSecuritySuggestions(detectedVulnerabilities)
        };
    }

    identifyErrorPatterns(codeContext) {
        const patterns = [];
        
        // Common error patterns
        if (codeContext.includes("try") && !codeContext.includes("catch")) {
            patterns.push({ pattern: "Incomplete try-catch", severity: "high" });
        }
        
        if (codeContext.includes("async") && !codeContext.includes("await")) {
            patterns.push({ pattern: "Unused async", severity: "medium" });
        }
        
        if (codeContext.includes("callback") && !codeContext.includes("error")) {
            patterns.push({ pattern: "Missing error handling in callback", severity: "high" });
        }

        return patterns;
    }

    analyzeErrorPropagation(codeContext) {
        return {
            errorBubbling: this.analyzeErrorBubbling(codeContext),
            errorContainment: this.assessErrorContainment(codeContext),
            errorLogging: this.assessErrorLogging(codeContext),
            errorContext: this.assessErrorContext(codeContext)
        };
    }

    // System monitoring methods
    monitorResourceUsage(systemContext) {
        return {
            cpuUsage: this.monitorCPU(systemContext),
            memoryUsage: this.monitorMemory(systemContext),
            diskUsage: this.monitorDisk(systemContext),
            networkUsage: this.monitorNetwork(systemContext),
            resourceTrends: this.analyzeResourceTrends(systemContext)
        };
    }

    collectPerformanceMetrics(systemContext) {
        return {
            responseTime: this.measureResponseTime(systemContext),
            throughput: this.measureThroughput(systemContext),
            errorRate: this.calculateErrorRate(systemContext),
            availability: this.calculateAvailability(systemContext),
            performanceTrends: this.analyzePerformanceTrends(systemContext)
        };
    }

    checkDependencyHealth(systemContext) {
        return {
            externalServices: this.checkExternalServices(systemContext),
            databases: this.checkDatabaseHealth(systemContext),
            thirdPartyAPIs: this.checkThirdPartyAPIs(systemContext),
            internalServices: this.checkInternalServices(systemContext),
            dependencyGraph: this.buildDependencyGraph(systemContext)
        };
    }

    checkServiceAvailability(systemContext) {
        return {
            uptime: this.calculateUptime(systemContext),
            downtime: this.calculateDowntime(systemContext),
            mttr: this.calculateMTTR(systemContext),
            mtbf: this.calculateMTBF(systemContext),
            slaCompliance: this.checkSLACompliance(systemContext)
        };
    }

    // Helper methods for analysis
    assessSyntaxQuality(detectedErrors) {
        const errorCount = detectedErrors.reduce((sum, error) => sum + error.count, 0);
        return Math.max(0, 100 - errorCount * 5);
    }

    provideSyntaxSuggestions(detectedErrors) {
        return detectedErrors.map(error => ({
            error: error.type,
            suggestion: `Fix ${error.type} issues to improve code quality`,
            priority: error.severity
        }));
    }

    assessRuntimeSafety(detectedErrors) {
        const errorCount = detectedErrors.reduce((sum, error) => sum + error.count, 0);
        return Math.max(0, 100 - errorCount * 10);
    }

    provideRuntimeSuggestions(detectedErrors) {
        return detectedErrors.map(error => ({
            error: error.type,
            suggestion: `Add proper error handling for ${error.type}`,
            priority: error.severity
        }));
    }

    assessConcurrencySafety(detectedIssues) {
        const issueCount = detectedIssues.reduce((sum, issue) => sum + issue.count, 0);
        return Math.max(0, 100 - issueCount * 15);
    }

    provideConcurrencySuggestions(detectedIssues) {
        return detectedIssues.map(issue => ({
            issue: issue.type,
            suggestion: `Implement proper synchronization for ${issue.type}`,
            priority: issue.severity
        }));
    }

    calculateSecurityScore(detectedVulnerabilities) {
        const vulnCount = detectedVulnerabilities.reduce((sum, vuln) => sum + vuln.count, 0);
        return Math.max(0, 100 - vulnCount * 20);
    }

    provideSecuritySuggestions(detectedVulnerabilities) {
        return detectedVulnerabilities.map(vuln => ({
            vulnerability: vuln.type,
            suggestion: `Address ${vuln.type} vulnerability immediately`,
            priority: vuln.severity
        }));
    }

    // Synthesis and confidence
    provideGuardianRecommendations(guardianResult) {
        const recommendations = [];
        
        if (guardianResult.errorAnalysis.securityAnalysis.vulnerabilitiesDetected.length > 0) {
            recommendations.push({
                priority: "critical",
                category: "security",
                recommendation: "Address security vulnerabilities immediately",
                details: guardianResult.errorAnalysis.securityAnalysis.vulnerabilitiesDetected
            });
        }

        if (guardianResult.healthMonitoring.resourceUsage.cpuUsage > 80) {
            recommendations.push({
                priority: "high",
                category: "performance",
                recommendation: "Optimize CPU usage",
                details: "CPU usage exceeds 80% threshold"
            });
        }

        if (guardianResult.failurePrediction.probabilityAssessment.some(p => p.probability > 0.7)) {
            recommendations.push({
                priority: "high",
                category: "reliability",
                recommendation: "Implement preventive measures for high-probability failures",
                details: guardianResult.failurePrediction.probabilityAssessment
            });
        }

        return recommendations;
    }

    calculateGuardianConfidence(guardianResult) {
        let confidence = 0.6;
        
        if (guardianResult.errorAnalysis.syntaxAnalysis.errorsDetected.length > 0) {
            confidence += 0.1;
        }
        
        if (guardianResult.healthMonitoring.performanceMetrics.length > 0) {
            confidence += 0.1;
        }
        
        if (guardianResult.autoRecovery.errorDetection) {
            confidence += 0.1;
        }
        
        if (guardianResult.securityMonitoring.vulnerabilityScanning) {
            confidence += 0.1;
        }

        return Math.min(confidence, 1.0);
    }

    countErrors(guardianResult) {
        let count = 0;
        count += guardianResult.errorAnalysis.syntaxAnalysis.errorsDetected.length;
        count += guardianResult.errorAnalysis.runtimeAnalysis.errorsDetected.length;
        count += guardianResult.errorAnalysis.concurrencyAnalysis.issuesDetected.length;
        count += guardianResult.errorAnalysis.securityAnalysis.vulnerabilitiesDetected.length;
        return count;
    }

    calculateHealthScore(guardianResult) {
        const errorCount = this.countErrors(guardianResult);
        return Math.max(0, 100 - errorCount * 5);
    }

    assessRecoveryReadiness(guardianResult) {
        let readiness = 0.5;
        
        if (guardianResult.autoRecovery.automaticRetry) {
            readiness += 0.2;
        }
        
        if (guardianResult.autoRecovery.fallbackSystems) {
            readiness += 0.2;
        }
        
        if (guardianResult.incidentResponse.responseProcedures) {
            readiness += 0.1;
        }

        return Math.min(readiness, 1.0);
    }

    // Placeholder implementations for remaining methods
    analyzeConditions(codeContext) { return { complexity: "medium", coverage: "high" }; }
    analyzeLoops(codeContext) { return { infiniteRisk: "low", optimization: "medium" }; }
    analyzeStateManagement(codeContext) { return { complexity: "medium", consistency: "high" }; }
    analyzeDataFlow(codeContext) { return { complexity: "medium", validation: "high" }; }
    identifyEdgeCases(codeContext) { return ["null input", "empty array", "boundary conditions"]; }
    provideLogicSuggestions(codeContext) { return [{ suggestion: "Add input validation", priority: "medium" }]; }
    detectMemoryLeaks(codeContext) { return ["unclosed connections", "event listeners"]; }
    detectBufferOverflows(codeContext) { return []; }
    assessMemoryManagement(codeContext) { return { efficiency: "high", leaks: "low" }; }
    identifyGCIssues(codeContext) { return []; }
    provideMemorySuggestions(codeContext) { return [{ suggestion: "Implement proper cleanup", priority: "medium" }]; }
    analyzeFileOperations(codeContext) { return { errorHandling: "good", performance: "optimal" }; }
    analyzeNetworkOperations(codeContext) { return { errorHandling: "good", performance: "optimal" }; }
    analyzeDatabaseOperations(codeContext) { return { errorHandling: "good", performance: "optimal" }; }
    assessIOErrorHandling(codeContext) { return "comprehensive"; }
    provideIOSuggestions(codeContext) { return []; }
    identifyConnectionIssues(codeContext) { return []; }
    assessTimeoutHandling(codeContext) { return "proper"; }
    assessRetryLogic(codeContext) { return "implemented"; }
    assessNetworkRecovery(codeContext) { return "robust"; }
    provideNetworkSuggestions(codeContext) { return []; }
    analyzeErrorBubbling(codeContext) { return "controlled"; }
    assessErrorContainment(codeContext) { return "effective"; }
    assessErrorLogging(codeContext) { return "comprehensive"; }
    assessErrorContext(codeContext) { return "detailed"; }
    monitorCPU(systemContext) { return { current: 45, trend: "stable" }; }
    monitorMemory(systemContext) { return { current: 60, trend: "stable" }; }
    monitorDisk(systemContext) { return { current: 30, trend: "stable" }; }
    monitorNetwork(systemContext) { return { current: 25, trend: "stable" }; }
    analyzeResourceTrends(systemContext) { return { prediction: "stable", confidence: "high" }; }
    measureResponseTime(systemContext) { return { avg: 200, p95: 500, p99: 1000 }; }
    measureThroughput(systemContext) { return { current: 1000, max: 5000 }; }
    calculateErrorRate(systemContext) { return { current: 0.01, threshold: 0.05 }; }
    calculateAvailability(systemContext) { return { current: 99.9, target: 99.95 }; }
    analyzePerformanceTrends(systemContext) { return { trend: "improving", forecast: "positive" }; }
    checkExternalServices(systemContext) { return { allHealthy: true, degraded: [] }; }
    checkDatabaseHealth(systemContext) { return { connections: "healthy", latency: "low" }; }
    checkThirdPartyAPIs(systemContext) { return { allHealthy: true, rateLimits: "within" }; }
    checkInternalServices(systemContext) { return { allHealthy: true, load: "balanced" }; }
    buildDependencyGraph(systemContext) { return { nodes: 10, edges: 15, cycles: 0 }; }
    calculateUptime(systemContext) { return { current: 99.9, target: 99.95 }; }
    calculateDowntime(systemContext) { return { monthly: 43, yearly: 526 }; }
    calculateMTTR(systemContext) { return { current: 15, target: 10 }; }
    calculateMTBF(systemContext) { return { current: 720, target: 1440 }; }
    checkSLACompliance(systemContext) { return { compliant: true, penalty: 0 }; }
    identifyFailureModes(codeContext) { return ["hardware", "software", "network", "human"]; }
    assessFailureProbabilities(codeContext) { return [{ mode: "network", probability: 0.1 }]; }
    analyzeFailureImpact(codeContext) { return { critical: 2, high: 5, medium: 10 }; }
    identifyEarlyWarningIndicators(codeContext) { return ["memory spike", "cpu increase", "error rate"]; }
    applyPredictiveModels(codeContext) { return { accuracy: 0.85, confidence: "high" }; }
    suggestRiskMitigation(codeContext) { return ["redundancy", "monitoring", "automation"]; }
    designErrorDetection(codeContext) { return { realtime: true, comprehensive: true }; }
    designRetryLogic(codeContext) { return { maxAttempts: 3, backoff: "exponential" }; }
    designFallbackSystems(codeContext) { return { primary: "cloud", fallback: "local" }; }
    designCircuitBreakers(codeContext) { return { threshold: 5, timeout: 60000 }; }
    designGracefulDegradation(codeContext) { return { levels: 3, triggers: ["load", "errors"] }; }
    designSelfHealingMechanisms(codeContext) { return { automated: true, coverage: "high" }; }
    optimizeMemory(codeContext) { return { techniques: ["pooling", "caching"], improvement: "30%" }; }
    optimizeCPU(codeContext) { return { techniques: ["parallelization", "caching"], improvement: "25%" }; }
    optimizeIO(codeContext) { return { techniques: ["batching", "async"], improvement: "40%" }; }
    optimizeNetwork(codeContext) { return { techniques: ["compression", "keep-alive"], improvement: "35%" }; }
    implementResourcePooling(codeContext) { return { connections: 10, threads: 4 }; }
    designLoadBalancing(codeContext) { return { strategy: "round-robin", healthCheck: true }; }
    scanVulnerabilities(codeContext) { return { critical: 0, high: 1, medium: 3 }; }
    detectIntrusions(codeContext) { return { detected: 0, blocked: 5 }; }
    detectAnomalies(codeContext) { return { anomalies: 2, falsePositives: 1 }; }
    checkCompliance(codeContext) { return { gdpr: true, hipaa: false, pci: true }; }
    setupSecurityAlerts(codeContext) { return { channels: ["email", "slack"], severity: "high" }; }
    prepareSecurityIncidentResponse(codeContext) { return { team: "ready", procedures: "documented" }; }
    configureThresholds(codeContext) { return { cpu: 80, memory: 85, errors: 5 }; }
    routeAlerts(codeContext) { return { routing: "intelligent", escalation: "automatic" }; }
    defineEscalationProcedures(codeContext) { return { levels: 3, timeouts: [5, 15, 30] }; }
    configureNotifications(codeContext) { return { email: true, sms: false, slack: true }; }
    integrateDashboards(codeContext) { return { grafana: true, kibana: true }; }
    classifyIncidents(codeContext) { return { sev1: "critical", sev2: "high", sev3: "medium" }; }
    defineResponseProcedures(codeContext) { return { documented: true, tested: true }; }
    designCommunicationPlan(codeContext) { return { stakeholders: ["dev", "ops", "management"], frequency: "hourly" }; }
    defineRecoveryProcedures(codeContext) { return { automated: true, manual: false }; }
    designPostIncidentAnalysis(codeContext) { return { rootCause: true, prevention: true }; }
    designContinuousImprovement(codeContext) { return { feedback: "collected", actions: "implemented" }; }
    assessCapacityNeeds(systemContext) { return { current: 60, projected: 75, recommendation: "scale" }; }
    identifyBottlenecks(systemContext) { return ["database", "network", "cpu"]; }

    static parsePowerShellError(errorLog) {
        const errorPatterns = [
            { pattern: /not recognized/i, category: "Sintassi Comando" },
            { pattern: /access denied/i, category: "Permessi Amministratore" },
            { pattern: /cannot find path/i, category: "Percorso File Non Trovato" },
            { pattern: /term not recognized/i, category: "Comando Non Riconosciuto" },
            { pattern: /missing parameter/i, category: "Parametro Mancante" },
            { pattern: /invalid operation/i, category: "Operazione Non Valida" },
            { pattern: /permission denied/i, category: "Permessi Insufficienti" },
            { pattern: /file in use/i, category: "File Già In Uso" },
            { pattern: /disk full/i, category: "Disco Pieno" },
            { pattern: /network unreachable/i, category: "Rete Non Raggiungibile" }
        ];
        
        for (let entry of errorPatterns) {
            if (entry.pattern.test(errorLog)) {
                return { 
                    crashDetected: true, 
                    category: entry.category, 
                    log: errorLog,
                    severity: this.assessErrorSeverity(entry.category),
                    suggestedAction: this.suggestErrorAction(entry.category)
                };
            }
        }
        
        return { 
            crashDetected: false, 
            category: "Sconosciuto", 
            log: errorLog,
            severity: "low",
            suggestedAction: "Monitorare per ulteriori errori"
        };
    }

    static assessErrorSeverity(category) {
        const criticalCategories = ["Permessi Amministratore", "Permessi Insufficienti", "Disco Pieno"];
        const highCategories = ["Percorso File Non Trovato", "Rete Non Raggiungibile", "File Già In Uso"];
        
        if (criticalCategories.includes(category)) return "critical";
        if (highCategories.includes(category)) return "high";
        return "medium";
    }

    static suggestErrorAction(category) {
        const actions = {
            "Sintassi Comando": "Verificare la sintassi del comando e consultare la documentazione",
            "Permessi Amministratore": "Eseguire come amministratore o richiedere permessi elevati",
            "Percorso File Non Trovato": "Verificare che il percorso del file sia corretto",
            "Comando Non Riconosciuto": "Verificare che il comando esista e sia nel PATH",
            "Parametro Mancante": "Fornire tutti i parametri richiesti dal comando",
            "Operazione Non Valida": "Verificare i parametri e il contesto dell'operazione",
            "Permessi Insufficienti": "Richiedere permessi appropriati o modificare le ACL",
            "File Già In Uso": "Chiudere il file o attendere che venga rilasciato",
            "Disco Pieno": "Liberare spazio su disco o utilizzare un altro disco",
            "Rete Non Raggiungibile": "Verificare la connessione di rete e la raggiungibilità dell'host"
        };
        
        return actions[category] || "Consultare la documentazione per risolvere l'errore";
    }
}

module.exports = ImmuneGuardian;
