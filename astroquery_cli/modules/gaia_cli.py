from typing import Optional, List
import typer
from astroquery.gaia import Gaia, conf as gaia_conf
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console

from ..utils import display_table, handle_astroquery_exception, parse_coordinates, parse_angle_str_to_quantity, common_output_options, save_table_to_file
from ..i18n import get_translator

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="gaia",
        help=builtins._("Query the Gaia archive."),
        no_args_is_help=True
    )

    gaia_conf.show_server_messages = False

    # ================== GAIA_TABLES =============================
    GAIA_TABLES = {
        "main_source": "gaiadr3.gaia_source",
        "dr2_source": "gaiadr2.gaia_source",
        "edr3_source": "gaiaedr3.gaia_source",
        "tmass_best_neighbour": "gaiadr3.tmass_psc_xsc_best_neighbour",
        "allwise_best_neighbour": "gaiadr3.allwise_best_neighbour",
    }
    # ============================================================

    # ================== GAIA_VOTABLE_FIELDS =====================
    GAIA_VOTABLE_FIELDS = [
        "source_id",
        "ra",
        "dec",
        "parallax",
        "pmra",
        "pmdec",
        "phot_g_mean_mag",
        "radial_velocity",
        "astrometric_excess_noise",
        # ...
    ]
    # ============================================================


    @app.command(name="query-object", help=builtins._("Query Gaia main source for a given object name or coordinates."))
    def query_object(
        ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Object name or coordinates (e.g., 'M31', '10.68h +41.26d').")),
        radius: str = typer.Option("5arcsec", help=builtins._("Search radius for matching Gaia source (e.g., '5arcsec', '0.001deg').")),
        table_name: str = typer.Option(
            GAIA_TABLES["main_source"],
            help=builtins._("Gaia table to query. Default: gaiadr3.gaia_source"),
            autocompletion=lambda: list(GAIA_TABLES.keys())
        ),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Columns to retrieve (e.g., 'source_id', 'ra', 'dec', 'parallax').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(5, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        resolved_table_name = GAIA_TABLES.get(table_name, table_name)
        _ = get_translator(ctx.obj.get("lang", "en") if ctx.obj else "en")
        console = Console()
        try:
            try:
                coords_obj = parse_coordinates(ctx, target)
            except Exception:
                # fallback: resolve name via Simbad
                from astroquery.simbad import Simbad
                simbad = Simbad()
                simbad.add_votable_fields("ra", "dec")
                simbad_result = simbad.query_object(target)
                if simbad_result is not None and len(simbad_result) > 0:
                    ra = simbad_result["ra"][0]
                    dec = simbad_result["dec"][0]
                    from astropy.coordinates import SkyCoord
                    coords_obj = SkyCoord(f"{ra} {dec}", unit=(u.hourangle, u.deg))
                    console.print(f"[yellow]Resolved '{target}' { _('to coordinates via SIMBAD:') } {ra} {dec}[/yellow]")
                else:
                    console.print(_("[red]Could not resolve '{target}' to coordinates via SIMBAD.[/red]").format(target=target))
                    raise typer.Exit(code=1)

            rad_quantity = parse_angle_str_to_quantity(ctx, radius)
            if rad_quantity is None:
                console.print(_("[bold red]Invalid radius provided.[/bold red]"))
                raise typer.Exit(code=1)

            query = f"""
            SELECT TOP 1 {', '.join(columns) if columns else 'source_id, ra, dec, parallax, pmra, pmdec, phot_g_mean_mag, radial_velocity'}
            FROM {resolved_table_name}
            WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {coords_obj.ra.deg}, {coords_obj.dec.deg}, {rad_quantity.to(u.deg).value}))
            """
            console.print(_("[cyan]Querying Gaia for object: '{target}'...[/cyan]").format(target=target))
            console.print(f"[dim]{query.strip()}[/dim]")

            job = Gaia.launch_job(query, dump_to_file=False)
            result_table = job.get_results()

            if result_table is not None and len(result_table) > 0:
                title = _("Gaia Main Source for '{target}'").format(target=target)
                display_table(ctx, result_table, title=title, max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("Gaia object query"))
            else:
                console.print(_("[yellow]No Gaia source found for '{target}' in the given radius.[/yellow]").format(target=target))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("Gaia query_object"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="cone-search", help=builtins._("Perform a cone search around a coordinate."))
    def cone_search(ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Central object name or coordinates (e.g., 'M31', '10.68h +41.26d').")),
        radius: str = typer.Option("10arcsec", help=builtins._("Search radius (e.g., '5arcmin', '0.1deg').")),
        table_name: str = typer.Option(
            GAIA_TABLES["main_source"],
            help=builtins._("Gaia table to query. Common choices: {choices} or specify full table name.").format(choices=list(GAIA_TABLES.keys())),
            autocompletion=lambda: list(GAIA_TABLES.keys())
        ),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve (e.g., 'source_id', 'ra', 'dec', 'pmra'). Default: all columns from the table for a small radius, or a default set for larger radii.")),
        row_limit: int = typer.Option(1000, help=builtins._("Maximum number of rows to return from the server.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        login_user: Optional[str] = typer.Option(None, envvar="GAIA_USER", help=builtins._("Gaia archive username (or set GAIA_USER env var).")),
        login_password: Optional[str] = typer.Option(None, envvar="GAIA_PASSWORD", help=builtins._("Gaia archive password (or set GAIA_PASSWORD env var). Prompt if user set but no password."), prompt=False, hide_input=True),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        resolved_table_name = GAIA_TABLES.get(table_name, table_name)
        console.print(_("[cyan]Performing Gaia cone search on '{table_name}' around '{target}' with radius {radius}...[/cyan]").format(table_name=resolved_table_name, target=target, radius=radius))

        if login_user and not login_password:
            login_password = typer.prompt(_("Gaia archive password"), hide_input=True)

        if login_user and login_password:
            console.print(_("[dim]Logging into Gaia archive as '{user}'...[/dim]").format(user=login_user))
            try:
                Gaia.login(user=login_user, password=login_password)
            except Exception as e:
                console.print(_("[bold red]Gaia login failed: {error}[/bold red]").format(error=e))
                console.print(_("[yellow]Proceeding with anonymous access if possible.[/yellow]"))
        elif Gaia.authenticated():
            console.print(_("[dim]Already logged into Gaia archive as '{user}'.[/dim]").format(user=Gaia.credentials.username if Gaia.credentials else _('unknown user')))
        else:
            console.print(_("[dim]No Gaia login credentials provided. Using anonymous access.[/dim]"))

        try:
            coords_obj = parse_coordinates(target)
            rad_quantity = parse_angle_str_to_quantity(radius)
            if rad_quantity is None:
                console.print(_("[bold red]Invalid radius provided.[/bold red]"))
                raise typer.Exit(code=1)

            query = f"""
            SELECT {', '.join(columns) if columns else '*'}
            FROM {resolved_table_name}
            WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {coords_obj.ra.deg}, {coords_obj.dec.deg}, {rad_quantity.to(u.deg).value}))
            LIMIT {row_limit}
            """
            console.print(_("[dim]Executing ADQL query (first {row_limit} rows):[/dim]").format(row_limit=row_limit))
            console.print(f"[dim]{query.strip()}[/dim]")

            job = Gaia.launch_job(query, dump_to_file=False)
            result_table = job.get_results()

            if result_table is not None and len(result_table) > 0:
                title = _("Gaia Cone Search Results ({table_name})").format(table_name=resolved_table_name)
                if Gaia.authenticated() and Gaia.credentials:
                    title += _(" (User: {user})").format(user=Gaia.credentials.username)
                display_table(result_table, title=title, max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("Gaia cone search"))
            else:
                console.print(_("[yellow]No results found from Gaia for this cone search.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(e, _("Gaia cone search on {table_name}").format(table_name=resolved_table_name))
            raise typer.Exit(code=1)
        finally:
            if login_user and Gaia.authenticated():
                Gaia.logout()
                console.print(_("[dim]Logged out from Gaia archive.[/dim]"))

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()


    @app.command(name="adql-query", help=builtins._("Execute a raw ADQL query (synchronous)."))
    def adql_query(ctx: typer.Context,
        query: str = typer.Argument(..., help=builtins._("The ADQL query string.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        login_user: Optional[str] = typer.Option(None, envvar="GAIA_USER", help=builtins._("Gaia archive username (or set GAIA_USER env var).")),
        login_password: Optional[str] = typer.Option(None, envvar="GAIA_PASSWORD", help=builtins._("Gaia archive password (or set GAIA_PASSWORD env var). Prompt if user set but no password."), prompt=False, hide_input=True),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Executing Gaia ADQL query...[/cyan]"))
        console.print(f"[dim]{query}[/dim]")

        if login_user and not login_password:
            login_password = typer.prompt(_("Gaia archive password"), hide_input=True)

        if login_user and login_password:
            console.print(_("[dim]Logging into Gaia archive as '{user}'...[/dim]").format(user=login_user))
            try:
                Gaia.login(user=login_user, password=login_password)
            except Exception as e:
                console.print(_("[bold red]Gaia login failed: {error}[/bold red]").format(error=e))
                console.print(_("[yellow]Proceeding with anonymous access if possible.[/yellow]"))
        elif Gaia.authenticated():
            console.print(_("[dim]Already logged into Gaia archive as '{user}'.[/dim]").format(user=Gaia.credentials.username if Gaia.credentials else _('unknown user')))

        try:
            job = Gaia.launch_job(query, dump_to_file=False)
            result_table = job.get_results()

            if result_table is not None and len(result_table) > 0:
                title = _("Gaia ADQL Query Results")
                if Gaia.authenticated() and Gaia.credentials:
                    title += _(" (User: {user})").format(user=Gaia.credentials.username)
                display_table(result_table, title=title, max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("Gaia ADQL query"))
            else:
                console.print(_("[yellow]ADQL query returned no results or an empty table.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(e, _("Gaia ADQL query"))
            if "ERROR:" in str(e):
                console.print(_("[bold red]ADQL Query Error Details from server:\n{error_details}[/bold red]").format(error_details=str(e)))
            raise typer.Exit(code=1)
        finally:
            if login_user and Gaia.authenticated():
                Gaia.logout()
                console.print(_("[dim]Logged out from Gaia archive.[/dim]"))

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()
 
    return app
