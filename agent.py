"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable  # noqa: F401 — handler comes in unit 4


# ── query parsing (regex) ─────────────────────────────────────────────────────

# "under $30", "below 30", "less than $30", "max $30", "up to 30", "<= $30",
# or a bare "$30".
_PRICE_PATTERNS = [
    re.compile(
        r"\b(?:under|below|less\s+than|max(?:imum)?|up\s+to|no\s+more\s+than|at\s+most)"
        r"\s*\$?\s*(\d+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    re.compile(r"<=?\s*\$?\s*(\d+(?:\.\d+)?)"),
    re.compile(r"\$\s*(\d+(?:\.\d+)?)(?:\s*(?:or\s+less|max|and\s+under))?", re.IGNORECASE),
]

_SIZE_VALUE = (
    r"us\s*\d+(?:\.\d+)?|w\d+(?:\s*l\d+)?|xxs|xs|xxl|xl|s|m|l|"
    r"small|medium|large|one\s+size"
)
# "size M", "size: US 8", "in a medium", "in size small"
_SIZE_PATTERNS = [
    re.compile(rf"\bsize\s*:?\s*({_SIZE_VALUE})\b", re.IGNORECASE),
    re.compile(rf"\bin\s+(?:a\s+)?({_SIZE_VALUE})\b(?!\s*(?:wash|color|colour))", re.IGNORECASE),
]
_SIZE_WORDS = {"small": "S", "medium": "M", "large": "L"}


def parse_query(query: str) -> dict:
    """
    Split a plain-language query into description / size / max_price, by regex.

    The price and size phrases are cut out of the text; whatever is left is the
    description. Nothing found means None for that field (no filter).
    """
    text = query or ""
    max_price = None
    for pattern in _PRICE_PATTERNS:
        match = pattern.search(text)
        if match:
            max_price = float(match.group(1))
            text = text[: match.start()] + " " + text[match.end():]
            break

    size = None
    for pattern in _SIZE_PATTERNS:
        match = pattern.search(text)
        if match:
            raw = re.sub(r"\s+", " ", match.group(1).strip())
            size = _SIZE_WORDS.get(raw.lower(), raw.upper())
            text = text[: match.start()] + " " + text[match.end():]
            break

    description = re.sub(r"[,;]+", " ", text)
    description = re.sub(r"\s+", " ", description).strip()
    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """
    Say WHAT to change, not just that nothing came back.

    Re-runs the (local, free) search with one filter relaxed at a time to find
    out which constraint emptied the results. No model calls happen here.
    """
    desc, size, price = parsed["description"], parsed["size"], parsed["max_price"]
    looked_for = f"'{desc}'" if desc else "your search"
    filters = []
    if size:
        filters.append(f"size {size}")
    if price is not None:
        filters.append(f"under ${price:.0f}")
    head = f"No listings matched {looked_for}" + (f" ({', '.join(filters)})" if filters else "") + "."

    if not desc:
        return head + " Tell me what kind of item you want, e.g. 'graphic tee', 'denim jacket', 'boots'."

    if price is not None:
        no_price = search_listings(desc, size, None)
        if no_price:
            cheapest = min(float(x["price"]) for x in no_price)
            return head + f" Try raising your budget — the cheapest match is ${cheapest:.0f}."
    if size:
        no_size = search_listings(desc, None, price)
        if no_size:
            sizes = sorted({x["size"] for x in no_size})[:4]
            return head + f" Try a different size or drop it — matches come in {', '.join(sizes)}."
    if search_listings(desc, None, None):
        return head + " Try removing both the size and the price limit."
    return head + (
        " Try different keywords — a category (tops, bottoms, outerwear, shoes, "
        "accessories) or a style like 'vintage', 'y2k', 'grunge'."
    )


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "styling_mode": None,        # stretch branch: closet / no_style_match / empty_wardrobe
        "styling_note": None,        # why that mode was chosen
        "wardrobe_used": None,       # the wardrobe that actually went into suggest_outfit
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


def _shared_style_tags(item: dict, wardrobe: dict) -> set[str]:
    """Style tags the item has in common with anything in the wardrobe."""
    item_tags = {t.lower() for t in item.get("style_tags") or []}
    owned = {
        t.lower()
        for piece in (wardrobe or {}).get("items") or []
        for t in piece.get("style_tags") or []
    }
    return item_tags & owned


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # Each pass round the loop reads the session, decides the next step, runs
    # one tool, and writes its result back. Values go through the session —
    # never straight from one call into the next.
    next_step = "parse"
    count = 0
    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        if next_step == "parse":
            session["parsed"] = parse_query(session["query"])
            next_step = "search"

        elif next_step == "search":
            p = session["parsed"]
            session["search_results"] = search_listings(
                p["description"], p["size"], p["max_price"]
            )
            if not session["search_results"]:
                session["error"] = _no_results_message(p)
                next_step = "done"
            else:
                session["selected_item"] = session["search_results"][0]
                next_step = "check_wardrobe"

        elif next_step == "check_wardrobe":
            # ── SECOND BRANCH (stretch) ── does the closet suit this item?
            items = (session["wardrobe"] or {}).get("items") or []
            shared = _shared_style_tags(session["selected_item"], session["wardrobe"])
            if not items:
                session["styling_mode"] = "empty_wardrobe"
                session["styling_note"] = "No saved wardrobe — styling with common staples."
                session["wardrobe_used"] = {"items": []}
            elif not shared:
                tags = ", ".join(session["selected_item"].get("style_tags") or [])
                session["styling_mode"] = "no_style_match"
                session["styling_note"] = (
                    f"Nothing in your wardrobe shares a style with this piece ({tags}) "
                    "— styling it with staples instead."
                )
                session["wardrobe_used"] = {"items": []}
            else:
                session["styling_mode"] = "closet"
                session["styling_note"] = f"Matched your wardrobe on: {', '.join(sorted(shared))}."
                session["wardrobe_used"] = session["wardrobe"]
            next_step = "suggest"

        elif next_step == "suggest":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe_used"]
            )
            next_step = "fit_card"

        elif next_step == "fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )
            next_step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
