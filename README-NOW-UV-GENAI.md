# Serena CLI tools

This is a fork of the Serena MCP server adding a cli interface to all provided tools.

It allows to replace the MCP server with a cli tool + SKILL.md.

The only additions are:
- src/serena/cli_tools.py (cli interface to all tools)
- CLI_TOOL_SUMMARY.md (documentaion for `cli_tools`)
- serena-cli-tools-skill.md (skill for the cli tools, to be renamed to SKILL.md)
- README-NOW-UV-GENAI.md (this file)

The only changed file is:
- pyproject.toml to add the `cli_tools` module to the package

The main branch is constanlty updated with the latest version of the official Serena MCP server.
