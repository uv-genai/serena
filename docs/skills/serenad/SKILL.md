---
name: serenad
description: Provides a thin, fast client (`serenad-cli`) that talks to the persistent Serena daemon (`serenad`). Use this skill for all code‑editing, symbol‑search, and memory operations when a daemon is running; it falls back to the original `serena-cli` if the daemon is unavailable.
---

# Serena Daemon Client (serenad-cli) Skill for Coding Agents

## Overview
`serenad-cli` is the **fast** entry‑point for Serena's tooling when a **Serena daemon** (`serenad`) is running.  
The daemon keeps a **single `SerenaAgent` instance** (with all language servers) alive, so every command executes in **~0.1‑0.6 s** instead of the ~2 s start‑up cost of the original `serena-cli`.

If the daemon is not reachable, `serenad-cli` transparently falls back to the classic `serena-cli` implementation, guaranteeing backward compatibility.

| Feature | `serenad-cli` (daemon) | `serena-cli` (stand‑alone) |
|---------|------------------------|----------------------------|
| Startup cost | **≈ 0.1‑0.6 s** (daemon already warm) | **≈ 2 s** (new Python process + LSP start) |
| Language‑server reuse | **Yes** – one persistent process per language | **No** – fresh LSP each run |
| CLI surface | Identical to `serena-cli` (all 41 tools) | Identical |
| Fallback | Automatic when daemon down | N/A |

---

## 1️⃣  Prerequisites & Installation

### Install `uv` (if not already present)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Serena with Daemon Support

The daemon tools (`serenad`, `serenad-cli`) are now registered as entry points in the package.

#### Option A: Install from GitHub (Recommended)
```bash
# Install or reinstall from the latest GitHub version
uv tool install "git+https://github.com/oraios/serena.git" --force
```

After installation, these commands will be available on your `$PATH`:

```bash
serenad          # Daemon manager (start/stop/status/logs/restart)
serenad-cli      # Thin client for fast tool execution
serena-cli       # Original standalone client (fallback)
```

#### Option B: Local Development Installation
If you're working from a local clone:

```bash
git clone https://github.com/oraios/serena.git
cd serena
uv sync
```

Then use the virtual environment's binaries:
```bash
./venv/bin/serenad start --project .
./venv/bin/serenad-cli list_dir --relative_path src
```

Or activate the venv first:
```bash
source .venv/bin/activate
serenad start --project .
serenad-cli list_dir --relative_path src
```

---

## 2️⃣  Starting the Daemon

```bash
# Start a daemon for the current project (detached)
serenad start --project .

# The command prints:
#   ✅ Daemon started successfully (PID: 12345)
#   URL: http://127.0.0.1:24282
#   Logs: /Users/<you>/.serena/logs/daemon.log
```

The daemon writes two files in `~/.serena/`:

* `daemon.pid` – PID of the background process  
* `daemon.json` – `{ "host": "127.0.0.1", "port": 24282, "pid": 12345, ... }`

You can query its health:

```bash
curl -s http://127.0.0.1:24282/health | jq .
# → {"pid":12345,"status":"healthy"}
```

---

## 3️⃣  Using `serenad-cli`

The **argument list** is **identical** to `serena-cli`.  
All tools are available (`read_file`, `find_symbol`, `search_for_pattern`, …) and the same `--json` flag works.

### Basic Syntax
```bash
serenad-cli <tool> [options] [--json]
# or (if entry point is installed):
serenad-cli <tool> [options] [--json]
```

### Example: List a directory
```bash
serenad-cli list_dir --relative_path src
```

### Example: Find a symbol (with body)
```bash
serenad-cli find_symbol --name_path_pattern "UserService/login" --include_body
```

### Example: Read a file as JSON
```bash
serenad-cli read_file --relative_path src/main.py --json
```

### Example: Search for TODOs (JSON output)
```bash
serenad-cli search_for_pattern --substring_pattern "TODO" --json
```

All commands run in **sub‑second** time because the daemon already has the language servers loaded.

---

## 4️⃣  Common Tools Reference

### File Operations
- `list_dir --relative_path <dir>` - List directory contents
- `read_file --relative_path <file>` - Read a file
- `create_text_file --relative_path <file> --content "<content>"` - Create a file
- `replace_content --relative_path <file> --needle "<search>" --repl "<replace>"` - Replace text

### Symbol Operations
- `get_symbols_overview --relative_path <file>` - Get symbols in a file
- `find_symbol --name_path_pattern "<pattern>" --include_body` - Find a symbol
- `find_referencing_symbols --name_path "<symbol>" --relative_path <file>` - Find references

