# astroquery_cli/modules/simbad_cli.py
from typing import Optional, List

import typer
from astroquery.simbad import Simbad, SimbadClass
from astropy.table import Table
from rich.console import Console

from ..utils import display_table, handle_astroquery_exception, common_output_options, save_table_to_file

console = Console()
app = typer.Typer(
    name="simbad",
    help="Query the SIMBAD astronomical database. 🆔"
)

# Configure Simbad
Simbad.ROW_LIMIT = 50 # Default row limit for queries
Simbad.TIMEOUT = 60   # Default timeout

# Helper to add common fields to query
def add_common_fields(simbad_instance: Simbad):
    """Adds a set of commonly useful fields to the Simbad query."""
    fields_to_add = [
        "ra(d)", "dec(d)", "plx", "plx_error", # Basic astrometry
        "rv_value", "rvz_error",              # Radial velocity
        "pmra", "pmdec", "pm_err_maj", "pm_err_min", # Proper motions
        "sptype",                             # Spectral type
        "fe_h",                               # Metallicity
        "flux(V)", "flux_error(V)",           # V-band magnitude
        "flux(B)", "flux_error(B)",           # B-band magnitude
        "flux(R)", "flux_error(R)",           # R-band magnitude
        "flux(I)", "flux_error(I)",           # I-band magnitude
        "flux(J)", "flux_error(J)",           # J-band magnitude
        "flux(H)", "flux_error(H)",           # H-band magnitude
        "flux(K)", "flux_error(K)",           # K-band magnitude
        "otype(V)",                           # Main object type verbose
        "id(HD)", "id(HIP)", "id(TYC)", "id(Gaia)" # Common identifiers
    ]
    for field in fields_to_add:
        try:
            simbad_instance.add_votable_fields(field)
        except ValueError: # Field might already be default or invalid for some reason
            # console.print(f"[dim]Could not add field '{field}' to SIMBAD query (might be default or unavailable).[/dim]")
            pass # Silently skip if field can't be added

@app.command(name="query-object", help="Query basic data for an astronomical object.")
def query_object(
    object_name: str = typer.Argument(..., help="Name of the object to query (e.g., 'M101', 'HD12345')."),
    wildcard: bool = typer.Option(False, "--wildcard", "-w", help="Enable wildcard searching for the object name."),
    add_fields: Optional[List[str]] = typer.Option(None, "--add-field", help="Additional VOTable fields to retrieve (e.g., 'otype', 'sptype'). Can be specified multiple times."),
    remove_fields: Optional[List[str]] = typer.Option(None, "--remove-field", help="Default VOTable fields to remove (e.g., 'coo_bibcode'). Can be specified multiple times."),
    include_common_fields: bool = typer.Option(True, help="Automatically include a set of common useful fields."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(10, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    """
    Retrieves information about a specific astronomical object from SIMBAD.
    Example: aq simbad query-object M31
    Example: aq simbad query-object "HD 1*" --wildcard --add-field sptype
    """
    console.print(f"[cyan]Querying SIMBAD for object: '{object_name}'...[/cyan]")
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
            console.print(f"[green]Found {len(result_table)} match(es) for '{object_name}'.[/green]")
            display_table(result_table, title=f"SIMBAD Data for {object_name}", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "SIMBAD object query")
        else:
            console.print(f"[yellow]No information found for object '{object_name}'.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, "SIMBAD query_object")
        raise typer.Exit(code=1)


@app.command(name="query-ids", help="Query all identifiers for an astronomical object.")
def query_ids(
    object_name: str = typer.Argument(..., help="Name of the object (e.g., 'Polaris')."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
):
    """
    Retrieves all known identifiers for a given astronomical object.
    Example: aq simbad query-ids M51
    """
    console.print(f"[cyan]Querying SIMBAD for identifiers of: '{object_name}'...[/cyan]")
    s = Simbad()
    try:
        result_table: Optional[Table] = s.query_objectids(object_name)
        if result_table:
            display_table(result_table, title=f"SIMBAD Identifiers for {object_name}", max_rows=max_rows_display)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "SIMBAD ID query")
        else:
            console.print(f"[yellow]No identifiers found for object '{object_name}'.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "SIMBAD query_objectids")
        raise typer.Exit(code=1)


@app.command(name="query-bibcode", help="Query objects associated with a bibcode or bibcode list.")
def query_bibcode(
    bibcodes: List[str] = typer.Argument(..., help="Bibcode(s) to query (e.g., '2003A&A...409..581H'). Can specify multiple."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(50, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    """
    Retrieves objects from SIMBAD that are cited in the given bibcode(s).
    Example: aq simbad query-bibcode 1997AJ....113.2104S
    Example: aq simbad query-bibcode 2003A&A...409..581H 2004A&A...418..989P
    """
    console.print(f"[cyan]Querying SIMBAD for objects in bibcode(s): {', '.join(bibcodes)}...[/cyan]")
    s = Simbad()
    add_common_fields(s) # Bibcode queries benefit from more fields
    try:
        result_table: Optional[Table] = s.query_bibcode(bibcodes) # bibcodes can be a list
        if result_table:
            display_table(result_table, title=f"SIMBAD Objects for Bibcode(s)", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "SIMBAD bibcode query")
        else:
            console.print(f"[yellow]No objects found for the given bibcode(s).[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "SIMBAD query_bibcode")
        raise typer.Exit(code=1)

# TODO: Add more Simbad functionalities like query_region, query_criteria, list_votable_fields if desired.
