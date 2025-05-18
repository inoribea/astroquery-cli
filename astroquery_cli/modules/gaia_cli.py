from typing import Optional, List
import typer
from astroquery.gaia import Gaia, conf as gaia_conf
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console

from ..utils import display_table, handle_astroquery_exception, parse_coordinates, parse_angle_str_to_quantity, common_output_options, save_table_to_file
from ..i18n import get_translator

_ = get_translator()
console = Console()
app = typer.Typer(
    name="gaia",
    help=_("Query the ESA Gaia mission archive. 🛰️"),
    no_args_is_help=True
)

gaia_conf.show_server_messages = False

GAIA_TABLES = {
    "main_source": "gaiadr3.gaia_source",
    "dr2_source": "gaiadr2.gaia_source",
    "edr3_source": "gaiaedr3.gaia_source",
    "tmass_best_neighbour": "gaiadr3.tmass_psc_xsc_best_neighbour",
    "allwise_best_neighbour": "gaiadr3.allwise_best_neighbour",
}

@app.command(name="cone-search", help=_("Perform a cone search around a coordinate."))
def cone_search(
    target: str = typer.Argument(..., help=_("Central object name or coordinates (e.g., 'M31', '10.68h +41.26d').")),
    radius: str = typer.Option("10arcsec", help=_("Search radius (e.g., '5arcmin', '0.1deg').")),
    table_name: str = typer.Option(
        GAIA_TABLES["main_source"],
        help=_("Gaia table to query. Common choices: {choices} or specify full table name.").format(choices=list(GAIA_TABLES.keys())),
        autocompletion=lambda: list(GAIA_TABLES.keys())
    ),
    columns: Optional[List[str]] = typer.Option(None, "--col", help=_("Specific columns to retrieve (e.g., 'source_id', 'ra', 'dec', 'pmra'). Default: all columns from the table for a small radius, or a default set for larger radii.")),
    row_limit: int = typer.Option(1000, help=_("Maximum number of rows to return from the server.")),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help=_("Maximum number of rows to display. Use -1 for all rows.")),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help=_("Show all columns in the output table.")),
    login_user: Optional[str] = typer.Option(None, envvar="GAIA_USER", help=_("Gaia archive username (or set GAIA_USER env var).")),
    login_password: Optional[str] = typer.Option(None, envvar="GAIA_PASSWORD", help=_("Gaia archive password (or set GAIA_PASSWORD env var). Prompt if user set but no password."), prompt=False, hide_input=True)
):
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


@app.command(name="adql-query", help=_("Execute a raw ADQL query (synchronous)."))
def adql_query(
    query: str = typer.Argument(..., help=_("The ADQL query string.")),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help=_("Maximum number of rows to display. Use -1 for all rows.")),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help=_("Show all columns in the output table.")),
    login_user: Optional[str] = typer.Option(None, envvar="GAIA_USER", help=_("Gaia archive username (or set GAIA_USER env var).")),
    login_password: Optional[str] = typer.Option(None, envvar="GAIA_PASSWORD", help=_("Gaia archive password (or set GAIA_PASSWORD env var). Prompt if user set but no password."), prompt=False, hide_input=True)
):
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