### Search
- `search_for_pattern --substring_pattern "<pattern>"` - Search for text
- `find_file --file_mask "*.py" --relative_path src` - Find files by pattern

### Memory
- `write_memory --memory_name "<name>" --content "<content>"` - Store knowledge
- `read_memory --memory_name "<name>"` - Retrieve memory
- `list_memories` - List all memories

### Configuration
- `tools` - List available tools
- `projects` - List registered projects
- `activate_project --project_path <path>` - Activate a project

---

## 5️⃣  Fallback Behaviour

If the daemon is stopped or unreachable:

```bash
serenad-cli read_file --relative_path src/main.py
```

`serenad-cli` will detect the missing daemon, print a short notice, and then invoke the original `serena-cli` implementation so the command still succeeds.

---

## 6️⃣  Workflow Patterns for Agents

### Pattern 1 – Quick File Exploration
```bash
# 1) Get a symbols‑level overview
serenad-cli get_symbols_overview --relative_path src/main.py

# 2) Read the file
serenad-cli read_file --relative_path src/main.py

# 3) Find a specific function
serenad-cli find_symbol --name_path_pattern "main" --include_body
```

### Pattern 2 – Safe Refactoring
```bash
# 1) Locate the function to rename
serenad-cli find_symbol --name_path_pattern "old_name" --include_body

# 2) Find all references
serenad-cli find_referencing_symbols --name_path "old_name"

# 3) Rename it (daemon updates all call‑sites)
serenad-cli rename_symbol --name_path "old_name" --new_name "new_name"
```

### Pattern 3 – Store Project Knowledge
```bash
# Write a memory entry
serenad-cli write_memory --memory_name "architecture" \
    --content "Layered MVC, services in src/services/, models in src/models/."

# Retrieve it later
serenad-cli read_memory --memory_name "architecture"
```

### Pattern 4 – Explore Project Structure
```bash
# List all files in src/
serenad-cli list_dir --relative_path src --recursive

# Find all Python test files
serenad-cli find_file --file_mask "*test*.py" --relative_path .
```

---

## 7️⃣  Daemon Management

### Start Daemon
```bash
serenad start --project /path/to/project
```

### Stop Daemon
```bash
serenad stop
```

### Check Status
```bash
serenad status
```

### View Logs
```bash
serenad logs
```

### Restart Daemon
```bash
serenad restart --project /path/to/project
```

---

## 8️⃣  Error Handling

| Situation | What you'll see | Suggested fix |
|-----------|------------------|----------------|
| Daemon not running | `Daemon not running. Using standalone mode…` | Start it with `serenad start --project .` |
| No active project | `Error: No active project` | Activate a project: `serenad-cli activate_project --project_path /path/to/project` |
| Symbol not found | `❌ Error: Symbol not found` | Verify the name/path with `get_symbols_overview` first |
| Language‑server crash | Daemon logs show stack trace | Restart the daemon (`serenad restart`) |
| Missing required parameter | `Error: Missing required parameter: <param>` | Check the tool's help: `serenad-cli <tool> --help` |

All tools return **machine‑readable JSON** when `--json` is supplied, making them easy to parse in scripts:

```bash
result=$(serenad-cli find_symbol --name_path_pattern "User" --json)
echo "$result" | jq .
```

---

## 9️⃣  Performance Comparison

| Operation | Standalone (`serena-cli`) | Daemon (`serenad-cli`) | Speedup |
|-----------|--------------------------|------------------------|---------|
| First command | ~2‑3 s | ~0.6 s | ~4x |
| Subsequent commands | ~2‑3 s | ~0.1‑0.2 s | **~15‑20x** |
| Language server startup | Every time | Once (at daemon start) | Massive |

The daemon shines when running multiple commands in sequence, as the language servers stay warm.

---

## 🔟  Best Practices

1. **Start the daemon once** at the beginning of your session: `serenad start --project .`
2. **Use `--json` output** for scripting and automation
3. **Check daemon status** before running commands: `serenad status`
4. **Always specify `--relative_path`** from the project root
5. **Use `find_symbol` with `--include_body`** to see implementation details
6. **Check references with `find_referencing_symbols`** before making changes
7. **Store important information in memory** for future sessions
8. **Enable verbose mode** when debugging issues

---

## 📝 Installing the Skill in the Agent Framework

The skill is available at `~/.pi/agent/skills/serenad`.  
When the agent's prompt mentions **`serenad-cli`** or **daemon mode**, it should:

1. Prefer the daemon‑based workflow (fast, stateful)
2. Start the daemon if not running: `serenad start --project .`
3. Fall back to the classic `serena-cli` only if the daemon is unavailable
4. Use the workflow patterns above for common tasks

---  

*End of `serenad` skill.*
