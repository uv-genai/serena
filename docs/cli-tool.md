# Serena CLI Tool

The Serena CLI (`serena-cli`) provides a command-line interface to all of Serena's tools, allowing you to interact with Serena's capabilities directly from the terminal.

## Installation

The CLI is automatically installed when you install Serena:

```bash
uv run serena-cli --help
```

## Basic Usage

```bash
serena-cli <command> [OPTIONS]
```

### Global Options

- `-p, --project TEXT` - Path or name of project to use
- `-c, --context TEXT` - Context to use
- `-v, --verbose` - Enable verbose output
- `--help` - Show help message

## Available Commands

### Tool Management

#### List Tools

```bash
# List all active tools
serena-cli tools

# List all tools including optional ones
serena-cli tools --all

# Quiet mode (only tool names)
serena-cli tools --quiet

# List only optional tools
serena-cli tools --only-optional
```

#### Get Tool Description

```bash
serena-cli tool-description <tool_name>
```

### Project Management

#### List Projects

```bash
serena-cli projects
```

#### List Contexts

```bash
serena-cli contexts
```

#### List Modes

```bash
serena-cli modes
```

## Tool Commands

All Serena tools are available as individual commands. Here are some examples:

### File Operations

#### Read File

```bash
# Read entire file
serena-cli read_file --project <project> --relative_path <path>

# Read specific lines
serena-cli read_file --project <project> --relative_path <path> --start_line 0 --end_line 50

# Output as JSON
serena-cli read_file --project <project> --relative_path <path> --json
```

#### List Directory

```bash
# List files in directory
serena-cli list_dir --project <project> --relative_path .

# Recursive listing
serena-cli list_dir --project <project> --relative_path . --recursive

# Skip ignored files
serena-cli list_dir --project <project> --relative_path . --skip_ignored_files
```

#### Create File

```bash
serena-cli create_text_file --project <project> --relative_path <path> --content "<file content>"
```

#### Replace Content

```bash
# Replace text (literal)
serena-cli replace_content --project <project> --relative_path <path> --needle "<search text>" --repl "<replacement text>" --mode literal

# Replace using regex
serena-cli replace_content --project <project> --relative_path <path> --needle "<regex pattern>" --repl "<replacement>" --mode regex
```

### Symbol Operations

#### Get Symbol Overview

```bash
# Get overview of symbols in a file
serena-cli get_symbols_overview --project <project> --relative_path <path>
```

#### Find Symbol

```bash
# Find symbol by name
serena-cli find_symbol --project <project> --name_path_pattern "<symbol name>"

# Find with body
serena-cli find_symbol --project <project> --name_path_pattern "<symbol name>" --include_body true

# Restrict to specific file
serena-cli find_symbol --project <project> --name_path_pattern "<symbol name>" --relative_path <path>
```

#### Find Referencing Symbols

```bash
serena-cli find_referencing_symbols --project <project> --name_path "<symbol name>" --relative_path <path>
```

#### Rename Symbol

```bash
serena-cli rename_symbol --project <project> --name_path "<old name>" --new_name "<new name>" --relative_path <path>
```

### Memory Operations

#### Write Memory

```bash
serena-cli write_memory --project <project> --memory_name "<memory name>" --content "<content>"
```

#### Read Memory

```bash
serena-cli read_memory --project <project> --memory_name "<memory name>"
```

#### List Memories

```bash
# List all memories
serena-cli list_memories

# List memories by topic
serena-cli list_memories --topic "<topic>"
```

#### Delete Memory

```bash
serena-cli delete_memory --project <project> --memory_name "<memory name>"
```

### Code Editing

#### Insert After Symbol

```bash
serena-cli insert_after_symbol --project <project> --name_path "<symbol name>" --body "<content to insert>" --relative_path <path>
```

#### Insert Before Symbol

```bash
serena-cli insert_before_symbol --project <project> --name_path "<symbol name>" --body "<content to insert>" --relative_path <path>
```

#### Replace Symbol Body

```bash
serena-cli replace_symbol_body --project <project> --name_path "<symbol name>" --body "<new body>" --relative_path <path>
```

### Search Operations

#### Search for Pattern

