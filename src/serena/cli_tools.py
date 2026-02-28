"""
Command-line interface for Serena's tools.
This module provides a CLI that exposes all Serena tools as individual commands.
"""

import json
import sys
from typing import Any

import click
from sensai.util import logging

from serena.agent import SerenaAgent
from serena.config.serena_config import SerenaConfig
from serena.tools import ToolRegistry


# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


class SerenaCLI(click.MultiCommand):
    """
    Main CLI entry point that dynamically exposes all Serena tools as commands.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._agent: SerenaAgent | None = None
        self._tool_registry = ToolRegistry()

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List all available tool commands."""
        # Add special commands that are not tools
        special_commands = ["tools", "tool-description", "projects", "contexts", "modes"]
        return sorted(special_commands + self._tool_registry.get_tool_names())

    def get_command(self, ctx: click.Context, name: str) -> click.Command | None:
        """Get a command for the given tool name."""
        # Check for special commands first
        if name in ["tools", "tool-description", "projects", "contexts", "modes"]:
            return self._get_special_command(name)
        
        if not self._tool_registry.is_valid_tool_name(name):
            click.echo(f"Error: Unknown tool '{name}'. Use 'serena-cli tools' to list available tools.", err=True)
            return None

        # Get the tool class
        tool_class = self._tool_registry.get_tool_class_by_name(name)
        
        # Create a dynamic command for this tool
        return self._create_tool_command(name, tool_class)

    def _create_tool_command(self, tool_name: str, tool_class: type) -> click.Command:
        """Create a click command for a given tool class."""
        tool_instance = None  # Will be created when command is invoked
        
        # Get tool metadata
        tool_description = tool_class.get_tool_description()
        tool_docstring = tool_class.get_apply_docstring_from_cls()
        
        # Get parameter metadata
        func_metadata = tool_class.get_apply_fn_metadata_from_cls()
        param_model = func_metadata.arg_model
        
        # Build click command parameters from tool parameters
        params = []
        for param_name, param_info in func_metadata.arg_model.model_fields.items():
            param_type = self._get_click_type(param_info.annotation)
            param_help = param_info.description or ""
            default = param_info.default
            required = param_info.is_required()
            
            # Handle bool types specially - use flag-style options
            if param_info.annotation == bool:
                # For bool parameters, use a flag-style option with --param-name and --no-param-name
                params.append(
                    click.Option(
                        [f"--{param_name}", f"--no-{param_name}"],
                        type=click.BOOL,
                        default=default if not required else False,
                        help=param_help,
                        is_flag=True,
                    )
                )
            else:
                if required:
                    default = click.UNPROCESSED
                
                params.append(
                    click.Option(
                        [f"--{param_name}"],
                        type=param_type,
                        default=default,
                        help=param_help,
                        required=required,
                    )
                )

        @click.command(name=tool_name, help=tool_description, params=params)
        @click.option("--project", type=str, default=None, help="Path or name of project to use")
        @click.option("--context", type=str, default=None, help="Context to use")
        @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
        @click.option("--json", "output_json", is_flag=True, help="Output result as JSON")
        @click.pass_context
        def tool_cmd(
            ctx: click.Context,
            project: str | None,
            context: str | None,
            verbose: bool,
            output_json: bool,
            **kwargs: Any,
        ) -> None:
            """Execute the {tool_name} tool."""
            # Initialize agent if needed
            if self._agent is None:
                config = SerenaConfig()
                self._agent = SerenaAgent(project=project, serena_config=config, context=context)
            
            # Get tool instance
            tool = self._agent.get_tool_by_name(tool_name)
            
            if verbose:
                click.echo(f"Executing tool: {tool_name}", err=True)
                click.echo(f"Parameters: {kwargs}", err=True)
            
            # Execute tool
            try:
                result = tool.apply_ex(log_call=verbose, catch_exceptions=True, **kwargs)
                
                # Output result
                if output_json:
                    try:
                        # Try to parse as JSON if result looks like JSON
                        if result.startswith("{") or result.startswith("["):
                            parsed = json.loads(result)
                            click.echo(json.dumps(parsed, indent=2, ensure_ascii=False))
                        else:
                            click.echo(result)
                    except json.JSONDecodeError:
                        click.echo(result)
                else:
                    click.echo(result)
                    
            except Exception as e:
                click.echo(f"Error executing tool: {e}", err=True)
                sys.exit(1)

        return tool_cmd

    def _get_special_command(self, name: str) -> click.Command:
        """Get a special command (not a tool)."""
        if name == "tools":
            @click.command(name="tools", help="List all available Serena tools")
            @click.option("--all", "-a", "include_optional", is_flag=True, help="Include optional (disabled by default) tools")
            @click.option("--quiet", "-q", is_flag=True, help="Only print tool names")
            def tools_cmd(include_optional: bool, quiet: bool) -> None:
                """List all available Serena tools."""
                registry = ToolRegistry()
                if quiet:
                    if include_optional:
                        tool_names = registry.get_tool_names()
                    else:
                        tool_names = registry.get_tool_names_default_enabled()
                    for tool_name in tool_names:
                        click.echo(tool_name)
                else:
                    registry.print_tool_overview(include_optional=include_optional)
            return tools_cmd
        
        elif name == "tool-description":
            @click.command(name="tool-description", help="Get description of a specific tool")
            @click.argument("tool_name", type=str)
            def tool_description_cmd(tool_name: str) -> None:
                """Get description of a specific tool."""
                registry = ToolRegistry()
                if not registry.is_valid_tool_name(tool_name):
                    click.echo(f"Error: Unknown tool '{tool_name}'", err=True)
                    click.echo(f"Available tools: {', '.join(registry.get_tool_names())}", err=True)
                    return
                tool_class = registry.get_tool_class_by_name(tool_name)
                click.echo(f"Tool: {tool_name}")
                click.echo(f"Description: {tool_class.get_tool_description()}")
                click.echo(f"\nDocstring:")
                click.echo(tool_class.get_apply_docstring_from_cls())
            return tool_description_cmd
        
        elif name == "projects":
            @click.command(name="projects", help="List registered Serena projects")
            def projects_cmd() -> None:
                """List registered Serena projects."""
                from serena.config.serena_config import SerenaConfig
                config = SerenaConfig.from_config_file()
                projects = config.projects
                if not projects:
                    click.echo("No projects registered.")
                    return
                click.echo("Registered projects:")
                for proj in projects:
                    click.echo(f"  - {proj.project_name}: {proj.project_root}")
            return projects_cmd
        
        elif name == "contexts":
            @click.command(name="contexts", help="List available Serena contexts")
            def contexts_cmd() -> None:
                """List available Serena contexts."""
                from serena.config.context_mode import SerenaAgentContext
                contexts = SerenaAgentContext.list_registered_context_names()
                if not contexts:
                    click.echo("No contexts available.")
                    return
                click.echo("Available contexts:")
                for ctx_name in contexts:
                    ctx_path = SerenaAgentContext.get_path(ctx_name)
                    click.echo(f"  - {ctx_name}: {ctx_path}")
            return contexts_cmd
        
        elif name == "modes":
            @click.command(name="modes", help="List available Serena modes")
            def modes_cmd() -> None:
                """List available Serena modes."""
                from serena.config.context_mode import SerenaAgentMode
                modes = SerenaAgentMode.list_registered_mode_names()
                if not modes:
                    click.echo("No modes available.")
                    return
                click.echo("Available modes:")
                for mode_name in modes:
                    mode_path = SerenaAgentMode.get_path(mode_name)
                    click.echo(f"  - {mode_name}: {mode_path}")
            return modes_cmd
        
        return None

    def _get_click_type(self, annotation: type) -> click.ParamType:
        """Convert Python type annotation to click type."""
        import typing
        
        # Handle optional types
        origin = typing.get_origin(annotation)
        if origin is typing.Union:
            args = typing.get_args(annotation)
            # Remove NoneType for optional types
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return self._get_click_type(non_none_args[0])
        
        # Handle basic types
        if annotation == str:
            return click.STRING
        elif annotation == int:
            return click.INT
        elif annotation == float:
            return click.FLOAT
        elif annotation == bool:
            # Use flag-style option for bool
            return click.BOOL
        elif annotation == list or (origin is list and len(typing.get_args(annotation)) > 0):
            return click.STRING  # Accept as comma-separated string
        elif annotation == dict or (origin is dict and len(typing.get_args(annotation)) > 0):
            return click.STRING  # Accept as JSON string
        else:
            # Default to string for unknown types
            return click.STRING


@click.group(cls=SerenaCLI, help="Serena CLI - Execute Serena's tools from the command line")
@click.option("--project", "-p", type=str, default=None, help="Default project to use")
@click.option("--context", "-c", type=str, default=None, help="Default context to use")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, project: str | None, context: str | None, verbose: bool) -> None:
    """
    Serena CLI - Execute Serena's tools from the command line.
    
    This CLI exposes all Serena tools as individual commands.
    Use 'serena-cli <tool_name> --help' for tool-specific help.
    """
    ctx.ensure_object(dict)
    ctx.obj["project"] = project
    ctx.obj["context"] = context
    ctx.obj["verbose"] = verbose


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()