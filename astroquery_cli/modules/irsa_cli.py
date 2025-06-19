import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.irsa import Irsa
from astroquery.ipac.irsa import Irsa as IrsaGator
from astroquery.irsa_dust import IrsaDust # Added for dust
from astropy.coordinates import SkyCoord # Ensure this is active
import astropy.units as u # Ensure this is active
import os # Added for dust
import re # Added for dust
from io import StringIO # Added for dust
from contextlib import redirect_stdout # Added for dust
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
    parse_coordinates,
    parse_angle_str_to_quantity,
    global_keyboard_interrupt_handler
)
from ..i18n import get_translator
from astroquery_cli.common_options import setup_debug_context # Added for dust
from astroquery_cli.debug import debug # Added for dust

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="irsa",
        help=builtins._("Query NASA/IPAC Infrared Science Archive (IRSA)."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @app.callback()
    def irsa_callback(
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

    # ================== IRSA_FIELDS =============================
    IRSA_FIELDS = [
        "ra",
        "dec",
        "designation",
        "w1mpro",
        "w2mpro",
        "w3mpro",
        "w4mpro",
        "ph_qual",
        "cc_flags",
        "ext_flg",
        # ...
    ]
    # ============================================================

    # ================== IRSA_DUST_FIELDS ========================
    IRSA_DUST_FIELDS = [
        "E(B-V)",
        "tau_100",
        "IRIS100",
        "Planck_857",
        "Planck_545",
        "Planck_353",
        "Planck_217",
        "Planck_Temp",
        # ...
    ]
    # ============================================================


    Irsa.ROW_LIMIT = 500

    gator_app = typer.Typer(help=builtins._(
        "IRSA Gator catalog operations.\n\n"
        "Example: python -m astroquery_cli.main irsa gator query \"83.822083 -5.391111\" \"30arcsec\" --catalog fp_psc\n"
        "Use 'python -m astroquery_cli.main irsa gator list' to list all available catalogs."
    ))

    @gator_app.command("query")
    @global_keyboard_interrupt_handler
    def query_gator(ctx: typer.Context,
        target_input: str = typer.Argument(
            ...,
            help=builtins._(
                "Coordinates (e.g., '00 42 44.3 +41 16 09') or catalog name (e.g., 'fp_psc')."
            )
        ),
        radius: Optional[str] = typer.Argument(None, help=builtins._("Search radius (e.g., '10arcsec', '0.5deg'). Required if coordinates provided.")),
        catalog: Optional[str] = typer.Option(None, "--catalog", "-C", help=builtins._("Explicitly specify the IRSA catalog name (e.g., 'allwise_p3as_psd'). Defaults to 'gaia_dr3_source'.")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve (comma separated or multiple use). Use 'all' for all columns.")),
        column_filters: Optional[List[str]] = typer.Option(None, "--filter", help=builtins._("Column filters (e.g., 'w1mpro>10', 'ph_qual=A'). Can be specified multiple times.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        import time
        test_mode = ctx.obj.get("test") if ctx.obj else False
        start = time.perf_counter() if test_mode else None

        try:
            final_catalog = catalog
            final_coordinates = None
            final_radius = radius

            coord_obj = parse_coordinates(ctx, target_input)

            if coord_obj: 
                final_coordinates = target_input
                if not final_catalog:
                    final_catalog = "gaia_dr3_source"
                    console.print(_("[yellow]No catalog specified with coordinates. Defaulting to 'gaia_dr3_source' catalog.[/yellow]"))
                if not final_radius:
                    console.print(_("[red]Error: Radius is required when coordinates are provided.[/red]"))
                    raise typer.Exit(code=1)
                console.print(_("[cyan]Querying IRSA catalog '{catalog}' via Gator for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(catalog=final_catalog, coordinates=final_coordinates, radius=final_radius))
                rad_quantity = parse_angle_str_to_quantity(ctx, final_radius)
                result_table: Optional[AstropyTable] = Irsa.query_region(
                    coordinates=coord_obj,
                    radius=rad_quantity,
                    catalog=final_catalog,
                    columns=",".join(columns) if columns else '*',
                )
            else:  
                if final_catalog and final_catalog != target_input:
                    console.print(_("[red]Error: Catalog name provided as both positional argument and --catalog option. Please use only one.[/red]"))
                    raise typer.Exit(code=1)
                final_catalog = target_input
                if final_radius:
                    console.print(_("[red]Error: Catalog name '{target_input}' provided as first argument, but a radius '{radius}' was also provided. Catalog queries do not use radius. Please use 'irsa gator <catalog_name>' without a radius, or provide coordinates and a radius.[/red]").format(target_input=target_input, radius=radius))
                    raise typer.Exit(code=1)
                console.print(_("[cyan]Browsing IRSA catalog '{catalog}' (first {limit} rows)...[/cyan]").format(catalog=final_catalog, limit=Irsa.ROW_LIMIT))
                from astropy.coordinates import SkyCoord
                import astropy.units as u
                coord = SkyCoord("17h45m40.04s", "-29d00m28.1s", frame='icrs')
                rad_quantity = 180 * u.deg
                result_table: Optional[AstropyTable] = Irsa.query_region(
                    coordinates=coord,
                    radius=rad_quantity,
                    catalog=final_catalog
                )

            if result_table and columns and columns != ["all"]:
                col_set = set(result_table.colnames)
                selected_cols = [col for col in columns if col in col_set]
                if selected_cols:
                    result_table = result_table[selected_cols]

            if result_table and column_filters:
                for filt in column_filters:
                    import re
                    m = re.match(r"^(\w+)\s*([<>=!]+)\s*([\w\.\-]+)$", filt)
                    if m:
                        col, op, val = m.groups()
                        if col in result_table.colnames:
                            expr = f"result_table['{col}'] {op} {repr(type(result_table[col][0])(val))}"
                            result_table = result_table[eval(expr)]

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) in '{catalog}'.[/green]").format(count=len(result_table), catalog=final_catalog))
                display_table(ctx, result_table, title=_("IRSA Gator: {catalog}").format(catalog=final_catalog), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_file, output_format, _("IRSA Gator {catalog} query").format(catalog=final_catalog))
            else:
                console.print(_("[yellow]No information found in '{catalog}' for the specified region.[/yellow]").format(catalog=final_catalog))
        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA Gator query for catalog {catalog}").format(catalog=final_catalog if final_catalog else "unknown"))
            raise typer.Exit(code=1)

        if test_mode:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()
    @gator_app.command("list")
    def list_gator_catalogs():
        """
        List all available IRSA Gator catalogs.
        """
        try:
            from astroquery.irsa import Irsa
            catalogs = list(Irsa.list_catalogs())
            from rich.table import Table
            from rich.console import Console
            cols = 5
            rows = (len(catalogs) + cols - 1) // cols
            data = [catalogs[i * rows:(i + 1) * rows] for i in range(cols)]
            data = [col + [""] * (rows - len(col)) for col in data]
            table = Table(title="Available IRSA Gator catalogs")
            for i in range(cols):
                table.add_column(f"Col{i+1}")
            for row in zip(*data):
                table.add_row(*row)
            Console().print(table)
        except Exception as e:
            console.print(f"[red]Failed to fetch catalog list: {e}[/red]")

    @app.command(name="region", help=builtins._("Perform a cone search across multiple IRSA collections."))
    @global_keyboard_interrupt_handler
    def query_region(ctx: typer.Context,
        coordinates: str = typer.Argument(..., help=builtins._("Coordinates (e.g., '10.68h +41.26d', 'M31').")),
        radius: str = typer.Argument(..., help=builtins._("Search radius (e.g., '10arcsec', '0.5deg').")),
        collection: Optional[str] = typer.Option(None, help=builtins._("Specify a collection (e.g., 'allwise', '2MASS'). Leave blank for a general search.")),
        columns: Optional[List[str]] = typer.Option(None, "--col", help=builtins._("Specific columns to retrieve (comma separated or multiple use). Use 'all' for all columns.")),
        column_filters: Optional[List[str]] = typer.Option(None, "--filter", help=builtins._("Column filters (e.g., 'w1mpro>10', 'ph_qual=A'). Can be specified multiple times.")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(20, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table."))
    ):
        console.print(_("[cyan]Performing IRSA cone search for region: '{coordinates}' with radius '{radius}'...[/cyan]").format(coordinates=coordinates, radius=radius))
        try:
            coord = parse_coordinates(ctx, coordinates)
            rad_quantity = parse_angle_str_to_quantity(ctx, radius)

            result_table: Optional[AstropyTable] = Irsa.query_region(
                coordinates=coord,
                radius=rad_quantity,
                collection=collection
            )

            # Apply column selection
            if result_table and columns and columns != ["all"]:
                col_set = set(result_table.colnames)
                selected_cols = [col for col in columns if col in col_set]
                if selected_cols:
                    result_table = result_table[selected_cols]

            # Apply column filters
            if result_table and column_filters:
                for filt in column_filters:
                    import re
                    m = re.match(r"^(\w+)\s*([<>=!]+)\s*([\w\.\-]+)$", filt)
                    if m:
                        col, op, val = m.groups()
                        if col in result_table.colnames:
                            expr = f"result_table['{col}'] {op} {repr(type(result_table[col][0])(val))}"
                            result_table = result_table[eval(expr)]

            if result_table and len(result_table) > 0:
                console.print(_("[green]Found {count} match(es) in IRSA holdings.[/green]").format(count=len(result_table)))
                display_table(ctx, result_table, title=_("IRSA Cone Search Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(ctx, result_table, output_format, _("IRSA cone search query"))
            else:
                console.print(_("[yellow]No information found in IRSA for the specified region{collection_info}.[/yellow]").format(collection_info=_(" in collection {collection}").format(collection=collection) if collection else ''))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA query_region"))
            raise typer.Exit(code=1)

    app.add_typer(gator_app, name="gator")

    dust_app = typer.Typer(
        name="dust",
        help=builtins._("IRSA dust maps operations."),
        invoke_without_command=True, # Add this to allow callback to run without subcommand
        no_args_is_help=False # Set to False for custom handling
    )

    @dust_app.callback()
    def dust_callback(
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

        # Custom help display logic
        if ctx.invoked_subcommand is None and \
           not any(arg in ["-h", "--help"] for arg in ctx.args): # Use ctx.args for subcommand arguments
            # Capture the full help output by explicitly calling the app with --help
            help_output_capture = StringIO()
            with redirect_stdout(help_output_capture):
                try:
                    # Call the app with --help to get the full help output
                    # Pass the current command's arguments to simulate the help call
                    dust_app(ctx.args + ["--help"])
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

    @dust_app.command(name="extinction", help=builtins._("Get E(B-V) dust extinction values for one or more coordinates."))
    @global_keyboard_interrupt_handler
    def get_extinction(ctx: typer.Context,
        targets: List[str] = typer.Argument(..., help=builtins._("Object name(s) or coordinate(s) (e.g., 'M31', '10.68h +41.26d', '160.32 41.45'). Can be specified multiple times.")),
        map_name: str = typer.Option("SFD", help=builtins._("Dust map to query ('SFD', 'Planck', 'IRIS'). SFD is Schlegel, Finkbeiner & Davis (1998).")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying IRSA Dust ({map_name}) for extinction at: {targets_str}...[/cyan]").format(map_name=map_name, targets_str=', '.join(targets)))

        coordinates_list = []
        for target_str in targets:
            try:
                coordinates_list.append(parse_coordinates(ctx, target_str))
            except typer.Exit:
                raise

        if not coordinates_list:
            console.print(_("[red]No valid coordinates parsed.[/red]"))
            raise typer.Exit(code=1)

        try:
            if len(coordinates_list) == 1:
                table_result = IrsaDust.get_extinction_table(coordinates_list[0], map_name=map_name)
            else:
                results = []
                debug(_("Fetching extinction for each target individually..."))
                for i, coord in enumerate(coordinates_list):
                    debug(_("  Processing target {current_num}/{total_num}: {target_name}").format(current_num=i+1, total_num=len(coordinates_list), target_name=targets[i]))
                    try:
                        tbl = IrsaDust.get_extinction_table(coord, map_name=map_name)
                        tbl['target_input'] = targets[i]
                        tbl['RA_input'] = coord.ra.deg
                        tbl['Dec_input'] = coord.dec.deg
                        results.append(tbl)
                    except Exception as e_single:
                        console.print(_("[yellow]Could not get extinction for '{target_name}': {error}[/yellow]").format(target_name=targets[i], error=e_single))
                
                if not results:
                    console.print(_("[yellow]No extinction data retrieved for any target.[/yellow]"))
                    raise typer.Exit()

                from astropy.table import vstack
                table_result = vstack(results)

            if table_result is not None and len(table_result) > 0:
                display_table(ctx, table_result, title=_("IRSA Dust Extinction ({map_name})").format(map_name=map_name))
                if output_file:
                    save_table_to_file(ctx, table_result, output_file, output_format, _("IRSA Dust {map_name} extinction").format(map_name=map_name))
            else:
                console.print(_("[yellow]No extinction data returned by IRSA Dust ({map_name}).[/yellow]").format(map_name=map_name))

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA Dust ({map_name}) get_extinction_table").format(map_name=map_name))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @dust_app.command(name="map", help=builtins._("Get a FITS image of a dust map for a region."))
    @global_keyboard_interrupt_handler
    def get_map(ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Central object name or coordinates (e.g., 'M31', '10.68h +41.26d').")),
        radius: str = typer.Option("1 degree", help=builtins._("Radius of the image (e.g., '30arcmin', '1.5deg').")),
        map_name: str = typer.Option("SFD", help=builtins._("Dust map to query ('SFD', 'Planck', 'IRIS').")),
        output_dir: str = typer.Option(".", "--out-dir", help=builtins._("Directory to save the FITS image(s).")),
        filename_prefix: str = typer.Option("dust_map", help=builtins._("Prefix for the output FITS filename(s).")),
        test: bool = typer.Option(False, "--test", "-t", help=_("Enable test mode and print elapsed time."))
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying IRSA Dust ({map_name}) for map around '{target}' with radius {radius}...[/cyan]").format(map_name=map_name, target=target, radius=radius))

        try:
            coords = parse_coordinates(ctx, target)
            rad_quantity = u.Quantity(radius)
        except Exception as e:
            console.print(_("[bold red]Error parsing input: {error}[/bold red]").format(error=e))
            raise typer.Exit(code=1)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            debug(_("Created output directory: {output_dir}").format(output_dir=output_dir))

        try:
            image_hdulists = IrsaDust.get_images(coords, radius=rad_quantity, map_name=map_name, image_type="ebv")

            if not image_hdulists:
                console.print(_("[yellow]No map images returned by IRSA Dust ({map_name}) for this region.[/yellow]").format(map_name=map_name))
                return

            for i, hdul in enumerate(image_hdulists):
                map_type_suffix = ""
                if 'FILETYPE' in hdul[0].header:
                    map_type_suffix = f"_{hdul[0].header['FILETYPE'].lower().replace(' ', '_')}"
                elif len(image_hdulists) > 1:
                    map_type_suffix = f"_map{i+1}"

                filename = os.path.join(output_dir, f"{filename_prefix}_{map_name.lower()}{map_type_suffix}_{coords.ra.deg:.2f}_{coords.dec.deg:.2f}.fits")
                hdul.writeto(filename, overwrite=True)
                console.print(_("[green]Saved dust map: {filename}[/green]").format(filename=filename))
                hdul.close()

        except Exception as e:
            handle_astroquery_exception(ctx, e, _("IRSA Dust ({map_name}) get_images").format(map_name=map_name))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    app.add_typer(dust_app, name="dust")
    return app
