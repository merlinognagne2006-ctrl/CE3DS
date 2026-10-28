# Strumenti di verifica di FINANCIAL BOT

Questi file **non servono per usare l'EA**. Servono a ripetere i controlli fatti sul codice. Funzionano su Linux con g++ (C++17) e Python 3 (pandas).

| File | A cosa serve |
|---|---|
| `mq5tocpp.py` | Traduce `FINANCIAL_BOT.mq5` in C++. Il programma viene racchiuso in una struct, e i letterali, gli array e gli input MQL5 diventano equivalenti C++ |
| `mql5shim.hpp` | Le funzioni MQL5 usate dall'EA, ricreate in C++ con un broker simulato: barre M1, bid/ask, stop lato server, storico, variabili globali, file, CTrade con le stesse firme della libreria standard |
| `check_main.cpp` | Controllo di compilazione: `python3 mq5tocpp.py FINANCIAL_BOT.mq5 FINANCIAL_BOT.check.hpp check && g++ -std=c++17 -fsyntax-only -Wall -Wextra check_main.cpp` |
| `harness.cpp` | Backtest del codice vero dell'EA sui dati al minuto, con le regole prop (perdita giornaliera e totale) controllate minuto per minuto e i payout mensili |
| `export_bin.py` | Converte i dati M1 (parquet, UTC) nel formato binario del simulatore |
| `run_years.sh` | Backtest completo 2011-2026, un anno per processo |
| `challenges.py` | Una challenge che parte ogni mese: fase 1, fase 2 e 6 mesi di conto finanziato |
| `challenges_combo.py` | Stesse challenge con le fasi in Qualità e il conto finanziato in Bilanciata |
| `table_to_mq5.py` | Riscrive la tabella dei punti dell'EA da un file JSON. È servito a controllare che la tabella nell'EA sia identica a quella della ricerca e a creare la variante "costruita nel 2021" |
| `analisi/parity.py`, `analisi/trades_cmp.py` | Confronto segnale per segnale e trade per trade con la ricerca |
| `analisi/final_report.py` | Riassunto delle challenge storiche (esiti effettivi letti dai risultati di ogni fase) |
| `test_instance.cpp`, `test_live.cpp`, `test_panel.cpp` | Prove di una sola copia per conto, fuso orario del server, calendario MT5 e ForexFactory, pannello e pulsanti |

Per compilare il backtest, dalla cartella che contiene `harness.cpp`:

```
python3 mq5tocpp.py ../FINANCIAL_BOT.mq5 FINANCIAL_BOT.run.hpp run
g++ -std=c++17 -O2 -I. -o harness harness.cpp
```

Il backtest legge i dati da `data/NAS_M1.bin` e `data/XAU_M1.bin`, preparati con `export_bin.py`, e le notizie da `common/FINANCIAL_BOT_news_history.csv`.

Per cercare errori di memoria aggiungi `-fsanitize=address,undefined` alla compilazione.
