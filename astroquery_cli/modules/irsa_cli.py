import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.irsa import Irsa
from astroquery.ipac.irsa import Irsa as IrsaGator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    parse_coordinates,
    parse_angle_str_to_quantity,
    global_keyboard_interrupt_handler
)
from ..i18n import get_translator
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout
from astroquery_cli.common_options import setup_debug_context # Import setup_debug_context

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="irsa",
        help=builtins._("Query NASA/IPAC Infrared Science Archive (IRSA)."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def irsa_callback(
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

    # ================== IRSA_FIELDS =============================
    IRSA_FIELDS = [
        "ra",
        "dec",
        "designation",
        "w1mpro",
        "w2mpro",
        "w3mpro",
        "w4mpro",
        "ph_qual",
        "cc_flags",
        "ext_flg",
        # ...
    ]
    # ============================================================


    Irsa.ROW_LIMIT = 500

    @app.command(name="gator", help=builtins._("Query a specific catalog in IRSA using Gator."))
    @global_keyboard_interrupt_handler
    def query_gator(ctx: typer.Context,
        catalog: str = typer.Argument(..., help=builtins._("Name of the IRSA catalog (e.g., 'allwise_p3as_psd', 'fp_psc').")),
        coordinates: Optional[str] = typer.Argument(None, help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M51'). If not provided, returns first 500 rows.")),
        radius: Optional[str] = typer.Argument(None, help=builtins._("Search radius (e.g., '10arcsec', '0.5deg'). Required if coordinates provided.")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve (comma separated or multiple use). Use 'all' for all columns.")),
        column_filters: Optional[List[str]] = typer.Option(None, "--filter", help=builtins._("Column filters (e.g., 'w1mpro>10', 'ph_qual=A'). Can be specified multiple times.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        import time
        test_mode = ctx.obj.get("test") if ctx.obj else False
        start = time.perf_counter() if test_mode else None

        try:
            if coordinates and radius:
                console.print(_("[cyan]Querying IRSA catalog '{catalog}' via Gator for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(catalog=catalog, coordinates=coordinates, radius=radius))
                coord = parse_coordinates(ctx, coordinates)
                rad_quantity = parse_angle_str_to_quantity(ctx, radius)

                # Use query_region with catalog parameter for Gator-like functionality
                result_table: Optional[AstropyTable] = Irsa.query_region(
                    coordinates=coord,
                    radius=rad_quantity,
                    catalog=catalog
                )
            elif coordinates and not radius:
                console.print(_("[red]Error: Radius is required when coordinates are provided.[/red]"))
                raise typer.Exit(code=1)
            else:
                console.print(_("[cyan]Browsing IRSA catalog '{catalog}' (first {limit} rows)...[/cyan]").format(catalog=catalog, limit=Irsa.ROW_LIMIT))
                # For browsing without coordinates, we can use a wide search or try to get schema info
                # Since IRSA Gator typically requires coordinates, we'll use a fallback approach
                from astropy.coordinates import SkyCoord
                import astropy.units as u
                
                # Use galactic center as default coordinates for browsing
                coord = SkyCoord("17h45m40.04s", "-29d00m28.1s", frame='icrs')
                rad_quantity = 180 * u.deg  # Very wide search to get representative data
                
                # Use query_region with catalog parameter for browsing
                result_table: Optional[AstropyTable] = Irsa.query_region(
                    coordinates=coord,
                    radius=rad_quantity,
                    catalog=catalog
                )

            # Apply column selection
            if result_table and columns and columns != ["all"]:
                col_set = set(result_table.colnames)
                selected_cols = [col for col in columns if col in col_set]
                if selected_cols:
                    result_table = result_table[selected_cols]

            # Apply column filters
            if result_table and column_filters:
                for filt in column_filters:
                    # Example: 'w1mpro>10', 'ph_qual==A'
                    import re
                    m = re.match(r"^(\w+)\s*([<>=!]+)\s*([\w\.\-]+)$", filt)
                    if m:
                        col, op, val = m.groups()
                        if col in result_table.colnames:
                            expr = f"result_table['{col}'] {op} {repr(type(result_table[col][0])(val))}"
                            result_table = result_table[eval(expr)]
                    # else: ignore malformed filter

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) in '{catalog}'.[/green]").format(count=len(result_table), catalog=catalog))
                display_table(ctx, result_table, title=_("IRSA Gator: {catalog}").format(catalog=catalog), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("IRSA Gator {catalog} query").format(catalog=catalog))
            else:
                console.print(_("[yellow]No information found in '{catalog}' for the specified region.[/yellow]").format(catalog=catalog))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA Gator query for catalog {catalog}").format(catalog=catalog))
            raise typer.Exit(code=1)

        if test_mode:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="list-gator-catalogs", help=builtins._("List available catalogs in IRSA Gator for a mission."))
    def list_gator_catalogs(ctx: typer.Context,
        mission: Optional[str] = typer.Option(None, help=builtins._("Filter catalogs by mission code (e.g., 'WISE', 'SPITZER').")),
    ):
        console.print(_("[cyan]Fetching list of available IRSA Gator catalogs {mission_info}...[/cyan]").format(mission_info=_("for mission {mission}").format(mission=mission) if mission else ''))
        try:
            console.print(_("[yellow]Listing all Gator catalogs programmatically is complex via astroquery.irsa directly.[/yellow]"))
            console.print(_("[yellow]Please refer to the IRSA Gator website for a comprehensive list of catalogs.[/yellow]"))
            console.print(_("[yellow]Common catalog examples: 'allwise_p3as_psd', 'ptf_lightcurves', 'fp_psc' (2MASS).[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA list_gator_catalogs"))
            raise typer.Exit(code=1)

    @app.command(name="region", help=builtins._("Perform a cone search across multiple IRSA collections."))
    @global_keyboard_interrupt_handler
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M31').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '10arcsec', '0.5deg').")),
        collection: Optional[str] = typer.Option(None, help=builtins._("Specify a collection (e.g., 'allwise', '2MASS'). Leave blank for a general search.")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve (comma separated or multiple use). Use 'all' for all columns.")),
        column_filters: Optional[List[str]] = typer.Option(None, "--filter", help=builtins._("Column filters (e.g., 'w1mpro>10', 'ph_qual=A'). Can be specified multiple times.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        console.print(_("[cyan]Performing IRSA cone search for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            coord = parse_coordinates(ctx, coordinates)
            rad_quantity = parse_angle_str_to_quantity(ctx, radius)

            result_table: Optional[AstropyTable] = Irsa.query_region(
                coordinates=coord,
                radius=rad_quantity,
                collection=collection
            )

            # Apply column selection
            if result_table and columns and columns != ["all"]:
                col_set = set(result_table.colnames)
                selected_cols = [col for col in columns if col in col_set]
                if selected_cols:
                    result_table = result_table[selected_cols]

            # Apply column filters
            if result_table and column_filters:
                for filt in column_filters:
                    import re
                    m = re.match(r"^(\w+)\s*([<>=!]+)\s*([\w\.\-]+)$", filt)
                    if m:
                        col, op, val = m.groups()
                        if col in result_table.colnames:
                            expr = f"result_table['{col}'] {op} {repr(type(result_table[col][0])(val))}"
                            result_table = result_table[eval(expr)]

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) in IRSA holdings.[/green]").format(count=len(result_table)))
                display_table(ctx, result_table, title=_("IRSA Cone Search Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("IRSA cone search query"))
            else:
                console.print(_("[yellow]No information found in IRSA for the specified region{collection_info}.[/yellow]").format(collection_info=_(" in collection {collection}").format(collection=collection) if collection else ''))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA query_region"))
            raise typer.Exit(code=1)

    return app
