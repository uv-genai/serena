# Serena Daemon (serenad) Architecture & Testing Results

## Two Modes of Operation

| Mode | Command | Description | Speed |
|------|---------|-------------|-------|
| **Standalone** | `serena-cli <tool>` | Creates new process with SerenaAgent + LSPs each time | ~2-3s per command |
| **Daemon** | `serenad start` + `serenad-cli <tool>` | Persistent background server with warm LSPs | ~0.1-0.6s per command |

## Key Components

| File | Purpose |
|------|---------|
| `serenad_cli.py` | **Daemon manager** (Click-based): `start`, `stop`, `status`, `logs`, `restart` |
| `serenad_client_cli.py` | **Thin CLI client** (Click-based): Talks to daemon via HTTP REST |
| `serenad_api.py` | **Flask HTTP server**: Exposes tools at `/tools/<tool_name>` |
| `serenad_runner.py` | **Process runner**: Initializes SerenaAgent and starts Flask server |

## Entry Points (pyproject.toml)

```
serenad      → serena.serenad_cli:cli      # Daemon manager
serenad-cli  → serena.serenad_client_cli:cli  # Client tool
```

## Tested Commands

```bash
# Daemon management
serenad start --project /path/to/project --detach
serenad status
serenad logs
serenad stop

# Using the daemon client
serenad-cli list_dir --relative_path src
serenad-cli find_symbol --name_path_pattern "SerenaAgent"
serenad-cli search_for_pattern --substring_pattern "TODO"
serenad-cli --json find_symbol --name_path_pattern "main"

# Direct HTTP API
curl http://127.0.0.1:24282/health
curl http://127.0.0.1:24282/tools
curl -X POST http://127.0.0.1:24282/tools/find_symbol -d '{"name_path_pattern": "SerenaAgent"}'
```

## Test Results

| Feature | Status | Notes |
|---------|--------|-------|
| `serenad start/stop/status` | ✅ Working | Daemon manages PID file, config, and logs |
| `serenad-cli` daemon mode | ✅ Working | Fast HTTP calls to daemon |
| HTTP API (`/health`, `/tools`, `/tools/<name>`) | ✅ Working | 45 tools exposed via REST |
| JSON output (`--json` flag) | ✅ Working | Machine-readable output |
| Fallback to standalone | ❌ Broken | Import of `execute_tool_standalone` fails |
| `read_file` CLI params | ❌ Mismatch | CLI uses `offset/limit`, tool expects `start_line/end_line` |

## Issues Found

1. **read_file parameter mismatch**: The CLI defines `--offset` and `--limit`, but the tool expects `start_line` and `end_line`. Fix needed in `serenad_client_cli.py`.

2. **Fallback to standalone mode fails**: The import `from serena.cli_tools import execute_tool` fails because `cli_tools.py` doesn't export such a function. The fallback would need to be reimplemented.

## Files Summary

```
~/.serena/
├── daemon.pid          # PID of running daemon
├── daemon.json         # Daemon config (host, port, pid, project)
└── logs/
    └── daemon.log      # Daemon output logs
```

## Performance Comparison

```
Standalone mode: ~2-3 seconds per command (new process each time)
Daemon mode:     ~0.1-0.6 seconds per command (warm LSPs)

Speedup: ~15-20x faster for repeated commands
```

---

*Report generated: 2026-03-13*
