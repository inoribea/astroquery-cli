import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.alma import Alma
import logging # Import logging
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    parse_coordinates,
    parse_angle_str_to_quantity,
    global_keyboard_interrupt_handler,
)
from .. import i18n
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout
import sys # Import sys
from astroquery_cli.common_options import setup_debug_context # Import setup_debug_context
from astroquery_cli.debug import debug # Import debug function

def get_app():
    import builtins
    _ = builtins._ # Ensure _ is available
    app = typer.Typer(
        name="alma",
        help=builtins._("Query the ALMA archive."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def alma_callback(
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

        # Custom help display logic
        if ctx.invoked_subcommand is None and \
           not any(arg in ["-h", "--help"] for arg in ctx.args): # Use ctx.args for subcommand arguments
            # Capture the full help output by explicitly calling the app with --help
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    # Call the app with --help to get the full help output
                    # Pass the current command's arguments to simulate the help call
                    app(ctx.args + ["--help"])
                except SystemExit:
                    pass # Typer exits after showing help, catch the SystemExit exception
            full_help_text = help_output_capture.getvalue()

            # Extract only the "Commands" section using regex, including the full bottom border
            commands_match = re.search(r'╭─ Commands ─.*?(\n(?:│.*?\n)*)╰─.*─╯', full_help_text, re.DOTALL)
            if commands_match:
                commands_section = commands_match.group(0)
                # Remove the "Usage:" line if present in the full help text
                filtered_commands_section = "\n".join([
                    line for line in commands_section.splitlines() if "Usage:" not in line
                ])
                console.print(filtered_commands_section)
            else:
                # Fallback: if commands section not found, print full help
                console.print(full_help_text)
            raise typer.Exit()

    # Suppress ALMA log messages during import
    logging.getLogger('astroquery.alma').setLevel(logging.WARNING)

    Alma.ROW_LIMIT = 50
    Alma.TIMEOUT = 60

    ALMA_FIELDS = [
        'band_list', 'data_rights', 'frequency', 'instrument_name',
        # ...
    ]

    @app.command(name="object", help=builtins._("Query ALMA for observations of an object."))
    @global_keyboard_interrupt_handler
    def query_object(
        ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the astronomical object, e.g., 'Orion KL', 'Sgr B2', 'NGC 253'.")),
        public_data: bool = typer.Option(True, help=builtins._("Query only public data.")),
        science_data: bool = typer.Option(True, help=builtins._("Query only science data.")),
        payload: Optional[List[str]] = typer.Option(None, "--payload-field", help=builtins._("Specify payload fields to query (e.g., 'band_list', 'target_name').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
        _ = i18n.get_translator(lang)
        alma = Alma()
        try:
            # Debugging information
            debug(f"query_object - object_name: {object_name}")

            console.print(f"[cyan]{_('Querying ALMA for object: {object_name}').format(object_name=object_name)}[/cyan]")
            query_payload = {'source_name_alma': object_name}
            if payload:
                for item in payload:
                    if '=' in item:
                        key, value = item.split('=', 1)
                        query_payload[key] = value
                    else:
                        console.print(_("[yellow]Payload item '{item}' is not a key=value pair. Ignoring.[/yellow]").format(item=item))

            result_table: Optional[AstropyTable] = alma.query(
                payload=query_payload,
                public=public_data,
                science=science_data
            )

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) for '{object_name}'.[/green]").format(count=len(result_table), object_name=object_name))
                display_table(ctx, result_table, title=_("ALMA Data for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("ALMA object query"))
            else:
                console.print(_("[yellow]No information found for object '{object_name}'.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ALMA object"))
            raise typer.Exit(code=1)

    @app.command(name="region", help=builtins._("Query ALMA for observations in a sky region."))
    @global_keyboard_interrupt_handler
    def query_region(
        ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', '150.0 2.0').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '0.1deg', '5arcmin').")),
        public_data: bool = typer.Option(True, help=builtins._("Query only public data.")),
        science_data: bool = typer.Option(True, help=builtins._("Query only science data.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
        _ = i18n.get_translator(lang)
        try:
            # Debugging information
            debug(f"query_region - coordinates: {coordinates}, radius: {radius}")

            console.print(f"[cyan]{_('Querying ALMA for region: {coordinates} with radius {radius}').format(coordinates=coordinates, radius=radius)}[/cyan]")
            coord = parse_coordinates(ctx, coordinates)
            rad = parse_angle_str_to_quantity(ctx, radius)
            alma = Alma()
            result_table: Optional[AstropyTable] = alma.query_region(
                coord,
                radius=rad,
                public=public_data,
                science=science_data
            )

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) in the region.[/green]").format(count=len(result_table)))
                display_table(ctx, result_table, title=_("ALMA Data for Region"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("ALMA region query"))
            else:
                console.print(_("[yellow]No information found for the specified region.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ALMA region"))
            raise typer.Exit(code=1)


    return app
