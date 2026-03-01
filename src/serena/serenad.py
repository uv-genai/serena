#!/usr/bin/env python3
"""
================================================================================
SERENAD: Serena Daemon Manager
================================================================================

This script provides a daemon mode for the Serena CLI tools.
It allows the MCP server to run persistently in the background, providing
fast (~0.1s) responses to CLI commands by avoiding the ~2s startup overhead
of creating new language server instances on every invocation.

ARCHITECTURE:

┌─────────────────────────────────────────────────────────────────────────┐
│                          STANDALONE MODE (Current)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  $ serena-cli find_symbol ...                                            │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  New Process: Parse → Create Agent → Start LSPs (~2s) → Execute │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           DAEMON MODE (New)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  $ serenad start --project /path                                 │    │
│  │       │                                                          │    │
│  │       ▼                                                          │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │  serenad (Daemon)                                        │    │    │
│  │  │  - Starts MCP Server (SSE/HTTP)                          │    │    │
│  │  │  - Initializes SerenaAgent + LSPs (one-time, ~2s)        │    │    │
│  │  │  - Listens on http://127.0.0.1:24282                     │    │    │
│  │  │  - PID: ~/.serena/daemon.pid                             │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  $ serenad-cli find_symbol ...  (~0.1s, no LSP startup)         │    │
│  │       │                                                          │    │
│  │       ▼                                                          │    │
│  │  ┌─────────────────┐      HTTP POST      ┌─────────────────┐    │    │
│  │  │ serenad-cli     │ ──────────────────► │  Daemon         │    │    │
│  │  │ (thin client)   │   /tools/call       │  (already       │    │    │
│  │  │                 │                     │   running)      │    │    │
│  │  │                 │ ◄────────────────── │                 │    │    │
│  │  │                 │    JSON Result      │  LSPs warm      │    │    │
│  │  └─────────────────┘                     └─────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

USAGE:
    serenad start --project /path/to/project [--port 24282] [--detach]
    serenad stop
    serenad status
    serenad logs
    serenad restart

FILES:
    ~/.serena/daemon.pid          - PID of running daemon
    ~/.serena/daemon.json         - Daemon connection info (host, port)
    ~/.serena/logs/daemon.log     - Daemon output logs

================================================================================
"""

import os
import sys
import time
import signal
import json
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Optional

# Import Serena MCP components (these are existing, we just use them)
try:
    from serena.mcp import SerenaMCPFactory
    from serena.agent import SerenaAgent
    from sensai.util import logging as slogging
except ImportError as e:
    print(f"Error: Could not import Serena modules. Ensure you are in the project root or have installed the package.")
    print(f"Details: {e}")
    sys.exit(1)

# Configuration
DEFAULT_PORT = 24282
DEFAULT_HOST = "127.0.0.1"
SERENA_DIR = Path.home() / ".serena"
PID_FILE = SERENA_DIR / "daemon.pid"
CONFIG_FILE = SERENA_DIR / "daemon.json"
LOG_DIR = SERENA_DIR / "logs"
LOG_FILE = LOG_DIR / "daemon.log"


def setup_logging():
    """Setup logging to both file and console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler (for start/stop messages)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_daemon_info() -> Optional[dict]:
    """Read daemon connection info from config file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_daemon_info(host: str, port: int, pid: int):
    """Save daemon connection info to config file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump({
            "host": host,
            "port": port,
            "pid": pid,
            "started_at": time.time()
        }, f, indent=2)


def remove_daemon_info():
    """Remove daemon config file."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def is_daemon_running() -> bool:
    """Check if daemon is running by checking PID file and process."""
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError, OSError):
        # Process doesn't exist or PID file is invalid
        return False


def start_daemon(project_path: str, port: int = DEFAULT_PORT, host: str = DEFAULT_HOST, detach: bool = True):
    """
    Start the Serena daemon.
    
    Args:
        project_path: Path to the project to activate
        port: Port to run the MCP server on
        host: Host to bind to
        detach: If True, run as a background process
    """
    logger = setup_logging()
    
    if is_daemon_running():
        logger.error("Daemon is already running.")
        info = get_daemon_info()
        if info:
            logger.error(f"  PID: {info.get('pid')}")
            logger.error(f"  URL: http://{info.get('host')}:{info.get('port')}")
        return 1
    
    logger.info(f"Starting Serena daemon for project: {project_path}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Host: {host}")
    
    # Prepare the daemon runner script
    # We use a separate process to run the MCP server
    daemon_script = Path(__file__).parent / "serenad_runner.py"
    
    if detach:
        # Start as background process
        logger.info("Starting in detached mode...")
        
        # Create a subprocess that runs the daemon runner module
        cmd = [
            sys.executable, "-m", "serena.serenad_runner",
            "--project", project_path,
            "--port", str(port),
            "--host", host,
            "--log-file", str(LOG_FILE),
            "--pid-file", str(PID_FILE)
        ]
        
        # Start the process with nohup-like behavior
        import subprocess
        with open(os.devnull, 'w') as devnull:
            process = subprocess.Popen(
                cmd,
                stdout=devnull,
                stderr=devnull,
                start_new_session=True  # Detach from controlling terminal
            )
        
        pid = process.pid
        
        # Write PID file immediately so is_daemon_running() works
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
        
        # Wait a moment for the daemon to initialize
        time.sleep(2)
        
        # Check if process is still running
        try:
            os.kill(pid, 0)  # Check if process exists
            save_daemon_info(host, port, pid)
            logger.info(f"✅ Daemon started successfully (PID: {pid})")
            logger.info(f"   URL: http://{host}:{port}")
            logger.info(f"   Logs: {LOG_FILE}")
            logger.info(f"   Stop with: serenad stop")
            return 0
        except OSError:
            logger.error("❌ Daemon failed to start. Check logs for details.")
            PID_FILE.unlink(missing_ok=True)
            return 1
    else:
        # Run in foreground (for debugging)
        logger.info("Starting in foreground mode (Ctrl+C to stop)...")
        save_daemon_info(host, port, os.getpid())
        
        # Run the daemon runner module
        try:
            # Execute the runner module using -m flag
            import subprocess
            result = subprocess.run([
                sys.executable, "-m", "serena.serenad_runner",
                "--project", project_path,
                "--port", str(port),
                "--host", host,
                "--log-file", str(LOG_FILE)
            ])
            return result.returncode
        except KeyboardInterrupt:
            logger.info("Stopping daemon...")
            return 0
        finally:
            remove_daemon_info()


