# astroquery_cli/modules/irsa_dust_cli.py
from typing import Optional, List

import typer
from astroquery.irsa_dust import IrsaDust
from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console

from ..utils import handle_astroquery_exception, parse_coordinates, display_table, save_table_to_file, common_output_options
import os

console = Console()
app = typer.Typer(
    name="irsa-dust",
    help="Query IRSA dust extinction maps (SFD98, Planck, etc.). ☁️"
)

@app.command(name="get-extinction", help="Get E(B-V) dust extinction values for one or more coordinates.")
def get_extinction(
    targets: List[str] = typer.Argument(..., help="Object name(s) or coordinate(s) (e.g., 'M31', '10.68h +41.26d', '160.32 41.45'). Can be specified multiple times."),
    map_name: str = typer.Option("SFD", help="Dust map to query ('SFD', 'Planck', 'IRIS'). SFD is Schlegel, Finkbeiner & Davis (1998)."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
):
    """
    Retrieves E(B-V) dust extinction values from IRSA for the given target(s).
    Example: aq irsa-dust get-extinction M101 "00h42m44.3s +41d16m09s"
    """
    console.print(f"[cyan]Querying IRSA Dust ({map_name}) for extinction at: {', '.join(targets)}...[/cyan]")

    coordinates_list = []
    for target_str in targets:
        try:
            coordinates_list.append(parse_coordinates(target_str))
        except typer.Exit:
            # parse_coordinates already prints error and exits, re-raise to stop processing
            raise

    if not coordinates_list:
        console.print("[red]No valid coordinates parsed.[/red]")
        raise typer.Exit(code=1)

    try:
        # IrsaDust.get_extinction_table expects a single SkyCoord or a list of SkyCoords
        # For a single target, astroquery might return a Table directly.
        # For multiple targets, it returns a list of Tables (one per target).
        # Let's standardize to always work with a list of SkyCoords for simplicity.
        if len(coordinates_list) == 1:
            table_result = IrsaDust.get_extinction_table(coordinates_list[0], map_name=map_name)
        else:
            # get_extinction_table doesn't directly support a list of coords to return one table.
            # We need to call it for each.
            results = []
            console.print("[dim]Fetching extinction for each target individually...[/dim]")
            for i, coord in enumerate(coordinates_list):
                console.print(f"[dim]  Processing target {i+1}/{len(coordinates_list)}: {targets[i]}[/dim]")
                try:
                    tbl = IrsaDust.get_extinction_table(coord, map_name=map_name)
                    # Add original target info for clarity
                    tbl['target_input'] = targets[i]
                    tbl['RA_input'] = coord.ra.deg
                    tbl['Dec_input'] = coord.dec.deg
                    results.append(tbl)
                except Exception as e_single:
                    console.print(f"[yellow]Could not get extinction for '{targets[i]}': {e_single}[/yellow]")
            
            if not results:
                console.print("[yellow]No extinction data retrieved for any target.[/yellow]")
                raise typer.Exit()

            from astropy.table import vstack
            table_result = vstack(results)


        if table_result is not None and len(table_result) > 0:
            display_table(table_result, title=f"IRSA Dust Extinction ({map_name})")
            if output_file:
                save_table_to_file(table_result, output_file, output_format, f"IRSA Dust {map_name} extinction")
        else:
            console.print(f"[yellow]No extinction data returned by IRSA Dust ({map_name}).[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, f"IRSA Dust ({map_name}) get_extinction_table")
        raise typer.Exit(code=1)

@app.command(name="get-map", help="Get a FITS image of a dust map for a region.")
def get_map(
    target: str = typer.Argument(..., help="Central object name or coordinates (e.g., 'M31', '10.68h +41.26d')."),
    radius: str = typer.Option("1 degree", help="Radius of the image (e.g., '30arcmin', '1.5deg')."),
    map_name: str = typer.Option("SFD", help="Dust map to query ('SFD', 'Planck', 'IRIS')."),
    output_dir: str = typer.Option(".", "--out-dir", help="Directory to save the FITS image(s)."),
    filename_prefix: str = typer.Option("dust_map", help="Prefix for the output FITS filename(s).")
):
    """
    Retrieves FITS image(s) of the specified dust map from IRSA for a region.
    The image is for E(B-V). Temperature and other maps might also be returned depending on the service.
    Example: aq irsa-dust get-map M31 --radius 0.5deg --out-dir ./dust_images
    """
    console.print(f"[cyan]Querying IRSA Dust ({map_name}) for map around '{target}' with radius {radius}...[/cyan]")

    try:
        coords = parse_coordinates(target)
        rad_quantity = u.Quantity(radius)
    except Exception as e:
        console.print(f"[bold red]Error parsing input: {e}[/bold red]")
        raise typer.Exit(code=1)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        console.print(f"[dim]Created output directory: {output_dir}[/dim]")

    try:
        # IrsaDust.get_images returns a list of astropy.io.fits.HDUList objects
        image_hdulists = IrsaDust.get_images(coords, radius=rad_quantity, map_name=map_name, image_type="ebv") # Specify E(B-V)

        if not image_hdulists:
            console.print(f"[yellow]No map images returned by IRSA Dust ({map_name}) for this region.[/yellow]")
            return

        for i, hdul in enumerate(image_hdulists):
            # Construct a meaningful filename
            # Header might contain info, e.g., hdul[0].header.get('OBJECT')
            # For SFD, it usually returns one E(B-V) map.
            # For Planck, it might return E(B-V), T, Psi, etc.
            map_type_suffix = ""
            if 'FILETYPE' in hdul[0].header: # Planck specific
                map_type_suffix = f"_{hdul[0].header['FILETYPE'].lower().replace(' ', '_')}"
            elif len(image_hdulists) > 1: # Generic suffix if multiple files
                map_type_suffix = f"_map{i+1}"

            filename = os.path.join(output_dir, f"{filename_prefix}_{map_name.lower()}{map_type_suffix}_{coords.ra.deg:.2f}_{coords.dec.deg:.2f}.fits")
            hdul.writeto(filename, overwrite=True)
            console.print(f"[green]Saved dust map: {filename}[/green]")
            hdul.close()

    except Exception as e:
        handle_astroquery_exception(e, f"IRSA Dust ({map_name}) get_images")
        raise typer.Exit(code=1)
