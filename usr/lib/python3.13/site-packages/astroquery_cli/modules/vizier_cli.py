# astroquery_cli/modules/vizier_cli.py
from typing import Optional, List, Tuple

import typer
from astroquery.vizier import Vizier, conf as vizier_conf
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console
from rich.panel import Panel

from ..utils import display_table, handle_astroquery_exception

console = Console()
app = typer.Typer(
    name="vizier",
    help="Query the VizieR database of astronomical catalogs. 📖"
)

# --- Helper Functions ---
def parse_angle_str_to_quantity(angle_str: Optional[str]) -> Optional[u.Quantity]:
    """Parses a string like '5arcmin' or '1deg' into an astropy.units.Quantity."""
    if angle_str is None:
        return None
    try:
        return u.Quantity(angle_str)
    except Exception as e:
        console.print(f"[bold red]Error parsing angle string '{angle_str}': {e}[/bold red]")
        console.print("[yellow]Hint: Use format like '5arcmin', '0.5deg', '10arcsec'.[/yellow]")
        raise typer.Exit(code=1)

def parse_coordinates(coords_str: str) -> SkyCoord:
    """Parses a coordinate string into an astropy.coordinates.SkyCoord object."""
    try:
        if ',' in coords_str and ('h' in coords_str or 'd' in coords_str or ':' in coords_str):
            # Assume ICRS RA, Dec string if it contains common separators
            return SkyCoord(coords_str, frame='icrs', unit=(u.hourangle, u.deg))
        elif len(coords_str.split()) == 2: # Potentially decimal degrees
            try:
                ra, dec = map(float, coords_str.split())
                return SkyCoord(ra, dec, frame='icrs', unit='deg')
            except ValueError:
                pass # Fall through to general parsing
        # Let SkyCoord try its best
        return SkyCoord.from_name(coords_str) # Try as object name first
    except Exception: # If from_name fails, try as coordinates
        try:
            return SkyCoord(coords_str, frame='icrs', unit=(u.deg, u.deg)) # Default to deg, deg
        except Exception as e:
            console.print(f"[bold red]Error parsing coordinates '{coords_str}': {e}[/bold red]")
            console.print("[yellow]Hint: Try 'M31', '10.68h +41.26d', or '160.32 41.45'.[/yellow]")
            raise typer.Exit(code=1)


def parse_constraints_list(constraints_list: Optional[List[str]]) -> Optional[dict]:
    """
    Parses a list of 'column=condition' strings into a dictionary.
    e.g., ["Vmag=<10", "B-V=0.5..1.0"] -> {"Vmag": "<10", "B-V": "0.5..1.0"}
    """
    if not constraints_list:
        return None
    parsed_constraints = {}
    for item in constraints_list:
        if '=' not in item:
            console.print(f"[bold red]Invalid constraint format: '{item}'. Expected 'column=condition'.[/bold red]")
            raise typer.Exit(code=1)
        key, value = item.split('=', 1)
        parsed_constraints[key.strip()] = value.strip()
    return parsed_constraints

VIZIER_SERVERS = {
    "vizier_cds": "https://vizier.cds.unistra.fr/viz-bin/",
    "vizier_eso": "https://vizier.eso.org/viz-bin/",
    "vizier_nao": "https://vizier.nao.ac.jp/viz-bin/",
    "vizier_adac": "https://vizier.china-vo.org/viz-bin/",
    # Add more if known and relevant
}

# --- CLI Commands ---

