# astroquery_cli/modules/jplhorizons_cli.py
from typing import Optional, List, Tuple
from enum import Enum

import typer
from astroquery.jplhorizons import Horizons, conf as jpl_conf
from astropy.time import Time
from rich.console import Console

from ..utils import display_table, handle_astroquery_exception

# 使用 Rich 控制台
console = Console()
app = typer.Typer(
    name="jplhorizons",
    help="Query JPL Horizons service for ephemerides, orbital elements, and vector data. 🛰️"
)

# --- Configuration ---
# Allow setting JPL server via environment variable or option
# Default to NASA JPL server, but allow specifying KSB (e.g. for comets)
JPL_SERVERS = {
    "nasa": jpl_conf.horizons_server,
    "ksb": "https://ssd.jpl.nasa.gov/horizons_batch.cgi" # Example, check official URL if needed
}

# --- Argument Types and Choices ---
class IDType(str, Enum):
    smallbody = "smallbody"  # Asteroid or comet
    majorbody = "majorbody"  # Planet, satellite, Sun, or specific spacecraft
    designation = "designation" # Asteroid or comet designation
    name = "name"          # Name, if recognized
    asteroid_number = "asteroid_number"
    comet_name = "comet_name"
    # Add more as needed based on Horizons documentation

class EphemType(str, Enum):
    OBSERVER = "OBSERVER"
    VECTORS = "VECTORS"
    ELEMENTS = "ELEMENTS"
    # SPK = "SPK" # SPK generation might be too complex for a simple CLI initially

# --- Helper Functions for Autocompletion (Examples) ---
def get_common_locations():
    """Provides a list of common observatory codes for autocompletion."""
    return ["500", "geo", "010", "F51", "G84"] # Geocentric, Sun, Haleakala, Pan-STARRS 1, Catalina Sky Survey

def get_default_quantities_ephem():
    """Default quantities for ephemerides."""
    # RA/DEC, Alt/Az, range, range-rate, angular separation, etc.
    return "1,2,4,8,9,10,12,13,14,19,20,21,23,24,31" # Common set, adjust as needed

