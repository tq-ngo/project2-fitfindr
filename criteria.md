# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
<!-- Why 4 of 5 and not 5 of 5? Something about your search, probably —
     "my search is a plain keyword match and some phrasings will miss" is a
     real answer. -->
The loop is deterministic once search returns something. The risk is  search: it's a plain keyword match after a regex parse, so a phrasing the regex misreads or a word in no listing can empty the results for a query a person would call matchable. A model call can also fail on the rate limiter. 1 miss in 5 allows for that, 2 would mean the parser is broken, not unlucky.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
<!-- Why is 5 of 5 reasonable here when criterion 1 isn't? What's different
     about this path? -->
This path never touches the model. Parsing, search and the branch are plain Python over a fixed file, and the "what to change" message is built by re-running the local search with one filter relaxed at a time. Same input, same output, every time, so anything below 5 of 5 is a bug in the branch, not randomness. "Names what to change" means the message contains a concrete suggestion (raise budget to $X, a different size, or different keywords), not just "No results".

---

## 3. Something about state

**The item search found is the item the later tools received.**

<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->

For a matching query, `session["selected_item"]["id"]` equals
`session["search_results"][0]["id"]`, and `session["fit_card"]` mentions that same item's `price` and `platform`, in 5 of 5 tries.

Checked by printing the session at the end of `run_agent()`: the id
comparison is a direct equality check, and price/platform are a substring search of `session["fit_card"]` for e.g. `$24` and `depop`.

**Why this target:**
`run_agent` writes the first result into `session["selected_item"]` and both later tools read it back from there, so the id check should never fail, 5 of 5. I added the price/platform check because a state bug wouldn't look like a state bug: if the wrong item leaked through, the caption would quote the wrong price or platform, and that is the only place a user would ever see it. That half depends on the model obeying the prompt, which is why it's the half I expect to be tested hardest.

---

## 4. Something about the fit card

**The fit card reads like a post, and isn't a template.**

<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->

Run the same matching query 5 times with the cache off. Each fit card is
at most 60 words, contains no brand name unless the listing has one,
and no two of the five share the same first sentence, in at least 4 of
5 cards (the "same first sentence" check counts a card as failing if its
opening sentence is word-for-word identical to any other card's).

**Why this target:**
The prompt asks for under 60 words and forbids inventing a brand, but the
model runs at temperature 0.9 and doesn't always count words, so 1 overrun
in 5 is plausible. Don't demand 5 of 5 because can't control the model's wording — only constrain it. I don't go lower because 60 words is
already generous for a caption; two overruns would mean the prompt isn't
working. The identical-opening check catches the cache or temperature being
wrong (both are set in config.py), and the brand check matters because 32 of
the 40 listings have `brand: null` and a model likes to fill gaps.

---

## 5. Your choice

**Search respects the price ceiling and the size.**

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->

For 5 different queries that include a price and/or a size (e.g. "graphic
tee size M under $30", "jeans size W30 under $40", "sneakers size US 8",
"jacket in a medium under $50", "tee size L under $20"), every listing in
`session["search_results"]` has `price <= max_price` and a size that matches
as whole tokens (an "M" query never returns "US 9" shoes, and "L" never
returns "XL"; "One Size" items are allowed) — 5 of 5 queries, 0 violating
listings.

**Why this target:**
This is the filter people notice first when it's wrong — a $45 jacket in a
"under $30" search, or shoes in a "small top" search, makes the whole agent
look broken. It's pure Python with no model in it, and sizes are compared as
tokens instead of substrings precisely to avoid `"s" in "us 9"`. So the only
acceptable count is zero violations. The part that can still miss is the
regex parser not recognising a size phrase, which would show up as a query
that ignored its size — and that counts as a fail here.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
