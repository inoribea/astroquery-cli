import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.ned import Ned
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
    name="ned",
    help="Query NASA/IPAC Extragalactic Database (NED)."
)

Ned.TIMEOUT = 120 # NED can be slow

@app.command(name="query-object", help="Query NED for an object by name.")
def query_object(
    object_name: str = typer.Argument(..., help="Name of the extragalactic object."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(1, help="Maximum number of objects to display (usually 1 for direct name)."), # NED object queries usually return 1 primary match
    show_all_columns: bool = typer.Option(True, "--show-all-cols", help="Show all columns in the output table.") # Usually want all for NED object
):
    console.print(f"[cyan]Querying NED for object: '{object_name}'...[/cyan]")
    try:
        result_table: Optional[AstropyTable] = Ned.query_object(object_name)

        if result_table and len(result_table) > 0:
            console.print(f"[green]Found information for '{object_name}'.[/green]")
            display_table(result_table, title=f"NED Data for {object_name}", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "NED object query")
        else:
            console.print(f"[yellow]No information found for object '{object_name}'.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "NED query_object")
        raise typer.Exit(code=1)

@app.command(name="query-region", help="Query NED for objects in a sky region.")
def query_region(
    coordinates: str = typer.Argument(..., help="Coordinates (e.g., '10.68h +41.26d', 'M101')."),
    radius: str = typer.Argument(..., help="Search radius (e.g., '5arcmin', '0.1deg')."),
    equinox: str = typer.Option("J2000", help="Equinox of coordinates (e.g., 'J2000', 'B1950')."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying NED for region: '{coordinates}' with radius '{radius}'...[/cyan]")
    try:
        coord = parse_coordinates(coordinates) # Assumes ICRS/J2000 if not specified in string
        rad_quantity = parse_angle_str_to_quantity(radius)

        result_table: Optional[AstropyTable] = Ned.query_region(
            coord,
            radius=rad_quantity,
            equinox=equinox
        )

        if result_table and len(result_table) > 0:
            console.print(f"[green]Found {len(result_table)} object(s) in the region.[/green]")
            display_table(result_table, title=f"NED Objects in Region", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "NED region query")
        else:
            console.print(f"[yellow]No objects found in the specified region.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "NED query_region")
        raise typer.Exit(code=1)

@app.command(name="get-images", help="Get image metadata for an object from NED.")
def get_images(
    object_name: str = typer.Argument(..., help="Name of the extragalactic object."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(10, help="Maximum number of image entries to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(True, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Fetching image list from NED for object: '{object_name}'...[/cyan]")
    try:
        images_table: Optional[AstropyTable] = Ned.get_images(object_name)
        if images_table and len(images_table) > 0:
            console.print(f"[green]Found {len(images_table)} image entries for '{object_name}'.[/green]")
            display_table(images_table, title=f"NED Image List for {object_name}", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(images_table, output_file, output_format, "NED image list query")
        else:
            console.print(f"[yellow]No image entries found for object '{object_name}'.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "NED get_images")
        raise typer.Exit(code=1)
