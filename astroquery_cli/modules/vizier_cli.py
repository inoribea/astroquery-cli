from typing import Optional, List, Tuple

import typer
from astroquery.vizier import Vizier, conf as vizier_conf
from astropy.coordinates import SkyCoord
import astropy.units as u

from ..i18n import get_translator
from ..utils import console, display_table, handle_astroquery_exception, global_keyboard_interrupt_handler
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout
from astroquery_cli.common_options import setup_debug_context # Import setup_debug_context
from astroquery_cli.debug import debug # Import debug function

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="vizier",
        help=builtins._("Query the VizieR astronomical catalog service."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def vizier_callback(
        ctx: typer.Context,
        debug: bool = typer.Option(
            False,
            "-t",
            "--debug",
            help=_("Enable debug mode with verbose output."),
            envvar="AQC_DEBUG"
        ),
        verbose: bool = typer.Option(
            False,
            "-v",
            "--verbose",
            help=_("Enable verbose output.")
        )
    ):
        setup_debug_context(ctx, debug, verbose)

        # Custom help display logic
        if ctx.invoked_subcommand is None and \
           not any(arg in ["-h", "--help"] for arg in ctx.args): # Use ctx.args for subcommand arguments
            # Capture the full help output by explicitly calling the app with --help
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    # Call the app with --help to get the full help output
                    # Pass the current command's arguments to simulate the help call
                    app(ctx.args + ["--help"])
                except SystemExit:
                    pass # Typer exits after showing help, catch the SystemExit exception
            full_help_text = help_output_capture.getvalue()

            # Extract only the "Commands" section using regex, including the full bottom border
            commands_match = re.search(r'╭─ Commands ─.*?(\n(?:│.*?\n)*)╰─.*─╯', full_help_text, re.DOTALL)
            if commands_match:
                commands_section = commands_match.group(0)
                # Remove the "Usage:" line if present in the full help text
                filtered_commands_section = "\n".join([
                    line for line in commands_section.splitlines() if "Usage:" not in line
                ])
                console.print(filtered_commands_section)
            else:
                # Fallback: if commands section not found, print full help
                console.print(full_help_text)
            raise typer.Exit()

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


    def parse_angle_str_to_quantity(ctx: typer.Context, angle_str: Optional[str]) -> Optional[u.Quantity]:
        if angle_str is None:
            return None
        try:
            return u.Quantity(angle_str)
        except Exception as e:
            console.print(_("[bold red]Error parsing angle string '{angle_str}': {error_message}[/bold red]").format(angle_str=angle_str, error_message=e))
            console.print(_("[yellow]Hint: Use format like '5arcmin', '0.5deg', '10arcsec'.[/yellow]"))
            raise typer.Exit(code=1)

    def parse_coordinates(ctx: typer.Context, coords_str: str) -> SkyCoord:
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


    def parse_constraints_list(ctx: typer.Context, constraints_list: Optional[List[str]]) -> dict:
        parsed_constraints = {}
        if constraints_list:
            for item in constraints_list:
                if '=' not in item:
                    console.print(_("[bold red]Invalid constraint format: '{item}'. Expected 'column=condition'.[/bold red]").format(item=item))
                    raise typer.Exit(code=1)
                key, value = item.split('=', 1)
                parsed_constraints[key.strip()] = value.strip()
        return parsed_constraints

    VIZIER_SERVERS = {
        "vizier_cds": "vizier.cds.unistra.fr",
        "vizier_eso": "vizier.eso.org",
        "vizier_nao": "vizier.nao.ac.jp",
        "vizier_adac": "vizier.china-vo.org",
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
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Searching for VizieR catalogs...[/cyan]"))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        debug(_("Using VizieR server: {server_url}").format(server_url=vizier_conf.server))

        query_params = {}
        if keywords:
            query_params['keywords'] = keywords
            debug(_("Keywords: {keywords_list}").format(keywords_list=keywords))
        if ucd is not None: # Only add if not None
            query_params['ucd'] = ucd
            debug(_("UCD: {ucd_val}").format(ucd_val=ucd))
        if source_name is not None: # Only add if not None
            query_params['source_name'] = source_name
            debug(_("Source Name: {source_val}").format(source_val=source_name))

        if not query_params:
            console.print(_("[yellow]Please provide at least one search criterion (keyword, ucd, or source name).[/yellow]"))
            console.print(_("Example: `aqc vizier find-catalogs --keyword photometry --keyword M31`"))
            raise typer.Exit(code=1)

        try:
            result_tables = Vizier.find_catalogs(**query_params)
            if result_tables and len(result_tables) > 0 and 0 in result_tables.keys():
                display_table(
                    ctx,
                    result_tables[0],
                    title=_("Found VizieR Catalogs"),
                    max_rows=max_catalogs,
                    show_all_columns=show_all_columns
                )
            else:
                console.print(_("[yellow]No catalogs found matching your criteria.[/yellow]"))
                return

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("VizieR find_catalogs"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(
        name="list",
        help=builtins._(
            "List all available VizieR catalogs. "
            "Note: VizieR API does not support listing all catalogs at once. "
            "If no catalogs are found, try 'find-catalogs' with keywords. "
            "Common keywords: 'photometry', 'galaxy', 'quasar', 'gaia', '2mass', 'sdss', 'star', 'cluster', 'radio', 'infrared', 'xray', 'survey', 'variable', 'proper motion', 'catalog'. "
            "Example: aqc vizier find-catalogs --keyword photometry --keyword galaxy"
        )
    )
    @global_keyboard_interrupt_handler
    def list_catalogs(ctx: typer.Context,
        max_catalogs: int = typer.Option(20, help=builtins._("Maximum number of catalogs to list.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        vizier_server: str = typer.Option(
            "vizier_cds",
            help=builtins._("VizieR server to use. Choices: {server_list}").format(server_list=list(VIZIER_SERVERS.keys())),
            autocompletion=lambda: list(VIZIER_SERVERS.keys())
        )
    ):
        console.print(_("[cyan]Attempting to list all VizieR catalogs...[/cyan]"))
        console.print(_("[yellow]Note: If this returns no catalogs, the VizieR service might not support listing all catalogs directly, or there might be a network issue. Consider using 'find-catalogs' with specific keywords instead.[/yellow]"))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        debug(_("Using VizieR server: {server_url}").format(server_url=vizier_conf.server))

        try:
            # Attempt to get all catalogs. If this fails or returns empty,
            # we will fall back to a keyword search and provide suggestions.
            all_catalogs = Vizier.get_catalogs(catalog=[])
            
            if all_catalogs:
                display_table(
                    ctx,
                    all_catalogs[0],
                    title=_("All Available VizieR Catalogs"),
                    max_rows=max_catalogs,
                    show_all_columns=show_all_columns
                )
            else:
                console.print(_(
                    "[yellow]No catalogs found using direct listing. "
                    "VizieR API does not support listing all catalogs at once. "
                    "Please use keyword search. "
                    "Common keywords: 'photometry', 'galaxy', 'quasar', 'gaia', '2mass', 'sdss', 'star', 'cluster', 'radio', 'infrared', 'xray', 'survey', 'variable', 'proper motion', 'catalog'.[/yellow]"
                ))
                console.print(_("[yellow]Example: aqc vizier find-catalogs --keyword photometry --keyword galaxy[/yellow]"))
                return

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("VizieR list_catalogs"))
            console.print(_(
                "[yellow]VizieR API does not support listing all catalogs at once. "
                "Please use keyword search. "
                "Common keywords: 'photometry', 'galaxy', 'quasar', 'gaia', '2mass', 'sdss', 'star', 'cluster', 'radio', 'infrared', 'xray', 'survey', 'variable', 'proper motion', 'catalog'.[/yellow]"
            ))
            console.print(_("[yellow]Example: aqc vizier find-catalogs --keyword photometry --keyword galaxy[/yellow]"))
            return

    @app.command(name="object", help=builtins._("Query catalogs around an object name or specific coordinates."))
    @global_keyboard_interrupt_handler
    def query_object(ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Object name (e.g., 'M31') or coordinates (e.g., '10.68h +41.26d' or '160.32 41.45').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '5arcmin', '0.1deg'). Can be specified as positional argument or with -r/--radius."), rich_help_panel="Arguments", show_default=False),
        catalogs: Optional[List[str]] = typer.Option(None, "--catalog", "-c", help=builtins._("VizieR catalog identifier(s) (e.g., 'I/261/gaiadr3', 'J/ApJ/710/1776'). Can be specified multiple times. Default: 'I/261/gaiadr3'")),
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
        catalogs_to_query = catalogs if catalogs is not None else ['I/261/gaiadr3']
        console.print(_("[cyan]Querying VizieR for object '{target_name}' in catalog(s): {catalog_list}...[/cyan]").format(target_name=target, catalog_list=', '.join(catalogs_to_query)))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        vizier_conf.row_limit = row_limit
        debug(_("Using VizieR server: {server_url}, Row limit: {limit}").format(server_url=vizier_conf.server, limit=row_limit))

        coords = parse_coordinates(ctx, target)
        rad_quantity = parse_angle_str_to_quantity(ctx, radius)

        # Process column_filters to be a dictionary as expected by Vizier
        processed_column_filters = parse_constraints_list(ctx, column_filters)

        viz = Vizier(columns=columns if columns else ["*"], catalog=catalogs_to_query, column_filters=processed_column_filters, row_limit=row_limit)

        try:
            result_tables = viz.query_object(
                coords,
                radius=rad_quantity,
            )

            if not result_tables:
                console.print(_("[yellow]No results returned from VizieR for this query.[/yellow]"))
                return

            for table_name in result_tables.keys():
                table_data = result_tables[table_name]
                if table_data is not None and len(table_data) > 0:
                    display_table(ctx, table_data, title=_("Results from {catalog_name} for {target_name}").format(catalog_name=table_name, target_name=target), max_rows=max_rows_display, show_all_columns=show_all_columns)
                else:
                    console.print(_("[yellow]No data found in catalog '{catalog_name}' for the given criteria.[/yellow]").format(catalog_name=table_name))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("Vizier object"))
            raise typer.Exit(code=1)


    @app.command(name="region", help=builtins._("Query catalogs within a sky region (cone or box)."))
    @global_keyboard_interrupt_handler
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Central coordinates for the region (e.g., '10.68h +41.26d' or '160.32 41.45').")),
        radius: Optional[str] = typer.Argument(None, help=builtins._("Cone search radius (e.g., '5arcmin', '0.1deg'). Use if not specifying width/height. Can be specified as positional argument or with -r/--radius."), rich_help_panel="Arguments", show_default=False),
        width: Optional[str] = typer.Option(None, "--width", help=builtins._("Width of a box region (e.g., '10arcmin', '0.5deg'). Requires --height.")),
        height: Optional[str] = typer.Option(None, "--height", help=builtins._("Height of a box region (e.g., '10arcmin', '0.5deg'). Requires --width.")),
        catalogs: Optional[List[str]] = typer.Option(None, "--catalog", "-c", help=builtins._("VizieR catalog identifier(s) (e.g., 'I/261/gaiadr3', 'J/ApJ/710/1776'). Can be specified multiple times. Default: 'I/261/gaiadr3'")),
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
        catalogs_to_query = catalogs if catalogs is not None else ['I/261/gaiadr3']
        console.print(_(f"[cyan]Querying VizieR region around '{coordinates}' in catalog(s): {', '.join(catalogs_to_query)}...[/cyan]"))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        vizier_conf.row_limit = row_limit
        debug(_(f"Using VizieR server: {vizier_conf.server}, Row limit: {row_limit}"))

        coords_obj = parse_coordinates(ctx, coordinates) # Changed to coords_obj
        rad_quantity = parse_angle_str_to_quantity(ctx, radius)
        width_quantity = parse_angle_str_to_quantity(ctx, width)
        height_quantity = parse_angle_str_to_quantity(ctx, height)

        if rad_quantity is not None and (width_quantity is not None or height_quantity is not None):
            console.print(_(f"[bold red]Error: Specify either --radius (for cone search) OR (--width and --height) (for box search), not both.[/bold red]"))
            raise typer.Exit(code=1)
        if (width_quantity is not None and height_quantity is None) or (width_quantity is None and height_quantity is not None):
            console.print(_(f"[bold red]Error: For a box search, both --width and --height must be specified.[/bold red]"))
            raise typer.Exit(code=1)
        if rad_quantity is None and (width_quantity is None and height_quantity is None):
            console.print(_(f"[bold red]Error: You must specify search dimensions: either --radius OR (--width and --height).[/bold red]"))
            raise typer.Exit(code=1)

        # Process column_filters to be a dictionary as expected by Vizier
        processed_column_filters = parse_constraints_list(ctx, column_filters)

        viz = Vizier(columns=columns if columns else ["*"], catalog=catalogs, column_filters=processed_column_filters, row_limit=row_limit)

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

            max_tables_display = 5
            for idx, table_name in enumerate(result_tables.keys()):
                if idx >= max_tables_display:
                    break
                table_data = result_tables[table_name]
                if table_data is not None and len(table_data) > 0:
                    display_table(ctx, table_data, title=_(f"Results from {table_name} for region around {coordinates}"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                else:
                    console.print(_(f"[yellow]No data found in catalog '{table_name}' for the given criteria.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("Vizier region"))
            raise typer.Exit(code=1)


    @app.command(name="constraints", help=builtins._("Query catalogs based on specific column constraints or keywords."))
    @global_keyboard_interrupt_handler
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
        console.print(_(f"[cyan]Querying VizieR with constraints in catalog(s): {', '.join(catalogs)}...[/cyan]"))
        vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
        vizier_conf.row_limit = row_limit
        debug(_(f"Using VizieR server: {vizier_conf.server}, Row limit: {row_limit}"))

        parsed_constraints = parse_constraints_list(ctx, constraints)
        if not parsed_constraints and not keywords:
            console.print(_("[yellow]Please provide at least --constraint(s) or --keyword(s) for this query type.[/yellow]"))
            raise typer.Exit(code=1)

        query_kwargs = {}
        if parsed_constraints:
            query_kwargs.update(parsed_constraints)
            debug(_(f"Using constraints: {query_kwargs}"))
        if keywords:
            query_kwargs['keywords'] = " ".join(keywords)
            debug(_(f"Using keywords: {query_kwargs['keywords']}"))


        viz = Vizier(columns=columns if columns else ["*"], row_limit=row_limit)
        viz.catalog = catalogs

        try:
            result_tables = viz.query_constraints(**query_kwargs)

            if not result_tables:
                console.print(_("[yellow]No results returned from VizieR for this query.[/yellow]"))
                return

            for table_name in result_tables.keys():
                table_data = result_tables[table_name]
                if table_data is not None and len(table_data) > 0:
                    display_table(ctx, table_data, title=_(f"Constraint Query Results from {table_name}"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                else:
                    console.print(_(f"[yellow]No data found in catalog '{table_name}' for the given criteria.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("Vizier constraints"))
            raise typer.Exit(code=1)

    return app
