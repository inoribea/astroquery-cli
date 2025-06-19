import typer
from typing import Optional, List, Any
from enum import Enum
from astropy.table import Table as AstropyTable
from astroquery.jplhorizons import Horizons, conf as jpl_conf
from astroquery.jplsbdb import SBDB
from astropy.time import Time
from rich.console import Console
import re
from io import StringIO
from contextlib import redirect_stdout

from ..utils import (
    display_table,
    handle_astroquery_exception,
    global_keyboard_interrupt_handler,
    console,
    common_output_options,
    save_table_to_file
)
from .. import i18n
from astroquery_cli.common_options import setup_debug_context
from astroquery_cli.debug import debug

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="jpl",
        help=builtins._("Query JPL services (Horizons and Small-Body Database)."),
        invoke_without_command=True,
        no_args_is_help=False
    )

    @app.callback()
    def jpl_callback(
        ctx: typer.Context,
        debug_flag: bool = typer.Option(
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
        setup_debug_context(ctx, debug_flag, verbose)

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

    # ================== JPL_HORIZONS_QUANTITIES =================
    JPL_HORIZONS_QUANTITIES = [
        "1", "2", "4", "8", "9", "10", "12", "13", "14", "19", "20", "21", "23", "24", "31",
    ]
    # ============================================================

    JPL_SERVERS = {
        "nasa": jpl_conf.horizons_server,
        "ksb": "https://ssd.jpl.nasa.gov/horizons_batch.cgi"
    }

    class IDType(str, Enum):
        smallbody = "smallbody"
        majorbody = "majorbody"
        designation = "designation"
        name = "name"
        asteroid_number = "asteroid_number"
        comet_name = "comet_name"

    class EphemType(str, Enum):
        OBSERVER = "OBSERVER"
        VECTORS = "VECTORS"
        ELEMENTS = "ELEMENTS"

    def get_common_locations(ctx: typer.Context,):
        lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
        _ = i18n.get_translator(lang)
        return ["500", "geo", "010", "F51", "G84"]

    def get_default_quantities_ephem(ctx: typer.Context,):
        lang = ctx.obj.get("lang", "en") if ctx.obj else "en"
        _ = i18n.get_translator(lang)
        return "1,2,4,8,9,10,12,13,14,19,20,21,23,24,31"

    @app.command(name="horizons", help=builtins._("Query ephemerides, orbital elements, or vectors for a target object."))
    @global_keyboard_interrupt_handler
    def query_horizons(ctx: typer.Context,
        target: Optional[str] = typer.Argument(None, help=builtins._("Object ID (e.g., 'Mars', 'Ceres', '2000NM', '@10'). Use '@' prefix for spacecraft ID.")),
        epochs: Optional[str] = typer.Option(
            None,
            help=_(
                "Epochs for the query. Can be a single ISO time (e.g., '2023-01-01 12:00'), "
                "a list of times separated by commas (e.g., '2023-01-01,2023-01-02'), "
                "or a start,stop,step dict-like string (e.g., \"{'start':'2023-01-01', 'stop':'2023-01-05', 'step':'1d'}\"). "
                "If None, uses current time for single epoch queries like elements/vectors."
            )
        ),
        start_time: Optional[str] = typer.Option(None, "--start", help=builtins._("Start time for ephemeris range (YYYY-MM-DD [HH:MM]). Overrides 'epochs' if 'end_time' is also set.")),
        end_time: Optional[str] = typer.Option(None, "--end", help=builtins._("End time for ephemeris range (YYYY-MM-DD [HH:MM]).")),
        step: Optional[str] = typer.Option("1d", "--step", help=builtins._("Time step for ephemeris range (e.g., '1d', '1h', '10m'). Used if 'start_time' and 'end_time' are set.")),
        location: str = typer.Option(
            "500",
            help=builtins._("Observatory code (e.g., '500' for Geocenter, 'geo' is alias for '500'). Try common codes or find specific ones."),
            autocompletion=get_common_locations
        ),
        id_type: Optional[IDType] = typer.Option(
            None,
            case_sensitive=False,
            help=builtins._("Type of the target identifier. If None, Horizons will try to guess.")
        ),
        ephem_type: EphemType = typer.Option(
            EphemType.ELEMENTS,
            case_sensitive=False,
            help=builtins._("Type of ephemeris to retrieve.")
        ),
        quantities: Optional[str] = typer.Option(
            None,
            help=builtins._("Comma-separated string of quantity codes (e.g., '1,2,19,20'). Relevant for OBSERVER and VECTORS. See JPL Horizons docs for codes. Uses sensible defaults if None.")
        ),
        max_rows: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table, even if wide.")),
        jpl_server: str = typer.Option(
            "nasa",
            help=builtins._("JPL Horizons server to use. Choices: {server_list}").format(server_list=list(JPL_SERVERS.keys())),
            autocompletion=lambda: list(JPL_SERVERS.keys())
        ),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        if target is None and not any(arg in ["-h", "--help"] for arg in ctx.args):
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    ctx.get_help()
                except SystemExit:
                    pass
            full_help_text = help_output_capture.getvalue()
            
            # Remove the "Options" section
            full_help_text = re.sub(r'╭─ Options ─.*?(\n(?:│.*?\n)*)╰─.*─╯', '', full_help_text, flags=re.DOTALL)
            # Remove the "Commands" section
            full_help_text = re.sub(r'╭─ Commands ─.*?(\n(?:│.*?\n)*)╰─.*─╯', '', full_help_text, flags=re.DOTALL)
            
            console.print(full_help_text)
            raise typer.Exit()

        console.print(_("[cyan]Querying JPL Horizons for '{target}'...[/cyan]").format(target=target))

        current_server = JPL_SERVERS.get(jpl_server.lower(), jpl_conf.horizons_server)
        if jpl_conf.horizons_server != current_server:
            debug(_("Using JPL server: {server}").format(server=current_server))
            jpl_conf.horizons_server = current_server

        epoch_dict = None
        if start_time and end_time:
            epoch_dict = {'start': start_time, 'stop': end_time, 'step': step}
            debug(_("Using epoch range: {start} to {end} with step {step}").format(start=start_time, end=end_time, step=step))
        elif epochs:
            if epochs.startswith("{") and epochs.endswith("}"):
                try:
                    import ast
                    epoch_dict = ast.literal_eval(epochs)
                    debug(_("Using epoch dict: {epoch_dict}").format(epoch_dict=epoch_dict))
                except (ValueError, SyntaxError) as e:
                    console.print(_("[red]Error parsing epoch dictionary: {error}. Please ensure it's a valid Python dictionary string.[/red]").format(error=e))
                    raise typer.Exit(code=1)
        auto_majorbodies = {"sun", "mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "moon"}
        auto_id_type = id_type.value if id_type else ("majorbody" if target.strip().lower() in auto_majorbodies else None)
        query_params = {
            "id": target,
            "location": location,
            "epochs": epoch_dict,
            "id_type": auto_id_type,
        }

        query_params = {k: v for k, v in query_params.items() if v is not None}

        try:
            obj = Horizons(**query_params)

            table_title = _("{ephem_type} for {target}").format(ephem_type=ephem_type.value, target=target)
            result_table = None

            if ephem_type == EphemType.OBSERVER:
                q = quantities or get_default_quantities_ephem(ctx)
                debug(_("Requesting quantities: {quantities}").format(quantities=q))
                result_table = obj.ephemerides(quantities=q, get_raw_response=False)

            elif ephem_type == EphemType.VECTORS:
                q = quantities
                if q: debug(_("Requesting quantities for vectors: {quantities}").format(quantities=q))
                result_table = obj.vectors(quantities=q, get_raw_response=False) if q else obj.vectors(get_raw_response=False)

            elif ephem_type == EphemType.ELEMENTS:
                try:
                    result_table = obj.elements(get_raw_response=False)
                except Exception:
                    raw = obj.elements(get_raw_response=True)
                    console.print(str(raw))
                try:
                    import datetime
                    now = datetime.datetime.now()
                    today = now.strftime('%Y-%m-%d')
                    eph_table = obj.ephemerides(get_raw_response=False)
                    display_table(ctx, eph_table, title="Ephemerides for today", max_rows=max_rows, show_all_columns=show_all_columns)
                except Exception as e:
                    console.print(f"[red]Ephemerides table error: {e}[/red]")
            
            if result_table is not None and len(result_table) > 0:
                display_table(ctx, result_table, title=table_title, max_rows=max_rows, show_all_columns=show_all_columns)
            else:
                console.print(_("[yellow]No results found for '{target}' with the specified parameters.[/yellow]").format(target=target))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("JPL Horizons object"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    sbdb_app = typer.Typer(
        name="sbdb",
        help=builtins._("Query JPL Small-Body Database (SBDB)."),
        no_args_is_help=False
    )

    @sbdb_app.callback(invoke_without_command=True) # Make query_sbdb the callback
    @global_keyboard_interrupt_handler
    def query_sbdb(ctx: typer.Context,
        target: Optional[str] = typer.Argument(None, help=builtins._("Target small body (e.g., 'Ceres', '1P', '2023 BU').")), # Make target optional for help display
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

        if target is None and not any(arg in ["-h", "--help"] for arg in ctx.args):
            # If no target is provided and not asking for help, show help for this command
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                ctx.get_help()
            full_help_text = help_output_capture.getvalue()
            
            # Remove the "Options" section
            full_help_text = re.sub(r'╭─ Options ─.*?(\n(?:│.*?\n)*)╰─.*─╯', '', full_help_text, flags=re.DOTALL)
            # Remove the "Commands" section
            full_help_text = re.sub(r'╭─ Commands ─.*?(\n(?:│.*?\n)*)╰─.*─╯', '', full_help_text, flags=re.DOTALL)
            
            console.print(full_help_text)
            raise typer.Exit()

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

    app.add_typer(sbdb_app, name="sbdb")
    return app
