/******************************************************************************
 * ANALOG FINDER · Google Earth Engine pipeline
 *
 * Paste into the Earth Engine Code Editor (code.earthengine.google.com) and press Run.
 *
 *  MODE = 'sites' : measures the factors around every site listed in SITES and
 *                   exports one CSV row per site (analog_sites_features.csv).
 *  MODE = 'scan'  : scores every land pixel on Earth against one Moon/Mars target,
 *                   shows the result as a map layer, and exports the best-matching
 *                   areas as candidate new analogs (analog_candidates_<target>.csv).
 *
 * Exports appear in the Tasks tab (top right): click RUN to send them to Google Drive.
 * Then feed the CSVs to update_map.py to refresh the Analog Finder map.
 *
 * Data (all open):
 *   TerraClimate monthly precipitation .............. aridity (NASA GPM IMERG kept for comparison)
 *   NASA MODIS MOD13A2 NDVI .......................... bare ground
 *   NASA MODIS MOD11A2 day/night land surface temp ... cold, thermal swing, ground-ice proxy
 *   ESA Copernicus GLO-30 DEM ........................ altitude, slope
 *   NASA/JPL ASTER Global Emissivity Database ........ rock-type indices (quartz, carbonate, mafic)
 * Practical info (not scored): NASA SMAP soil moisture, travel time to cities (Oxford MAP),
 *   World Database on Protected Areas.
 ******************************************************************************/

// ============================== SETTINGS =====================================
var MODE = 'sites';            // 'sites', 'build' (once, before global scans) or 'scan'
var TARGET_ID = 'mars-jezero'; // scan only. One of: moon-sp, moon-mare, moon-pit, moon-high,
                               // mars-jezero, mars-gale, mars-arcadia, mars-arsia, mars-meridiani
var START = '2015-01-01';      // climate averaging period
var END = '2025-01-01';
var SITE_RADIUS_M = 10000;     // sites: average over a circle this big around each site
var SCAN_SCALE_M = 5000;       // scan: pixel size. Use 1000 with a smaller SCAN_REGION.
var SCAN_REGION = null;        // null = whole Earth. Example (Egypt):
                               // ee.Geometry.Rectangle([24, 21.5, 37, 32], null, false)
var CANDIDATE_TOP_PCT = 0.5;   // scan: keep the best 0.5 % of land pixels as candidates
var MAX_CANDIDATES = 150;      // scan: how many candidate areas to export
var KNOWN_RADIUS_KM = 100;     // scan: flag candidates within this distance of a listed site
var DRIVE_FOLDER = 'analog_finder';
// Global layers are computed once by MODE 'build' and saved here; global scans read them.
var LAYERS_ASSET = 'projects/astronautsaast/assets/analog_layers_5km';

