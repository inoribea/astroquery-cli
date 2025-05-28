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
        "simbad": "simbad",
        "alma": "alma",
        "esasky": "esasky",
        "gaia": "gaia",
        "irsa": "irsa",
        "irsa_dust": "irsa_dust",
        "jplhorizons": "jplhorizons",
        "jplsbdb": "jplsbdb",
        "mast": "mast",
        "nasa_ads": "nasa_ads",
        "ned": "ned",
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
                        # According to the provided documentation, MastClass is the main class
                        official_fields = set(astroquery_module.Mast.get_available_columns())
                    else:
                        # Try common methods to get official fields
                        found_fields = False
                        for attr_name in ["list_fields", "list_votable_fields"]:
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
                            print(f"Could not determine how to get official fields for {module_name.upper()} using common methods. Skipping.")
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
