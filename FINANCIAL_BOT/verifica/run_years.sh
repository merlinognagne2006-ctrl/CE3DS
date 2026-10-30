#!/bin/bash
# backtest completo per anni (in parallelo), impostazioni di base senza obiettivo/perdita massima
# uso: HARNESS=./harness Y0=2011 Y1=2026 ./run_years.sh cartella [--set Inp=valore ...]
OUT=${1:-runs/full}; shift; EXTRA="$*"; H=${HARNESS:-./harness}; Y0=${Y0:-2011}; Y1=${Y1:-2026}
mkdir -p $OUT
for y in $(seq $Y0 $Y1); do
  echo "--from $y-01-01 --to $((y+1))-01-01 --out $OUT/$y --set InpTargetPct=0 --set InpMaxLossPct=1000 $EXTRA" | sed 's/ *$//'
done | xargs -P 4 -L 1 $H > $OUT/run.txt 2>&1
sort $OUT/run.txt
