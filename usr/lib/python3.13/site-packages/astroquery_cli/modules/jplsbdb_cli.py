import typer
from typing import Optional, List, Any
from astropy.table import Table as AstropyTable
from astroquery.jplsbdb import SBDB
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
)

app = typer.Typer(
    name="jplsbdb",
    help="Query JPL Small-Body Database (SBDB)."
)

@app.command(name="query", help="Query JPL SBDB for a small body.")
def query_sbdb(
    target: str = typer.Argument(..., help="Target small body (e.g., 'Ceres', '1P', '2023 BU')."),
    id_type: Optional[str] = typer.Option("auto", help="Type of target identifier ('name', 'des', 'moid', 'spk', 'auto')."),
    phys_par: bool = typer.Option(False, "--phys-par", help="Include physical parameters."),
    orb_el: bool = typer.Option(False, "--orb-el", help="Include orbital elements."),
    close_approach: bool = typer.Option(False, "--ca-data", help="Include close-approach data."),
    radar_obs: bool = typer.Option(False, "--radar-obs", help="Include radar observation data."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(20, help="Maximum number of rows to display for tables. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in output tables.")
):
    console.print(f"[cyan]Querying JPL SBDB for target: '{target}'...[/cyan]")
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
            console.print(f"[green]Data found for '{target}'.[/green]")
            # SBDB query returns a dictionary-like object (astropy.table.Row or custom dict)
            # We can try to display it nicely. If it's a Row, it behaves like a one-row table.
            if isinstance(sbdb_query, AstropyTable) and len(sbdb_query) > 0 : # if it returns a table
                 display_table(sbdb_query, title=f"JPL SBDB Data for {target}", max_rows=max_rows_display, show_all_columns=show_all_columns)
                 if output_file:
                    save_table_to_file(sbdb_query, output_file, output_format, f"JPL SBDB query for {target}")

            elif hasattr(sbdb_query, 'items'): # If it's dict-like (e.g. astropy.table.Row)
                console.print(f"[bold magenta]SBDB Data for: {sbdb_query.get('object', {}).get('fullname', target)}[/bold magenta]")
                output_data = {}
                for key, value in sbdb_query.items():
                    if isinstance(value, AstropyTable):
                        console.print(f"\n[bold underline]Table: {key}[/bold underline]")
                        display_table(value, title=f"{key} for {target}", max_rows=max_rows_display, show_all_columns=show_all_columns)
                        if output_file: # Save tables separately
                             save_table_to_file(value, output_file.replace(".", f"_{key}."), output_format, f"JPL SBDB {key} for {target}")
                    elif isinstance(value, dict) or isinstance(value, list):
                        console.print(f"\n[bold]{key}:[/bold]")
                        console.print_json(data=value)
                        output_data[str(key)] = value
                    else:
                        console.print(f"[bold]{key}:[/bold] {value}")
                        output_data[str(key)] = str(value)

                if output_file and not any(isinstance(v, AstropyTable) for v in sbdb_query.values()):
                    # Save non-table data as JSON if no tables were primary output
                    import json
                    try:
                        with open(output_file if '.json' in output_file else output_file + ".json", 'w') as f:
                            json.dump(output_data, f, indent=2)
                        console.print(f"[green]Primary data saved to {output_file if '.json' in output_file else output_file + '.json'}[/green]")
                    except Exception as json_e:
                        console.print(f"[red]Could not save non-table data as JSON: {json_e}[/red]")
            else:
                 console.print(str(sbdb_query))

        else:
            console.print(f"[yellow]No information found for target '{target}'.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, "JPL SBDB query")
        raise typer.Exit(code=1)
