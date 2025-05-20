import typer
from typing import Optional, List, Any
from astropy.table import Table as AstropyTable
from astroquery.jplsbdb import SBDB
from ..i18n import get_translator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
)

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="jplsbdb",
        help=builtins._("Query JPL Small-Body Database (SBDB)."),
        no_args_is_help=True
    )

    # ================== JPL_SBDB_FIELDS =========================
    JPL_SBDB_FIELDS = [
        "spkid",
        "full_name",
        "class",
        "epoch",
        "a",
        "e",
        "i",
        "per",
        "node",
        "om",
        "w",
        "ma",
        "q",
        "H",
        "G",
        "tp",
        "MOID",
        "diameter",
        "albedo",
        # ...
    ]
    # ============================================================



    @app.command(name="query", help=builtins._("Query JPL SBDB for a small body."))
    def query_sbdb(ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Target small body (e.g., 'Ceres', '1P', '2023 BU').")),
        id_type: Optional[str] = typer.Option("auto", help=builtins._("Type of target identifier ('name', 'des', 'moid', 'spk', 'auto').")),
        phys_par: bool = typer.Option(False, "--phys-par", help=builtins._("Include physical parameters.")),
        orb_el: bool = typer.Option(False, "--orb-el", help=builtins._("Include orbital elements.")),
        close_approach: bool = typer.Option(False, "--ca-data", help=builtins._("Include close-approach data.")),
        radar_obs: bool = typer.Option(False, "--radar-obs", help=builtins._("Include radar observation data.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display for tables. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in output tables.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying JPL SBDB for target: '{target}'...[/cyan]").format(target=target))
        try:
            sbdb_query = SBDB.query(
                target,
                id_type=id_type,
                phys_par=phys_par,
                orb_el=orb_el,
                ca_data=close_approach,
                radar_obs=radar_obs,
                full_precision=True
            )

            if sbdb_query:
                console.print(_("[green]Data found for '{target}'.[/green]").format(target=target))
                if isinstance(sbdb_query, AstropyTable) and len(sbdb_query) > 0 :
                    display_table(sbdb_query, title=_("JPL SBDB Data for {target}").format(target=target), max_rows=max_rows_display, show_all_columns=show_all_columns)
                    if output_file:
                        save_table_to_file(sbdb_query, output_file, output_format, _("JPL SBDB query for {target}").format(target=target))

                elif hasattr(sbdb_query, 'items'):
                    object_fullname = sbdb_query.get('object', {}).get('fullname', target)
                    console.print(_("[bold magenta]SBDB Data for: {fullname}[/bold magenta]").format(fullname=object_fullname))
                    output_data = {}
                    for key, value in sbdb_query.items():
                        if isinstance(value, AstropyTable):
                            console.print(_("\n[bold underline]Table: {key}[/bold underline]").format(key=key))
                            display_table(value, title=_("{key} for {target}").format(key=key, target=target), max_rows=max_rows_display, show_all_columns=show_all_columns)
                            if output_file:
                                save_table_to_file(value, output_file.replace(".", f"_{key}."), output_format, _("JPL SBDB {key} for {target}").format(key=key, target=target))
                        elif isinstance(value, dict) or isinstance(value, list):
                            console.print(_("\n[bold]{key}:[/bold]").format(key=key))
                            console.print_json(data=value)
                            output_data[str(key)] = value
                        else:
                            console.print(_("[bold]{key}:[/bold] {value}").format(key=key, value=value))
                            output_data[str(key)] = str(value)

                    if output_file and not any(isinstance(v, AstropyTable) for v in sbdb_query.values()):
                        import json
                        try:
                            file_path = output_file if '.json' in output_file else output_file + ".json"
                            with open(file_path, 'w') as f:
                                json.dump(output_data, f, indent=2)
                            console.print(_("[green]Primary data saved to {file_path}[/green]").format(file_path=file_path))
                        except Exception as json_e:
                            console.print(_("[red]Could not save non-table data as JSON: {error}[/red]").format(error=json_e))
                else:
                    console.print(str(sbdb_query))

            else:
                console.print(_("[yellow]No information found for target '{target}'.[/yellow]").format(target=target))

        except Exception as e:
            handle_astroquery_exception(e, _("JPL SBDB query"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    return app
