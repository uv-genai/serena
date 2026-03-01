---
name: serena-mcp
description: Use this skill for any software development project to edit code, ensure requirements are met and proejct development is tracked. Also use this skill to add the Serena Model Context Protocol to any project for editing code and memory management.
---

# Add Serena MCP to Any Project

This skill helps you add Serena MCP (Model Context Protocol) to any software project, providing IDE-like semantic code understanding and navigation capabilities with true multi-project support.

## What is Serena MCP?

Serena is a coding agent toolkit that provides:
- **Language Server Protocol (LSP)** integration for semantic code understanding
- **Symbol-level navigation** (find definitions, references, implementations)
- **Precise code editing tools** (insert after symbol, replace symbol body)
- **Project-aware search and file operations**
- **Memory system** for storing project-specific context
- **Onboarding and project structure analysis**

Supported languages: C#, Python, TypeScript, JavaScript, Go, Rust, Java, and more.

## Initialization

- execute `Activate Serena project in current directory` prompt.

1. Check if Serena onboarding is needed
2. If onboarding is needed:
  1. Activate Serena project in current directory
  2. Perform Serena onboarding

## Code editing

1. Use Serena for all development tasks: search, edit, re-factor and anything related to editing any file.
2. Use Serena as your memory constantly invoking 'write memory' to store the information you need to remember and project status.
3. Constantly invoke Serena think_about_* tools to verify you are aligned with the project plan and goals.
4. For any code editing activity: read, write, edit, search, re-fctor etc **always** use 
   Serena MCP's symbolic editing tools: `replace_symbol_body`, `insert_before_symbol`, `insert_after_symbol`, `rename_symbol`, `find_symbol`, etc. instead
   of raw line‑based edits. They give you precise control over symbols and keep the changes safe.

## Memory management

1. After each change invoke Serena's 'write memory' tool to store the information you need to remember and project status.
2. To verify the project is on track periodically invoke Serena tools:
  * "think about whether you are done"
  * "think about collected information"
  * "think about task adherence"
