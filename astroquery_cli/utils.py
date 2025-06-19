from typing import Optional, Dict, Any
import functools

import typer
from astropy.table import Table as AstropyTable
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console
from rich.table import Table as RichTable
from rich.padding import Padding
import shutil
import os
import re
import builtins
import astroquery_cli.i18n as i18n
from pyvo.dal.tap import TAPResults # Import TAPResults

console = Console()

def add_common_fields(ctx: typer.Context, simbad_instance):
    lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
    fields = ["otype", "sptype", "flux(V)", "flux(B)", "flux(J)", "flux(H)", "flux(K)", "flux(G)"]
    for field in fields:
        simbad_instance.add_votable_fields(field)

def is_narrow_terminal(ctx: typer.Context, min_width=100):
    lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
    terminal_size = shutil.get_terminal_size((80, 20))
    return terminal_size.columns < min_width

def suggest_web_view(ctx: typer.Context, result_url: str, reason: str = ""):
    lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
    suggestion = builtins._('Terminal too narrow or content too complex, please open in browser:')
    if reason:
        console.print(f"[cyan]{reason}[/cyan]")
    console.print(f"[bold green]{suggestion}[/bold green]\n[blue underline]{result_url}[/blue underline]")
    try:
        import webbrowser
        webbrowser.open_new_tab(result_url)
    except Exception:
        pass

def parse_coordinates(ctx: typer.Context, coords_str: str) -> Optional[SkyCoord]:
    """
    Parses a coordinate string into an Astropy SkyCoord object.
    Handles various common formats including decimal degrees and HMS/DMS.
    """
    if not coords_str:
        console.print("[bold red]Error: Coordinate string cannot be empty.[/bold red]")
        raise typer.Exit(code=1)
    try:
        if re.match(r"^\s*[\d\.\-+]+\s+[\d\.\-+]+\s*$", coords_str):
             parts = coords_str.split()
             if len(parts) == 2:
                 return SkyCoord(ra=float(parts[0]), dec=float(parts[1]), unit=(u.deg, u.deg), frame='icrs')
        return SkyCoord(coords_str, frame='icrs')
    except Exception as e1:
        # Do not exit here, just print error and return None
        console.print(f"[bold red]Error: Could not parse coordinates '{coords_str}'.[/bold red]")
        console.print(f"[yellow]Details: {e1}[/yellow]")
        console.print(f"[yellow]Ensure format is recognized by Astropy (e.g., '10.68h +41.26d', '10d30m0s 20d0m0s', '150.0 2.0' for deg).[/yellow]")
        return None

def parse_angle_str_to_quantity(ctx: typer.Context, angle_str: str) -> u.Quantity:
    """
    Parses a string representing an angle with units (e.g., "10arcsec", "0.5deg")
    into an astropy Quantity object.
    """
    if not angle_str:
        console.print("[bold red]Error: Angle string cannot be empty.[/bold red]")
        raise typer.Exit(code=1)
    try:
        original_str = angle_str
        angle_str = angle_str.lower().strip()

        replacements = {
            "degrees": "deg", "degree": "deg",
            "arcminutes": "arcmin", "arcminute": "arcmin",
            "arcseconds": "arcsec", "arcsecond": "arcsec",
        }
        for full, abb in replacements.items():
            if angle_str.endswith(full):
                angle_str = angle_str.replace(full, abb)
                break

        match = re.match(r"([+-]?\d*\.?\d+)\s*([a-z]+)", angle_str, re.IGNORECASE)
        if match:
            value_str, unit_str = match.groups()
            value = float(value_str)
            try:
                unit = u.Unit(unit_str)
                if unit.physical_type == 'angle':
                    return u.Quantity(value, unit)
                else:
                    console.print(f"[bold red]Error: Invalid unit '{unit_str}' for an angle in '{original_str}'. Must be an angular unit.[/bold red]")
                    raise typer.Exit(code=1)
            except ValueError:
                console.print(f"[bold red]Error: Unknown unit '{unit_str}' in angle string '{original_str}'.[/bold red]")
                console.print(f"[yellow]Use common units like 'deg', 'arcmin', 'arcsec'.[/yellow]")
                raise typer.Exit(code=1)
        else:
            try:
                q = u.Quantity(original_str)
                if q.unit.physical_type == 'angle':
                    return q
                else:
                    console.print(f"[bold red]Error: Value '{original_str}' parsed but is not an angle.[/bold red]")
                    raise typer.Exit(code=1)
            except Exception:
                console.print(f"[bold red]Error: Could not parse angle string '{original_str}'.[/bold red]")
                console.print(f"[yellow]Please provide a value and an angular unit (e.g., '10arcsec', '0.5 deg', '15 arcmin').[/yellow]")
                raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[bold red]Error parsing angle string '{angle_str}': {e}[/bold red]")
        raise typer.Exit(code=1)

