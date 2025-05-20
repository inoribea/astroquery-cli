import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.mast import Observations
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
        name="mast",
        help=builtins._("Query the Mikulski Archive for Space Telescopes (MAST)."),
        no_args_is_help=True
    )

    # ================== MAST_FIELDS =============================
    MAST_FIELDS = [
        "obsid",
        "provenance_name",
        "obs_collection",
        "instrument_name",
        "target_name",
        "t_min",
        "t_max",
        "s_ra",
        "s_dec",
        "em_min",
        "em_max",
        "telescope_name",
        "proposal_pi",
        "dataRights",
        "calib_level",
        "dataProductType",
        "obs_title",
        # ...
    ]
    # ============================================================

    Observations.TIMEOUT = 120
    Observations.PAGESIZE = 2000

    @app.command(name="query-object", help=builtins._("Query MAST for observations of an object."))
    def query_object(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the astronomical object.")),
        radius: Optional[str] = typer.Option("0.2 deg", help=builtins._("Search radius around the object.")),
        obs_collection: Optional[List[str]] = typer.Option(None, "--collection", help=builtins._("Observation collection (e.g., 'HST', 'TESS').")),
        instrument_name: Optional[List[str]] = typer.Option(None, "--instrument", help=builtins._("Instrument name (e.g., 'WFC3', 'ACS').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying MAST for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        try:
            rad_quantity = parse_angle_str_to_quantity(ctx, radius) if radius else None
            result_table: Optional[AstropyTable] = Observations.query_object(
                object_name,
                radius=rad_quantity
            )

            if result_table and obs_collection:
                mask = [any(coll.upper() in str(item).upper() for coll in obs_collection) for item in result_table['obs_collection']]
                result_table = result_table[mask]
            if result_table and instrument_name:
                mask = [any(inst.upper() in str(item).upper() for inst in instrument_name) for item in result_table['instrument_name']]
                result_table = result_table[mask]


            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} observation(s) for '{object_name}'.[/green]").format(count=len(result_table), object_name=object_name))
                display_table(ctx, result_table, title=_("MAST Observations for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("MAST object query"))
            else:
                console.print(_("[yellow]No observations found for object '{object_name}' with specified criteria.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(ctx, e, "MAST query_object")
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="query-region", help=builtins._("Query MAST for observations in a sky region."))
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M101').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '0.1deg', '5arcmin').")),
        obs_collection: Optional[List[str]] = typer.Option(None, "--collection", help=builtins._("Observation collection.")),
        instrument_name: Optional[List[str]] = typer.Option(None, "--instrument", help=builtins._("Instrument name.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying MAST for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
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
                console.print(_("[green]Found {count} observation(s) in the region.[/green]").format(count=len(result_table)))
                display_table(ctx, result_table, title=_("MAST Observations for Region"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("MAST region query"))
            else:
                console.print(_("[yellow]No observations found for the specified region with given criteria.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(e, _("MAST query_region"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="get-products", help=builtins._("Get data product URLs for given observation IDs."))
    def get_products(ctx: typer.Context,
        obs_ids: List[str] = typer.Argument(..., help=builtins._("List of observation IDs.")),
        product_type: Optional[List[str]] = typer.Option(None, "--type", help=builtins._("Product type(s) (e.g., 'SCIENCE', 'PREVIEW').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(50, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(True, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Fetching product list for obs ID(s): {obs_id_list}...[/cyan]").format(obs_id_list=', '.join(obs_ids)))
        try:
            products_table: Optional[AstropyTable] = Observations.get_product_urls(
                obs_ids,
                productType=product_type if product_type else None
            )
            if products_table and len(products_table) > 0:
                console.print(_("[green]Found {count} data products.[/green]").format(count=len(products_table)))
                display_table(ctx, products_table, title=_("MAST Data Products"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(products_table, output_file, output_format, _("MAST products list"))
                console.print(_("[info]Use 'aqc mast download-products <obs_id> ...' or 'astroquery.mast.Observations.download_products()' to download.[/info]"))
            else:
                console.print(_("[yellow]No data products found for the given observation ID(s) and criteria.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(e, _("MAST get_product_urls"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    return app
