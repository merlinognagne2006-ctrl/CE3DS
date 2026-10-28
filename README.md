# FINANCIAL BOT

**Expert Advisor per MetaTrader 5 che fa trading da solo sul Nasdaq 100 e sull'oro, pensato per superare le challenge delle prop firm.**

Entra quando il Nasdaq **accelera** e solo se il segnale ottiene un **punteggio di qualità** abbastanza alto. Lascia correre i trade buoni, chiude in fretta quelli sbagliati e rispetta sempre i limiti di perdita della prop. Non usa machine learning: ogni decisione segue regole fisse, verificabili e stimate su 12 anni di dati.

![Pannello di FINANCIAL BOT](FINANCIAL_BOT/report/pannello.png)

---

## Indice

1. [In breve](#1-in-breve)
2. [Come funziona, passo per passo](#2-come-funziona-passo-per-passo)
3. [Il punteggio di qualità](#3-il-punteggio-di-qualità)
4. [Quanto rischia per ogni trade](#4-quanto-rischia-per-ogni-trade)
5. [Come esce dai trade](#5-come-esce-dai-trade)
6. [Le protezioni del conto](#6-le-protezioni-del-conto)
7. [Il filtro notizie](#7-il-filtro-notizie)
8. [L'oro](#8-loro)
9. [Due giornate vere, minuto per minuto](#9-due-giornate-vere-minuto-per-minuto)
10. [Le tre modalità](#10-le-tre-modalità)
11. [Risultati](#11-risultati)
12. [Installazione](#12-installazione)
13. [Il pannello](#13-il-pannello)
14. [Tutte le impostazioni](#14-tutte-le-impostazioni)
15. [Cosa NON fa](#15-cosa-non-fa)
16. [Domande frequenti](#16-domande-frequenti)
17. [Contenuto del repository](#17-contenuto-del-repository)

---

## 1. In breve

| | |
|---|---|
| **Mercati** | Nasdaq 100 (motore principale) e oro (solo durante gli shock di volatilità) |
| **Piattaforma** | MetaTrader 5, un solo EA su un solo grafico qualsiasi |
| **Stile** | Momentum intraday: entra quando il prezzo accelera, come i fondi che seguono il trend della giornata |
| **Trade al giorno** | Circa 3-4 nella modalità predefinita (Qualità) |
| **Durata dei trade** | Da pochi minuti (quelli sbagliati) a 2 ore al massimo (quelli buoni) |
| **Stop loss** | Sempre presente, sul server del broker, a 1,5 volte la volatilità a 5 minuti (ATR) |
| **Take profit** | Nessuno: il guadagno lo protegge un trailing stop |
| **Rischio per trade** | 0,25% del capitale di base. Con il rischio dinamico di solito tra 0,17% e 0,44%, al massimo 0,75% |
| **Limiti** | Massimo 3 posizioni aperte, perdita giornaliera 3%, perdita massima 9%, stop dopo 3 perdite di fila |
| **Notizie** | Nessun ingresso da 5 minuti prima a 5 minuti dopo le notizie USA rosse e gialle |
| **Notte e weekend** | Mai posizioni aperte durante la chiusura giornaliera né nel weekend |
| **Automatico** | Riconosce da solo simboli, capitale, fuso orario del server e calendario delle notizie |

---

## 2. Come funziona, passo per passo

Ogni 5 minuti, alla chiusura di una candela, FINANCIAL BOT ripete questi passi.

### Passo 1: misura il mercato

Calcola sulle candele a 5 minuti **già chiuse** (mai su quella in corso, così non "sbircia il futuro"):

- **ATR**, la volatilità normale del momento: quanto si muove in media il prezzo in 5 minuti. Tutte le distanze del bot sono misurate in ATR, così si adatta da solo ai giorni calmi e a quelli agitati;
- **VWAP**, il prezzo medio della giornata;
- la **media mobile a 20 periodi**;
- il **trend a 1 ora**, a **15 minuti** e **giornaliero**;
- la **noise area**: la fascia entro cui il Nasdaq si muove "normalmente" a quell'ora, calcolata sugli stessi orari dei 14 giorni precedenti.

### Passo 2: cerca un'accelerazione (5 segnali)

| # | Segnale | Quando scatta (esempio per un acquisto; per una vendita è l'opposto) |
|---|---|---|
| 1 | **Impulso 15 minuti** | Il prezzo è salito di almeno **1,5 ATR** nelle ultime 3 candele |
| 2 | **Impulso 30 minuti** | Il prezzo è salito di almeno **2,5 ATR** nelle ultime 6 candele |
| 3 | **Distanza dal VWAP** | Il prezzo è almeno **2 ATR sopra il prezzo medio della giornata** e il trend a 1 ora è al rialzo |
| 4 | **Pullback nel trend** | È una giornata di trend (prezzo fuori dalla noise area), il prezzo è tornato a toccare la media a 20 e ora riparte superando il massimo della candela precedente |
| 5 | **Uscita dalla noise area** | Il prezzo esce sopra la fascia di movimento normale per quell'ora (metodo di Zarattini, Aziz e Barbon, usato dai fondi momentum sul mercato americano) |

Se almeno un segnale scatta e **nessuno indica la direzione opposta**, c'è un candidato. Se i segnali sono in contrasto, il bot non fa niente.

### Passo 3: dà un voto al candidato

Calcola il **punteggio di qualità** sommando i punti di 10 caratteristiche (paragrafo 3).

### Passo 4: decide se entrare

Entra solo se **tutte** queste condizioni sono vere:

- il punteggio supera la **soglia della modalità**: 30 in Qualità, 20 in Bilanciata, 10 in Alta frequenza;
- è il **primo minuto** della nuova candela, quindi il segnale è fresco;
- **non** si è tra le 16:00 e le 18:30 di New York (chiusura e riapertura giornaliera del Nasdaq) e **non** è venerdì dopo le 15:30 di New York;
- **non** si è nella finestra di ±5 minuti di una notizia rossa o gialla;
- sul conto ci sono **meno di 3 posizioni aperte**, contando anche quelle manuali o di altri EA;
- lo **spread** è normale (meno di un quarto dell'ATR);
- la giornata e il conto **non sono fermi** per una delle protezioni (paragrafo 6);
- c'è ancora **margine di perdita**: se tutti gli stop delle posizioni aperte venissero presi insieme a quello nuovo, non si supererebbe né la perdita giornaliera né quella totale.

**Se è passato molto tempo senza trade**, cioè 90 minuti senza ingressi, la soglia scende di 10 punti. Dopo una lunga attesa il bot "guarda la situazione" ed entra al primo segnale accettabile, invece di aspettare solo quelli perfetti.

### Passo 5: calcola il lotto e apre

Calcola quanto rischiare (paragrafo 4) e da lì il **numero di lotti**: il rischio in denaro diviso la distanza dello stop, usando il valore del tick del broker. In questo modo funziona con qualsiasi contratto e con qualsiasi taglia di conto. Controlla anche che il margine libero basti. Poi apre l'ordine **con lo stop loss già impostato sul server**.

### Passo 6: segue la posizione

Ogni secondo controlla le posizioni aperte: muove il trailing stop, chiude a tempo e chiude prima della pausa serale (paragrafo 5).

---

## 3. Il punteggio di qualità

Il punteggio è una somma di punti. Ogni punto vale circa **+0,01 R**: un segnale con punteggio 30 ha reso storicamente in media il 30% di R in più di un segnale medio, dove **R è il rischio del trade**. I punti sono stati stimati su 12 anni di Nasdaq al minuto, senza machine learning: per ogni fascia di ogni caratteristica, quanto rendevano in media i segnali di quella fascia.

| Caratteristica | Come assegna i punti |
|---|---|
| **Ora di New York** | Apertura 9:30-10:00 **+14**; 10:00-13:30 da +8 a +10; 13:30-15:00 da +3 a +6; sera 18:30-19:30 +8; notte 23:00-24:00 da −10 a −11; mattina europea 5:00-6:30 da **−13 a −17** |
| **Segnali concordi** | 1 segnale −1; 2 segnali +1; 3 segnali +8; 4 o 5 segnali **+30** |
| **Impulso 30 minuti** | Oltre 6 ATR **+17**; da 4 a 6 ATR +11; impulsi medi da 0 a −3 |
| **Impulso 15 minuti** | Oltre 4 ATR **+20**; da 3 a 4 ATR +4; da 1,5 a 2,5 ATR −2 |
| **Noise area** | Prezzo fuori dalla fascia nella direzione del trade **+13**; dentro la fascia −2 |
| **Trend a 15 minuti** | A favore +1; contro **−5** |
| **Trend giornaliero** | Neutro +4; a favore +1; contro −1 |
| **Distanza dal VWAP** | Prezzo dal lato sbagliato del VWAP **−6**; vicino −3; oltre 4 ATR a favore +1 |
| **Volatilità rispetto alla media del giorno** | Mercato più calmo del solito da −2 a −4; volatilità in aumento (da 1 a 1,7 volte) da +3 a **+5** |
| **Giorno della settimana** | Lunedì +1; martedì +3; mercoledì −5; giovedì +2; venerdì −1 |

Ogni segnale finisce nel registro e sul pannello con il dettaglio dei punti. Per esempio:

`ora +14 | segnali 3:+8 | imp30 -1 | imp15 -2 | trendG -1 | M15 +1 | noise +13 | VWAP +1 | volat +3 | giorno -5` → **punteggio 31**

---

## 4. Quanto rischia per ogni trade

Si parte dal **rischio base** (0,25% del capitale) e lo si adatta.

| Regola | Effetto |
|---|---|
| **Punteggio** | Sotto 20 → metà rischio; da 20 a 39 → rischio pieno; da 40 in su → **1,5 volte** |
| **Vincite di fila nella giornata** | +25% per ogni trade vincente consecutivo, fino al doppio. Così sfrutta le giornate in cui il mercato "gira" |
| **Conto in perdita** | Il rischio scende man mano che ci si avvicina alla perdita massima, fino a 0,4 volte |
| **Oro** | Sempre metà rischio |
| **Margine di perdita** | Il rischio non può mai superare lo spazio rimasto fino al limite giornaliero o al limite totale, contando gli stop delle posizioni già aperte. Se lo spazio è troppo poco, non entra |

Si calcola sempre sul **capitale iniziale**, senza interesse composto: dopo un guadagno il bot non aumenta la puntata per questo.

Con il rischio dinamico spento (pulsante "Rischio: FISSO") ogni trade rischia esattamente il rischio base.

---

## 5. Come esce dai trade

| Uscita | Quando |
|---|---|
| **Stop loss** | A **1,5 ATR** dal prezzo di ingresso, impostato subito sul server del broker. Se il trade è sbagliato, di solito esce in 10-20 minuti |
| **Trailing stop** | Quando il trade ha guadagnato **4 ATR**, lo stop si porta a **3 ATR dal massimo raggiunto** (dal minimo per le vendite) e lo segue. Il trade buono corre finché il movimento continua |
| **Tempo massimo** | Dopo **2 ore** il trade viene chiuso comunque |
| **Chiusura serale** | Alle **16:50 di New York** chiude tutto: niente posizioni durante la pausa del Nasdaq né nel weekend |
| **Perdita giornaliera** | Se l'equity del giorno arriva a −3%, chiude tutto (paragrafo 6) |

Non c'è un take profit fisso. Nella ricerca, i target fissi (per esempio rapporto 1:1 o 1:2) **eliminavano il vantaggio**: il guadagno di questa strategia viene da pochi movimenti grandi, che un target taglierebbe.

Il risultato tipico è questo:
- un terzo dei trade vince, in media **+2,2 volte il rischio**;
- due terzi perdono, in media **−1 volta il rischio**.

---

## 6. Le protezioni del conto

| Protezione | Predefinito | Cosa fa |
|---|---|---|
| **Posizioni massime** | 3 | Non apre se sul conto ci sono già 3 posizioni, comprese quelle manuali |
| **Perdita giornaliera** | 3% | Calcolata sull'equity rispetto all'inizio della giornata del server. Al −3% chiude tutto e si ferma fino al giorno dopo. La prop di solito concede il 5%: il margine copre slittamenti e gap |
| **Stop di fila** | 3 | Dopo 3 trade chiusi in perdita uno dopo l'altro si ferma per il resto della giornata. Le giornate storte non diventano disastri |
| **Protezione del profitto** | da +2%, metà | Se la giornata ha superato +2% e poi restituisce metà del guadagno massimo, smette di aprire per oggi |
| **Nessun limite al guadagno** | — | Le giornate buone corrono: nel backtest la migliore è arrivata a +12,7% |
| **Perdita massima** | 9% | Avvicinandosi riduce il rischio. Al −9% chiude tutto e si ferma **definitivamente** finché non premi "Reset blocco". La prop di solito concede il 10% |
| **Obiettivo** | 8% | Raggiunto l'obiettivo chiude tutto e si ferma definitivamente. Per la fase 2 si imposta 5%, sul conto finanziato 0 (nessun obiettivo) |
| **Giorni minimi di trading** | 4 | Se la prop richiede un minimo di giorni con trade, dopo l'obiettivo apre **un solo micro-trade al giorno** (lotto minimo, 2 minuti, rischio di circa 1 $) finché li raggiunge |
| **Una sola copia per conto** | — | Se trascini il bot su un secondo grafico dello stesso conto, il secondo si rifiuta di partire: niente trade doppi |
| **Memoria dei blocchi** | — | I fermi e il saldo di inizio giornata sono salvati subito: un riavvio di MT5 o un crash non li fa dimenticare |

---

## 7. Il filtro notizie

- **Fonte gratuita:** il **calendario economico integrato di MetaTrader 5**, aggiornato da MetaQuotes. Se il broker non lo fornisce, il bot usa il calendario di **ForexFactory** via internet (bisogna abilitare l'indirizzo in MT5, vedi l'installazione).
- **Quando aggiorna:** carica le notizie all'avvio e all'inizio di ogni giornata (mezzanotte del server), poi le aggiorna ogni ora. Il lunedì fa la scansione della settimana e la scrive nel registro.
- **Cosa blocca:** nessun nuovo ingresso **da 5 minuti prima a 5 minuti dopo** ogni notizia USA **rossa** (alto impatto) o **gialla** (medio impatto). Finita la finestra, il bot torna a operare normalmente.
- **Opzione per i conti finanziati** con regole sulle notizie: chiude le posizioni N minuti prima di una notizia rossa (impostazione `InpNewsCloseMin`, spenta di default).
- **Sul pannello:** la prossima notizia, il suo colore e quanto manca. Durante la finestra compare "pausa notizia".

---

## 8. L'oro

Sull'oro le regole del Nasdaq non funzionano altrettanto bene. Nei test ha retto solo un caso: gli **shock di volatilità**.

Il bot entra sull'oro solo quando:
- l'ATR a 5 minuti è almeno **2,3 volte** la sua media di un giorno;
- si è nella sessione di New York (08:00-15:30);
- almeno uno dei 5 segnali di accelerazione è attivo.

In quel caso rischia **metà** del normale e tiene **al massimo 1 posizione** sull'oro. Succede in media una volta ogni 5 giorni di borsa.

---

## 9. Due giornate vere, minuto per minuto

Queste sono due giornate del backtest del **codice vero** del bot (modalità Qualità, conto da 100.000 $). Gli orari sono di New York.

### Una giornata buona: 23 settembre 2026 (+3,6%)

| Ora | Cosa succede |
|---|---|
| 09:35 | Il Nasdaq scende con forza all'apertura. 3 segnali concordi, prezzo uscito sotto la noise area. **Punteggio 31** → **vende** 7,39 lotti a 30.629, stop a 30.663 (rischio 0,25%) |
| 09:45 | La discesa continua. **Punteggio 30** → seconda vendita, 6,88 lotti a 30.613 |
| 09:55 | Impulso a 30 minuti molto forte (+11 punti). **Punteggio 38** → terza vendita, 5,91 lotti a 30.554. Ora le posizioni sono 3: il massimo |
| 09:55-10:35 | Il Nasdaq scende di circa 200 punti. Superati i 4 ATR di guadagno, il trailing stop segue il prezzo a 3 ATR di distanza |
| 10:33-10:35 | Il rimbalzo fa scattare i trailing stop: **+6,3 R, +5,3 R e +2,9 R**, cioè **+3.612 $** in un'ora |
| 12:15 | Dopo 90 minuti senza ingressi la soglia scende a 20. **Punteggio 20** → quarta vendita, con rischio 0,44% (3 vincite di fila) |
| 14:15 | Sono passate 2 ore e il trade viene chiuso a tempo, quasi in pari (−16 $) |
| **Fine** | **+3.596 $ (+3,6%)** |

### Una giornata storta: 8 settembre 2026 (−1,0%)

| Ora | Cosa succede |
|---|---|
| 09:45 | Segnale fortissimo: 4 segnali concordi, impulsi a 15 e 30 minuti al massimo. **Punteggio 95** → vende con rischio 0,38% (1,5 volte, punteggio sopra 40) |
| 09:49 | Il Nasdaq si gira subito: **stop loss**, −375 $ |
| 09:55 e 10:00 | Altri due segnali di vendita (punteggi 50 e 34) → altre due vendite |
| 10:55 | Il rialzo continua: entrambi gli stop vengono presi, −625 $ |
| 10:56 | **3 stop loss di fila → il bot si ferma per il resto della giornata** |
| **Fine** | **−1.000 $ (−1,0%)**. Senza la protezione avrebbe continuato a vendere in un mercato che saliva |

Così è fatto il sistema: una giornata negativa costa in media lo 0,6% e quasi mai più del 2%, una giornata positiva rende in media l'1,8%.

---

## 10. Le tre modalità

Si sceglie con il pulsante **Modalità** del pannello o con l'impostazione `InpMode`.

| | **Qualità** (predefinita) | Bilanciata | Alta frequenza |
|---|---|---|---|
| Soglia del punteggio | 30 | 20 | 10 |
| Trade al giorno | 3,4 | 5,1 | 6,1 |
| Risultato medio per trade | +0,13 R | +0,09 R | +0,05 R |
| Risultato medio al giorno | +0,15% | +0,15% | +0,09% |
| Massimo calo (trading continuo, 2011-2026) | **21%** | 38% | 32% |
| Anni negativi su 16 | **0** | 1 | 2 |
| Challenge superate (entrambe le fasi, 182 prove) | **87%** | 80% | — |

**Qualità** è consigliata per le challenge: passa più spesso e ha cali più piccoli. **Bilanciata** fa più trade e in media ha guadagnato un po' di più sul conto finanziato, ma con più variabilità. **Alta frequenza** serve solo se vuoi molta azione: il vantaggio per trade è basso.

---

## 11. Risultati

Tutti i numeri vengono dal **codice vero dell'EA**, eseguito su 16 anni di dati al minuto (Nasdaq 2011-2026, oro 2016-2026) in un broker simulato. Le condizioni:
- spread realistici: circa 1,5 punti sul Nasdaq e 0,40 $ sull'oro;
- ingresso all'apertura della candela successiva;
- stop eseguiti sul massimo e minimo di ogni minuto.

![Backtest 2011-2026](FINANCIAL_BOT/report/backtest_2011_2026.png)

### Trading continuo, modalità Qualità (rischio base 0,25%)

| | |
|---|---|
| Trade vincenti | 35% (vincita media +2,2 R, perdita media −1 R) |
| Risultato medio | +0,15% al giorno, circa +42% l'anno dal 2014 |
| Anni negativi | **0 su 16**, compresi i 2011-2013 mai usati per costruire il sistema (+24%, +16%, +10%) |
| Giorni positivi | 33%: due giorni su tre chiudono in leggera perdita, il guadagno arriva dai giorni forti |
| Giorno migliore / peggiore | +12,7% / −2,6% |
| Massimo calo | 21% (somma dei giorni) |
| Mesi positivi | 120 su 190 |

### Challenge simulate

Una challenge da 100.000 $ fatta partire **all'inizio di ogni mese** dal 2011 al 2026 (182 partenze). Le condizioni:
- fase 1 con obiettivo 8%, fase 2 con obiettivo 5%;
- regole della prop controllate minuto per minuto: perdita giornaliera 5%, perdita totale 10%;
- poi 6 mesi di conto finanziato con payout mensile all'80%.

| Modalità Qualità | Tutto 2011-2026 | 2011-2013 (mai visti) | 2022-2026 |
|---|---|---|---|
| **Entrambe le fasi superate** | **87%** | 66% | 90% |
| Giorni di trading per la fase 1 (mediana) | 29 | 45 | 41 |
| Finanziati con almeno un payout in 6 mesi | 80% | 52% | 70% |
| Guadagno medio per challenge (payout − 500 $ di costo) | 7.987 $ | 2.901 $ | 4.278 $ |

- **Prova più severa:** con il punteggio ricostruito usando **solo i dati fino al 2021**, le challenge del 2022-2026 passano nell'**80%** dei casi. È la stima più vicina al futuro.
- **Nessuna violazione delle regole prop** in circa 650 challenge simulate. La perdita giornaliera peggiore è stata del 2,45% e il calo totale peggiore del 9,0%.
- **Possono esserci periodi deboli.** Comprando 10 challenge una al mese a partire dal 2011, ne sarebbero passate solo 2-3.

Tutti i dettagli sono nel [manuale](FINANCIAL_BOT/LEGGIMI.md) e nei file della cartella [`FINANCIAL_BOT/report`](FINANCIAL_BOT/report).

---

## 12. Installazione

1. **Scarica** il repository: pulsante verde **Code > Download ZIP**. La cartella che serve è [`FINANCIAL_BOT`](FINANCIAL_BOT).
2. **Copia l'EA.** In MetaTrader 5 apri `File > Apri cartella dati`, poi `MQL5 > Experts`, e copia lì `FINANCIAL_BOT.mq5`.
3. **Compila.** Premi F4 per aprire MetaEditor, apri il file e premi **F7**: in basso deve comparire `0 errors`.
4. **Abilita il trading automatico.** In `Strumenti > Opzioni > Expert Advisors` spunta **Consenti il trading algoritmico**.
   - Consigliato: spunta anche **Consenti WebRequest** e aggiungi `https://nfs.faireconomy.media` (calendario notizie di riserva).
5. **Controlla lo storico.** In `Strumenti > Opzioni > Grafici` metti **Barre max nel grafico** ad almeno 10.000.
6. **Avvia il bot.** Apri **un** grafico qualsiasi (es. US100 a 5 minuti) e trascinaci sopra `FINANCIAL_BOT`. Spunta "Consenti trading algoritmico" e premi OK. Accendi il pulsante **Algo Trading** in alto.
7. **Controlla il pannello:** stato ATTIVO, simboli trovati, capitale corretto e prossima notizia.
8. **Tieni MT5 acceso dal lunedì al venerdì**, meglio su una VPS (10-20 €/mese).

**Per le challenge:**
- fase 2: imposta `Obiettivo % = 5`;
- conto finanziato: imposta `Obiettivo % = 0`;
- **scagliona** le challenge invece di farle partire tutte lo stesso giorno: farebbero gli stessi identici trade;
- prima di usarlo su una challenge, provalo 1-2 settimane su un **conto demo**.

---

## 13. Il pannello

Il pannello in alto a sinistra mostra tutto e si comanda con il mouse.

| Riga / pulsante | Cosa mostra o cosa fa |
|---|---|
| **Stato** | ATTIVO, IN PAUSA, pausa notizia, FERMO PER OGGI (con il motivo) oppure FERMO definitivo (obiettivo raggiunto, perdita massima o margine esaurito) |
| **Capitale ed equity** | Capitale di riferimento, equity, risultato totale e di oggi in %, costo della challenge |
| **Limiti** | Livelli in denaro dell'obiettivo, dello stop totale e dello stop di oggi |
| **Oggi** | Trade fatti, stop di fila (x/3), vincenti di fila, posizioni aperte (x/3), rischio del prossimo trade |
| **Notizie** | Prossima notizia rossa o gialla, quanto manca e la fonte |
| **Campi modificabili** | Capitale, costo della challenge, obiettivo %, perdita max %, perdita giorno %, rischio base %, stop dopo N stop loss. Si scrivono e si salvano con **Salva impostazioni** |
| **Pulsanti** | Modalità, rischio dinamico o fisso, Nasdaq on/off, oro on/off, filtro notizie on/off, **PAUSA**, **CHIUDI TUTTO**, Reset blocco |
| **Ultimo segnale** | Per Nasdaq e oro: direzione, punteggio, soglia e dettaglio dei punti |

Ogni evento (segnali scartati e bloccati con il motivo, ingressi, trailing, uscite, fermi, riepilogo di fine giornata) viene scritto in `MQL5/Files/FINANCIAL_BOT_log.csv`, che si apre con Excel.

---

## 14. Tutte le impostazioni

| Impostazione | Predefinito | Significato |
|---|---|---|
| `InpCapital` | 0 | Capitale iniziale. 0 = automatico (primo deposito del conto) |
| `InpChallengeCost` | 0 | Costo della challenge, solo informativo (sul pannello) |
| `InpTargetPct` | 8 | Obiettivo %: raggiunto chiude tutto e si ferma (0 = nessuno) |
| `InpMaxLossPct` | 9 | Perdita massima totale %: raggiunta chiude tutto e si ferma |
| `InpDailyLossPct` | 3 | Perdita massima giornaliera % (sull'equity) |
| `InpRiskPct` | 0,25 | Rischio base per trade, in % del capitale |
| `InpMaxLossStreak` | 3 | Fermo per la giornata dopo N stop loss di fila (0 = mai) |
| `InpMinTradingDays` | 4 | Giorni minimi di trading della prop (0 = nessuno) |
| `InpMode` | 0 | 0 = Qualità, 1 = Bilanciata, 2 = Alta frequenza |
| `InpTradeNasdaq` / `InpTradeGold` | sì / sì | Opera il Nasdaq / l'oro |
| `InpDynamicRisk` | sì | Rischio dinamico (punteggio, vincite di fila, riduzione in perdita) |
| `InpIdleMinutes` / `InpIdleRelax` | 90 / 10 | Dopo 90 minuti senza ingressi la soglia scende di 10 punti |
| `InpLockStartPct` / `InpLockGivePct` | 2 / 50 | Protezione del profitto: da +2% nella giornata, stop se restituisce il 50% |
| `InpMaxPositions` | 3 | Posizioni aperte al massimo sul conto (tutte) |
| `InpMaxNasdaq` / `InpMaxGold` | 3 / 1 | Posizioni al massimo per simbolo |
| `InpNewsFilter` | sì | Filtro notizie acceso |
| `InpNewsBeforeMin` / `InpNewsAfterMin` | 5 / 5 | Minuti senza ingressi prima e dopo la notizia |
| `InpNewsMedium` | sì | Anche le notizie gialle, non solo le rosse |
| `InpNewsCurrencies` | USD | Valute considerate (separate da virgola) |
| `InpNewsWebFallback` | sì | Usa ForexFactory se il calendario di MT5 non risponde |
| `InpNewsCloseMin` | 0 | Chiude le posizioni N minuti prima delle notizie rosse (0 = no) |
| `InpNasdaqSymbol` / `InpGoldSymbol` | vuoto | Nome del simbolo. Vuoto = riconoscimento automatico (NAS100, US100.cash, USTEC, XAUUSD, GOLD…) |
| `InpMagic` | 770100 | Numero magico (Nasdaq = 770100, oro = 770101) |
| `InpMaxSpreadAtr` | 0,25 | Salta il trade se lo spread supera questa frazione dell'ATR |
| `InpServerDST` | 1 | Ora legale del server: 1 = come gli USA (FTMO e quasi tutti), 2 = Europa, 0 = nessuna |
| `InpTesterUTCOffset` | 2 | Solo per il Tester: ore del server rispetto a UTC d'inverno |
| `InpShowPanel` / `InpLogCsv` | sì / sì | Mostra il pannello / scrive il registro |

---

## 15. Cosa NON fa

- **Non fa 20 trade al giorno.** Più trade vuol dire meno vantaggio per trade: oltre 5-6 trade al giorno spread e commissioni si mangiano il guadagno.
- **Non usa martingala, griglie o medie** sulle posizioni in perdita: ogni trade ha il suo stop dall'inizio.
- **Non tiene posizioni** nella pausa serale del Nasdaq né nel weekend.
- **Non usa machine learning:** tutte le regole sono fisse e leggibili nel codice.
- **Non garantisce guadagni.** Ci sono stati periodi deboli (2011-2012) e possono tornare.

---

## 16. Domande frequenti

**Perché la maggior parte dei giorni chiude in perdita?**
Perché è un sistema "a trend": prende tante piccole perdite veloci e pochi guadagni grandi. Nel backtest due giorni su tre sono in leggera perdita (in media −0,6%), mentre i giorni positivi rendono in media +1,8%. Non spegnerlo dopo qualche giorno negativo.

**Per ore non apre niente: è normale?**
Sì. Entra solo quando c'è un'accelerazione con un buon punteggio, soprattutto all'apertura di New York (15:30 ora italiana). Sul pannello vedi l'ultimo segnale e il suo punteggio.

**Posso usarlo su più conti?**
Sì, una copia per conto. Ma se le challenge partono lo stesso giorno faranno gli stessi trade: conviene scaglionarle.

**Funziona con il mio broker?**
Riconosce da solo i nomi più comuni dei simboli. Se non li trova, scrivi il nome esatto in `InpNasdaqSymbol` / `InpGoldSymbol`. Il fuso orario del server lo misura da solo.

**Come lo provo nel Tester di MT5?**
Copia `FINANCIAL_BOT/Common_Files/FINANCIAL_BOT_news_history.csv` nella cartella comune dei terminali (`...\MetaQuotes\Terminal\Common\Files`), poi lancia il Tester sul Nasdaq a 5 minuti. Le istruzioni complete sono nel [manuale](FINANCIAL_BOT/LEGGIMI.md).

**Come è stato verificato il codice?**
In tre modi:
- il codice MQL5 è stato tradotto in C++ e compilato in modalità rigorosa (0 errori, 0 avvisi);
- è stato eseguito in un broker simulato su 16 anni di dati, con controlli di memoria;
- i segnali sono stati confrontati con quelli della ricerca: 423.733 su 423.739 identici.

La compilazione finale va fatta in MetaEditor (F7). Gli strumenti di verifica sono in [`FINANCIAL_BOT/verifica`](FINANCIAL_BOT/verifica).

---

## 17. Contenuto del repository

| Percorso | Contenuto |
|---|---|
| [`FINANCIAL_BOT/FINANCIAL_BOT.mq5`](FINANCIAL_BOT/FINANCIAL_BOT.mq5) | L'Expert Advisor |
| [`FINANCIAL_BOT/LEGGIMI.md`](FINANCIAL_BOT/LEGGIMI.md) | Il manuale d'uso completo |
| [`FINANCIAL_BOT/Common_Files/`](FINANCIAL_BOT/Common_Files) | Le notizie storiche 2010-2026 per il Tester di MT5 |
| [`FINANCIAL_BOT/report/`](FINANCIAL_BOT/report) | Grafici e tabelle: backtest per anno, modalità, tutte le challenge simulate |
| [`FINANCIAL_BOT/verifica/`](FINANCIAL_BOT/verifica) | Traduttore MQL5 → C++, broker simulato e test |
| [`ricerca/`](ricerca) | Gli script Python della ricerca e le tabelle del punteggio |

---

> **Avvertenza.** FINANCIAL BOT è stato costruito con cura e verificato a fondo sui dati storici, ma **i risultati passati non garantiscono quelli futuri**. Il trading comporta il rischio di perdere denaro. Inizia da un conto demo e usa solo denaro che puoi permetterti di perdere, come il costo delle challenge.
