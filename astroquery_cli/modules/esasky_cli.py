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
from ..i18n import get_translator

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="esasky",
        help=builtins._("Query the ESA Sky archive."),
        no_args_is_help=True
    )
    
    # ================== ESASKY_CATALOGS =========================
    ESASKY_CATALOGS = [
        "Gaia DR3",
        "Gaia DR2",
        "Hipparcos",
        "AllWISE",
        "2MASS",
        "Messier",
        "NGC",
        # ...
    ]
    # ============================================================
    # ================== ESASKY_FIELDS ===========================
    ESASKY_FIELDS = [
        "main_id",
        "source_id",
        "ra",
        "dec",
        # ...
    ]
    # ============================================================



    @app.command(name="query-object-catalogs", help=builtins._("Query ESASky catalogs for an object."))
    def query_object_catalogs(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the astronomical object.")),
        catalogs: Optional[List[str]] = typer.Option(None, "--catalog", help=builtins._("Specify catalogs to query (e.g., 'Gaia DR3'). Can be specified multiple times.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying ESASky catalogs for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        try:
            result_tables_dict: Optional[dict] = ESASky.query_object_catalogs(object_name, catalogs=catalogs if catalogs else None)

            if result_tables_dict:
                console.print(_("[green]Found data for '{object_name}' in {count} catalog(s).[/green]").format(object_name=object_name, count=len(result_tables_dict)))
                for cat_name, table_list in result_tables_dict.items():
                    if table_list:
                        table = table_list[0]
                        display_table(table, title=_("ESASky: {cat_name} for {object_name}").format(cat_name=cat_name, object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                        if output_file:
                            save_table_to_file(table, output_file.replace(".", f"_{cat_name}."), output_format, _("ESASky {cat_name} object query").format(cat_name=cat_name))
                    else:
                        console.print(_("[yellow]No results from catalog '{cat_name}' for '{object_name}'.[/yellow]").format(cat_name=cat_name, object_name=object_name))
            else:
                console.print(_("[yellow]No catalog information found for object '{object_name}'.[/yellow]").format(object_name=object_name))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("ESASky query_object_catalogs"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="query-region-catalogs", help=builtins._("Query ESASky catalogs in a sky region."))
    def query_region_catalogs(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M101').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '0.1deg', '5arcmin').")),
        catalogs: Optional[List[str]] = typer.Option(None, "--catalog", help=builtins._("Specify catalogs to query.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying ESASky catalogs for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            rad_quantity = parse_angle_str_to_quantity(radius)
            result_tables_dict: Optional[dict] = ESASky.query_region_catalogs(coordinates, radius=rad_quantity, catalogs=catalogs if catalogs else None)

            if result_tables_dict:
                console.print(_("[green]Found data in {count} catalog(s) for the region.[/green]").format(count=len(result_tables_dict)))
                for cat_name, table_list in result_tables_dict.items():
                    if table_list:
                        table = table_list[0]
                        display_table(table, title=_("ESASky: {cat_name} for region").format(cat_name=cat_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                        if output_file:
                            save_table_to_file(table, output_file.replace(".", f"_{cat_name}."), output_format, _("ESASky {cat_name} region query").format(cat_name=cat_name))
                    else:
                        console.print(_("[yellow]No results from catalog '{cat_name}' for the region.[/yellow]").format(cat_name=cat_name))
            else:
                console.print(_("[yellow]No catalog information found for the specified region.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(e, _("ESASky query_region_catalogs"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="list-catalogs", help=builtins._("List available missions/catalogs in ESASky."))
    def list_catalogs(ctx: typer.Context,
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Fetching list of available ESASky missions/catalogs...[/cyan]"))
        try:
            missions_table: Optional[AstropyTable] = ESASky.list_catalogs()
            if missions_table and len(missions_table) > 0:
                display_table(missions_table, title=_("Available ESASky Missions/Catalogs"), max_rows=-1)
            else:
                console.print(_("[yellow]Could not retrieve mission list or list is empty.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(e, _("ESASky list_catalogs"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()
        
    return app
