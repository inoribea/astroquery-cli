import os
import importlib
import sys

def run_field():
    # Add the parent directory to sys.path to allow importing astroquery_cli
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    module_dir = os.path.join(os.path.dirname(__file__), "..", "modules")
    
    # Mapping of astroquery_cli.modules to astroquery modules
    # Add more mappings here if the module name in astroquery is different from astroquery_cli.modules
    MODULE_MAP = {
        "alma": "alma",
        "esasky": "esasky",
        "gaia": "gaia",
        "irsa": "irsa",
        "irsa_dust": "irsa_dust",
        "jplhorizons": "jplhorizons",
        "jplsbdb": "jplsbdb",
        "mast": "mast",
        "ads": "ads",
        "ned": "ned",
        "heasarc": "heasarc",
        "sdss": "sdss",
        "eso": "eso",
        "nist": "nist",
        "simbad": "simbad",
        "splatalogue": "splatalogue",
        "vizier": "vizier",
    }

    for filename in os.listdir(module_dir):
        if filename.endswith("_cli.py") and filename != "__init__.py":
            module_name = filename[:-7]  # Remove '_cli.py'
            
            if module_name not in MODULE_MAP:
                print(f"Skipping {module_name}: No mapping found in MODULE_MAP.")
                continue

            astroquery_module_name = MODULE_MAP[module_name]
            
            try:
                # Dynamically import astroquery_cli module
                cli_module = importlib.import_module(f"astroquery_cli.modules.{module_name}_cli")
                
                # Dynamically import astroquery module
                astroquery_module = importlib.import_module(f"astroquery.{astroquery_module_name}")

                print(f"\nChecking fields for {module_name.upper()}:")

                official_fields = set()
                local_fields = set(getattr(cli_module, f"{module_name.upper()}_FIELDS", []))

                try:
                    if module_name == "simbad":
                        official_fields = set(str(row[0]) for row in astroquery_module.Simbad.list_votable_fields())
                    elif module_name == "alma":
                        alma = astroquery_module.Alma()
                        try:
                            results = alma.query_object('M83', public=True, maxrec=1)
                            if results is not None:
                                official_fields = set(results.colnames)
                            else:
                                print(f"ALMA query returned no results, skipping field check.")
                                continue
                        except Exception as e:
                            print(f"ALMA query failed, skipping field check: {e}")
                            continue
                    elif module_name == "mast":
                        print(f"Note: Automatic field retrieval for MAST is not directly supported by a simple method like 'list_fields'.")
                        print(f"Please refer to MAST documentation for available query parameters and result columns.")
                        continue # Skip field check for MAST
                    elif module_name == "vizier":
                        print(f"Note: VizieR fields are catalog-specific. Please specify a catalog to view its fields.")
                        print(f"Example: `aqc vizier object M31 5arcmin --catalog I/261/gaiadr3 --col all`")
                        continue # Skip field check for VizieR
                    elif module_name == "gaia":
                        try:
                            # Gaia fields are typically retrieved via TAP queries
                            # This is a simplified attempt to get some column names
                            # A more robust solution would involve querying TAP schema
                            tables = astroquery_module.Gaia.load_tables(only_names=True)
                            if tables:
                                # Try to get columns from a known table, e.g., 'gaiadr3.gaia_source'
                                # This is a placeholder and might need adjustment
                                # For now, we'll just acknowledge that it's complex
                                print(f"Note: Gaia fields are extensive and table-specific (TAP service).")
                                print(f"Please refer to Gaia TAP documentation for specific table columns.")
                                continue
                            else:
                                print(f"Gaia.load_tables() returned no tables, skipping field check.")
                                continue
                        except Exception as e:
                            print(f"Error getting Gaia fields: {e}")
                            print(f"Skipping field check for GAIA.")
                            continue
                    elif module_name == "heasarc":
                        try:
                            # Heasarc fields are table-specific. Get tables first, then columns from a table.
                            tables = astroquery_module.Heasarc.get_tables()
                            if tables:
                                # Try to get columns from the first table found
                                first_table = tables[0]
                                columns = astroquery_module.Heasarc.get_columns(first_table)
                                official_fields = set(col.name for col in columns)
                            else:
                                print(f"Heasarc.get_tables() returned no tables, skipping field check.")
                                continue
                        except Exception as e:
                            print(f"Error getting Heasarc fields: {e}")
                            print(f"Skipping field check for HEASARC.")
                            continue
                    elif module_name == "sdss":
                        try:
                            official_fields = set(astroquery_module.SDSS.get_available_columns())
                        except Exception as e:
                            print(f"Error getting SDSS fields: {e}")
                            print(f"Skipping field check for SDSS.")
                            continue
                    elif module_name == "eso":
                        try:
                            # ESO fields are typically retrieved via list_fields()
                            official_fields = set(astroquery_module.ESO.list_fields())
                        except Exception as e:
                            print(f"Error getting ESO fields: {e}")
                            print(f"Skipping field check for ESO.")
                            continue
                    elif module_name == "nist":
                        try:
                            # NIST fields can be obtained from a sample query result
                            results = astroquery_module.NIST.get_transitions(wavelength_range=(1000, 1001), energy_unit='eV', top=1)
                            if results is not None and len(results) > 0:
                                official_fields = set(results.colnames)
                            else:
                                print(f"NIST query returned no results, skipping field check.")
                                continue
                        except Exception as e:
                            print(f"Error getting NIST fields: {e}")
                            print(f"Skipping field check for NIST.")
                            continue
                    else:
                        # Try common methods to get official fields, including a small query if possible
                        found_fields = False
                        for attr_name in ["list_fields", "list_votable_fields", "get_available_columns"]:
                            if hasattr(astroquery_module, attr_name):
                                try:
                                    method = getattr(astroquery_module, attr_name)
                                    if callable(method):
                                        if attr_name == "list_votable_fields":
                                            official_fields = set(str(row[0]) for row in method())
                                        else:
                                            official_fields = set(method())
                                        found_fields = True
                                        break
                                except Exception as e:
                                    print(f"Attempt with {attr_name} failed for {module_name.upper()}: {e}")
                                    pass # Continue to next method if one fails
                        
                        if not found_fields:
                            # Attempt a small query to get column names from results
                            try:
                                if hasattr(astroquery_module, 'query_object'):
                                    # Generic query_object attempt
                                    results = astroquery_module.query_object('M31', radius='0.01 deg', maxrec=1)
                                    if results is not None and len(results) > 0:
                                        official_fields = set(results.colnames)
                                        found_fields = True
                                elif hasattr(astroquery_module, 'query_region'):
                                    # Generic query_region attempt
                                    results = astroquery_module.query_region('M31', radius='0.01 deg', maxrec=1)
                                    if results is not None and len(results) > 0:
                                        official_fields = set(results.colnames)
                                        found_fields = True
                                # Add more specific query attempts for other modules if needed
                            except Exception as e:
                                print(f"Attempt with generic query for {module_name.upper()} failed: {e}")
                                pass # Continue to next method if one fails

                        if not found_fields:
                            if module_name in ["jplhorizons", "jplsbdb"]:
                                print(f"Note: {module_name.upper()} fields are dynamic and depend on the specific query. Automatic field retrieval is not applicable.")
                            else:
                                print(f"Could not determine how to get official fields for {module_name.upper()} using common methods. Please refer to its documentation. Skipping.")
                            continue

                except Exception as e:
                    print(f"Error getting official fields for {module_name.upper()}: {e}")
                    print(f"Skipping field check for {module_name.upper()}.")
                    continue

                extra = local_fields - official_fields
                if extra:
                    print(f"{module_name.upper()}_FIELDS contains invalid fields: {extra}")
                    print(f"Official fields: {sorted(official_fields)}")
                else:
                    print(f"{module_name.upper()}_FIELDS: All fields valid.")

            except ImportError as e:
                print(f"Error importing module for {module_name.upper()}: {e}")
            except Exception as e:
                print(f"{module_name.upper()}_FIELDS check error: {e}")

if __name__ == "__main__":
    run_field()
