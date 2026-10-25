# Data sources and licences

Every building's `building.json` names its own source, licence and attribution, and so does `manifest.csv`. The licences differ by source:

| Source (`source`) | Licence | Attribution | What we changed |
|---|---|---|---|
| `swiss_dwellings` | CC BY 4.0 | Swiss Dwellings, Standfest et al. / Archilyse, https://zenodo.org/records/7070952 | Converted to our format. Added the shared stair halls (recovered from gaps in the plan), stair and lift cores, building entrances and generated furniture. Every addition is marked `synthetic: true` or `source: generated`. |
| `resplan` | CC BY 4.0 | ResPlan, Agour et al., https://github.com/m-agour/ResPlan | Rescaled to metres, added hallways and door connectivity, and generated furniture. |
| `osm_indoor` | ODbL 1.0 | © OpenStreetMap contributors, https://www.openstreetmap.org/copyright | Projected to local metres and split per level. Added fallback doors where none were mapped, small lift spaces for lifts mapped as nodes, and generated furniture. **This part of the dataset is a derived database under the ODbL. If you share it, it stays under the ODbL.** |
| `procedural` | CC0 1.0 | Generated for the Munich hackathon | Everything is generated. |

Furniture with `source: generated` comes from rules in `config/furniture_catalog.yaml`. Fixtures with `source: dataset` come from the original data.

## Campus explorer map layers

The optional geographic explorer at `/explore` uses these additional sources. Provider attribution
remains visible in the map. These layers do not replace the per-building source and licence metadata.

| Layer | Source and attribution | Licence / terms | Use |
|---|---|---|---|
| Photographic Earth | [Sentinel-2 cloudless](https://s2maps.eu) by EOX IT Services GmbH, containing modified Copernicus Sentinel data 2016 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Raster globe entrance; fades out at city scale. No tiles are committed. |
| Vector campus basemap | [OpenFreeMap](https://openfreemap.org), OpenMapTiles, © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) | OSM-derived data under ODbL | Geographic context and schematic building extrusions. |
| Bavarian aerial imagery | © [Bayerische Vermessungsverwaltung](https://geodaten.bayern.de/opengeodata/) | CC BY 4.0 | DOP20 WMS orthophoto, loaded from the public service. No imagery is committed. |
| Optional photographic 3D | [Google Maps Platform](https://developers.google.com/maps/documentation/javascript/3d/overview) | Proprietary Google Maps Platform terms | Runtime browser-key mode with Google's required attribution. No Google imagery, tiles or credentials are committed. |

The staged Earth-to-building interaction was informed by a separate Claude prototype. This branch
implements the concept within the Locora explorer; it does not import that worktree's files or alter
that worktree. Generated indoor models remain traceable to the source `building.json` and its licence.
