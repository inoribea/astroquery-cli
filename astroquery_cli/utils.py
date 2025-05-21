from typing import Optional, Dict, Any

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
from astroquery_cli import i18n

builtins._ = i18n._

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
        console.print(f"[bold red]Error: Could not parse coordinates '{coords_str}'.[/bold red]")
        console.print(f"[yellow]Details: {e1}[/yellow]")
        console.print(f"[yellow]Ensure format is recognized by Astropy (e.g., '10.68h +41.26d', '10d30m0s 20d0m0s', '150.0 2.0' for deg).[/yellow]")
        raise typer.Exit(code=1)

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
    if astro_table is None or len(astro_table) == 0:
        console.print(Padding(f"[yellow]No data returned for '{title if title else 'query'}'.[/yellow]", (0,2)))
        return

    rich_table = RichTable(title=title, show_lines=True, header_style="bold magenta", expand=False)

    displayed_columns = astro_table.colnames
    if not show_all_columns and len(astro_table.colnames) > 10:
        console.print(f"[cyan]Table has {len(astro_table.colnames)} columns. Displaying first 10. Use --show-all-columns to see all.[/cyan]")
        displayed_columns = astro_table.colnames[:10]

    for col_name in displayed_columns:
        rich_table.add_column(col_name, overflow="fold" if max_col_width else "ellipsis", max_width=max_col_width if max_col_width and max_col_width > 0 else None)

    num_rows_to_display = len(astro_table)
    show_ellipsis = False
    if max_rows > 0 and len(astro_table) > max_rows :
        num_rows_to_display = max_rows
        show_ellipsis = True

    for i in range(num_rows_to_display):
        row = astro_table[i]
        rich_table.add_row(*[str(row[item_name]) for item_name in displayed_columns])

    console.print(rich_table)
    if show_ellipsis:
        console.print(f"... and {len(astro_table) - max_rows} more rows. Use --max-rows -1 to display all rows.")
    console.print(Padding(f"Total rows: {len(astro_table)}", (0,2)))

def handle_astroquery_exception(ctx: typer.Context, e: Exception, service_name: str):
    lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
    console.print(f"[bold red]Error querying {service_name}:[/bold red]")
    console.print(f"{type(e).__name__}: {e}")
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