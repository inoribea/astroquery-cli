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
from ..i18n import get_translator

_ = get_translator()
app = typer.Typer(
    name="alma",
    help=_("Query the ALMA Science Archive."),
    no_args_is_help=True
)

Alma.ROW_LIMIT = 50
Alma.TIMEOUT = 60

@app.command(name="query-object", help=_("Query ALMA for observations of an object."))
def query_object(
    object_name: str = typer.Argument(..., help=_("Name of the astronomical object.")),
    public_data: bool = typer.Option(True, help=_("Query only public data.")),
    science_data: bool = typer.Option(True, help=_("Query only science data.")),
    payload: Optional[List[str]] = typer.Option(None, "--payload-field", help=_("Specify payload fields to query (e.g., 'band_list', 'target_name').")),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help=_("Maximum number of rows to display. Use -1 for all rows.")),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help=_("Show all columns in the output table."))
):
    console.print(_("[cyan]Querying ALMA for object: '{object_name}'...[/cyan]").format(object_name=object_name))
    alma = Alma()
    try:
        query_payload = {'source_name_alma': object_name}
        if payload:
            for item in payload:
                if '=' in item:
                    key, value = item.split('=', 1)
                    query_payload[key] = value
                else:
                    console.print(_("[yellow]Payload item '{item}' is not a key=value pair. Ignoring.[/yellow]").format(item=item))

        result_table: Optional[AstropyTable] = alma.query(
            payload=query_payload,
            public=public_data,
            science=science_data
        )

        if result_table and len(result_table) > 0:
            console.print(_("[green]Found {count} match(es) for '{object_name}'.[/green]").format(count=len(result_table), object_name=object_name))
            display_table(result_table, title=_("ALMA Data for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, _("ALMA object query"))
        else:
            console.print(_("[yellow]No information found for object '{object_name}'.[/yellow]").format(object_name=object_name))
    except Exception as e:
        handle_astroquery_exception(e, _("ALMA query_object"))
        raise typer.Exit(code=1)

@app.command(name="query-region", help=_("Query ALMA for observations in a sky region."))
def query_region(
    coordinates: str = typer.Argument(..., help=_("Coordinates (e.g., '10.68h +41.26d', '150.0 2.0').")),
    radius: str = typer.Argument(..., help=_("Search radius (e.g., '0.1deg', '5arcmin').")),
    public_data: bool = typer.Option(True, help=_("Query only public data.")),
    science_data: bool = typer.Option(True, help=_("Query only science data.")),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help=_("Maximum number of rows to display. Use -1 for all rows.")),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help=_("Show all columns in the output table."))
):
    console.print(_("[cyan]Querying ALMA for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
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
            console.print(_("[green]Found {count} match(es) in the region.[/green]").format(count=len(result_table)))
            display_table(result_table, title=_("ALMA Data for Region"), max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, _("ALMA region query"))
        else:
            console.print(_("[yellow]No information found for the specified region.[/yellow]"))
    except Exception as e:
        handle_astroquery_exception(e, _("ALMA query_region"))
        raise typer.Exit(code=1)
