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
polling_places_url = (
    "https://www.over.org.il/api/tables/"
    "govmap_243675_16d94168_777c7b7e/features"
)
polling_places_filename = "polling_places.csv"
polling_place_columns = (
    "objectId,unique_id,regional_committee_code,regional_committee_name,"
    "settlement_code,settlement_name,polling_station_code,cluster_code,"
    "polling_station_address,polling_station_location,accessible,"
    "special_accessibility,eligible_voters,_first_seen"
)
required_polling_place_columns = {
    "ברזל", "סמל ישוב בחירות", "סמל קלפי", "כתובת קלפי",
    "קו אורך", "קו רוחב",
}


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


def read_polling_places(path):
    polling_places = pd.read_csv(
        path,
        encoding="utf-8-sig",
        dtype={"ברזל": "string", "סמל קלפי": "string"},
    )
    if not required_polling_place_columns.issubset(polling_places.columns):
        raise RuntimeError(f"{path} did not contain the expected polling-place columns")
    return polling_places


def download_polling_places():
    """Download the final polling-place table and cache it as a plain CSV.

    The source retains previous snapshots. Keeping the newest row for each
    ``ברזל`` ID produces the current national table rather than duplicates.
    """
    output_path = output_directory / polling_places_filename

    try:
        features = []
        offset = 0
        while True:
            response = requests.get(
                polling_places_url,
                params={
                    "columns": polling_place_columns,
                    "limit": 5000,
                    "offset": offset,
                },
                headers=chrome_headers,
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            page = payload["features"]
            features.extend(page)
            if len(page) < 5000:
                break
            offset += len(page)

        records = []
        for feature in features:
            properties = feature["properties"]
            geometry = feature["geometry"]
            coordinates = geometry["coordinates"]
            if geometry["type"] == "MultiPoint":
                coordinates = coordinates[0]
            longitude, latitude = coordinates
            records.append({
                "סמל ועדה": properties["regional_committee_code"],
                "שם ועדה": properties["regional_committee_name"],
                "סמל ישוב בחירות": properties["settlement_code"],
                "שם ישוב בחירות": properties["settlement_name"],
                "סמל קלפי": properties["polling_station_code"],
                "סמל רכוז": properties["cluster_code"],
                "כתובת קלפי": properties["polling_station_address"],
                "מקום קלפי": properties["polling_station_location"],
                "נגישה": properties["accessible"],
                "נגישה מיוחדת": properties["special_accessibility"],
                "בוחרי כנסת בפועל": properties["eligible_voters"],
                "ברזל": properties["unique_id"],
                "קו אורך": longitude,
                "קו רוחב": latitude,
                "_first_seen": properties["_first_seen"],
            })

        polling_places = pd.DataFrame.from_records(records)
        polling_places = (
            polling_places.sort_values("_first_seen")
            .drop_duplicates("ברזל", keep="last")
            .drop(columns="_first_seen")
            .sort_values(["סמל ישוב בחירות", "סמל קלפי"])
            .reset_index(drop=True)
        )
        if len(polling_places) < 10_000:
            raise RuntimeError("The polling-place download was unexpectedly incomplete")
        if polling_places[["קו אורך", "קו רוחב"]].isna().any().any():
            raise RuntimeError("The polling-place download contained missing coordinates")
    except (requests.RequestException, ValueError, KeyError, TypeError, RuntimeError):
        if not output_path.exists():
            raise
        return read_polling_places(output_path)

    output_directory.mkdir(exist_ok=True)
    polling_places.to_csv(output_path, index=False, encoding="utf-8-sig")
    return read_polling_places(output_path)


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
    polling_places = download_polling_places()
    print(f"Saved {polling_places_filename}: {len(polling_places):,} rows")
    print(polling_places.head())
