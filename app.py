#!/usr/bin/env python3
"""
FitFindr — command line.

    python app.py ask 'vintage graphic tee under $30, size M'
    python app.py ask                     keep asking until you quit
    python app.py ask --empty-wardrobe    run as a user with nothing saved
    python app.py listings                browse the data  (Milestone 1)
    python app.py fields                  what fields a listing has
    python app.py examples                queries worth trying, including a dud

Add --trace to any `ask` to print the loop step by step.

⚠️ Quote your query with SINGLE quotes. In PowerShell, "under $30" in double
quotes silently becomes "under " — PowerShell reads $30 as a variable and
substitutes nothing, so you search with no price ceiling and get no error
telling you why. Single quotes are literal in PowerShell, bash and zsh alike.
"""

import argparse
import sys

import config

# Every query here except the last one has something real to find in
# data/listings.json. If you add your own, check it against the data first — a
# query that finds nothing because the item doesn't exist looks exactly like a
# search tool that's broken.
EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "silk slip dress in midi length under $40",
    "platform sneakers size 8",
    "denim jacket under $50",
    "designer ballgown size XXS under $5",   # matches nothing, on purpose
]


def cmd_fields(args):
    """Milestone 1 — you can't filter on a field that isn't there."""
    from utils.data_loader import load_listings, get_example_wardrobe

    listing = load_listings()[0]
    print("A listing has these fields:\n")
    for key, value in listing.items():
        shown = str(value)
        if len(shown) > 58:
            shown = shown[:58] + "…"
        print(f"  {key:<14} {type(value).__name__:<6} {shown}")

    item = get_example_wardrobe()["items"][0]
    print("\nA wardrobe item has these fields:\n")
    for key, value in item.items():
        shown = str(value)
        if len(shown) > 58:
            shown = shown[:58] + "…"
        print(f"  {key:<14} {type(value).__name__:<6} {shown}")

    print(
        "\nThese are what search_listings can filter on. Read a few whole "
        "listings\nwith `python app.py listings` before you write it."
    )


def cmd_listings(args):
    """Milestone 1 — read the data before you write tools against it."""
    from utils.data_loader import load_listings

    listings = load_listings()

    if args.full:
        import json
        for listing in listings[: args.n]:
            print(json.dumps(listing, indent=2))
            print()
        return

    print(f"{len(listings)} listings.\n")
    print(f"{'id':<6}{'price':>8}  {'size':<22}{'platform':<11}title")
    print("-" * 92)
    for listing in listings[: args.n]:
        print(
            f"{str(listing['id']):<6}"
            f"{listing['price']:>8.2f}  "
            f"{str(listing['size']):<22}"
            f"{listing['platform']:<11}"
            f"{listing['title'][:38]}"
        )
    if len(listings) > args.n:
        print(f"\n… {len(listings) - args.n} more. Use -n {len(listings)} to see them all.")
    print("\nRead five or six all the way through: python app.py listings --full -n 6")


def cmd_examples(args):
    print("Queries worth trying:\n")
    for query in EXAMPLE_QUERIES[:-1]:
        print(f"  python app.py ask '{query}'")
    print(f"\nAnd one the data cannot match — this is the empty-search branch:\n")
    print(f"  python app.py ask '{EXAMPLE_QUERIES[-1]}'")
    print(
        "\nSingle quotes on purpose. In PowerShell a query in \"double quotes\"\n"
        "loses the $30 — it gets read as a variable — and you search with no\n"
        "price ceiling, with nothing to tell you it happened."
    )


