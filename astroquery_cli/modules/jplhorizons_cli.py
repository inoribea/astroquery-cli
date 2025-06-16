import typer
from typing import Optional, List
from enum import Enum 
from astropy.table import Table as AstropyTable
from astroquery.jplhorizons import Horizons, conf as jpl_conf
from astropy.time import Time
from rich.console import Console

from ..utils import display_table, handle_astroquery_exception, global_keyboard_interrupt_handler, console
from .. import i18n
import re # Import re
from io import StringIO # Import StringIO
from contextlib import redirect_stdout # Import redirect_stdout
from astroquery_cli.common_options import setup_debug_context # Import setup_debug_context

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="jplhorizons",
        help=builtins._("Query JPL Horizons ephemeris service."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def jplhorizons_callback(
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

    # ================== JPL_HORIZONS_QUANTITIES =================
    JPL_HORIZONS_QUANTITIES = [
        "1",
        "2",
        "4",
        "8",
        "9",
        "10",
        "12",
        "13",
        "14",
        "19",
        "20",
        "21",
        "23",
        "24",
        "31",
        # ...
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

    @app.command(name="query", help=builtins._("Query ephemerides, orbital elements, or vectors for a target object."))
    @global_keyboard_interrupt_handler
    def query(ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Object ID (e.g., 'Mars', 'Ceres', '2000NM', '@10'). Use '@' prefix for spacecraft ID.")),
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

        console.print(_("[cyan]Querying JPL Horizons for '{target}'...[/cyan]").format(target=target))

        current_server = JPL_SERVERS.get(jpl_server.lower(), jpl_conf.horizons_server)
        if jpl_conf.horizons_server != current_server:
            console.print(_("[dim]Using JPL server: {server}[/dim]").format(server=current_server))
            jpl_conf.horizons_server = current_server

        epoch_dict = None
        if start_time and end_time:
            epoch_dict = {'start': start_time, 'stop': end_time, 'step': step}
            console.print(_("[dim]Using epoch range: {start} to {end} with step {step}[/dim]").format(start=start_time, end=end_time, step=step))
        elif epochs:
            if epochs.startswith("{") and epochs.endswith("}"):
                try:
                    import ast
                    epoch_dict = ast.literal_eval(epochs)
                    console.print(_("[dim]Using epoch dict: {epoch_dict}[/dim]").format(epoch_dict=epoch_dict))
                except (ValueError, SyntaxError) as e:
                    console.print(_("[bold red]Error parsing --epochs as dict: {error}[/bold red]").format(error=e))
                    console.print(_("[yellow]Example: --epochs \"{{'start':'2023-01-01', 'stop':'2023-01-05', 'step':'1d'}}\"[/yellow]"))
                    raise typer.Exit(code=1)
            elif ',' in epochs:
                epoch_dict = [t.strip() for t in epochs.split(',')]
                console.print(_("[dim]Using epoch list: {epoch_list}[/dim]").format(epoch_list=epoch_dict))
            else:
                epoch_dict = epochs
                console.print(_("[dim]Using single epoch: {epoch}[/dim]").format(epoch=epoch_dict))
        elif ephem_type in [EphemType.ELEMENTS, EphemType.VECTORS]:
            epoch_dict = Time.now().jd
            console.print(_("[dim]No epoch specified for {ephem_type}, using current JD: {epoch}[/dim]").format(ephem_type=ephem_type.value, epoch=epoch_dict))
        elif ephem_type == EphemType.OBSERVER:
            import datetime
            now = datetime.datetime.now()
            today = now.strftime('%Y-%m-%d')
            tomorrow = (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            epoch_dict = {'start': today, 'stop': tomorrow, 'step': '1d'}
            console.print(_("[yellow]No epoch specified for OBSERVER, using today as default: {epoch_dict}[/yellow]").format(epoch_dict=epoch_dict))

        # 针对主星体自动设置 id_type
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
                console.print(_("[dim]Requesting quantities: {quantities}[/dim]").format(quantities=q))
                result_table = obj.ephemerides(quantities=q, get_raw_response=False)

            elif ephem_type == EphemType.VECTORS:
                q = quantities
                if q: console.print(_("[dim]Requesting quantities for vectors: {quantities}[/dim]").format(quantities=q))
                result_table = obj.vectors(quantities=q, get_raw_response=False) if q else obj.vectors(get_raw_response=False)

            elif ephem_type == EphemType.ELEMENTS:
                # 先输出物理参数
                try:
                    result_table = obj.elements(get_raw_response=False)
                    # display_table(ctx, result_table, title=table_title, max_rows=max_rows, show_all_columns=show_all_columns) # Will be displayed later
                except Exception:
                    raw = obj.elements(get_raw_response=True)
                    console.print(str(raw))
                # 再输出当天的观测表格
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

    return app