@app.command(name="find-catalogs", help="Find VizieR catalogs based on keywords, UCDs, or source names.")
def find_catalogs(
    keywords: Optional[List[str]] = typer.Option(None, "--keyword", "-k", help="Keyword(s) to search for in catalog descriptions."),
    ucd: Optional[str] = typer.Option(None, help="UCD (Unified Content Descriptor) to filter catalogs."),
    source_name: Optional[str] = typer.Option(None, "--source", help="Source name or pattern (e.g., 'Gaia DR3', '2MASS')."),
    # Other parameters from Vizier.find_catalogs can be added here
    max_catalogs: int = typer.Option(20, help="Maximum number of catalogs to list."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table."),
    vizier_server: str = typer.Option(
        "vizier_cds",
        help=f"VizieR server to use. Choices: {list(VIZIER_SERVERS.keys())}",
        autocompletion=lambda: list(VIZIER_SERVERS.keys())
    )
):
    """
    Lists VizieR catalogs matching the given criteria.
    Use this to discover catalog identifiers (e.g., 'I/261/gaiadr3', 'J/ApJ/710/1776').
    """
    console.print(f"[cyan]Searching for VizieR catalogs...[/cyan]")
    vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
    console.print(f"[dim]Using VizieR server: {vizier_conf.server}[/dim]")

    query_params = {}
    if keywords:
        query_params['keywords'] = keywords
        console.print(f"[dim]Keywords: {keywords}[/dim]")
    if ucd:
        query_params['ucd'] = ucd
        console.print(f"[dim]UCD: {ucd}[/dim]")
    if source_name:
        query_params['source_name'] = source_name
        console.print(f"[dim]Source Name: {source_name}[/dim]")

    if not query_params:
        console.print("[yellow]Please provide at least one search criterion (keyword, ucd, or source name).[/yellow]")
        console.print("Example: `aq vizier find-catalogs --keyword photometry --keyword M31`")
        raise typer.Exit(code=1)

    try:
        result_tables = Vizier.find_catalogs(**query_params) # Returns a TableList with one table
        if result_tables:
            display_table(
                result_tables[0],
                title="Found VizieR Catalogs",
                max_rows=max_catalogs,
                show_all_columns=show_all_columns
            )
        else:
            console.print("[yellow]No catalogs found matching your criteria.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, "VizieR find_catalogs")
        raise typer.Exit(code=1)


@app.command(name="query-object", help="Query catalogs around an object name or specific coordinates.")
def query_object(
    target: str = typer.Argument(..., help="Object name (e.g., 'M31') or coordinates (e.g., '10.68h +41.26d' or '160.32 41.45')."),
    radius: str = typer.Option("2arcmin", help="Search radius (e.g., '5arcmin', '0.1deg')."),
    catalogs: List[str] = typer.Option(..., "--catalog", "-c", help="VizieR catalog identifier(s) (e.g., 'I/261/gaiadr3', 'J/ApJ/710/1776'). Can be specified multiple times."),
    columns: Optional[List[str]] = typer.Option(None, "--col", help="Specific columns to retrieve (e.g., 'RAJ2000', 'DEJ2000', 'pmRA'). Use 'all' for all columns. Can be specified multiple times."),
    column_filters: Optional[List[str]] = typer.Option(None, "--filter", help="Column filters (e.g., 'Imag<15', 'B-V>0.5'). Can be specified multiple times. Format: 'column_name<operator>value'."),
    row_limit: int = typer.Option(vizier_conf.row_limit, help="Maximum number of rows to return per catalog."),
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display per table. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table."),
    vizier_server: str = typer.Option(
        "vizier_cds",
        help=f"VizieR server to use. Choices: {list(VIZIER_SERVERS.keys())}",
        autocompletion=lambda: list(VIZIER_SERVERS.keys())
    )
):
    """
    Queries VizieR catalogs for sources around a given celestial object or coordinate.
    Use `aq vizier find-catalogs` to discover catalog identifiers.
    """
    console.print(f"[cyan]Querying VizieR for object '{target}' in catalog(s): {', '.join(catalogs)}...[/cyan]")
    vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
    vizier_conf.row_limit = row_limit
    console.print(f"[dim]Using VizieR server: {vizier_conf.server}, Row limit: {row_limit}[/dim]")

    coords = parse_coordinates(target)
    rad_quantity = parse_angle_str_to_quantity(radius)

    viz = Vizier(columns=columns if columns else ["*"], catalog=catalogs, column_filters=column_filters, row_limit=row_limit)

    try:
        result_tables = viz.query_object(
            object_name_or_coordinates=coords,
            radius=rad_quantity,
            # catalog=catalogs, # Now set in Vizier constructor
            # columns=columns if columns else ["*"], # Now set in Vizier constructor
            # column_filters=column_filters # Now set in Vizier constructor
        )

        if not result_tables:
            console.print("[yellow]No results returned from VizieR for this query.[/yellow]")
            return

        for table_name, table_data in result_tables.items():
            if table_data is not None and len(table_data) > 0:
                display_table(
                    table_data,
                    title=f"Results from {table_name} for {target}",
                    max_rows=max_rows_display,
                    show_all_columns=show_all_columns
                )
            else:
                console.print(f"[yellow]No data found in catalog '{table_name}' for the given criteria.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, f"VizieR query_object for {target}")
        raise typer.Exit(code=1)


@app.command(name="query-region", help="Query catalogs within a sky region (cone or box).")
def query_region(
    coordinates: str = typer.Argument(..., help="Central coordinates for the region (e.g., '10.68h +41.26d' or '160.32 41.45')."),
    radius: Optional[str] = typer.Option(None, help="Cone search radius (e.g., '5arcmin', '0.1deg'). Use if not specifying width/height."),
    width: Optional[str] = typer.Option(None, help="Width of a box region (e.g., '10arcmin', '0.5deg'). Requires --height."),
    height: Optional[str] = typer.Option(None, help="Height of a box region (e.g., '10arcmin', '0.5deg'). Requires --width."),
    catalogs: List[str] = typer.Option(..., "--catalog", "-c", help="VizieR catalog identifier(s). Can be specified multiple times."),
    columns: Optional[List[str]] = typer.Option(None, "--col", help="Specific columns to retrieve. Use 'all' for all columns. Can be specified multiple times."),
    column_filters: Optional[List[str]] = typer.Option(None, "--filter", help="Column filters (e.g., 'Imag<15'). Can be specified multiple times."),
    row_limit: int = typer.Option(vizier_conf.row_limit, help="Maximum number of rows to return per catalog."),
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display per table. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table."),
    vizier_server: str = typer.Option(
        "vizier_cds",
        help=f"VizieR server to use. Choices: {list(VIZIER_SERVERS.keys())}",
        autocompletion=lambda: list(VIZIER_SERVERS.keys())
    )
):
    """
    Queries VizieR catalogs for sources within a specified sky region.
    Specify either `radius` for a cone search, or both `width` and `height` for a box search.
    """
    console.print(f"[cyan]Querying VizieR region around '{coordinates}' in catalog(s): {', '.join(catalogs)}...[/cyan]")
    vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
    vizier_conf.row_limit = row_limit
    console.print(f"[dim]Using VizieR server: {vizier_conf.server}, Row limit: {row_limit}[/dim]")

    coords_obj = parse_coordinates(coordinates)
    rad_quantity = parse_angle_str_to_quantity(radius)
    width_quantity = parse_angle_str_to_quantity(width)
    height_quantity = parse_angle_str_to_quantity(height)

    if rad_quantity and (width_quantity or height_quantity):
        console.print("[bold red]Error: Specify either --radius (for cone search) OR (--width and --height) (for box search), not both.[/bold red]")
        raise typer.Exit(code=1)
    if (width_quantity and not height_quantity) or (not width_quantity and height_quantity):
        console.print("[bold red]Error: For a box search, both --width and --height must be specified.[/bold red]")
        raise typer.Exit(code=1)
    if not rad_quantity and not (width_quantity and height_quantity):
        console.print("[bold red]Error: You must specify search dimensions: either --radius OR (--width and --height).[/bold red]")
        raise typer.Exit(code=1)

    viz = Vizier(columns=columns if columns else ["*"], catalog=catalogs, column_filters=column_filters, row_limit=row_limit)

    try:
        result_tables = viz.query_region(
            coordinates=coords_obj,
            radius=rad_quantity,
            width=width_quantity,
            height=height_quantity,
            # catalog=catalogs, # Now set in Vizier constructor
            # columns=columns if columns else ["*"], # Now set in Vizier constructor
            # column_filters=column_filters # Now set in Vizier constructor
        )

        if not result_tables:
            console.print("[yellow]No results returned from VizieR for this query.[/yellow]")
            return

        for table_name, table_data in result_tables.items():
            if table_data is not None and len(table_data) > 0:
                display_table(
                    table_data,
                    title=f"Results from {table_name} for region around {coordinates}",
                    max_rows=max_rows_display,
                    show_all_columns=show_all_columns
                )
            else:
                console.print(f"[yellow]No data found in catalog '{table_name}' for the given criteria.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, f"VizieR query_region for {coordinates}")
        raise typer.Exit(code=1)


@app.command(name="query-constraints", help="Query catalogs based on specific column constraints or keywords.")
def query_constraints(
    catalogs: List[str] = typer.Option(..., "--catalog", "-c", help="VizieR catalog identifier(s). Can be specified multiple times."),
    constraints: Optional[List[str]] = typer.Option(None, "--constraint", help="Constraints on column values (e.g., 'Vmag=<10', 'B-V=0.5..1.0'). Can be specified multiple times. Format: 'column_name=condition'."),
    keywords: Optional[List[str]] = typer.Option(None, "--keyword", "-k", help="Keywords to filter results within the catalog (different from finding catalogs)."),
    columns: Optional[List[str]] = typer.Option(None, "--col", help="Specific columns to retrieve. Use 'all' for all columns. Can be specified multiple times."),
    row_limit: int = typer.Option(vizier_conf.row_limit, help="Maximum number of rows to return per catalog."),
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display per table. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table."),
    vizier_server: str = typer.Option(
        "vizier_cds",
        help=f"VizieR server to use. Choices: {list(VIZIER_SERVERS.keys())}",
        autocompletion=lambda: list(VIZIER_SERVERS.keys())
    )
):
    """
    Queries VizieR catalogs using general constraints on column values or keywords.
    This is the most flexible way to query VizieR.
    Constraints should be provided as 'column_name=condition', e.g., --constraint "Vmag=<10".
    """
    console.print(f"[cyan]Querying VizieR with constraints in catalog(s): {', '.join(catalogs)}...[/cyan]")
    vizier_conf.server = VIZIER_SERVERS.get(vizier_server.lower(), vizier_conf.server)
    vizier_conf.row_limit = row_limit
    console.print(f"[dim]Using VizieR server: {vizier_conf.server}, Row limit: {row_limit}[/dim]")

    parsed_constraints = parse_constraints_list(constraints)
    if not parsed_constraints and not keywords:
        console.print("[yellow]Please provide at least --constraint(s) or --keyword(s) for this query type.[/yellow]")
        raise typer.Exit(code=1)

    # For query_constraints, it seems better to pass catalog directly to the method
    # rather than initializing Vizier with it, especially if a user queries multiple catalogs
    # where constraints might apply differently or are only relevant to some.
    # However, astroquery.Vizier.query_constraints expects `self.catalog` to be set
    # or `catalog` kwarg to be a string (not list).
    # So, we will iterate if multiple catalogs are given.

    query_kwargs = {}
    if parsed_constraints:
        query_kwargs.update(parsed_constraints)
        console.print(f"[dim]Using constraints: {query_kwargs}[/dim]")
    if keywords:
        query_kwargs['keywords'] = " ".join(keywords) # astroquery expects space-separated string
        console.print(f"[dim]Using keywords: {query_kwargs['keywords']}[/dim]")


    viz = Vizier(columns=columns if columns else ["*"], row_limit=row_limit)
    # Vizier.query_constraints doesn't directly take a `catalog` list argument like query_object/region
    # It uses self.catalog. So we might need to loop or ensure it works as expected.
    # According to docs, self.catalog can be a list for the constructor.

    try:
        # If Vizier is initialized with a list of catalogs, query_constraints should ideally work.
        # Let's test this behavior. If not, we'll need to loop.
        viz.catalog = catalogs # Set the catalogs for this specific query
        result_tables = viz.query_constraints(**query_kwargs)

        if not result_tables:
            console.print("[yellow]No results returned from VizieR for this query.[/yellow]")
            return

        for table_name, table_data in result_tables.items():
            if table_data is not None and len(table_data) > 0:
                display_table(
                    table_data,
                    title=f"Constraint Query Results from {table_name}",
                    max_rows=max_rows_display,
                    show_all_columns=show_all_columns
                )
            else:
                console.print(f"[yellow]No data found in catalog '{table_name}' for the given criteria.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, f"VizieR query_constraints")
        raise typer.Exit(code=1)
