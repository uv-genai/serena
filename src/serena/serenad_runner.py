#!/usr/bin/env python3
"""
Simple HTTP API daemon runner for Serena.
"""

import os
import sys
import argparse
import logging

try:
    from serena.serenad_api import run_server
except ImportError as e:
    print(f"Error: Could not import Serena modules: {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Serena Daemon Runner")
    parser.add_argument("--project", required=True, help="Path to the project")
    parser.add_argument("--port", type=int, required=True, help="Port to run on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--log-file", help="Path to log file")
    parser.add_argument("--pid-file", help="Path to PID file")
    
    args = parser.parse_args()
    
    # Write PID file if specified
    if args.pid_file:
        from pathlib import Path
        pid_file = Path(args.pid_file)
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()))
    
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
    
    logger = logging.getLogger(__name__)
    logger.info(f"Daemon runner starting for project: {args.project}")
    logger.info(f"Server will run on http://{args.host}:{args.port}")
    logger.info(f"Process PID: {os.getpid()}")
    
    try:
        run_server(args.host, args.port, args.project)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Daemon runner stopped")

if __name__ == "__main__":
    main()
