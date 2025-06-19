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

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="sdss",
        help=builtins._(
            "Query the Sloan Digital Sky Survey (SDSS) database.\n\n"
            "Perform a query on SDSS. You must provide parameters for exactly one of the following query types:\n\n"
            "  1. Cone Search:\n"
            "     --ra <RA> --dec <DEC> --radius <RADIUS>\n"
            "     (e.g., --ra '10.5 deg' --dec '20.1 deg' --radius '2 arcmin')\n"
            "  2. Spectroscopic Object ID Search:\n"
            "     --specobjid <ID> [--objtype <TYPE>]\n"
            "     (e.g., --specobjid 2634622337315530752 --objtype 'GALAXY')\n"
            "  3. Fiber ID Search:\n"
            "     --plate <PLATE> --mjd <MJD> --fiberid <FIBERID> [--objtype <TYPE>]\n"
            "     (e.g., --plate 123 --mjd 51608 --fiberid 1)"
        ),
        invoke_without_command=True,
        no_args_is_help=False
    )

    @app.callback()
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
        )
    ):
        setup_debug_context(ctx, debug, verbose)

        if ctx.invoked_subcommand is None and \
           not any(arg in ["-h", "--help"] for arg in ctx.args):
            # Print initial help text (Usage and main description)
            console.print(f"Usage: {ctx.command.get_usage(ctx)}\n")
            console.print(ctx.command.help)

            # Manually construct and print the Commands section
            commands_list = []
            for command in app.registered_commands:
                command_name = command.name
                command_help = command.help if command.help else ""
                # Adjust padding to match Typer's default formatting for commands
                commands_list.append(f"│ {command_name:<7} {command_help}") 

            if commands_list:
                # Get terminal width for dynamic box sizing
                try:
                    terminal_width = os.get_terminal_size().columns
                except OSError:
                    terminal_width = 80 # Fallback if not in a proper terminal

                # Typer often uses a default width around 80-100. Let's cap it to avoid overly wide boxes.
                box_width = min(terminal_width, 100) 
                
                # Calculate inner content width for padding
                # The format is "│ {name} {help} │"
                # So, inner content width is box_width - 4 (for two '│ ' and two ' │')
                inner_content_width = box_width - 4

                console.print("╭─ Commands " + "─" * (box_width - len("╭─ Commands ") - 1) + "╮")
                for cmd_line in commands_list:
                    # cmd_line is like "│ query   Perform a query..."
                    # We need to pad the part after "│ "
                    content_to_pad = cmd_line[2:]
                    padded_line = f"│ {content_to_pad.ljust(inner_content_width)} │"
                    console.print(padded_line)
                console.print("╰─" + "─" * (box_width - 3) + "╯") # Corrected: box_width - 3
            
            # Do NOT print Options section as per user's latest request
            
            raise typer.Exit()

    @app.command(
        name="query",
        help=builtins._(
            "Perform a query on SDSS using the options provided to the main 'sdss' command."
        )
    )
    @global_keyboard_interrupt_handler
    def query_sdss(
        ctx: typer.Context,
        ra: Optional[str] = typer.Option(None, help=builtins._("Right Ascension (e.g., '10.5 deg', '0h42m30s'). Required for cone search.")),
        dec: Optional[str] = typer.Option(None, help=builtins._("Declination (e.g., '20.1 deg', '+41d12m0s'). Required for cone search.")),
        radius: Optional[str] = typer.Option(None, help=builtins._("Search radius (e.g., '0.5 deg', '2 arcmin'). Max 3 arcmin. Required for cone search.")),
        objtype: Optional[str] = typer.Option(None, help=builtins._("Object type (e.g., 'STAR', 'GALAXY', 'QSO'). Note: This parameter is only applicable for queries using specobjid or plate/mjd/fiberid, not for cone searches.")),
        specobjid: Optional[int] = typer.Option(None, help=builtins._("Spectroscopic object ID. Required for specobjid search.")),
        plate: Optional[int] = typer.Option(None, help=builtins._("Plate number for spectroscopic data. Required for fiber ID search.")),
        mjd: Optional[int] = typer.Option(None, help=builtins._("Modified Julian Date for spectroscopic data. Required for fiber ID search.")),
        fiberid: Optional[int] = typer.Option(None, help=builtins._("Fiber ID for spectroscopic data. Required for fiber ID search.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(
            25, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")
        ),
        show_all_columns: bool = typer.Option(
            False, "--show-all-cols", help=builtins._("Show all columns in the output table.")
        ),
    ):
        # Remove the custom help message filtering logic
        # This ensures Typer's default help generation is used,
        # which will correctly display the query command's help.
        pass # No changes needed here, the original parameters are already in place.

        if ctx.obj.get("DEBUG"):
            debug(f"query_sdss - ra: {ra}, dec: {dec}, radius: {radius}, objtype: {objtype}, specobjid: {specobjid}")

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
