import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.irsa import Irsa
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    parse_coordinates,
    parse_angle_str_to_quantity,
)

app = typer.Typer(
    name="irsa",
    help="Query NASA/IPAC Infrared Science Archive (IRSA)."
)

Irsa.ROW_LIMIT = 500 # Default is 500, can be adjusted

@app.command(name="query-gator", help="Query a specific catalog in IRSA using Gator.")
def query_gator(
    catalog: str = typer.Argument(..., help="Name of the IRSA catalog (e.g., 'allwise_p3as_psd')."),
    coordinates: str = typer.Argument(..., help="Coordinates (e.g., '10.68h +41.26d', 'M51')."),
    radius: str = typer.Argument(..., help="Search radius (e.g., '10arcsec', '0.5deg')."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying IRSA catalog '{catalog}' via Gator for region: '{coordinates}' with radius '{radius}'...[/cyan]")
    try:
        coord = parse_coordinates(coordinates)
        rad_quantity = parse_angle_str_to_quantity(radius)

        result_table: Optional[AstropyTable] = Irsa.query_gator(
            catalog=catalog,
            coordinates=coord,
            radius=rad_quantity
        )

        if result_table and len(result_table) > 0:
            console.print(f"[green]Found {len(result_table)} match(es) in '{catalog}'.[/green]")
            display_table(result_table, title=f"IRSA Gator: {catalog}", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, f"IRSA Gator {catalog} query")
        else:
            console.print(f"[yellow]No information found in '{catalog}' for the specified region.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, f"IRSA Gator query for catalog {catalog}")
        raise typer.Exit(code=1)

@app.command(name="list-gator-catalogs", help="List available catalogs in IRSA Gator for a mission.")
def list_gator_catalogs(
    mission: Optional[str] = typer.Option(None, help="Filter catalogs by mission code (e.g., 'WISE', 'SPITZER')."),
):
    console.print(f"[cyan]Fetching list of available IRSA Gator catalogs {f'for mission {mission}' if mission else ''}...[/cyan]")
    try:
        # The list_catalogs function in astroquery.irsa might not exist or be directly usable for Gator.
        # Gator catalog listing is usually done via the web interface or TAP.
        # For now, we'll simulate or point to documentation.
        # A more robust way would be to query the IRSA TAP service for table metadata.
        # As a placeholder, we can list some common ones or tell user to check web.
        console.print("[yellow]Listing all Gator catalogs programmatically is complex via astroquery.irsa directly.[/yellow]")
        console.print("[yellow]Please refer to the IRSA Gator website for a comprehensive list of catalogs.[/yellow]")
        console.print("[yellow]Common catalog examples: 'allwise_p3as_psd', 'ptf_lightcurves', 'fp_psc' (2MASS).[/yellow]")
        # If Irsa.list_catalogs() becomes available or if we implement TAP query:
        # catalogs_table = Irsa.list_catalogs(mission_code=mission)
        # display_table(catalogs_table, title="IRSA Gator Catalogs")
    except Exception as e:
        handle_astroquery_exception(e, "IRSA list_gator_catalogs")
        raise typer.Exit(code=1)

@app.command(name="query-region", help="Perform a cone search across multiple IRSA collections.")
def query_region(
    coordinates: str = typer.Argument(..., help="Coordinates (e.g., '10.68h +41.26d', 'M31')."),
    radius: str = typer.Argument(..., help="Search radius (e.g., '10arcsec', '0.5deg')."),
    collection: Optional[str] = typer.Option(None, help="Specify a collection (e.g., ' ऑलवाइज', '2MASS'). Leave blank for a general search."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Performing IRSA cone search for region: '{coordinates}' with radius '{radius}'...[/cyan]")
    try:
        coord = parse_coordinates(coordinates)
        rad_quantity = parse_angle_str_to_quantity(radius)

        result_table: Optional[AstropyTable] = Irsa.query_region(
            coordinates=coord,
            radius=rad_quantity,
            collection=collection
        )
        if result_table and len(result_table) > 0:
            console.print(f"[green]Found {len(result_table)} match(es) in IRSA holdings.[/green]")
            display_table(result_table, title=f"IRSA Cone Search Results", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, f"IRSA cone search query")
        else:
            console.print(f"[yellow]No information found in IRSA for the specified region{f' in collection {collection}' if collection else ''}.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, "IRSA query_region")
        raise typer.Exit(code=1)
