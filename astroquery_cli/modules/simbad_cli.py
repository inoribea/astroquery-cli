from typing import Optional, List

import typer
from astroquery.simbad import Simbad, SimbadClass
from astropy.table import Table
from rich.console import Console
from astroquery_cli.utils import display_table, handle_astroquery_exception, common_output_options, save_table_to_file, add_common_fields, console
from ..i18n import get_translator

def get_app():
    import builtins
    _ = builtins._
    help_text = _("SIMBAD astronomical database.")
    app = typer.Typer(
        name="simbad",
        help=help_text,
        no_args_is_help=True
    )

    Simbad.ROW_LIMIT = 50
    Simbad.TIMEOUT = 60
    # ================== SIMBAD_FIELDS =========================
    SIMBAD_FIELDS = [
        "main_id", "ra", "dec", "otype", "B", "V", "J", "H", "K", "G"
        #...
    ]
    # ===========================================================


    @app.command(name="query-object", help=builtins._("Query basic data for an astronomical object."))
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
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        """
        Retrieves information about a specific astronomical object from SIMBAD.
        Example: aqc simbad query-object M31
        Example: aqc simbad query-object "HD 1*" --wildcard --add-field sptype
        """
        import time
        start = time.perf_counter() if test else None

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
                    save_table_to_file(result_table, output_file, output_format, _("SIMBAD object query"))
            else:
                console.print(_("[yellow]No information found for object '{object_name}'.[/yellow]").format(object_name=object_name))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("SIMBAD query_object"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()


    @app.command(name="query-ids", help=builtins._("Query all identifiers for an astronomical object."))
    def query_ids(ctx: typer.Context,
        object_name: str = typer.Argument(..., help=builtins._("Name of the object (e.g., 'Polaris').")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        """
        Retrieves all known identifiers for a given astronomical object.
        Example: aqc simbad query-ids M51
        """
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying SIMBAD for identifiers of: '{object_name}'...[/cyan]").format(object_name=object_name))
        s = Simbad()
        try:
            result_table: Optional[Table] = s.query_objectids(object_name)
            if result_table:
                display_table(ctx, result_table, title=_("SIMBAD Identifiers for {object_name}").format(object_name=object_name), max_rows=max_rows_display)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("SIMBAD ID query"))
            else:
                console.print(_("[yellow]No identifiers found for object '{object_name}'.[/yellow]").format(object_name=object_name))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("SIMBAD query_objectids"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()


    @app.command(name="query-bibcode", help=builtins._("Query objects associated with a bibcode or bibcode list."))
    def query_bibcode(ctx: typer.Context,
        bibcodes: List[str] = typer.Argument(..., help=builtins._("Bibcode(s) to query (e.g., '2003A&A...409..581H'). Can specify multiple.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(50, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        """
        Retrieves objects from SIMBAD that are cited in the given bibcode(s).
        Example: aqc simbad query-bibcode 1997AJ....113.2104S
        Example: aqc simbad query-bibcode 2003A&A...409..581H 2004A&A...418..989P
        """
        import time
        start = time.perf_counter() if test else None

        bibcodes_str = ', '.join(bibcodes)
        console.print(_("[cyan]Querying SIMBAD for objects in bibcode(s): {bibcodes_list}...[/cyan]").format(bibcodes_list=bibcodes_str))
        s = Simbad()
        add_common_fields(ctx, s)
        try:
            result_table: Optional[Table] = s.query_bibcode(bibcodes)
            if result_table:
                display_table(ctx, result_table, title=_("SIMBAD Objects for Bibcode(s)"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("SIMBAD bibcode query"))
            else:
                console.print(_("[yellow]No objects found for the given bibcode(s).[/yellow]"))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("SIMBAD query_bibcode"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    # TODO: Add more Simbad functionalities like query_region, query_criteria, list_votable_fields if desired.

    return app