```bash
# Search in all files
serena-cli search_for_pattern --project <project> --substring_pattern "<pattern>"

# Search only in code files
serena-cli search_for_pattern --project <project> --substring_pattern "<pattern>" --restrict_search_to_code_files true
```

#### Find File

```bash
serena-cli find_file --project <project> --file_mask "<pattern>" --relative_path <path>
```

### Shell Commands

#### Execute Shell Command

```bash
# Execute command in project root
serena-cli execute_shell_command --project <project> --command "<shell command>"

# Execute in specific directory
serena-cli execute_shell_command --project <project> --command "<shell command>" --cwd <directory>

# Capture stderr
serena-cli execute_shell_command --project <project> --command "<shell command>" --capture_stderr true
```

### Configuration

#### Activate Project

```bash
serena-cli activate_project --project <project_name_or_path>
```

#### Switch Modes

```bash
serena-cli switch_modes --modes "<mode1>" "<mode2>"
```

#### Get Current Config

```bash
serena-cli get_current_config
```

### JetBrains Tools (Optional)

#### JetBrains Find Symbol

```bash
serena-cli jet_brains_find_symbol --project <project> --name_path_pattern "<symbol name>"
```

#### JetBrains Type Hierarchy

```bash
serena-cli jet_brains_type_hierarchy --project <project> --name_path "<symbol name>" --relative_path <path> --hierarchy_type "both"
```

## Output Formats

### JSON Output

Most tools support JSON output using the `--json` flag:

```bash
serena-cli read_file --project <project> --relative_path <path> --json
```

### Verbose Output

Enable verbose logging with the `-v` flag:

```bash
serena-cli read_file --project <project> --relative_path <path> -v
```

## Examples

### Example 1: Read and Display a File

```bash
serena-cli read_file --project my-project --relative_path src/main.py
```

### Example 2: Find All References to a Function

```bash
serena-cli find_referencing_symbols --project my-project --name_path "my_function" --relative_path src/main.py
```

### Example 3: Search for a Pattern

```bash
serena-cli search_for_pattern --project my-project --substring_pattern "TODO" --restrict_search_to_code_files true
```

### Example 4: Replace Content Using Regex

```bash
serena-cli replace_content --project my-project --relative_path src/main.py --needle "def old_function" --repl "def new_function" --mode regex
```

### Example 5: Get Symbol Overview

```bash
serena-cli get_symbols_overview --project my-project --relative_path src/main.py
```

## Tips

1. **Always specify a project**: Most tools require a project to be specified using `--project`.

2. **Use relative paths**: File paths should be relative to the project root.

3. **Check tool descriptions**: Use `serena-cli tool-description <tool_name>` to get detailed information about any tool.

4. **Enable verbose mode**: Use `-v` to see detailed execution logs.

5. **Use JSON output**: For scripting and automation, use `--json` to get structured output.

## Troubleshooting

### "No active project" error

Make sure to specify a project using `--project` or activate it first:

```bash
serena-cli activate_project --project <project_name>
```

### Tool not found

Check if the tool name is correct:

```bash
serena-cli tools
```

### Language server issues

If you encounter language server issues, try restarting it:

```bash
serena-cli restart_language_server
```

## Advanced Usage

### Using in Scripts

The CLI can be used in shell scripts:

```bash
#!/bin/bash
PROJECT="my-project"
FILE="src/main.py"

# Read file content
CONTENT=$(serena-cli read_file --project $PROJECT --relative_path $FILE)

# Find symbol
SYMBOLS=$(serena-cli find_symbol --project $PROJECT --name_path_pattern "my_function" --include_body true)

# Search for pattern
RESULTS=$(serena-cli search_for_pattern --project $PROJECT --substring_pattern "TODO")
```

### Combining Tools

Tools can be combined in pipelines:

```bash
# Get symbol overview and filter
serena-cli get_symbols_overview --project my-project --relative_path src/main.py | grep "Function"
```

## See Also

- [Serena Documentation](https://oraios.github.io/serena/)
- [Serena Tools](https://oraios.github.io/serena/01-about/035_tools.html)
- [Serena Configuration](https://oraios.github.io/serena/02-usage/050_configuration.html)