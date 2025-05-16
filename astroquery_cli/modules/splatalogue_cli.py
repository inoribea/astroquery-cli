import typer
from typing import Optional, List, Tuple
from astropy.table import Table as AstropyTable
import astropy.units as u
from astroquery.splatalogue import Splatalogue
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
)

app = typer.Typer(
    name="splatalogue",
    help="Query the Splatalogue spectral line database."
)

Splatalogue.TIMEOUT = 120 # Splatalogue can be slow

def parse_frequency_range(freq_str: str) -> Tuple[u.Quantity, u.Quantity]:
    parts = freq_str.split('-')
    if len(parts) != 2:
        console.print(f"[red]Error: Frequency range '{freq_str}' must be in 'min-max' format (e.g., '100GHz-110GHz').[/red]")
        raise typer.Exit(code=1)
    try:
        min_freq = u.Quantity(parts[0].strip())
        max_freq = u.Quantity(parts[1].strip())
        if not (min_freq.unit.is_equivalent(u.Hz) and max_freq.unit.is_equivalent(u.Hz)):
            console.print(f"[red]Error: Frequencies must have units of frequency (e.g., GHz, MHz).[/red]")
            raise typer.Exit(code=1)
        return min_freq, max_freq
    except Exception as e:
        console.print(f"[red]Error parsing frequency range '{freq_str}': {e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="query-lines", help="Query spectral lines from Splatalogue.")
def query_lines(
    frequency_range: str = typer.Argument(..., help="Frequency range (e.g., '100GHz-110GHz', '2100MHz-2200MHz')."),
    chemical_name: Optional[str] = typer.Option(None, "--chemical", help="Chemical name pattern (e.g., 'CO', '%H2O%')."),
    energy_max: Optional[float] = typer.Option(None, help="Maximum energy in K (E_upper)."),
    energy_type: Optional[str] = typer.Option("el", help="Energy type ('el' or 'eu' for E_lower or E_upper)."),
    line_strengths: Optional[str] = typer.Option(None, help="Line strength units (e.g., 'ls1', 'ls2', 'ls4', 'ls5' for CDMS/JPL or TopModel)."),
    exclude: Optional[List[str]] = typer.Option(None, "--exclude", help="Species to exclude (e.g., 'HDO')."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(50, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying Splatalogue for lines in range '{frequency_range}'...[/cyan]")
    try:
        min_freq, max_freq = parse_frequency_range(frequency_range)

        kwargs = {}
        if chemical_name:
            kwargs['chemical_name'] = chemical_name
        if energy_max is not None:
            kwargs['energy_max'] = energy_max
            kwargs['energy_type'] = energy_type
        if line_strengths:
            kwargs['line_strengths'] = line_strengths
        if exclude:
            kwargs['exclude'] = exclude

        result_table: Optional[AstropyTable] = Splatalogue.query_lines(
            min_frequency=min_freq,
            max_frequency=max_freq,
            **kwargs
        )

        if result_table and len(result_table) > 0:
            console.print(f"[green]Found {len(result_table)} spectral line(s).[/green]")
            display_table(result_table, title=f"Splatalogue Lines", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "Splatalogue line query")
        else:
            console.print(f"[yellow]No spectral lines found for the given criteria.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "Splatalogue query_lines")
        raise typer.Exit(code=1)

@app.command(name="get-species-table", help="Get the table of NRAO recommended species.")
def get_species_table(
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(50, help="Maximum number of rows to display. Use -1 for all rows."),
):
    console.print("[cyan]Fetching NRAO recommended species table from Splatalogue...[/cyan]")
    try:
        species_table: Optional[AstropyTable] = Splatalogue.get_species_table()
        if species_table and len(species_table) > 0:
            display_table(species_table, title="Splatalogue NRAO Recommended Species", max_rows=max_rows_display, show_all_columns=True)
            if output_file:
                save_table_to_file(species_table, output_file, output_format, "Splatalogue species table")
        else:
            console.print("[yellow]Could not retrieve species table or it is empty.[/yellow]")
    except Exception as e:
        handle_astroquery_exception(e, "Splatalogue get_species_table")
        raise typer.Exit(code=1)