// ====================== SITES AND TARGETS (from the map) ======================
var SITES = [
  {"id": "atacama", "name": "Atacama Desert (Yungay)", "lat": -24.08, "lon": -69.92, "status": "known", "lith": ["evaporite"]},
  {"id": "haughton", "name": "Haughton Crater, Devon Island", "lat": 75.38, "lon": -89.68, "status": "known", "lith": ["carbonate"]},
  {"id": "deathvalley", "name": "Death Valley", "lat": 36.46, "lon": -116.87, "status": "known", "lith": ["evaporite", "basalt"]},
  {"id": "mdrs", "name": "Hanksville (MDRS)", "lat": 38.41, "lon": -110.79, "status": "known", "lith": ["clay", "sandstone"]},
  {"id": "dryvalleys", "name": "McMurdo Dry Valleys", "lat": -77.5, "lon": 161.8, "status": "known", "lith": ["granite", "basalt"]},
  {"id": "holuhraun", "name": "Holuhraun & Askja", "lat": 64.87, "lon": -16.83, "status": "known", "lith": ["basalt"]},
  {"id": "hawaii", "name": "Mauna Kea / Mauna Loa", "lat": 19.6, "lon": -155.47, "status": "known", "lith": ["basalt"]},
  {"id": "lanzarote", "name": "Lanzarote", "lat": 29.03, "lon": -13.73, "status": "known", "lith": ["basalt"]},
  {"id": "riotinto", "name": "Río Tinto", "lat": 37.69, "lon": -6.59, "status": "known", "lith": ["ironox"]},
  {"id": "svalbard", "name": "Bockfjorden", "lat": 79.45, "lon": 13.35, "status": "known", "lith": ["basalt", "carbonate"]},
  {"id": "meteor", "name": "Meteor Crater", "lat": 35.03, "lon": -111.02, "status": "known", "lith": ["sandstone"]},
  {"id": "cotm", "name": "Craters of the Moon", "lat": 43.42, "lon": -113.52, "status": "known", "lith": ["basalt"]},
  {"id": "mistastin", "name": "Mistastin Lake crater", "lat": 55.88, "lon": -63.31, "status": "studied", "lith": ["anorthosite"]},
  {"id": "allanhills", "name": "Allan Hills blue ice", "lat": -76.7, "lon": 159.7, "status": "studied", "lith": ["ice", "granite"]},
  {"id": "dallol", "name": "Dallol, Danakil Depression", "lat": 14.24, "lon": 40.3, "status": "studied", "lith": ["evaporite", "ironox"]},
  {"id": "qaidam", "name": "Qaidam Basin (Lenghu)", "lat": 38.6, "lon": 93.3, "status": "studied", "lith": ["evaporite", "clay"]},
  {"id": "puna", "name": "Puna de Atacama (Antofalla)", "lat": -25.5, "lon": -67.6, "status": "studied", "lith": ["evaporite", "basalt"]},
  {"id": "kamil", "name": "Kamil Crater", "lat": 22.02, "lon": 26.09, "status": "new", "lith": ["sandstone"]},
  {"id": "gilf", "name": "Gilf Kebir Plateau", "lat": 23.3, "lon": 25.9, "status": "new", "lith": ["sandstone"]},
  {"id": "whitedesert", "name": "White Desert (Farafra)", "lat": 27.33, "lon": 28.05, "status": "studied", "lith": ["carbonate"]},
  {"id": "sandsea", "name": "Great Sand Sea", "lat": 26, "lon": 25, "status": "new", "lith": ["sandstone"]},
  {"id": "lut", "name": "Dasht-e Lut", "lat": 30.4, "lon": 59.3, "status": "new", "lith": ["clay", "basalt"]},
  {"id": "khaybar", "name": "Harrat Khaybar", "lat": 25.2, "lon": 39.9, "status": "new", "lith": ["basalt"]},
  {"id": "bayuda", "name": "Bayuda Volcanic Field", "lat": 18.33, "lon": 32.75, "status": "new", "lith": ["basalt"]},
  {"id": "tibesti", "name": "Emi Koussi, Tibesti", "lat": 19.8, "lon": 18.55, "status": "new", "lith": ["basalt"]},
  {"id": "wabar", "name": "Wabar craters", "lat": 21.5, "lon": 50.47, "status": "new", "lith": ["sandstone"]},
  {"id": "fiskenaesset", "name": "Fiskenæsset anorthosite", "lat": 63.08, "lon": -50.68, "status": "new", "lith": ["anorthosite"]},
  {"id": "scan-kharga-east", "name": "Plateau east of Kharga Oasis", "lat": 25.133, "lon": 30.913, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-abutartur", "name": "Abu Tartur Plateau (north)", "lat": 25.638, "lon": 30.067, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-kharga-edfu", "name": "Limestone plateau between Kharga and Edfu", "lat": 24.525, "lon": 31.075, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-dakhla-north", "name": "Plateau north of Dakhla Oasis", "lat": 25.867, "lon": 28.692, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-kurkur", "name": "Sinn el-Kaddab Plateau near Kurkur", "lat": 23.65, "lon": 32.343, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-nasser-east", "name": "Eastern Desert east of Lake Nasser", "lat": 23.551, "lon": 33.085, "status": "new", "lith": ["clay"]},
  // World-scan candidates (rock type assigned afterwards from ASTER; scan- sites never define rock fingerprints)
  {"id": "scan-atacama-coast", "name": "Atacama coast range (Tarapacá), Chile", "lat": -21.94, "lon": -70.0, "status": "new", "lith": ["evaporite"]},
  {"id": "scan-aksaichin", "name": "Aksai Chin plateau, western Tibet", "lat": 35.55, "lon": 79.52, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-changtang", "name": "Qiangtang (Changtang) plateau, northern Tibet", "lat": 35.33, "lon": 81.59, "status": "new", "lith": ["granite"]},
  {"id": "scan-victoria", "name": "Victoria Island, Canadian Arctic", "lat": 71.57, "lon": -107.73, "status": "new", "lith": ["granite"]},
  {"id": "scan-haruj", "name": "Al Haruj volcanic field, Libya", "lat": 27.07, "lon": 17.82, "status": "new", "lith": ["basalt"]},
  {"id": "scan-qena-east", "name": "Eastern Desert north-east of Qena, Egypt", "lat": 26.79, "lon": 32.77, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-haruj-south", "name": "Desert south of Al Haruj, Libya", "lat": 25.62, "lon": 17.76, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-ngari", "name": "Ngari plateau, western Tibet", "lat": 33.84, "lon": 80.56, "status": "new", "lith": ["granite"]},
  {"id": "scan-ica", "name": "Ica Desert, Peru", "lat": -14.71, "lon": -75.62, "status": "new", "lith": ["clay"]},
  {"id": "scan-moquegua", "name": "Moquegua desert, southern Peru", "lat": -17.45, "lon": -71.21, "status": "new", "lith": ["granite"]},
  {"id": "scan-hohxil", "name": "Hoh Xil plateau, northern Tibet", "lat": 36.22, "lon": 88.78, "status": "new", "lith": ["granite"]},
  {"id": "scan-arkatag", "name": "Arka Tag highlands, northern Tibet", "lat": 36.81, "lon": 85.23, "status": "new", "lith": ["granite"]},
  {"id": "scan-hala", "name": "Qinghai highlands near Hala Lake", "lat": 37.93, "lon": 97.04, "status": "new", "lith": ["granite"]},
  {"id": "scan-pamir", "name": "Eastern Pamir plateau, China", "lat": 38.2, "lon": 74.81, "status": "new", "lith": ["granite"]},
  {"id": "scan-nunavut", "name": "Arctic Nunavut (Gulf of Boothia coast)", "lat": 70.36, "lon": -85.45, "status": "new", "lith": ["granite"]},
  // Documented lava-tube fields (cave catalogue check)
  {"id": "lavabeds", "name": "Lava Beds National Monument", "lat": 41.71, "lon": -121.51, "status": "known", "lith": ["basalt"]},
  {"id": "elmalpais", "name": "El Malpais National Monument", "lat": 34.94, "lon": -108.08, "status": "known", "lith": ["basalt"]},
  {"id": "undara", "name": "Undara lava tubes", "lat": -18.22, "lon": 144.58, "status": "studied", "lith": ["basalt"]},
  {"id": "jawa", "name": "Harrat al-Shaam near Jawa", "lat": 32.33, "lon": 37.05, "status": "new", "lith": ["basalt"]},
  {"id": "payenia", "name": "Payenia lava flows near Puelén", "lat": -37.25, "lon": -67.73, "status": "new", "lith": ["basalt"]},
  // Lunar south pole world-scan candidates
  {"id": "scan-karakoram", "name": "Eastern Karakoram", "lat": 35.10, "lon": 77.46, "status": "new", "lith": ["granite"]},
  {"id": "scan-baffin", "name": "Cumberland Peninsula, Baffin Island", "lat": 67.13, "lon": -65.33, "status": "new", "lith": ["granite"]},
  {"id": "scan-verkhoyansk", "name": "Verkhoyansk Range, Siberia", "lat": 68.38, "lon": 128.53, "status": "new", "lith": ["granite"]},
  {"id": "scan-stelias", "name": "Saint Elias Mountains", "lat": 61.42, "lon": -141.69, "status": "new", "lith": ["granite"]},
  // Best 10 km spots from 250 m Jezero scans
  {"id": "scan-kharga-best", "name": "Plateau south-east of Kharga Oasis", "lat": 24.774, "lon": 31.108, "status": "new", "lith": ["carbonate"]},
  {"id": "scan-aksaichin-best", "name": "Aksai Chin plateau (eastern part)", "lat": 35.428, "lon": 79.947, "status": "new", "lith": ["carbonate"]}
];
var TARGETS = [
  {"id": "moon-sp", "body": "moon", "name": "Lunar south pole", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 0.1, "alt": 1, "relief": 1, "ice": 1, "caves": 0, "crater": 1}, "w": {"arid": 2, "barren": 2, "cold": 3, "swing": 1, "alt": 1, "relief": 2, "lith": 3, "ice": 3, "caves": 0, "crater": 2}, "lith": {"anorthosite": 1, "granite": 0.5, "ice": 0.5, "basalt": 0.3}},
  {"id": "moon-mare", "body": "moon", "name": "Mare Imbrium plains", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 1, "alt": 1, "relief": 0.03, "ice": 0, "caves": 0, "crater": 0.7}, "w": {"arid": 2, "barren": 2, "cold": 1, "swing": 2, "alt": 1, "relief": 3, "lith": 3, "ice": 1, "caves": 0, "crater": 1}, "lith": {"basalt": 1, "anorthosite": 0.3, "granite": 0.2}},
  {"id": "moon-pit", "body": "moon", "name": "Mare Tranquillitatis pit", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 1, "alt": 1, "relief": 0.03, "ice": 0, "caves": 1, "crater": 0.5}, "w": {"arid": 2, "barren": 2, "cold": 1, "swing": 1, "alt": 1, "relief": 1, "lith": 3, "ice": 0, "caves": 4, "crater": 0}, "lith": {"basalt": 1, "anorthosite": 0.2}},
  {"id": "moon-high", "body": "moon", "name": "Descartes highlands", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 1, "alt": 1, "relief": 0.2, "ice": 0, "caves": 0, "crater": 1}, "w": {"arid": 2, "barren": 2, "cold": 1, "swing": 1, "alt": 1, "relief": 2, "lith": 4, "ice": 0, "caves": 0, "crater": 3}, "lith": {"anorthosite": 1, "granite": 0.4, "basalt": 0.3}},
  {"id": "mars-jezero", "body": "mars", "name": "Jezero Crater", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 1, "alt": 1, "relief": 0.15, "ice": 0, "caves": 0, "crater": 1}, "w": {"arid": 3, "barren": 2, "cold": 1, "swing": 1, "alt": 1, "relief": 1, "lith": 4, "ice": 0, "caves": 0, "crater": 1}, "lith": {"carbonate": 1, "clay": 0.9, "evaporite": 0.5, "sandstone": 0.4, "basalt": 0.3}},
  {"id": "mars-gale", "body": "mars", "name": "Gale Crater", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 1, "alt": 1, "relief": 0.67, "ice": 0, "caves": 0, "crater": 1}, "w": {"arid": 3, "barren": 2, "cold": 1, "swing": 1, "alt": 1, "relief": 1, "lith": 4, "ice": 0, "caves": 0, "crater": 1}, "lith": {"evaporite": 1, "clay": 0.9, "ironox": 0.6, "sandstone": 0.6, "carbonate": 0.5}},
  {"id": "mars-arcadia", "body": "mars", "name": "Arcadia Planitia", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 1, "alt": 1, "relief": 0.02, "ice": 1, "caves": 0, "crater": 0}, "w": {"arid": 2, "barren": 2, "cold": 3, "swing": 1, "alt": 1, "relief": 3, "lith": 1, "ice": 4, "caves": 0, "crater": 0}, "lith": {"basalt": 1, "ice": 0.8, "clay": 0.7, "sandstone": 0.6, "granite": 0.5}},
  {"id": "mars-arsia", "body": "mars", "name": "Arsia Mons pits", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 1, "alt": 1, "relief": 0.07, "ice": 0, "caves": 1, "crater": 0}, "w": {"arid": 2, "barren": 2, "cold": 1, "swing": 1, "alt": 2, "relief": 1, "lith": 3, "ice": 0, "caves": 4, "crater": 0}, "lith": {"basalt": 1}},
  {"id": "mars-meridiani", "body": "mars", "name": "Meridiani Planum", "ideal": {"arid": 1, "barren": 1, "cold": 1, "swing": 1, "alt": 1, "relief": 0.02, "ice": 0, "caves": 0, "crater": 0.5}, "w": {"arid": 2, "barren": 2, "cold": 1, "swing": 1, "alt": 1, "relief": 2, "lith": 4, "ice": 0, "caves": 0, "crater": 1}, "lith": {"ironox": 1, "evaporite": 0.8, "sandstone": 0.6, "clay": 0.4}}
];

