"""Reference implementations of the two things everything else depends on:
the fee formula and the position P&L decomposition.

These exist to be TESTED. `build_21_wallet_positions.py` implements the same
arithmetic inline for streaming reasons, and `tests/test_accounting.py`
recomputes a sample of its real output through these functions and asserts
agreement -- so this is a check on the actual pipeline, not a parallel copy that
could drift from it silently.
"""
from decimal import Decimal

# Verified empirically against 5,362 on-chain fee-bearing fills:
# median relative error 7.71e-08, 100.0% within 1%, modal implied rate 1000 bps.
# The DOCUMENTED schedule, 0.07*p*(1-p), matched 0.0% and is wrong.
POLY_FEE_RATE = 0.10
POLY_FEE_BPS = 1000
EPS = 1e-6


def poly_fee_per_share(price):
    """Economic taker fee in dollars per share: rate * min(p, 1-p)."""
    if not 0.0 < price < 1.0:
        raise ValueError(f"price out of range: {price}")
    return POLY_FEE_RATE * min(price, 1.0 - price)


def poly_fee(price, shares):
    """Economic taker fee in dollars for `shares` at `price`."""
    return poly_fee_per_share(price) * shares


def poly_fee_raw_onchain(price, shares, side):
    """The RAW on-chain `fee` amount, in the asset the MAKER receives.

    `OrderFilled` amounts describe what the maker gave and received, and the fee
    is charged on the maker's leg:
        makerAssetId == 0 -> maker paid USDC, got tokens -> BUY, fee in tokens
        takerAssetId == 0 -> maker paid tokens, got USDC -> SELL, fee in USDC

    Inverting this is exactly the error that produced a 0.96 median relative
    error before it was caught, so the two branches are kept explicit.
    """
    m = min(price, 1.0 - price)
    if side == "BUY":
        return POLY_FEE_RATE * m * shares / price      # outcome tokens
    if side == "SELL":
        return POLY_FEE_RATE * m * shares              # collateral
    raise ValueError(f"bad side: {side}")


def decode_fill(maker_asset_id, taker_asset_id, maker_amount, taker_amount,
                usdc_decimals=1_000_000.0):
    """-> (side, token_id, shares, usdc, price) from the MAKER's perspective."""
    ma, ta = str(maker_asset_id), str(taker_asset_id)
    mf, tf = int(maker_amount), int(taker_amount)
    if ma == "0" and ta != "0":
        side, token, shares, usdc = "BUY", ta, tf, mf
    elif ta == "0" and ma != "0":
        side, token, shares, usdc = "SELL", ma, mf, tf
    else:
        return None                        # token-for-token, not a cash trade
    if shares <= 0 or usdc <= 0:
        return None
    price = usdc / shares
    if not 0.0 < price < 1.0:
        return None
    return side, token, shares / usdc_decimals, usdc / usdc_decimals, price


def reconstruct(events, is_winner):
    """Position P&L for one (wallet, market, outcome token).

    `events`: iterable of (ts, side, shares, price, fee_usd), CHRONOLOGICAL.
    `is_winner`: True / False / None (None = no settlement available).

    The metric that matters:
        edge = realised value per share - average entry price
             = (proceeds + settlement value) / shares_in  -  cost / shares_in

    Never a win rate. A wallet buying at 0.90 and winning 90% has zero edge.
    A position exited early is scored at its exit price; one held to settlement
    at 0 or 1. That is the wallet's realised outcome.

    A negative running balance means tokens arrived from a split (USDC -> a
    complete set), which is a ConditionalTokens event absent from the orderbook
    subgraph. Those have an entry cost we cannot see, so they are FLAGGED and
    excluded from edge statistics -- never repaired with an assumed cost.
    """
    shares_in = cost = shares_out = proceeds = fees = 0.0
    bal = min_bal = 0.0
    n_buy = n_sell = 0
    first_ts = last_ts = None

    for ts, side, shares, price, fee_usd in events:
        if first_ts is None:
            first_ts = ts
        last_ts = ts if last_ts is None else max(last_ts, ts)
        fees += fee_usd
        if side == "BUY":
            shares_in += shares
            cost += shares * price
            bal += shares
            n_buy += 1
        elif side == "SELL":
            shares_out += shares
            proceeds += shares * price
            bal -= shares
            n_sell += 1
        else:
            raise ValueError(f"bad side: {side}")
        min_bal = min(min_bal, bal)

    flags = []
    if min_bal < -EPS:
        flags.append("negative_balance_split_or_external")
    if shares_in <= EPS:
        flags.append("no_buys_sell_only")

    held = bal > EPS
    settle_value = (max(bal, 0.0) * (1.0 if is_winner else 0.0)
                    if is_winner is not None else None)

    if shares_in > EPS and settle_value is not None:
        entry_px = cost / shares_in
        realised = (proceeds + settle_value) / shares_in
        edge = realised - entry_px
        edge_net = edge - fees / shares_in
        pnl = proceeds + settle_value - cost - fees
    else:
        entry_px = (cost / shares_in) if shares_in > EPS else None
        realised = edge = edge_net = pnl = None

    return {
        "n_trades": n_buy + n_sell, "n_buys": n_buy, "n_sells": n_sell,
        "shares_in": shares_in, "shares_out": shares_out,
        "cost": cost, "proceeds": proceeds, "fees": fees,
        "final_balance": bal, "min_balance": min_bal,
        "held_to_settlement": held, "settle_value": settle_value,
        "entry_px": entry_px, "realised_per_share": realised,
        "edge": edge, "edge_net": edge_net, "pnl": pnl,
        "first_ts": first_ts, "last_ts": last_ts,
        "flags": flags,
    }
