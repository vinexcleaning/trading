"""The single authority on which Kalshi field names are live, and which are gone.

Three sessions have now shipped a bug from reading a Kalshi field name that no
longer exists. Every time the symptom was the same: **the key is absent, `.get()`
returns `None`, and `None` flows into arithmetic that produces a clean-looking
zero.** Nothing raises. The run completes. The numbers are wrong in the
flattering direction.

    C024 / set1_overshoot   `volume` -> `volume_fp`. A dedupe summed to zero
                            and the first run reported a clean fake result.
    mlb-paper 2026-08-07    `/orderbook` returns `orderbook_fp.yes_dollars`,
                            not `orderbook.yes`. Read the documented-looking
                            path and every depth reads 0.
    crypto 2026-08-07       `yes_price` / `no_price` / `count` on the TRADE
                            object. 3,979,927 rows stored with a null price.
                            Its own recorder's docstring warned about exactly
                            this, in those words, and the new puller did it
                            anyway.

The last one is why this module exists rather than another paragraph of prose:
**the warning was already written down and was read past.** GUARDS #6 records
the same lesson from the fee formula, which went from 3 copies to 17 while the
rule was only a convention and stopped at 17 the day it became a failing test.

## The two halves

`LIVE` / `DEAD` below are the map, measured against the live API on 2026-08-07
rather than recited from documentation. `assert_priced()` is the runtime
content-assert: call it once on the first object of any pull, and a schema
change costs ten seconds instead of two fifty-minute pulls.

## The subtlety that makes a blanket ban WRONG

On **candlesticks**, `yes_bid` / `yes_ask` / `price` are still live — but as
*containers* whose leaves are `*_dollars`:

    candle["yes_bid"]["close_dollars"]      correct
    candle["yes_bid"]                       a dict, not a number

while on the same candlestick object `volume` and `open_interest` **are** dead
and renamed to `volume_fp` / `open_interest_fp`. So "candlesticks are exempt"
is also wrong, and that half-truth is currently the guidance in STATUS.md.
A checker has to know the object KIND, which is why this is a table and not a
regex.
"""
from __future__ import annotations

# kind -> {dead_name: live_name}. Measured against api.elections.kalshi.com
# on 2026-08-07; every "dead" name below was verified ABSENT from the object,
# and every "live" name verified present.
DEAD = {
    "market": {
        "yes_bid": "yes_bid_dollars", "yes_ask": "yes_ask_dollars",
        "no_bid": "no_bid_dollars", "no_ask": "no_ask_dollars",
        "last_price": "last_price_dollars",
        "previous_price": "previous_price_dollars",
        "previous_yes_bid": "previous_yes_bid_dollars",
        "previous_yes_ask": "previous_yes_ask_dollars",
        "volume": "volume_fp", "volume_24h": "volume_24h_fp",
        "open_interest": "open_interest_fp",
        "yes_bid_size": "yes_bid_size_fp", "yes_ask_size": "yes_ask_size_fp",
    },
    "trade": {
        "yes_price": "yes_price_dollars", "no_price": "no_price_dollars",
        "count": "count_fp",
    },
    "orderbook": {
        "orderbook": "orderbook_fp",
        "yes": "yes_dollars", "no": "no_dollars",
    },
    # On a candlestick, `volume` and `open_interest` ARE dead. `yes_bid`,
    # `yes_ask` and `price` are NOT -- see LIVE_CONTAINERS.
    "candlestick": {
        "volume": "volume_fp", "open_interest": "open_interest_fp",
    },
}

# kind -> names that survive but are CONTAINERS. Reading one gets you a dict,
# not a number, and `float()` on it raises -- which is the good case, because
# it is loud.
LIVE_CONTAINERS = {
    "candlestick": {
        "yes_bid": ("open_dollars", "high_dollars", "low_dollars",
                    "close_dollars"),
        "yes_ask": ("open_dollars", "high_dollars", "low_dollars",
                    "close_dollars"),
        "price": ("open_dollars", "high_dollars", "low_dollars",
                  "close_dollars", "mean_dollars", "previous_dollars"),
    },
}