def stop_daemon():
    """Stop the running daemon."""
    logger = setup_logging()
    
    if not is_daemon_running():
        logger.error("Daemon is not running.")
        return 1
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        logger.info(f"Stopping daemon (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to terminate
        for _ in range(10):
            if not is_daemon_running():
                break
            time.sleep(0.5)
        
        if is_daemon_running():
            logger.error("Daemon did not stop gracefully. Force killing...")
            os.kill(pid, signal.SIGKILL)
        
        remove_daemon_info()
        logger.info("✅ Daemon stopped.")
        return 0
        
    except ProcessLookupError:
        logger.error("Daemon process not found. Cleaning up PID file...")
        PID_FILE.unlink(missing_ok=True)
        remove_daemon_info()
        return 1
    except Exception as e:
        logger.error(f"Error stopping daemon: {e}")
        return 1


def status_daemon():
    """Show daemon status."""
    logger = setup_logging()
    
    if not is_daemon_running():
        logger.info("Daemon is not running.")
        return 1
    
    info = get_daemon_info()
    if info:
        logger.info("✅ Daemon is running")
        logger.info(f"  PID: {info.get('pid')}")
        logger.info(f"  URL: http://{info.get('host')}:{info.get('port')}")
        logger.info(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info.get('started_at', 0)))}")
        logger.info(f"  Logs: {LOG_FILE}")
        return 0
    else:
        logger.error("Daemon appears to be running but config is missing.")
        return 1


def show_logs():
    """Show daemon logs."""
    if not LOG_FILE.exists():
        print("No logs found.")
        return 1
    
    # Tail the log file
    try:
        subprocess.run(["tail", "-f", str(LOG_FILE)])
    except FileNotFoundError:
        # Fallback for systems without 'tail'
        with open(LOG_FILE, 'r') as f:
            print(f.read())
    return 0





def main():
    """Main entry point for serenad command."""
    parser = argparse.ArgumentParser(
        description="Serena Daemon Manager - Run Serena CLI tools as a persistent background service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  serenad start --project /path/to/project
  serenad start --project . --port 24283
  serenad start --project . --detach
  serenad status
  serenad stop
  serenad logs
  serenad restart
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the daemon")
    start_parser.add_argument("--project", "-p", required=True, help="Path to the project to activate")
    start_parser.add_argument("--port", "-P", type=int, default=DEFAULT_PORT, help=f"Port to run on (default: {DEFAULT_PORT})")
    start_parser.add_argument("--host", "-H", default=DEFAULT_HOST, help=f"Host to bind to (default: {DEFAULT_HOST})")
    start_parser.add_argument("--detach", "-d", action="store_true", default=True, help="Run as background process (default: True)")
    start_parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground (for debugging)")
    
    # Stop command
    subparsers.add_parser("stop", help="Stop the daemon")
    
    # Status command
    subparsers.add_parser("status", help="Show daemon status")
    
    # Logs command
    subparsers.add_parser("logs", help="Show daemon logs")
    
    # Restart command
    subparsers.add_parser("restart", help="Restart the daemon")
    
    args = parser.parse_args()
    
    if args.command == "start":
        return start_daemon(
            project_path=args.project,
            port=args.port,
            host=args.host,
            detach=not args.foreground
        )
    elif args.command == "stop":
        return stop_daemon()
    elif args.command == "status":
        return status_daemon()
    elif args.command == "logs":
        return show_logs()
    elif args.command == "restart":
        stop_daemon()
        time.sleep(1)
        return start_daemon(
            project_path=args.project if hasattr(args, 'project') else ".",
            port=args.port if hasattr(args, 'port') else DEFAULT_PORT,
            host=args.host if hasattr(args, 'host') else DEFAULT_HOST
        )
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())