import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request
from urllib.request import urlopen
import xml.etree.ElementTree as ET


BGG_API_BASE = "https://boardgamegeek.com/xmlapi2"


class BggApiError(Exception):
    pass

def _load_bgg_token():
    token_file = os.getenv("BGG_API_TOKEN_FILE")

    if token_file:
        path = Path(token_file).expanduser()

        try:
            token = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise BggApiError(
                f"Impossible de lire le fichier du token BGG : {path}"
            ) from exc

        if not token:
            raise BggApiError(
                f"Le fichier du token BGG est vide : {path}"
            )

        return token

    # Compatibilité temporaire avec l’ancienne configuration.
    token = os.getenv("BGG_API_TOKEN", "").strip()

    if token:
        return token

    raise BggApiError(
        "Configure BGG_API_TOKEN_FILE pour utiliser BoardGameGeek."
    )


def _fetch_xml(path, params):
    token = _load_bgg_token()

    url = f"{BGG_API_BASE}/{path}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "RacinePoir Ludotheque",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return ET.fromstring(response.read())
    except (HTTPError, URLError, TimeoutError, ET.ParseError) as exc:
        raise BggApiError("BoardGameGeek est temporairement indisponible.") from exc


def search_games(query, limit=8):
    root = _fetch_xml("search", {"query": query, "type": "boardgame"})
    matches = []

    for item in root.findall("item")[:limit]:
        name = item.find("name")
        year = item.find("yearpublished")
        matches.append({
            "bgg_id": item.get("id"),
            "title": name.get("value") if name is not None else "Jeu sans titre",
            "year_published": year.get("value") if year is not None else None,
        })

    return matches


def game_details(bgg_id):
    root = _fetch_xml("thing", {"id": bgg_id, "stats": 1})
    item = root.find("item")

    if item is None:
        return None

    def value(path):
        node = item.find(path)
        return node.get("value") if node is not None else None

    def integer(path):
        raw = value(path)
        return int(raw) if raw and raw.isdigit() else None

    def first_text(path):
        node = item.find(path)
        return node.text if node is not None else None

    primary_name = item.find("name[@type='primary']")
    publisher = item.find("link[@type='boardgamepublisher']")
    average_weight = item.find("statistics/ratings/averageweight")

    return {
        "bgg_id": int(bgg_id),
        "title": primary_name.get("value") if primary_name is not None else "Jeu sans titre",
        "description": first_text("description"),
        "publisher": publisher.get("value") if publisher is not None else None,
        "year_published": integer("yearpublished"),
        "min_players": integer("minplayers"),
        "max_players": integer("maxplayers"),
        "min_playtime": integer("minplaytime"),
        "max_playtime": integer("maxplaytime"),
        "age_min": integer("minage"),
        "complexity": float(average_weight.get("value")) if average_weight is not None else None,
        "cover_image_url": first_text("image"),
    }
