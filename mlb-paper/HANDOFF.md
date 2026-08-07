# HANDOFF — mlb-paper

**Written 2026-08-07.** A paper-only forward test of five MLB mentalities on
Kalshi. No credentials, no order endpoint, no money — enforced by a test that
walks every file and is itself checked against a planted violation.

Read in this order: [MENTALITIES.md](MENTALITIES.md) →
[TARGET_CHOICE.md](TARGET_CHOICE.md) → [PREREGISTRATION.md](PREREGISTRATION.md)
→ [DECISIONS.md](DECISIONS.md). The joint multiplicity declaration is at the
repo root: [../JOINT_MULTIPLICITY.md](../JOINT_MULTIPLICITY.md).

---

## 1. What this is

Sixteen bots — **five mentalities × three exit modes, plus a no-trade control**
— trading the same pool of Kalshi MLB games on paper, with free entry and none
forced. Every decision writes its full reasoning and a sha1 of it to disk
**before the game starts**; `outcome_known` is set only by the settlement pass.

| mentality | claim | target |
|---|---|---|
| `starter` | only *new* pitcher news — debut, short rest, last-3-starts divergence | `KXMLBGAME` |
| `park-air` | tonight's air against a normal night at this park | `KXMLBTOTAL` |
| `bullpen` | the third of the game nobody reprices | `KXMLBTOTAL` |
| `early` | the window before the sharp line exists | `KXMLBGAME` |
| `lineup` | lineup-drop **latency**, not lineup information | `KXMLBGAME` |

## 2. The three measurements that already exist, before any settlement

**These are results, not plumbing, and they were all taken this session.**

### 2a. Kalshi's MLB price IS the de-vigged sharp line, on runs as well as winners

| | joined markets | games | median Pinnacle vig | **qualifying at > cost** | best net edge (hindsight) |
|---|---|---|---|---|---|
| `KXMLBGAME` | 20 | 10 | 2.55 pp | **0 (0.0%)** | **−1.82¢** |
| `KXMLBTOTAL` | 38 | 10 | 4.01 pp | **0 (0.0%)** | **−1.63¢** |

Extends `bot-hunt`'s q = 0 of 17 to totals for the first time. Fifth
independent confirmation in this repo.

### 2b. The mismatched-pair placebo fires exactly as designed

| | qualifying | best net edge |
|---|---|---|
| `KXMLBGAME` **placebo** | **8 of 18 (44%)** | **+24.76¢** |
| `KXMLBTOTAL` **placebo** | **28 of 34 (82%)** | **+20.49¢** |

A deliberately wrong join manufactures a large, confident, entirely fake edge.
**Any future MLB result that does not clear its own placebo by a wide margin is
a join error.** Not hypothetical: the first version of `target_choice.py`
reported an 80% qualifying rate and a 57¢ best edge because it matched on the
club pair without the start time, and baseball teams play each other three days
running.

### 2c. Neither over/under nor first-inning beats moneyline as the target

`SCOREBOARD.md`'s "**249** over/under markets recorded and never examined" is an
**11-strike ladder**: ~23 games, not 249. The "71 first-inning" figure is honest
(1 rung per game) but that market costs **6.5¢ to enter** against 3.0¢, shows
**two contracts** at the touch, and has no reference price anywhere. Dropped.
Over/under is kept as a co-target because it ties moneyline on cost, carries
**15× the depth**, and is where run-shaped information belongs. Full working in
[TARGET_CHOICE.md](TARGET_CHOICE.md).

## 3. What is running, where, and how to check it

| | |
|---|---|
| process | `mlb-paper/.venv/Scripts/python.exe src/run.py`, one tick per 300 s |
| writes to | `mlb-paper/data/paper.db` (gitignored), `mlb-paper/data/briefs/` |
| **the one command** | `deploy\check.bat` — first line is `ALIVE` or `*** STALE ***` |
| laptop install | `deploy\setup.bat`, then `deploy\install_task.ps1`. Click-by-click in [deploy/README.md](deploy/README.md) |

A PID lock refuses a second runner. A heartbeat row makes staleness visible in
one command. Both exist because `bot-hunt`'s recorder **died for 2.5 hours with
zero bytes in its error log and nothing noticed**.

