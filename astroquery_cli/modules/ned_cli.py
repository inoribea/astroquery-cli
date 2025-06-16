import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.ned import Ned
from ..i18n import get_translator
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
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout
from astroquery_cli.common_options import setup_debug_context # Import setup_debug_context

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="ned",
        help=builtins._("Query the NASA/IPAC Extragalactic Database (NED)."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def ned_callback(
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

    # ================== NED_FIELDS ==============================
    NED_FIELDS = [
        "Object Name",
        "Type",
        "RA(deg)",
        "DEC(deg)",
        "Redshift",
        "Photometry",
        "References",
        # ...
    ]
    # ============================================================

    Ned.TIMEOUT = 120

    @app.command(name="object", help=builtins._("Query NED for an object by name."))
    @global_keyboard_interrupt_handler
    def query_object(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the extragalactic object.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(1, help=builtins._("Maximum number of objects to display (usually 1 for direct name).")),
        show_all_columns: bool = typer.Option(True, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying NED for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        try:
            result_table: Optional[AstropyTable] = Ned.query_object(object_name)

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found information for '{object_name}'.[/green]").format(object_name=object_name))
                display_table(ctx, result_table, title=_("NED Data for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _( "NED object query"))
            else:
                console.print(_("[yellow]No information found for object '{object_name}'.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("NED object"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="region", help=builtins._("Query NED for objects in a sky region."))
    @global_keyboard_interrupt_handler
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M101').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '5arcmin', '0.1deg').")),
        equinox: str = typer.Option("J2000", help=builtins._("Equinox of coordinates (e.g., 'J2000', 'B1950').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying NED for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            coord = parse_coordinates(ctx, coordinates)
            rad_quantity = parse_angle_str_to_quantity(ctx, radius)

            result_table: Optional[AstropyTable] = Ned.query_region(
                coord,
                radius=rad_quantity,
                equinox=equinox
            )

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} object(s) in the region.[/green]").format(count=len(result_table)))
                display_table(ctx, result_table, title=_("NED Objects in Region"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _( "NED region query"))
            else:
                console.print(_("[yellow]No objects found in the specified region.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("NED region"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="images", help=builtins._("Get image metadata for an object from NED."))
    @global_keyboard_interrupt_handler
    def get_images(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the extragalactic object.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(10, help=builtins._("Maximum number of image entries to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(True, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Fetching image list from NED for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        try:
            images_table: Optional[AstropyTable] = Ned.get_images(object_name)
            if images_table and len(images_table) > 0:
                console.print(_("[green]Found {count} image entries for '{object_name}'.[/green]").format(count=len(images_table), object_name=object_name))
                display_table(ctx, images_table, title=_("NED Image List for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, images_table, output_file, output_format, _( "NED image list query"))
            else:
                console.print(_("[yellow]No image entries found for object '{object_name}'.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("NED images"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    return app
