#!/usr/bin/env python3
"""
Example script demonstrating how to use the serena-cli tool.

This script shows various ways to interact with Serena's tools from the command line.
"""

import subprocess
import sys


def run_command(cmd: list[str], description: str) -> None:
    """Run a command and print its output."""
    print(f"\n{'='*80}")
    print(f"Example: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # Filter out log messages for cleaner output
        output_lines = [line for line in result.stdout.split('\n') 
                       if not line.startswith('2026-') and 'INFO' not in line and 'WARNING' not in line]
        output = '\n'.join(output_lines).strip()
        
        if output:
            print(output[:2000])  # Limit output length
        if result.stderr:
            print(f"Stderr: {result.stderr[:500]}")
            
    except subprocess.TimeoutExpired:
        print("Command timed out")
    except Exception as e:
        print(f"Error: {e}")


def main() -> None:
    """Run example commands."""
    print("Serena CLI Examples")
    print("="*80)
    
    # Example 1: List all available tools
    run_command(
        ["uv", "run", "serena-cli", "tools"],
        "List all available Serena tools"
    )
    
    # Example 2: Read a file
    run_command(
        ["uv", "run", "serena-cli", "read_file", "--project", ".", "--relative_path", "README.md"],
        "Read the README.md file"
    )
    
    # Example 3: List directory contents
    run_command(
        ["uv", "run", "serena-cli", "list_dir", "--project", ".", "--relative_path", "src/serena/tools"],
        "List files in the tools directory"
    )
    
    # Example 4: Get symbol overview
    run_command(
        ["uv", "run", "serena-cli", "get_symbols_overview", "--project", ".", "--relative_path", "src/serena/cli_tools.py"],
        "Get symbol overview of cli_tools.py"
    )
    
    # Example 5: Find a symbol
    run_command(
        ["uv", "run", "serena-cli", "find_symbol", "--project", ".", "--name_path_pattern", "SerenaCLI", "--include_body", "true"],
        "Find the SerenaCLI class"
    )
    
    # Example 6: Search for a pattern
    run_command(
        ["uv", "run", "serena-cli", "search_for_pattern", "--project", ".", "--substring_pattern", "def main", "--restrict_search_to_code_files", "true"],
        "Search for 'def main' in code files"
    )
    
    # Example 7: Execute a shell command
    run_command(
        ["uv", "run", "serena-cli", "execute_shell_command", "--project", ".", "--command", "ls -la src/serena/tools"],
        "Execute shell command to list tools directory"
    )
    
    # Example 8: Get tool description
    run_command(
        ["uv", "run", "serena-cli", "tool-description", "read_file"],
        "Get description of read_file tool"
    )
    
    # Example 9: List projects
    run_command(
        ["uv", "run", "serena-cli", "projects"],
        "List registered Serena projects"
    )
    
    # Example 10: List contexts
    run_command(
        ["uv", "run", "serena-cli", "contexts"],
        "List available Serena contexts"
    )
    
    # Example 11: List modes
    run_command(
        ["uv", "run", "serena-cli", "modes"],
        "List available Serena modes"
    )
    
    print("\n" + "="*80)
    print("Examples completed!")
    print("="*80)
    print("\nFor more information, run: serena-cli --help")
    print("For tool-specific help, run: serena-cli <tool_name> --help")


if __name__ == "__main__":
    main()