## 4. What the pre-registration commits to, so it cannot be softened later

- **The P&L endpoint is UNTESTABLE.** sd ≈ 50¢ per game on a near-coin-flip
  market means resolving the measured 3.0¢ cost bar under the joint correction
  needs **~4,004 settled games per bot ≈ two and a half years**.
- **The primary endpoint is closing-line value**, sd ≈ 3¢, where **n = 130
  resolves 1.0¢** — reachable inside a month. That choice follows the one piece
  of external advice in the corpus that survives an n-check.
- **One BH denominator of 32 across BOTH forward tests**, superseding tennis's
  16. See [../JOINT_MULTIPLICITY.md](../JOINT_MULTIPLICITY.md).
- **Predicted: every bot lands between −3.0¢ and +0.5¢ on CLV, and only `early`
  has a mechanism for a positive number.** Written as a number so it can be
  wrong.

## 5. Free data sources, and the two that are forbidden

| source | status |
|---|---|
| `statsapi.mlb.com` | **ALLOWED.** Probables a day ahead, pitcher game logs with pitch counts, boxscore `battingOrder` and bullpen, standings with home/road splits, venue elevation **and `azimuthAngle`**, linescore for settlement |
| `aviationweather.gov` (NOAA) | **ALLOWED**, no robots.txt at all. METAR + **TAF**, a 24–30 h forecast of wind direction, speed, gusts and precipitation |
| `guest.api.arcadia.pinnacle.com` | **ALLOWED.** The sharp reference. Returns **HTTP 401 under load** — a rate limit wearing a credential status code, so it is optional everywhere |
| `api.elections.kalshi.com` | **ALLOWED**, public read only |
| `api.open-meteo.com` | 🚫 **`User-agent: * / Disallow: /`** |
| `api.weather.gov` | 🚫 **`User-agent: * / Disallow: /`** |
| `retrosheet.org/gamelogs/` | 🚫 explicitly disallowed (the rest of the site is not) |

`reports/robots_policy.json` is the enforcement point, not a report:
`robots_check.allowed()` refuses any host that has not been checked.

## 6. Field traps found this session — all four cost a wrong number first

1. **Kalshi's MLB ticker time is US EASTERN, not UTC.** Read as UTC every game
   sits 4 h early and the Pinnacle join rejected **100%** of candidates as
   "wrong day of the series". Verified two ways.
2. **Pinnacle's `/matchups` is 148 of 161 SPECIALS** ("Odd"/"Even" total runs),
   not games. Only `type == "matchup"` with home/away alignment is a game, and
   a special carries its real game inside `parent`.
3. **Pinnacle moneyline sides are keyed by `designation`, not `participantId`.**
   On games reached via a special's `parent` those ids are all `None`, the name
   lookup returns the same team for both prices, and the side is chosen at
   random. Symptom: Toronto quoted 33.5¢ came back with a 66.65¢ "fair value"
   and a 29.65¢ "edge". Read correctly the two prices agree to 0.2¢.
4. **`/orderbook` returns `orderbook_fp.yes_dollars`**, not `orderbook.yes` —
   the fourth renamed-field trap in this repo, after C024. The touch sizes are
   on the market object anyway.

And two that are general rather than Kalshi-specific:

5. **`hash()` on a `str` is salted per process**, so a cache keyed on it never
   hits across runs while looking exactly like a working cache.
6. **`zoneinfo` has no tz database on Windows.** `tzdata` is a hard dependency
   or every ticker parses four hours early.

## 7. The single next thing

**Let it run and check `deploy\check.bat` once a day.** The first decidable
answer is P5 (does the brief exist for the games Kalshi lists, by lead time),
which needs about a week. P1, the CLV endpoint, needs **n ≈ 130 decisions per
bot**; at the observed firing rates that is roughly **three to four weeks** for
`starter` and `early`, and longer for `park-air` and `bullpen` — which is why
shadow decisions exist.

**Do not read the P&L table before then.** It is pre-registered UNTESTABLE and
the archive's whole record is that the first thing anyone does with an
underpowered P&L number is believe it.