// ============================ 1. RAW EARTH LAYERS =============================
// Precipitation: TerraClimate (station-calibrated, 4.6 km) is used for scoring, because
// satellite-only IMERG overestimates rain in hyper-arid deserts (e.g. ~90 mm/yr at Yungay,
// Atacama, where gauges record ~1-2 mm/yr). IMERG is kept as 'precip_imerg' for comparison.
var precip = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE')
  .filterDate(START, END).select('pr').mean()
  .multiply(12)                                            // mean monthly total -> mm/yr
  .rename('precip');
var precipImerg = ee.ImageCollection('NASA/GPM_L3/IMERG_MONTHLY_V07')
  .filterDate(START, END).select('precipitation').mean()
  .multiply(24 * 365.25)                                   // mm/hr -> mm/yr
  .rename('precip_imerg');

var lstCol = ee.ImageCollection('MODIS/061/MOD11A2').filterDate(START, END);
var lstDay = lstCol.select('LST_Day_1km').mean().multiply(0.02).subtract(273.15);
var lstNight = lstCol.select('LST_Night_1km').mean().multiply(0.02).subtract(273.15);
var mat = lstDay.add(lstNight).divide(2).rename('mat');    // mean surface temperature, deg C
var dtr = lstDay.subtract(lstNight).rename('dtr');         // day-night surface swing, deg C

