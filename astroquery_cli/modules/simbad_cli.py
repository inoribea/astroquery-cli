from typing import Optional, List

import typer
from astroquery.simbad import Simbad, SimbadClass
from astropy.table import Table
from rich.console import Console
from astroquery_cli.utils import display_table, handle_astroquery_exception, common_output_options, save_table_to_file, add_common_fields, console
from astroquery_cli.common_options import setup_debug_context
from ..i18n import get_translator
from ..utils import global_keyboard_interrupt_handler
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout

def get_app():
    import builtins
    _ = builtins._
    help_text = _("SIMBAD astronomical database.")
    app = typer.Typer(
        name="simbad",
        help=help_text,
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def simbad_callback(
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

    Simbad.ROW_LIMIT = 50
    Simbad.TIMEOUT = 60
    # ================== SIMBAD_FIELDS =========================
    SIMBAD_FIELDS = [
        "main_id", "ra", "dec", "otype", "B", "V", "J", "H", "K", "G"
        #...
    ]
    # ===========================================================


    @app.command(name="object", help=builtins._("Query basic data for an astronomical object."))
    @global_keyboard_interrupt_handler
    def query_object(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the object to query (e.g., 'M101', 'HD12345').")),
        wildcard: bool = typer.Option(False, "--wildcard", "-w", help=builtins._("Enable wildcard searching for the object name.")),
        add_fields: Optional[List[str]] = typer.Option(None, "--add-field", help=builtins._("Additional VOTable fields to retrieve (e.g., 'otype', 'sptype'). Can be specified multiple times.")),
        remove_fields: Optional[List[str]] = typer.Option(None, "--remove-field", help=builtins._("Default VOTable fields to remove (e.g., 'coo_bibcode'). Can be specified multiple times.")),
        include_common_fields: bool = typer.Option(True, help=builtins._("Automatically include a set of common useful fields.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(10, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
    ):
        """
        Retrieves information about a specific astronomical object from SIMBAD.
        Example: aqc simbad query-object M31
        Example: aqc simbad query-object "HD 1*" --wildcard --add-field sptype
        """

        console.print(_("[cyan]Querying SIMBAD for object: '{object_name}'...[/cyan]").format(object_name=object_name))
        s = Simbad()
        if include_common_fields:
            add_common_fields(ctx, s)
        if add_fields:
            for field in add_fields:
                s.add_votable_fields(field)
        if remove_fields:
            for field in remove_fields:
                s.remove_votable_fields(field)

        try:
            result_table: Optional[Table] = s.query_object(object_name, wildcard=wildcard)

            if result_table:
                console.print(_("[green]Found {count} match(es) for '{object_name}'.[/green]").format(count=len(result_table), object_name=object_name))
                display_table(ctx, result_table, title=_("SIMBAD Data for {object_name}").format(object_name=object_name), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("SIMBAD object query"))
            else:
                console.print(_("[yellow]No information found for object '{object_name}'.[/yellow]").format(object_name=object_name))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("SIMBAD object"))
            raise typer.Exit(code=1)


    @app.command(name="ids", help=builtins._("Query all identifiers for an astronomical object."))
    @global_keyboard_interrupt_handler
    def query_objectids(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the object (e.g., 'Polaris').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows."))
    ):
        """
        Retrieves all known identifiers for a given astronomical object.
        Example: aqc simbad query-ids M51
        """
        console.print(_("[cyan]Querying SIMBAD for identifiers of: '{object_name}'...[/cyan]").format(object_name=object_name))
        s = Simbad()
        try:
            result_table: Optional[Table] = s.query_objectids(object_name)
            if result_table:
                display_table(ctx, result_table, title=_("SIMBAD Identifiers for {object_name}").format(object_name=object_name), max_rows=max_rows_display)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("SIMBAD ID query"))
            else:
                console.print(_("[yellow]No identifiers found for object '{object_name}'.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("SIMBAD ids"))
            raise typer.Exit(code=1)


    @app.command(name="bibcode", help=builtins._("Query objects associated with a bibcode or bibcode list."))
    @global_keyboard_interrupt_handler
    def query_bibcode(ctx: typer.Context,
        bibcodes: List[str] = typer.Argument(..., help=builtins._("Bibcode(s) to query (e.g., '2003A&A...409..581H'). Can specify multiple.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(50, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        """
        Retrieves objects from SIMBAD that are cited in the given bibcode(s).
        Example: aqc simbad query-bibcode 1997AJ....113.2104S
        Example: aqc simbad query-bibcode 2003A&A...409..581H 2004A&A...418..989P
        """
        bibcodes_str = ', '.join(bibcodes)
        console.print(_("[cyan]Querying SIMBAD for objects in bibcode(s): {bibcodes_list}...[/cyan]").format(bibcodes_list=bibcodes_str))
        s = Simbad()
        add_common_fields(ctx, s)
        try:
            result_table: Optional[Table] = s.query_bibcode(bibcodes)
            if result_table:
                display_table(ctx, result_table, title=_("SIMBAD Objects for Bibcode(s)"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("SIMBAD bibcode query"))
            else:
                console.print(_("[yellow]No objects found for the given bibcode(s).[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("SIMBAD bibcode"))
            raise typer.Exit(code=1)

    # TODO: Add more Simbad functionalities like query_region, query_criteria, list_votable_fields if desired.

    return app
