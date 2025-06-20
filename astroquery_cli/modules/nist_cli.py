import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.nist import Nist
import astropy.units as u
from ..i18n import get_translator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    global_keyboard_interrupt_handler,
)
import re
from io import StringIO
from contextlib import redirect_stdout
from astroquery_cli.common_options import setup_debug_context
from astroquery_cli.debug import debug

def get_app(_: callable):
    app = typer.Typer(
        name="nist",
        help=_("Query the NIST Atomic Spectra Database."),
        invoke_without_command=True,
        no_args_is_help=False
    )

    @app.callback()
    @global_keyboard_interrupt_handler
    def nist_callback(
        ctx: typer.Context,
        query_string: Optional[str] = typer.Argument(
            None,
            help=_("Primary query input: wavelength range (e.g., '2000 3000') or line name (e.g., 'Fe II').")
        ),
        minwav: Optional[float] = typer.Option(
            None,
            help=_("Explicit minimum wavelength (e.g., 2000). Overrides any wavelength range parsed from 'query_string'. "
                "Can be combined with '--linename'.")
        ),
        maxwav: Optional[float] = typer.Option(
            None,
            help=_("Explicit maximum wavelength (e.g., 3000). Overrides any wavelength range parsed from 'query_string'. "
                "Can be combined with '--linename'.")
        ),
        linename: Optional[str] = typer.Option(
            None,
            help=_("Explicit line name (e.g., 'Fe II', 'H I'). Overrides any line name parsed from 'query_string'. "
                "Can be combined with explicit '--minwav' and '--maxwav' for a specific range.")
        ),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(
            25, help=_("Maximum number of rows to display. Use -1 for all rows.")
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help=_("Show all columns in the output table.")
        ),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time.")),
        debug_flag: bool = typer.Option( # Renamed to avoid conflict with imported debug
            False,
            "--debug", # Removed -t to avoid conflict with --test
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
        setup_debug_context(ctx, debug_flag, verbose)

        # If no query string and no wavelength/linename options are provided, show help
        # This handles the case where `nist` is called without any arguments
        if query_string is None and minwav is None and maxwav is None and linename is None:
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    app(["--help"]) # Call app with --help to get its own help
                except SystemExit:
                    pass
            full_help_text = help_output_capture.getvalue()

            # Description text
            desc_text = (
                _("Query the NIST Atomic Spectra Database. You can query by:\n") +
                _("  1. Wavelength range: Provide two numbers (e.g., '2000 3000').\n") +
                _("  2. Line name: Provide a line name (e.g., 'Fe II', 'H I').\n") +
                _("     If a line name is provided without explicit --minwav/--maxwav, a broad default range will be used.\n") +
                _("You can combine explicit --minwav/--maxwav with --linename for a specific range.\n")
            )

            # If help is not explicitly requested, show simplified help
            if not any(arg in ["-h", "--help"] for arg in ctx.args):
                console.print(desc_text)
                
                # Extract and print Arguments section
                args_match = re.search(r"(╭─ Arguments ─+╮\n.*?\n╰─+╯)", full_help_text, flags=re.DOTALL)
                if args_match:
                    console.print(args_match.group(0))
                
                console.print(_("\nUse --help to see all available options."))
                raise typer.Exit()
            else:
                # If help IS explicitly requested, print full help
                console.print(desc_text)
                console.print(full_help_text)
                raise typer.Exit()
            # Typer will handle explicit --help, so we just return if it's not handled above.
            return

        _minwav = minwav
        _maxwav = maxwav
        _linename = linename

        # Try to parse query_string as minwav and maxwav
        parts = query_string.split() if query_string else []
        if len(parts) == 2:
            try:
                parsed_minwav = float(parts[0])
                parsed_maxwav = float(parts[1])
                if _minwav is None:
                    _minwav = parsed_minwav
                if _maxwav is None:
                    _maxwav = parsed_maxwav
            except ValueError:
                # If not two floats, treat query_string as linename
                if _linename is None and query_string: # Only assign if query_string is not None
                    _linename = query_string
        else:
            # If not two parts, treat query_string as linename
            if _linename is None and query_string: # Only assign if query_string is not None
                _linename = query_string

        # If linename is provided but no wavelength range, set a broad default range
        if _linename and (_minwav is None or _maxwav is None):
            if _minwav is None:
                _minwav = 1.0  # Default minimum wavelength
            if _maxwav is None:
                _maxwav = 100000.0  # Default maximum wavelength

        if _minwav is None or _maxwav is None:
            console.print(_(f"[red]Error: Wavelength range (MINWAV and MAXWAV) must be provided either as arguments or implicitly via a line name query.[/red]"))
            raise typer.Exit(code=1)

        if ctx.obj.get("DEBUG"):
            debug(f"query - minwav: {_minwav}, maxwav: {_maxwav}, linename: {_linename}")

        console.print(f"[cyan]{_('Querying NIST Atomic Spectra Database...')}[/cyan]")

        try:
            results = Nist.query(minwav=_minwav * u.AA, maxwav=_maxwav * u.AA, linename=_linename)

            if results and len(results) > 0:
                console.print(_("[green]Found {count} result(s) from NIST.[/green]").format(count=len(results)))
                display_table(ctx, results, title=_("NIST Query Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, results, output_file, output_format, _("NIST query"))
            else:
                console.print(_("[yellow]No results found for your NIST query.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("NIST query"))
            raise typer.Exit(code=1)

    return app
