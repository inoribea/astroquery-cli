import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.irsa import Irsa
from astroquery.ipac.irsa import Irsa as IrsaGator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    parse_coordinates,
    parse_angle_str_to_quantity,
    global_keyboard_interrupt_handler
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

    gator_app = typer.Typer(help=builtins._(
        "IRSA Gator catalog operations.\n\n"
        "Example: python -m astroquery_cli.main irsa gator query \"83.822083 -5.391111\" \"30arcsec\" --catalog fp_psc\n"
        "Use 'python -m astroquery_cli.main irsa gator list' to list all available catalogs."
    ))

    @gator_app.command("query")
    @global_keyboard_interrupt_handler
    def query_gator(ctx: typer.Context,
        target_input: str = typer.Argument(
            ...,
            help=builtins._(
                "Coordinates (e.g., '00 42 44.3 +41 16 09') or catalog name (e.g., 'fp_psc')."
            )
        ),
        radius: Optional[str] = typer.Argument(None, help=builtins._("Search radius (e.g., '10arcsec', '0.5deg'). Required if coordinates provided.")),
        catalog: Optional[str] = typer.Option(None, "--catalog", "-C", help=builtins._("Explicitly specify the IRSA catalog name (e.g., 'allwise_p3as_psd'). Defaults to 'gaia_dr3_source'.")),
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

        try:
            final_catalog = catalog
            final_coordinates = None
            final_radius = radius

            coord_obj = parse_coordinates(ctx, target_input)

            if coord_obj: 
                final_coordinates = target_input
                if not final_catalog:
                    final_catalog = "gaia_dr3_source"
                    console.print(_("[yellow]No catalog specified with coordinates. Defaulting to 'gaia_dr3_source' catalog.[/yellow]"))
                if not final_radius:
                    console.print(_("[red]Error: Radius is required when coordinates are provided.[/red]"))
                    raise typer.Exit(code=1)
                console.print(_("[cyan]Querying IRSA catalog '{catalog}' via Gator for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(catalog=final_catalog, coordinates=final_coordinates, radius=final_radius))
                rad_quantity = parse_angle_str_to_quantity(ctx, final_radius)
                result_table: Optional[AstropyTable] = Irsa.query_region(
                    coordinates=coord_obj,
                    radius=rad_quantity,
                    catalog=final_catalog,
                    columns=",".join(columns) if columns else '*',
                )
            else:  
                if final_catalog and final_catalog != target_input:
                    console.print(_("[red]Error: Catalog name provided as both positional argument and --catalog option. Please use only one.[/red]"))
                    raise typer.Exit(code=1)
                final_catalog = target_input
                if final_radius:
                    console.print(_("[red]Error: Catalog name '{target_input}' provided as first argument, but a radius '{radius}' was also provided. Catalog queries do not use radius. Please use 'irsa gator <catalog_name>' without a radius, or provide coordinates and a radius.[/red]").format(target_input=target_input, radius=radius))
                    raise typer.Exit(code=1)
                console.print(_("[cyan]Browsing IRSA catalog '{catalog}' (first {limit} rows)...[/cyan]").format(catalog=final_catalog, limit=Irsa.ROW_LIMIT))
                from astropy.coordinates import SkyCoord
                import astropy.units as u
                coord = SkyCoord("17h45m40.04s", "-29d00m28.1s", frame='icrs')
                rad_quantity = 180 * u.deg
                result_table: Optional[AstropyTable] = Irsa.query_region(
                    coordinates=coord,
                    radius=rad_quantity,
                    catalog=final_catalog
                )

            if result_table and columns and columns != ["all"]:
                col_set = set(result_table.colnames)
                selected_cols = [col for col in columns if col in col_set]
                if selected_cols:
                    result_table = result_table[selected_cols]

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
                console.print(_("[green]Found {count} match(es) in '{catalog}'.[/green]").format(count=len(result_table), catalog=final_catalog))
                display_table(ctx, result_table, title=_("IRSA Gator: {catalog}").format(catalog=final_catalog), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("IRSA Gator {catalog} query").format(catalog=final_catalog))
            else:
                console.print(_("[yellow]No information found in '{catalog}' for the specified region.[/yellow]").format(catalog=final_catalog))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA Gator query for catalog {catalog}").format(catalog=final_catalog if final_catalog else "unknown"))
            raise typer.Exit(code=1)

        if test_mode:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()
    @gator_app.command("list")
    def list_gator_catalogs():
        """
        List all available IRSA Gator catalogs.
        """
        try:
            from astroquery.irsa import Irsa
            catalogs = list(Irsa.list_catalogs())
            from rich.table import Table
            from rich.console import Console
            cols = 5
            rows = (len(catalogs) + cols - 1) // cols
            data = [catalogs[i * rows:(i + 1) * rows] for i in range(cols)]
            data = [col + [""] * (rows - len(col)) for col in data]
            table = Table(title="Available IRSA Gator catalogs")
            for i in range(cols):
                table.add_column(f"Col{i+1}")
            for row in zip(*data):
                table.add_row(*row)
            Console().print(table)
        except Exception as e:
            console.print(f"[red]Failed to fetch catalog list: {e}[/red]")

    @app.command(name="region", help=builtins._("Perform a cone search across multiple IRSA collections."))
    @global_keyboard_interrupt_handler
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
            coord = parse_coordinates(ctx, coordinates)
            rad_quantity = parse_angle_str_to_quantity(ctx, radius)

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
                display_table(ctx, result_table, title=_("IRSA Cone Search Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_format, _("IRSA cone search query"))
            else:
                console.print(_("[yellow]No information found in IRSA for the specified region{collection_info}.[/yellow]").format(collection_info=_(" in collection {collection}").format(collection=collection) if collection else ''))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA query_region"))
            raise typer.Exit(code=1)

    app.add_typer(gator_app, name="gator")
    return app
