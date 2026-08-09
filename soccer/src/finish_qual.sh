#!/bin/bash
# Wait for the qualifier backfill, then run everything that depends on it.
cd "$(dirname "$0")/../.."
LOG=soccer/reports/qual_chain.log
echo "waiting for backfill_run3..." > $LOG
for i in $(seq 1 400); do
  grep -q "^DONE in" soccer/reports/backfill_run3.log 2>/dev/null && break
  sleep 15
done
echo "backfill done at $(date)" >> $LOG
py -3 soccer/src/fetch_goal_minutes.py     >> soccer/reports/goal_minutes_run3.log 2>&1
echo "goal minutes done" >> $LOG
py -3 soccer/src/build_strength.py          >> soccer/reports/strength_run.log 2>&1
echo "strength done" >> $LOG
py -3 soccer/src/fetch_clock_anchors.py     >> soccer/reports/clock_anchors_run2.log 2>&1
echo "anchors done" >> $LOG
py -3 soccer/src/build_comeback_table.py    >> soccer/reports/table_run2.log 2>&1
echo "table done" >> $LOG
py -3 soccer/src/price_by_minute.py         >> soccer/reports/price_by_minute_run2.log 2>&1
echo "prices done" >> $LOG
py -3 soccer/src/clock_map.py               >> soccer/reports/clock_map_run2.log 2>&1
py -3 soccer/src/era_split.py               >> soccer/reports/era_run2.log 2>&1
py -3 soccer/src/gap_table.py               >> soccer/reports/gap_run2.log 2>&1
py -3 soccer/src/overreaction.py            >> soccer/reports/over_run2.log 2>&1
echo "CHAIN_COMPLETE $(date)" >> $LOG
