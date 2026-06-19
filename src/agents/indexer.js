/**
 * Advanced Project Indexer Agent
 * University-level capabilities in project indexing, dependency analysis, and codebase mapping
 * Specializes in: automatic project indexing, dependency graph generation, real-time file tracking
 */
class Indexer {
    constructor(context) {
        this.context = context;
        this.vscode = context.vscode || require('vscode');
        this.fs = require('fs');
        this.path = require('path');
        
        this.indexingCapabilities = [
            "Automatic File Discovery", "Dependency Analysis", "Import/Export Mapping",
            "Function/Class Extraction", "Real-time File Watching", "Incremental Indexing",
            "Large-scale Indexing", "Code Structure Analysis", "Call Graph Generation"
        ];
        
        this.projectIndex = new Map();
        this.dependencyGraph = new Map();
        this.callGraph = new Map();
        this.fileWatcher = null;
        this.indexingInProgress = false;
    }

    async execute(taskContext) {
        const { description, codeContext, systemContext, knowledgeBase } = taskContext;
        
        const indexingResult = {
            projectIndexing: this.indexProject(systemContext?.workspaceRoot),
            dependencyAnalysis: this.analyzeDependencies(),
            callGraphGeneration: this.generateCallGraph(),
            structureAnalysis: this.analyzeCodeStructure(),
            incrementalUpdate: this.setupIncrementalUpdates(),
            exportMapping: this.mapExports(),
            importMapping: this.mapImports()
        };

        return {
            agent: "Project Indexer",
            result: indexingResult,
            indexData: this.synthesizeIndexData(indexingResult),
            recommendations: this.provideIndexingRecommendations(indexingResult),
            confidence: this.calculateIndexingConfidence(indexingResult),
            metadata: {
                filesIndexed: this.projectIndex.size,
                dependenciesFound: this.dependencyGraph.size,
                callsTracked: this.callGraph.size,
                indexingTime: this.lastIndexingTime
            }
        };
    }

    async indexProject(workspaceRoot) {
        if (!workspaceRoot) {
            workspaceRoot = this.vscode.workspace.rootPath;
        }
        
        if (!workspaceRoot) {
            return { error: "No workspace root found" };
        }

        this.indexingInProgress = true;
        const startTime = Date.now();
        
        try {
            // Clear existing index
            this.projectIndex.clear();
            this.dependencyGraph.clear();
            this.callGraph.clear();

            // Index directory recursively
            await this.indexDirectory(workspaceRoot, "");
            
            // Analyze dependencies after indexing
            await this.analyzeDependencies();
            
            // Generate call graph
            await this.generateCallGraph();
            
            // Save index to file
            await this.saveIndexToFile();
            
            this.lastIndexingTime = Date.now() - startTime;
            
            return {
                success: true,
                filesIndexed: this.projectIndex.size,
                timeElapsed: this.lastIndexingTime
            };
            
        } catch (error) {
            console.error("Indexing error:", error);
            return { error: error.message };
        } finally {
            this.indexingInProgress = false;
        }
    }

    async indexDirectory(dir, relativePath) {
        try {
            const items = this.fs.readdirSync(dir);
            
            for (const item of items) {
                const fullPath = this.path.join(dir, item);
                const relativeItemPath = this.path.join(relativePath, item);
                const stats = this.fs.statSync(fullPath);

                if (stats.isDirectory()) {
                    // Skip common directories
                    if (!["node_modules", ".git", "dist", "build", "coverage", ".vscode", "bin", "obj"].includes(item)) {
                        await this.indexDirectory(fullPath, relativeItemPath);
                    }
                } else if (stats.isFile()) {
                    // Index file
                    await this.indexFile(fullPath, relativeItemPath, stats);
                }
            }
        } catch (error) {
            console.error(`Error indexing ${dir}:`, error);
        }
    }

    async indexFile(fullPath, relativePath, stats) {
        const ext = this.path.extname(relativePath).toLowerCase();
        const codeExtensions = [".js", ".ts", ".jsx", ".tsx", ".py", ".java", ".cpp", ".c", ".cs", ".go", ".rs", ".php", ".rb", ".vue", ".svelte"];
        
        if (codeExtensions.includes(ext)) {
            const content = this.fs.readFileSync(fullPath, "utf8");
            
            const fileInfo = {
                path: fullPath,
                relativePath: relativePath,
                extension: ext,
                size: stats.size,
                modified: stats.mtime,
                indexed: Date.now(),
                dependencies: [],
                imports: [],
                exports: [],
                functions: [],
                classes: [],
                lines: content.split('\n').length
            };
            
            // Extract functions and classes
            this.extractCodeStructure(content, fileInfo);
            
            this.projectIndex.set(relativePath, fileInfo);
        }
    }