var ndvi = ee.ImageCollection('MODIS/061/MOD13A2').filterDate(START, END)
  .select('NDVI').mean().multiply(0.0001).rename('ndvi');

// Copernicus DEM: build a 250 m version once so slope means the same thing for every site and scan.
var demCol = ee.ImageCollection('COPERNICUS/DEM/GLO30').select('DEM');
var dem30 = demCol.mosaic().setDefaultProjection(demCol.first().projection());
var dem250 = dem30.reduceResolution({reducer: ee.Reducer.mean(), maxPixels: 1024})
  .reproject({crs: 'EPSG:4326', scale: 250});
var elev = dem250.rename('elev');
var slope = ee.Terrain.slope(dem250).rename('slope');      // degrees, at 250 m

// ASTER thermal-infrared emissivity indices (Ninomiya et al.)
var aster = ee.Image('NASA/ASTER_GED/AG100_003');
function em(b) { return aster.select('emissivity_band' + b).multiply(0.001); }
var qi = em(11).multiply(em(11)).divide(em(10).multiply(em(12))).rename('qi'); // quartz index
var ci = em(13).divide(em(14)).rename('ci');                                    // carbonate index
var mi = em(12).divide(em(13)).rename('mi');                                    // mafic index

var RAW = ee.Image.cat([precip, precipImerg, ndvi, mat, dtr, elev, slope, qi, ci, mi]);
var RAW_BANDS = ['precip', 'precip_imerg', 'ndvi', 'mat', 'dtr', 'elev', 'slope', 'qi', 'ci', 'mi'];

