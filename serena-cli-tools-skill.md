---
name: serena-cli
description: Provides command-line access to all Serena tools for semantic code understanding and editing. Use this skill for all code editing tasks, from simple text search and replacements to complex refactoring.
---

# Serena CLI Skill for Coding Agents

## Overview
The **serena-cli** tool provides command-line access to Serena's powerful semantic code understanding and editing capabilities. Serena acts as an IDE-like toolkit for coding agents, enabling precise code retrieval and manipulation through symbolic operations rather than simple text search.

| Tool Category | Key Tools | Purpose |
|--------------|-----------|---------|
| **File Operations** | `read_file`, `list_dir`, `create_text_file`, `replace_content` | Read, list, create, and edit files |
| **Symbol Operations** | `find_symbol`, `get_symbols_overview`, `find_referencing_symbols` | Language-aware symbol search and navigation |
| **Memory** | `write_memory`, `read_memory`, `list_memories`, `delete_memory` | Project knowledge persistence |
| **Code Editing** | `insert_after_symbol`, `replace_symbol_body`, `rename_symbol` | Precise code modifications |
| **Search** | `search_for_pattern`, `find_file` | Pattern and file discovery |
| **Shell** | `execute_shell_command` | Run shell commands in project context |
| **Configuration** | `activate_project`, `switch_modes`, `get_current_config` | Manage projects and agent configuration |

All tools output **machine-readable text or JSON** which can be parsed and acted upon by downstream agents.

---

## 1. Prerequisites & Installation

### Requirement: `uv`
The **serena-cli** tool relies on `uv` for dependency management and execution. If `uv` is not installed, install it first:

```bash
# Install uv (one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installing Serena

#### Option A: Install from GitHub (recommended for latest version)
```bash
# Install directly from GitHub
uv tool install "git+https://github.com/uv-genai/serena.git"

# Or install a specific version
uv tool install "git+https://github.com/uv-genai/serena.git@v0.1.4"
```

### Action: You must install Serena CLI if not already installed by installing serena according to the above instructions.


#### Option B: Clone and install locally
```bash
git clone https://github.com/oraios/serena.git
cd serena
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync                     # installs all dependencies
```

After installation, the `serena-cli` command will be available on your `$PATH`:

```bash
serena-cli --help
```

### Activating a Project

Before using most tools, you need to activate a project:

```bash
# Activate by path
serena-cli activate_project --project /path/to/your/project

# Or specify project for each command
serena-cli read_file --project /path/to/project --relative_path src/main.py
```

---

## 2. File Operations

### Read File (`read_file`)

Reads a file within the project directory, with optional line ranges.

```bash
# Read entire file
serena-cli read_file --project <project_path> --relative_path <file_path>

# Read specific lines (0-indexed)
serena-cli read_file --project <project_path> --relative_path <file_path> --start_line 0 --end_line 50

# Output as JSON
serena-cli read_file --project <project_path> --relative_path <file_path> --json
```

**Use when**: You need to examine file contents, understand code structure, or read configuration files.

**Example**:
```bash
serena-cli read_file --project . --relative_path README.md
```

### List Directory (`list_dir`)

Lists files and directories in a given path, with optional recursion.

```bash
# List files in directory
serena-cli list_dir --project <project_path> --relative_path <dir_path>

# Recursive listing
serena-cli list_dir --project <project_path> --relative_path <dir_path> --recursive

# Skip ignored files (e.g., .gitignore)
serena-cli list_dir --project <project_path> --relative_path <dir_path> --skip_ignored_files

