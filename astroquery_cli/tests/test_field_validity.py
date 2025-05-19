import pytest

def check_fields(source_fields, official_fields, service_name):
    bad = set(source_fields) - set(official_fields)
    if bad:
        raise AssertionError(
            f"Invalid fields in {service_name}: {bad}\n"
            f"Official allowed fields:\n{sorted(official_fields)}"
        )


def check_fields(source_fields, official_fields, service_name):
    bad = set(source_fields) - set(official_fields)
    if bad:
        raise AssertionError(
            f"Invalid fields in {service_name}: {bad}\n"
            f"Official allowed fields:\n{sorted(official_fields)}"
        )

# ---------------- SIMBAD ------------------
def test_simbad_fields():
    from astroquery.simbad import Simbad
    import astroquery_cli.modules.simbad_cli as simbad_cli
    official_fields = set(Simbad.list_votable_fields())
    check_fields(simbad_cli.VOTABLE_FIELDS, official_fields, "SIMBAD")

# ---------------- ALMA --------------------
def test_alma_fields():
    from astroquery.alma import Alma
    import astroquery_cli.modules.alma_cli as alma_cli
    official_fields = set(Alma().get_dataarchive_table().colnames)
    check_fields(alma_cli.ALMA_VOTABLE_FIELDS, official_fields, "ALMA")

# ---------------- ESASKY ------------------
def test_esasky_fields():
    # 官方API暂无获得可选字段的直接方式，需手动维护
    import astroquery_cli.modules.esasky_cli as esasky_cli
    official_fields = set(esasky_cli.OFFICIAL_FIELDS)    # 手动维护
    check_fields(esasky_cli.ESASKY_FIELDS, official_fields, "ESASKY")

# ---------------- GAIA --------------------
def test_gaia_fields():
    from astroquery.gaia import Gaia
    import astroquery_cli.modules.gaia_cli as gaia_cli
    # 建议每次测试时都动态查官方表，防止Dr3更新字段后CLI没同步
    official_fields = set(Gaia.load_table('gaiadr3.gaia_source').columns)
    check_fields(gaia_cli.GAIA_FIELDS, official_fields, "GAIA")

# ---------------- IRSA --------------------
def test_irsa_fields():
    # 没有官方API获取全部字段列表，请在CLI中维护OFFICIAL_FIELDS
    import astroquery_cli.modules.irsa_cli as irsa_cli
    official_fields = set(irsa_cli.OFFICIAL_FIELDS)
    check_fields(irsa_cli.IRSA_FIELDS, official_fields, "IRSA")

# ---------------- IRSA DUST ---------------
def test_irsa_dust_fields():
    # 同上，需手动维护
    import astroquery_cli.modules.irsa_dust_cli as irsa_dust_cli
    official_fields = set(irsa_dust_cli.OFFICIAL_FIELDS)
    check_fields(irsa_dust_cli.IRSA_DUST_FIELDS, official_fields, "IRSA_DUST")

# ---------------- JPL HORIZONS ------------
def test_jplhorizons_fields():
    # 无官方字段API，手动维护
    import astroquery_cli.modules.jplhorizons_cli as jplhorizons_cli
    official_fields = set(jplhorizons_cli.OFFICIAL_FIELDS)
    check_fields(jplhorizons_cli.JPL_HORIZONS_FIELDS, official_fields, "JPL_HORIZONS")

# ---------------- JPL SBDB ---------------
def test_jplsbdb_fields():
    import astroquery_cli.modules.jplsbdb_cli as jplsbdb_cli
    official_fields = set(jplsbdb_cli.OFFICIAL_FIELDS)
    check_fields(jplsbdb_cli.JPL_SBDB_FIELDS, official_fields, "JPL_SBDB")

# ---------------- MAST -------------------
def test_mast_fields():
    # 无法直接获取所有官方字段，需手动维护
    import astroquery_cli.modules.mast_cli as mast_cli
    official_fields = set(mast_cli.OFFICIAL_FIELDS)
    check_fields(mast_cli.MAST_FIELDS, official_fields, "MAST")

# ---------------- NASA ADS ---------------
def test_nasa_ads_fields():
    # 同样需手动维护
    import astroquery_cli.modules.nasa_ads_cli as nasa_ads_cli
    official_fields = set(nasa_ads_cli.OFFICIAL_FIELDS)
    check_fields(nasa_ads_cli.NASA_ADS_FIELDS, official_fields, "NASA_ADS")

# ---------------- NED --------------------
def test_ned_fields():
    # 同样需手动维护
    import astroquery_cli.modules.ned_cli as ned_cli
    official_fields = set(ned_cli.OFFICIAL_FIELDS)
    check_fields(ned_cli.NED_FIELDS, official_fields, "NED")

# ---------------- SPLATALOGUE -------------
def test_splatalogue_fields():
    from astroquery.splatalogue import Splatalogue
    import astroquery_cli.modules.splatalogue_cli as splatalogue_cli
    # SPLATALOGUE 无法直接获全部支持字段
    official_fields = set(splatalogue_cli.OFFICIAL_FIELDS)
    check_fields(splatalogue_cli.SPLATALOGUE_FIELDS, official_fields, "SPLATALOGUE")

# ---------------- VIZIER -----------------
def test_vizier_fields():
    from astroquery.vizier import Vizier
    import astroquery_cli.modules.vizier_cli as vizier_cli
    table_id = "I/239/hip_main"  # 例: Hipparcos星表；按你实际的重要catalog编号替换
    official_fields = set(Vizier.get_catalogs(table_id)[0].colnames)
    check_fields(vizier_cli.VIZIER_FIELDS, official_fields, "VIZIER")
