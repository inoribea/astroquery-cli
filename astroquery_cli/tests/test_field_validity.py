def check_fields(source_fields, official_fields, service_name):
    bad = set(source_fields) - set(official_fields)
    if bad:
        raise AssertionError(
            f"Invalid fields in {service_name}: {bad}\n"
            f"Official allowed fields:\n{sorted(official_fields)}"
        )

def test_simbad_fields():
    from astroquery.simbad import Simbad
    import astroquery_cli.modules.simbad_cli as simbad_cli
    official_fields = set(str(row[0]) for row in Simbad.list_votable_fields())
    check_fields(simbad_cli.SIMBAD_FIELDS, official_fields, "SIMBAD")

def test_alma_fields():
    from astroquery.alma import Alma
    import astroquery_cli.modules.alma_cli as alma_cli
    alma = Alma()
    results = alma.query_object('M83', public=True, maxrec=1)
    official_fields = set(results.colnames)
    check_fields(alma_cli.ALMA_FIELDS, official_fields, "ALMA")
