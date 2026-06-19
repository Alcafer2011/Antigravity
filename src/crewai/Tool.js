/**
 * CrewAI-Style Tool Class
 * Based on CrewAI Tool architecture with name, description, function
 */
class Tool {
    constructor(config) {
        this.name = config.name;
        this.description = config.description;
        this.func = config.func;
        this.argsSchema = config.argsSchema || null;
        this.returnDirect = config.returnDirect || false;
        this.handleToolError = config.handleToolError || false;
    }

    /**
     * Execute the tool
     */
    async execute(task, context, args = {}) {
        try {
            if (typeof this.func !== 'function') {
                throw new Error(`Tool ${this.name} does not have a valid function`);
            }

            const result = await this.func(args, context, task);
            
            if (this.returnDirect) {
                return result;
            }
            
            return {
                tool: this.name,
                result: result,
                success: true
            };
        } catch (error) {
            if (this.handleToolError) {
                return {
                    tool: this.name,
                    error: error.message,
                    success: false
                };
            }
            
            throw new Error(`Tool ${this.name} execution failed: ${error.message}`);
        }
    }

    /**
     * Validate arguments against schema
     */
    validateArgs(args) {
        if (!this.argsSchema) {
            return { valid: true, errors: [] };
        }

        const errors = [];
        
        for (const [key, schema] of Object.entries(this.argsSchema)) {
            if (schema.required && !args.hasOwnProperty(key)) {
                errors.push(`Missing required argument: ${key}`);
            }
            
            if (args.hasOwnProperty(key)) {
                const value = args[key];
                
                if (schema.type && typeof value !== schema.type) {
                    errors.push(`Argument ${key} must be of type ${schema.type}`);
                }
                
                if (schema.enum && !schema.enum.includes(value)) {
                    errors.push(`Argument ${key} must be one of: ${schema.enum.join(', ')}`);
                }
            }
        }
        
        return {
            valid: errors.length === 0,
            errors
        };
    }

    /**
     * Get tool schema
     */
    getSchema() {
        return {
            name: this.name,
            description: this.description,
            parameters: this.argsSchema || {
                type: "object",
                properties: {},
                required: []
            }
        };
    }

    /**
     * Clone tool
     */
    clone() {
        return new Tool({
            name: this.name,
            description: this.description,
            func: this.func,
            argsSchema: this.argsSchema,
            returnDirect: this.returnDirect,
            handleToolError: this.handleToolError
        });
    }
}

/**
 * Tool decorator for creating tools from functions
 */
function tool(name, description, argsSchema = null) {
    return function(target, propertyKey, descriptor) {
        const originalMethod = descriptor.value;
        
        descriptor.value = async function(args, context, task) {
            return await originalMethod.call(this, args, context, task);
        };
        
        // Store tool metadata
        descriptor.value._toolMetadata = {
            name,
            description,
            argsSchema
        };
        
        return descriptor;
    };
}

module.exports = { Tool, tool };
