# Analog Finder: Earth Engine pipeline

This replaces the map's estimated site values with values measured from open satellite data, and scans the whole Earth for new analog sites.

## Files

| File | What it does |
|---|---|
| `analog_finder_gee.js` | Earth Engine script with two modes: `sites` and `scan` |
| `update_map.py` | Loads the CSVs from Earth Engine into the map (standard-library Python only) |
| `sites_meta.json` | Site names, rock types, notes, and cave and crater flags (catalog facts the satellites can't measure) |
| `analog-finder.html` | The map page that `update_map.py` updates |

## One-time setup

1. Sign in at https://code.earthengine.google.com with a Google account and register a Cloud project for noncommercial use. Earth Engine is free for research and education.
2. Create a new script, paste in all of `analog_finder_gee.js`, and save it.

## Step 1: Measure the listed sites

1. Leave `MODE = 'sites'` and press **Run**. The console prints the first 30 rows.
2. Open the **Tasks** tab, click **RUN** next to `analog_sites_features`, and wait for it to finish. The file goes to Google Drive in the `analog_finder` folder.
3. Download `analog_sites_features.csv`.

## Step 2: Scan Earth for new analogs

**First, once only:** set `MODE = 'build'`, press **Run**, then in **Tasks** run `analog_layers_build`. This computes all the Earth layers for the whole globe at 5 km as a background job and saves them to your project as `analog_layers_5km`. It can take an hour or more. Global scans read this saved file, which makes them fast and keeps them within the free tier's memory limit. Regional scans (with `SCAN_REGION` set) don't need it.


1. Set `MODE = 'scan'` and pick a `TARGET_ID`, for example `mars-jezero`.
2. Press **Run**. The map shows the match layer (bright = good match). Turn on the "Match 80% or more" layer to see the best areas in green. A global scan doesn't preview the candidate list in the Console because it's too heavy; it comes from the export.
3. In **Tasks**, run `analog_candidates_<target>` (the CSV of candidate areas) and, if you want the raster, `analog_match_<target>` (a GeoTIFF).
4. Repeat for other targets.

For a sharper regional scan, such as Egypt:

```js
var SCAN_SCALE_M = 1000;
var SCAN_REGION = ee.Geometry.Rectangle([24, 21.5, 37, 32], null, false);
```

## Step 3: Update the map

```bash
python3 update_map.py analog-finder.html \
  --sites analog_sites_features.csv \
  --candidates analog_candidates_mars_jezero.csv analog_candidates_moon_pit.csv \
  --top 5 --out analog-finder-updated.html
```

Open `analog-finder-updated.html` in a browser. Each site's detail panel now says whether its values were computed from satellite data or are still estimates. New scan candidates appear as green diamonds named "Scan candidate …".

## How each factor is measured

| Factor | Dataset (Earth Engine ID) | Value used |
|---|---|---|
| Aridity | `IDAHO_EPSCOR/TERRACLIMATE` (`pr`) | Mean precipitation 2015–2024, mm/yr. NASA GPM IMERG (`NASA/GPM_L3/IMERG_MONTHLY_V07`) is exported alongside as `precip_imerg` |
| Bare ground | `MODIS/061/MOD13A2` | Mean NDVI (0.1 or less counts as fully bare) |
| Cold | `MODIS/061/MOD11A2` | Mean of day and night land surface temperature, °C |
| Thermal swing | `MODIS/061/MOD11A2` | Day minus night land surface temperature, °C |
| Altitude | `COPERNICUS/DEM/GLO30` | Mean elevation (averaged to 250 m) |
| Relief | `COPERNICUS/DEM/GLO30` | Mean slope computed at 250 m, degrees |
| Altitude, relief (scan only) | `USGS/GMTED2010_FULL` (`mea`, native 232 m) | Same measures without reprojecting the whole globe; Antarctica falls back to Copernicus |
| Rock type | `NASA/ASTER_GED/AG100_003` | Quartz, carbonate and mafic emissivity indices |
| Ground ice | `MODIS/061/MOD11A2` | Proxy: mean surface temperature below −2 °C gives 1, below +2 °C gives 0.5 |

Normalization and weights match the map exactly, so a site's score in Earth Engine equals its score on the map.

**Rock type in the scan:** for each rock class (basalt, carbonate, sandstone and so on), the script averages the ASTER indices of the listed sites with that main rock. That average is the class "fingerprint". Every pixel is then compared with each fingerprint, so adding more well-known sites to `SITES` improves the rock-type estimate automatically.

## Limits to state in your presentation

- **Surface vs. air temperature.** MODIS measures the ground surface, which gets much hotter than the air in deserts. That is closer to what a rover or habitat experiences, but it is not the air-temperature climate figure people usually quote.
- **Ground ice is a temperature proxy,** not a permafrost map. Listed sites keep their catalogued permafrost flag.
- **The rock-type indices are coarse.** Three thermal-infrared ratios separate quartz-rich, carbonate and mafic rocks reasonably well. They can't identify anorthosite or specific sulfates reliably. Treat the scan's `lith_guess` as a lead to check against geologic maps.
- **Caves and impact craters aren't in the scan,** because no global raster of them exists. They come from catalogs (lava-tube inventories, the Earth Impact Database) for the listed sites only.
- **Precipitation source.** Satellite-only GPM IMERG overestimates rain in hyper-arid deserts (about 90 mm/yr at Yungay, where gauges record 1–2 mm), so scoring uses station-calibrated TerraClimate. Both are exported, and the comparison is a finding worth showing.
- **Resolution:** TerraClimate is about 4.6 km, GPM about 11 km, MODIS 1 km and ASTER GED 100 m. The scan averages everything to `SCAN_SCALE_M`.
- **ASTER GED (2000–2008) has gaps over ice sheets.** There, rock-type matching uses a neutral 0.3.