# Output as JSON
serena-cli list_dir --project <project_path> --relative_path <dir_path> --json
```

**Use when**: You need to explore project structure, find files, or understand directory organization.

**Example**:
```bash
serena-cli list_dir --project . --relative_path src/serena/tools --recursive --json
```

### Create Text File (`create_text_file`)

Creates or overwrites a file with the given content.

```bash
serena-cli create_text_file --project <project_path> --relative_path <file_path> --content "<file content>"
```

**Use when**: You need to create new files, generate configuration, or write documentation.

**Example**:
```bash
serena-cli create_text_file --project . --relative_path src/new_feature.py --content "def new_feature():\n    pass"
```

### Replace Content (`replace_content`)

Replaces content in a file, supporting both literal and regex patterns.

```bash
# Replace text (literal)
serena-cli replace_content --project <project_path> --relative_path <file_path> --needle "<search text>" --repl "<replacement text>" --mode literal

# Replace using regex
serena-cli replace_content --project <project_path> --relative_path <file_path> --needle "<regex pattern>" --repl "<replacement>" --mode regex
```

**Use when**: You need to make text replacements, fix typos, or update patterns across a file.

**Example**:
```bash
serena-cli replace_content --project . --relative_path src/main.py --needle "old_function" --repl "new_function" --mode literal
```

---

## 3. Symbol Operations (Serena's Superpower)

Serena's symbol operations are its key differentiator from simple text search. They understand code structure and relationships.

### Get Symbols Overview (`get_symbols_overview`)

Gets an overview of top-level symbols (classes, functions, methods) in a file.

```bash
serena-cli get_symbols_overview --project <project_path> --relative_path <file_path> --depth <nested_depth>
```

**Use when**: You need to understand what's in a file before diving deeper. This is the **first tool to call** when exploring a new file.

**Example**:
```bash
serena-cli get_symbols_overview --project . --relative_path src/main.py
```

**Output**:
```json
{
  "Class": ["UserManager", "DatabaseConnection"],
  "Function": ["main", "initialize"],
  "Method": ["__init__", "save", "load"]
}
```

### Find Symbol (`find_symbol`)

Performs a global or local search for symbols by name pattern.

```bash
# Find by name pattern
serena-cli find_symbol --project <project_path> --name_path_pattern "<symbol name>"

# Find with source code body
serena-cli find_symbol --project <project_path> --name_path_pattern "<symbol name>" --include_body true

# Find with additional info (docstrings, signatures)
serena-cli find_symbol --project <project_path> --name_path_pattern "<symbol name>" --include_info true

# Restrict search to specific file
serena-cli find_symbol --project <project_path> --name_path_pattern "<symbol name>" --relative_path <file_path>

# Substring matching (e.g., "get" matches "getValue", "getData")
serena-cli find_symbol --project <project_path> --name_path_pattern "getValue" --substring_matching true
```

**Use when**: You need to find where a function/class is defined, understand its implementation, or locate all occurrences of a symbol.

**Example**:
```bash
# Find a specific function
serena-cli find_symbol --project . --name_path_pattern "UserManager/__init__" --include_body true

# Find all functions matching a pattern
serena-cli find_symbol --project . --name_path_pattern "get*" --include_body true
```

### Find Referencing Symbols (`find_referencing_symbols`)

Finds all symbols that reference a given symbol (like "Find Usages" in IDEs).

```bash
serena-cli find_referencing_symbols --project <project_path> --name_path "<symbol name>" --relative_path <file_path>
```

**Use when**: You need to understand where a function/class is called, track dependencies, or assess the impact of changes.

**Example**:
```bash
serena-cli find_referencing_symbols --project . --name_path "UserManager/save" --relative_path src/user_manager.py
```

**Output**:
```json
[
  {
    "name_path": "UserController/create_user",
    "relative_path": "src/user_controller.py",
    "kind": "Function"
  },
  {
    "name_path": "APIHandler/register",
    "relative_path": "src/api_handler.py",
    "kind": "Function"
  }
]
```

---

## 4. Memory Operations

Serena's memory system allows you to store and retrieve project knowledge across sessions.

### Write Memory (`write_memory`)

Writes information to Serena's project-specific memory store.

```bash
serena-cli write_memory --project <project_path> --memory_name "<memory_name>" --content "<content>"
```

**Use when**: You want to store important project information, decisions, or context for future reference.

**Example**:
```bash
serena-cli write_memory --project . --memory_name "project_structure" --content "This project uses a MVC pattern with separate controllers, models, and views."
```

### Read Memory (`read_memory`)

Reads stored memory content.

```bash
serena-cli read_memory --project <project_path> --memory_name "<memory_name>"
```

**Use when**: You need to recall previously stored information about the project.

**Example**:
```bash
serena-cli read_memory --project . --memory_name "project_structure"
```

### List Memories (`list_memories`)

Lists all stored memories, optionally filtered by topic.

```bash
# List all memories
serena-cli list_memories --project <project_path>