# The minimum set that must be present AND non-None for the object to be usable
# at all. This is what `assert_priced` demands.
REQUIRED = {
    "market": ("yes_bid_dollars", "yes_ask_dollars"),
    "trade": ("yes_price_dollars", "count_fp"),
    "orderbook": ("orderbook_fp",),
    "candlestick": ("price",),
}

KINDS = tuple(DEAD)


class KalshiSchemaError(RuntimeError):
    """Raised when an object does not carry the fields it must carry."""


def assert_priced(obj, kind, where=""):
    """Fail loudly on the FIRST object of a pull if the schema has moved.

    GUARDS #13: a 200 and a row count are not a result. This is the ten-second
    version of the check that would have caught 3.98 million null-priced rows
    before the second fifty-minute pull.

    Call it once per pull, not per row -- it is a schema assertion, not a
    filter. Rows that individually lack a price should still be skipped by the
    caller and COUNTED, because "how many were unpriced" is itself a health
    number.
    """
    if kind not in REQUIRED:
        raise ValueError(f"unknown Kalshi object kind {kind!r}; "
                         f"expected one of {KINDS}")
    if not isinstance(obj, dict):
        raise KalshiSchemaError(
            f"{where or kind}: expected a dict, got {type(obj).__name__}")

    missing = [f for f in REQUIRED[kind] if obj.get(f) is None]
    if not missing:
        return True

    # Say WHICH dead name the caller probably reached for. A bare "field
    # missing" sends the reader to the network; naming the rename sends them
    # to the one-line fix.
    hints = []
    for dead, live in DEAD[kind].items():
        if dead in obj and live not in obj:
            hints.append(f"the object carries {dead!r} but not {live!r} -- "
                         f"the schema may have moved BACK, which nothing here "
                         f"expects; check before assuming")
    present = sorted(k for k in obj if isinstance(k, str))[:12]
    raise KalshiSchemaError(
        f"{where or kind}: required field(s) {missing} are absent or None. "
        f"This is the renamed-field trap (GUARDS #23). The live names end in "
        f"_dollars or _fp; the legacy integer-cent names are GONE and read "
        f"None on every object. Keys actually present: {present}. "
        + (" ".join(hints) if hints else ""))


def dead_names(kind=None):
    """Every legacy name, optionally for one kind. Used by the static test."""
    if kind:
        return dict(DEAD[kind])
    out = {}
    for k in DEAD.values():
        out.update(k)
    return out


def live_for(dead_name, kind=None):
    """The replacement for a legacy name, or None if it is not a known one."""
    return dead_names(kind).get(dead_name)


def is_container(name, kind):
    """True if `name` survives on this kind but returns a dict, not a number."""
    return name in LIVE_CONTAINERS.get(kind, {})


if __name__ == "__main__":
    import json
    import urllib.request

    UA = {"User-Agent": "trading-research/1.0 (guard self-check)"}
    B = "https://api.elections.kalshi.com/trade-api/v2"

    def g(u):
        return json.load(urllib.request.urlopen(
            urllib.request.Request(u, headers=UA), timeout=40))

    print("re-verifying the field map against the live API")
    m = g(B + "/markets?limit=1&status=open")["markets"][0]
    bad = [d for d in DEAD["market"] if d in m]
    good = [l for l in DEAD["market"].values() if l not in m]
    print(f"  market      : {len(DEAD['market'])} dead names, "
          f"{len(bad)} unexpectedly PRESENT {bad}")
    print(f"                {len(good)} live names unexpectedly ABSENT {good}")
    assert_priced(m, "market", "self-check")
    ob = g(f"{B}/markets/{m['ticker']}/orderbook?depth=1")
    print(f"  orderbook   : top-level keys {list(ob)}")
    assert_priced(ob, "orderbook", "self-check")
    print("\nself-check OK -- the map matches the live API.")
