import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.heasarc import Heasarc
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
        name="heasarc",
        help=builtins._("Query the HEASARC database."),
        invoke_without_command=True, # Allow invoking without a subcommand
        # no_args_is_help=True # Show help if no arguments are provided (handled manually below)
    )

    @app.callback()
    @global_keyboard_interrupt_handler
    def heasarc_callback(
        ctx: typer.Context,
        # Moved query options to callback
        ra: Optional[float] = typer.Option(None, help=builtins._("Right Ascension in degrees.")),
        dec: Optional[float] = typer.Option(None, help=builtins._("Declination in degrees.")),
        radius: Optional[float] = typer.Option(None, help=builtins._("Search radius in degrees (for cone search).")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(
            25, "--max-rows-display", help=builtins._("Maximum number of rows to display. Use -1 for all rows.")
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help=builtins._("Show all columns in the output table.")
        ),
        max_rows: int = typer.Option(
            100, "--max-rows", help=builtins._("Maximum number of rows to retrieve from the HEASARC database. Use -1 for all rows.")
        ),
        enable_debug: bool = typer.Option(
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
        ),
    ):
        setup_debug_context(ctx, enable_debug, verbose)
        debug(f"heasarc_callback: ctx.invoked_subcommand={ctx.invoked_subcommand}, ctx.args={ctx.args}")
        heasarc = Heasarc() # Instantiate Heasarc here for all operations

        # Check if a subcommand was invoked (e.g., 'list')
        if ctx.invoked_subcommand is not None:
            return # Let the subcommand handle its own logic

    @app.command(name="query", help=builtins._("Query a specific HEASARC mission. Use 'heasarc list' to see available missions."))
    @global_keyboard_interrupt_handler
    def query_heasarc_mission(
        ctx: typer.Context,
        mission: str = typer.Argument(..., help=builtins._("HEASARC mission name (e.g., 'atnfpsr').")),
        ra: Optional[float] = typer.Option(None, help=builtins._("Right Ascension in degrees.")),
        dec: Optional[float] = typer.Option(None, help=builtins._("Declination in degrees.")),
        radius: Optional[float] = typer.Option(None, help=builtins._("Search radius in degrees (for cone search).")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(
            25, "--max-rows-display", help=builtins._("Maximum number of rows to display. Use -1 for all rows.")
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help=builtins._("Show all columns in the output table.")
        ),
        max_rows: int = typer.Option(
            100, "--max-rows", help=builtins._("Maximum number of rows to retrieve from the HEASARC database. Use -1 for all rows.")
        ),
    ):
        # Debug context is set up by the heasarc_callback
        heasarc = Heasarc() # Instantiate Heasarc here for all operations

        console.print(f"[cyan]{_('Querying HEASARC mission: {mission}...').format(mission=mission)}[/cyan]")

        try:
            # Get the actual catalog name from the mission list
            catalogs = heasarc.list_catalogs()
            
            catalog_name = None
            search_mission_upper = mission.strip().upper()

            # Specific mapping for 'atnfpsr' to 'atnfpulsar'
            if search_mission_upper == 'ATNFPSR':
                catalog_name = 'atnfpulsar'
            else:
                for row in catalogs:
                    # Use 'name' as the primary key for catalog/table name
                    if 'name' in row and row['name'].strip().upper() == search_mission_upper:
                        catalog_name = row['name']
                        break
                    # Fallback to 'Table' or 'CATALOG' if 'name' is not present or doesn't match
                    elif 'Table' in row and row['Table'].strip().upper() == search_mission_upper:
                        catalog_name = row['Table']
                        break
                    elif 'CATALOG' in row and row['CATALOG'].strip().upper() == search_mission_upper:
                        catalog_name = row['CATALOG']
                        break
            
            if catalog_name is None:
                console.print(_(f"[red]Error: Mission '{mission}' not found in HEASARC catalogs. Use 'heasarc list' to see available missions.[/red]"))
                raise typer.Exit(code=1)

            # Set maxrec for query
            maxrec_value = None if max_rows == -1 else max_rows

            if ra is not None and dec is not None:
                if radius is None:
                    console.print(_("[red]Error: --radius is required when --ra and --dec are provided for a cone search.[/red]"))
                    raise typer.Exit(code=1)
                adql_query = heasarc.query_region(ra=ra, dec=dec, radius=radius, catalog=catalog_name, get_query_payload=True, maxrec=maxrec_value)
                console.print(f"[debug] ADQL Query (cone): {adql_query}")
                results = heasarc.query_region(ra=ra, dec=dec, radius=radius, catalog=catalog_name, maxrec=maxrec_value)
            else:
                # Use query_tap for all-sky queries with the correct catalog name
                adql_query_string = f"SELECT * FROM {catalog_name}"
                console.print(f"[debug] ADQL Query (all-sky): {adql_query_string}")
                results = heasarc.query_tap(query=adql_query_string, maxrec=maxrec_value)

            if results and len(results) > 0:
                console.print(_("[green]Found {count} result(s) from HEASARC.[/green]").format(count=len(results)))
                display_table(ctx, results, title=_("HEASARC Query Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, results, output_file, output_format, _("HEASARC query"))
            else:
                console.print(_("[yellow]No results found for your HEASARC query.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("HEASARC query"))
            raise typer.Exit(code=1)

    @app.command(name="list", help=builtins._("List available HEASARC missions."))
    @global_keyboard_interrupt_handler
    def list_heasarc_missions(
        ctx: typer.Context,
        max_rows_display: int = typer.Option(
            25, "--max-rows-display", "--max-rows", help=builtins._("Maximum number of rows to display. Use -1 for all rows.")
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help=builtins._("Show all columns in the output table.")
        ),
        prefix: Optional[str] = typer.Option(
            None, "--prefix", "-p", help=builtins._("Filter missions by a starting prefix (e.g., 'atnfpsr').")
        ),
    ):
        debug(f"list_heasarc_missions: max_rows_display={max_rows_display}, show_all_columns={show_all_columns}, prefix={prefix}")
        heasarc = Heasarc()
        console.print(f"[cyan]{_('Listing HEASARC missions...')}[/cyan]")
        try:
            missions_table = heasarc.list_catalogs()
            
            if prefix:
                original_count = len(missions_table)
                # Determine the correct column name for filtering
                mission_name_column = None
                if 'name' in missions_table.colnames:
                    mission_name_column = 'name'
                elif 'Table' in missions_table.colnames:
                    mission_name_column = 'Table'
                elif 'CATALOG' in missions_table.colnames:
                    mission_name_column = 'CATALOG'
                
                if mission_name_column:
                    # Apply the filter using boolean indexing
                    mask = [str(name).lower().startswith(prefix.lower()) for name in missions_table[mission_name_column]]
                    missions_table = missions_table[mask]
                else:
                    # If no suitable column is found, log a warning or handle appropriately
                    debug("Could not find a suitable mission name column ('name', 'Table', or 'CATALOG') for filtering.")

                console.print(_("[cyan]Filtered from {original_count} to {filtered_count} missions with prefix \"{prefix}\".[/cyan]").format(original_count=original_count, filtered_count=len(missions_table), prefix=prefix))

            if missions_table:
                display_table(ctx, missions_table, title=_("Available HEASARC Missions"), max_rows=max_rows_display, show_all_columns=show_all_columns)
            else:
                console.print(_("[yellow]No HEASARC missions found matching your criteria.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("HEASARC list missions"))
            raise typer.Exit(code=1)
    return app