    extractCodeStructure(content, fileInfo) {
        const ext = fileInfo.extension;
        
        if (ext === '.js' || ext === '.ts' || ext === '.jsx' || ext === '.tsx') {
            // Extract functions
            const functionRegex = /(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))/g;
            let match;
            while ((match = functionRegex.exec(content)) !== null) {
                const funcName = match[1] || match[2];
                if (funcName) fileInfo.functions.push(funcName);
            }
            
            // Extract classes
            const classRegex = /class\s+(\w+)/g;
            while ((match = classRegex.exec(content)) !== null) {
                fileInfo.classes.push(match[1]);
            }
            
            // Extract exports
            const exportRegex = /export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)/g;
            while ((match = exportRegex.exec(content)) !== null) {
                fileInfo.exports.push(match[1]);
            }
            
        } else if (ext === '.py') {
            // Extract functions
            const functionRegex = /def\s+(\w+)/g;
            while ((match = functionRegex.exec(content)) !== null) {
                fileInfo.functions.push(match[1]);
            }
            
            // Extract classes
            const classRegex = /class\s+(\w+)/g;
            while ((match = classRegex.exec(content)) !== null) {
                fileInfo.classes.push(match[1]);
            }
        }
    }

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
                const content = this.fs.readFileSync(fileInfo.path, "utf8");
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

    async generateCallGraph() {
        for (const [filePath, fileInfo] of this.projectIndex) {
            try {
                const content = this.fs.readFileSync(fileInfo.path, "utf8");
                
                // Track function calls
                for (const func of fileInfo.functions) {
                    const callPattern = new RegExp(`\\b${func}\\s*\\(`, 'g');
                    const matches = content.match(callPattern);
                    if (matches) {
                        if (!this.callGraph.has(filePath)) {
                            this.callGraph.set(filePath, []);
                        }
                        this.callGraph.get(filePath).push({
                            function: func,
                            callCount: matches.length
                        });
                    }
                }
            } catch (error) {
                console.error(`Error generating call graph for ${filePath}:`, error);
            }
        }
    }

    async analyzeCodeStructure() {
        const structure = {
            totalFiles: this.projectIndex.size,
            totalLines: 0,
            totalFunctions: 0,
            totalClasses: 0,
            fileTypes: {},
            averageFileSize: 0,
            largestFiles: []
        };

        for (const [filePath, fileInfo] of this.projectIndex) {
            structure.totalLines += fileInfo.lines;
            structure.totalFunctions += fileInfo.functions.length;
            structure.totalClasses += fileInfo.classes.length;
            structure.averageFileSize += fileInfo.size;
            
            // Count file types
            if (!structure.fileTypes[fileInfo.extension]) {
                structure.fileTypes[fileInfo.extension] = 0;
            }
            structure.fileTypes[fileInfo.extension]++;
            
            // Track largest files
            structure.largestFiles.push({
                path: filePath,
                size: fileInfo.size,
                lines: fileInfo.lines
            });
        }

        if (this.projectIndex.size > 0) {
            structure.averageFileSize = Math.round(structure.averageFileSize / this.projectIndex.size);
        }

        // Sort largest files
        structure.largestFiles.sort((a, b) => b.size - a.size);
        structure.largestFiles = structure.largestFiles.slice(0, 10);

        return structure;
    }

    async setupIncrementalUpdates() {
        if (this.fileWatcher) {
            this.fileWatcher.dispose();
        }

        const workspaceRoot = this.vscode.workspace.rootPath;
        if (!workspaceRoot) return { error: "No workspace root" };

        // Create file system watcher
        this.fileWatcher = this.vscode.workspace.createFileSystemWatcher(
            '**/*.{js,ts,jsx,tsx,py,java,cpp,c,cs,go,rs,php,rb,vue,svelte}'
        );

        this.fileWatcher.onDidChange(async (uri) => {
            await this.updateFileIndex(uri.fsPath);
        });

        this.fileWatcher.onDidCreate(async (uri) => {
            await this.updateFileIndex(uri.fsPath);
        });

        this.fileWatcher.onDidDelete(async (uri) => {
            await this.removeFileIndex(uri.fsPath);
        });

        return { success: true, message: "Incremental updates enabled" };
    }

    async updateFileIndex(filePath) {
        const relativePath = this.path.relative(this.vscode.workspace.rootPath, filePath);
        const stats = this.fs.statSync(filePath);
        
        if (this.projectIndex.has(relativePath)) {
            // Update existing file
            await this.indexFile(filePath, relativePath, stats);
        } else {
            // Add new file
            await this.indexFile(filePath, relativePath, stats);
        }
        
        await this.saveIndexToFile();
    }

    async removeFileIndex(filePath) {
        const relativePath = this.path.relative(this.vscode.workspace.rootPath, filePath);
        this.projectIndex.delete(relativePath);
        await this.saveIndexToFile();
    }

    async saveIndexToFile() {
        const workspaceRoot = this.vscode.workspace.rootPath;
        if (!workspaceRoot) return;

        const indexPath = this.path.join(workspaceRoot, "PROJECT_INDEX.json");
        
        const indexData = {
            version: "1.0.0",
            lastUpdated: new Date().toISOString(),
            projectRoot: workspaceRoot,
            files: {},
            dependencies: {},
            callGraph: {}
        };

        // Convert Maps to objects
        for (const [filePath, fileInfo] of this.projectIndex) {
            indexData.files[filePath] = fileInfo;
        }

        for (const [dep, files] of this.dependencyGraph) {
            indexData.dependencies[dep] = files;
        }

        for (const [filePath, calls] of this.callGraph) {
            indexData.callGraph[filePath] = calls;
        }

        try {
            this.fs.writeFileSync(indexPath, JSON.stringify(indexData, null, 2));
        } catch (error) {
            console.error("Failed to save index:", error);
        }
    }

    async loadIndexFromFile() {
        const workspaceRoot = this.vscode.workspace.rootPath;
        if (!workspaceRoot) return;

        const indexPath = this.path.join(workspaceRoot, "PROJECT_INDEX.json");
        
        try {
            if (this.fs.existsSync(indexPath)) {
                const content = this.fs.readFileSync(indexPath, "utf8");
                const indexData = JSON.parse(content);
                
                // Restore Maps
                for (const [filePath, fileInfo] of Object.entries(indexData.files)) {
                    this.projectIndex.set(filePath, fileInfo);
                }
                
                for (const [dep, files] of Object.entries(indexData.dependencies)) {
                    this.dependencyGraph.set(dep, files);
                }
                
                for (const [filePath, calls] of Object.entries(indexData.callGraph)) {
                    this.callGraph.set(filePath, calls);
                }
                
                return { success: true, loaded: true };
            }
        } catch (error) {
            console.error("Failed to load index:", error);
        }
        
        return { success: true, loaded: false };
    }

    mapExports() {
        const exports = {};
        for (const [filePath, fileInfo] of this.projectIndex) {
            if (fileInfo.exports.length > 0) {
                exports[filePath] = fileInfo.exports;
            }
        }
        return exports;
    }

    mapImports() {
        const imports = {};
        for (const [filePath, fileInfo] of this.projectIndex) {
            if (fileInfo.imports.length > 0) {
                imports[filePath] = fileInfo.imports;
            }
        }
        return imports;
    }

    synthesizeIndexData(indexingResult) {
        return {
            projectIndex: Array.from(this.projectIndex.entries()),
            dependencyGraph: Array.from(this.dependencyGraph.entries()),
            callGraph: Array.from(this.callGraph.entries()),
            structure: indexingResult.structureAnalysis,
            exports: indexingResult.exportMapping,
            imports: indexingResult.importMapping
        };
    }

    provideIndexingRecommendations(indexingResult) {
        const recommendations = [];
        
        if (this.projectIndex.size === 0) {
            recommendations.push({
                priority: "high",
                action: "No files indexed - check workspace configuration"
            });
        }
        
        if (!this.fileWatcher) {
            recommendations.push({
                priority: "medium",
                action: "Enable file watcher for real-time updates"
            });
        }
        
        return recommendations;
    }

    calculateIndexingConfidence(indexingResult) {
        let confidence = 0.5;
        
        if (this.projectIndex.size > 0) confidence += 0.2;
        if (this.dependencyGraph.size > 0) confidence += 0.1;
        if (this.callGraph.size > 0) confidence += 0.1;
        if (this.fileWatcher) confidence += 0.1;
        
        return Math.min(confidence, 1.0);
    }

    dispose() {
        if (this.fileWatcher) {
            this.fileWatcher.dispose();
            this.fileWatcher = null;
        }
    }
}

module.exports = Indexer;
