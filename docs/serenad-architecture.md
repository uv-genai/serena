# Serena Daemon (serenad) Architecture

## Overview

The Serena Daemon (`serenad`) provides a persistent background service for the Serena CLI tools. It eliminates the ~2 second startup overhead of creating new language server instances on every CLI invocation by keeping the MCP server and language servers running continuously.

## Problem Statement

### Standalone Mode (Current)

Every time you run a `serena-cli` command:

1. A new Python process is created
2. `SerenaAgent` is initialized
3. Language servers (Pyright, TypeScript, etc.) are downloaded/started
4. Tool is executed
5. Process exits

**Result:** ~2 seconds of overhead per command, even for simple operations.

### Daemon Mode (New)

The daemon runs once as a background process:

1. `serenad start` - Initializes agent and language servers once (~2 seconds)
2. Subsequent `serenad-cli` commands - Fast HTTP calls (~0.1 seconds)
3. `serenad stop` - Shuts down the daemon

**Result:** Instant responses after initial startup, state preserved between commands.

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          STANDALONE MODE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  $ serena-cli find_symbol --project . --name_path_pattern "MyClass"      │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    New Python Process                            │    │
│  │  ┌─────────────────┐                                             │    │
│  │  │ 1. Parse Args   │                                             │    │
│  │  │ 2. Create Agent │  ~2 seconds                                 │    │
│  │  │ 3. Start LSPs   │  (language servers initialize)              │    │
│  │  │ 4. Execute Tool │                                             │    │
│  │  │ 5. Print Result │                                             │    │
│  │  │ 6. Exit         │                                             │    │
│  │  └─────────────────┘                                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  $ serena-cli read_file --project . --relative_path "main.py"            │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Another New Python Process (~2s again)              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           DAEMON MODE                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   First: Start Daemon                            │    │
│  │                                                                  │    │
│  │  $ serenad start --project /path/to/project                      │    │
│  │       │                                                          │    │
│  │       ▼                                                          │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │            Serena MCP Server (Daemon)                    │    │    │
│  │  │                                                          │    │    │
│  │  │  ┌─────────────────┐  ┌─────────────────┐               │    │    │
│  │  │  │  SerenaAgent    │  │ Language Servers│               │    │    │
│  │  │  │  (persistent)   │  │ (Pyright, TS...)│               │    │    │
│  │  │  └─────────────────┘  └─────────────────┘               │    │    │
│  │  │                                                          │    │    │
│  │  │  Listening on http://127.0.0.1:24282                     │    │    │
│  │  │  PID: 12345  |  State: Ready                             │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Subsequent: Fast CLI Invocations                    │    │
│  │                                                                  │    │
│  │  $ serenad-cli find_symbol --name_path_pattern "MyClass"         │    │
│  │       │                                                          │    │
│  │       ▼                                                          │    │
│  │  ┌─────────────────┐      HTTP POST       ┌─────────────────┐   │    │
│  │  │ serenad-cli     │ ──────────────────►  │  Daemon         │   │    │
│  │  │ (thin client)   │   /tools/call        │  (already       │   │    │
│  │  │                 │                      │   running)      │   │    │
│  │  │  ~0.1 seconds   │ ◄────────────────── │                 │   │    │
│  │  │                 │      JSON Result     │  LSPs warm      │   │    │
│  │  └─────────────────┘                      └─────────────────┘   │    │
│  │                                                                  │    │
│  │  $ serenad-cli read_file --relative_path "main.py"               │    │
│  │       │                     │                                    │    │
│  │       └─────────────────────┘                                    │    │
│  │              Reuses same daemon (~0.1s)                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Communication Protocol

The daemon uses the Model Context Protocol (MCP) over HTTP with Server-Sent Events (SSE):

```
┌──────────────────┐                    ┌──────────────────┐
│   serenad-cli    │                    │   MCP Server     │
│   (Client)       │                    │   (Daemon)       │
├──────────────────┤                    ├──────────────────┤
│                  │                    │                  │
│  GET /health     │ ─────────────────► │  Health check    │
│                  │ ◄───────────────── │  200 OK          │
│                  │                    │                  │
│  POST /tools/call│ ─────────────────► │                  │
│  {               │                    │  Execute tool    │
│    "method":     │                    │  with LSP        │
│    "tools/call", │                    │                  │
│    "params": {   │                    │                  │
│      "name":     │                    │                  │
│      "find_symbol",│                  │                  │
│      "arguments":│                    │                  │
│      {...}       │                    │                  │
│    }             │                    │                  │
│  }               │                    │                  │
│                  │ ◄───────────────── │                  │
│                  │   JSON Response    │                  │
│                  │   {result}         │                  │
│                  │                    │                  │
└──────────────────┘                    └──────────────────┘
```

## Components

### 1. Daemon Manager (`serenad.py`)

**File:** `src/serena/serenad.py`

**Responsibilities:**
- Start/stop/status/restart the daemon
- Manage PID file (`~/.serena/daemon.pid`)
- Manage configuration (`~/.serena/daemon.json`)
- Log management (`~/.serena/logs/daemon.log`)

**Key Functions:**
```python
start_daemon(project_path, port, host, detach)
stop_daemon()
status_daemon()
show_logs()
```

### 2. Daemon Runner (`serenad_runner.py`)

**File:** `src/serena/serenad_runner.py`

**Responsibilities:**
- Initialize `SerenaAgent` with the project
- Start language servers (one-time cost)
- Create and run MCP server with SSE transport
- Handle graceful shutdown

**Key Code:**
```python
agent = SerenaAgent(project_paths=[project_path], enable_web_console=False)
factory = SerenaMCPFactory(agent)
mcp_server = factory.create_mcp_server()
mcp_server.run(transport="sse", host=host, port=port)
```

