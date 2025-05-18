import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.nasa_ads import ADS
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
)
import os

app = typer.Typer(
    name="ads",
    help="Query NASA Astrophysics Data System (ADS)."
)

# ADS.TOKEN = os.environ.get("ADS_DEV_KEY", None) # Users can set ADS_DEV_KEY for higher limits
ADS.ROW_LIMIT = 25 # Default for simple query

@app.command(name="query", help="Perform a query on NASA ADS.")
def query_ads(
    query_string: str = typer.Argument(..., help="ADS query string (e.g., 'author:\"Adam G. Riess\" year:1998', 'bibcode:1998AJ....116.1009R')."),
    fields: Optional[List[str]] = typer.Option(["bibcode", "title", "author", "year", "citation_count"], "--field", help="Fields to return."),
    sort_by: Optional[str] = typer.Option("citation_count", help="Sort results by (e.g., 'date', 'citation_count', 'score')."),
    max_pages: int = typer.Option(1, help="Maximum number of pages to retrieve."),
    rows_per_page: int = typer.Option(25, help="Number of results per page (max 200 for ADS API)."),
    output_file: Optional[str] = common_output_options["output_file"],
    output_format: Optional[str] = common_output_options["output_format"],
    max_rows_display: int = typer.Option(25, help="Maximum number of rows to display. Use -1 for all rows."),
    show_all_columns: bool = typer.Option(False, "--show-all-cols", help="Show all columns in the output table.")
):
    console.print(f"[cyan]Querying NASA ADS with: '{query_string}'...[/cyan]")
    if not ADS.TOKEN and "ADS_DEV_KEY" not in os.environ:
        console.print("[yellow]Warning: ADS_DEV_KEY environment variable not set. Queries may be rate-limited.[/yellow]")
    try:
        ads_query = ADS.query_simple(
            query_string,
            fl=fields,
            sort=sort_by,
            max_pages=max_pages,
            rows=min(rows_per_page, 200) # ADS API limit
        )

        if ads_query and len(ads_query) > 0:
            # query_simple returns an astropy.table.Table
            result_table = ads_query
            console.print(f"[green]Found {len(result_table)} result(s) from ADS.[/green]")
            display_table(result_table, title=f"ADS Query Results", max_rows=max_rows_display, show_all_columns=show_all_columns)
            if output_file:
                save_table_to_file(result_table, output_file, output_format, "NASA ADS query")
        else:
            console.print(f"[yellow]No results found for your ADS query.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, "NASA ADS query")
        raise typer.Exit(code=1)

@app.command(name="get-bibtex", help="Retrieve BibTeX entries for given bibcodes.")
def get_bibtex(
    bibcodes: List[str] = typer.Argument(..., help="List of ADS bibcodes."),
    output_file: Optional[str] = typer.Option(None, "-o", "--output-file", help="File to save BibTeX entries (e.g., refs.bib).")
):
    console.print(f"[cyan]Fetching BibTeX for: {', '.join(bibcodes)}...[/cyan]")
    if not ADS.TOKEN and "ADS_DEV_KEY" not in os.environ:
        console.print("[yellow]Warning: ADS_DEV_KEY environment variable not set. Queries may be rate-limited.[/yellow]")
    try:
        bibtex_entries = []
        for bibcode in bibcodes:
            q = ADS.query_simple(f"bibcode:{bibcode}", fl=['bibtex'])
            if q and 'bibtex' in q.colnames and q['bibtex'][0]:
                bibtex_entries.append(q['bibtex'][0])
            else:
                console.print(f"[yellow]Could not retrieve BibTeX for {bibcode}.[/yellow]")

        if bibtex_entries:
            full_bibtex_str = "\n\n".join(bibtex_entries)
            console.print("[green]BibTeX entries retrieved:[/green]")
            console.print(full_bibtex_str)
            if output_file:
                expanded_output_file = os.path.expanduser(output_file)
                with open(expanded_output_file, 'w', encoding='utf-8') as f:
                    f.write(full_bibtex_str)
                console.print(f"[green]BibTeX entries saved to '{expanded_output_file}'.[/green]")
        else:
            console.print("[yellow]No BibTeX entries could be retrieved.[/yellow]")

    except Exception as e:
        handle_astroquery_exception(e, "NASA ADS get_bibtex")
        raise typer.Exit(code=1)
