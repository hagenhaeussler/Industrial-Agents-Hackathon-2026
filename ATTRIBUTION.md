# Data sources and licences

Every building's `building.json` names its own source, licence and attribution, and so does `manifest.csv`. The licences differ by source:

| Source (`source`) | Licence | Attribution | What we changed |
|---|---|---|---|
| `swiss_dwellings` | CC BY 4.0 | Swiss Dwellings, Standfest et al. / Archilyse, https://zenodo.org/records/7070952 | Converted to our format. Added the shared stair halls (recovered from gaps in the plan), stair and lift cores, building entrances and generated furniture. Every addition is marked `synthetic: true` or `source: generated`. |
| `resplan` | CC BY 4.0 | ResPlan, Agour et al., https://github.com/m-agour/ResPlan | Rescaled to metres, added hallways and door connectivity, and generated furniture. |
| `osm_indoor` | ODbL 1.0 | © OpenStreetMap contributors, https://www.openstreetmap.org/copyright | Projected to local metres and split per level. Added fallback doors where none were mapped, small lift spaces for lifts mapped as nodes, and generated furniture. **This part of the dataset is a derived database under the ODbL. If you share it, it stays under the ODbL.** |
| `procedural` | CC0 1.0 | Generated for the Munich hackathon | Everything is generated. |

Furniture with `source: generated` comes from rules in `config/furniture_catalog.yaml`. Fixtures with `source: dataset` come from the original data.

## Workspace arrival map

The brief geographic entrance reuses the Earth style and footprint-derived camera bearing from
`feature/campus-explorer`. Its 17 real building locations/outlines come from that branch's OSM catalogue
(© OpenStreetMap contributors, ODbL). No evaluation data or generated indoor models are included.

- Photographic Earth: [Sentinel-2 cloudless](https://s2maps.eu) by EOX IT Services GmbH, containing modified
  Copernicus Sentinel data 2016, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Campus basemap: [OpenFreeMap](https://openfreemap.org), OpenMapTiles, ©
  [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), OSM-derived data under ODbL.

Attribution remains visible in the map. Imagery is requested at runtime; no imagery or credentials are committed.
