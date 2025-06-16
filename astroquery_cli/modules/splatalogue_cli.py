import typer
from typing import Optional, List, Tuple
from astropy.table import Table as AstropyTable
import astropy.units as u
from astropy.constants import c
from astroquery.splatalogue import Splatalogue
from ..i18n import get_translator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    global_keyboard_interrupt_handler,
)
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout
from astroquery_cli.common_options import setup_debug_context # Import setup_debug_context

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="splatalogue",
        help=builtins._("Query the Splatalogue spectral line database."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def splatalogue_callback(
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

    SPLATALOGUE_FIELDS = [
        "Object Name",
        "Type",
        "RA(deg)",
        "DEC(deg)",
        "Redshift",
        "Photometry",
        "References",
    ]

    Splatalogue.TIMEOUT = 120

    def parse_range(range_str: str, unit_type: str) -> Tuple[u.Quantity, u.Quantity]:
        parts = range_str.split('-')
        if len(parts) != 2:
            if unit_type == "wavelength":
                console.print(_("[red]Error: Wavelength range '{range_str}' must be in 'min-max' format (e.g., '100um-200um').[/red]").format(range_str=range_str))
            else:
                console.print(_("[red]Error: Frequency range '{range_str}' must be in 'min-max' format (e.g., '100GHz-110GHz').[/red]").format(range_str=range_str))
            raise typer.Exit(code=1)
        try:
            min_val = u.Quantity(parts[0].strip())
            max_val = u.Quantity(parts[1].strip())
            if unit_type == "wavelength":
                if not (min_val.unit.is_equivalent(u.m) and max_val.unit.is_equivalent(u.m)):
                    console.print(_("[red]Error: Wavelengths must have units of length (e.g., um, nm, mm).[/red]"))
                    raise typer.Exit(code=1)
            else:
                if not (min_val.unit.is_equivalent(u.Hz) and max_val.unit.is_equivalent(u.Hz)):
                    console.print(_("[red]Error: Frequencies must have units of frequency (e.g., GHz, MHz).[/red]"))
                    raise typer.Exit(code=1)
            return min_val, max_val
        except Exception as e:
            console.print(_("[red]Error parsing {unit_type} range '{range_str}': {error_message}[/red]").format(unit_type=unit_type, range_str=range_str, error_message=e))
            raise typer.Exit(code=1)

    @app.command(name="lines", help=builtins._("Query spectral lines from Splatalogue by chemical name. Optionally filter by wavelength (-w) or frequency (-f) range."))
    @global_keyboard_interrupt_handler
    def query_lines(ctx: typer.Context,
        chemical_name: str = typer.Argument(
            ...,
            help=(
                builtins._("Chemical name pattern (e.g., 'CO', '%H2O%'). ") +
                builtins._("You can use cent for SQL-like wildcards: ") +
                builtins._("'%CO%' matches any containing CO, ") +
                builtins._("'CO%' matches starting with CO, ") +
                builtins._("'%CO' matches matches ending with CO. ")
            )
        ),
wavelength_range: Optional[str] = typer.Argument(
            None, help=builtins._("Wavelength range (e.g., '100um-200um'). You can directly input this as the second argument without -w. Mutually exclusive with frequency_range.")
        ),
frequency_range: Optional[str] = typer.Argument(
            None, help=builtins._("Frequency range (e.g., '100GHz-110GHz'). You can directly input this as the second argument without -f. Mutually exclusive with wavelength_range.")
        ),
        energy_max: Optional[float] = typer.Option(None, help=builtins._("Maximum energy in K (E_upper).")),
        energy_type: Optional[str] = typer.Option("el", help=builtins._("Energy type ('el' or 'eu' for E_lower or E_upper).")),
        line_strengths: Optional[str] = typer.Option(None, help=builtins._("Line strength units (e.g., 'ls1', 'ls2', 'ls4', 'ls5' for CDMS/JPL or TopModel).")),
        exclude: Optional[List[str]] = typer.Option(None, "--exclude", help=builtins._("Species to exclude (e.g., 'HDO').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = typer.Option(
            None, "--output-format", help=builtins._("Astropy table format for saving (e.g. 'csv', 'ecsv', 'fits', 'votable'). Overrides file extension inference.")
        ),
        max_rows_display: int = typer.Option(50, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        # Mutually exclusive logic for range
        if wavelength_range and frequency_range:
            console.print(_("[red]You cannot specify both -w/--wavelength-range and -f/--frequency-range.[/red]"))
            raise typer.Exit(code=1)

        try:
            min_freq = max_freq = None
            if wavelength_range:
                min_wl, max_wl = parse_range(wavelength_range, "wavelength")
                min_freq = (c / max_wl).to(u.Hz)
                max_freq = (c / min_wl).to(u.Hz)
                console.print("[cyan]Querying Splatalogue for '{chemical_name}' in wavelength range '{wavelength_range}' ({min_freq:.2e}Hz - {max_freq:.2e}Hz)...[/cyan]".format(
                    chemical_name=chemical_name, wavelength_range=wavelength_range, min_freq=min_freq.value, max_freq=max_freq.value))
            elif frequency_range:
                min_freq, max_freq = parse_range(frequency_range, "frequency")
                console.print(_("[cyan]Querying Splatalogue for '{chemical_name}' in frequency range '{frequency_range}'...[/cyan]").format(
                    chemical_name=chemical_name, frequency_range=frequency_range))
            else:
                console.print(_("[red]Error: You must specify a wavelength or frequency range as the second argument (e.g., '100um-200um' or '100GHz-110GHz'). No -w or -f flag is needed; just provide the range directly.[/red]"))
                raise typer.Exit(code=1)

            kwargs = {'chemical_name': chemical_name}
            if energy_max is not None:
                kwargs['energy_max'] = energy_max
                kwargs['energy_type'] = energy_type
            if line_strengths:
                kwargs['line_strengths'] = line_strengths
            if exclude:
                kwargs['exclude'] = exclude

            if min_freq is not None and max_freq is not None:
                result_table: Optional[AstropyTable] = Splatalogue.query_lines(
                    min_frequency=min_freq,
                    max_frequency=max_freq,
                    **kwargs
                )
            else:
                result_table: Optional[AstropyTable] = Splatalogue.query_lines(
                    **kwargs
                )

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} spectral line(s).[/green]").format(count=len(result_table)))
                display_table(ctx, result_table, title=_("Splatalogue Lines"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("Splatalogue line query"))
            else:
                console.print(_("[yellow]No spectral lines found for the given criteria.[/yellow]"))
        except Exception as e:
            if isinstance(e, ValueError) and "No matching chemical species found" in str(e):
                console.print(_("[yellow]No matching chemical species found. Please check your chemical_name pattern and try removing wildcards or using a more specific name.[/yellow]"))
                raise typer.Exit(code=0)
            handle_astroquery_exception(ctx, e, _("Splatalogue lines"))
            raise typer.Exit(code=1)

    @app.command(name="species-table", help=builtins._("Get the table of NRAO recommended species."))
    @global_keyboard_interrupt_handler
    def get_species_table(ctx: typer.Context,
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(50, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        console.print(_("[cyan]Fetching NRAO recommended species table from Splatalogue...[/cyan]"))
        try:
            species_table: Optional[AstropyTable] = Splatalogue.get_species_table()
            if species_table and len(species_table) > 0:
                display_table(ctx, species_table, title=_("Splatalogue NRAO Recommended Species"), max_rows=max_rows_display, show_all_columns=True)
                if output_file:
                    save_table_to_file(ctx, species_table, output_file, output_format, _("Splatalogue species table"))
            else:
                console.print(_("[yellow]Could not retrieve species table or it is empty.[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("Splatalogue species-table"))
            raise typer.Exit(code=1)

    return app