// ---------- Practical information (shown on the map, NOT part of the match score) ----------
var smap = ee.ImageCollection('NASA/SMAP/SPL3SMP_E/005').filterDate('2016-01-01', '2023-12-01')
  .select('soil_moisture_am').mean().rename('smap');            // NASA SMAP soil moisture, m3/m3 (none where frozen)
var access = ee.Image('Oxford/MAP/accessibility_to_cities_2015_v1_0').select('accessibility')
  .rename('access_min');                                          // travel time to nearest city, minutes (Weiss et al. 2018)
var wdpa = ee.FeatureCollection('WCMC/WDPA/current/polygons');    // World Database on Protected Areas
function protectedName(pt) {
  var hit = wdpa.filterBounds(pt);
  return ee.Algorithms.If(hit.size().gt(0),
    ee.String(hit.first().get('NAME')).cat(' (').cat(ee.String(hit.first().get('DESIG_ENG'))).cat(')'), '');
}
var PRACTICAL_BANDS = ['smap', 'access_min', 'protected'];

// ===================== 2. NORMALISED FACTORS (same as the map) ================
function c01(img) { return img.max(0).min(1); }
function factors(raw) {
  var p = raw.select('precip').max(0), m = raw.select('mat');
  return ee.Image.cat([
    c01(ee.Image(1).subtract(p.add(1).log10().divide(3))).rename('arid'),
    // NDVI below ~0.1 is bare rock or soil in MODIS, so 0.1 counts as fully bare
    c01(ee.Image(1).subtract(raw.select('ndvi').unmask(0).subtract(0.1).divide(0.3))).rename('barren'),
    c01(ee.Image(30).subtract(m).divide(60)).rename('cold'),
    c01(raw.select('dtr').divide(45)).rename('swing'),
    c01(raw.select('elev').divide(4500)).rename('alt'),
    c01(raw.select('slope').divide(20)).rename('relief'),
    // ground-ice proxy: mean surface temperature below -2 C -> 1, below +2 C -> 0.5
    m.lt(-2).multiply(0.5).add(m.lt(2).multiply(0.5)).rename('ice')
  ]);
}
var FACTOR_KEYS = ['arid', 'barren', 'cold', 'swing', 'alt', 'relief', 'ice'];

