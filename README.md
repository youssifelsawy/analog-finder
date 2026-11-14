# Analog Finder

NASA Space Apps Challenge 2026 · Challenge: Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars

**Team AstronautsAAST:** Youssif Mohamed Ahmed Elsawy, Moustafa Ahmed Mahmoud El Ashry, Mazen Wael Mamdouh, Mahmoud Hany Sharaby · Arab Academy for Science, Technology and Maritime Transport, Egypt

**Live interactive map: https://youssifelsawy.github.io/analog-finder/**

Analog Finder scores places on Earth against 9 Moon and Mars sites (lunar south pole, Mare Imbrium, Mare Tranquillitatis pit, Descartes highlands; Jezero, Gale, Arcadia Planitia, Arsia Mons pits, Meridiani Planum) using open data from NASA, ESA and USGS. 59 Earth sites are measured on 10 factors, and whole-world scans find new candidate areas.

## Main findings
- Jezero Crater: two plateaus never proposed for Jezero top the world: Aksai Chin, between the Karakoram and Kunlun ranges, and the limestone plateau east of Kharga Oasis, Egypt, tied at 75%. NASA EMIT shows Kharga's carbonate is uniform (99–100% of detections at 6 spots) and Aksai Chin's patchy (56% and 11%), and Kharga is 4 h from a city: the practical first field site.
- Prior work: Egypt's Western Desert was compared to Mars in NASA-funded studies by Farouk El-Baz and colleagues (1979–82); its carbonate plateaus were not proposed as a Jezero analog.
- Moon lava-tube pit: Harrat Khaybar, Saudi Arabia, #1 ahead of documented lava-tube fields.
- Lunar south pole: the eastern Karakoram is the best match outside Antarctica.
- Mars base ice (Arcadia): the Tibetan Plateau and eastern Aksai Chin (74%) is the best match outside Antarctica.
- Gale and Meridiani: the Atacama coast range, Chile, is a new #1.
- Validation: 13 of 15 known analog pairs rank in the top quarter; 2,000 random re-weightings test robustness.

## Open the results
- `index.html`: the interactive map (the same file as the live link); works in any browser, even offline.
- `Analog-Finder-Space-Apps-demo-7-slides.pdf`: the submission demo.
- `Analog-Finder-talk-21-slides.pdf`: the full talk with all results.
- `rehearsal-and-submission.md`: talk script, Q&A and submission checklist.

## Folders
- `earth-engine/`: Google Earth Engine script (`MODE = 'sites' | 'build' | 'scan'`), site list, target fingerprints, and `update_map.py`, which loads Earth Engine, permafrost and EMIT results into the map.
- `processing/`: Python tools for EMIT minerals, ESA permafrost, MOLA slopes, scan figures, candidate areas from scan images, rock type from ASTER, and the offline map build.
- `target-measurement/`: GeoJSON boxes for LROC QuickMap (Moon), the Google Colab script for MOLA (Mars), and the EMIT point lists for AppEEARS.
- `validation/`: validation and sensitivity checks.
- `data/`: measured site values, permafrost and EMIT summaries, Moon values read in QuickMap (LOLA, Lunar Prospector, Diviner), validation and final rankings.
- `figures/`: world and 250 m scan maps, Sentinel-2 views, map screenshot.

## Use of AI
Code, slides and text were written with AI assistance (Claude, Anthropic). The team chose the challenge and targets, ran all Earth Engine, QuickMap, Colab and AppEEARS measurements, and checked the results.
