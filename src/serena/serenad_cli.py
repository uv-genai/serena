#!/usr/bin/env python3
"""
================================================================================
SERENAD: Serena Daemon Manager (Click-based CLI)
================================================================================

A beautiful, user-friendly command-line interface for managing the Serena daemon.

Usage:
    serenad start --project /path/to/project [--port 24282] [--detach]
    serenad stop
    serenad status
    serenad logs [--follow]
    serenad restart --project /path/to/project

Examples:
    \b
    $ serenad start --project .
    ✅ Daemon started successfully (PID: 12345)
       URL: http://127.0.0.1:24282
       Logs: ~/.serena/logs/daemon.log

    $ serenad status
    ✅ Daemon is running (PID: 12345)

    $ serenad stop
    ✅ Daemon stopped

================================================================================
"""

import os
import sys
import time
import signal
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

import click

# Import Serena components
try:
    from serena.mcp import SerenaMCPFactory
    from serena.agent import SerenaAgent
    from sensai.util import logging as slogging
except ImportError as e:
    click.echo(f"❌ Error: Could not import Serena modules. Ensure you are in the project root or have installed the package.", err=True)
    click.echo(f"   Details: {e}", err=True)
    sys.exit(1)

# Configuration
DEFAULT_PORT = 24282
DEFAULT_HOST = "127.0.0.1"
SERENA_DIR = Path.home() / ".serena"
PID_FILE = SERENA_DIR / "daemon.pid"
CONFIG_FILE = SERENA_DIR / "daemon.json"
LOG_FILE = SERENA_DIR / "logs" / "daemon.log"

# Ensure directories exist
SERENA_DIR.mkdir(parents=True, exist_ok=True)
(SERENA_DIR / "logs").mkdir(parents=True, exist_ok=True)


def _get_daemon_url() -> Optional[str]:
    """Get the daemon URL from config file."""
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        host = config.get('host', DEFAULT_HOST)
        port = config.get('port', DEFAULT_PORT)
        return f"http://{host}:{port}"
    except (json.JSONDecodeError, IOError, KeyError):
        return None


def _daemon_is_running() -> bool:
    """Check if daemon is running by checking PID file and process, or health endpoint."""
    url = _get_daemon_url()
    if url:
        # Try health endpoint first (most reliable)
        try:
            import requests
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
    
    # Fallback to PID file check
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError, OSError):
        return False


def _get_daemon_pid() -> Optional[int]:
    """Get the daemon PID if running."""
    if not PID_FILE.exists():
        return None
    
    try:
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    except (ValueError, IOError):
        return None


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    Serena Daemon Manager - Run Serena CLI tools as a persistent background service
    
    The daemon keeps SerenaAgent and language servers running in the background,
    providing ~15-20x faster response times for repeated commands.
    
    \b
    Quick Start:
        serenad start --project /path/to/project   # Start daemon
        serenad-cli find_symbol --name_path_pattern "MyClass"  # Use tools
        serenad stop                                # Stop daemon
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option('--project', '-p', required=True, help='Path to the project to activate')
@click.option('--port', '-P', type=int, default=DEFAULT_PORT, help=f'Daemon port (default: {DEFAULT_PORT})')
@click.option('--host', '-H', default=DEFAULT_HOST, help=f'Daemon host (default: {DEFAULT_HOST})')
@click.option('--log-level', '-l', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), default='INFO', help='Log level')
@click.option('--detach', '-d', is_flag=True, help='Run daemon in background (detached mode)')
def start(project, port, host, log_level, detach):
    """Start the Serena daemon."""
    project_path = Path(project).resolve()
    
    if not project_path.exists():
        click.echo(f"❌ Error: Project path does not exist: {project_path}", err=True)
        sys.exit(1)
    
    if _daemon_is_running():
        pid = _get_daemon_pid()
        click.echo(f"⚠️  Daemon is already running (PID: {pid})", err=True)
        click.echo(f"   Stop it first with: serenad stop", err=True)
        sys.exit(1)
    
    click.echo(f"🚀 Starting Serena daemon for project: {project_path}", err=True)
    click.echo(f"   Port: {port}", err=True)
    click.echo(f"   Host: {host}", err=True)
    
    if detach:
        click.echo(f"   Starting in detached mode...", err=True)
        
        # Prepare environment
        env = os.environ.copy()
        env['SERENA_DAEMON_MODE'] = '1'
        
        # Start detached process
        log_file = open(LOG_FILE, 'a')
        process = subprocess.Popen(
            [sys.executable, '-m', 'serena.serenad_runner', 
             '--project', str(project_path),
             '--port', str(port),
             '--host', host,
             '--log-file', str(LOG_FILE)],
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
            cwd=str(project_path)
        )
        
        # Wait a moment for the daemon to start
        time.sleep(2)
        
        if _daemon_is_running():
            pid = _get_daemon_pid()
            click.echo(f"✅ Daemon started successfully (PID: {pid})", err=True)
            click.echo(f"   URL: http://{host}:{port}", err=True)
            click.echo(f"   Logs: {LOG_FILE}", err=True)
            click.echo(f"   Stop with: serenad stop", err=True)
        else:
            click.echo(f"❌ Failed to start daemon. Check logs: {LOG_FILE}", err=True)
            sys.exit(1)
    else:
        # Run in foreground (for debugging)
        click.echo(f"   Running in foreground mode (Ctrl+C to stop)...", err=True)
        os.execvp(
            sys.executable,
            [sys.executable, '-m', 'serena.serenad_runner', str(project_path), host, str(port), log_level]
        )