# --- CLI Commands ---
@app.command(name="query", help="Query ephemerides, orbital elements, or vectors for a target object.")
def query_object(
    target: str = typer.Argument(..., help="Object ID (e.g., 'Mars', 'Ceres', '2000NM', '@10'). Use '@' prefix for spacecraft ID."),
    epochs: Optional[str] = typer.Option(
        None,
        help=(
            "Epochs for the query. Can be a single ISO time (e.g., '2023-01-01 12:00'), "
            "a list of times separated by commas (e.g., '2023-01-01,2023-01-02'), "
            "or a start,stop,step dict-like string (e.g., \"{'start':'2023-01-01', 'stop':'2023-01-05', 'step':'1d'}\"). "
            "If None, uses current time for single epoch queries like elements/vectors."
        )
    ),
    start_time: Optional[str] = typer.Option(None, "--start", help="Start time for ephemeris range (YYYY-MM-DD [HH:MM]). Overrides 'epochs' if 'end_time' is also set."),
    end_time: Optional[str] = typer.Option(None, "--end", help="End time for ephemeris range (YYYY-MM-DD [HH:MM])."),
    step: Optional[str] = typer.Option("1d", "--step", help="Time step for ephemeris range (e.g., '1d', '1h', '10m'). Used if 'start_time' and 'end_time' are set."),
    location: str = typer.Option(
        "500",
        help="Observatory code (e.g., '500' for Geocenter, 'geo' is alias for '500'). Try common codes or find specific ones.",
        autocompletion=get_common_locations
    ),
    id_type: Optional[IDType] = typer.Option(
        None,
        case_sensitive=False,
        help="Type of the target identifier. If None, Horizons will try to guess."
    ),
    ephem_type: EphemType = typer.Option(
        EphemType.OBSERVER,
        case_sensitive=False,
        help="Type of ephemeris to retrieve."
    ),
    quantities: Optional[str] = typer.Option(
        None,
        help="Comma-separated string of quantity codes (e.g., '1,2,19,20'). Relevant for OBSERVER and VECTORS. See JPL Horizons docs for codes. Uses sensible defaults if None."
    ),
    # airmass_lessthan: Optional[float] = typer.Option(None, help="Observer table: return only data with airmass less than this value."), # Example of more specific option
    # skip_daylight: bool = typer.Option(False, help="Observer table: skip query when sun is above horizon."),
    max_rows: int = typer.Option(20, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table, even if wide."),
    jpl_server: str = typer.Option(
        "nasa",
        help=f"JPL Horizons server to use. Choices: {list(JPL_SERVERS.keys())}",
        autocompletion=lambda: list(JPL_SERVERS.keys())
    )
):
    """
    Main query function for JPL Horizons.
    Fetches ephemerides (OBSERVER), orbital elements (ELEMENTS), or state vectors (VECTORS).
    """
    console.print(f"[cyan]Querying JPL Horizons for '{target}'...[/cyan]")

    current_server = JPL_SERVERS.get(jpl_server.lower(), jpl_conf.horizons_server)
    if jpl_conf.horizons_server != current_server:
        console.print(f"[dim]Using JPL server: {current_server}[/dim]")
        jpl_conf.horizons_server = current_server


    # Construct epochs dictionary
    epoch_dict = None
    if start_time and end_time:
        epoch_dict = {'start': start_time, 'stop': end_time, 'step': step}
        console.print(f"[dim]Using epoch range: {start_time} to {end_time} with step {step}[/dim]")
    elif epochs:
        if epochs.startswith("{") and epochs.endswith("}"): # dict-like string
            try:
                import ast
                epoch_dict = ast.literal_eval(epochs)
                console.print(f"[dim]Using epoch dict: {epoch_dict}[/dim]")
            except (ValueError, SyntaxError) as e:
                console.print(f"[bold red]Error parsing --epochs as dict: {e}[/bold red]")
                console.print(f"[yellow]Example: --epochs \"{{'start':'2023-01-01', 'stop':'2023-01-05', 'step':'1d'}}\"[/yellow]")
                raise typer.Exit(code=1)
        elif ',' in epochs: # list of times
            epoch_dict = [t.strip() for t in epochs.split(',')]
            console.print(f"[dim]Using epoch list: {epoch_dict}[/dim]")
        else: # single time
            epoch_dict = epochs
            console.print(f"[dim]Using single epoch: {epoch_dict}[/dim]")
    elif ephem_type in [EphemType.ELEMENTS, EphemType.VECTORS]:
        # Default to current time for elements/vectors if no epochs provided
        epoch_dict = Time.now().iso
        console.print(f"[dim]No epoch specified for {ephem_type.value}, using current time: {epoch_dict}[/dim]")
    elif ephem_type == EphemType.OBSERVER:
         console.print(f"[bold red]Error: For ephemeris type OBSERVER, you must specify --epochs or (--start, --end, --step).[/bold red]")
         raise typer.Exit(code=1)


    # Prepare query parameters
    query_params = {
        "id": target,
        "location": location,
        "epochs": epoch_dict,
        "id_type": id_type.value if id_type else None,
    }

    # Clean None values from query_params
    query_params = {k: v for k, v in query_params.items() if v is not None}

    try:
        obj = Horizons(**query_params)

        table_title = f"{ephem_type.value} for {target}"
        result_table = None

        if ephem_type == EphemType.OBSERVER:
            q = quantities or get_default_quantities_ephem()
            console.print(f"[dim]Requesting quantities: {q}[/dim]")
            result_table = obj.ephemerides(quantities=q, get_raw_response=False)
            # Could add specific options for ephemerides here, e.g.
            # if airmass_lessthan: result_table = obj.ephemerides(..., airmass_lessthan=airmass_lessthan)
            # if skip_daylight: result_table = obj.ephemerides(..., skip_daylight=skip_daylight)

        elif ephem_type == EphemType.VECTORS:
            q = quantities # For vectors, quantities might be different or not needed as much.
            if q: console.print(f"[dim]Requesting quantities for vectors: {q}[/dim]")
            result_table = obj.vectors(quantities=q, get_raw_response=False) if q else obj.vectors(get_raw_response=False)

        elif ephem_type == EphemType.ELEMENTS:
            q = quantities # For elements, quantities might be different.
            if q: console.print(f"[dim]Requesting quantities for elements: {q}[/dim]")
            result_table = obj.elements(quantities=q, get_raw_response=False) if q else obj.elements(get_raw_response=False)

        display_table(result_table, title=table_title, max_rows=max_rows, show_all_columns=show_all_columns)

    except Exception as e:
        handle_astroquery_exception(e, "JPL Horizons")
        raise typer.Exit(code=1)

# You can add more commands specific to JPL Horizons if needed,
# for example, a command to list common objects or search for objects,
# but these might require parsing Horizons web pages or other non-API interactions.
# For now, `query` is the primary interface.

# Example of a potential future command:
# @app.command(name="find", help="Try to find object ID using Horizons' search capabilities (experimental).")
# def find_object(name_fragment: str):
#     console.print(f"[yellow]Object finding functionality is experimental and may not always work.[/yellow]")
#     # This would require web scraping or using a different part of Horizons,
#     # as astroquery.jplhorizons primarily focuses on querying known IDs.
#     # For instance, Horizons().find_appropriate_name(name_fragment) might be useful
#     # but it's not a standard public API of astroquery's HorizonsClass.
#     try:
#         # This is a placeholder, actual implementation would be more complex
#         # and might involve trying HorizonsClass internal methods or web requests.
#         console.print(f"Attempting to find objects matching: '{name_fragment}'")
#         console.print("This feature is not fully implemented yet.")
#         # Potentially call some internal Horizons methods if they exist and are stable enough
#         # Or, inform the user to use the web interface for ambiguous searches.
#     except Exception as e:
#         handle_astroquery_exception(e, "JPL Horizons Find")