// ============================ helpers =========================================
function siteFeature(s, radius) {
  return ee.Feature(ee.Geometry.Point([s.lon, s.lat]).buffer(radius),
    {id: s.id, name: s.name, lat: s.lat, lon: s.lon, lith: s.lith[0],
     ref: s.id.indexOf('scan-') === 0 ? 0 : 1});   // scan candidates never define rock fingerprints
}
var sitePolys = ee.FeatureCollection(SITES.map(function (s) { return siteFeature(s, SITE_RADIUS_M); }));
var sitePoints = ee.FeatureCollection(SITES.map(function (s) {
  return ee.Feature(ee.Geometry.Point([s.lon, s.lat]), {id: s.id, name: s.name, status: s.status});
}));
var siteStats = RAW.reduceRegions({
  collection: sitePolys, reducer: ee.Reducer.mean(), scale: 250, tileScale: 8
});

// ============================ MODE: sites =====================================
if (MODE === 'sites') {
  var full = ee.Image.cat([RAW, smap, access]).reduceRegions({
    collection: sitePolys, reducer: ee.Reducer.mean(), scale: 250, tileScale: 8
  });
  var out = full.map(function (f) {
    return f.set('protected', protectedName(f.geometry().centroid(10))).setGeometry(null);
  });
  print('Site factors (first 30). Export from the Tasks tab for the full table.', out.limit(30));
  Map.addLayer(RAW.select('dtr'), {min: 0, max: 35, palette: ['1a2b3c', 'e3804f', 'fff2c0']}, 'Day-night swing (C)', false);
  Map.addLayer(RAW.select('precip'), {min: 0, max: 800, palette: ['fff2c0', 'e3804f', '1a2b3c']}, 'Precipitation (mm/yr)', false);
  Map.addLayer(sitePoints, {color: 'ffffff'}, 'Sites');
  Export.table.toDrive({
    collection: out,
    description: 'analog_sites_features',
    folder: DRIVE_FOLDER,
    fileFormat: 'CSV',
    selectors: ['id', 'name', 'lat', 'lon'].concat(RAW_BANDS).concat(PRACTICAL_BANDS)
  });
}

// ===================== scan-resolution layers (used by build and scan) ========
var GLOBE = ee.Geometry.Polygon([[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]]], null, false);
function scanLayers(scaleM) {
  var proj = ee.Projection('EPSG:4326').atScale(scaleM);
  // Aggregate fine layers to the scan pixel size (mean of the finer pixels inside each one).
  function toScan(img) {
    return img.reduceResolution({reducer: ee.Reducer.mean(), maxPixels: 65536}).reproject(proj);
  }
  // Terrain: USGS GMTED2010 (native ~232 m, 56S-84N); Antarctica falls back to Copernicus.
  var gmted = ee.Image('USGS/GMTED2010_FULL').select('mea');
  var demCoarse = dem30.reproject(proj);
  var elevScan = toScan(gmted).unmask(demCoarse).rename('elev');
  var slopeScan = toScan(ee.Terrain.slope(gmted)).unmask(ee.Terrain.slope(demCoarse)).rename('slope');
  return ee.Image.cat([
    ee.Image.cat([precip, precipImerg, ndvi, mat, dtr]).reproject(proj),
    elevScan, slopeScan, toScan(qi), toScan(ci), toScan(mi)
  ]).toFloat();
}

// ============================ MODE: build =====================================
// Run once. Computes every Earth layer for the whole globe at 5 km as a background task
// (no interactive memory limit) and saves it as an asset, so global scans are fast.
if (MODE === 'build') {
  Export.image.toAsset({
    image: scanLayers(5000),
    description: 'analog_layers_build',
    assetId: LAYERS_ASSET,
    region: GLOBE, crs: 'EPSG:4326', scale: 5000, maxPixels: 1e10,
    pyramidingPolicy: {'.default': 'mean'},
    shardSize: 64                     // small compute tiles keep memory use low
  });
  print('Go to the Tasks tab and RUN analog_layers_build. When it finishes, the asset ' +
        LAYERS_ASSET + ' exists and global scans (SCAN_REGION = null) will read from it.');
}