def display_table(
    ctx: typer.Context,
    astro_table: Optional[AstropyTable],
    title: str = "",
    max_rows: int = 20,
    show_all_columns: bool = False,
    max_col_width: Optional[int] = 30
):
    lang = ctx.obj.get("lang", "en") if ctx.obj else "en"

    # Convert TAPResults to AstropyTable if necessary
    if isinstance(astro_table, TAPResults):
        try:
            astro_table = astro_table.to_table()
        except Exception as e:
            console.print(f"[bold red]Error converting TAPResults to AstropyTable: {e}[/bold red]")
            # If conversion fails, we can't proceed with displaying as AstropyTable
            # A fallback could be to print raw TAPResults or exit
            console.print(f"[yellow]Cannot display results. Raw TAPResults object: {astro_table}[/yellow]")
            return

    # If astro_table is a list of lists, convert it to an AstropyTable
    if isinstance(astro_table, list) and all(isinstance(row, list) for row in astro_table):
        if not astro_table:
            console.print(Padding(f"[yellow]No data returned for '{title if title else 'query'}'.[/yellow]", (0,2)))
            return
        # Assume the first row contains headers if it's a list of lists
        # Or, if it's a simple key-value pair list, create generic headers
        if all(len(row) == 2 for row in astro_table):
            # This is likely a key-value pair list from dict_to_table_rows
            headers = ["Field", "Value"]
        else:
            # For other list of lists, try to infer headers or use generic ones
            headers = [f"Column {i+1}" for i in range(len(astro_table[0]))]
        
        try:
            astro_table = AstropyTable(rows=astro_table, names=headers)
        except Exception as e:
            console.print(f"[bold red]Error converting list to AstropyTable: {e}[/bold red]")
            # Fallback to just printing rows if conversion fails
            rich_table = RichTable(title=title, show_lines=True, header_style="bold magenta", expand=False)
            for h in headers:
                rich_table.add_column(h, overflow="fold" if max_col_width else "ellipsis", max_width=max_col_width if max_col_width and max_col_width > 0 else None)
            for row_data in astro_table:
                rich_table.add_row(*[str(item) for item in row_data])
            console.print(rich_table)
            console.print(Padding(f"Total rows: {len(astro_table)}", (0,2)))
            return

    if astro_table is None or len(astro_table) == 0:
        console.print(Padding(f"[yellow]No data returned for '{title if title else 'query'}'.[/yellow]", (0,2)))
        return

    rich_table = RichTable(title=title, show_lines=True, header_style="bold magenta", expand=False)

    displayed_columns = astro_table.colnames
    
    # If show_all_columns is True, bypass all column limiting
    if show_all_columns:
        pass # Display all columns
    elif is_narrow_terminal(ctx):
        # If narrow, only show the 'name' column for mission lists
        if 'name' in displayed_columns and 'description' in displayed_columns:
            console.print(f"[yellow]{builtins._('Terminal is narrow. Displaying only mission names for brevity. Use --show-all-cols to see descriptions.')}[/yellow]")
            displayed_columns = ['name']
        else: # If not mission list, or no description, still limit to 10 if not show_all_columns
            console.print(f"[cyan]Table has {len(astro_table.colnames)} columns. Displaying first 10. Use --show-all-cols to see all.[/cyan]")
            displayed_columns = astro_table.colnames[:10]
    else:
        # If not narrow, and there are many columns, still limit unless --show-all-cols is used
        if len(astro_table.colnames) > 10:
            console.print(f"[cyan]Table has {len(astro_table.colnames)} columns. Displaying first 10. Use --show-all-cols to see all.[/cyan]")
            displayed_columns = astro_table.colnames[:10]

    for col_name in displayed_columns:
        # Apply max_col_width only if it's not the 'description' column and max_col_width is set
        if col_name == 'description':
            rich_table.add_column(col_name, overflow="fold")
        else:
            rich_table.add_column(col_name, overflow="fold" if max_col_width else "ellipsis", max_width=max_col_width if max_col_width and max_col_width > 0 else None)

    num_rows_to_display = len(astro_table)
    show_ellipsis = False
    # Removed DEFAULT_HARD_LIMIT as it was causing truncation even with -1

    if max_rows == -1:
        num_rows_to_display = len(astro_table) # Display all rows if -1
    elif max_rows > 0 and len(astro_table) > max_rows:
        num_rows_to_display = max_rows
        show_ellipsis = True
    else:
        num_rows_to_display = len(astro_table)

    for i in range(num_rows_to_display):
        row = astro_table[i]
        rich_table.add_row(*[str(row[item_name]) for item_name in displayed_columns])

    console.print(rich_table)
    if show_ellipsis:
        # Adjusted message for hard limit vs. user-specified limit
        if max_rows == -1: # Hard limit was applied
            console.print(f"... and {len(astro_table) - num_rows_to_display} more rows. To display all, use --max-rows-display {len(astro_table)} or a sufficiently large number.")
        else: # User-specified limit was applied
            console.print(f"... and {len(astro_table) - max_rows} more rows. Use --max-rows-display -1 to display all rows.")
    console.print(Padding(f"Total rows: {len(astro_table)}", (0,2)))

