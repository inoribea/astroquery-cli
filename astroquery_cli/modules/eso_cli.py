import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.eso import Eso
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
    app = typer.Typer(
        name="eso",
        help=builtins._("Query the European Southern Observatory (ESO) archive."),
        invoke_without_command=True,
        no_args_is_help=False
    )

    @app.callback()
    def eso_callback(
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
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    app(ctx.args + ["--help"])
                except SystemExit:
                    pass
            full_help_text = help_output_capture.getvalue()

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

    @app.command(name="query", help=builtins._("Perform a query on ESO archive."))
    @global_keyboard_interrupt_handler
    def query_eso(
        ctx: typer.Context,
        object_name: Optional[str] = typer.Option(None, help=builtins._("Object name to query (e.g., 'M31').")),
        ra: Optional[float] = typer.Option(None, help=builtins._("Right Ascension in degrees.")),
        dec: Optional[float] = typer.Option(None, help=builtins._("Declination in degrees.")),
        radius: Optional[float] = typer.Option(None, help=builtins._("Search radius in degrees (for cone search).")),
        instrument: Optional[str] = typer.Option(None, help=builtins._("Instrument name (e.g., 'FORS2').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(
            25, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help=builtins._("Show all columns in the output table.")
        ),
    ):
        if ctx.obj.get("DEBUG"):
            debug(f"query_eso - object_name: {object_name}, ra: {ra}, dec: {dec}, radius: {radius}, instrument: {instrument}")

        console.print(f"[cyan]{_('Querying ESO archive...')}[/cyan]")

        try:
            eso = Eso()
            results = None

            if object_name:
                results = eso.query_object(object_name=object_name, instrument=instrument)
            elif ra is not None and dec is not None:
                if radius is None:
                    console.print(_("[red]Error: --radius is required when --ra and --dec are provided for a cone search.[/red]"))
                    raise typer.Exit(code=1)
                results = eso.query_region(ra=ra, dec=dec, radius=radius, instrument=instrument)
            else:
                console.print(_("[red]Error: Please provide either --object-name or both --ra and --dec (with --radius).[/red]"))
                raise typer.Exit(code=1)

            if results and len(results) > 0:
                console.print(_("[green]Found {count} result(s) from ESO.[/green]").format(count=len(results)))
                display_table(ctx, results, title=_("ESO Query Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, results, output_file, output_format, _("ESO query"))
            else:
                console.print(_("[yellow]No results found for your ESO query.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ESO query"))
            raise typer.Exit(code=1)

    @app.command(name="list-instruments", help=builtins._("List available ESO instruments."))
    @global_keyboard_interrupt_handler
    def list_instruments(ctx: typer.Context):
        console.print(f"[cyan]{_('Listing ESO instruments...')}[/cyan]")
        try:
            instruments = Eso.list_instruments()
            if instruments:
                console.print(_("[green]Available ESO Instruments:[/green]"))
                for i in instruments:
                    console.print(f"- {i}")
            else:
                console.print(_("[yellow]No ESO instruments found.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ESO list instruments"))
            raise typer.Exit(code=1)

    return app
