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
from ..i18n import get_translator

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="irsa",
        help=builtins._("Query NASA/IPAC Infrared Science Archive (IRSA)."),
        no_args_is_help=True
    )

    # ================== IRSA_FIELDS =============================
    IRSA_FIELDS = [
        "ra",
        "dec",
        "designation",
        "w1mpro",
        "w2mpro",
        "w3mpro",
        "w4mpro",
        "ph_qual",
        "cc_flags",
        "ext_flg",
        # ...
    ]
    # ============================================================


    Irsa.ROW_LIMIT = 500

    @app.command(name="query-gator", help=builtins._("Query a specific catalog in IRSA using Gator."))
    def query_gator(ctx: typer.Context,
        catalog: str = typer.Argument(..., help=builtins._("Name of the IRSA catalog (e.g., 'allwise_p3as_psd').")),
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M51').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '10arcsec', '0.5deg').")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve (comma separated or multiple use). Use 'all' for all columns.")),
        column_filters: Optional[List[str]] = typer.Option(None, "--filter", help=builtins._("Column filters (e.g., 'w1mpro>10', 'ph_qual=A'). Can be specified multiple times.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        import time
        test_mode = ctx.obj.get("test") if ctx.obj else False
        start = time.perf_counter() if test_mode else None

        console.print(_("[cyan]Querying IRSA catalog '{catalog}' via Gator for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(catalog=catalog, coordinates=coordinates, radius=radius))
        try:
            coord = parse_coordinates(coordinates)
            rad_quantity = parse_angle_str_to_quantity(radius)

            result_table: Optional[AstropyTable] = Irsa.query_gator(
                catalog=catalog,
                coordinates=coord,
                radius=rad_quantity
            )

            # Apply column selection
            if result_table and columns and columns != ["all"]:
                col_set = set(result_table.colnames)
                selected_cols = [col for col in columns if col in col_set]
                if selected_cols:
                    result_table = result_table[selected_cols]

            # Apply column filters
            if result_table and column_filters:
                for filt in column_filters:
                    # Example: 'w1mpro>10', 'ph_qual==A'
                    import re
                    m = re.match(r"^(\w+)\s*([<>=!]+)\s*([\w\.\-]+)$", filt)
                    if m:
                        col, op, val = m.groups()
                        if col in result_table.colnames:
                            expr = f"result_table['{col}'] {op} {repr(type(result_table[col][0])(val))}"
                            result_table = result_table[eval(expr)]
                    # else: ignore malformed filter

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) in '{catalog}'.[/green]").format(count=len(result_table), catalog=catalog))
                display_table(result_table, title=_("IRSA Gator: {catalog}").format(catalog=catalog), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("IRSA Gator {catalog} query").format(catalog=catalog))
            else:
                console.print(_("[yellow]No information found in '{catalog}' for the specified region.[/yellow]").format(catalog=catalog))
        except Exception as e:
            handle_astroquery_exception(e, _("IRSA Gator query for catalog {catalog}").format(catalog=catalog))
            raise typer.Exit(code=1)

        if test_mode:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="list-gator-catalogs", help=builtins._("List available catalogs in IRSA Gator for a mission."))
    def list_gator_catalogs(ctx: typer.Context,
        mission: Optional[str] = typer.Option(None, help=builtins._("Filter catalogs by mission code (e.g., 'WISE', 'SPITZER').")),
    ):
        console.print(_("[cyan]Fetching list of available IRSA Gator catalogs {mission_info}...[/cyan]").format(mission_info=_("for mission {mission}").format(mission=mission) if mission else ''))
        try:
            console.print(_("[yellow]Listing all Gator catalogs programmatically is complex via astroquery.irsa directly.[/yellow]"))
            console.print(_("[yellow]Please refer to the IRSA Gator website for a comprehensive list of catalogs.[/yellow]"))
            console.print(_("[yellow]Common catalog examples: 'allwise_p3as_psd', 'ptf_lightcurves', 'fp_psc' (2MASS).[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(e, _("IRSA list_gator_catalogs"))
            raise typer.Exit(code=1)

    @app.command(name="query-region", help=builtins._("Perform a cone search across multiple IRSA collections."))
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M31').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '10arcsec', '0.5deg').")),
        collection: Optional[str] = typer.Option(None, help=builtins._("Specify a collection (e.g., 'allwise', '2MASS'). Leave blank for a general search.")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve (comma separated or multiple use). Use 'all' for all columns.")),
        column_filters: Optional[List[str]] = typer.Option(None, "--filter", help=builtins._("Column filters (e.g., 'w1mpro>10', 'ph_qual=A'). Can be specified multiple times.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        console.print(_("[cyan]Performing IRSA cone search for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            coord = parse_coordinates(coordinates)
            rad_quantity = parse_angle_str_to_quantity(radius)

            result_table: Optional[AstropyTable] = Irsa.query_region(
                coordinates=coord,
                radius=rad_quantity,
                collection=collection
            )

            # Apply column selection
            if result_table and columns and columns != ["all"]:
                col_set = set(result_table.colnames)
                selected_cols = [col for col in columns if col in col_set]
                if selected_cols:
                    result_table = result_table[selected_cols]

            # Apply column filters
            if result_table and column_filters:
                for filt in column_filters:
                    import re
                    m = re.match(r"^(\w+)\s*([<>=!]+)\s*([\w\.\-]+)$", filt)
                    if m:
                        col, op, val = m.groups()
                        if col in result_table.colnames:
                            expr = f"result_table['{col}'] {op} {repr(type(result_table[col][0])(val))}"
                            result_table = result_table[eval(expr)]

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) in IRSA holdings.[/green]").format(count=len(result_table)))
                display_table(result_table, title=_("IRSA Cone Search Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("IRSA cone search query"))
            else:
                console.print(_("[yellow]No information found in IRSA for the specified region{collection_info}.[/yellow]").format(collection_info=_(" in collection {collection}").format(collection=collection) if collection else ''))

        except Exception as e:
            handle_astroquery_exception(e, _("IRSA query_region"))
            raise typer.Exit(code=1)

    return app
