# Credits and data-use notice

STORMWATCH is an independent open-source-style research prototype developed for this project; it is not an official NOAA, NHC, NWS or USAF software product.

Observations and metadata used in the example fixtures were transcribed from official NOAA/NHC public advisory and HDOB bulletins. For authoritative current conditions, use the source agencies directly. Advisory links and timestamps are included for traceability.

The offline low-resolution coastline/land vectors were derived from the geographic boundaries bundled with Matplotlib Basemap (GSHHG/GSHHS geographic boundary data). No attempt is made to represent them as surveyed navigation-quality boundaries; neither borders nor coastlines are suitable for navigation, aviation, or risk decisions.

The interface and Python/JS application source are newly created in this project. Python dependencies and external data products remain subject to their respective licenses and terms. Check these before commercial/public deployments.

NHC: https://www.nhc.noaa.gov/
GSHHG: https://www.soest.hawaii.edu/pwessel/gshhg/

Aircraft adapter attribution (v0.6): public ADS-B aircraft-sighting data retrieved from ADSB.lol and its contributors, licensed under the Open Database License (ODbL) v1.0: https://opendatacommons.org/licenses/odbl/1-0/ . Provider documentation: https://www.adsb.lol/docs/open-data/api/ . STORMWATCH does not redistribute stored ADS-B datasets in the application ZIP; any subsequent data redistribution remains subject to ODbL terms. NOAA aircraft identity references: https://www.omao.noaa.gov/aircraft-operations/noaa-hurricane-hunters and https://www.omao.noaa.gov/aircraft-operations/aircraft/gulfstream-iv-sp .

Map tile attribution (v0.7): detailed online tiles and street/place labels © OpenStreetMap contributors, https://www.openstreetmap.org/copyright. Tiles are fetched only in the interactive viewport from tile.openstreetmap.org in the user's browser. No OSM tile imagery is bundled with or bulk-cached by this software. Comply with https://operations.osmfoundation.org/policies/tiles/ and switch to a licensed dedicated provider before high-traffic production deployment. Offline coastline assets remain separate, as credited above.

Optional mapped satellite imagery (v0.7): NOAA nowCOAST ArcGIS time-enabled map service, https://nowcoast.noaa.gov/arcgis/rest/services/nowcoast/sat_meteo_imagery_time/MapServer. Layer IDs are selected from the upstream service metadata. Its time extent should not be mistaken for the verified acquisition timestamp of each output pixel. Availability depends on current NOAA service access; not tested live in this build environment.


### v0.8 forecast guidance

NHC ATCF public aids are objective forecast guidance and differ from official advisory forecasts and best tracks. Source: https://ftp.nhc.noaa.gov/atcf/aid_public/ . NOAA/NHC model identifiers and data access vary by cyclone and run. ECMWF IFS/AIFS and Google DeepMind experimental AI forecast licensing may differ from NHC data; this build only fetches publicly distributed A-deck records and does not redistribute proprietary weather products. Google Weather Lab provides separate experimental forecasts under its own terms. No HAFS-AI source is verified.
