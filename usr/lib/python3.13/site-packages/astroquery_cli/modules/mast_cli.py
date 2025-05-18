import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.mast import Observations
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
    name="mast",
    help="Query the Mikulski Archive for Space Telescopes (MAST)."
)

Observations.TIMEOUT = 120 # MAST can be slow
Observations.PAGESIZE = 2000 # Default is 500

@app.command(name="query-object", help="Query MAST for observations of an object.")
def query_object(
    object_name: str = typer.Argument(..., help="Name of the astronomical object."),
    radius: Optional[str] = typer.Option("0.2 deg", help="Search radius around the object."),
    obs_collection: Optional[List[str]] = typer.Option(None, "--collection", help="Observation collection (e.g., 'HST', 'TESS')."),
    instrument_name: Optional[List[str]] = typer.Option(None, "--instrument", help="Instrument name (e.g., 'WFC3', 'ACS')."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying MAST for object: '{object_name}'...[/cyan]")
    try:
        rad_quantity = parse_angle_str_to_quantity(radius) if radius else None
        result_table: Optional[AstropyTable] = Observations.query_object(
            object_name,
            radius=rad_quantity
        )

        # Further filtering if obs_collection or instrument_name are provided
        # This filtering is done client-side on the initial result_table
        if result_table and obs_collection:
            mask = [any(coll.upper() in str(item).upper() for coll in obs_collection) for item in result_table['obs_collection']]
            result_table = result_table[mask]
        if result_table and instrument_name:
            mask = [any(inst.upper() in str(item).upper() for inst in instrument_name) for item in result_table['instrument_name']]
            result_table = result_table[mask]


        if result_table and len(result_table) > 0:
            console.print(f"[green]Found {len(result_table)} observation(s) for '{object_name}'.[/green]")
            display_table(result_table, title=f"MAST Observations for {object_name}", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "MAST object query")
        else:
            console.print(f"[yellow]No observations found for object '{object_name}' with specified criteria.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "MAST query_object")
        raise typer.Exit(code=1)

@app.command(name="query-region", help="Query MAST for observations in a sky region.")
def query_region(
    coordinates: str = typer.Argument(..., help="Coordinates (e.g., '10.68h +41.26d', 'M101')."),
    radius: str = typer.Argument(..., help="Search radius (e.g., '0.1deg', '5arcmin')."),
    obs_collection: Optional[List[str]] = typer.Option(None, "--collection", help="Observation collection."),
    instrument_name: Optional[List[str]] = typer.Option(None, "--instrument", help="Instrument name."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying MAST for region: '{coordinates}' with radius '{radius}'...[/cyan]")
    try:
        coord = parse_coordinates(coordinates)
        rad_quantity = parse_angle_str_to_quantity(radius)

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
            console.print(f"[green]Found {len(result_table)} observation(s) in the region.[/green]")
            display_table(result_table, title=f"MAST Observations for Region", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "MAST region query")
        else:
            console.print(f"[yellow]No observations found for the specified region with given criteria.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "MAST query_region")
        raise typer.Exit(code=1)

@app.command(name="get-products", help="Get data product URLs for given observation IDs.")
def get_products(
    obs_ids: List[str] = typer.Argument(..., help="List of observation IDs."),
    product_type: Optional[List[str]] = typer.Option(None, "--type", help="Product type(s) (e.g., 'SCIENCE', 'PREVIEW')."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(50, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(True, "--show-all-cols", help="Show all columns in the output table.") # Usually want all for products
):
    console.print(f"[cyan]Fetching product list for obs ID(s): {', '.join(obs_ids)}...[/cyan]")
    try:
        products_table: Optional[AstropyTable] = Observations.get_product_urls(
            obs_ids,
            productType=product_type if product_type else None
        )
        if products_table and len(products_table) > 0:
            console.print(f"[green]Found {len(products_table)} data products.[/green]")
            display_table(products_table, title=f"MAST Data Products", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(products_table, output_file, output_format, "MAST products list")
            console.print(f"[info]Use 'aq mast download-products <obs_id> ...' or 'astroquery.mast.Observations.download_products()' to download.[/info]")
        else:
            console.print(f"[yellow]No data products found for the given observation ID(s) and criteria.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "MAST get_product_urls")
        raise typer.Exit(code=1)

