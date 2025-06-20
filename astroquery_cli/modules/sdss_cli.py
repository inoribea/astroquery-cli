import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.sdss import SDSS
from astropy import units as u
from astropy.coordinates import Angle, SkyCoord
from ..i18n import get_translator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    global_keyboard_interrupt_handler,
)
import os
import re # Keep re for other uses in the file
from astroquery_cli.common_options import setup_debug_context
from astroquery_cli.debug import debug

def get_app(_: callable):
    app = typer.Typer(
        name="sdss",
        help=(
            _("Query the Sloan Digital Sky Survey database.") + "\n\n" +
            _("Perform a query on SDSS. You must provide parameters for exactly one of the following query types:") + "\n\n" +
            _("  1. Cone Search:") + "\n" +
            _("     --ra <RA> --dec <DEC> --radius <RADIUS>") + "\n" +
            _("     (e.g., --ra '10.5 deg' --dec '20.1 deg' --radius '2 arcmin')") + "\n\n" +
            _("  2. Spectroscopic Object ID Search:") + "\n" +
            _("     --specobjid <ID> [--objtype <TYPE>]") + "\n" +
            _("     (e.g., --specobjid 2634622337315530752 --objtype 'GALAXY')") + "\n\n" +
            _("  3. Fiber ID Search:") + "\n" +
            _("     --plate <PLATE> --mjd <MJD> --fiberid <FIBERID> [--objtype <TYPE>]") + "\n" +
            _("     (e.g., --plate 123 --mjd 51608 --fiberid 1)")
        ),
        invoke_without_command=True,
        no_args_is_help=False
    )

    @app.callback()
    @global_keyboard_interrupt_handler
    def sdss_callback(
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
        ),
        ra: Optional[str] = typer.Option(None, help=_("Right Ascension (e.g., '10.5 deg', '0h42m30s'). Required for cone search.")),
        dec: Optional[str] = typer.Option(None, help=_("Declination (e.g., '20.1 deg', '+41d12m0s'). Required for cone search.")),
        radius: Optional[str] = typer.Option(None, help=_("Search radius (e.g., '0.5 deg', '2 arcmin'). Max 3 arcmin. Required for cone search.")),
        objtype: Optional[str] = typer.Option(None, help=_("Object type (e.g., 'STAR', 'GALAXY', 'QSO'). Note: This parameter is only applicable for queries using specobjid or plate/mjd/fiberid, not for cone searches.")),
        specobjid: Optional[int] = typer.Option(None, help=_("Spectroscopic object ID. Required for specobjid search.")),
        plate: Optional[int] = typer.Option(None, help=_("Plate number for spectroscopic data. Required for fiber ID search.")),
        mjd: Optional[int] = typer.Option(None, help=_("Modified Julian Date for spectroscopic data. Required for fiber ID search.")),
        fiberid: Optional[int] = typer.Option(None, help=_("Fiber ID for spectroscopic data. Required for fiber ID search.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(
            25, help=_("Maximum number of rows to display. Use -1 for all rows.")
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help=_("Show all columns in the output table.")
        ),
    ):
        setup_debug_context(ctx, debug, verbose)

        # If no query parameters are provided and help is not explicitly requested,
        # Typer's default behavior will now print the help message for the main command.
        # The custom help printing logic is removed.
        if ctx.invoked_subcommand is not None:
            return # Let Typer handle subcommands if they exist (though we're removing 'query')

        if ctx.obj.get("DEBUG"):
            debug(f"sdss_callback - ra: {ra}, dec: {dec}, radius: {radius}, objtype: {objtype}, specobjid: {specobjid}")

        # Check if any query parameters are provided
        query_params_provided = any([ra, dec, radius, objtype, specobjid, plate, mjd, fiberid])

        if not query_params_provided and not any(arg in ["-h", "--help"] for arg in ctx.args):
            # If no query parameters and no help flag, print help and exit
            # This mimics the original behavior of showing help when no command/args are given
            console.print(f"Usage: {ctx.command.get_usage(ctx)}\n")
            console.print(ctx.command.help)
            raise typer.Exit()
        elif not query_params_provided and any(arg in ["-h", "--help"] for arg in ctx.args):
            # If only help flag is provided, let Typer handle it
            return

        console.print(f"[cyan]{_('Querying SDSS...')}[/cyan]")

        try:
            # Parse inputs first
            parsed_ra = None
            parsed_dec = None
            parsed_radius = None
            try:
                if ra:
                    parsed_ra = Angle(ra).deg
                if dec:
                    parsed_dec = Angle(dec).deg
                if radius:
                    parsed_radius = u.Quantity(radius)
            except Exception as e:
                console.print(_(f"[red]Error parsing coordinate or radius value: {e}. Please ensure values are in a valid format (e.g., '10.5 deg', '5 arcmin').[/red]"))
                raise typer.Exit(code=1)

            results = None
            query_type = None

            if parsed_ra is not None or parsed_dec is not None or parsed_radius is not None:
                # Cone search
                query_type = "cone"
                if parsed_ra is None or parsed_dec is None or parsed_radius is None:
                    console.print(_("[red]Error: For a cone search, --ra, --dec, and --radius are all required. Please provide all three.[/red]"))
                    raise typer.Exit(code=1)
                if specobjid is not None or plate is not None or mjd is not None or fiberid is not None:
                    console.print(_("[red]Error: Cannot combine cone search parameters (--ra, --dec, --radius) with other query types (--specobjid or --plate, --mjd, --fiberid).[/red]"))
                    raise typer.Exit(code=1)
                coords = SkyCoord(parsed_ra, parsed_dec, unit=(u.deg, u.deg))
                results = SDSS.query_region(coordinates=coords, radius=parsed_radius)
            elif specobjid is not None:
                # Spectroscopic object ID search
                query_type = "specobjid"
                if parsed_ra is not None or parsed_dec is not None or parsed_radius is not None or \
                   plate is not None or mjd is not None or fiberid is not None:
                    console.print(_("[red]Error: Cannot combine --specobjid with other query types (cone search or fiber ID search).[/red]"))
                    raise typer.Exit(code=1)
                results = SDSS.query_sql(f"SELECT * FROM SpecObj WHERE specobjid = {specobjid}")
            elif plate is not None or mjd is not None or fiberid is not None:
                # Fiber ID search
                query_type = "fiberid"
                if plate is None or mjd is None or fiberid is None:
                    console.print(_("[red]Error: For a fiber ID search, --plate, --mjd, and --fiberid are all required. Please provide all three.[/red]"))
                    raise typer.Exit(code=1)
                if parsed_ra is not None or parsed_dec is not None or parsed_radius is not None or specobjid is not None:
                    console.print(_("[red]Error: Cannot combine fiber ID search parameters (--plate, --mjd, --fiberid) with other query types (cone search or specobjid search).[/red]"))
                    raise typer.Exit(code=1)
                results = SDSS.query_fiberid(plate=plate, mjd=mjd, fiberid=fiberid)
            else:
                console.print(_("[red]Error: No valid query parameters provided. Please specify parameters for one of the following query types: coordinates (--ra, --dec, --radius), or --specobjid, or --plate, --mjd, and --fiberid.[/red]"))
                raise typer.Exit(code=1)

            if results and len(results) > 0:
                if objtype and 'objtype' in results.colnames and (query_type == "fiberid" or query_type == "specobjid"):
                    initial_count = len(results)
                    results = results[results['objtype'] == objtype.upper()]
                    if len(results) == 0:
                        console.print(_("[yellow]No results found for objtype '{objtype}' after filtering.[/yellow]").format(objtype=objtype))
                        raise typer.Exit(code=0)
                    else:
                        console.print(_("[green]Filtered {filtered_count} results for objtype '{objtype}' from {initial_count} total.[/green]").format(
                            filtered_count=len(results), objtype=objtype, initial_count=initial_count))

                console.print(_("[green]Found {count} result(s) from SDSS.[/green]").format(count=len(results)))
                display_table(ctx, results, title=_("SDSS Query Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, results, output_file, output_format, _("SDSS query"))
            else:
                console.print(_("[yellow]No results found for your SDSS query.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("SDSS query"))
            raise typer.Exit(code=1)

    return app
