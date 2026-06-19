/**
 * Streaming Diff Module
 * Provides real-time diff visualization similar to Continue
 * Simplified implementation without complex streaming infrastructure
 */

const vscode = require('vscode');
const diff = require('diff');

class StreamingDiffManager {
    constructor(context) {
        this.context = context;
        this.enabled = true;
        this.diffDecorationType = null;
        this.activeDiffs = new Map();
        
        this.initialize();
    }

    initialize() {
        // Create decoration types for diff visualization
        this.diffDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: new vscode.ThemeColor('diffEditor.insertedTextBackground'),
            borderColor: new vscode.ThemeColor('diffEditor.insertedTextBorder'),
            borderStyle: 'solid',
            borderWidth: '1px'
        });

        this.removedDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: new vscode.ThemeColor('diffEditor.removedTextBackground'),
            borderColor: new vscode.ThemeColor('diffEditor.removedTextBorder'),
            borderStyle: 'solid',
            borderWidth: '1px',
            textDecoration: 'line-through'
        });

        // Listen to configuration changes
        vscode.workspace.onDidChangeConfiguration(event => {
            if (event.affectsConfiguration('antigravity.enableStreamingDiff')) {
                this.enabled = vscode.workspace.getConfiguration('antigravity').get('enableStreamingDiff', true);
            }
        });

        this.enabled = vscode.workspace.getConfiguration('antigravity').get('enableStreamingDiff', true);
    }

    /**
     * Show diff between original and modified text
     */
    showDiff(editor, originalText, modifiedText) {
        if (!this.enabled || !editor) {
            return;
        }

        const diffResult = this.computeDiff(originalText, modifiedText);
        this.displayDiff(editor, diffResult);
        
        // Store active diff for this editor
        this.activeDiffs.set(editor.document.uri.toString(), {
            original: originalText,
            modified: modifiedText,
            diff: diffResult
        });

        // Set context key for keybindings
        vscode.commands.executeCommand('setContext', 'antigravity.diffVisible', true);
    }

    /**
     * Compute diff between two texts
     */
    computeDiff(original, modified) {
        const changes = diff.diffLines(original, modified);
        const addedRanges = [];
        const removedRanges = [];

        let currentLine = 0;

        changes.forEach(change => {
            if (change.added) {
                const lines = change.value.split('\n').filter(line => line !== '');
                if (lines.length > 0) {
                    addedRanges.push({
                        start: currentLine,
                        end: currentLine + lines.length - 1,
                        text: change.value
                    });
                }
            } else if (change.removed) {
                const lines = change.value.split('\n').filter(line => line !== '');
                if (lines.length > 0) {
                    removedRanges.push({
                        start: currentLine,
                        end: currentLine + lines.length - 1,
                        text: change.value
                    });
                }
            } else {
                currentLine += change.count || 0;
            }
        });

        return { addedRanges, removedRanges };
    }

    /**
     * Display diff in editor using decorations
     */
    displayDiff(editor, diffResult) {
        const addedDecorations = diffResult.addedRanges.map(range => ({
            range: new vscode.Range(range.start, 0, range.end, 0),
            hoverMessage: `Added: ${range.text}`
        }));

        const removedDecorations = diffResult.removedRanges.map(range => ({
            range: new vscode.Range(range.start, 0, range.end, 0),
            hoverMessage: `Removed: ${range.text}`
        }));

        editor.setDecorations(this.diffDecorationType, addedDecorations);
        editor.setDecorations(this.removedDecorationType, removedDecorations);
    }

    /**
     * Accept current diff and apply changes
     */
    acceptDiff(editor) {
        const uri = editor.document.uri.toString();
        const activeDiff = this.activeDiffs.get(uri);

        if (!activeDiff) {
            return false;
        }

        // Apply the modified text
        const edit = new vscode.WorkspaceEdit();
        const fullRange = new vscode.Range(
            new vscode.Position(0, 0),
            new vscode.Position(editor.document.lineCount, 0)
        );
        
        edit.replace(editor.document.uri, fullRange, activeDiff.modified);
        
        return vscode.workspace.applyEdit(edit).then(success => {
            if (success) {
                this.clearDiff(editor);
                return true;
            }
            return false;
        });
    }

    /**
     * Reject current diff and revert to original
     */
    rejectDiff(editor) {
        const uri = editor.document.uri.toString();
        const activeDiff = this.activeDiffs.get(uri);

        if (!activeDiff) {
            return false;
        }

        // Revert to original text
        const edit = new vscode.WorkspaceEdit();
        const fullRange = new vscode.Range(
            new vscode.Position(0, 0),
            new vscode.Position(editor.document.lineCount, 0)
        );
        
        edit.replace(editor.document.uri, fullRange, activeDiff.original);
        
        return vscode.workspace.applyEdit(edit).then(success => {
            if (success) {
                this.clearDiff(editor);
                return true;
            }
            return false;
        });
    }

    /**
     * Clear diff decorations and state
     */
    clearDiff(editor) {
        if (!editor) {
            return;
        }

        editor.setDecorations(this.diffDecorationType, []);
        editor.setDecorations(this.removedDecorationType, []);
        
        const uri = editor.document.uri.toString();
        this.activeDiffs.delete(uri);

        vscode.commands.executeCommand('setContext', 'antigravity.diffVisible', false);
    }

    /**
     * Check if there's an active diff for the given editor
     */
    hasActiveDiff(editor) {
        if (!editor) {
            return false;
        }
        return this.activeDiffs.has(editor.document.uri.toString());
    }

    dispose() {
        if (this.diffDecorationType) {
            this.diffDecorationType.dispose();
        }
        if (this.removedDecorationType) {
            this.removedDecorationType.dispose();
        }
        this.activeDiffs.clear();
    }
}

module.exports = StreamingDiffManager;
