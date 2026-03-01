# Serena Daemon Mode (serenad)

## Overview

Serena can operate in two modes:

1. **Standalone Mode** (default via `serena-cli`): Each CLI invocation creates a new Python process, initializes a `SerenaAgent`, starts language servers, executes the tool, and exits. Simple but has ~2-3 seconds of startup overhead per invocation.

2. **Daemon Mode** (via `serenad` + `serenad-cli`): A background HTTP server runs continuously with a persistent `SerenaAgent` and warm language servers. The thin client (`serenad-cli`) communicates via simple REST HTTP calls, providing **~15-20x faster** response times (~0.1-0.6s vs ~2-3s).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STANDALONE MODE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  $ serena-cli find_symbol --project . --name_path_pattern "MyClass"      │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    New Python Process                            │    │
│  │  ┌─────────────────┐                                             │    │
│  │  │ 1. Parse Args   │                                             │    │
│  │  │ 2. Create Agent │  ~2-3 seconds                               │    │
│  │  │ 3. Start LSPs   │  (Pyright, TypeScript initialize)           │    │
│  │  │ 4. Execute Tool │                                             │    │
│  │  │ 5. Print Result │                                             │    │
│  │  │ 6. Exit         │                                             │    │
│  │  └─────────────────┘                                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Next command: Another fresh process (~2-3s again)                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           DAEMON MODE                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STEP 1: Start Daemon (once per session)                                 │
│  ───────────────────────────────────────────────────────────────────     │
│                                                                          │
│  $ serenad start --project /path/to/project                              │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │            serenad_runner.py (background process)               │    │
│  │  ┌───────────────────────────────────────────────────────────┐  │    │
│  │  │  serenad_api.py (Flask HTTP Server on port 24282)         │  │    │
│  │  │                                                           │  │    │
│  │  │  Endpoints:                                               │  │    │
│  │  │  • GET  /health        → {"status": "healthy"}            │  │    │
│  │  │  • GET  /tools         → {"tools": [...]}                 │  │    │
│  │  │  • POST /tools/<name>  → Execute tool                     │  │    │
│  │  │                                                           │  │    │
│  │  │  ┌───────────────────────────────────────────────────┐   │  │    │
│  │  │  │  SerenaAgent (persistent)                         │   │  │    │
│  │  │  │  • Language Servers (warm):                       │   │  │    │
│  │  │  │    - Pyright (Python)                             │   │  │    │
│  │  │  │    - TypeScript (Vue/JS)                          │   │  │    │
│  │  │  │  • All 41 Tools ready                             │   │  │    │
│  │  │  │  • Symbol caches loaded                           │   │  │    │
│  │  │  └───────────────────────────────────────────────────┘   │  │    │
│  │  └───────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│       ✓ PID written to ~/.serena/daemon.pid                             │
│       ✓ Config written to ~/.serena/daemon.json                         │
│                                                                          │
│  STEP 2: Fast CLI Invocations (repeated)                                 │
│  ───────────────────────────────────────────────────────────────────     │
│                                                                          │
│  $ serenad-cli find_symbol --name_path_pattern "MyClass" --include_body  │
│       │                                                                  │
│       ▼ HTTP POST                                                       │
│  ┌─────────────┐           http://127.0.0.1:24282/tools/find_symbol     │
│  │ serenad-cli │ ───────────────────────────────────────────────────►   │
│  │ (thin client│           {                                             │
│  │  ~0.1-0.6s  │           │  "name_path_pattern": "MyClass",          │
│  └─────────────┘           │  "include_body": true                      │
│                            │}                                            │
│                            ▲                                             │
│                            │ HTTP Response                               │
│                            └───────────────────────────────────────────  │
│                            {                                              │
│                              "success": true,                            │
│                              "result": [...]                             │
│                            }                                              │
│                                                                          │
│  Subsequent commands reuse the same daemon (~0.1-0.6s each)              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Communication Protocol

The daemon uses a **simple REST HTTP API** (not MCP SSE):

```
┌──────────────────┐                    ┌──────────────────┐
│   serenad-cli    │                    │   Flask Server   │
│   (Client)       │                    │   (Daemon)       │
├──────────────────┤                    ├──────────────────┤
│                  │                    │                  │
│  GET /health     │ ────────────────►  │  Check status    │
│                  │ ◄────────────────  │                  │
│                  │  {"status":"healthy"}                 │
│                  │                    │                  │
│  GET /tools      │ ────────────────►  │  List tools      │
│                  │ ◄────────────────  │                  │
│                  │  {"tools":["read_  │                  │
│                  │   file","find_..."]}                 │
│                  │                    │                  │
│  POST /tools/    │ ────────────────►  │  Validate params │
│   find_symbol    │  JSON body:        │  Execute tool    │
│                  │  {                 │  via SerenaAgent │
│  {               │   "name_path_      │                  │
│   "name_path_    │    pattern": "...",│                  │
│    pattern":     │   "include_body":  │                  │
│    "...",        │    true            │                  │
│   "include_body":│  }                 │                  │
│    true          │                    │                  │
│  }               │ ◄────────────────  │                  │
│                  │  {"success":true,  │                  │
│                  │   "result":[...]}  │                  │
│                  │                    │                  │
└──────────────────┘                    └──────────────────┘
```

## Performance Comparison

| Metric | Standalone Mode | Daemon Mode | Improvement |
|--------|----------------|-------------|-------------|
| **First Command** | ~2-3s | ~0.6s | ~4x faster |
| **Subsequent Commands** | ~2-3s | ~0.1-0.2s | **~15-20x faster** |
| **Language Server Startup** | Every time | Once (at daemon start) | Massive savings |
| **Memory Usage** | Fresh each time | Persistent ~200-500MB | Trade-off for speed |
| **Cache Warmth** | Cold caches | Warm caches | Faster lookups |
| **Best For** | Occasional use, scripts | Frequent use, interactive | — |

## Installation

### Install Serena

```bash
# Install from GitHub
uv tool install "git+https://github.com/oraios/serena.git"

# Or install in development mode
cd serena
uv sync
```

### Entry Points

After installation, these commands are available:

```bash
serenad          # Daemon manager (start/stop/status/logs/restart)
serenad-cli      # Thin client (fast tool execution)
serena-cli       # Original standalone client (fallback)
```

**Note**: If entry points aren't installed yet, you can run directly:
```bash
uv run -m serena.serenad start --project .
uv run -m serena.serenad_client list_dir --relative_path .
```

## Usage

### Starting the Daemon

```bash
# Start daemon with a specific project (detached)
uv run -m serena.serenad start --project /path/to/project

# Start daemon with options
uv run -m serena.serenad start --project . --port 24282 --log-level DEBUG

# The daemon writes:
# - ~/.serena/daemon.pid (process ID)
# - ~/.serena/daemon.json (connection info: host, port)
# - ~/.serena/logs/daemon.log (output logs)
```

### Using the CLI Client

All tools work the same as `serena-cli`, just faster:

```bash
# File operations
uv run -m serena.serenad_client list_dir --relative_path src
uv run -m serena.serenad_client read_file --relative_path src/main.py
uv run -m serena.serenad_client create_text_file --relative_path new.py --content "def foo(): pass"

# Symbol operations
uv run -m serena.serenad_client find_symbol --name_path_pattern "UserService/login" --include_body
uv run -m serena.serenad_client get_symbols_overview --relative_path src/main.py
uv run -m serena.serenad_client find_referencing_symbols --name_path "UserService/login"

# Search
uv run -m serena.serenad_client search_for_pattern --substring_pattern "TODO"
uv run -m serena.serenad_client find_file --file_mask "*test*.py" --relative_path .

# Memory
uv run -m serena.serenad_client write_memory --memory_name "architecture" --content "Layered MVC..."
uv run -m serena.serenad_client read_memory --memory_name "architecture"
uv run -m serena.serenad_client list_memories

# Configuration
uv run -m serena.serenad_client tools          # List all tools
uv run -m serena.serenad_client projects       # List registered projects
uv run -m serena.serenad_client activate_project --project_path /path/to/project
```

### JSON Output

Use `--json` flag for machine-readable output:

```bash
uv run -m serena.serenad_client --json list_dir --relative_path src | jq .
uv run -m serena.serenad_client --json find_symbol --name_path_pattern "User" | jq '.[].name_path'
```

### Managing the Daemon

```bash
# Check daemon status
uv run -m serena.serenad status

# Stop the daemon
uv run -m serena.serenad stop

# Restart the daemon
uv run -m serena.serenad restart --project /path/to/project

# View daemon logs
uv run -m serena.serenad logs
uv run -m serena.serenad logs --follow  # Tail logs
```

### Direct HTTP Access

You can also call the API directly with curl:

```bash
# Health check
curl http://127.0.0.1:24282/health

# List tools
curl http://127.0.0.1:24282/tools

# Execute a tool
curl -X POST http://127.0.0.1:24282/tools/list_dir \
  -H "Content-Type: application/json" \
  -d '{"relative_path": "src", "recursive": false}'
```

## Implementation Details

### Files Created

| File | Purpose |
|------|---------|
| `src/serena/serenad.py` | Daemon manager (start/stop/status/logs/restart) |
| `src/serena/serenad_runner.py` | Detached process launcher |
| `src/serena/serenad_api.py` | Flask HTTP API server |
| `src/serena/serenad_client.py` | Thin CLI client |
| `docs/daemon-mode.md` | This documentation |
| `docs/serenad-architecture.md` | Detailed architecture guide |
| `examples/serenad_example.py` | Usage examples |

### Daemon Components

#### 1. Daemon Manager (`serenad`)
- Manages daemon process lifecycle
- Handles start/stop/status/restart commands
- Writes PID file and connection config
- Redirects output to log file

#### 2. Daemon Runner (`serenad_runner.py`)
- Launches daemon in detached mode
- Uses `subprocess.Popen` with `start_new_session=True`
- Handles proper daemonization (double-fork pattern)
- Manages signal handling and cleanup

#### 3. HTTP API Server (`serenad_api.py`)
- Flask-based REST API (threaded mode)
- Endpoints:
  - `GET /health` - Health check
  - `GET /tools` - List available tools
  - `POST /tools/<tool_name>` - Execute tool with JSON params
- Validates required parameters
- Returns JSON responses

#### 4. CLI Client (`serenad_cli.py`)
- Reads daemon config from `~/.serena/daemon.json`
- Checks daemon health before making requests
- Sends tool parameters as JSON to `/tools/<name>`
- Falls back to standalone mode if daemon unavailable
- Supports `--json` output format

### Session State

The daemon maintains persistent state:

- **Active Project**: Loaded at daemon start
- **Language Servers**: One persistent process per language (Pyright, TypeScript, etc.)
- **Symbol Caches**: Warm and ready for fast lookups
- **Memory State**: Project memories persist across commands
- **Tool Instances**: All 41 tools initialized and ready

## Troubleshooting

### Daemon won't start

```bash
# Check if port is already in use
lsof -i :24282

# Remove stale PID file
rm ~/.serena/daemon.pid

# Check daemon logs
cat ~/.serena/logs/daemon.log

# Try starting with debug logging
uv run -m serena.serenad start --project . --log-level DEBUG
```

### Connection refused

```bash
# Verify daemon is running
uv run -m serena.serenad status

# Check daemon config
cat ~/.serena/daemon.json

# Test health endpoint
curl http://127.0.0.1:24282/health
```

### Tool returns error

```bash
# Check if project is activated
uv run -m serena.serenad_client projects

# Activate project if needed
uv run -m serena.serenad_client activate_project --project_path /path/to/project

# Check tool help for required parameters
uv run -m serena.serenad_client <tool_name> --help
```

### Language server issues

```bash
# Restart the daemon to reinitialize language servers
uv run -m serena.serenad restart --project .

# Check language server logs
tail -f ~/.serena/logs/daemon.log

# View detailed logs
uv run -m serena.serenad logs --level DEBUG
```

### Fallback to standalone mode

If the daemon is not running, `serenad-cli` automatically falls back to standalone mode:

```
Using daemon at http://127.0.0.1:24282...
Error calling daemon: Connection refused
Falling back to standalone mode...
```

This ensures backward compatibility - your scripts will still work even if the daemon isn't running.

## Best Practices

1. **Start daemon once per session**: Run `serenad start` at the beginning of your work session
2. **Use for frequent commands**: Daemon shines when running multiple commands in sequence
3. **Check status before use**: `serenad status` to verify daemon is healthy
4. **Leverage JSON output**: Use `--json` flag for scripting and automation
5. **Store project knowledge**: Use memory tools to save important information
6. **Restart after changes**: Restart daemon if you modify Serena's source code
7. **Monitor logs**: Check logs if something goes wrong

## When to Use Daemon Mode

✅ **Use daemon mode when**:
- Running multiple commands in sequence
- Interactive development sessions
- IDE integration (constant tool usage)
- CI/CD pipelines with many Serena commands
- Want fastest possible response times

❌ **Use standalone mode when**:
- Running occasional single commands
- Scripts that run infrequently
- Memory is constrained
- Don't want background processes

## Future Improvements

Potential enhancements:

1. **Multiple Projects**: Support for multiple project sessions on different ports
2. **Authentication**: Token-based auth for remote access
3. **WebSocket Support**: Real-time updates for long-running operations
4. **Auto-restart**: Automatically restart daemon on crash
5. **Health Monitoring**: Periodic checks and automatic recovery
6. **Metrics Endpoint**: `/metrics` for monitoring performance
7. **Configuration Reload**: Hot-reload config without restart

## Related Documentation

- [serenad-architecture.md](serenad-architecture.md) - Detailed architecture with diagrams
- [cli-tool.md](cli-tool.md) - Complete CLI tool reference
- [SKILL.md](../../.pi/agent/skills/serenad/SKILL.md) - Agent skill for using serenad

---

*Last updated: March 2026*