@cli.command()
def stop():
    """Stop the running daemon."""
    if not _daemon_is_running():
        click.echo("⚠️  Daemon is not running", err=True)
        sys.exit(0)
    
    pid = _get_daemon_pid()
    click.echo(f"🛑 Stopping daemon (PID: {pid})...", err=True)
    
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        
        # Force kill if still running
        if _daemon_is_running():
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
        
        # Remove PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
        
        click.echo("✅ Daemon stopped.", err=True)
        
    except OSError as e:
        click.echo(f"❌ Error stopping daemon: {e}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Show daemon status."""
    if _daemon_is_running():
        pid = _get_daemon_pid()
        url = _get_daemon_url()
        
        # Try to get more info from health endpoint
        try:
            import requests
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                health_data = response.json()
                start_time = health_data.get('start_time', 'unknown')
                click.echo(f"✅ Daemon is running", err=True)
                click.echo(f"   PID: {pid}", err=True)
                click.echo(f"   URL: {url}", err=True)
                click.echo(f"   Started: {start_time}", err=True)
                click.echo(f"   Logs: {LOG_FILE}", err=True)
                return
        except:
            pass
        
        # Fallback to basic info
        click.echo(f"✅ Daemon is running", err=True)
        click.echo(f"   PID: {pid}", err=True)
        click.echo(f"   URL: {url}", err=True)
        click.echo(f"   Logs: {LOG_FILE}", err=True)
    else:
        click.echo("⚠️  Daemon is not running", err=True)
        click.echo(f"   Start with: serenad start --project /path/to/project", err=True)


@cli.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output (like tail -f)')
@click.option('--lines', '-n', type=int, default=50, help='Number of lines to show (default: 50)')
def logs(follow, lines):
    """Show daemon logs."""
    if not LOG_FILE.exists():
        click.echo("⚠️  No log file found. Daemon may not have been started yet.", err=True)
        sys.exit(0)
    
    if follow:
        # Use tail -f equivalent
        try:
            subprocess.run(['tail', '-f', '-n', str(lines), str(LOG_FILE)])
        except FileNotFoundError:
            # Fallback for systems without tail
            click.echo("⚠️  'tail' command not found. Showing last lines instead...", err=True)
            with open(LOG_FILE, 'r') as f:
                lines_list = f.readlines()
                for line in lines_list[-lines:]:
                    click.echo(line, nl=False)
    else:
        # Show last N lines
        with open(LOG_FILE, 'r') as f:
            lines_list = f.readlines()
            for line in lines_list[-lines:]:
                click.echo(line, nl=False)


@cli.command()
@click.option('--project', '-p', required=True, help='Path to the project to activate')
@click.option('--port', '-P', type=int, default=DEFAULT_PORT, help=f'Daemon port (default: {DEFAULT_PORT})')
@click.option('--host', '-H', default=DEFAULT_HOST, help=f'Daemon host (default: {DEFAULT_HOST})')
@click.option('--log-level', '-l', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), default='INFO', help='Log level')
def restart(project, port, host, log_level):
    """Restart the daemon."""
    if _daemon_is_running():
        click.echo("🔄 Restarting daemon...", err=True)
        stop()
        time.sleep(1)
    
    start.callback(project=project, port=port, host=host, log_level=log_level, detach=True)


if __name__ == '__main__':
    import signal
    cli()