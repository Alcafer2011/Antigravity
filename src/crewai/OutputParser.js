/**
 * CrewAI-Style Output Parser Class
 * Based on CrewAI OutputParser for structured output
 */
class OutputParser {
    constructor(config) {
        this.type = config.type || 'text';
        this.schema = config.schema || null;
        this.instructions = config.instructions || '';
    }

    /**
     * Parse output from LLM
     */
    parse(text) {
        switch (this.type) {
            case 'json':
                return this._parseJson(text);
            case 'pydantic':
                return this._parsePydantic(text);
            case 'csv':
                return this._parseCsv(text);
            case 'list':
                return this._parseList(text);
            default:
                return this._parseText(text);
        }
    }

    /**
     * Get format instructions
     */
    getFormatInstructions() {
        let instructions = this.instructions;
        
        if (this.type === 'json') {
            instructions += '\n\nOutput must be valid JSON format.';
            if (this.schema) {
                instructions += '\n\nSchema:\n' + JSON.stringify(this.schema, null, 2);
            }
        } else if (this.type === 'pydantic') {
            instructions += '\n\nOutput must match the specified Pydantic model schema.';
            if (this.schema) {
                instructions += '\n\nSchema:\n' + JSON.stringify(this.schema, null, 2);
            }
        } else if (this.type === 'csv') {
            instructions += '\n\nOutput must be valid CSV format.';
        } else if (this.type === 'list') {
            instructions += '\n\nOutput must be a list of items.';
        }
        
        return instructions;
    }

    /**
     * Parse JSON output
     */
    _parseJson(text) {
        try {
            // Extract JSON from text if it's embedded
            const jsonMatch = text.match(/\{[\s\S]*\}/);
            const jsonStr = jsonMatch ? jsonMatch[0] : text;
            const parsed = JSON.parse(jsonStr);
            
            // Validate against schema if provided
            if (this.schema) {
                this._validateSchema(parsed, this.schema);
            }
            
            return parsed;
        } catch (error) {
            throw new Error(`Failed to parse JSON: ${error.message}`);
        }
    }

    /**
     * Parse Pydantic-style output
     */
    _parsePydantic(text) {
        // Pydantic is Python-specific, so we parse as JSON with schema validation
        return this._parseJson(text);
    }

    /**
     * Parse CSV output
     */
    _parseCsv(text) {
        const lines = text.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        const rows = [];
        
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim());
            const row = {};
            headers.forEach((header, index) => {
                row[header] = values[index];
            });
            rows.push(row);
        }
        
        return rows;
    }

    /**
     * Parse list output
     */
    _parseList(text) {
        // Try to parse as JSON array first
        try {
            const parsed = JSON.parse(text);
            if (Array.isArray(parsed)) {
                return parsed;
            }
        } catch (error) {
            // Fall back to splitting by newlines or commas
        }
        
        // Split by newlines or commas
        const separator = text.includes('\n') ? '\n' : ',';
        return text.split(separator).map(item => item.trim()).filter(item => item);
    }

    /**
     * Parse plain text output
     */
    _parseText(text) {
        return text.trim();
    }

    /**
     * Validate against schema
     */
    _validateSchema(data, schema) {
        // Simple schema validation
        for (const [key, value] of Object.entries(schema)) {
            if (value.required && !data.hasOwnProperty(key)) {
                throw new Error(`Missing required field: ${key}`);
            }
            
            if (data.hasOwnProperty(key)) {
                const dataValue = data[key];
                
                if (value.type && typeof dataValue !== value.type) {
                    throw new Error(`Field ${key} must be of type ${value.type}`);
                }
            }
        }
    }

    /**
     * Clone parser
     */
    clone() {
        return new OutputParser({
            type: this.type,
            schema: this.schema ? JSON.parse(JSON.stringify(this.schema)) : null,
            instructions: this.instructions
        });
    }
}

module.exports = OutputParser;
