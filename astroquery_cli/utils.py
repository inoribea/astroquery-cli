from typing import Optional, Dict, Any

import typer
from astropy.table import Table as AstropyTable
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console
from rich.table import Table as RichTable
from rich.padding import Padding
import os
import re

console = Console()

def parse_coordinates(coords_str: str) -> Optional[SkyCoord]:
    """
    Parses a coordinate string into an Astropy SkyCoord object.
    Handles various common formats including decimal degrees and HMS/DMS.
    """
    if not coords_str:
        console.print("[bold red]Error: Coordinate string cannot be empty.[/bold red]")
        raise typer.Exit(code=1)
    try:
        # Try parsing directly with SkyCoord, which handles many formats
        # including decimal degrees and HMS/DMS if separated by space
        # and units are implicitly understood or common (deg for decimal)
        if re.match(r"^\s*[\d\.\-+]+\s+[\d\.\-+]+\s*$", coords_str): # Likely decimal degrees
             parts = coords_str.split()
             if len(parts) == 2:
                 return SkyCoord(ra=float(parts[0]), dec=float(parts[1]), unit=(u.deg, u.deg), frame='icrs')
        return SkyCoord(coords_str, frame='icrs')
    except Exception as e1:
        console.print(f"[bold red]Error: Could not parse coordinates '{coords_str}'.[/bold red]")
        console.print(f"[yellow]Details: {e1}[/yellow]")
        console.print(f"[yellow]Ensure format is recognized by Astropy (e.g., '10.68h +41.26d', '10d30m0s 20d0m0s', '150.0 2.0' for deg).[/yellow]")
        raise typer.Exit(code=1)

def parse_angle_str_to_quantity(angle_str: str) -> u.Quantity:
    """
    Parses a string representing an angle with units (e.g., "10arcsec", "0.5deg")
    into an astropy Quantity object.
    """
    if not angle_str:
        console.print("[bold red]Error: Angle string cannot be empty.[/bold red]")
        raise typer.Exit(code=1)
    try:
        # Common units and their abbreviations for parsing
        # Astropy's u.Quantity.from_string is quite good but can be strict.
        # This helper tries to make it more robust for common CLI inputs.
        original_str = angle_str
        angle_str = angle_str.lower().strip()

        # Replace common full names with astropy abbreviations if Quantity struggles
        replacements = {
            "degrees": "deg", "degree": "deg",
            "arcminutes": "arcmin", "arcminute": "arcmin",
            "arcseconds": "arcsec", "arcsecond": "arcsec",
        }
        for full, abb in replacements.items():
            if angle_str.endswith(full):
                angle_str = angle_str.replace(full, abb)
                break # Avoid multiple replacements like arcsecond -> arcsec -> arcsec

        # Separate number and unit
        match = re.match(r"([+-]?\d*\.?\d+)\s*([a-z]+)", angle_str, re.IGNORECASE)
        if match:
            value_str, unit_str = match.groups()
            value = float(value_str)
            # Check if unit_str is a valid astropy unit
            try:
                unit = u.Unit(unit_str)
                if unit.physical_type == 'angle':
                    return u.Quantity(value, unit)
                else:
                    console.print(f"[bold red]Error: Invalid unit '{unit_str}' for an angle in '{original_str}'. Must be an angular unit.[/bold red]")
                    raise typer.Exit(code=1)
            except ValueError: # If u.Unit(unit_str) fails
                console.print(f"[bold red]Error: Unknown unit '{unit_str}' in angle string '{original_str}'.[/bold red]")
                console.print(f"[yellow]Use common units like 'deg', 'arcmin', 'arcsec'.[/yellow]")
                raise typer.Exit(code=1)
        else: # If regex doesn't match (e.g., no unit provided, or malformed)
            # Try parsing directly with astropy, it might catch some cases
            try:
                q = u.Quantity(original_str)
                if q.unit.physical_type == 'angle':
                    return q
                else:
                    console.print(f"[bold red]Error: Value '{original_str}' parsed but is not an angle.[/bold red]")
                    raise typer.Exit(code=1)
            except Exception: # Catch broad exception from Quantity parsing
                console.print(f"[bold red]Error: Could not parse angle string '{original_str}'.[/bold red]")
                console.print(f"[yellow]Please provide a value and an angular unit (e.g., '10arcsec', '0.5 deg', '15 arcmin').[/yellow]")
                raise typer.Exit(code=1)

    except Exception as e: # General fallback, though specific errors above should handle most
        console.print(f"[bold red]Error parsing angle string '{angle_str}': {e}[/bold red]")
        raise typer.Exit(code=1)


def display_table(
    astro_table: Optional[AstropyTable],
    title: str = "",
    max_rows: int = 20,
    show_all_columns: bool = False,
    max_col_width: Optional[int] = 30
):
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
    if max_rows > 0 and len(astro_table) > max_rows : # Check max_rows > 0 for "show all"
        num_rows_to_display = max_rows
        show_ellipsis = True

    for i in range(num_rows_to_display):
        row = astro_table[i]
        rich_table.add_row(*[str(row[item_name]) for item_name in displayed_columns])

    console.print(rich_table)
    if show_ellipsis:
        console.print(f"... and {len(astro_table) - max_rows} more rows. Use --max-rows -1 to display all rows.")
    console.print(Padding(f"Total rows: {len(astro_table)}", (0,2)))

def handle_astroquery_exception(e: Exception, service_name: str):
    console.print(f"[bold red]Error querying {service_name}:[/bold red]")
    console.print(f"{type(e).__name__}: {e}")
    if hasattr(e, 'response') and e.response is not None:
        try:
            content = e.response.text
            if "Error" in content or "Fail" in content or "ERROR" in content: # Added ERROR for TAP query errors
                 console.print(f"[italic]Server response details: {content[:500]}...[/italic]")
        except Exception:
            pass

common_output_options: Dict[str, Any] = {
    "output_file": typer.Option(None, "--output-file", "-o", help="Path to save the output table (e.g., data.csv, results.ecsv, table.fits). Format inferred from extension."),
    "output_format": typer.Option(None, "--output-format", "-f", help="Astropy table format for saving (e.g., 'csv', 'ecsv', 'fits', 'votable'). Overrides inference from filename extension."),
    # max_rows and show_all_columns are display-specific, so they are usually defined per command
    # However, if you want them to be truly "common output options" for saving behavior,
    # they could be here, but their primary use is for `display_table`.
    # For now, I'll keep them in the command definitions for display control.
}

def save_table_to_file(table: AstropyTable, output_file: str, output_format: Optional[str], query_type: str):
    if not output_file:
        return
    filename = os.path.expanduser(output_file)
    file_format = output_format
    if not file_format:
        _, ext = os.path.splitext(filename)
        if ext:
            file_format = ext[1:].lower() # ensure lowercase for matching
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
        # Check if it's an astropy unknown format error
        if "No writer defined for format" in str(e) or "Unknown format" in str(e):
            available_formats = list(AstropyTable.write.formats.keys())
            console.print(f"[yellow]Tip: Ensure the format '{file_format}' is supported by Astropy.[/yellow]")
            console.print(f"[yellow]Available astropy table write formats include: {', '.join(available_formats)}[/yellow]")
        elif file_format not in AstropyTable.write.formats and file_format not in ['pickle', 'pkl']:
             console.print(f"[yellow]Available astropy table write formats: {list(AstropyTable.write.formats.keys())}[/yellow]")

