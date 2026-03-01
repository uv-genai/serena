#!/usr/bin/env python3
"""
================================================================================
SERENAD EXAMPLE: Using the Serena Daemon
================================================================================

This script demonstrates how to use the Serena daemon for fast CLI operations.

PREREQUISITES:
1. Install the package: uv pip install -e .
2. Start the daemon: serenad start --project /path/to/project

USAGE:
    python serenad_example.py

================================================================================
"""

import subprocess
import time
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str):
    """Run a command and print the result."""
    print(f"\n{'='*60}")
    print(f"Command: {description}")
    print(f"{'='*60}")
    print(f"$ {' '.join(cmd)}")
    print()
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"[stderr] {result.stderr}", file=sys.stderr)
    
    print(f"\n[Timing] {elapsed:.3f}s")
    return result.returncode


def main():
    print("="*60)
    print("SERENAD DEMO: Fast Serena CLI via Daemon")
    print("="*60)
    
    # Check if daemon is running
    print("\n1. Checking daemon status...")
    run_command(["serenad", "status"], "Check daemon status")
    
    # If not running, start it
    if run_command(["serenad", "status"], "Check status")[0] != 0:
        print("\n2. Starting daemon...")
        # Use current directory as project
        project_path = str(Path.cwd())
        run_command(["serenad", "start", "--project", project_path], 
                   f"Start daemon for project: {project_path}")
        
        # Wait for daemon to be ready
        print("\nWaiting for daemon to be ready...")
        time.sleep(3)
    
    # Now run some fast commands
    print("\n3. Running fast CLI commands...")
    
    # List tools
    run_command(["serenad-cli", "tools"], "List available tools")
    
    # Find a symbol
    run_command(["serenad-cli", "find_symbol", "--name_path_pattern", "main"], 
               "Find 'main' symbol")
    
    # Read a file (if it exists)
    if Path("README.md").exists():
        run_command(["serenad-cli", "read_file", "--relative_path", "README.md"],
                   "Read README.md")
    
    # Get symbols overview
    if Path("src/serena/serenad.py").exists():
        run_command(["serenad-cli", "get_symbols_overview", 
                    "--relative_path", "src/serena/serenad.py"],
                   "Get symbols from serenad.py")
    
    # Search for pattern
    run_command(["serenad-cli", "search_for_pattern", 
                "--substring_pattern", "TODO"],
               "Search for 'TODO' pattern")
    
    # JSON output example
    run_command(["serenad-cli", "--json", "find_symbol", 
                "--name_path_pattern", "main"],
               "Find symbol with JSON output")
    
    # Stop the daemon
    print("\n4. Stopping daemon...")
    run_command(["serenad", "stop"], "Stop daemon")
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nKey Takeaways:")
    print("  • Daemon startup: ~2 seconds (one-time)")
    print("  • Subsequent commands: ~0.1 seconds")
    print("  • Speedup: ~20x faster for repeated commands")
    print("  • State preserved between commands")
    print("  • Language servers stay warm")


if __name__ == "__main__":
    main()