# List memories by topic
serena-cli list_memories --project <project_path> --topic "<topic>"
```

**Use when**: You need to see what information has been stored or find memories related to a specific topic.

**Example**:
```bash
serena-cli list_memories --project .
```

### Delete Memory (`delete_memory`)

Deletes a stored memory.

```bash
serena-cli delete_memory --project <project_path> --memory_name "<memory_name>"
```

**Use when**: You need to remove outdated or incorrect information from memory.

---

## 5. Code Editing Operations

Serena provides precise code editing capabilities that understand symbol boundaries.

### Insert After Symbol (`insert_after_symbol`)

Inserts content after a symbol's definition.

```bash
serena-cli insert_after_symbol --project <project_path> --name_path "<symbol name>" --body "<content to insert>" --relative_path <file_path>
```

**Use when**: You need to add new methods after existing ones, insert documentation, or extend functionality.

**Example**:
```bash
serena-cli insert_after_symbol --project . --name_path "UserService/login" --body "    # New authentication logic\n    pass" --relative_path src/user_service.py
```

### Insert Before Symbol (`insert_before_symbol`)

Inserts content before a symbol's definition.

```bash
serena-cli insert_before_symbol --project <project_path> --name_path "<symbol name>" --body "<content to insert>" --relative_path <file_path>
```

**Use when**: You need to add content before existing symbols.

### Replace Symbol Body (`replace_symbol_body`)

Replaces the entire body of a symbol (function, method, class).

```bash
serena-cli replace_symbol_body --project <project_path> --name_path "<symbol name>" --body "<new body>" --relative_path <file_path>
```

**Use when**: You need to completely rewrite a function or method while preserving its signature.

**Example**:
```bash
serena-cli replace_symbol_body --project . --name_path "UserService/validate_user" --body "    if not user:\n        raise ValueError('User not found')\n    return user.is_active" --relative_path src/user_service.py
```

### Rename Symbol (`rename_symbol`)

Renames a symbol throughout the codebase (safe refactoring).

```bash
serena-cli rename_symbol --project <project_path> --name_path "<old symbol name>" --new_name "<new name>" --relative_path <file_path>
```

**Use when**: You need to rename a function, class, or method and have all references updated automatically.

**Example**:
```bash
serena-cli rename_symbol --project . --name_path "UserService/check_auth" --new_name "UserService/validate_authentication" --relative_path src/user_service.py
```

---

## 6. Search Operations

### Search for Pattern (`search_for_pattern`)

Performs pattern search across the codebase.

```bash
# Search in all files
serena-cli search_for_pattern --project <project_path> --substring_pattern "<pattern>"

# Search only in code files (skip config, docs, etc.)
serena-cli search_for_pattern --project <project_path> --substring_pattern "<pattern>" --restrict_search_to_code_files true

# Output as JSON
serena-cli search_for_pattern --project <project_path> --substring_pattern "<pattern>" --json
```

**Use when**: You need to find all occurrences of a text pattern, TODOs, FIXMEs, or specific code patterns.

**Example**:
```bash
# Find all TODO comments
serena-cli search_for_pattern --project . --substring_pattern "TODO" --restrict_search_to_code_files true

