#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { execFile } from "child_process";
import { access, constants, readFile, stat } from "fs/promises";
import { basename, dirname, extname, isAbsolute, join, relative, resolve } from "path";
import { fileURLToPath } from "url";
import { promisify } from "util";

const execFileAsync = promisify(execFile);
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Security configuration
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB max file size
const ALLOWED_EXTENSIONS = ['.json'];

/**
 * Validate that a path is within the workspace folder and is safe to access
 * @param {string} filePath - The absolute file path to validate
 * @returns {Promise<void>} - Throws error if validation fails
 */
async function validatePath(filePath) {
    // Resolve to absolute path
    const absolutePath = resolve(filePath);
    
    // Get workspace folder (extension directory) and current working directory
    const workspaceFolder = process.env.WORKSPACE_FOLDER;
    const cwd = process.cwd();
    
    // Check if path is within either the workspace or current working directory
    let isWithinAllowedPath = false;
    
    if (workspaceFolder) {
        const absoluteWorkspace = resolve(workspaceFolder);
        const relativePath = relative(absoluteWorkspace, absolutePath);
        if (!relativePath.startsWith('..') && !isAbsolute(relativePath)) {
            isWithinAllowedPath = true;
        }
    }
    
    // Also allow files in the current working directory (where gemini was invoked)
    if (!isWithinAllowedPath) {
        const absoluteCwd = resolve(cwd);
        const relativePath = relative(absoluteCwd, absolutePath);
        if (!relativePath.startsWith('..') && !isAbsolute(relativePath)) {
            isWithinAllowedPath = true;
        }
    }
    
    if (!isWithinAllowedPath) {
        throw new Error("Access denied: file must be within workspace or current directory");
    }

    // Check file extension
    const ext = (extname(absolutePath) || '').toLowerCase();
    const hasValidExtension = ALLOWED_EXTENSIONS.includes(ext);
    if (!hasValidExtension) {
        throw new Error(`Access denied: only ${ALLOWED_EXTENSIONS.join(', ')} files are allowed`);
    }

    // Check file exists and is accessible
    try {
        await access(absolutePath, constants.R_OK | constants.W_OK);
    } catch (err) {
        throw new Error("File not accessible or does not exist");
    }

    // Check file size
    const stats = await stat(absolutePath);
    if (stats.size > MAX_FILE_SIZE) {
        throw new Error(`File too large: maximum size is ${MAX_FILE_SIZE / (1024 * 1024)}MB`);
    }
}

/**
 * Sanitize error messages to not expose full filesystem paths
 * @param {string} message - The error message
 * @param {string} filePath - The file path to sanitize
 * @returns {string} - Sanitized message
 */
function sanitizeErrorMessage(message, filePath) {
    if (!message) return message;
    
    // Replace full absolute paths with just the filename
    const fileName = basename(filePath);
    const sanitized = message
        .replace(new RegExp(filePath, 'g'), fileName)
        .replace(/[\/\\][^\s\/\\]+[\/\\][^\s\/\\]+[\/\\]/g, ''); // Remove any other absolute paths (Unix/Windows)
    
    return sanitized;
}

/**
 * Validate field_name parameter for stringify_json_field
 * @param {string} fieldName - The field name to validate
 * @returns {void} - Throws error if validation fails
 */
function validateFieldName(fieldName) {
    // Must start with a valid UUID or node identifier
    if (!fieldName || typeof fieldName !== 'string') {
        throw new Error("field_name must be a non-empty string");
    }

    // Basic structure validation: should be like "node-id/path/to/field"
    const parts = fieldName.split('/');
    if (parts.length < 2) {
        throw new Error("field_name must include node ID and field path");
    }

    // Prevent injection attempts
    const dangerousPatterns = ['..', '~', '$', '`', '|', ';', '&', '<', '>', '\n', '\r'];
    for (const pattern of dangerousPatterns) {
        if (fieldName.includes(pattern)) {
            throw new Error("field_name contains invalid characters");
        }
    }
}

