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
from .. import i18n

def get_app():
    import builtins
    app = typer.Typer(
        name="alma",
        help=builtins._("Query the ALMA archive."),
        no_args_is_help=True
    )

    Alma.ROW_LIMIT = 50
    Alma.TIMEOUT = 60

    ALMA_FIELDS = [
        'band_list', 'data_rights', 'frequency', 'instrument_name',
        # ...
    ]

    @app.command(name="query-object", help=builtins._("Query ALMA for observations of an object."))
    def query_object(
        ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the astronomical object.")),
        public_data: bool = typer.Option(True, help=builtins._("Query only public data.")),
        science_data: bool = typer.Option(True, help=builtins._("Query only science data.")),
        payload: Optional[List[str]] = typer.Option(None, "--payload-field", help=builtins._("Specify payload fields to query (e.g., 'band_list', 'target_name').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
        _ = i18n.get_translator(lang)
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
                display_table(ctx, result_table, title=_("ALMA Data for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("ALMA object query"))
            else:
                console.print(_("[yellow]No information found for object '{object_name}'.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ALMA query_object"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="query-region", help=builtins._("Query ALMA for observations in a sky region."))
    def query_region(
        ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', '150.0 2.0').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '0.1deg', '5arcmin').")),
        public_data: bool = typer.Option(True, help=builtins._("Query only public data.")),
        science_data: bool = typer.Option(True, help=builtins._("Query only science data.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
        _ = i18n.get_translator(lang)
        console.print(_("[cyan]Querying ALMA for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            coord = parse_coordinates(ctx, coordinates)
            rad = parse_angle_str_to_quantity(ctx, radius)
            alma = Alma()

            result_table: Optional[AstropyTable] = alma.query_region(
                coord,
                radius=rad,
                public=public_data,
                science=science_data
            )

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) in the region.[/green]").format(count=len(result_table)))
                display_table(ctx, result_table, title=_("ALMA Data for Region"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("ALMA region query"))
            else:
                console.print(_("[yellow]No information found for the specified region.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ALMA query_region"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    return app
