from typing import Optional, List

import typer
from astroquery.simbad import Simbad, SimbadClass
from astropy.table import Table
from rich.console import Console
from ..i18n import get_translator
_ = get_translator()

from ..utils import display_table, handle_astroquery_exception, common_output_options, save_table_to_file

console = Console()
app = typer.Typer(
    name="simbad",
    help=_("Query the SIMBAD astronomical database. 🆔"),
    no_args_is_help=True
)

Simbad.ROW_LIMIT = 50
Simbad.TIMEOUT = 60

def add_common_fields(simbad_instance: Simbad):
    fields_to_add = [
        "ra(d)", "dec(d)", "plx", "plx_error",
        "rv_value", "rv_error",
        "pmra", "pmdec", "pm_err_maj", "pm_err_min",
        "sptype",
        "fe_h",
        "flux(V)", "flux_error(V)",
        "flux(B)", "flux_error(B)",
        "flux(R)", "flux_error(R)",
        "flux(I)", "flux_error(I)",
        "flux(J)", "flux_error(J)",
        "flux(H)", "flux_error(H)",
        "flux(K)", "flux_error(K)",
        "otype(V)",
        "id(HD)", "id(HIP)", "id(TYC)", "id(Gaia)"
    ]
    for field in fields_to_add:
        try:
            simbad_instance.add_votable_fields(field)
        except ValueError:
            pass

@app.command(name="query-object", help=_("Query basic data for an astronomical object."))
def query_object(
    object_name: str = typer.Argument(..., help=_("Name of the object to query (e.g., 'M101', 'HD12345').")),
    wildcard: bool = typer.Option(False, "--wildcard", "-w", help=_("Enable wildcard searching for the object name.")),
    add_fields: Optional[List[str]] = typer.Option(None, "--add-field", help=_("Additional VOTable fields to retrieve (e.g., 'otype', 'sptype'). Can be specified multiple times.")),
    remove_fields: Optional[List[str]] = typer.Option(None, "--remove-field", help=_("Default VOTable fields to remove (e.g., 'coo_bibcode'). Can be specified multiple times.")),
    include_common_fields: bool = typer.Option(True, help=_("Automatically include a set of common useful fields.")),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(10, help=_("Maximum number of rows to display. Use -1 for all rows.")),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help=_("Show all columns in the output table."))
):
    """
    Retrieves information about a specific astronomical object from SIMBAD.
    Example: aq simbad query-object M31
    Example: aq simbad query-object "HD 1*" --wildcard --add-field sptype
    """
    console.print(_("[cyan]Querying SIMBAD for object: '{object_name}'...[/cyan]").format(object_name=object_name))
    s = Simbad()
    if include_common_fields:
        add_common_fields(s)
    if add_fields:
        for field in add_fields:
            s.add_votable_fields(field)
    if remove_fields:
        for field in remove_fields:
            s.remove_votable_fields(field)

    try:
        result_table: Optional[Table] = s.query_object(object_name, wildcard=wildcard)

        if result_table:
            console.print(_("[green]Found {count} match(es) for '{object_name}'.[/green]").format(count=len(result_table), object_name=object_name))
            display_table(result_table, title=_("SIMBAD Data for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, _("SIMBAD object query"))
        else:
            console.print(_("[yellow]No information found for object '{object_name}'.[/yellow]").format(object_name=object_name))

    except Exception as e:
        handle_astroquery_exception(e, _("SIMBAD query_object"))
        raise typer.Exit(code=1)


@app.command(name="query-ids", help=_("Query all identifiers for an astronomical object."))
def query_ids(
    object_name: str = typer.Argument(..., help=_("Name of the object (e.g., 'Polaris').")),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help=_("Maximum number of rows to display. Use -1 for all rows.")),
):
    """
    Retrieves all known identifiers for a given astronomical object.
    Example: aq simbad query-ids M51
    """
    console.print(_("[cyan]Querying SIMBAD for identifiers of: '{object_name}'...[/cyan]").format(object_name=object_name))
    s = Simbad()
    try:
        result_table: Optional[Table] = s.query_objectids(object_name)
        if result_table:
            display_table(result_table, title=_("SIMBAD Identifiers for {object_name}").format(object_name=object_name), max_rows=max_rows_display)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, _("SIMBAD ID query"))
        else:
            console.print(_("[yellow]No identifiers found for object '{object_name}'.[/yellow]").format(object_name=object_name))
    except Exception as e:
        handle_astroquery_exception(e, _("SIMBAD query_objectids"))
        raise typer.Exit(code=1)


@app.command(name="query-bibcode", help=_("Query objects associated with a bibcode or bibcode list."))
def query_bibcode(
    bibcodes: List[str] = typer.Argument(..., help=_("Bibcode(s) to query (e.g., '2003A&A...409..581H'). Can specify multiple.")),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(50, help=_("Maximum number of rows to display. Use -1 for all rows.")),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help=_("Show all columns in the output table."))
):
    """
    Retrieves objects from SIMBAD that are cited in the given bibcode(s).
    Example: aq simbad query-bibcode 1997AJ....113.2104S
    Example: aq simbad query-bibcode 2003A&A...409..581H 2004A&A...418..989P
    """
    bibcodes_str = ', '.join(bibcodes)
    console.print(_("[cyan]Querying SIMBAD for objects in bibcode(s): {bibcodes_list}...[/cyan]").format(bibcodes_list=bibcodes_str))
    s = Simbad()
    add_common_fields(s)
    try:
        result_table: Optional[Table] = s.query_bibcode(bibcodes)
        if result_table:
            display_table(result_table, title=_("SIMBAD Objects for Bibcode(s)"), max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, _("SIMBAD bibcode query"))
        else:
            console.print(_("[yellow]No objects found for the given bibcode(s).[/yellow]"))
    except Exception as e:
        handle_astroquery_exception(e, _("SIMBAD query_bibcode"))
        raise typer.Exit(code=1)

# TODO: Add more Simbad functionalities like query_region, query_criteria, list_votable_fields if desired.
