import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.nasa_exoplanet_archive import NasaExoplanetArchive
from ..i18n import get_translator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    global_keyboard_interrupt_handler,
)
import os
import re
from io import StringIO
from contextlib import redirect_stdout
from astroquery_cli.common_options import setup_debug_context
from astroquery_cli.debug import debug

def get_app():
    import builtins
    _ = builtins._

    exoplanet_app = typer.Typer(
        name="exoplanet",
        help=builtins._("Query the NASA Exoplanet Archive."),
        invoke_without_command=True,
        no_args_is_help=False
    )

    @exoplanet_app.callback()
    def exoplanet_main_callback(
        ctx: typer.Context,
        debug: bool = typer.Option(
            False,
            "-t",
            "--debug",
            help=_("Enable debug mode with verbose output."),
            envvar="AQC_DEBUG"
        ),
        verbose: bool = typer.Option(
            False,
            "-v",
            "--verbose",
            help=_("Enable verbose output.")
        )
    ):
        setup_debug_context(ctx, debug, verbose)

        if ctx.invoked_subcommand is None and \
           not any(arg in ["-h", "--help"] for arg in ctx.args):
            # Capture the full help output by explicitly calling the app with --help
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    exoplanet_app(ctx.args + ["--help"])
                except SystemExit:
                    pass
            full_help_text = help_output_capture.getvalue()

            # Extract only the "Commands" section using regex, including the full bottom border
            commands_match = re.search(r'╭─ Commands ─.*?(\n(?:│.*?\n)*)╰─.*─╯', full_help_text, re.DOTALL)
            if commands_match:
                commands_section = commands_match.group(0)
                filtered_commands_section = "\n".join([
                    line for line in commands_section.splitlines() if "Usage:" not in line
                ])
                console.print(filtered_commands_section)
            else:
                console.print(full_help_text)
            raise typer.Exit()

    @exoplanet_app.command(name="query", help=builtins._("Query the NASA Exoplanet Archive for a specific planet."))
    @global_keyboard_interrupt_handler
    def exoplanet_query_command(
        ctx: typer.Context,
        planet_name: str = typer.Argument(..., help=builtins._("Planet name (e.g., 'Kepler-186 f').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(
            25, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help=builtins._("Show all columns in the output table.")
        )
    ):
        # debug and verbose options are handled by the main callback
        if ctx.obj.get("DEBUG"):
            debug(f"query_exoplanet - planet_name: {planet_name}")

        console.print(f"[cyan]{_('Querying NASA Exoplanet Archive...')}[/cyan]")

        try:
            results = NasaExoplanetArchive.query_object(planet_name)

            if results and len(results) > 0:
                console.print(_("[green]Found {count} result(s) from NASA Exoplanet Archive.[/green]").format(count=len(results)))
                display_table(ctx, results, title=_("NASA Exoplanet Archive Query Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, results, output_file, output_format, _("NASA Exoplanet Archive query"))
            else:
                console.print(_("[yellow]No results found for your NASA Exoplanet Archive query.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("NASA Exoplanet Archive query"))
            raise typer.Exit(code=1)

    return exoplanet_app