# Find all print statements
serena-cli search_for_pattern --project . --substring_pattern "print(" --restrict_search_to_code_files true
```

### Find File (`find_file`)

Finds files matching a pattern.

```bash
serena-cli find_file --project <project_path> --file_mask "<pattern>" --relative_path <dir_path>
```

**Use when**: You need to find files by name pattern (e.g., all test files, all config files).

**Example**:
```bash
# Find all test files
serena-cli find_file --project . --file_mask "*test*.py" --relative_path src

# Find all configuration files
serena-cli find_file --project . --file_mask "config*.yml" --relative_path .
```

---

## 7. Shell Commands

### Execute Shell Command (`execute_shell_command`)

Executes shell commands in the project context.

```bash
# Execute in project root
serena-cli execute_shell_command --project <project_path> --command "<shell command>"

# Execute in specific directory
serena-cli execute_shell_command --project <project_path> --command "<shell command>" --cwd <directory>

# Capture stderr
serena-cli execute_shell_command --project <project_path> --command "<shell command>" --capture_stderr true
```

**Use when**: You need to run build commands, tests, or other external tools.

**Example**:
```bash
# Run tests
serena-cli execute_shell_command --project . --command "pytest tests/"

# Check git status
serena-cli execute_shell_command --project . --command "git status"

# Install dependencies
serena-cli execute_shell_command --project . --command "pip install -e ."
```

---

## 8. Configuration and Management

### List Tools (`tools`)

Lists all available Serena tools.

```bash
# List active tools
serena-cli tools

# List all tools including optional ones
serena-cli tools --all

# Quiet mode (only tool names)
serena-cli tools --quiet
```

### Tool Description (`tool-description`)

Gets detailed description of a specific tool.

```bash
serena-cli tool-description <tool_name>
```

**Use when**: You need to understand what a tool does and its parameters.

**Example**:
```bash
serena-cli tool-description find_symbol
```

### List Projects (`projects`)

Lists all registered Serena projects.

```bash
serena-cli projects
```

### List Contexts (`contexts`)

Lists available Serena contexts (pre-configured tool sets).

```bash
serena-cli contexts
```

### List Modes (`modes`)

Lists available Serena modes (operational patterns).

```bash
serena-cli modes
```

---

## 9. Workflow Patterns for Agents

### Pattern 1: Explore File Structure

```bash
# 1) Get overview of file
serena-cli get_symbols_overview --project . --relative_path src/main.py

# 2) Read the file
serena-cli read_file --project . --relative_path src/main.py

# 3) Find specific symbols
serena-cli find_symbol --project . --name_path_pattern "main" --include_body true
```

### Pattern 2: Understand Dependencies

```bash
# 1) Find a symbol
serena-cli find_symbol --project . --name_path_pattern "UserService/login" --include_body true

# 2) Find all references to it
serena-cli find_referencing_symbols --project . --name_path "UserService/login" --relative_path src/user_service.py

# 3) Explore referenced files
serena-cli read_file --project . --relative_path src/auth_handler.py
```

### Pattern 3: Make Safe Code Changes

```bash
# 1) Find the symbol to modify
serena-cli find_symbol --project . --name_path_pattern "validate_user" --include_body true

# 2) Check where it's used
serena-cli find_referencing_symbols --project . --name_path "validate_user" --relative_path src/user_service.py

# 3) Replace the symbol body safely
serena-cli replace_symbol_body --project . --name_path "UserService/validate_user" --body "    # Enhanced validation logic\n    pass" --relative_path src/user_service.py
```

### Pattern 4: Store Project Knowledge

```bash
# 1) Write important information
serena-cli write_memory --project . --memory_name "architecture" --content "This project uses a layered architecture with API, business logic, and data layers."

# 2) Read it later
serena-cli read_memory --project . --memory_name "architecture"

# 3) List all memories
serena-cli list_memories --project .
```

### Pattern 5: Search and Replace

```bash
# 1) Find all occurrences
serena-cli search_for_pattern --project . --substring_pattern "TODO" --restrict_search_to_code_files true

