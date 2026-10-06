"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Helper functions ────────────────────────────────────────────────────────────

# Words that carry no meaning for matching
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "on", "of", "to",
    "i", "im", "me", "my", "want", "looking", "look", "find", "need", "some",
    "something", "any", "anything", "please", "size", "under", "below", "max",
    "less", "than", "cheap", "that", "is", "it", "its", "like", "would",
}

# Listing sizes that fit any requested size.
_ONE_SIZE = re.compile(r"\bone\s*size\b", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    """Lowercase alphanumeric tokens. "S/M" -> ["s", "m"], "W30 L30" -> ["w30", "l30"]."""
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", (text or "").lower().replace("'", ""))


def _stem(word: str) -> str:
    """Crude plural folding so "tees" matches "tee" and "jeans" matches "jean"."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Token match, not substring match.

    Every token of the requested size has to appear as a whole token in the
    listing's size. So "M" matches "M", "S/M", "M/L" but NOT "US 9"; "L" does
    not match "XL"; "W30" matches "W30 L30"; "US 8" does not match "US 8.5".
    A "One Size" listing matches any requested size.
    """
    if _ONE_SIZE.search(listing_size or ""):
        return True
    want = set(_tokens(wanted))
    have = set(_tokens(listing_size))
    return bool(want) and want <= have


def _describe_item(item: dict) -> str:
    """A plain-text summary of a listing for prompts. Never prints a missing brand."""
    parts = [
        f"Title: {item.get('title', 'unknown item')}",
        f"Category: {item.get('category', 'unknown')}",
        f"Colors: {', '.join(item.get('colors') or []) or 'not listed'}",
        f"Style tags: {', '.join(item.get('style_tags') or []) or 'none'}",
        f"Size: {item.get('size', 'not listed')}",
        f"Condition: {item.get('condition', 'not listed')}",
        f"Price: ${float(item.get('price', 0)):.2f}",
        f"Platform: {item.get('platform', 'unknown')}",
    ]
    if item.get("brand"):
        parts.insert(1, f"Brand: {item['brand']}")
    if item.get("description"):
        parts.append(f"Seller description: {item['description']}")
    return "\n".join(parts)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    query_words = {_stem(w) for w in _tokens(description) if w not in _STOPWORDS}
    if not query_words:
        return []

    scored = []
    for listing in load_listings():
        price = float(listing.get("price", 0))
        if max_price is not None and price > float(max_price):
            continue
        if size and not _size_matches(size, listing.get("size", "")):
            continue

        # Where a word matches says how much it counts. A word in the title or
        # the tags is what the item IS; a word in the seller's blurb is weaker.
        fields = {
            3: listing.get("title", ""),
            2: " ".join(
                (listing.get("style_tags") or [])
                + (listing.get("colors") or [])
                + [listing.get("category", ""), listing.get("brand") or ""]
            ),
            1: listing.get("description", ""),
        }
        score = 0
        for weight, text in fields.items():
            field_words = {_stem(w) for w in _tokens(text)}
            score += weight * len(query_words & field_words)

        if score > 0:
            scored.append((score, -price, listing))

    # Highest score first; ties go to the cheaper item.
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [listing for _, _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    items = (wardrobe or {}).get("items") or []
    system = (
        "You are a friendly personal stylist for someone who shops secondhand. "
        "Be concrete and brief. Plain text, no markdown headers."
    )

    if not items:
        prompt = (
            "The user is considering this thrifted item but hasn't saved any "
            "wardrobe pieces yet.\n\n"
            f"{_describe_item(new_item)}\n\n"
            "Suggest 2 outfits built around it using common staple pieces most "
            "people own or could easily get (say what kind of piece, colour and "
            "fit). One line per outfit, starting with 'Outfit 1:' and 'Outfit 2:'. "
            "Then one short tip on what to look for next time they thrift."
        )
        fallback = (
            f"Outfit 1: {new_item.get('title', 'This piece')} with straight-leg "
            "jeans and clean white sneakers.\nOutfit 2: Dress it up with tailored "
            "trousers and a simple neutral layer."
        )
    else:
        closet = "\n".join(
            f"- {w.get('name', 'unnamed')} ({w.get('category', '?')}; "
            f"colors: {', '.join(w.get('colors') or []) or 'n/a'}; "
            f"tags: {', '.join(w.get('style_tags') or []) or 'n/a'})"
            + (f" — note: {w['notes']}" if w.get("notes") else "")
            for w in items
        )
        prompt = (
            "The user is considering this thrifted item:\n\n"
            f"{_describe_item(new_item)}\n\n"
            f"Their wardrobe:\n{closet}\n\n"
            "Suggest 2 outfits that pair the new item with pieces they ALREADY "
            "OWN. Name each wardrobe piece exactly as written above. One or two "
            "lines per outfit, starting with 'Outfit 1:' and 'Outfit 2:'."
        )
        fallback = (
            f"Outfit 1: {new_item.get('title', 'This piece')} with your "
            f"{items[0].get('name', 'favourite basics')}."
        )

    response = (generate(prompt, system=system) or "").strip()
    # The loop needs a non-empty string to pass on; never hand back "".
    return response or fallback


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            "Couldn't write a fit card: no outfit suggestion was provided for "
            f"{new_item.get('title', 'this item')}."
        )

    price = f"${float(new_item.get('price', 0)):.0f}"
    platform = new_item.get("platform", "a thrift app")
    system = (
        "You write short, casual social media captions for thrift finds. "
        "Sound like a real person posting an outfit, not a product listing."
    )
    prompt = (
        f"The find:\n{_describe_item(new_item)}\n\n"
        f"How they're styling it:\n{outfit.strip()}\n\n"
        "Write ONE caption, 2 to 4 sentences, under 60 words. Rules:\n"
        f"- mention the item, the price ({price}) and the platform ({platform}) "
        "once each\n"
        "- describe the vibe of ONE of the outfits specifically\n"
        "- at most 2 emoji and at most 3 hashtags, at the end\n"
        "- if no brand is given above, do not invent one\n"
        "Return only the caption text, no quotes, no preamble."
    )
    caption = (generate(prompt, system=system) or "").strip().strip('"')
    return caption or (
        f"Thrifted this {new_item.get('title', 'piece')} for {price} on "
        f"{platform} and I'm obsessed. Styled it exactly how I wanted."
    )


# ── Tool 4: compare_prices ──────────────────────────────────────────

def compare_prices(item: dict) -> dict:
    """
    Compare an item's price against other listings in the same category.

    Computes category statistics (average, minimum, and maximum prices) and assesses
    whether the item is a 'great_deal' (<= 85% of average), 'fair' (85% to 115%),
    or 'above_average' (> 115% of average).

    Args:
        item: a listing dict (e.g. from search_listings or session['selected_item']).

    Returns:
        A dict with category price stats and deal assessment:
        {
            "category": str,
            "item_price": float,
            "category_count": int,
            "category_avg": float,
            "category_min": float,
            "category_max": float,
            "deal_rating": str,       # 'great_deal', 'fair', 'above_average', or 'unknown'
            "difference": float,      # item_price - category_avg (negative = cheaper than avg)
            "summary": str,           # human-readable summary
        }
    """
    if not item or not isinstance(item, dict):
        return {
            "category": "unknown",
            "item_price": 0.0,
            "category_count": 0,
            "category_avg": 0.0,
            "category_min": 0.0,
            "category_max": 0.0,
            "deal_rating": "unknown",
            "difference": 0.0,
            "summary": "No item provided for price comparison.",
        }

    category = item.get("category", "")
    item_price = float(item.get("price", 0.0))

    all_listings = load_listings()
    same_category = [
        float(x.get("price", 0.0))
        for x in all_listings
        if x.get("category") == category
    ]

    if not same_category:
        return {
            "category": category,
            "item_price": item_price,
            "category_count": 0,
            "category_avg": item_price,
            "category_min": item_price,
            "category_max": item_price,
            "deal_rating": "unknown",
            "difference": 0.0,
            "summary": f"No other listings found in category '{category}' to compare.",
        }

    category_avg = round(sum(same_category) / len(same_category), 2)
    category_min = round(min(same_category), 2)
    category_max = round(max(same_category), 2)
    diff = round(item_price - category_avg, 2)

    if item_price <= category_avg * 0.85:
        deal_rating = "great_deal"
        verdict = f"great deal (${abs(diff):.2f} below average)"
    elif item_price <= category_avg * 1.15:
        deal_rating = "fair"
        verdict = f"fair price (within typical range, avg is ${category_avg:.2f})"
    else:
        deal_rating = "above_average"
        verdict = f"above average price (${diff:.2f} above average of ${category_avg:.2f})"

    summary = (
        f"${item_price:.2f} is a {verdict} for {category} "
        f"(category range: ${category_min:.2f} – ${category_max:.2f}, avg: ${category_avg:.2f})."
    )
    if deal_rating == "above_average":
        summary = (
            f"${item_price:.2f} is an {verdict} for {category} "
            f"(category range: ${category_min:.2f} – ${category_max:.2f}, avg: ${category_avg:.2f})."
        )

    return {
        "category": category,
        "item_price": item_price,
        "category_count": len(same_category),
        "category_avg": category_avg,
        "category_min": category_min,
        "category_max": category_max,
        "deal_rating": deal_rating,
        "difference": diff,
        "summary": summary,
    }

