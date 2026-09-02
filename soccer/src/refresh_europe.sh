#!/bin/bash
# Pull the European season into local storage before Kalshi's ~69-day window
# drops it. Data pulled is permanent; data left in the API is not. SO006 died
# exactly this way -- the dataset it needed aged out before anyone re-ran it.
cd "$(dirname "$0")/../.."
L=soccer/reports/europe_chain.log
echo "start $(date)" > $L
py -3 soccer/src/backfill_espn.py       >> soccer/reports/backfill_run4.log 2>&1
echo "fixtures done $(date)" >> $L
py -3 soccer/src/fetch_goal_minutes.py  >> soccer/reports/goal_minutes_run4.log 2>&1
echo "goal minutes done $(date)" >> $L
py -3 soccer/src/build_strength.py      >> soccer/reports/strength_run2.log 2>&1
echo "strength done $(date)" >> $L
py -3 soccer/src/fetch_clock_anchors.py >> soccer/reports/clock_anchors_run3.log 2>&1
echo "anchors done $(date)" >> $L
py -3 soccer/src/price_by_minute.py     >> soccer/reports/price_by_minute_run4.log 2>&1
echo "PRICES DONE $(date)" >> $L