// ============================ MODE: scan ======================================
if (MODE === 'scan') {
  var T = null;
  TARGETS.forEach(function (t) { if (t.id === TARGET_ID) { T = t; } });
  if (!T) { throw new Error('Unknown TARGET_ID: ' + TARGET_ID); }

  var region = SCAN_REGION || GLOBE;
  // Global scans read the saved 5 km layers; regional scans compute layers on the fly.
  var proj = ee.Projection('EPSG:4326').atScale(SCAN_REGION ? SCAN_SCALE_M : 5000);
  if (!SCAN_REGION) { SCAN_SCALE_M = 5000; }
  var rawScan = SCAN_REGION ? scanLayers(SCAN_SCALE_M) : ee.Image(LAYERS_ASSET);
  var F = factors(rawScan);
  var land = rawScan.select('mat').mask().and(rawScan.select('dtr').mask());

  // --- rock type: compare ASTER indices with the average of reference sites of each rock type ---
  // A class's fingerprint is the mean (qi, ci, mi) of listed sites whose main rock is that class.
  var withAster = siteStats.filter(ee.Filter.eq('ref', 1)).filter(ee.Filter.notNull(['qi', 'ci', 'mi']));
  var sd = {
    qi: ee.Number(withAster.aggregate_total_sd('qi')),
    ci: ee.Number(withAster.aggregate_total_sd('ci')),
    mi: ee.Number(withAster.aggregate_total_sd('mi'))
  };
  var LITH_CLASSES = ['basalt', 'anorthosite', 'evaporite', 'carbonate', 'clay', 'sandstone', 'ironox', 'granite'];
  function classSimilarity(cls) {
    var ref = siteStats.filter(ee.Filter.eq('ref', 1)).filter(ee.Filter.eq('lith', cls))
      .filter(ee.Filter.notNull(['qi', 'ci', 'mi']));
    var sim = ee.Image(0);
    ['qi', 'ci', 'mi'].forEach(function (k) {
      var mu = ee.Number(ref.aggregate_mean(k));
      var z = rawScan.select(k).subtract(ee.Image.constant(mu)).divide(ee.Image.constant(sd[k]));
      sim = sim.add(z.pow(2));
    });
    sim = sim.divide(3).multiply(-0.5).exp();                       // 1 = identical fingerprint
    return ee.Image(ee.Algorithms.If(ref.size().gt(0), sim, ee.Image(0))).rename(cls);
  }
  var simStack = ee.Image.cat(LITH_CLASSES.map(classSimilarity));
  var lithMatch = ee.Image(0);
  Object.keys(T.lith).forEach(function (cls) {
    if (LITH_CLASSES.indexOf(cls) >= 0) {
      lithMatch = lithMatch.max(simStack.select(cls).multiply(T.lith[cls]));
    }
  });
  lithMatch = lithMatch.unmask(0.3);                              // no ASTER data (e.g. ice): neutral
  var lithGuess = simStack.toArray().arrayArgmax().arrayGet([0]).rename('lith_idx');

  // --- weighted match, same formula as the map (caves and craters need catalogs, so they are skipped) ---
  var num = ee.Image(0), wsum = 0;
  FACTOR_KEYS.forEach(function (k) {
    var w = T.w[k] || 0;
    if (w > 0) {
      var ideal = (T.ideal[k] === undefined) ? 0 : T.ideal[k];
      num = num.add(ee.Image(1).subtract(F.select(k).subtract(ideal).abs()).multiply(w));
      wsum += w;
    }
  });
  num = num.add(lithMatch.multiply(T.w.lith || 0));
  wsum += (T.w.lith || 0);
  var match = num.divide(wsum).updateMask(land).rename('match');

  var skipped = ['caves', 'crater'].filter(function (k) { return (T.w[k] || 0) > 0; });
  print('Target:', T.name, '| factors used:', FACTOR_KEYS.concat(['lith']),
        skipped.length ? '| not in scan (no global layer): ' + skipped.join(', ') : '');

  // --- best areas ---
  var thr = ee.Number(match.reduceRegion({
    reducer: ee.Reducer.percentile([100 - CANDIDATE_TOP_PCT]), geometry: region,
    scale: SCAN_SCALE_M * 2, maxPixels: 1e10, bestEffort: true
  }).values().get(0));
  if (SCAN_REGION) { print('Match threshold for the top ' + CANDIDATE_TOP_PCT + '% of land:', thr); }

  var top = match.gte(thr).selfMask();
  var areas = top.addBands(match).reduceToVectors({
    geometry: region, crs: 'EPSG:4326', scale: SCAN_SCALE_M, geometryType: 'polygon', eightConnected: true,
    reducer: ee.Reducer.mean(), labelProperty: 'zone', maxPixels: 1e10, bestEffort: true, tileScale: 8
  });
  var minArea = 2 * SCAN_SCALE_M * SCAN_SCALE_M / 1e6;            // at least two pixels
  var candidates = areas.map(function (f) {
    var g = f.geometry();
    return f.set({area_km2: g.area(1000).divide(1e6)});
  }).filter(ee.Filter.gte('area_km2', minArea))
    .sort('mean', false).limit(MAX_CANDIDATES)
    .map(function (f) {
      var g = f.geometry();
      var c = g.centroid(1000);
      var vals = rawScan.reduceRegion({
        reducer: ee.Reducer.mean(), geometry: g, crs: 'EPSG:4326', scale: SCAN_SCALE_M, maxPixels: 1e8, bestEffort: true
      });
      var li = lithGuess.reduceRegion({
        reducer: ee.Reducer.mode(), geometry: g, crs: 'EPSG:4326', scale: SCAN_SCALE_M, maxPixels: 1e8, bestEffort: true
      }).get('lith_idx');
      var pv = ee.Image.cat([smap, access]).reduceRegion({
        reducer: ee.Reducer.mean(), geometry: g, crs: 'EPSG:4326', scale: SCAN_SCALE_M, maxPixels: 1e8, bestEffort: true
      });
      var near = sitePoints.filterBounds(c.buffer(KNOWN_RADIUS_KM * 1000));
      var coords = c.coordinates();
      return ee.Feature(null, vals).set({
        target: TARGET_ID,
        lon: coords.get(0), lat: coords.get(1),
        match: f.get('mean'),
        area_km2: f.get('area_km2'),
        smap: pv.get('smap'), access_min: pv.get('access_min'), protected: protectedName(c),
        near_listed_site: ee.Algorithms.If(near.size().gt(0), near.first().get('id'), ''),
        lith_guess: ee.Algorithms.If(ee.Algorithms.IsEqual(li, null), 'unknown',
                                     ee.List(LITH_CLASSES).get(ee.Number(li).round().int()))
      });
    });

  Map.setOptions('SATELLITE');
  Map.addLayer(match, {min: 0.4, max: 1, palette: ['0d141c', '26374a', '7a5a48', 'e3804f', 'ffe1b8']}, 'Match: ' + T.name);
  Map.addLayer(match.gte(0.8).selfMask(), {palette: ['5cc8a8']}, 'Match 80% or more', false);
  Map.addLayer(sitePoints, {color: 'ffffff'}, 'Listed sites');
  if (SCAN_REGION) {
    Map.centerObject(SCAN_REGION);
    Map.addLayer(top, {palette: ['5cc8a8']}, 'Top ' + CANDIDATE_TOP_PCT + '% areas');
    print('Best candidate areas (first 20)', candidates.limit(20));
  } else {
    print('Global scan: the candidate list is too big to preview here. ' +
          'Run analog_candidates_' + TARGET_ID.replace('-', '_') + ' in the Tasks tab.');
  }

  Export.table.toDrive({
    collection: candidates,
    description: 'analog_candidates_' + TARGET_ID.replace('-', '_'),
    folder: DRIVE_FOLDER,
    fileFormat: 'CSV',
    selectors: ['target', 'lon', 'lat', 'match', 'area_km2', 'near_listed_site', 'lith_guess'].concat(RAW_BANDS).concat(PRACTICAL_BANDS)
  });
  Export.image.toDrive({
    image: match.toFloat(), description: 'analog_match_' + TARGET_ID.replace('-', '_'),
    folder: DRIVE_FOLDER, region: region, crs: 'EPSG:4326', scale: SCAN_SCALE_M, maxPixels: 1e10
  });
}
