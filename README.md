# astroquery-cli

The scripts in this project are function calls for the fish shell and rely on the fish shell. They have not been tested on other terminals.

The scripts rely on astroquery. Please install it yourself to ensure normal calls.

(astroquery, astropy, tabulate, numpy, pandas, matplotlib)

## Todo
 Option
 
 - [x] jplhorizons
 - [x] vizier
 - [x] simbad
 - [x] gaia
 - [x] ned
 - [x] exoplanet
 - [x] mast
 - [x] alma
 - [x] skyview
 - [x] splatalogue

 Platform
 
 - [x] python
 - [ ] fish shell completion
 - [x] powershell completion
 - [ ] zsh complation

## astroquery

``` fish
astroquery

Available astroquery commands:
        echo "Available astroquery commands:"
        echo "  astroquery simbad      # Query SIMBAD database"
        echo "  astroquery vizier      # Query VizieR catalogs"
        echo "  astroquery gaia        # Query Gaia database"
        echo "  astroquery skyview     # Get images from SkyView"
        echo "  astroquery ned         # Query NED database"
        echo "  astroquery jplhorizons # Query JPL Horizons for solar system objects"
        echo "  astroquery exoplanet   # Query NASA Exoplanet Archive"
        echo "  astroquery mast        # Query MAST Archive (Hubble, TESS, JWST, etc.)"
        echo "  astroquery alma        # Query ALMA Archive"
        echo "  astroquery splatalogue # Query Splatalogue for spectral lines"
```
