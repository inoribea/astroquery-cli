def run_field():
    # SIMBAD 字段校验
    try:
        from astroquery.simbad import Simbad
        import astroquery_cli.modules.simbad_cli as simbad_cli
        official_fields = set(str(row[0]) for row in Simbad.list_votable_fields())
        local_fields = set(getattr(simbad_cli, "SIMBAD_FIELDS", []))
        extra = local_fields - official_fields
        if extra:
            print(f"SIMBAD_FIELDS contains invalid fields: {extra}")
            print(f"Official fields: {sorted(official_fields)}")
        else:
            print("SIMBAD_FIELDS: All fields valid.")
    except Exception as e:
        print(f"SIMBAD_FIELDS check error: {e}")

    # ALMA 字段校验
    try:
        from astroquery.alma import Alma
        import astroquery_cli.modules.alma_cli as alma_cli
        alma = Alma()
        try:
            results = alma.query_object('M83', public=True, maxrec=1)
        except Exception as e:
            print(f"ALMA query failed, skipping test: {e}")
            return
        official_fields = set(results.colnames)
        local_fields = set(getattr(alma_cli, "ALMA_FIELDS", []))
        extra = local_fields - official_fields
        if extra:
            print(f"ALMA_FIELDS contains invalid fields: {extra}")
            print(f"Official fields: {sorted(official_fields)}")
        else:
            print("ALMA_FIELDS: All fields valid.")
    except Exception as e:
        print(f"ALMA_FIELDS check error: {e}")

if __name__ == "__main__":
    run_field()
