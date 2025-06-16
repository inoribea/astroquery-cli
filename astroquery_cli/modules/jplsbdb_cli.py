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
    global_keyboard_interrupt_handler
)
import re
from io import StringIO
from contextlib import redirect_stdout
from astroquery_cli.common_options import setup_debug_context

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="jplsbdb",
        help=builtins._("Query JPL Small-Body Database (SBDB)."),
        invoke_without_command=True,
        no_args_is_help=False
    )

    @app.callback()
    def jplsbdb_callback(
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
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    app(ctx.args + ["--help"])
                except SystemExit:
                    pass
            full_help_text = help_output_capture.getvalue()
            commands_match = re.search(r'╭─ Commands ─.*?(\n(?:│.*?\n)*)╰─.*─╯', full_help_text, re.DOTALL)
            if commands_match:
                commands_section = commands_match.group(0)
                filtered_commands_section = "\n".join([
                    line for line in commands_section.splitlines() if "Usage:" not in line
                ])
                console.print(filtered_commands_section)
            else:
                console.print(full_help_text)
            raise typer.Exit()

    @app.command(name="object", help=builtins._("Query JPL SBDB for a small body."))
    @global_keyboard_interrupt_handler
    def query_sbdb(ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Target small body (e.g., 'Ceres', '1P', '2023 BU').")),
        id_type: Optional[str] = typer.Option(None, help=builtins._("Type of target identifier ('name', 'des', 'moid', 'spk') (default: let SBDB auto-detect).")),
        phys_par: bool = typer.Option(False, "--phys-par", help=builtins._("Include physical parameters.")),
        orb_el: bool = typer.Option(False, "--orb-el", help=builtins._("Include orbital elements.")),
        close_approach: bool = typer.Option(False, "--ca-data", help=builtins._("Include close-approach data.")),
        radar_obs: bool = typer.Option(False, "--radar-obs", help=builtins._("Include radar observation data.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display for tables. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in output tables.")),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying JPL SBDB for target: '{target}'...[/cyan]").format(target=target))
        try:
            query_kwargs = {}
            if id_type:
                query_kwargs['id_type'] = id_type
            sbdb_query = SBDB.query(
                target,
                **query_kwargs,
                full_precision=True
            )

            if sbdb_query:
                console.print(_("[green]Data found for '{target}'.[/green]").format(target=target))
                if isinstance(sbdb_query, AstropyTable) and len(sbdb_query) > 0 :
                    display_table(ctx, sbdb_query, title=_("JPL SBDB Data for {target}").format(target=target), max_rows=max_rows_display, show_all_columns=show_all_columns)
                    if output_file:
                        save_table_to_file(ctx, sbdb_query, output_file, output_format, _("JPL SBDB query for {target}").format(target=target))

                elif hasattr(sbdb_query, 'items'):
                    object_fullname = sbdb_query.get('object', {}).get('fullname', target)
                    console.print(_("[bold magenta]SBDB Data for: {fullname}[/bold magenta]").format(fullname=object_fullname))
                    output_data = {}

                    def process_quantity_objects(obj):
                        if isinstance(obj, dict):
                            return {k: process_quantity_objects(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [process_quantity_objects(elem) for elem in obj]
                        elif hasattr(obj, 'value') and hasattr(obj, 'unit'):
                            return f"{obj.value} {obj.unit}"
                        return obj

                    def dict_to_table_rows(d, field_order=None):
                        rows = []
                        if field_order:
                            for k in field_order:
                                if k in d:
                                    rows.append([str(k), str(d[k])])
                            for k in d:
                                if k not in field_order:
                                    rows.append([str(k), str(d[k])])
                        else:
                            for k, v in d.items():
                                rows.append([str(k), str(v)])
                        return rows

                    for key, value in sbdb_query.items():
                        processed_value = process_quantity_objects(value)
                        # 定制字段顺序
                        if key == "object":
                            field_order = ["spkid", "kind", "fullname", "orbit_id", "neo", "prefix", "des", "pha", "orbit_class"]
                            if isinstance(processed_value, dict):
                                rows = dict_to_table_rows(processed_value, field_order)
                                display_table(ctx, rows, title="Object")
                                output_data[str(key)] = processed_value
                            else:
                                display_table(ctx, [[str(processed_value)]], title="Object")
                                output_data[str(key)] = processed_value
                        elif key == "orbit":
                            field_order = [
                                "cov_epoch", "elements", "n_dop_obs_used", "last_obs", "soln_date", "not_valid_after",
                                "n_del_obs_used", "not_valid_before", "epoch", "model_pars", "equinox", "data_arc",
                                "moid", "moid_jup", "producer", "condition_code", "t_jup", "orbit_id", "source",
                                "sb_used", "pe_used", "first_obs", "two_body", "rms", "n_obs_used", "comment"
                            ]
                            if isinstance(processed_value, dict):
                                rows = dict_to_table_rows(processed_value, field_order)
                                display_table(ctx, rows, title="Orbit")
                                output_data[str(key)] = processed_value
                            else:
                                display_table(ctx, [[str(processed_value)]], title="Orbit")
                                output_data[str(key)] = processed_value
                        elif key == "model_pars":
                            field_order = ["A1", "A1_sig", "A1_kind", "A2", "A2_sig", "A2_kind", "S0", "S0_sig", "S0_kind"]
                            if isinstance(processed_value, dict):
                                rows = dict_to_table_rows(processed_value, field_order)
                                display_table(ctx, rows, title="Model Parameters")
                                output_data[str(key)] = processed_value
                            else:
                                display_table(ctx, [[str(processed_value)]], title="Model Parameters")
                                output_data[str(key)] = processed_value
                        elif key == "elements":
                            field_order = [
                                "e", "e_sig", "a", "a_sig", "q", "q_sig", "i", "i_sig", "om", "om_sig", "w", "w_sig",
                                "ma", "ma_sig", "tp", "tp_sig", "per", "per_sig", "n", "n_sig", "ad", "ad_sig"
                            ]
                            if isinstance(processed_value, dict):
                                rows = dict_to_table_rows(processed_value, field_order)
                                display_table(ctx, rows, title="Elements")
                                output_data[str(key)] = processed_value
                            else:
                                display_table(ctx, [[str(processed_value)]], title="Elements")
                                output_data[str(key)] = processed_value
                        elif isinstance(processed_value, dict):
                            rows = dict_to_table_rows(processed_value)
                            display_table(ctx, rows, title=key)
                            output_data[str(key)] = processed_value
                        elif isinstance(processed_value, list):
                            if all(isinstance(item, dict) for item in processed_value):
                                headers = set()
                                for item in processed_value:
                                    headers.update(item.keys())
                                headers = list(headers)
                                table_rows = []
                                for item in processed_value:
                                    row = [str(item.get(h, "")) for h in headers]
                                    table_rows.append(row)
                                display_table(ctx, table_rows, title=key)
                                output_data[str(key)] = processed_value
                            else:
                                for item in processed_value:
                                    display_table(ctx, [[str(item)]], title=key)
                                output_data[str(key)] = processed_value
                        else:
                            display_table(ctx, [[str(processed_value)]], title=key)
                            output_data[str(key)] = processed_value

                    if output_file and not any(isinstance(v, AstropyTable) for v in sbdb_query.values()):
                        import json
                        try:
                            class QuantityEncoder(json.JSONEncoder):
                                def default(self, obj):
                                    if hasattr(obj, 'value') and hasattr(obj, 'unit'):
                                        return f"{obj.value} {obj.unit}"
                                    return json.JSONEncoder.default(self, obj)

                            file_path = output_file if '.json' in output_file else output_file + ".json"
                            with open(file_path, 'w') as f:
                                json.dump(output_data, f, indent=2, cls=QuantityEncoder)
                            console.print(_("[green]Primary data saved to {file_path}[/green]").format(file_path=file_path))
                        except Exception as json_e:
                            console.print(_("[red]Could not save non-table data as JSON: {error}[/red]").format(error=json_e))
                else:
                    console.print(str(sbdb_query))

            else:
                console.print(_("[yellow]No information found for target '{target}'.[/yellow]").format(target=target))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("JPL SBDB object"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    return app
