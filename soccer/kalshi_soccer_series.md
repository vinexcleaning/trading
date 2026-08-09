# What Kalshi actually lists per soccer match

**Measured 2026-08-08** by asking Kalshi directly for settled events on each
series ticker. Read-only, unauthenticated, no credentials.

This was an open question. Two documents in this repo disagreed and **both were
badly incomplete**:

- `soccer/dataset.md` said five competitions: Liga MX, Argentina, Copa do
  Brasil, Colombia, MLS.
- `soccer/reports/tape_soccer_scan.json` showed ten, dominated by international
  friendlies.
- The tasking noted that **neither mentioned the Premier League or the Champions
  League**, and asked the `devig` chat for a definitive list.

**The Premier League and the Champions League are both there, and so is most of
Europe.** Nobody had looked.

## Per-match series that exist and have settled markets

| Kalshi series | Competition | ESPN slug | In the backfill |
|---|---|---|---|
| `KXEPLGAME` | Premier League | `eng.1` | yes |
| `KXUCLGAME` | Champions League | `uefa.champions` | yes |
| `KXUELGAME` | Europa League | `uefa.europa` | **added 08-08** |
| `KXLALIGAGAME` | La Liga | `esp.1` | yes |
| `KXSERIEAGAME` | Serie A | `ita.1` | yes |
| `KXBUNDESLIGAGAME` | Bundesliga | `ger.1` | yes |
| `KXLIGUE1GAME` | Ligue 1 | `fra.1` | **added 08-08** |
| `KXWCGAME` | World Cup | `fifa.world` | **added 08-08** |
| `KXCLUBWCGAME` | Club World Cup | `fifa.cwc` | **added 08-08** |
| `KXMLSGAME` | MLS | `usa.1` | yes |
| `KXLIGAMXGAME` | Liga MX | `mex.1` | yes |
| `KXDIMAYORGAME` | Colombia | `col.1` | yes |
| `KXURYPDGAME` | Uruguay | `uru.1` | yes |
| `KXPERLIGA1GAME` | Peru | `per.1` | yes |
| `KXECULPGAME` | Ecuador | `ecu.1` | yes |
| `KXCHLLDPGAME` | Chile | `chi.1` | yes |
| `KXUSLGAME` | USL | `usa.usl.1` | yes |
| `KXNWSLGAME` | NWSL | `usa.nwsl` | yes |
| `KXCOPADOBRASILGAME` | Copa do Brasil | `bra.copa_do_brazil` | yes |
| `KXINTLFRIENDLYGAME` | International friendlies | `fifa.friendly` | yes |

## The friendlies figure was a calendar artifact, as suspected

`tape_soccer_scan.json` found 139 of 210 tickers were international friendlies
and the tasking asked, reasonably, whether Kalshi's soccer book is mostly
friendlies — which would matter, because a friendly is a different sport for
this purpose.

**It is not.** That scan covers 2026-05-24 to 06-11, which is the international
break immediately before the 2026 World Cup — the fortnight when friendlies are
nearly all the football there is. The most recent settled friendly event on
Kalshi is `KXINTLFRIENDLYGAME-26JUN11AUTGTM`, i.e. the series went quiet exactly
when the break ended, while MLS, Liga MX, Colombia, Uruguay, Peru, Ecuador,
Chile, USL, NWSL and Copa do Brasil all have settled events dated August 2026.

Friendlies are still kept as their own competition in the table rather than
blended in.

## Not found, and worth someone checking

**No per-match series was found for the Brazilian Serie A or the Argentine
league**, despite `soccer/dataset.md` listing Argentina as bettable and
`espn_backfill_coverage.json` carrying both. Tickers tried and empty:
`KXBRASERIEAGAME`, `KXBRAGAME`, `KXBRASILEIRAOGAME`, `KXBRASILGAME`,
`KXARGGAME`, `KXARGLPFGAME`, `KXARGPRIMERAGAME`, `KXARGENTINAGAME`.

That is a failure to guess the right ticker, **not** evidence the markets do not
exist. Both leagues stay in the backfill, because the fixture data is free and
the cost of being wrong in that direction is nothing.

## What this does not say

Nothing here measures **liquidity**. A series existing is not the same as a
market you can get filled in, and the whole B024 result in `LEDGER.md` turns on
exactly that distinction — an edge that was real on the mid and gone at the ask.
Depth and spread per series is still the `devig` chat's question and is not
answered here.