# 2) Read the file with TODOs
serena-cli read_file --project . --relative_path src/feature.py

# 3) Replace the TODO with implementation
serena-cli replace_content --project . --relative_path src/feature.py --needle "# TODO: implement" --repl "    # Implemented\n    pass" --mode literal
```

---

## 10. Why Use Serena CLI?

### Advantages Over Simple Text Search

1. **Symbol-Aware**: Serena understands code structure, not just text. It knows that `UserService.login` is a method within a class, not just two words appearing together.

2. **Safe Refactoring**: When you rename a symbol, Serena updates all references automatically, preventing broken code.

3. **Precise Editing**: Serena edits at symbol boundaries, preserving formatting and structure.

4. **Context Preservation**: Serena remembers project knowledge through its memory system.

5. **Language Server Integration**: Serena uses language servers for accurate symbol information across 30+ programming languages.

### When to Use Serena CLI

✅ **Use Serena when**:
- Working with large codebases
- Needing to understand code structure
- Making refactoring changes
- Searching for specific functions/classes
- Needing safe, precise code edits
- Wanting to store project knowledge

❌ **Don't use Serena when**:
- Making simple text replacements in small files
- Working with non-code files (images, binaries)
- Needing to search outside the project

---

## 11. Error Handling

### Common Errors and Solutions

**"No active project"**
```bash
# Solution: Activate a project first
serena-cli activate_project --project /path/to/project
```

**"Symbol not found"**
```bash
# Solution: Check symbol name and file path
serena-cli get_symbols_overview --project . --relative_path src/main.py
```

**"File not found"**
```bash
# Solution: Check relative path from project root
serena-cli list_dir --project . --relative_path .
```

**Language server errors**
```bash
# Solution: Restart language server
serena-cli restart_language_server
```

### Output Parsing

All tools output text or JSON. For scripting:

```bash
# Parse JSON output
result=$(serena-cli find_symbol --project . --name_path_pattern "main" --json)
echo "$result" | jq '.'

# Check exit code
serena-cli read_file --project . --relative_path nonexistent.py
if [ $? -ne 0 ]; then
    echo "File not found"
fi
```

---

## 12. Advanced Usage

### Using in Scripts

```bash
#!/bin/bash
PROJECT="/path/to/project"

# Read file and process
CONTENT=$(serena-cli read_file --project $PROJECT --relative_path src/main.py)
echo "File has $(echo "$CONTENT" | wc -l) lines"

# Find all functions
FUNCTIONS=$(serena-cli get_symbols_overview --project $PROJECT --relative_path src/main.py | grep Function)
echo "Found functions: $FUNCTIONS"

# Search for patterns
grep_results=$(serena-cli search_for_pattern --project $PROJECT --substring_pattern "TODO" --json)
echo "Found TODOs: $grep_results"
```

### Combining with Other Tools

```bash
# Find symbols and read their files
serena-cli find_symbol --project . --name_path_pattern "Controller" --include_body true | \
    jq -r '.[].relative_path' | \
    xargs -I {} serena-cli read_file --project . --relative_path {}
```

---

## 13. Getting Help

```bash
# Main help
serena-cli --help

# Tool-specific help
serena-cli read_file --help
serena-cli find_symbol --help

# List all tools
serena-cli tools

# Get tool description
serena-cli tool-description read_file
```

---

## 14. Best Practices

1. **Always start with `get_symbols_overview`** when exploring a new file
2. **Use `find_symbol` with `--include_body`** to see implementation details
3. **Check references with `find_referencing_symbols`** before making changes
4. **Store important information in memory** for future sessions
5. **Use `--json` output** for scripting and automation
6. **Enable verbose mode (`-v`)** when debugging issues
7. **Always specify `--project`** to avoid "no active project" errors

---

*End of Skill description.*
