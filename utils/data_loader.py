"""
Utility functions for loading the mock listings dataset and wardrobe schema.
Use these in your tool implementations to access the data without re-reading
the files each time.
"""

import json
import os
from typing import Optional

# Resolve the path to the data directory relative to this file
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_listings() -> list[dict]:
    """
    Load all mock listings from the dataset.

    Returns:
        A list of listing dictionaries. Each listing has the following fields:
        - id (str)
        - title (str)
        - description (str)
        - category (str): one of tops, bottoms, outerwear, shoes, accessories
        - style_tags (list[str])
        - size (str)
        - condition (str): excellent, good, or fair
        - price (float)
        - colors (list[str])
        - brand (str or None)
        - platform (str): depop, thredUp, or poshmark
    """
    path = os.path.join(_DATA_DIR, "listings.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_wardrobe_schema() -> dict:
    """
    Load the wardrobe schema, including the example wardrobe and empty template.

    Returns:
        A dictionary containing:
        - schema: the field definitions for a wardrobe item
        - example_wardrobe: a sample wardrobe with 10 items
        - empty_wardrobe: a starting template for a new user
    """
    path = os.path.join(_DATA_DIR, "wardrobe_schema.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _wardrobe(name: str) -> dict:
    """
    Pull one wardrobe out of the schema file, without the documentation keys.

    The JSON uses underscore-prefixed keys (_description, _note) to explain
    itself to a human reader. Those are notes about the file, not part of a
    wardrobe, and stripping them here means both wardrobes below come back
    the same shape. Otherwise the empty one carries an extra _note key, and a
    tool that formats the whole dict into a prompt would send the model a
    sentence about templates.
    """
    wardrobe = load_wardrobe_schema()[name]
    return {k: v for k, v in wardrobe.items() if not k.startswith("_")}


def get_example_wardrobe() -> dict:
    """
    Convenience function — returns just the example wardrobe items list.

    Returns:
        A wardrobe dict with an 'items' key containing a list of wardrobe items.
    """
    return _wardrobe("example_wardrobe")


def get_empty_wardrobe() -> dict:
    """
    Convenience function — returns an empty wardrobe template.

    Returns:
        A wardrobe dict with an empty 'items' list. Same shape as the example
        wardrobe — the only difference is that 'items' is empty.
    """
    return _wardrobe("empty_wardrobe")


# ── Style Memory: persistent wardrobe between runs ──────────────────

_USER_WARDROBE_PATH = os.path.join(_DATA_DIR, "user_wardrobe.json")


def load_saved_wardrobe() -> dict:
    """
    Load the persistent user wardrobe from disk (data/user_wardrobe.json).
    If no saved wardrobe exists yet, initializes it from the example wardrobe.

    Returns:
        A wardrobe dict with an 'items' list.
    """
    if os.path.exists(_USER_WARDROBE_PATH):
        try:
            with open(_USER_WARDROBE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "items" in data:
                    return data
        except Exception:
            pass

    # Initialize with example wardrobe
    wardrobe = get_example_wardrobe()
    save_wardrobe(wardrobe)
    return wardrobe


def save_wardrobe(wardrobe: dict) -> None:
    """
    Persist the wardrobe to disk (data/user_wardrobe.json).
    """
    with open(_USER_WARDROBE_PATH, "w", encoding="utf-8") as f:
        json.dump(wardrobe, f, indent=2)


def add_wardrobe_item(
    name: str,
    category: str,
    colors: list[str] | None = None,
    style_tags: list[str] | None = None,
    notes: str | None = None,
) -> dict:
    """
    Add a new item to the user's persistent wardrobe and save it.

    Returns:
        The updated wardrobe dict.
    """
    wardrobe = load_saved_wardrobe()
    items = wardrobe.setdefault("items", [])
    new_id = f"w_user_{len(items) + 1:03d}"
    item = {
        "id": new_id,
        "name": name,
        "category": category,
        "colors": colors or [],
        "style_tags": style_tags or [],
        "notes": notes,
    }
    items.append(item)
    save_wardrobe(wardrobe)
    return wardrobe


def reset_saved_wardrobe(to_empty: bool = False) -> dict:
    """
    Reset the persistent wardrobe to either the example wardrobe or an empty wardrobe.
    """
    wardrobe = get_empty_wardrobe() if to_empty else get_example_wardrobe()
    save_wardrobe(wardrobe)
    return wardrobe



# --- Quick sanity check ---
if __name__ == "__main__":
    listings = load_listings()
    print(f"Loaded {len(listings)} listings.")
    print(f"First listing: {listings[0]['title']} — ${listings[0]['price']}")

    wardrobe = get_example_wardrobe()
    print(f"\nExample wardrobe has {len(wardrobe['items'])} items.")
    print(f"First item: {wardrobe['items'][0]['name']}")
