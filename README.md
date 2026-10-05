# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

You type what you're thrifting for in plain language, like `vintage graphic tee
under $30` or `denim jacket in a medium, below 50`. FitFindr searches 40
secondhand listings (depop, thredUp, poshmark) for the best match within your
size and budget, suggests two outfits that pair it with pieces already in your
wardrobe, and writes a short caption you could post with the fit. If nothing
matches, it stops and tells you which filter to loosen. It won't make up an
outfit for an item that doesn't exist.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters `data/listings.json` by price ceiling and size,
  scores what's left by keyword overlap with the description (title word = 3,
  tag/color/category/brand word = 2, seller-description word = 1), and returns
  the best matches first.
- **Inputs:** <!-- name and type each: `max_price` (float), not "a price" --> `description` (str): keywords, e.g. `"vintage graphic tee"`.
  `size` (str | None): e.g. `"M"`, `"US 8"`, `"W30"`; `None` skips the size
  filter. `max_price` (float | None): inclusive ceiling; `None` skips it.
- **Returns:** `list[dict]`, at most `config.SEARCH_RESULT_LIMIT` (10) listing
  dicts sorted by score, highest first (ties go to the cheaper one). Each has
  `id`, `title`, `description`, `category`, `style_tags` (list), `size`,
  `condition`, `price` (float), `colors` (list), `brand` (str or None),
  `platform`. **Size rule:** every token of the requested size must appear as
  a whole token in the listing's size, so `M` matches `M`, `S/M`, `M/L` but
  never `US 9`. `L` never matches `XL`, and `US 8` never matches `US 8.5`.
  Listings sized "One Size" match any size.
- **When it has nothing:** an empty list `[]`. Never `None`, never an
  exception. That covers no keyword hits, everything filtered out, or a
  description with only stopwords (e.g. `""`).

### `suggest_outfit`

- **What it does:** Asks the model (via `generate()`) for two outfits built
  around the new item, naming pieces the user already owns.
- **Inputs:** `new_item` (dict): one listing dict from `search_listings`.
  `wardrobe` (dict): `{"items": [ {id, name, category, colors, style_tags,
notes}, ... ]}`, and `items` may be empty.
- **Returns:** `str`, non-empty plain text: `"Outfit 1: …"` and `"Outfit 2: …"`,
  each naming wardrobe pieces by their exact `name`.
- **When it has nothing:** an empty wardrobe (`items == []`) still returns a
  non-empty string. It gives two outfits built from common staples (white tee,
  straight-leg jeans, etc.) plus one thrifting tip. If the model returns an
  empty reply, it returns a hard-coded fallback outfit string. It never
  returns `""`.

### `create_fit_card`

- **What it does:** Asks the model for a short social-media caption about the
  find and how it's styled.
- **Inputs:** `outfit` (str): the text from `suggest_outfit`. `new_item`
  (dict): the same listing dict.
- **Returns:** `str`, one caption of 2–4 sentences (prompted for under 60
  words) that mentions the item, its price (e.g. `$24`) and its platform once
  each, with at most 2 emoji and 3 hashtags. It doesn't name a brand unless the
  listing has one.
- **When it has nothing:** if `outfit` is empty or whitespace, it makes no
  model call and returns `"Couldn't write a fit card: no outfit suggestion was
provided for <title>."`. If the model returns an empty reply, it returns a
  template caption with the title, price and platform.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` that names the filter to change, and stop. `suggest_outfit`
and `create_fit_card` are never called, so `outfit_suggestion` and `fit_card`
stay `None`. Otherwise, take the first result into `session["selected_item"]`
and go to `suggest_outfit`, then `create_fit_card`.

To find which filter to name, the message re-runs the local search with one
filter relaxed at a time (no model calls). If dropping the price finds
something, it says "raise your budget, the cheapest match is $X". If dropping
the size finds something, it lists the sizes that exist. Otherwise it suggests
different keywords or categories.

**Where it lives:** `agent.py::run_agent` (message built by
`agent.py::_no_results_message`)

**How the query is parsed:** <!-- regex, string splitting, or asking the model — say which --> Regex, in `agent.py::parse_query`. Price phrases
(`under/below/less than/max/up to $N`, `<= N`, or a bare `$N`) become
`max_price`. Size phrases (`size M`, `size: US 8.5`, `size W30`, `in a medium`)
become `size`, with small/medium/large mapped to S/M/L. Both are cut out of the
text, and what's left is the `description`.

**What moves through the session:** <!-- which fields, in what order --> `query` → `parsed` {description, size,
max_price} → `search_results` → `selected_item` (= `search_results[0]`) →
`outfit_suggestion` → `fit_card`. `error` is set only on the early stop. The
loop is a `while next_step != "done"` state machine that calls
`trace.check_iterations()` on every pass. Each step reads its inputs from the
session and writes its result back. No value is passed directly from one tool
call to the next.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   Outfit 1: Pair the Graphic Tee — 2003 Tour Bootleg Style with your baggy straight-leg jeans, black combat boots, and black crossbody bag for an effortless grunge streetwear look.

Outfit 2: Layer the Vintage black denim jacket over the Graphic Tee — 2003 Tour Bootleg Style, paired with your wide-leg khaki trousers and chunky white sneakers for a cool contrast of earth tones and edgy graphics.

  Fit card: Nothing beats a perfectly worn-in tee. Throwing this graphic tee on with baggy jeans and chunky boots gives major effortless grunge vibes. Grab it on depop for just $24 before I change my mind. 🖤⛓️

#depop #grungetyle #y2k
```

**And the branch: a query that matches nothing**

