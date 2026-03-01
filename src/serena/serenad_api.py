#!/usr/bin/env python3
"""
Simple HTTP API server for Serena daemon.
Exposes Serena tools via REST API instead of MCP SSE.
"""

import os
import sys
import json
import argparse
import logging
from flask import Flask, request, jsonify
from threading import Thread

try:
    from serena.agent import SerenaAgent
    from serena.tools.tools_base import Tool
except ImportError as e:
    print(f"Error: Could not import Serena modules: {e}")
    sys.exit(1)

app = Flask(__name__)
agent: SerenaAgent = None
logger = logging.getLogger(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "pid": os.getpid()})


@app.route('/tools', methods=['GET'])
def list_tools():
    """List available tools."""
    if agent is None:
        return jsonify({"error": "Agent not initialized"}), 500
    
    tool_names = list(agent.tools.keys())
    return jsonify({"tools": tool_names})


@app.route('/tools/<tool_name>', methods=['POST'])
def call_tool(tool_name):
    """Call a tool by name."""
    if agent is None:
        return jsonify({"error": "Agent not initialized"}), 500
    
    if tool_name not in agent.tools:
        return jsonify({"error": f"Tool '{tool_name}' not found"}), 404
    
    try:
        params = request.get_json() or {}
        
        # Get the tool instance
        tool = agent.tools[tool_name]
        
        # Get the tool's apply function metadata
        metadata = tool.get_apply_fn_metadata_from_cls()
        
        # FuncMetadata is a Pydantic model with an 'arg_model' attribute
        # that contains the validated argument schema
        arg_model = metadata.arg_model
        
        # Check for missing required parameters
        for param_name, field_info in arg_model.model_fields.items():
            if field_info.is_required() and param_name not in params:
                return jsonify({"error": f"Missing required parameter: {param_name}"}), 400
        
        # Call the tool - pass all provided params (the tool's apply method handles validation)
        result = tool.apply(**params)
        
        return jsonify({"success": True, "result": result})
    
    except TypeError as e:
        # Handle missing/invalid parameters
        logger.error(f"Parameter error for tool {tool_name}: {e}")
        return jsonify({"error": f"Invalid parameters: {e}"}), 400
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def run_server(host: str, port: int, project: str):
    """Run the HTTP API server."""
    global agent
    
    # Initialize the agent
    logger.info(f"Initializing SerenaAgent for project: {project}")
    agent = SerenaAgent(project=project)
    # Build a convenient name → tool instance mapping for the HTTP API
    # The original SerenaAgent stores tools internally as `_all_tools` (class → instance).
    # We expose a `tools` dict that maps the public tool name (as used on the CLI) to the instance.
    try:
        agent.tools = {tool.get_name_from_cls(): tool for tool in agent._all_tools.values()}
    except Exception as e:
        logger.error(f"Failed to build tool name map: {e}")
        agent.tools = {}
    logger.info("SerenaAgent initialized successfully")
    
    # Run Flask app
    logger.info(f"Starting HTTP API server on http://{host}:{port}")
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serena HTTP API Server")
    parser.add_argument("--project", required=True, help="Path to the project")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--log-file", help="Path to log file")
    
    args = parser.parse_args()
    
    # Setup logging
    if args.log_file:
        logging.basicConfig(
            filename=args.log_file,
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    run_server(args.host, args.port, args.project)