def handle_astroquery_exception(ctx: typer.Context, e: Exception, service_name: str):
    lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
    console.print(f"[bold red]Error querying {service_name}:[/bold red]")
    import traceback
    console.print(f"[yellow][debug] type(e): {type(e)}[/yellow]")
    console.print(f"[yellow][debug] e: {e}[/yellow]")
    console.print(f"[yellow][debug] ctx: {ctx}[/yellow]")
    console.print(f"[yellow][debug] ctx.params: {getattr(ctx, 'params', None)}[/yellow]")
    console.print(f"[yellow][debug] traceback:[/yellow]")
    console.print("".join(traceback.format_exception(type(e), e, e.__traceback__)))
    try:
        console.print(f"{type(e).__name__}: {e}")
    except KeyError as ke:
        console.print(f"[red]KeyError in error message: {ke}. Some translation or error string is missing a key.[/red]")
        console.print(f"[red]Original exception type: {type(e).__name__}[/red]")
        console.print(f"[red]ctx.params: {getattr(ctx, 'params', None)}[/red]")
        if hasattr(e, '__traceback__'):
            console.print("[red]Traceback:[/red]")
            console.print("".join(traceback.format_tb(e.__traceback__)))
    except Exception as ee:
        console.print(f"[red]Unexpected error in error handler: {ee}[/red]")
        console.print(f"[red]ctx.params: {getattr(ctx, 'params', None)}[/red]")
    # 打印异常链，便于定位隐藏的 format 错误
    if hasattr(e, '__context__') and e.__context__:
        console.print(f"[dim]Exception context: {type(e.__context__).__name__}: {e.__context__}[/dim]")
    if hasattr(e, '__cause__') and e.__cause__:
        console.print(f"[dim]Exception cause: {type(e.__cause__).__name__}: {e.__cause__}[/dim]")
    if hasattr(e, 'response') and e.response is not None:
        try:
            content = e.response.text
            if "Error" in content or "Fail" in content or "ERROR" in content:
                console.print(f"[italic]Server response details: {content[:500]}...[/italic]")
        except Exception:
            pass

common_output_options = {
    "output_file": typer.Option(
        None,
        "--output-file",
        "-o",
        help=builtins._("Path to save the output table (e.g., data.csv, results.ecsv, table.fits). Format inferred from extension.")
    ),
    "output_format": typer.Option(
        None,
        "--output-format",
        "-f",
        help=builtins._("Astropy table format for saving (e.g., 'csv', 'ecsv', 'fits', 'votable'). Overrides inference from filename extension.")
    ),
}

def save_table_to_file(ctx: typer.Context, table: AstropyTable, output_file: str, output_format: Optional[str], query_type: str):
    lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
    if not output_file:
        return
    filename = os.path.expanduser(output_file)
    file_format = output_format
    if not file_format:
        _, ext = os.path.splitext(filename)
        if ext:
            file_format = ext[1:].lower()
        else:
            file_format = 'ecsv'
            filename += f".{file_format}"
            console.print(f"[yellow]No file extension or format specified, saving as '{filename}' (ECSV format).[/yellow]")

    console.print(f"[cyan]Saving {query_type} results to '{filename}' as {file_format}...[/cyan]")
    try:
        if file_format in ['pickle', 'pkl']:
             import pickle
             with open(filename, 'wb') as f:
                 pickle.dump(table, f)
        else:
            table.write(filename, format=file_format, overwrite=True)
        console.print(f"[green]Successfully saved to '{filename}'.[/green]")
    except Exception as e:
        console.print(f"[bold red]Error saving table to '{filename}' (format: {file_format}): {e}[/bold red]")
        if "No writer defined for format" in str(e) or "Unknown format" in str(e):
            available_formats = list(AstropyTable.write.formats.keys())
            console.print(f"[yellow]Tip: Ensure the format '{file_format}' is supported by Astropy.[/yellow]")
            console.print(f"[yellow]Available astropy table write formats include: {', '.join(available_formats)}[/yellow]")
        elif file_format not in AstropyTable.write.formats and file_format not in ['pickle', 'pkl']:
             console.print(f"[yellow]Available astropy table write formats: {list(AstropyTable.write.formats.keys())}[/yellow]")

def global_keyboard_interrupt_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            from rich.console import Console
            from astroquery_cli import i18n
            _ = i18n.get_translator()
            console = Console()
            console.print(f"[bold yellow]{_('User interrupted the query. Exiting safely.')}[bold yellow]")
            import os
            os._exit(130)
    return wrapper
