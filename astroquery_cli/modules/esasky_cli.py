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
)

app = typer.Typer(
    name="esasky",
    help="Query and explore data with ESASky."
)

@app.command(name="query-object-catalogs", help="Query ESASky catalogs for an object.")
def query_object_catalogs(
    object_name: str = typer.Argument(..., help="Name of the astronomical object."),
    catalogs: Optional[List[str]] = typer.Option(None, "--catalog", help="Specify catalogs to query (e.g., 'Gaia DR3'). Can be specified multiple times."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying ESASky catalogs for object: '{object_name}'...[/cyan]")
    try:
        result_tables_dict: Optional[dict] = ESASky.query_object_catalogs(object_name, catalogs=catalogs if catalogs else None)

        if result_tables_dict:
            console.print(f"[green]Found data for '{object_name}' in {len(result_tables_dict)} catalog(s).[/green]")
            for cat_name, table_list in result_tables_dict.items():
                if table_list: # table_list is a list containing one table
                    table = table_list[0]
                    display_table(table, title=f"ESASky: {cat_name} for {object_name}", max_rows=max_rows_display, show_all_columns=show_all_columns)
                    if output_file:
                        # Modify filename for multiple tables if needed or save first one
                        save_table_to_file(table, output_file.replace(".", f"_{cat_name}."), output_format, f"ESASky {cat_name} object query")
                else:
                    console.print(f"[yellow]No results from catalog '{cat_name}' for '{object_name}'.[/yellow]")
        else:
            console.print(f"[yellow]No catalog information found for object '{object_name}'.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, "ESASky query_object_catalogs")
        raise typer.Exit(code=1)

@app.command(name="query-region-catalogs", help="Query ESASky catalogs in a sky region.")
def query_region_catalogs(
    coordinates: str = typer.Argument(..., help="Coordinates (e.g., '10.68h +41.26d', 'M101')."),
    radius: str = typer.Argument(..., help="Search radius (e.g., '0.1deg', '5arcmin')."),
    catalogs: Optional[List[str]] = typer.Option(None, "--catalog", help="Specify catalogs to query."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying ESASky catalogs for region: '{coordinates}' with radius '{radius}'...[/cyan]")
    try:
        rad_quantity = parse_angle_str_to_quantity(radius)
        result_tables_dict: Optional[dict] = ESASky.query_region_catalogs(coordinates, radius=rad_quantity, catalogs=catalogs if catalogs else None)

        if result_tables_dict:
            console.print(f"[green]Found data in {len(result_tables_dict)} catalog(s) for the region.[/green]")
            for cat_name, table_list in result_tables_dict.items():
                if table_list:
                    table = table_list[0]
                    display_table(table, title=f"ESASky: {cat_name} for region", max_rows=max_rows_display, show_all_columns=show_all_columns)
                    if output_file:
                        save_table_to_file(table, output_file.replace(".", f"_{cat_name}."), output_format, f"ESASky {cat_name} region query")
                else:
                    console.print(f"[yellow]No results from catalog '{cat_name}' for the region.[/yellow]")
        else:
            console.print(f"[yellow]No catalog information found for the specified region.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "ESASky query_region_catalogs")
        raise typer.Exit(code=1)

@app.command(name="list-missions", help="List available missions/catalogs in ESASky.")
def list_missions():
    console.print("[cyan]Fetching list of available ESASky missions/catalogs...[/cyan]")
    try:
        missions_table: Optional[AstropyTable] = ESASky.list_missions()
        if missions_table and len(missions_table) > 0:
            display_table(missions_table, title="Available ESASky Missions/Catalogs", max_rows=-1)
        else:
            console.print("[yellow]Could not retrieve mission list or list is empty.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "ESASky list_missions")
        raise typer.Exit(code=1)
