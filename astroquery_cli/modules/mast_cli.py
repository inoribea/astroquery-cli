import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.mast import Observations
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
        name="mast",
        help=builtins._("Query the Mikulski Archive for Space Telescopes (MAST)."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def mast_callback(
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

    # ================== MAST_FIELDS =============================
    MAST_FIELDS = [
        "obsid",
        "provenance_name",
        "obs_collection",
        "instrument_name",
        "target_name",
        "t_min",
        "t_max",
        "s_ra",
        "s_dec",
        "em_min",
        "em_max",
        "telescope_name",
        "proposal_pi",
        "dataRights",
        "calib_level",
        "dataProductType",
        "obs_title",
        # ...
    ]
    # ============================================================

    Observations.TIMEOUT = 120
    Observations.PAGESIZE = 2000

    @app.command(name="object", help=builtins._("Query MAST for observations of an object."))
    @global_keyboard_interrupt_handler
    def query_object(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the astronomical object.")),
        radius: Optional[str] = typer.Option("0.2 deg", help=builtins._("Search radius around the object.")),
        obs_collection: Optional[List[str]] = typer.Option(None, "--collection", help=builtins._("Observation collection (e.g., 'HST', 'TESS').")),
        instrument_name: Optional[List[str]] = typer.Option(None, "--instrument", help=builtins._("Instrument name (e.g., 'WFC3', 'ACS').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
test: bool = typer.Option(False, "--test", "-t", help=builtins._("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying MAST for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        try:
            rad_quantity = parse_angle_str_to_quantity(ctx, radius) if radius else None
            result_table: Optional[AstropyTable] = Observations.query_object(
                object_name,
                radius=rad_quantity
            )

            if result_table and obs_collection:
                mask = [any(coll.upper() in str(item).upper() for coll in obs_collection) for item in result_table['obs_collection']]
                result_table = result_table[mask]
            if result_table and instrument_name:
                mask = [any(inst.upper() in str(item).upper() for inst in instrument_name) for item in result_table['instrument_name']]
                result_table = result_table[mask]


            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} observation(s) for '{object_name}'.[/green]").format(count=len(result_table), object_name=object_name))
                display_table(ctx, result_table, title=_("MAST Observations for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("MAST object query"))
            else:
                console.print(_("[yellow]No observations found for object '{object_name}' with specified criteria.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(ctx, e, "MAST object")
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="region", help=builtins._("Query MAST for observations in a sky region."))
    @global_keyboard_interrupt_handler
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M101').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '0.1deg', '5arcmin').")),
        obs_collection: Optional[List[str]] = typer.Option(None, "--collection", help=builtins._("Observation collection.")),
        instrument_name: Optional[List[str]] = typer.Option(None, "--instrument", help=builtins._("Instrument name.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
test: bool = typer.Option(False, "--test", "-t", help=builtins._("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying MAST for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            coord = parse_coordinates(ctx, coordinates)
            rad_quantity = parse_angle_str_to_quantity(ctx, radius)

            result_table: Optional[AstropyTable] = Observations.query_region(
                coord,
                radius=rad_quantity
            )
            if result_table and obs_collection:
                mask = [any(coll.upper() in str(item).upper() for coll in obs_collection) for item in result_table['obs_collection']]
                result_table = result_table[mask]
            if result_table and instrument_name:
                mask = [any(inst.upper() in str(item).upper() for inst in instrument_name) for item in result_table['instrument_name']]
                result_table = result_table[mask]

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} observation(s) in the region.[/green]").format(count=len(result_table)))
                display_table(ctx, result_table, title=_("MAST Observations for Region"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("MAST region query"))
            else:
                console.print(_("[yellow]No observations found for the specified region with given criteria.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("MAST region"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="get-products", help=builtins._("Get data product URLs for given observation IDs."))
    def get_products(ctx: typer.Context,
        obs_ids: List[str] = typer.Argument(..., help=builtins._("List of observation IDs.")),
        product_type: Optional[List[str]] = typer.Option(None, "--type", help=builtins._("Product type(s) (e.g., 'SCIENCE', 'PREVIEW').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(50, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(True, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
test: bool = typer.Option(False, "--test", "-t", help=builtins._("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Fetching product list for obs ID(s): {obs_id_list}...[/cyan]").format(obs_id_list=', '.join(obs_ids)))
        try:
            products_table: Optional[AstropyTable] = Observations.get_product_urls(
                obs_ids,
                productType=product_type if product_type else None
            )
            if products_table and len(products_table) > 0:
                console.print(_("[green]Found {count} data products.[/green]").format(count=len(products_table)))
                display_table(ctx, products_table, title=_("MAST Data Products"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, products_table, output_file, output_format, _("MAST products list"))
                console.print(_("[info]Use 'aqc mast download-products <obs_id> ...' or 'astroquery.mast.Observations.download_products()' to download.[/info]"))
            else:
                console.print(_("[yellow]No data products found for the given observation ID(s) and criteria.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("MAST get_product_urls"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    return app
