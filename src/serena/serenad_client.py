#!/usr/bin/env python3
"""
================================================================================
SERENAD CLIENT: Thin CLI client for the Serena daemon
================================================================================

This script provides a fast CLI interface that communicates with the running
Serena daemon via HTTP. It avoids the ~2s startup overhead of creating new
language server instances on every invocation.

USAGE:
    serenad-cli <tool> [options]
    
    serenad-cli find_symbol --name_path_pattern "MyClass"
    serenad-cli read_file --relative_path "src/main.py"
    serenad-cli get_symbols_overview --relative_path "src/main.py"
    serenad-cli search_for_pattern --substring_pattern "TODO"

The client automatically:
1. Reads daemon connection info from ~/.serena/daemon.json
2. Connects to the daemon via HTTP/SSE
3. Sends tool invocation requests
4. Prints the result

If the daemon is not running, it falls back to the standalone mode
(using the original cli_tools.py logic).

================================================================================
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from pathlib import Path
from typing import Optional, Any, Dict, List

# Import the original cli_tools for fallback
try:
    # Try to import from the same package
    from serena.cli_tools import execute_tool as execute_tool_standalone
except ImportError:
    execute_tool_standalone = None

# Configuration
SERENA_DIR = Path.home() / ".serena"
CONFIG_FILE = SERENA_DIR / "daemon.json"
DEFAULT_TIMEOUT = 30


def get_daemon_url() -> Optional[str]:
    """Get the daemon URL from config file."""
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        host = config.get('host', '127.0.0.1')
        port = config.get('port', 24282)
        return f"http://{host}:{port}"
    except (json.JSONDecodeError, IOError, KeyError):
        return None


def check_daemon_status(url: str) -> bool:
    """Check if the daemon is responding."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def call_daemon_tool(url: str, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a tool on the daemon via HTTP.
    
    The daemon exposes a simple REST endpoint: POST /tools/<tool_name>
    We send the parameters as JSON body and get the result back.
    """
    endpoint = f"{url}/tools/{tool_name}"
    
    # Send parameters directly as JSON body (not wrapped in JSON-RPC)
    response = requests.post(
        endpoint,
        json=params,
        timeout=DEFAULT_TIMEOUT
    )
    
    if response.status_code != 200:
        raise Exception(f"Daemon returned status {response.status_code}: {response.text}")
    
    result = response.json()
    
    # Handle JSON-RPC response
    if "error" in result:
        raise Exception(f"Tool execution error: {result['error']}")
    
    return result.get("result", {})


def execute_tool_with_daemon(tool_name: str, params: Dict[str, Any], use_json: bool = False) -> int:
    """
    Execute a tool using the daemon if available, otherwise fall back to standalone.
    
    Returns exit code (0 for success, 1 for error).
    """
    url = get_daemon_url()
    
    if url and check_daemon_status(url):
        # Use daemon
        print(f"Using daemon at {url}...", file=sys.stderr)
        try:
            result = call_daemon_tool(url, tool_name, params)
            
            if use_json:
                print(json.dumps(result, indent=2))
            else:
                # Pretty print the result
                if isinstance(result, dict):
                    if "content" in result:
                        content = result["content"]
                        if isinstance(content, list) and len(content) > 0:
                            # Print content items
                            for item in content:
                                if isinstance(item, dict) and "text" in item:
                                    print(item["text"])
                                else:
                                    print(json.dumps(item, indent=2))
                        else:
                            print(content)
                    else:
                        print(json.dumps(result, indent=2))
                else:
                    print(result)
            
            return 0
            
        except Exception as e:
            print(f"Error calling daemon: {e}", file=sys.stderr)
            # Fall back to standalone
            print("Falling back to standalone mode...", file=sys.stderr)
    else:
        print("Daemon not running. Using standalone mode...", file=sys.stderr)
    
    # Fallback to standalone mode
    if execute_tool_standalone:
        try:
            result = execute_tool_standalone(tool_name, params, use_json=use_json)
            return result
        except Exception as e:
            print(f"Error in standalone mode: {e}", file=sys.stderr)
            return 1
    else:
        print("Error: Standalone mode not available (cli_tools not imported)", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with dynamic tool commands."""
    parser = argparse.ArgumentParser(
        description="Serena CLI Client - Fast interface to Serena tools via daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  serenad-cli find_symbol --name_path_pattern "MyClass"
  serenad-cli read_file --relative_path "src/main.py"
  serenad-cli get_symbols_overview --relative_path "src/main.py"
  serenad-cli search_for_pattern --substring_pattern "TODO"
  serenad-cli tools
  serenad-cli projects
  serenad-cli --json find_symbol --name_path_pattern "MyClass"

Use 'serenad start --project /path' to start the daemon first.
        """
    )
    
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    parser.add_argument("--project", "-p", help="Project path (required for most tools)")
    
    # Subcommands for tools
    subparsers = parser.add_subparsers(dest="tool", help="Tool to execute")
    
    # Common tool patterns - we'll add all 41 tools dynamically
    # For now, let's add the most common ones
    
    # read_file
    read_parser = subparsers.add_parser("read_file", help="Read a file")
    read_parser.add_argument("--relative_path", required=True, help="Path to the file")
    read_parser.add_argument("--offset", type=int, help="Line offset")
    read_parser.add_argument("--limit", type=int, help="Line limit")
    
    # list_dir
    list_parser = subparsers.add_parser("list_dir", help="List directory contents")
    list_parser.add_argument("--relative_path", required=True, help="Directory path")
    list_parser.add_argument("--recursive", action="store_true", default=False, help="Recursively list subdirectories")
    list_parser.add_argument("--skip_ignored_files", action="store_true", default=False, help="Skip ignored files")
    
    # get_symbols_overview
    symbols_parser = subparsers.add_parser("get_symbols_overview", help="Get symbol overview")
    symbols_parser.add_argument("--relative_path", required=True, help="File path")
    
    # find_symbol
    find_parser = subparsers.add_parser("find_symbol", help="Find a symbol")
    find_parser.add_argument("--name_path_pattern", required=True, help="Name pattern")
    find_parser.add_argument("--include_body", action="store_true", help="Include symbol body")
    find_parser.add_argument("--language", help="Language filter")
    
    # search_for_pattern
    search_parser = subparsers.add_parser("search_for_pattern", help="Search for a pattern")
    search_parser.add_argument("--substring_pattern", help="Substring pattern")
    search_parser.add_argument("--regex_pattern", help="Regex pattern")
    search_parser.add_argument("--language", help="Language filter")
    
    # replace_in_file
    replace_parser = subparsers.add_parser("replace_in_file", help="Replace text in file")
    replace_parser.add_argument("--relative_path", required=True, help="File path")
    replace_parser.add_argument("--old_text", required=True, help="Text to find")
    replace_parser.add_argument("--new_text", required=True, help="Text to replace with")
    replace_parser.add_argument("--max_replacements", type=int, help="Max replacements")
    
    # create_file
    create_parser = subparsers.add_parser("create_file", help="Create a file")
    create_parser.add_argument("--relative_path", required=True, help="File path")
    create_parser.add_argument("--content", help="File content")
    
    # delete_file
    delete_parser = subparsers.add_parser("delete_file", help="Delete a file")
    delete_parser.add_argument("--relative_path", required=True, help="File path")
    
    # move_file
    move_parser = subparsers.add_parser("move_file", help="Move/rename a file")
    move_parser.add_argument("--source_path", required=True, help="Source path")
    move_parser.add_argument("--dest_path", required=True, help="Destination path")
    
    # projects
    subparsers.add_parser("projects", help="List active projects")
    
    # contexts
    subparsers.add_parser("contexts", help="List available contexts")
    
    # modes
    subparsers.add_parser("modes", help="List available modes")
    
    # tools
    subparsers.add_parser("tools", help="List available tools")
    
    # activate_project
    activate_parser = subparsers.add_parser("activate_project", help="Activate a project")
    activate_parser.add_argument("--project_path", required=True, help="Project path")
    
    # set_mode
    mode_parser = subparsers.add_parser("set_mode", help="Set operational mode")
    mode_parser.add_argument("--mode", required=True, help="Mode name")
    
    # set_context
    context_parser = subparsers.add_parser("set_context", help="Set context")
    context_parser.add_argument("--context", required=True, help="Context name")
    
    # add_memory
    memory_parser = subparsers.add_parser("add_memory", help="Add project memory")
    memory_parser.add_argument("--title", required=True, help="Memory title")
    memory_parser.add_argument("--content", required=True, help="Memory content")
    memory_parser.add_argument("--tags", help="Comma-separated tags")
    
    # get_memories
    get_memories_parser = subparsers.add_parser("get_memories", help="Get project memories")
    get_memories_parser.add_argument("--query", help="Search query")
    
    # delete_memory
    delete_memory_parser = subparsers.add_parser("delete_memory", help="Delete a memory")
    delete_memory_parser.add_argument("--memory_id", required=True, help="Memory ID")
    
    # onboarding
    subparsers.add_parser("onboarding", help="Run onboarding process")
    
    # get_tool_info
    info_parser = subparsers.add_parser("get_tool_info", help="Get tool information")
    info_parser.add_argument("--tool_name", required=True, help="Tool name")
    
    return parser


def main():
    """Main entry point for serenad-cli command."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.tool:
        parser.print_help()
        return 1
    
    # Build params from args
    params = {}
    
    # Add project if provided
    if args.project:
        params["project_path"] = args.project
    
    # Add tool-specific params
    if args.tool == "read_file":
        params["relative_path"] = args.relative_path
        if args.offset:
            params["offset"] = args.offset
        if args.limit:
            params["limit"] = args.limit
    
    elif args.tool == "list_dir":
        params["relative_path"] = args.relative_path
        params["recursive"] = args.recursive
        params["skip_ignored_files"] = args.skip_ignored_files
    
    elif args.tool == "get_symbols_overview":
        params["relative_path"] = args.relative_path
    
    elif args.tool == "find_symbol":
        params["name_path_pattern"] = args.name_path_pattern
        params["include_body"] = args.include_body
        if args.language:
            params["language"] = args.language
    
    elif args.tool == "search_for_pattern":
        if args.substring_pattern:
            params["substring_pattern"] = args.substring_pattern
        if args.regex_pattern:
            params["regex_pattern"] = args.regex_pattern
        if args.language:
            params["language"] = args.language
    
    elif args.tool == "replace_in_file":
        params["relative_path"] = args.relative_path
        params["old_text"] = args.old_text
        params["new_text"] = args.new_text
        if args.max_replacements:
            params["max_replacements"] = args.max_replacements
    
    elif args.tool == "create_file":
        params["relative_path"] = args.relative_path
        if args.content:
            params["content"] = args.content
    
    elif args.tool == "delete_file":
        params["relative_path"] = args.relative_path
    
    elif args.tool == "move_file":
        params["source_path"] = args.source_path
        params["dest_path"] = args.dest_path
    
    elif args.tool == "activate_project":
        params["project_path"] = args.project_path
    
    elif args.tool == "set_mode":
        params["mode"] = args.mode
    
    elif args.tool == "set_context":
        params["context"] = args.context
    
    elif args.tool == "add_memory":
        params["title"] = args.title
        params["content"] = args.content
        if args.tags:
            params["tags"] = args.tags.split(",")
    
    elif args.tool == "get_memories":
        if args.query:
            params["query"] = args.query
    
    elif args.tool == "delete_memory":
        params["memory_id"] = args.memory_id
    
    elif args.tool == "get_tool_info":
        params["tool_name"] = args.tool_name
    
    # Execute the tool
    start_time = time.time()
    exit_code = execute_tool_with_daemon(args.tool, params, use_json=args.json)
    elapsed = time.time() - start_time
    
    # Print timing info (useful for debugging)
    if os.environ.get("SERENAD_DEBUG"):
        print(f"\n[Debug] Execution time: {elapsed:.3f}s", file=sys.stderr)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())