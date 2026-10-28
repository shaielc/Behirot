# 2026 map sources

The notebook's locality boundary layer follows the map-data pipeline documented
in [`RavBogard/israelielection`](https://github.com/RavBogard/israelielection/blob/main/scripts/vote-map/build.mts).
The processed TopoJSON retains a `src` property on each geometry (`mot2026` or
`cbs2008`).

- **Ministry of Transport locality polygons:** `accid_muni.zip`, EPSG:2039,
  keyed by `CITYCODE` (the CBS locality code). The source contains 1,174
  locality polygons but represents the West Bank as a single feature with code
  9999, so that feature is not used.
  [Official data.gov.il download](https://data.gov.il/dataset/7ac4505d-dfd8-4ebf-90e5-eefdefd292de/resource/42097396-d215-44eb-b979-509f29873865/download/accid_muni.zip)
- **CBS 2008 statistical areas:** statistical-area polygons dissolved by
  `SEMEL_YISH` to supply locality boundaries, principally for West Bank
  localities missing from the Transport layer. This is a 2008 census layer and
  its own description says it is not a reference for reconstructing official
  locality boundaries.
  [Official data.gov.il download](https://data.gov.il/dataset/6b729165-dc9c-49b3-afc6-eceabd8fef70/resource/3b88cb58-62cd-43ea-9156-7b81ead557b1/download/50400-2008.7z)
Election results come from the Central Elections Committee's 2026 `expb.csv`
ballot-box export. The notebook aggregates ballot boxes by `סמל ישוב` and joins
those locality totals to the boundary geometry through `code`.
