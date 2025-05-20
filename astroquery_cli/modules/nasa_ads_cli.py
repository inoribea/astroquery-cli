import typer
from typing import Optional, List
from astropy.table import Table as AstropyTable
from astroquery.nasa_ads import ADS
from ..i18n import get_translator
from ..utils import (
    console,
    display_table,
    handle_astroquery_exception,
    common_output_options,
    save_table_to_file,
)
import os

def get_app():
    import builtins
    _ = builtins._
    app = typer.Typer(
        name="nasa_ads",
        help=builtins._("Query the NASA Astrophysics Data System (ADS)."),
        no_args_is_help=True
    )

    # ================== NASA_ADS_FIELDS =========================
    NASA_ADS_FIELDS = [
        "bibcode",
        "title",
        "author",
        "year",
        "citation_count",
        "abstract",
        "doi",
        "keyword",
        # ...
    ]
    # ============================================================

    ADS.ROW_LIMIT = 25

    @app.command(name="query", help=builtins._("Perform a query on NASA ADS."))
    def query_ads(ctx: typer.Context,
        query_string: str = typer.Argument(..., help=_("ADS query string (e.g., 'author:\"Adam G. Riess\" year:1998', 'bibcode:1998AJ....116.1009R').")),
        fields: Optional[List[str]] = typer.Option(["bibcode", "title", "author", "year", "citation_count"], "--field", help=builtins._("Fields to return.")),
        sort_by: Optional[str] = typer.Option("citation_count", help=builtins._("Sort results by (e.g., 'date', 'citation_count', 'score').")),
        max_pages: int = typer.Option(1, help=builtins._("Maximum number of pages to retrieve.")),
        rows_per_page: int = typer.Option(25, help=builtins._("Number of results per page (max 200 for ADS API).")),
        output_file: Optional[str] = common_output_options["output_file"],
        output_format: Optional[str] = common_output_options["output_format"],
        max_rows_display: int = typer.Option(25, help=builtins._("Maximum number of rows to display. Use -1 for all rows.")),
        show_all_columns: bool = typer.Option(False, "--show-all-cols", help=builtins._("Show all columns in the output table.")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Querying NASA ADS with: '{query_string}'...[/cyan]").format(query_string=query_string))
        if not ADS.TOKEN and "ADS_DEV_KEY" not in os.environ:
            console.print(_("[yellow]Warning: ADS_DEV_KEY environment variable not set. Queries may be rate-limited.[/yellow]"))
        try:
            ads_query = ADS.query_simple(
                query_string,
                fl=fields,
                sort=sort_by,
                max_pages=max_pages,
                rows=min(rows_per_page, 200)
            )

            if ads_query and len(ads_query) > 0:
                result_table = ads_query
                console.print(_("[green]Found {count} result(s) from ADS.[/green]").format(count=len(result_table)))
                display_table(result_table, title=_("ADS Query Results"), max_rows=max_rows_display, show_all_columns=show_all_columns)
                if output_file:
                    save_table_to_file(result_table, output_file, output_format, _("NASA ADS query"))
            else:
                console.print(_("[yellow]No results found for your ADS query.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(e, _("NASA ADS query"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()

    @app.command(name="get-bibtex", help=builtins._("Retrieve BibTeX entries for given bibcodes."))
    def get_bibtex(ctx: typer.Context,
        bibcodes: List[str] = typer.Argument(..., help=builtins._("List of ADS bibcodes.")),
        output_file: Optional[str] = typer.Option(None, "-o", "--output-file", help=builtins._("File to save BibTeX entries (e.g., refs.bib).")),
        test: bool = typer.Option(False, "--test", "-t", help="Enable test mode and print elapsed time.")
    ):
        import time
        start = time.perf_counter() if test else None

        console.print(_("[cyan]Fetching BibTeX for: {bibcode_list}...[/cyan]").format(bibcode_list=', '.join(bibcodes)))
        if not ADS.TOKEN and "ADS_DEV_KEY" not in os.environ:
            console.print(_("[yellow]Warning: ADS_DEV_KEY environment variable not set. Queries may be rate-limited.[/yellow]"))
        try:
            bibtex_entries = []
            for bibcode in bibcodes:
                q = ADS.query_simple(f"bibcode:{bibcode}", fl=['bibtex'])
                if q and 'bibtex' in q.colnames and q['bibtex'][0]:
                    bibtex_entries.append(q['bibtex'][0])
                else:
                    console.print(_("[yellow]Could not retrieve BibTeX for {bibcode}.[/yellow]").format(bibcode=bibcode))

            if bibtex_entries:
                full_bibtex_str = "\n\n".join(bibtex_entries)
                console.print(_("[green]BibTeX entries retrieved:[/green]"))
                console.print(full_bibtex_str)
                if output_file:
                    expanded_output_file = os.path.expanduser(output_file)
                    with open(expanded_output_file, 'w', encoding='utf-8') as f:
                        f.write(full_bibtex_str)
                    console.print(_("[green]BibTeX entries saved to '{file_path}'.[/green]").format(file_path=expanded_output_file))
            else:
                console.print(_("[yellow]No BibTeX entries could be retrieved.[/yellow]"))

        except Exception as e:
            handle_astroquery_exception(e, _("NASA ADS get_bibtex"))
            raise typer.Exit(code=1)

        if test:
            elapsed = time.perf_counter() - start
            print(f"Elapsed: {elapsed:.3f} s")
            raise typer.Exit()
        
    return app
