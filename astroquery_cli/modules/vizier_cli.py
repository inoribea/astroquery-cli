from typing import Optional, List, Tuple

import typer
from astroquery.vizier import Vizier, conf as vizier_conf
from astropy.coordinates import SkyCoord
import astropy.units as u

from ..i18n import get_translator
from ..utils import console, display_table, handle_astroquery_exception

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="vizier",
        help=builtins._("Query the VizieR astronomical catalog service."),
        no_args_is_help=True
    )

    # ================== VIZIER_FIELDS ===========================
    VIZIER_FIELDS = [
        "HIP",
        "RAh",
        "RAm",
        "RAs",
        "DE-",
        "DEd",
        "DEm",
        "DEs",
        "Vmag",
        "Plx",
        "pmRA",
        "pmDE",
        # ...
    ]
    # ============================================================


    def parse_angle_str_to_quantity(ctx: typer.Context,angle_str: Optional[str]) -> Optional[u.Quantity]:
        if angle_str is None:
            return None
        try:
            return u.Quantity(angle_str)
        except Exception as e:
            console.print(_("[bold red]Error parsing angle string '{angle_str}': {error_message}[/bold red]").format(angle_str=angle_str, error_message=e))
            console.print(_("[yellow]Hint: Use format like '5arcmin', '0.5deg', '10arcsec'.[/yellow]"))
            raise typer.Exit(code=1)

    def parse_coordinates(ctx: typer.Context,coords_str: str) -> SkyCoord:
        try:
            if ',' in coords_str and ('h' in coords_str or 'd' in coords_str or ':' in coords_str):
                return SkyCoord(coords_str, frame='icrs', unit=(u.hourangle, u.deg))
            elif len(coords_str.split()) == 2:
                try:
                    ra, dec = map(float, coords_str.split())
                    return SkyCoord(ra, dec, frame='icrs', unit='deg')
                except ValueError:
                    pass
            return SkyCoord.from_name(coords_str)
        except Exception:
            try:
                return SkyCoord(coords_str, frame='icrs', unit=(u.deg, u.deg))
            except Exception as e:
                console.print(_("[bold red]Error parsing coordinates '{coords_str}': {error_message}[/bold red]").format(coords_str=coords_str, error_message=e))
                console.print(_("[yellow]Hint: Try 'M31', '10.68h +41.26d', or '160.32 41.45'.[/yellow]"))
                raise typer.Exit(code=1)


    def parse_constraints_list(ctx: typer.Context,constraints_list: Optional[List[str]]) -> Optional[dict]:
        if not constraints_list:
            return None
        parsed_constraints = {}
        for item in constraints_list:
            if '=' not in item:
                console.print(_("[bold red]Invalid constraint format: '{item}'. Expected 'column=condition'.[/bold red]").format(item=item))
                raise typer.Exit(code=1)
            key, value = item.split('=', 1)
            parsed_constraints[key.strip()] = value.strip()
        return parsed_constraints

    VIZIER_SERVERS = {
        "vizier_cds": "https://vizier.cds.unistra.fr/viz-bin/",
        "vizier_eso": "https://vizier.eso.org/viz-bin/",
        "vizier_nao": "https://vizier.nao.ac.jp/viz-bin/",
        "vizier_adac": "https://vizier.china-vo.org/viz-bin/",
    }

    @app.command(name="find-catalogs", help=builtins._("Find VizieR catalogs based on keywords, UCDs, or source names."))
    def find_catalogs(ctx: typer.Context,
        keywords: Optional[List[str]] = typer.Option(None, "--keyword", "-k", help=builtins._("Keyword(s) to search for in catalog descriptions.")),
        ucd: Optional[str] = typer.Option(None, help=builtins._("UCD (Unified Content Descriptor) to filter catalogs.")),
        source_name: Optional[str] = typer.Option(None, "--source", help=builtins._("Source name or pattern (e.g., 'Gaia DR3', '2MASS').")),
        max_catalogs: int = typer.Option(20, help=builtins._("Maximum number of catalogs to list.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        vizier_server: str = typer.Option(
            "vizier_cds",
            help=builtins._("VizieR server to use. Choices: {server_list}").format(server_list=list(VIZIER_SERVERS.keys())),
            autocompletion=lambda: list(VIZIER_SERVERS.keys())
        ),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Searching for VizieR catalogs...[/cyan]"))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        console.print(_("[dim]Using VizieR server: {server_url}[/dim]").format(server_url=vizier_conf.server))

        query_params = {}
        if keywords:
            query_params['keywords'] = keywords
            console.print(_("[dim]Keywords: {keywords_list}[/dim]").format(keywords_list=keywords))
        if ucd:
            query_params['ucd'] = ucd
            console.print(_("[dim]UCD: {ucd_val}[/dim]").format(ucd_val=ucd))
        if source_name:
            query_params['source_name'] = source_name
            console.print(_("[dim]Source Name: {source_val}[/dim]").format(source_val=source_name))

        if not query_params:
            console.print(_("[yellow]Please provide at least one search criterion (keyword, ucd, or source name).[/yellow]"))
            console.print(_("Example: `aqc vizier find-catalogs --keyword photometry --keyword M31`"))
            raise typer.Exit(code=1)

        try:
            result_tables = Vizier.find_catalogs(**query_params)
            if result_tables:
                display_table(
                    result_tables[0],
                    title=_("Found VizieR Catalogs"),
                    max_rows=max_catalogs,
                    show_all_columns=show_all_columns
                )
            else:
                console.print(_("[yellow]No catalogs found matching your criteria.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(e, _("VizieR find_catalogs"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()


    @app.command(name="query-object", help=builtins._("Query catalogs around an object name or specific coordinates."))
    def query_object(ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Object name (e.g., 'M31') or coordinates (e.g., '10.68h +41.26d' or '160.32 41.45').")),
        radius: str = typer.Option("2arcmin", help=builtins._("Search radius (e.g., '5arcmin', '0.1deg').")),
        catalogs: List[str] = typer.Option(..., "--catalog", "-c", help=builtins._("VizieR catalog identifier(s) (e.g., 'I/261/gaiadr3', 'J/ApJ/710/1776'). Can be specified multiple times.")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve (e.g., 'RAJ2000', 'DEJ2000', 'pmRA'). Use 'all' for all columns. Can be specified multiple times.")),
        column_filters: Optional[List[str]] = typer.Option(None, "--filter", help=builtins._("Column filters (e.g., 'Imag<15', 'B-V>0.5'). Can be specified multiple times. Format: 'column_name<operator>value'.")),
        row_limit: int = typer.Option(vizier_conf.row_limit, help=builtins._("Maximum number of rows to return per catalog.")),
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display per table. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        vizier_server: str = typer.Option(
            "vizier_cds",
            help=builtins._("VizieR server to use. Choices: {server_list}").format(server_list=list(VIZIER_SERVERS.keys())),
            autocompletion=lambda: list(VIZIER_SERVERS.keys())
        )
    ):
        console.print(_("[cyan]Querying VizieR for object '{target_name}' in catalog(s): {catalog_list}...[/cyan]").format(target_name=target, catalog_list=', '.join(catalogs)))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        vizier_conf.row_limit = row_limit
        console.print(_("[dim]Using VizieR server: {server_url}, Row limit: {limit}[/dim]").format(server_url=vizier_conf.server, limit=row_limit))

        coords = parse_coordinates(target)
        rad_quantity = parse_angle_str_to_quantity(radius)

        viz = Vizier(columns=columns if columns else ["*"], catalog=catalogs, column_filters=column_filters, row_limit=row_limit)

        try:
            result_tables = viz.query_object(
                object_name_or_coordinates=coords,
                radius=rad_quantity,
            )

            if not result_tables:
                console.print(_("[yellow]No results returned from VizieR for this query.[/yellow]"))
                return

            for table_name, table_data in result_tables.items():
                if table_data is not None and len(table_data) > 0:
                    display_table(
                        table_data,
                        title=_("Results from {catalog_name} for {target_name}").format(catalog_name=table_name, target_name=target),
                        max_rows=max_rows_display,
                        show_all_columns=show_all_columns
                    )
                else:
                    console.print(_("[yellow]No data found in catalog '{catalog_name}' for the given criteria.[/yellow]").format(catalog_name=table_name))

        except Exception as e:
            handle_astroquery_exception(e, _("VizieR query_object for {target_name}").format(target_name=target))
            raise typer.Exit(code=1)


    @app.command(name="query-region", help=builtins._("Query catalogs within a sky region (cone or box)."))
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Central coordinates for the region (e.g., '10.68h +41.26d' or '160.32 41.45').")),
        radius: Optional[str] = typer.Option(None, help=builtins._("Cone search radius (e.g., '5arcmin', '0.1deg'). Use if not specifying width/height.")),
        width: Optional[str] = typer.Option(None, help=builtins._("Width of a box region (e.g., '10arcmin', '0.5deg'). Requires --height.")),
        height: Optional[str] = typer.Option(None, help=builtins._("Height of a box region (e.g., '10arcmin', '0.5deg'). Requires --width.")),
        catalogs: List[str] = typer.Option(..., "--catalog", "-c", help=builtins._("VizieR catalog identifier(s). Can be specified multiple times.")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve. Use 'all' for all columns. Can be specified multiple times.")),
        column_filters: Optional[List[str]] = typer.Option(None, "--filter", help=builtins._("Column filters (e.g., 'Imag<15'). Can be specified multiple times.")),
        row_limit: int = typer.Option(vizier_conf.row_limit, help=builtins._("Maximum number of rows to return per catalog.")),
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display per table. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        vizier_server: str = typer.Option(
            "vizier_cds",
            help=builtins._("VizieR server to use. Choices: {server_list}").format(server_list=list(VIZIER_SERVERS.keys())),
            autocompletion=lambda: list(VIZIER_SERVERS.keys())
        )
    ):
        console.print(_("[cyan]Querying VizieR region around '{coords_str}' in catalog(s): {catalog_list}...[/cyan]").format(coords_str=coordinates, catalog_list=', '.join(catalogs)))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        vizier_conf.row_limit = row_limit
        console.print(_("[dim]Using VizieR server: {server_url}, Row limit: {limit}[/dim]").format(server_url=vizier_conf.server, limit=row_limit))

        coords_obj = parse_coordinates(coordinates)
        rad_quantity = parse_angle_str_to_quantity(radius)
        width_quantity = parse_angle_str_to_quantity(width)
        height_quantity = parse_angle_str_to_quantity(height)

        if rad_quantity and (width_quantity or height_quantity):
            console.print(_("[bold red]Error: Specify either --radius (for cone search) OR (--width and --height) (for box search), not both.[/bold red]"))
            raise typer.Exit(code=1)
        if (width_quantity and not height_quantity) or (not width_quantity and height_quantity):
            console.print(_("[bold red]Error: For a box search, both --width and --height must be specified.[/bold red]"))
            raise typer.Exit(code=1)
        if not rad_quantity and not (width_quantity and height_quantity):
            console.print(_("[bold red]Error: You must specify search dimensions: either --radius OR (--width and --height).[/bold red]"))
            raise typer.Exit(code=1)

        viz = Vizier(columns=columns if columns else ["*"], catalog=catalogs, column_filters=column_filters, row_limit=row_limit)

        try:
            result_tables = viz.query_region(
                coordinates=coords_obj,
                radius=rad_quantity,
                width=width_quantity,
                height=height_quantity,
            )

            if not result_tables:
                console.print(_("[yellow]No results returned from VizieR for this query.[/yellow]"))
                return

            for table_name, table_data in result_tables.items():
                if table_data is not None and len(table_data) > 0:
                    display_table(
                        table_data,
                        title=_("Results from {catalog_name} for region around {coords_str}").format(catalog_name=table_name, coords_str=coordinates),
                        max_rows=max_rows_display,
                        show_all_columns=show_all_columns
                    )
                else:
                    console.print(_("[yellow]No data found in catalog '{catalog_name}' for the given criteria.[/yellow]").format(catalog_name=table_name))

        except Exception as e:
            handle_astroquery_exception(e, _("VizieR query_region for {coords_str}").format(coords_str=coordinates))
            raise typer.Exit(code=1)


    @app.command(name="query-constraints", help=builtins._("Query catalogs based on specific column constraints or keywords."))
    def query_constraints(ctx: typer.Context,
        catalogs: List[str] = typer.Option(..., "--catalog", "-c", help=builtins._("VizieR catalog identifier(s). Can be specified multiple times.")),
        constraints: Optional[List[str]] = typer.Option(None, "--constraint", help=builtins._("Constraints on column values (e.g., 'Vmag=<10', 'B-V=0.5..1.0'). Can be specified multiple times. Format: 'column_name=condition'.")),
        keywords: Optional[List[str]] = typer.Option(None, "--keyword", "-k", help=builtins._("Keywords to filter results within the catalog (different from finding catalogs).")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve. Use 'all' for all columns. Can be specified multiple times.")),
        row_limit: int = typer.Option(vizier_conf.row_limit, help=builtins._("Maximum number of rows to return per catalog.")),
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display per table. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        vizier_server: str = typer.Option(
            "vizier_cds",
            help=builtins._("VizieR server to use. Choices: {server_list}").format(server_list=list(VIZIER_SERVERS.keys())),
            autocompletion=lambda: list(VIZIER_SERVERS.keys())
        )
    ):
        console.print(_("[cyan]Querying VizieR with constraints in catalog(s): {catalog_list}...[/cyan]").format(catalog_list=', '.join(catalogs)))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        vizier_conf.row_limit = row_limit
        console.print(_("[dim]Using VizieR server: {server_url}, Row limit: {limit}[/dim]").format(server_url=vizier_conf.server, limit=row_limit))

        parsed_constraints = parse_constraints_list(constraints)
        if not parsed_constraints and not keywords:
            console.print(_("[yellow]Please provide at least --constraint(s) or --keyword(s) for this query type.[/yellow]"))
            raise typer.Exit(code=1)

        query_kwargs = {}
        if parsed_constraints:
            query_kwargs.update(parsed_constraints)
            console.print(_("[dim]Using constraints: {constraints_dict}[/dim]").format(constraints_dict=query_kwargs))
        if keywords:
            query_kwargs['keywords'] = " ".join(keywords)
            console.print(_("[dim]Using keywords: {keywords_str}[/dim]").format(keywords_str=query_kwargs['keywords']))


        viz = Vizier(columns=columns if columns else ["*"], row_limit=row_limit)
        viz.catalog = catalogs

        try:
            result_tables = viz.query_constraints(**query_kwargs)

            if not result_tables:
                console.print(_("[yellow]No results returned from VizieR for this query.[/yellow]"))
                return

            for table_name, table_data in result_tables.items():
                if table_data is not None and len(table_data) > 0:
                    display_table(
                        table_data,
                        title=_("Constraint Query Results from {catalog_name}").format(catalog_name=table_name),
                        max_rows=max_rows_display,
                        show_all_columns=show_all_columns
                    )
                else:
                    console.print(_("[yellow]No data found in catalog '{catalog_name}' for the given criteria.[/yellow]").format(catalog_name=table_name))

        except Exception as e:
            handle_astroquery_exception(e, _("VizieR query_constraints"))
            raise typer.Exit(code=1)

    return app
