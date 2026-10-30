# Ricerca di FINANCIAL BOT

Gli script Python usati per trovare e validare la strategia. Sono qui **come documentazione**. Per rifarli servono i dati storici al minuto (circa 1 GB), che non sono nel repository; le fonti sono elencate più sotto.

## I file che hanno portato a FINANCIAL BOT

| File | A cosa serve |
|---|---|
| `prep_hist.py`, `prep_dukas_gold.py`, `prep_news.py`, `build_feats.py` | Preparazione dei dati: M1 in UTC, notizie, caratteristiche su candele M5 |
| `feat.py` | Caratteristiche calcolate solo su candele chiuse: ATR di Wilder, impulsi, VWAP, trend H1 e M15 |
| `engine2.py`, `strat_lab.py` | Simulatore ordine per ordine al minuto: stop, trailing, uscita a tempo, costi |
| `lab_trendday.py` | Noise area (Zarattini-Aziz-Barbon) e pullback nella giornata di trend |
| `candidates_nas.py` | I 5 segnali di accelerazione, le regole di sessione e le caratteristiche di ogni segnale |
| `score_build.py`, `score24.py` | Il punteggio deterministico: punti per fascia di ogni caratteristica, stimati su un periodo e verificati su un altro |
| `exits_test.py` | Confronto delle uscite: i target fissi distruggono il vantaggio; vince stop 1,5 ATR con trailing |
| `portfolio_sim.py`, `mc_v2.py`, `mc_final2.py`, `final_stats.py` | Regole di portafoglio dell'EA (posizioni massime, stop giornalieri, rischio dinamico, notizie) e Monte Carlo delle challenge |
| `score_table_FINAL.json` | La tabella dei punti usata dall'EA, stimata su 2014-2026 |
| `score_table_IS2021.json` | La stessa tabella stimata solo sul 2014-2021, usata per la prova "come se costruito nel 2021" |

Gli altri file (`groupb*`, `groupc*`, `selector*`, `strategies.py`, `run*`, `portfolio.py`, `mc_final.py`, `mc_groups.py`, …) appartengono alle prime fasi del lavoro, cioè ai vecchi gruppi di bot A/B/C. **Quei bot non hanno retto sul periodo 2014-2026 e sono stati sostituiti da FINANCIAL BOT.**

## Fonti dei dati

| Dato | Fonte |
|---|---|
| Nasdaq 100 e oro al minuto | HistData, già convertiti in UTC dal repository GitHub `antonyaca/Aca5983` |
| Oro al minuto con spread e volume | `Dypoi/XAUUSD_Dataset` (dati Dukascopy) |
| Calendario delle notizie | `spoluan/forex-factory-scraper` e `ehsanrs2/forexfactory-scraper` (ForexFactory) |

Gli script contengono ancora i percorsi locali usati durante la ricerca. La verifica del codice dell'EA, cioè il backtest del codice MQL5 vero, sta in `FINANCIAL_BOT/verifica/`.
