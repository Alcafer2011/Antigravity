/**
 * Tab Autocomplete Module
 * Provides AI-powered code completion suggestions similar to Continue
 * Simplified implementation without complex Next Edit features
 */

const vscode = require('vscode');

class AutocompleteManager {
    constructor(context, providerManager) {
        this.context = context;
        this.providerManager = providerManager;
        this.enabled = true;
        this.debounceTimer = null;
        this.debounceDelay = 300; // ms
        
        this.initialize();
    }

    initialize() {
        // Register completion item provider
        const provider = vscode.languages.registerCompletionItemProvider(
            { pattern: '**' },
            this.provideCompletionItems.bind(this),
            '\t' // Trigger on tab
        );

        this.context.subscriptions.push(provider);

        // Listen to configuration changes
        vscode.workspace.onDidChangeConfiguration(event => {
            if (event.affectsConfiguration('antigravity.enableAutocomplete')) {
                this.enabled = vscode.workspace.getConfiguration('antigravity').get('enableAutocomplete', true);
            }
        });

        this.enabled = vscode.workspace.getConfiguration('antigravity').get('enableAutocomplete', true);
    }

    async provideCompletionItems(document, position, token, context) {
        if (!this.enabled || !this.providerManager) {
            return [];
        }

        // Debounce to avoid too many requests
        return new Promise((resolve) => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(async () => {
                try {
                    const suggestions = await this.generateSuggestions(document, position);
                    resolve(suggestions);
                } catch (error) {
                    console.error('Autocomplete error:', error);
                    resolve([]);
                }
            }, this.debounceDelay);
        });
    }

    async generateSuggestions(document, position) {
        // Get context around cursor
        const textBeforeCursor = document.getText(
            new vscode.Range(new vscode.Position(0, 0), position)
        );
        
        const textAfterCursor = document.getText(
            new vscode.Range(position, new vscode.Position(document.lineCount, 0))
        );

        // Get current line
        const line = document.lineAt(position.line).text;
        const linePrefix = line.substring(0, position.character);

        // Simple context-based suggestions
        const suggestions = [];

        // Function/method completion
        if (linePrefix.match(/\w+\.$/)) {
            suggestions.push(...this.generateMethodCompletions(linePrefix));
        }

        // Variable completion
        if (linePrefix.match(/\w+$/)) {
            suggestions.push(...this.generateVariableCompletions(linePrefix, textBeforeCursor));
        }

        // Statement completion
        if (linePrefix.trim().endsWith('{') || linePrefix.trim().endsWith(';')) {
            suggestions.push(...this.generateStatementCompletions(linePrefix));
        }

        return suggestions.map(s => ({
            label: s.label,
            kind: vscode.CompletionItemKind[s.kind] || vscode.CompletionItemKind.Text,
            detail: s.detail,
            documentation: s.documentation,
            insertText: s.insertText,
            range: new vscode.Range(position.translate(0, -linePrefix.length), position)
        }));
    }

    generateMethodCompletions(prefix) {
        const objectName = prefix.replace('.', '');
        const completions = [];

        // Common JavaScript methods
        const methods = {
            'console': ['log', 'error', 'warn', 'info', 'debug'],
            'Array': ['push', 'pop', 'shift', 'unshift', 'map', 'filter', 'reduce', 'forEach'],
            'String': ['toUpperCase', 'toLowerCase', 'trim', 'split', 'replace', 'substring'],
            'Object': ['keys', 'values', 'entries', 'assign', 'create'],
            'Promise': ['then', 'catch', 'finally', 'all', 'race'],
            'Math': ['floor', 'ceil', 'round', 'abs', 'max', 'min', 'random']
        };

        if (methods[objectName]) {
            methods[objectName].forEach(method => {
                completions.push({
                    label: `${objectName}.${method}()`,
                    kind: 'Method',
                    detail: `Method ${method}`,
                    documentation: `Calls ${method} on ${objectName}`,
                    insertText: `${method}()$0`
                });
            });
        }

        return completions;
    }

    generateVariableCompletions(prefix, textBeforeCursor) {
        const completions = [];
        const variablePattern = /(?:const|let|var)\s+(\w+)/g;
        let match;

        while ((match = variablePattern.exec(textBeforeCursor)) !== null) {
            const variableName = match[1];
            if (variableName.startsWith(prefix) && variableName !== prefix) {
                completions.push({
                    label: variableName,
                    kind: 'Variable',
                    detail: 'Variable',
                    documentation: `Variable ${variableName}`,
                    insertText: variableName
                });
            }
        }

        return completions;
    }

    generateStatementCompletions(prefix) {
        const completions = [];

        // Common statement patterns
        completions.push({
            label: 'if statement',
            kind: 'Snippet',
            detail: 'If statement',
            documentation: 'Create an if statement',
            insertText: 'if (${1:condition}) {\n\t${2:// code}\n}'
        });

        completions.push({
            label: 'for loop',
            kind: 'Snippet',
            detail: 'For loop',
            documentation: 'Create a for loop',
            insertText: 'for (let ${1:i} = 0; ${1:i} < ${2:length}; ${1:i}++) {\n\t${3:// code}\n}'
        });

        completions.push({
            label: 'function',
            kind: 'Snippet',
            detail: 'Function declaration',
            documentation: 'Create a function',
            insertText: 'function ${1:name}(${2:params}) {\n\t${3:// code}\n}'
        });

        completions.push({
            label: 'async function',
            kind: 'Snippet',
            detail: 'Async function',
            documentation: 'Create an async function',
            insertText: 'async function ${1:name}(${2:params}) {\n\t${3:// code}\n}'
        });

        return completions;
    }

    dispose() {
        clearTimeout(this.debounceTimer);
    }
}

module.exports = AutocompleteManager;
