import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.ned import Ned
from ..i18n import get_translator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    parse_coordinates,
    parse_angle_str_to_quantity,
)

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="ned",
        help=builtins._("Query the NASA/IPAC Extragalactic Database (NED)."),
        no_args_is_help=True
    )

    # ================== NED_FIELDS ==============================
    NED_FIELDS = [
        "Object Name",
        "Type",
        "RA(deg)",
        "DEC(deg)",
        "Redshift",
        "Photometry",
        "References",
        # ...
    ]
    # ============================================================

    Ned.TIMEOUT = 120

    @app.command(name="query-object", help=builtins._("Query NED for an object by name."))
    def query_object(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the extragalactic object.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(1, help=builtins._("Maximum number of objects to display (usually 1 for direct name).")),
        show_all_columns: bool = typer.Option(True, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying NED for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        try:
            result_table: Optional[AstropyTable] = Ned.query_object(object_name)

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found information for '{object_name}'.[/green]").format(object_name=object_name))
                display_table(result_table, title=_("NED Data for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("NED object query"))
            else:
                console.print(_("[yellow]No information found for object '{object_name}'.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(e, _("NED query_object"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="query-region", help=builtins._("Query NED for objects in a sky region."))
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M101').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '5arcmin', '0.1deg').")),
        equinox: str = typer.Option("J2000", help=builtins._("Equinox of coordinates (e.g., 'J2000', 'B1950').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying NED for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            coord = parse_coordinates(coordinates)
            rad_quantity = parse_angle_str_to_quantity(radius)

            result_table: Optional[AstropyTable] = Ned.query_region(
                coord,
                radius=rad_quantity,
                equinox=equinox
            )

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} object(s) in the region.[/green]").format(count=len(result_table)))
                display_table(result_table, title=_("NED Objects in Region"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("NED region query"))
            else:
                console.print(_("[yellow]No objects found in the specified region.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(e, _("NED query_region"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="get-images", help=builtins._("Get image metadata for an object from NED."))
    def get_images(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the extragalactic object.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(10, help=builtins._("Maximum number of image entries to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(True, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Fetching image list from NED for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        try:
            images_table: Optional[AstropyTable] = Ned.get_images(object_name)
            if images_table and len(images_table) > 0:
                console.print(_("[green]Found {count} image entries for '{object_name}'.[/green]").format(count=len(images_table), object_name=object_name))
                display_table(images_table, title=_("NED Image List for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(images_table, output_file, output_format, _("NED image list query"))
            else:
                console.print(_("[yellow]No image entries found for object '{object_name}'.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(e, _("NED get_images"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    return app