def _ask_one(query, wardrobe, use_trace):
    from agent import run_agent
    import trace as trace_module

    if use_trace:
        trace_module.start_trace()

    session = run_agent(query, wardrobe)

    print()
    if session["error"]:
        print(f"  {session['error']}")
    else:
        item = session["selected_item"] or {}
        print(f"  Found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
        if session.get("price_comparison"):
            print(f"  Deal:     {session['price_comparison']['summary']}")
        if session.get("styling_note"):
            print(f"  Styling:  [{session.get('styling_mode')}] {session['styling_note']}")
        print()
        print(f"  Outfit:   {session['outfit_suggestion']}")
        print()
        print(f"  Fit card: {session['fit_card']}")
    print()

    if use_trace:
        text = trace_module.get_trace()
        if not text:
            print(
                "  (--trace printed nothing. You haven't added trace.step() calls to\n"
                "   run_agent() yet — that's unit 4, Milestone 2.)\n"
            )
    return session


def cmd_wardrobe(args):
    """View and manage persistent style memory wardrobe."""
    from utils.data_loader import (
        load_saved_wardrobe,
        add_wardrobe_item,
        reset_saved_wardrobe,
    )

    if args.reset:
        w = reset_saved_wardrobe(to_empty=False)
        print(f"Reset persistent wardrobe to example items ({len(w['items'])} items).")
        return
    if args.clear:
        w = reset_saved_wardrobe(to_empty=True)
        print("Cleared persistent wardrobe (0 items).")
        return
    if args.add:
        tags = [t.strip() for t in (args.style or "").split(",") if t.strip()]
        colors = [c.strip() for c in (args.colors or "").split(",") if c.strip()]
        w = add_wardrobe_item(
            name=args.add,
            category=args.category or "tops",
            colors=colors,
            style_tags=tags,
            notes=args.notes,
        )
        print(f"Added '{args.add}' to persistent wardrobe! Total items: {len(w['items'])}.")
        return

    w = load_saved_wardrobe()
    items = w.get("items", [])
    print(f"Persistent Wardrobe ({len(items)} items):\n")
    for i, it in enumerate(items, 1):
        cols = ", ".join(it.get("colors") or []) or "n/a"
        tags = ", ".join(it.get("style_tags") or []) or "n/a"
        print(f"  [{i:02d}] {it.get('name')} ({it.get('category')})")
        print(f"       colors: {cols} | style: {tags}")
        if it.get("notes"):
            print(f"       note: {it['notes']}")


def cmd_ask(args):
    from utils.data_loader import (
        get_example_wardrobe,
        get_empty_wardrobe,
        load_saved_wardrobe,
        add_wardrobe_item,
    )
    import generate

    if args.empty_wardrobe:
        wardrobe = get_empty_wardrobe()
        print("(running with an empty wardrobe)")
    elif args.example_wardrobe:
        wardrobe = get_example_wardrobe()
    else:
        wardrobe = load_saved_wardrobe()

    try:
        if args.query:
            session = _ask_one(args.query, wardrobe, args.trace)
            if args.save and session.get("selected_item"):
                sel = session["selected_item"]
                add_wardrobe_item(
                    name=sel.get("title", "Thrift piece"),
                    category=sel.get("category", "tops"),
                    colors=sel.get("colors") or [],
                    style_tags=sel.get("style_tags") or [],
                    notes=f"Thrifted for ${sel.get('price', 0)} on {sel.get('platform')}",
                )
                print(f"  [style memory] Saved '{sel.get('title')}' to persistent wardrobe!\n")
        else:
            print("Ask for something, or press Enter on an empty line to quit.\n")
            while True:
                try:
                    query = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if not query:
                    break
                session = _ask_one(query, wardrobe, args.trace)
                if args.save and session.get("selected_item"):
                    sel = session["selected_item"]
                    add_wardrobe_item(
                        name=sel.get("title", "Thrift piece"),
                        category=sel.get("category", "tops"),
                        colors=sel.get("colors") or [],
                        style_tags=sel.get("style_tags") or [],
                        notes=f"Thrifted for ${sel.get('price', 0)} on {sel.get('platform')}",
                    )
                    print(f"  [style memory] Saved '{sel.get('title')}' to persistent wardrobe!\n")
    finally:
        print(generate.usage())


def build_parser():
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="FitFindr",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_fields = sub.add_parser("fields", help="what fields the data has")
    p_fields.set_defaults(func=cmd_fields)

    p_list = sub.add_parser("listings", help="browse the listings data")
    p_list.add_argument("-n", type=int, default=15, help="how many to show")
    p_list.add_argument("--full", action="store_true", help="print whole records")
    p_list.set_defaults(func=cmd_listings)

    p_ex = sub.add_parser("examples", help="queries worth trying")
    p_ex.set_defaults(func=cmd_examples)

    p_ask = sub.add_parser("ask", help="run the agent")
    p_ask.add_argument("query", nargs="?")
    p_ask.add_argument("--trace", action="store_true", help="print the loop step by step")
    p_ask.add_argument(
        "--empty-wardrobe",
        action="store_true",
        help="run as a user with nothing saved — one of unit 4's failure modes",
    )
    p_ask.add_argument(
        "--example-wardrobe",
        action="store_true",
        help="use the starter example wardrobe instead of your saved persistent wardrobe",
    )
    p_ask.add_argument(
        "--save",
        action="store_true",
        help="save the matched thrift find into your persistent style memory wardrobe",
    )
    p_ask.set_defaults(func=cmd_ask)

    # ── Style Memory: wardrobe manager command ──
    p_w = sub.add_parser("wardrobe", help="view and manage persistent style memory wardrobe")
    p_w.add_argument("--add", metavar="NAME", help="add an item to your wardrobe by name")
    p_w.add_argument(
        "--category",
        choices=["tops", "bottoms", "outerwear", "shoes", "accessories"],
        default="tops",
        help="category for added item (default: tops)",
    )
    p_w.add_argument("--colors", help="comma-separated colors (e.g. 'black,white')")
    p_w.add_argument("--style", help="comma-separated style tags (e.g. 'vintage,grunge')")
    p_w.add_argument("--notes", help="notes on fit or styling")
    p_w.add_argument("--reset", action="store_true", help="reset persistent wardrobe to example items")
    p_w.add_argument("--clear", action="store_true", help="clear persistent wardrobe to an empty closet")
    p_w.set_defaults(func=cmd_wardrobe)

    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001 — students read this, not a traceback
        print(f"\n{type(exc).__name__}: {exc}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
