"""Match a Kalshi event to the ESPN fixture it is about.

WHY THIS EXISTS AS ITS OWN FILE. The exact-name join in `price_at_state.py`
matched **6 of 66** Champions League qualifying events. Not because the data was
missing -- both sides had all 66 -- but because Kalshi and ESPN spell European
clubs differently, and usually only slightly:

    Kalshi "Kairat"          ESPN "Kairat Almaty"
    Kalshi "Nijmegen"        ESPN "NEC Nijmegen"
    Kalshi "Sturm Graz"      ESPN "SK Sturm Graz"
    Kalshi "Bodoe/Glimt"     ESPN "Bodo/Glimt"
    Kalshi "Union Gilloise"  ESPN "Union St.-Gilloise"

An exact-match join silently reports that as "no fixture", which is
indistinguishable in the output from Kalshi not listing the competition at all.
That is exactly how this folder nearly published "there is no European league in
the price sample".

HOW IT JOINS, AND WHY IT IS SAFE. The candidate set is only the fixtures on that
date give or take a day, in any competition -- a few dozen at most. Within that
set, both Kalshi names must match the same fixture's two teams on token overlap
at THRESHOLD or better, and **the best candidate must beat the second best**. A
tie returns nothing rather than a guess. That takes 6 to 54 of 66.

THE ALIASES ARE HAND-WRITTEN AND THAT IS DECLARED. Twelve clubs are not near-
misses but genuinely different names for the same team -- Crvena Zvezda is Red
Star Belgrade, Aarhus is AGF, Kuopion Palloseura is KuPS. There is no string
metric that gets those; they need a dictionary. Each one below was checked by
eye against the fixture on the date. **A dictionary entry is a claim and can be
wrong**, so the end-to-end check below is what actually protects the result.

THE CHECK THAT MATTERS. `verify_join()` takes joined pairs and asks whether the
side Kalshi SETTLED as the winner is the side ESPN records as winning. A wrong
join puts a real price on the wrong match, which is worse than a missing one,
and this catches it without trusting any name at all.

Read-only. No credentials.
"""
import datetime
import re
import unicodedata
from collections import defaultdict

THRESHOLD = 0.5
DAY_SLACK = 1

# Words that carry no identity. "1" is here for 1. FC Koeln and friends.
STOP = {"fc", "fk", "sk", "nk", "ac", "if", "aif", "sc", "cf", "cd", "ca",
        "club", "de", "the", "sv", "bk", "fa", "cfr", "us", "as", "ss", "ssc",
        "afc", "1", "ii", "b"}

# Genuinely different names for the same club. Hand-checked on 2026-08-09
# against the fixture on the date. Keys and values are both normalised on use,
# so case and punctuation here do not matter.
ALIASES = {
    "crvena zvezda": "red star belgrade",
    "aarhus": "agf",
    "sabah masazir": "sabah",
    "kuopion palloseura": "kups",
    "be er sheva": "hapoel be er sheva",
    "beer sheva": "hapoel be er sheva",
    "lech poznan": "lech poznan",
    "larne": "larne",
}


def norm(s):
    """Fold accents, strip punctuation, drop noise words -> list of tokens."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    # Scandinavian and German transliterations that ESPN and Kalshi disagree on.
    s = (s.replace("ø", "o").replace("æ", "a").replace("å", "a")
          .replace("oe", "o").replace("ae", "a").replace("ue", "u"))
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    toks = [t for t in s.split() if t]
    joined = " ".join(toks)
    if joined in ALIASES:
        toks = ALIASES[joined].split()
    return [t for t in toks if t not in STOP]


def score(a, b):
    """0 to 1. How much of the shorter name is contained in the longer."""
    A, B = set(norm(a)), set(norm(b))
    if not A or not B:
        return 0.0
    return len(A & B) / min(len(A), len(B))


def index(fixtures):
    """{date -> [fixture]} from an iterable of ESPN fixture rows."""
    by = defaultdict(list)
    for f in fixtures:
        by[f["date"][:10]].append(f)
    return by


def find(by_date, date, team_a, team_b):
    """The one fixture this Kalshi event is about, or None.

    `date` is a YYYY-MM-DD string. Kalshi dates an event by local kickoff and
    ESPN stamps UTC, so a late kickoff lands on the next UTC day -- hence the
    one-day slack in both directions.
    """
    try:
        d = datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return None, "unparseable date"
    cands = []
    for delta in range(-DAY_SLACK, DAY_SLACK + 1):
        ds = (d + datetime.timedelta(days=delta)).strftime("%Y-%m-%d")
        cands.extend(by_date.get(ds, []))
    if not cands:
        return None, "no fixture on that date"

    scored = []
    for c in cands:
        straight = min(score(team_a, c["home"]), score(team_b, c["away"]))
        flipped = min(score(team_a, c["away"]), score(team_b, c["home"]))
        s = max(straight, flipped)
        if s >= THRESHOLD:
            scored.append((s, c))
    if not scored:
        return None, "no fixture matched the names"
    scored.sort(key=lambda x: -x[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        # Two fixtures fit equally well. Guessing here would put a real price on
        # the wrong match, so it returns nothing instead.
        return None, "two fixtures matched equally well"
    return scored[0][1], "ok"


def verify_join(pairs):
    """Does Kalshi's settled winner agree with ESPN's final score?

    `pairs` is [(kalshi_winner_side, espn_fixture)] where kalshi_winner_side is
    'home', 'away' or 'draw' as resolved against the ESPN roster.

    Returns (agree, disagree, unknown). **Disagreements are joins that are
    wrong**, and they are the only evidence here that does not depend on
    believing a name.
    """
    agree = disagree = unknown = 0
    for side, fx in pairs:
        hg, ag = fx.get("home_goals"), fx.get("away_goals")
        if hg is None or ag is None or side is None:
            unknown += 1
            continue
        espn = "home" if hg > ag else ("away" if ag > hg else "draw")
        if espn == side:
            agree += 1
        else:
            disagree += 1
    return agree, disagree, unknown