// Create an MCP server instance
const server = new Server(
  {
    name: "journey-tools",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Add instructions - required by Gemini CLI
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
        {
          name: "journey_fixes",
          description: "Performs common fixes to a generated journey JSON file. It should be done directly after the journey is generated.",
          inputSchema: {
            type: "object",
            properties: {
              journey_json_path: {
                type: "string",
                description: "Path to the journey JSON file to validate",
              },
            },
            required: ["journey_json_path"],
          },
        },
        {
          name: "validate_journey_metadata",
          description: "Checks whether the overall structure of the journey json file is correct, i.e. the type, version_id, timestamps and other metadata are present and correct.",
          inputSchema: {
            type: "object",
            properties: {
              journey_json_path: {
                type: "string",
                description: "Path to the journey JSON file to validate",
              },
            },
            required: ["journey_json_path"],
          },
        },
        {
          name: "validate_journey_structure",
          description: "Checks whether a journey json file has a valid structure, i.e. if all its nodes are reachable from the head node, all loops and blocks are properly nested, and each node has a unique id that matches its key in the nodes object.",
          inputSchema: {
            type: "object",
            properties: {
              journey_json_path: {
                type: "string",
                description: "Path to the journey JSON file to validate",
              },
            },
            required: ["journey_json_path"],
          },
        },
        {
          name: "validate_journey_required_fields",
          description: "Checks whether a journey json file has all of the required fields for each node type.",
          inputSchema: {
            type: "object",
            properties: {
              journey_json_path: {
                type: "string",
                description: "Path to the journey JSON file to validate",
              },
            },
            required: ["journey_json_path"],
          },
        },
        {
          name: "validate_journey_expressions",
          description: "Checks whether the expressions inside a journey json file are valid.",
          inputSchema: {
            type: "object",
            properties: {
              journey_json_path: {
                type: "string",
                description: "Path to the journey JSON file to validate",
              },
            },
            required: ["journey_json_path"],
          },
        },
        {
          name: "validate_journey_variables",
          description: "Checks whether a journey json file has variables properly defined and used, i.e. if there are no variables that are used before they are defined.",
          inputSchema: {
            type: "object",
            properties: {
              journey_json_path: {
                type: "string",
                description: "Path to the journey JSON file to validate",
              },
            },
            required: ["journey_json_path"],
          },
        },
        {
          name: "stringify_json_field",
          description: "Stringifies a JSON schema and inserts it into fields that require stringified JSON with literal \\n and \\\". Use for: (1) action/form_schema/value in form nodes, (2) links/N/data_json_schema/value in login_form escape links. Works even if journey JSON is malformed!",
          inputSchema: {
            type: "object",
            properties: {
              json_path: {
                type: "string",
                description: "Path to the JSON file to stringify (form schema or data schema)",
              },
              journey_json_path: {
                type: "string",
                description: "Path to the journey JSON file",
              },
              field_name: {
                type: "string",
                description: "Field path starting with NODE_ID. Examples: 'node-abc-123/action/form_schema/value' for form schemas, 'node-xyz-456/links/0/data_json_schema/value' for login_form link schemas.",
              },
            },
            required: ["json_path", "journey_json_path", "field_name"],
          },
        },
        {
          name: "display_journey_examples",
          description: "Display complete journey examples with explanations and JSON. Use this to reference working patterns for common journey types like loops, password reset flows, authentication patterns, and registration with protection.",
          inputSchema: {
            type: "object",
            properties: {
              pattern: {
                type: "string",
                description: "The type of example to display: 'loop' (password authentication retry patterns), 'email_otp_authentication' (email OTP with username lookup), 'password_reset' (email OTP password reset with optional passkey), 'registration' (complete registration with risk assessment, IDV, device and passkey setup), or 'all' (show all examples)",
                enum: ["loop", "email_otp_authentication", "password_reset", "registration", "all"],
              },
              include_explanation: {
                type: "boolean",
                description: "Whether to include the explanation and generation instructions (true) or just the JSON (false). Defaults to true.",
              },
            },
          },
        }
    ],
  }
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {

    const validator_scripts = {
        "journey_fixes": "journey_fixes.py",
        "validate_journey_metadata": "validate_journey_metadata.py",
        "validate_journey_structure": "validate_journey_structure.py",
        "validate_journey_required_fields": "validate_journey_required_fields.py",
        "validate_journey_expressions": "validate_journey_expressions.py",
        "validate_journey_variables": "validate_journey_variables.py"
      }

    if (request.params.name !== "journey_fixes" && 
        request.params.name !== "validate_journey_structure" && 
        request.params.name !== "validate_journey_required_fields" && 
        request.params.name !== "validate_journey_expressions" &&
        request.params.name !== "validate_journey_variables" && 
        request.params.name !== "validate_journey_metadata" &&
        request.params.name !== "stringify_json_field" &&
        request.params.name !== "display_journey_examples") {
        throw new Error(`Unknown tool: ${request.params.name}`);
    }

    if (Object.keys(validator_scripts).includes(request.params.name)) {
        const journey_json_path = request.params.arguments?.journey_json_path;
        if (!journey_json_path || typeof journey_json_path !== "string") {
            throw new Error("journey_json_path is required and must be a string");
        }

        // Resolve to absolute path to handle relative paths correctly
        const absolute_path = resolve(journey_json_path);

        // Validate path security
        try {
            await validatePath(absolute_path);
        } catch (error) {
            return {
                content: [{
                    type: "text",
                    text: `Security validation failed: ${error.message}`,
                }],
                isError: true,
            };
        }

        try {
            const { stdout, stderr } = await execFileAsync(
            "python3",
            [validator_scripts[request.params.name], absolute_path],
            { 
                cwd: import.meta.dirname,
                env: {
                    ...process.env,
                    USER_CWD: process.cwd()
                }
            }
            );

            return {
            content: [
                {
                type: "text",
                text: stdout.trim() || "Validation successful",
                },
            ],
            };
        } catch (error) {
            const sanitizedStderr = sanitizeErrorMessage(error.stderr || '', absolute_path);
            const sanitizedStdout = sanitizeErrorMessage(error.stdout || '', absolute_path);
            const sanitizedMessage = sanitizeErrorMessage(error.message || '', absolute_path);
            
            return {
            content: [
                {
                type: "text",
                text: `Validation failed: ${sanitizedStderr || sanitizedStdout || sanitizedMessage}`,
                },
            ],
            isError: true,
            };
        }
    }

    if (request.params.name === "stringify_json_field") {
        const json_path = request.params.arguments?.json_path;
        const journey_json_path = request.params.arguments?.journey_json_path;
        const field_name = request.params.arguments?.field_name;

        if (!json_path || typeof json_path !== "string") {
            throw new Error("json_path is required and must be a string");
        }
        if (!journey_json_path || typeof journey_json_path !== "string") {
            throw new Error("journey_json_path is required and must be a string");
        }
        if (!field_name || typeof field_name !== "string") {
            throw new Error("field_name is required and must be a string");
        }

        // Validate field_name
        try {
            validateFieldName(field_name);
        } catch (error) {
            return {
                content: [{
                    type: "text",
                    text: `Invalid field_name: ${error.message}`,
                }],
                isError: true,
            };
        }

        // Resolve to absolute paths
        const absolute_json_path = resolve(json_path);
        const absolute_journey_path = resolve(journey_json_path);

        // Validate both paths
        try {
            await validatePath(absolute_json_path);
            await validatePath(absolute_journey_path);
        } catch (error) {
            return {
                content: [{
                    type: "text",
                    text: `Security validation failed: ${error.message}`,
                }],
                isError: true,
            };
        }

        try {
            const { stdout, stderr } = await execFileAsync(
            "python3",
            ["stringify_json_field.py", absolute_json_path, absolute_journey_path, field_name],
            { 
                cwd: import.meta.dirname,
                env: {
                    ...process.env,
                    USER_CWD: process.cwd()
                }
            }
            );

            return {
            content: [
                {
                type: "text",
                text: stdout.trim() || "Successfully stringified and inserted JSON field",
                },
            ],
            };
        } catch (error) {
            const sanitizedStderr = sanitizeErrorMessage(error.stderr || '', absolute_journey_path);
            const sanitizedStdout = sanitizeErrorMessage(error.stdout || '', absolute_journey_path);
            const sanitizedMessage = sanitizeErrorMessage(error.message || '', absolute_journey_path);
            
            return {
            content: [
                {
                type: "text",
                text: `Stringify failed: ${sanitizedStderr || sanitizedStdout || sanitizedMessage}`,
                },
            ],
            isError: true,
            };
        }
    }

    if (request.params.name === "display_journey_examples") {
        const pattern = request.params.arguments?.pattern || "all";
        const include_explanation = request.params.arguments?.include_explanation !== false;

        // Map pattern to example files
        const patternMap = {
            'loop': ['loop_example.md'],
            'password_reset': ['password_reset_example.md'],
            'email_otp_authentication': ['email_otp_authentication_example.md'],
            'registration': ['registration_with_protection_example.md'],
            'all': [
                'loop_example.md',
                'email_otp_authentication_example.md',
                'password_reset_example.md',
                'registration_with_protection_example.md'
            ]
        };

        const files = patternMap[pattern] || patternMap['all'];
        const examplesDir = join(__dirname, 'examples');

        let output = '';

        try {
            for (const file of files) {
                const filePath = join(examplesDir, file);
                const content = await readFile(filePath, 'utf-8');

                if (!include_explanation) {
                    // Extract only the JSON part
                    const jsonMatch = content.match(/```json\n([\s\S]+?)\n```/);
                    if (jsonMatch) {
                        output += `\n## ${file.replace('_example.md', '').replace(/_/g, ' ').toUpperCase()}\n\n`;
                        output += '```json\n' + jsonMatch[1] + '\n```\n\n';
                    }
                } else {
                    output += content + '\n\n---\n\n';
                }
            }

            if (!output) {
                output = `No examples found for pattern: ${pattern}. Available patterns: loop, password_reset, all`;
            }

            return {
                content: [{
                    type: "text",
                    text: output.trim(),
                }],
            };
        } catch (error) {
            return {
                content: [{
                    type: "text",
                    text: `Error reading examples: ${error.message}`,
                }],
                isError: true,
            };
        }
    }

    return {
        content: [
            {
                type: "text",
                text: "Unknown tool",
            },
        ],
    };
    }
);

// Start the MCP server with stdio transport
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
