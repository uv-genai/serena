#!/usr/bin/env python3
"""
================================================================================
SERENAD-CLI: Serena Daemon Client (Click-based CLI)
================================================================================

A beautiful, user-friendly command-line interface for executing Serena tools
via the daemon. Provides ~15-20x faster response times compared to standalone mode.

Usage:
    serenad-cli <tool> [OPTIONS]
    
Examples:
    \b
    $ serenad-cli list_dir --relative_path src
    $ serenad-cli find_symbol --name_path_pattern "MyClass" --include_body
    $ serenad-cli read_file --relative_path src/main.py
    $ serenad-cli search_for_pattern --substring_pattern "TODO"
    $ serenad-cli --json list_dir --relative_path .

The client automatically:
  1. Checks if daemon is running
  2. Uses daemon if available (~0.1s response)
  3. Falls back to standalone mode if daemon is down

================================================================================
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Optional, Any, Dict

import click

# Import the original cli_tools for fallback
try:
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
    """Call a tool on the daemon via HTTP REST API."""
    endpoint = f"{url}/tools/{tool_name}"
    
    response = requests.post(endpoint, json=params, timeout=DEFAULT_TIMEOUT)
    
    if response.status_code != 200:
        raise Exception(f"Daemon returned status {response.status_code}: {response.text}")
    
    result = response.json()
    
    if "error" in result:
        raise Exception(f"Tool execution error: {result['error']}")
    
    return result.get("result", {})


def format_result(result: Any, as_json: bool = False) -> str:
    """Format the result for display."""
    if as_json:
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    if isinstance(result, str):
        return result
    elif isinstance(result, dict):
        # Pretty print dict
        if "content" in result:
            content = result["content"]
            if isinstance(content, list):
                return "\n".join([json.dumps(item, ensure_ascii=False) for item in content])
            return str(content)
        return json.dumps(result, indent=2, ensure_ascii=False)
    elif isinstance(result, list):
        return "\n".join([json.dumps(item, ensure_ascii=False) for item in result])
    else:
        return str(result)


# Create the main Click group
@click.group(invoke_without_command=True)
@click.option('--json', '-j', is_flag=True, help='Output in JSON format')
@click.option('--project', '-p', help='Project path (required for many tools)')
@click.pass_context
def cli(ctx, json, project):
    """
    Serena CLI Client - Fast interface to Serena tools via daemon
    
    Execute Serena tools with ~15-20x faster response times by using the
    persistent daemon instead of starting a new process for each command.
    
    \b
    Quick Start:
        1. Start the daemon: serenad start --project /path/to/project
        2. Run tools:        serenad-cli <tool> [options]
        3. Stop daemon:      serenad stop
    
    \b
    Available Tools:
        read_file              Read a file
        list_dir               List directory contents
        find_symbol            Find a symbol by name pattern
        search_for_pattern     Search for text patterns
        get_symbols_overview   Get symbol overview of a file
        create_text_file       Create a new file
        replace_content        Replace text in a file
        ... and many more
    """
    # Store global options in context
    ctx.ensure_object(dict)
    ctx.obj['json'] = json
    ctx.obj['project'] = project
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Tool commands - each tool becomes a Click command
# We'll dynamically create these based on the tool registry
def create_tool_command(tool_name: str, tool_class):
    """Create a Click command for a tool."""
    
    # Get tool metadata
    try:
        metadata = tool_class.get_apply_fn_metadata_from_cls()
        arg_model = metadata.arg_model
        docstring = tool_class.get_apply_docstring_from_cls()
    except Exception:
        metadata = None
        docstring = tool_class.__doc__ or ""
    
    # Build parameters for the Click command
    params = []
    
    # Add common parameters
    if metadata:
        for param_name, field_info in arg_model.model_fields.items():
            if param_name in ['self', 'cls', 'log_call', 'catch_exceptions', 'mcp_ctx', 'max_answer_chars', 'args']:
                continue
            
            # Determine parameter type and options
            is_required = field_info.is_required()
            default = field_info.default if not is_required else None
            
            # Skip max_answer_chars as it's internal
            if param_name == 'max_answer_chars':
                continue
            
            # Create Click option
            if isinstance(default, bool):
                # Boolean flag
                if default:
                    param = click.option(f'--{param_name}/--no-{param_name}', default=default, help=f'{param_name} parameter')
                else:
                    param = click.option(f'--{param_name}/--no-{param_name}', default=default, help=f'{param_name} parameter')
            elif default is not None:
                param = click.option(f'--{param_name}', type=str, default=str(default) if default is not None else None, help=f'{param_name} parameter')
            else:
                param = click.option(f'--{param_name}', type=str, required=is_required, help=f'{param_name} parameter')
            
            params.append(param)
    
    # Create the command function
    def make_command_func(tool_name):
        @click.pass_context
        def command_func(ctx, **kwargs):
            # Filter out None values
            params = {k: v for k, v in kwargs.items() if v is not None}
            
            # Add project if provided
            if ctx.obj.get('project'):
                params['project_path'] = ctx.obj['project']
            
            # Execute the tool
            url = get_daemon_url()
            use_json = ctx.obj.get('json', False)
            
            if url and check_daemon_status(url):
                # Use daemon
                click.echo(f"Using daemon at {url}...", err=True)
                try:
                    result = call_daemon_tool(url, tool_name, params)
                    click.echo(format_result(result, use_json))
                    return 0
                except Exception as e:
                    click.echo(f"❌ Error calling daemon: {e}", err=True)
                    click.echo("   Falling back to standalone mode...", err=True)
            else:
                click.echo("⚠️  Daemon not running. Using standalone mode...", err=True)
            
            # Fallback to standalone
            if execute_tool_standalone:
                # Build args for standalone execution
                args_list = [tool_name]
                for k, v in params.items():
                    args_list.append(f"--{k}")
                    if v is not True:  # Don't add value for boolean flags
                        args_list.append(str(v))
                
                return execute_tool_standalone(args_list)
            else:
                click.echo("❌ Error: Standalone mode not available", err=True)
                return 1
        
        return command_func
    
    # Set command name and documentation
    command_func = make_command_func(tool_name)
    command_func.__name__ = tool_name
    command_func.__doc__ = docstring
    
    # Apply parameters
    for param in reversed(params):
        command_func = param(command_func)
    
    return command_func


# Dynamically add tool commands (silently ignore failures to ensure clean CLI)
try:
    from serena.tools.tools_base import ToolRegistry
    
    @cli.result_callback()
    def process_result(result, **kwargs):
        return result
    
    # Get all tool classes and create commands
    for tool_class in ToolRegistry().get_all_tool_classes():
        tool_name = tool_class.get_name_from_cls()
        command = create_tool_command(tool_name, tool_class)
        cli.add_command(command)
        
except Exception:
    # Silently ignore dynamic loading errors; rely on manually defined commands
    pass


# Add some commonly used tools manually for better UX
@cli.command('list_dir')
@click.option('--relative_path', required=True, help='Directory path')
@click.option('--recursive', '-r', is_flag=True, help='Recursively list subdirectories')
@click.option('--skip_ignored_files', '-s', is_flag=True, help='Skip ignored files')
@click.pass_context
def list_dir(ctx, relative_path, recursive, skip_ignored_files):
    """List directory contents."""
    params = {
        'relative_path': relative_path,
        'recursive': recursive,
        'skip_ignored_files': skip_ignored_files
    }
    
    url = get_daemon_url()
    use_json = ctx.obj.get('json', False)
    
    if url and check_daemon_status(url):
        click.echo(f"Using daemon at {url}...", err=True)
        try:
            result = call_daemon_tool(url, 'list_dir', params)
            click.echo(format_result(result, use_json))
            return 0
        except Exception as e:
            click.echo(f"❌ Error calling daemon: {e}", err=True)
    else:
        click.echo("⚠️  Daemon not running. Using standalone mode...", err=True)
    
    if execute_tool_standalone:
        args = ['list_dir', '--relative_path', relative_path]
        if recursive:
            args.append('--recursive')
        if skip_ignored_files:
            args.append('--skip_ignored_files')
        return execute_tool_standalone(args)
    else:
        click.echo("❌ Error: Standalone mode not available", err=True)
        return 1


@cli.command('find_symbol')
@click.option('--name_path_pattern', required=True, help='Name pattern to search for')
@click.option('--include_body', '-b', is_flag=True, help='Include symbol body in result')
@click.option('--language', '-l', help='Language filter')
@click.option('--relative_path', help='Restrict search to specific file')
@click.option('--substring_matching', '-s', is_flag=True, help='Use substring matching')
@click.pass_context
def find_symbol(ctx, name_path_pattern, include_body, language, relative_path, substring_matching):
    """Find a symbol by name pattern."""
    params = {
        'name_path_pattern': name_path_pattern,
        'include_body': include_body
    }
    if language:
        params['language'] = language
    if relative_path:
        params['relative_path'] = relative_path
    if substring_matching:
        params['substring_matching'] = substring_matching
    
    url = get_daemon_url()
    use_json = ctx.obj.get('json', False)
    
    if url and check_daemon_status(url):
        click.echo(f"Using daemon at {url}...", err=True)
        try:
            result = call_daemon_tool(url, 'find_symbol', params)
            click.echo(format_result(result, use_json))
            return 0
        except Exception as e:
            click.echo(f"❌ Error calling daemon: {e}", err=True)
    else:
        click.echo("⚠️  Daemon not running. Using standalone mode...", err=True)
    
    if execute_tool_standalone:
        args = ['find_symbol', '--name_path_pattern', name_path_pattern]
        if include_body:
            args.append('--include_body')
        if language:
            args.extend(['--language', language])
        return execute_tool_standalone(args)
    else:
        click.echo("❌ Error: Standalone mode not available", err=True)
        return 1


@cli.command('read_file')
@click.option('--relative_path', required=True, help='Path to the file')
@click.option('--offset', '-o', type=int, help='Line offset (1-based)')
@click.option('--limit', '-n', type=int, help='Maximum number of lines')
@click.pass_context
def read_file(ctx, relative_path, offset, limit):
    """Read a file."""
    params = {'relative_path': relative_path}
    if offset:
        params['offset'] = offset
    if limit:
        params['limit'] = limit
    
    url = get_daemon_url()
    use_json = ctx.obj.get('json', False)
    
    if url and check_daemon_status(url):
        click.echo(f"Using daemon at {url}...", err=True)
        try:
            result = call_daemon_tool(url, 'read_file', params)
            click.echo(format_result(result, use_json))
            return 0
        except Exception as e:
            click.echo(f"❌ Error calling daemon: {e}", err=True)
    else:
        click.echo("⚠️  Daemon not running. Using standalone mode...", err=True)
    
    if execute_tool_standalone:
        args = ['read_file', '--relative_path', relative_path]
        if offset:
            args.extend(['--offset', str(offset)])
        if limit:
            args.extend(['--limit', str(limit)])
        return execute_tool_standalone(args)
    else:
        click.echo("❌ Error: Standalone mode not available", err=True)
        return 1


@cli.command('search_for_pattern')
@click.option('--substring_pattern', help='Substring pattern to search for')
@click.option('--regex_pattern', '-r', help='Regex pattern to search for')
@click.option('--language', '-l', help='Language filter')
@click.option('--restrict_to_code_files', '-c', is_flag=True, help='Restrict to code files only')
@click.pass_context
def search_for_pattern(ctx, substring_pattern, regex_pattern, language, restrict_to_code_files):
    """Search for a pattern in the codebase."""
    params = {}
    if substring_pattern:
        params['substring_pattern'] = substring_pattern
    if regex_pattern:
        params['regex_pattern'] = regex_pattern
    if language:
        params['language'] = language
    if restrict_to_code_files:
        params['restrict_search_to_code_files'] = True
    
    url = get_daemon_url()
    use_json = ctx.obj.get('json', False)
    
    if url and check_daemon_status(url):
        click.echo(f"Using daemon at {url}...", err=True)
        try:
            result = call_daemon_tool(url, 'search_for_pattern', params)
            click.echo(format_result(result, use_json))
            return 0
        except Exception as e:
            click.echo(f"❌ Error calling daemon: {e}", err=True)
    else:
        click.echo("⚠️  Daemon not running. Using standalone mode...", err=True)
    
    if execute_tool_standalone:
        args = ['search_for_pattern']
        if substring_pattern:
            args.extend(['--substring_pattern', substring_pattern])
        if regex_pattern:
            args.extend(['--regex_pattern', regex_pattern])
        return execute_tool_standalone(args)
    else:
        click.echo("❌ Error: Standalone mode not available", err=True)
        return 1


if __name__ == '__main__':
    cli()