### 3. CLI Client (`serenad_client.py`)

**File:** `src/serena/serenad_client.py`

**Responsibilities:**
- Parse CLI arguments
- Read daemon connection info from `~/.serena/daemon.json`
- Send HTTP requests to daemon
- Fall back to standalone mode if daemon is not running
- Format and display results

**Key Functions:**
```python
get_daemon_url()
check_daemon_status(url)
call_daemon_tool(url, tool_name, params)
execute_tool_with_daemon(tool_name, params, use_json)
```

## File Structure

```
~/.serena/
├── daemon.pid          # PID of running daemon
├── daemon.json         # Daemon config (host, port, pid)
└── logs/
    └── daemon.log      # Daemon output logs

Project Root/
└── .serena/
    └── ...             # Project-specific Serena data
```

## Usage

### Starting the Daemon

```bash
# Start daemon with a specific project
serenad start --project /path/to/project

# Start daemon with custom port
serenad start --project . --port 24283

# Start daemon in foreground (for debugging)
serenad start --project . --foreground

# Start daemon detached (default)
serenad start --project . --detach
```

### Using the CLI Client

```bash
# All tool commands work the same, just faster
serenad-cli find_symbol --name_path_pattern "MyClass" --include_body
serenad-cli read_file --relative_path "src/main.py"
serenad-cli get_symbols_overview --relative_path "src/main.py"
serenad-cli search_for_pattern --substring_pattern "TODO"
serenad-cli replace_in_file --relative_path "src/main.py" --old_text "foo" --new_text "bar"

# JSON output
serenad-cli --json find_symbol --name_path_pattern "MyClass"

# With project activation
serenad-cli --project . read_file --relative_path "src/main.py"
```

### Managing the Daemon

```bash
# Check daemon status
serenad status

# Stop the daemon
serenad stop

# Restart the daemon
serenad restart

# View daemon logs
serenad logs

# View logs with tail
tail -f ~/.serena/logs/daemon.log
```

## Comparison

| Feature | Standalone Mode | Daemon Mode |
|---------|----------------|-------------|
| **Startup Time** | ~2 seconds per command | ~0.1 seconds (after daemon start) |
| **Initial Cost** | None | ~2 seconds (one-time) |
| **Memory Usage** | Fresh process each time | Persistent ~200-500MB |
| **State** | Lost after each call | Preserved between calls |
| **Caching** | Cold caches each time | Warm caches, faster lookups |
| **Complexity** | Simple, no state | Requires daemon management |
| **Use Case** | Occasional use, scripts | Frequent use, interactive |
| **Network** | Local only | Local HTTP (can be remote) |

## Performance

### Standalone Mode
```
$ time serena-cli find_symbol --project . --name_path_pattern "MyClass"
...
real    0m2.345s
user    0m1.890s
sys     0m0.455s
```

### Daemon Mode
```
$ time serenad-cli find_symbol --name_path_pattern "MyClass"
...
real    0m0.123s
user    0m0.045s
sys     0m0.078s
```

**Speedup:** ~18x faster for subsequent commands

## Troubleshooting

### Daemon won't start

```bash
# Check if port is in use
lsof -i :24282

# Check for stale PID file
rm ~/.serena/daemon.pid

# Check daemon logs
cat ~/.serena/logs/daemon.log

# Start in foreground to see errors
serenad start --project . --foreground
```

### Connection refused

```bash
# Verify daemon is running
serenad status

# Check daemon URL
cat ~/.serena/daemon.json

# Restart daemon
serenad restart
```

### Language server issues

```bash
# Restart the daemon to reinitialize language servers
serenad restart

# Check daemon logs for LSP errors
serenad logs

# Start in foreground to see detailed logs
serenad start --project . --foreground
```

### Daemon crashes

```bash
# Check logs for crash reason
tail -f ~/.serena/logs/daemon.log

# Clean up stale PID
rm ~/.serena/daemon.pid

# Restart
serenad start --project .
```

## Implementation Details

### Daemon Process Management

The daemon uses Unix session detachment for background execution:

```python
# In serenad.py
process = subprocess.Popen(
    cmd,
    stdout=devnull,
    stderr=devnull,
    start_new_session=True  # Detach from controlling terminal
)
```

### MCP Server Transport

The daemon uses SSE (Server-Sent Events) transport for HTTP communication:

```python
# In serenad_runner.py
mcp_server.run(
    transport="sse",
    host=self.host,
    port=self.port
)
```

### Tool Invocation

Tools are invoked via JSON-RPC style requests:

```python
# In serenad_client.py
request_data = {
    "method": "tools/call",
    "params": {
        "name": tool_name,
        "arguments": params
    },
    "jsonrpc": "2.0",
    "id": 1
}
```

## Future Enhancements

1. **Multiple Projects**: Support for multiple project sessions
2. **Authentication**: Token-based authentication for remote access
3. **WebSocket Support**: Alternative to SSE for bidirectional communication
4. **Auto-restart**: Automatically restart daemon on crash
5. **Health Monitoring**: Periodic health checks and automatic recovery
6. **Unix Socket**: Use Unix domain socket instead of TCP for local communication
7. **CLI Completion**: Bash/Zsh completion for tool names and parameters

## Security Considerations

- Daemon only binds to `127.0.0.1` by default (localhost only)
- No authentication currently implemented (local use only)
- For remote access, use SSH tunneling or VPN
- Consider adding token authentication for production use

## Related Documentation

- [Serena CLI Tool](./cli-tool.md) - Standalone CLI usage
- [Serena Agent](../src/serena/agent.py) - Agent implementation
- [Serena MCP](../src/serena/mcp.py) - MCP server implementation
- [MCP Protocol](https://modelcontextprotocol.io/) - Model Context Protocol spec