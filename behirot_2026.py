from io import BytesIO
from pathlib import Path
import json

import pandas as pd
import requests


chrome_headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

base_url = "https://media26.bechirot.gov.il/files"
output_directory = Path(__file__).parent / "2026"
files = ("expb.csv",)
required_columns = {"שם ישוב", "סמל ישוב", "מצביעים", "כשרים"}


def read_election_csv(source, source_name):
    election_data = pd.read_csv(source, encoding="utf-8-sig")
    if not required_columns.issubset(election_data.columns):
        raise RuntimeError(
            f"{source_name} did not contain the expected election columns"
        )
    return election_data


def download_election_file(filename):
    url = f"{base_url}/{filename}?"
    output_path = output_directory / filename

    # The election server occasionally answers with its HTML landing page and
    # a 200 status. Parse and validate before replacing the cached export.
    try:
        response = requests.get(url, headers=chrome_headers, timeout=30)
        response.raise_for_status()
        election_data = read_election_csv(BytesIO(response.content), url)
    except (requests.RequestException, pd.errors.ParserError, RuntimeError):
        if not output_path.exists():
            raise
        return read_election_csv(output_path, output_path)

    output_directory.mkdir(exist_ok=True)
    output_path.write_bytes(response.content)

    return election_data


def topojson_to_geojson(path):
    """Convert the locality-boundary TopoJSON used by the map to GeoJSON."""
    topology = json.loads(Path(path).read_text(encoding="utf-8"))
    transform = topology.get("transform")
    decoded_arcs = []

    for encoded_arc in topology["arcs"]:
        if transform:
            x = y = 0
            arc = []
            scale_x, scale_y = transform["scale"]
            translate_x, translate_y = transform["translate"]
            for delta_x, delta_y in encoded_arc:
                x += delta_x
                y += delta_y
                arc.append([x * scale_x + translate_x, y * scale_y + translate_y])
        else:
            arc = encoded_arc
        decoded_arcs.append(arc)

    def decode_ring(arc_indexes):
        ring = []
        for arc_index in arc_indexes:
            arc = decoded_arcs[~arc_index][::-1] if arc_index < 0 else decoded_arcs[arc_index]
            ring.extend(arc[1:] if ring else arc)
        return ring

    features = []
    for collection in topology["objects"].values():
        for geometry in collection["geometries"]:
            if geometry["type"] == "Polygon":
                coordinates = [decode_ring(ring) for ring in geometry["arcs"]]
            elif geometry["type"] == "MultiPolygon":
                coordinates = [
                    [decode_ring(ring) for ring in polygon]
                    for polygon in geometry["arcs"]
                ]
            else:
                continue
            features.append({
                "type": "Feature",
                "properties": geometry.get("properties", {}),
                "geometry": {"type": geometry["type"], "coordinates": coordinates},
            })

    return {"type": "FeatureCollection", "features": features}


if __name__ == "__main__":
    for filename in files:
        election_data = download_election_file(filename)
        print(f"Saved {filename}: {len(election_data):,} rows, "
              f"{len(election_data.columns):,} columns")
        print(election_data.head())
