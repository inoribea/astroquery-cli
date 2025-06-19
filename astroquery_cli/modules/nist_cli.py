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

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="nist",
        help="Query the NIST Atomic Spectra Database.",
        invoke_without_command=True,
        no_args_is_help=False
    )

    @app.callback()
    @global_keyboard_interrupt_handler
    def nist_callback(
        ctx: typer.Context,
        query_string: Optional[str] = typer.Argument(
            None,
            help="Primary query input. Can be:\n"
                "  1. A wavelength range (e.g., '2000 3000').\n"
                "  2. A line name (e.g., 'Fe II', 'H I').\n"
                "If a line name is provided without explicit --minwav/--maxwav, a broad default range will be used."
        ),
        minwav: Optional[float] = typer.Option(
            None,
            help="Explicit minimum wavelength (e.g., 2000). Overrides any wavelength range parsed from 'query_string'. "
                "Can be combined with '--linename'."
        ),
        maxwav: Optional[float] = typer.Option(
            None,
            help="Explicit maximum wavelength (e.g., 3000). Overrides any wavelength range parsed from 'query_string'. "
                "Can be combined with '--linename'."
        ),
        linename: Optional[str] = typer.Option(
            None,
            help="Explicit line name (e.g., 'Fe II', 'H I'). Overrides any line name parsed from 'query_string'. "
                "Can be combined with explicit '--minwav' and '--maxwav' for a specific range."
        ),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(
            25, help="Maximum number of rows to display. Use -1 for all rows."
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help="Show all columns in the output table."
        ),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time."),
        debug_flag: bool = typer.Option( # Renamed to avoid conflict with imported debug
            False,
            "--debug", # Removed -t to avoid conflict with --test
            help="Enable debug mode with verbose output.",
            envvar="AQC_DEBUG"
        ),
        verbose: bool = typer.Option(
            False,
            "-v",
            "--verbose",
            help="Enable verbose output."
        )
    ):
        setup_debug_context(ctx, debug_flag, verbose)

        # If no query string and no wavelength/linename options are provided, show help
        # This handles the case where `nist` is called without any arguments
        if query_string is None and minwav is None and maxwav is None and linename is None:
            # If help is not explicitly requested, but no arguments are given, show help
            if not any(arg in ["-h", "--help"] for arg in ctx.args):
                help_output_capture = StringIO()
                with redirect_stdout(help_output_capture):
                    try:
                        app(["--help"]) # Call app with --help to get its own help
                    except SystemExit:
                        pass
                console.print(help_output_capture.getvalue())
                raise typer.Exit()
            # If help IS explicitly requested, Typer will handle it, so we just return.
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
            console.print(f"[red]{_('Error: Wavelength range (MINWAV and MAXWAV) must be provided either as arguments or implicitly via a line name query.')}[/red]")
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