```
$ python agent.py
...
=== A query it can't ===
  stopped: No listings matched 'designer ballgown' (size XXS, under $5). Try different keywords — a category (tops, bottoms, outerwear, shoes, accessories) or a style like 'vintage', 'y2k', 'grunge'.
  fit_card is None — it should still be None here
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', ... (7 listings total, all <= $30)
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit 1: Pair the Vintage Levi's 501 Jeans — Medium Wash with the White ribbed tank top, Black cropped zip hoodie, and Chunky white sneakers for an easy, casual streetwear look.

Outfit 2: Style the Vintage Levi's 501 Jeans — Medium Wash with the Oversized grey crewneck sweatshirt, Brown leather belt, and Black combat boots for a cozy, vintage-inspired outfit.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Nothing beats the knee-fading on these vintage Levi's. Paired with crisp white sneakers, it's the ultimate casual weekend fit. Grab them on depop for $38 before I change my mind. 👖✨

#vintagelevis #denim #streetwear
```

Run three times with `AI201_CACHE=0`: three different captions, same facts
($38, depop, Levi's). The temperature (0.9) is doing its job.

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- _What I asked for:_ I gave Claude my `search_listings` spec (description, size, max_price; empty list on no match) and the starter's warning that `"s" in "us 9"` is True, and asked for the tool built on `load_listings()`.
- _What came back:_ A filter that matches sizes as whole tokens (so `M` matches `S/M` but not `US 9`, and `L` doesn't match `XL`) and ranks by weighted keyword overlap, returning `[]` when nothing matches. Its first tokenizer used `[a-z0-9.]+`, which would have glued a sentence-ending period onto a word ("tee." would not match "tee"). Running it also showed a limit: `leather bomber under $20` returns a $12 leather belt, because "leather" matches and the $75 bomber is over budget.
- _What I changed:_ I changed the tokenizer to `[a-z0-9]+(?:\.[0-9]+)?` so "8.5" stays one token but trailing periods don't stick. I tested `search_listings` on its own with a size/price query, an impossible query and an empty string before wiring it in. I left the belt result alone because it's a keyword-match limit, not a bug, and it is the kind of miss criterion 1's "4 of 5" allows for. I also simplified the stopword comment in `tools.py` to my own wording.

**Moment 2**

- _What I asked for:_ Help drafting the state criterion (criterion 3) and the "why this target" lines for all five criteria.
- _What came back:_ A state criterion that said the selected item's title "appears in the fit card's prompt input". Nothing in the session records that, so nobody could check it without reading my code.
- _What I changed:_ I cut that clause so criterion 3 only checks things you can print from the session: `selected_item["id"]` equals `search_results[0]["id"]`, and `fit_card` mentions that item's price and platform. When Claude first filled in the README and `criteria.md`, it also deleted the template's instruction comments. I caught that and had them restored, so the grader's instructions are still in the file and my answers sit under them.

---

## Stretch Features

**A second branch: the wardrobe check.** This lives in `agent.py::run_agent`, in
the `check_wardrobe` step that runs after an item is selected and before
`suggest_outfit`.

The loop now looks at the selected item against the wardrobe and takes one of
three paths:

| Condition                                                                       | `session["styling_mode"]` | What `suggest_outfit` receives                                                                            |
| ------------------------------------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------------- |
| Wardrobe has no items                                                           | `"empty_wardrobe"`        | an empty wardrobe, so it returns staple-based general advice                                              |
| Wardrobe has items, but none shares a single `style_tag` with the selected item | `"no_style_match"`        | an empty wardrobe, so it returns staple-based advice instead of forcing a y2k piece into a minimal closet |
| At least one wardrobe item shares a style tag                                   | `"closet"`                | the full wardrobe                                                                                         |

The wardrobe that actually went into the tool is stored in
`session["wardrobe_used"]`, and the reason is in `session["styling_note"]`, so
the path taken can be read straight from the session. The selected item never
changes. This branch only decides what the second tool is given, so criterion
3 still holds.

Why this condition: with the example wardrobe, 2 of the 40 listings share no
style tag with anything the user owns (`lst_009` Platform Mary Janes, with
y2k/goth/platform/90s, and `lst_023` Crochet Halter Top, with
cottagecore/boho/crochet/summer). Before this branch, the model was asked to
build outfits from a closet that didn't fit the piece.

**All three paths, from the CLI:**

```
$ python app.py ask 'vintage graphic tee under $30'
  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop
  Styling:  [closet] Matched your wardrobe on: grunge, streetwear, vintage.

$ python app.py ask 'mary janes'
  Found:    Platform Mary Janes — Black Patent — $55.0 on depop
  Styling:  [no_style_match] Nothing in your wardrobe shares a style with this piece (y2k, goth, platform, 90s) — styling it with staples instead.
  Outfit:   Outfit 1: Pair them with a black pleated mini skirt, a snug white baby tee, and sheer black tights.
  ...

$ python app.py ask 'denim jacket under $50' --empty-wardrobe
  Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark
  Styling:  [empty_wardrobe] No saved wardrobe — styling with common staples.
```

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1.        |        |       |       |       |       |       |         |
| 2.        |        |       |       |       |       |       |         |
| 3.        |        |       |       |       |       |       |         |
| 4.        |        |       |       |       |       |       |         |
| 5.        |        |       |       |       |       |       |         |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| #   | Criterion | Target | Verdict | How I decided |
| --- | --------- | ------ | ------- | ------------- |
| 1   |           |        |         |               |
| 2   |           |        |         |               |
| 3   |           |        |         |               |
| 4   |           |        |         |               |
| 5   |           |        |         |               |

**Diagnoses**

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1.        |        |       |       |       |       |       |         |
| 2.        |        |       |       |       |       |       |         |
| 3.        |        |       |       |       |       |       |         |
| 4.        |        |       |       |       |       |       |         |
| 5.        |        |       |       |       |       |       |         |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
