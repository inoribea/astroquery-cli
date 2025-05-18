import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.alma import Alma
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
    name="alma",
    help="Query the ALMA Science Archive."
)

Alma.ROW_LIMIT = 50
Alma.TIMEOUT = 60
# Alma.archive_url = "https://almascience.eso.org" # Default, can be changed

@app.command(name="query-object", help="Query ALMA for observations of an object.")
def query_object(
    object_name: str = typer.Argument(..., help="Name of the astronomical object."),
    public_data: bool = typer.Option(True, help="Query only public data."),
    science_data: bool = typer.Option(True, help="Query only science data."),
    payload: Optional[List[str]] = typer.Option(None, "--payload-field", help="Specify payload fields to query (e.g., 'band_list', 'target_name')."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying ALMA for object: '{object_name}'...[/cyan]")
    alma = Alma()
    # Example: alma.login("username", store_password=True) if needed for proprietary data
    try:
        query_payload = {'source_name_alma': object_name}
        if payload:
            for item in payload:
                if '=' in item:
                    key, value = item.split('=', 1)
                    query_payload[key] = value
                else:
                    console.print(f"[yellow]Payload item '{item}' is not a key=value pair. Ignoring.[/yellow]")

        result_table: Optional[AstropyTable] = alma.query(
            payload=query_payload,
            public=public_data,
            science=science_data
        )

        if result_table and len(result_table) > 0:
            console.print(f"[green]Found {len(result_table)} match(es) for '{object_name}'.[/green]")
            display_table(result_table, title=f"ALMA Data for {object_name}", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "ALMA object query")
        else:
            console.print(f"[yellow]No information found for object '{object_name}'.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "ALMA query_object")
        raise typer.Exit(code=1)

@app.command(name="query-region", help="Query ALMA for observations in a sky region.")
def query_region(
    coordinates: str = typer.Argument(..., help="Coordinates (e.g., '10.68h +41.26d', '150.0 2.0')."),
    radius: str = typer.Argument(..., help="Search radius (e.g., '0.1deg', '5arcmin')."),
    public_data: bool = typer.Option(True, help="Query only public data."),
    science_data: bool = typer.Option(True, help="Query only science data."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying ALMA for region: '{coordinates}' with radius '{radius}'...[/cyan]")
    try:
        coord = parse_coordinates(coordinates)
        rad = parse_angle_str_to_quantity(radius)
        alma = Alma()

        result_table: Optional[AstropyTable] = alma.query_region(
            coord,
            radius=rad,
            public=public_data,
            science=science_data
        )

        if result_table and len(result_table) > 0:
            console.print(f"[green]Found {len(result_table)} match(es) in the region.[/green]")
            display_table(result_table, title=f"ALMA Data for Region", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "ALMA region query")
        else:
            console.print(f"[yellow]No information found for the specified region.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "ALMA query_region")
        raise typer.Exit(code=1)
