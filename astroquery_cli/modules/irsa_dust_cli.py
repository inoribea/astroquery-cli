from typing import Optional, List

import typer
from astroquery.irsa_dust import IrsaDust
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console

from ..utils import handle_astroquery_exception, parse_coordinates, display_table, save_table_to_file, common_output_options
from ..i18n import get_translator
import os

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="irsa_dust",
        help=builtins._("Query IRSA dust maps."),
        no_args_is_help=True
    )

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


    @app.command(name="get-extinction", help=builtins._("Get E(B-V) dust extinction values for one or more coordinates."))
    def get_extinction(ctx: typer.Context,
        targets: List[str] = typer.Argument(..., help=builtins._("Object name(s) or coordinate(s) (e.g., 'M31', '10.68h +41.26d', '160.32 41.45'). Can be specified multiple times.")),
        map_name: str = typer.Option("SFD", help=builtins._("Dust map to query ('SFD', 'Planck', 'IRIS'). SFD is Schlegel, Finkbeiner & Davis (1998).")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying IRSA Dust ({map_name}) for extinction at: {targets_str}...[/cyan]").format(map_name=map_name, targets_str=', '.join(targets)))

        coordinates_list = []
        for target_str in targets:
            try:
                coordinates_list.append(parse_coordinates(target_str))
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
                console.print(_("[dim]Fetching extinction for each target individually...[/dim]"))
                for i, coord in enumerate(coordinates_list):
                    console.print(_("[dim]  Processing target {current_num}/{total_num}: {target_name}[/dim]").format(current_num=i+1, total_num=len(coordinates_list), target_name=targets[i]))
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
                display_table(table_result, title=_("IRSA Dust Extinction ({map_name})").format(map_name=map_name))
                if output_file:
                    save_table_to_file(table_result, output_file, output_format, _("IRSA Dust {map_name} extinction").format(map_name=map_name))
            else:
                console.print(_("[yellow]No extinction data returned by IRSA Dust ({map_name}).[/yellow]").format(map_name=map_name))

        except Exception as e:
            handle_astroquery_exception(e, _("IRSA Dust ({map_name}) get_extinction_table").format(map_name=map_name))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="get-map", help=builtins._("Get a FITS image of a dust map for a region."))
    def get_map(ctx: typer.Context,
        target: str = typer.Argument(..., help=builtins._("Central object name or coordinates (e.g., 'M31', '10.68h +41.26d').")),
        radius: str = typer.Option("1 degree", help=builtins._("Radius of the image (e.g., '30arcmin', '1.5deg').")),
        map_name: str = typer.Option("SFD", help=builtins._("Dust map to query ('SFD', 'Planck', 'IRIS').")),
        output_dir: str = typer.Option(".", "--out-dir", help=builtins._("Directory to save the FITS image(s).")),
        filename_prefix: str = typer.Option("dust_map", help=builtins._("Prefix for the output FITS filename(s).")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying IRSA Dust ({map_name}) for map around '{target}' with radius {radius}...[/cyan]").format(map_name=map_name, target=target, radius=radius))

        try:
            coords = parse_coordinates(target)
            rad_quantity = u.Quantity(radius)
        except Exception as e:
            console.print(_("[bold red]Error parsing input: {error}[/bold red]").format(error=e))
            raise typer.Exit(code=1)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            console.print(_("[dim]Created output directory: {output_dir}[/dim]").format(output_dir=output_dir))

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
            handle_astroquery_exception(e, _("IRSA Dust ({map_name}) get_images").format(map_name=map_name))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    return app
