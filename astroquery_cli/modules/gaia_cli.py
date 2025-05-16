# astroquery_cli/modules/gaia_cli.py
from typing import Optional, List

import typer
from astroquery.gaia import Gaia, conf as gaia_conf
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console

from ..utils import display_table, handle_astroquery_exception, parse_coordinates, parse_angle_str_to_quantity, common_output_options, save_table_to_file

console = Console()
app = typer.Typer(
    name="gaia",
    help="Query the ESA Gaia mission archive. 🛰️"
)

# Gaia Configuration
gaia_conf.show_server_messages = False # Suppress server messages by default
# gaia_conf.tap_plus_url = "..." # Can be configured if needed

GAIA_TABLES = {
    "main_source": "gaiadr3.gaia_source", # Default and most common
    "dr2_source": "gaiadr2.gaia_source",
    "edr3_source": "gaiaedr3.gaia_source",
    "tmass_best_neighbour": "gaiadr3.tmass_psc_xsc_best_neighbour",
    "allwise_best_neighbour": "gaiadr3.allwise_best_neighbour",
    # Add more common tables or allow free-form input
}

@app.command(name="cone-search", help="Perform a cone search around a coordinate.")
def cone_search(
    target: str = typer.Argument(..., help="Central object name or coordinates (e.g., 'M31', '10.68h +41.26d')."),
    radius: str = typer.Option("10arcsec", help="Search radius (e.g., '5arcmin', '0.1deg')."),
    table_name: str = typer.Option(
        GAIA_TABLES["main_source"],
        help=f"Gaia table to query. Common choices: {list(GAIA_TABLES.keys())} or specify full table name.",
        autocompletion=lambda: list(GAIA_TABLES.keys())
    ),
    columns: Optional[List[str]] = typer.Option(None, "--col", help="Specific columns to retrieve (e.g., 'source_id', 'ra', 'dec', 'pmra'). Default: all columns from the table for a small radius, or a default set for larger radii."),
    row_limit: int = typer.Option(1000, help="Maximum number of rows to return from the server."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table."),
    login_user: Optional[str] = typer.Option(None, envvar="GAIA_USER", help="Gaia archive username (or set GAIA_USER env var)."),
    login_password: Optional[str] = typer.Option(None, envvar="GAIA_PASSWORD", help="Gaia archive password (or set GAIA_PASSWORD env var). Prompt if user set but no password.", prompt=False, hide_input=True) # prompt=False initially
):
    """
    Performs a cone search on the Gaia archive.
    Example: aq gaia cone-search M13 --radius 1arcmin --table_name gaiadr3.gaia_source
    Example: aq gaia cone-search "17h45m40s -29d00m28s" --radius 5arcsec --col source_id --col phot_g_mean_mag
    """
    resolved_table_name = GAIA_TABLES.get(table_name, table_name) # Use mapping if key, else use as direct table name
    console.print(f"[cyan]Performing Gaia cone search on '{resolved_table_name}' around '{target}' with radius {radius}...[/cyan]")

    if login_user and not login_password:
        login_password = typer.prompt("Gaia archive password", hide_input=True)

    if login_user and login_password:
        console.print(f"[dim]Logging into Gaia archive as '{login_user}'...[/dim]")
        try:
            Gaia.login(user=login_user, password=login_password)
        except Exception as e:
            console.print(f"[bold red]Gaia login failed: {e}[/bold red]")
            # Decide if to proceed anonymously or exit. For cone search, anonymous often works.
            console.print("[yellow]Proceeding with anonymous access if possible.[/yellow]")
    elif Gaia.authenticated():
        console.print(f"[dim]Already logged into Gaia archive as '{Gaia.credentials.username if Gaia.credentials else 'unknown user'}'.[/dim]")
    else:
        console.print("[dim]No Gaia login credentials provided. Using anonymous access.[/dim]")


    try:
        coords_obj = parse_coordinates(target)
        rad_quantity = parse_angle_str_to_quantity(radius)
        if rad_quantity is None: # Should not happen if parse_angle_str_to_quantity raises Exit on error
            console.print("[bold red]Invalid radius provided.[/bold red]")
            raise typer.Exit(code=1)

        query = f"""
        SELECT {', '.join(columns) if columns else '*'}
        FROM {resolved_table_name}
        WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {coords_obj.ra.deg}, {coords_obj.dec.deg}, {rad_quantity.to(u.deg).value}))
        LIMIT {row_limit}
        """
        # Using Gaia.query_object_async for cone search is often recommended.
        # Or construct ADQL for Gaia.launch_job_async
        # Gaia.cone_search_async might be simpler if it fits the needs.

        # For simplicity and control over columns/table, let's use a synchronous ADQL job.
        console.print(f"[dim]Executing ADQL query (first {row_limit} rows):[/dim]")
        console.print(f"[dim]{query.strip()}[/dim]")

        job = Gaia.launch_job(query, dump_to_file=False) # Synchronous
        result_table = job.get_results()

        if result_table is not None and len(result_table) > 0:
            title = f"Gaia Cone Search Results ({resolved_table_name})"
            if Gaia.authenticated() and Gaia.credentials:
                 title += f" (User: {Gaia.credentials.username})"
            display_table(result_table, title=title, max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "Gaia cone search")
        else:
            console.print(f"[yellow]No results found from Gaia for this cone search.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, f"Gaia cone search on {resolved_table_name}")
        raise typer.Exit(code=1)
    finally:
        if login_user and Gaia.authenticated(): # Logout if we logged in
            Gaia.logout()
            console.print("[dim]Logged out from Gaia archive.[/dim]")


@app.command(name="adql-query", help="Execute a raw ADQL query (synchronous).")
def adql_query(
    query: str = typer.Argument(..., help="The ADQL query string."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table."),
    login_user: Optional[str] = typer.Option(None, envvar="GAIA_USER", help="Gaia archive username (or set GAIA_USER env var)."),
    login_password: Optional[str] = typer.Option(None, envvar="GAIA_PASSWORD", help="Gaia archive password (or set GAIA_PASSWORD env var). Prompt if user set but no password.", prompt=False, hide_input=True)
):
    """
    Executes a raw ADQL query against the Gaia archive.
    The query is run synchronously. For long queries, consider using the Gaia web interface or astroquery scripting.
    Example: aq gaia adql-query "SELECT TOP 10 source_id, ra, dec FROM gaiadr3.gaia_source WHERE phot_g_mean_mag < 10"
    """
    console.print(f"[cyan]Executing Gaia ADQL query...[/cyan]")
    console.print(f"[dim]{query}[/dim]")

    if login_user and not login_password:
        login_password = typer.prompt("Gaia archive password", hide_input=True)

    if login_user and login_password:
        console.print(f"[dim]Logging into Gaia archive as '{login_user}'...[/dim]")
        try:
            Gaia.login(user=login_user, password=login_password)
        except Exception as e:
            console.print(f"[bold red]Gaia login failed: {e}[/bold red]")
            console.print("[yellow]Proceeding with anonymous access if possible.[/yellow]")
    elif Gaia.authenticated():
        console.print(f"[dim]Already logged into Gaia archive as '{Gaia.credentials.username if Gaia.credentials else 'unknown user'}'.[/dim]")

    try:
        job = Gaia.launch_job(query, dump_to_file=False) # Synchronous
        result_table = job.get_results()

        if result_table is not None and len(result_table) > 0:
            title = f"Gaia ADQL Query Results"
            if Gaia.authenticated() and Gaia.credentials:
                 title += f" (User: {Gaia.credentials.username})"
            display_table(result_table, title=title, max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "Gaia ADQL query")
        else:
            console.print(f"[yellow]ADQL query returned no results or an empty table.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, "Gaia ADQL query")
        # astroquery often raises a generic Exception for TapPlusJobError, so check message
        if "ERROR:" in str(e):
            console.print(f"[bold red]ADQL Query Error Details from server:\n{str(e)}[/bold red]")
        raise typer.Exit(code=1)
    finally:
        if login_user and Gaia.authenticated(): # Logout if we logged in
            Gaia.logout()
            console.print("[dim]Logged out from Gaia archive.[/dim]")
