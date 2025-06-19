import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.esasky import ESASky
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
from ..i18n import get_translator
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout
from astroquery_cli.common_options import setup_debug_context # Import setup_debug_context
from astroquery_cli.debug import debug # Import debug function

def get_app():
    import builtins
    _ = builtins._ # This line is fine, it just ensures _ is available in this scope
    app = typer.Typer(
        name="esasky",
        help=builtins._("Query the ESA Sky archive."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def esasky_callback(
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
    
    # ================== ESASKY_CATALOGS =========================
    ESASKY_CATALOGS = [
        "TYCHO-2",
        "2RXS",
        "ALLWISE",
        "PLANCK-PSZ2",
        "PLANCK-PCCS2-LFI",
        "PLANCK-PCCS2-HFI",
        "XMM-SLEW",
        "GAIA-DR3",
        "PLANCK-PGCC",
        "INTEGRAL",
        "HIPPARCOS-2",
        "PLANCK-PCCS2E-HFI",
        "HERSCHEL-SPSC-350",
        "XMM-EPIC",
        "HERSCHEL-SPSC-250",
        "HERSCHEL-HPPSC-160",
        "HERSCHEL-HPPSC-100",
        "HERSCHEL-HPPSC-070",
        "AKARI-IRC-SC",
        "OU_BLAZARS",
        "TWOMASS",
        "HERSCHEL-SPSC-500",
        "EROSITA-EFEDS-MAIN",
        "EROSITA-EFEDS-HARD",
        "EUCLID-MER",
        "atnfpsr-SC21",
        "XMM-EPIC-STACK",
        "XMM-OM",
        "HCV",
        "FERMI_3FHL",
        "FERMI_4FGL-DR2",
        "EROSITA-ETACHA-MAIN",
        "SWIFT-2SXPS",
        "EROSITA-ETACHA-HARD",
        "FERMI_4LAC-DR2",
        "ICECUBE",
        "HSC",
        "PLATO ASPIC1.1",
        "2WHSP",
        "GAIA-FPR",
        "EROSITA-ERASS-HARD",
        "EROSITA-ERASS-MAIN",
        "GLADE+",
        "LAMOST_MRS",
        "LAMOST_LRS"
    ]
    # ============================================================
    # ================== ESASKY_FIELDS ===========================
    ESASKY_FIELDS = [
        "main_id",
        "source_id",
        "ra",
        "dec",
        # ...
    ]
    # ============================================================



    @app.command(name="object", help=builtins._("Query ESASky catalogs for an object."))
    @global_keyboard_interrupt_handler
    def query_object_catalogs(ctx: typer.Context,
        object_name: str = typer.Argument(
            ...,
            help=builtins._("Name of the astronomical object (e.g., 'NGC 253', 'HD 189733'). eg：M31、NGC 253、HD 189733")
        ),
        catalogs: Optional[List[str]] = typer.Option(
            None,
            "--catalog",
            help=builtins._("Specify catalogs to query (e.g., 'GAIA-DR3', '2MASS', 'ALLWISE'). Can be specified multiple times. Use 'list-catalogs' command to see all available catalogs. Default: GAIA-DR3.")
        ),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
test: bool = typer.Option(False, "--test", "-t", help=builtins._("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying ESASky catalogs for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        try:
            # Ensure catalogs_to_query is always a list of strings.
            # If catalogs is None or empty, use the predefined ESASKY_CATALOGS.
            # Otherwise, use the catalogs provided by the user.
            catalogs_to_query = catalogs if catalogs else ["GAIA-DR3"]
            
            result_tables_dict: Optional[dict] = ESASky.query_object_catalogs(object_name, catalogs=catalogs_to_query)

            if result_tables_dict:
                console.print(_("[green]Found data for '{object_name}' in {count} catalog(s).[/green]").format(object_name=object_name, count=len(result_tables_dict)))
                from astropy.table.table import Table
                try:
                    from astropy.table.table import TableList
                except ImportError:
                    TableList = None
                try:
                    from astroquery.utils.commons import TableList as AQTableList
                except ImportError:
                    AQTableList = None
                if isinstance(result_tables_dict, dict):
                    for cat_name, table_list in result_tables_dict.items():
                        if table_list:
                            table = table_list[0]
                            display_table(ctx, table, title=_("ESASky: {cat_name} for {object_name}").format(cat_name=cat_name, object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                            if output_file:
                                save_table_to_file(table, output_file.replace(".", f"_{cat_name}."), output_format, _("ESASky {cat_name} object query").format(cat_name=cat_name))
                        else:
                            console.print(_("[yellow]No results from catalog '{cat_name}' for '{object_name}'.[/yellow]").format(cat_name=cat_name, object_name=object_name))
                elif (TableList is not None and isinstance(result_tables_dict, TableList)) or (AQTableList is not None and isinstance(result_tables_dict, AQTableList)):
                    for table in result_tables_dict:
                        display_table(ctx, table, title=_("ESASky object result"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                        if output_file:
                            save_table_to_file(table, output_file, output_format, _("ESASky object query"))
                    return
                elif isinstance(result_tables_dict, Table):
                    display_table(ctx, result_tables_dict, title=_("ESASky object result"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                    if output_file:
                        save_table_to_file(result_tables_dict, output_file, output_format, _("ESASky object query"))
                else:
                    if hasattr(result_tables_dict, "tables") and hasattr(result_tables_dict, "keys"):
                        for table in result_tables_dict:
                            cat_name = getattr(table, "name", None) or getattr(table, "meta", {}).get("name", "Unknown")
                            display_table(ctx, table, title=_("ESASky: {cat_name} for {object_name}").format(cat_name=cat_name, object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                            if output_file:
                                save_table_to_file(table, output_file.replace(".", f"_{cat_name}."), output_format, _("ESASky {cat_name} object query").format(cat_name=cat_name))
                        return
                    else:
                        console.print(_("[yellow]Unknown result type from ESASky.query_object_catalogs.[/yellow]"))
                        debug(f"type: {type(result_tables_dict)}, value: {result_tables_dict}")
            else:
                console.print(_("[yellow]No catalog information found for object '{object_name}'.[/yellow]").format(object_name=object_name))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ESASky object"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="region", help=builtins._("Query ESASky catalogs in a sky region."))
    @global_keyboard_interrupt_handler
    def query_region_catalogs(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M101', '299.86808 -14.67788').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '0.1deg', '5arcmin', '10s').")),
        catalogs: Optional[List[str]] = typer.Option(
            None,
            "--catalog",
            help=builtins._("Specify catalogs to query (e.g., 'XMM-Newton (XMM-SSC)', 'atnfpsr (CDA)'). Can be specified multiple times. Use 'object' command to see all available catalogs.")
        ),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
test: bool = typer.Option(False, "--test", "-t", help=builtins._("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying ESASky catalogs for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            rad_quantity = parse_angle_str_to_quantity(radius)
            result_tables_dict: Optional[dict] = ESASky.query_region_catalogs(coordinates, radius=rad_quantity, catalogs=catalogs if catalogs else None)

            if result_tables_dict:
                console.print(_("[green]Found data in {count} catalog(s) for the region.[/green]").format(count=len(result_tables_dict)))
                for cat_name, table_list in result_tables_dict.items():
                    if table_list:
                        table = table_list[0]
                        display_table(ctx, table, title=_("ESASky: {cat_name} for region").format(cat_name=cat_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                        if output_file:
                            save_table_to_file(table, output_file.replace(".", f"_{cat_name}."), output_format, _("ESASky {cat_name} region query").format(cat_name=cat_name))
                    else:
                        console.print(_("[yellow]No results from catalog '{cat_name}' for the region.[/yellow]").format(cat_name=cat_name))
            else:
                console.print(_("[yellow]No catalog information found for the specified region.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ESASky region"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="list", help=builtins._("List available missions/catalogs in ESASky."))
    @global_keyboard_interrupt_handler
    def list_catalogs(ctx: typer.Context,
test: bool = typer.Option(False, "--test", "-t", help=builtins._("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Fetching list of available ESASky missions/catalogs...[/cyan]"))
        try:
            missions_raw_data = ESASky.list_catalogs()
            missions_table: Optional[AstropyTable] = None

            if missions_raw_data:
                if isinstance(missions_raw_data, AstropyTable):
                    missions_table = missions_raw_data
                elif isinstance(missions_raw_data, list):
                    # If it's a list of strings, create a single-column table
                    if all(isinstance(item, str) for item in missions_raw_data):
                        missions_table = AstropyTable({'Catalog': missions_raw_data})
                    else:
                        console.print(_("[bold red]Unexpected list content from ESASky.list_catalogs(). Expected list of strings or AstropyTable.[/bold red]"))
                        raise typer.Exit(code=1)
                else:
                    console.print(_("[bold red]Unexpected return type from ESASky.list_catalogs(). Expected AstropyTable or list.[/bold red]"))
                    raise typer.Exit(code=1)
            
            if missions_table and len(missions_table) > 0:
                display_table(ctx, missions_table, title=_("Available ESASky Missions/Catalogs"), max_rows=-1)
            else:
                console.print(_("[yellow]Could not retrieve mission list or list is empty.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ESASky list_catalogs"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()
        
    return app
