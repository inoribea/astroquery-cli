from typing import Optional, List
import typer
from astroquery.gaia import Gaia, conf as gaia_conf
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console

console = Console()

# Suppress Gaia server messages during import
gaia_conf.show_server_messages = False

from ..utils import display_table, handle_astroquery_exception, parse_coordinates, parse_angle_str_to_quantity, common_output_options, save_table_to_file
from ..utils import global_keyboard_interrupt_handler
from ..i18n import get_translator
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout
from astroquery_cli.common_options import setup_debug_context # Import setup_debug_context
from astroquery_cli.debug import debug # Import debug function

def get_app():
    import builtins
    _ = builtins._ # This line is fine, it just ensures _ is available in this scope
    app = typer.Typer(
        name="gaia",
        help=builtins._("Query the Gaia archive."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def gaia_callback(
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
        # Re-enable Gaia server messages when the gaia app is actually invoked
        gaia_conf.show_server_messages = True
        

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

    # Removed: console = Console() # This console instance is fine

    @app.command(name="object", help=builtins._("Query Gaia main source for a given object name or coordinates."))
    @global_keyboard_interrupt_handler
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
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        resolved_table_name = GAIA_TABLES.get(table_name, table_name)
        # Removed: _ = get_translator(ctx.obj.get("lang", "en") if ctx.obj else "en")
        # This line was overriding the builtins._ set by main.py
        try:
            coords_obj = parse_coordinates(ctx, target)
            rad_quantity = parse_angle_str_to_quantity(ctx, radius)
            if rad_quantity is None:
                message = builtins._("Invalid radius provided.")
                console.print(f"[bold red]{message}[/bold red]")
                raise typer.Exit(code=1)

            query = f"""
            SELECT TOP 1 {', '.join(columns) if columns else 'source_id, ra, dec, parallax, pmra, pmdec, phot_g_mean_mag, radial_velocity'}
            FROM {resolved_table_name}
            WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {coords_obj.ra.deg}, {coords_obj.dec.deg}, {rad_quantity.to(u.deg).value}))
            """
            console.print(builtins._("[cyan]Querying Gaia for object: {target}...[/cyan]").format(target=target)) # Use builtins._

            job = Gaia.launch_job(query, dump_to_file=False)
            debug("Job launched. Getting results...")
            result_table = job.get_results()
            debug(f"Results retrieved. Table length: {len(result_table) if result_table is not None else 0}")

            if result_table is not None and len(result_table) > 0:
                title = _("Gaia Main Source for '{target}'").format(target=target)
                display_table(ctx, result_table, title=title, max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("Gaia object query"))
            else:
                console.print(_("[yellow]No Gaia source found for '{target}' in the given radius.[/yellow]").format(target=target))

        except Exception as e:
            handle_astroquery_exception(ctx, e, "Gaia query_object")
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="cone-search", help=builtins._("Perform a cone search around a coordinate."))
    @global_keyboard_interrupt_handler
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
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        resolved_table_name = GAIA_TABLES.get(table_name, table_name)
        console.print(_("[cyan]Performing Gaia cone search on '{table_name}' around '{target}' with radius {radius}...[/cyan]").format(table_name=resolved_table_name, target=target, radius=radius))

        if login_user and not login_password:
            login_password = typer.prompt(_("Gaia archive password"), hide_input=True)

        if login_user and login_password:
            debug(_("Logging into Gaia archive as '{user}'...").format(user=login_user))
            try:
                Gaia.login(user=login_user, password=login_password)
            except Exception as e:
                console.print(_("[bold red]Gaia login failed: {error}[/bold red]").format(error=e))
                console.print(_("[yellow]Proceeding with anonymous access if possible.[/yellow]"))
        elif Gaia.authenticated():
            debug(_("Already logged into Gaia archive as '{user}'.").format(user=Gaia.credentials.username if Gaia.credentials else _('unknown user')))
        else:
            debug(_("No Gaia login credentials provided. Using anonymous access."))

        try:
            coords_obj = parse_coordinates(ctx, target)
            rad_quantity = parse_angle_str_to_quantity(ctx, radius)
            if rad_quantity is None:
                console.print(_("[bold red]Invalid radius provided.[/bold red]"))
                raise typer.Exit(code=1)

            query = f"""
            SELECT {', '.join(columns) if columns else '*'}
            FROM {resolved_table_name}
            WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {coords_obj.ra.deg}, {coords_obj.dec.deg}, {rad_quantity.to(u.deg).value}))
            LIMIT {row_limit}
            """
            debug(_("Executing ADQL query (first {row_limit} rows):").format(row_limit=row_limit))
            debug(f"{query.strip()}")

            job = Gaia.launch_job(query, dump_to_file=False)
            result_table = job.get_results()

            if result_table is not None and len(result_table) > 0:
                title = _("Gaia Cone Search Results ({table_name})").format(table_name=resolved_table_name)
                if Gaia.authenticated() and Gaia.credentials:
                    title += _(" (User: {user})").format(user=Gaia.credentials.username)
                display_table(ctx, result_table, title=title, max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("Gaia cone search"))
            else:
                console.print(_("[yellow]No results found from Gaia for this cone search.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("Gaia cone search on {table_name}").format(table_name=resolved_table_name))
            raise typer.Exit(code=1)
        finally:
            if login_user and Gaia.authenticated():
                Gaia.logout()
                debug(_("Logged out from Gaia archive."))

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()


    @app.command(name="adql-query", help=builtins._("Execute a raw ADQL query (synchronous)."))
    @global_keyboard_interrupt_handler
    def adql_query(ctx: typer.Context,
        query: str = typer.Argument(..., help=builtins._("The ADQL query string.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        login_user: Optional[str] = typer.Option(None, envvar="GAIA_USER", help=builtins._("Gaia archive username (or set GAIA_USER env var).")),
        login_password: Optional[str] = typer.Option(None, envvar="GAIA_PASSWORD", help=builtins._("Gaia archive password (or set GAIA_PASSWORD env var). Prompt if user set but no password."), prompt=False, hide_input=True),
test: bool = typer.Option(False, "--test", "-t", help=builtins._("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Executing Gaia ADQL query...[/cyan]"))
        debug(f"{query}")

        if login_user and not login_password:
            login_password = typer.prompt(_("Gaia archive password"), hide_input=True)

        if login_user and login_password:
            debug(_("Logging into Gaia archive as '{user}'...").format(user=login_user))
            try:
                Gaia.login(user=login_user, password=login_password)
            except Exception as e:
                console.print(_("[bold red]Gaia login failed: {error}[/bold red]").format(error=e))
                console.print(_("[yellow]Proceeding with anonymous access if possible.[/yellow]"))
        elif Gaia.authenticated():
            debug(_("Already logged into Gaia archive as '{user}'.").format(user=Gaia.credentials.username if Gaia.credentials else _('unknown user')))

        try:
            job = Gaia.launch_job(query, dump_to_file=False)
            result_table = job.get_results()

            if result_table is not None and len(result_table) > 0:
                title = _("Gaia ADQL Query Results")
                if Gaia.authenticated() and Gaia.credentials:
                    title += _(" (User: {user})").format(user=Gaia.credentials.username)
                display_table(ctx, result_table, title=title, max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("Gaia ADQL query"))
            else:
                console.print(_("[yellow]ADQL query returned no results or an empty table.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("Gaia ADQL query"))
            if "ERROR:" in str(e):
                console.print(_("[bold red]ADQL Query Error Details from server:\n{error_details}[/bold red]").format(error_details=str(e)))
            raise typer.Exit(code=1)
        finally:
            if login_user and Gaia.authenticated():
                Gaia.logout()
                debug(_("Logged out from Gaia archive."))

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()
 
    return app
