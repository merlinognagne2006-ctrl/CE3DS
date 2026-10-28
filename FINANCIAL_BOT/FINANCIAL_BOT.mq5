//+------------------------------------------------------------------+
//| FINANCIAL_BOT.mq5 - Nasdaq & Oro: momentum intraday con punteggio|
//|                                                                  |
//| UN SOLO EA, su UN SOLO grafico (qualsiasi simbolo/timeframe).    |
//| Opera NAS100 (motore principale) e XAUUSD (solo shock di         |
//| volatilita') con le regole trovate e validate nella ricerca      |
//| 2014-2026 (vedi README). Nessun machine learning: tutto e'       |
//| calcolato in modo deterministico.                                |
//|                                                                  |
//| Ingresso: alla chiusura di ogni candela M5 il sistema cerca      |
//| un'accelerazione (5 segnali: impulso 15', impulso 30', distanza  |
//| dal VWAP col trend H1, pullback nella giornata di trend, uscita  |
//| dalla "noise area"). Se i segnali concordano calcola un          |
//| PUNTEGGIO (fascia oraria, n. di segnali concordi, forza, trend   |
//| M15 e giornaliero, noise area, VWAP, volatilita', giorno).       |
//| Entra solo se il punteggio supera la soglia della modalita'.     |
//| Uscita: stop 1.5 ATR, nessun target (si lascia correre),         |
//| trailing 3 ATR dopo +4 ATR, chiusura dopo 120 minuti e sempre    |
//| prima delle 16:50 di New York.                                   |
//+------------------------------------------------------------------+
#property copyright "FINANCIAL BOT"
#property version   "1.10"
#property description "Nasdaq & Oro momentum intraday - punteggio deterministico, regole prop, filtro notizie"

#include <Trade/Trade.mqh>

//=== INPUT ==========================================================
input group "=== CONTO (modificabili anche dal pannello) ==="
input double InpCapital        = 0;      // Capitale iniziale (0 = automatico: primo deposito del conto)
input double InpChallengeCost  = 0;      // Costo della challenge (solo informativo, nel pannello)
input double InpTargetPct      = 8.0;    // Obiettivo %: raggiunto chiude tutto e si ferma (0 = nessuno)
input double InpMaxLossPct     = 9.0;    // Perdita massima totale % (lasciare margine sotto il limite prop)
input double InpDailyLossPct   = 3.0;    // Perdita massima giornaliera % (equity, include le posizioni aperte)
input double InpRiskPct        = 0.25;   // Rischio base per trade % del capitale
input int    InpMaxLossStreak  = 3;      // Stop per oggi dopo N stop loss di fila (0 = disattivato)
input int    InpMinTradingDays = 4;      // Giorni minimi di trading della prop: dopo l'obiettivo 1 micro-trade al giorno (0 = no)

input group "=== STRATEGIA ==="
input int    InpMode           = 0;      // Modalita': 0 = Qualita' (consigliata per le challenge), 1 = Bilanciata, 2 = Alta frequenza
input bool   InpTradeNasdaq    = true;   // Opera il Nasdaq (motore principale)
input bool   InpTradeGold      = true;   // Opera l'oro (solo shock di volatilita', rischio dimezzato)
input bool   InpDynamicRisk    = true;   // Rischio dinamico (punteggio + serie vincente + riduzione in perdita)
input int    InpIdleMinutes    = 90;     // Dopo N minuti senza ingressi la soglia scende (0 = no)
input int    InpIdleRelax      = 10;     // Di quanti punti scende la soglia
input double InpLockStartPct   = 2.0;    // Protezione profitto: da +X% nella giornata...
input double InpLockGivePct    = 50.0;   // ...stop ingressi se restituisce piu' del Y% del massimo
input int    InpMaxPositions   = 3;      // Posizioni aperte al massimo sul conto (tutte, anche manuali)
input int    InpMaxNasdaq      = 3;      // Posizioni Nasdaq al massimo
input int    InpMaxGold        = 1;      // Posizioni oro al massimo

input group "=== NOTIZIE (calendario economico MT5, gratuito) ==="
input bool   InpNewsFilter     = true;   // Blocca nuovi ingressi vicino alle notizie
input int    InpNewsBeforeMin  = 5;      // Minuti prima della notizia
input int    InpNewsAfterMin   = 5;      // Minuti dopo la notizia
input bool   InpNewsMedium     = true;   // Anche le notizie gialle (impatto medio), non solo le rosse
input string InpNewsCurrencies = "USD";  // Valute considerate (separate da virgola)
input bool   InpNewsWebFallback= true;   // Se il calendario MT5 non risponde usa ForexFactory (WebRequest)
input int    InpNewsCloseMin   = 0;      // Chiude le posizioni N minuti prima delle notizie ROSSE (0 = no; per conti con regole sulle notizie)

input group "=== SIMBOLI (vuoto = riconoscimento automatico) ==="
input string InpNasdaqSymbol   = "";     // Es. NAS100, US100.cash, USTEC, NDX100
input string InpGoldSymbol     = "";     // Es. XAUUSD, GOLD

input group "=== AVANZATE ==="
input int    InpMagic          = 770100; // Magic number (Nasdaq = magic, oro = magic + 1)
input double InpMaxSpreadAtr   = 0.25;   // Salta il trade se lo spread supera questa frazione dell'ATR M5
input int    InpServerDST      = 1;      // Ora legale del server: 1 = come USA (FTMO e quasi tutti), 2 = Europa, 0 = nessuna
input int    InpTesterUTCOffset= 2;      // Solo Strategy Tester: ore server - UTC d'inverno (FTMO e simili = 2)
input bool   InpShowPanel      = true;   // Mostra il pannello
input bool   InpLogCsv         = true;   // Registra segnali e trade in MQL5/Files/FINANCIAL_BOT_log.csv

//=== COSTANTI DELLA STRATEGIA (dalla ricerca, non modificare) ======
#define SL_ATR        1.5
#define TRAIL_ATR     3.0
#define TRAIL_ON_ATR  4.0
#define HOLD_MIN      120
#define CLOSE_NY_MIN  1010     // 16:50 New York: chiusura forzata
#define NOENTRY_A     960      // 16:00 NY ...
#define NOENTRY_B     1110     // ... 18:30 NY: nessun ingresso (chiusura/riapertura giornaliera)
#define FRIDAY_LAST   930      // venerdi' nessun ingresso dopo le 15:30 NY
#define GOLD_WIN_A    480      // oro: finestra 08:00 ...
#define GOLD_WIN_B    930      // ... 15:30 NY
#define GOLD_SHOCK    2.3      // oro: ATR14 / ATR288 minimo (shock di volatilita')
#define NBARS         6000     // candele M5 lette (circa 20 giorni)
#define MIN_BARS      4000     // sotto questo numero di candele M5 non si opera
#define MAX_LATE_SEC  60       // il segnale vale solo nel primo minuto della nuova candela (come nella ricerca)

//=== TABELLA DEI PUNTI (stimata su Nasdaq 2011-2026, research/score_build.py) ===
// fascia oraria di New York (minuto di inizio della mezz'ora) -> punti
int BucketPts(int m)
{
   static const int key[] = {0,30,60,90,120,150,180,210,240,270,300,330,360,390,420,450,480,510,540,570,600,630,660,690,720,
                             750,780,810,840,870,900,930,1080,1110,1140,1170,1200,1230,1260,1290,1320,1350,1380,1410};
   static const int pts[] = {-9,-6,1,-1,0,-2,-5,2,-1,-6,-13,-17,-17,-8,5,1,-4,-6,0,14,8,9,9,8,8,
                             9,10,6,3,6,-1,0,0,8,8,0,3,0,-4,2,-4,-8,-11,-10};
   int b = (m / 30) * 30;
   for(int i = 0; i < ArraySize(key); i++) if(key[i] == b) return pts[i];
   return 0;
}
// intervalli (a,b] come pandas.cut: restituisce l'indice o -1 se fuori
int BinIndex(const double &edges[], double x)
{
   for(int i = 0; i < ArraySize(edges) - 1; i++) if(x > edges[i] && x <= edges[i + 1]) return i;
   return -1;
}
int PtsFrom(const double &edges[], const int &pts[], double x)
{
   int k = BinIndex(edges, x);
   return (k < 0) ? 0 : pts[k];
}
double E_MOM6[] = {-99, 1, 2.5, 3, 4, 6, 99};       int P_MOM6[] = {0, -1, -3, 0, 11, 17};
double E_MOM3[] = {-99, 1, 1.5, 2.5, 3, 4, 99};     int P_MOM3[] = {0, 0, -2, 0, 4, 20};
double E_VWD[]  = {-99, 0, 2, 3, 4, 99};            int P_VWD[]  = {-6, -3, 0, -1, 1};
double E_ATRR[] = {0, 0.7, 1.0, 1.3, 1.7, 2.5, 99}; int P_ATRR[] = {-4, -2, 3, 5, 3, 2};
int NtrigPts(int n) { if(n >= 4) return 30; if(n == 3) return 8; if(n == 2) return 1; if(n == 1) return -1; return 0; }
int TrD1Pts(int v)  { return v > 0 ? 1 : (v < 0 ? -1 : 4); }
int TrM15Pts(int v) { return v > 0 ? 1 : (v < 0 ? -5 : 0); }
int NoisePts(int v) { return v > 0 ? 13 : (v < 0 ? 0 : -2); }
int DowPts(int dow) { if(dow == 0) return 1; if(dow == 1) return 3; if(dow == 2) return -5; if(dow == 3) return 2; if(dow == 4) return -1; return 0; }

//=== STATO ==========================================================
struct SymState
{
   string   name;
   bool     ok;
   bool     gold;
   int      hEmaH1;     // EMA50 H1
   int      hEmaM15;    // EMA20 M15
   datetime lastBar;    // ultima candela M5 elaborata
   datetime lastEntryBar;
   int      bars;       // candele M5 disponibili all'ultimo calcolo
   // ultimo segnale (per il pannello)
   int      sigDir;
   int      sigScore;
   string   sigInfo;
   datetime sigTime;
};

SymState g_sym[2];        // 0 = Nasdaq, 1 = oro
CTrade   g_trade;
string   g_prefix;        // prefisso delle variabili globali
int      g_baseOff = 0;   // server - UTC senza ora legale, in secondi
double   g_capAuto = 0;   // capitale rilevato automaticamente
bool     g_netting = false;
datetime g_dayStart = 0;  // inizio del giorno server corrente
double   g_dayStartBal = 0;
bool     g_haltDay = false;
string   g_haltReason = "";
bool     g_halted = false;  // fermo definitivo (target o perdita massima) fino al reset
bool     g_haltLogged = false;
uint     g_lastDraw = 0;
int      g_tradeDays = 0;   // giorni con almeno un ingresso sul conto
datetime g_tradeDaysAt = 0;

// notizie (ordinate per orario UTC)
datetime g_newsTime[];
int      g_newsImp[];     // 3 = alta (rossa), 2 = media (gialla)
string   g_newsName[];
datetime g_newsLoaded = 0;
datetime g_newsWeek = 0;
bool     g_newsCsvDone = false;
string   g_newsSource = "nessuna";

//=== CONFIGURAZIONE (input oppure valori salvati dal pannello) ======
string GVN(string k) { return g_prefix + k; }
double Cfg(string k, double def) { return GlobalVariableCheck(GVN(k)) ? GlobalVariableGet(GVN(k)) : def; }
double Capital()
{
   double c = Cfg("CAP", InpCapital);
   if(c <= 0) c = g_capAuto;
   return c > 0 ? c : MathMax(AccountInfoDouble(ACCOUNT_BALANCE), 1.0);
}
double ChallengeCost() { return Cfg("FEE", InpChallengeCost); }
double TargetPct()     { return Cfg("TGT", InpTargetPct); }
double MaxLossPct()    { return Cfg("MXL", InpMaxLossPct); }
double DailyLossPct()  { return Cfg("DLY", InpDailyLossPct); }
double RiskPct()       { return Cfg("RSK", InpRiskPct); }
int    LossStreakMax() { return (int)Cfg("LSM", InpMaxLossStreak); }
int    Mode()          { return (int)Cfg("MOD", InpMode); }
bool   UseNasdaq()     { return Cfg("NAS", InpTradeNasdaq ? 1 : 0) != 0; }
bool   UseGold()       { return Cfg("XAU", InpTradeGold ? 1 : 0) != 0; }
bool   DynRisk()       { return Cfg("DYN", InpDynamicRisk ? 1 : 0) != 0; }
bool   NewsOn()        { return Cfg("NWS", InpNewsFilter ? 1 : 0) != 0; }
bool   Paused()        { return Cfg("PAU", 0) != 0; }
int    Threshold()     { int m = Mode(); return m == 0 ? 30 : (m == 2 ? 10 : 20); }
string ModeName()      { int m = Mode(); return m == 0 ? "Qualita'" : (m == 2 ? "Alta frequenza" : "Bilanciata"); }

// se l'utente cambia un input nella finestra delle proprieta', l'input vince sul valore salvato dal pannello
void SyncInput(string k, double v)
{
   string ik = GVN("IN_" + k);
   if(!GlobalVariableCheck(ik) || GlobalVariableGet(ik) != v) { GlobalVariableDel(GVN(k)); GlobalVariableSet(ik, v); }
}

//=== TEMPO ==========================================================
int      YearOf(datetime t) { MqlDateTime d; TimeToStruct(t, d); return d.year; }
datetime DateOf(int y, int m, int d) { MqlDateTime s; ZeroMemory(s); s.year = y; s.mon = m; s.day = d; return StructToTime(s); }
// n-esima domenica del mese (n = 1..4) oppure l'ultima (n = 0), alle 00:00
datetime SundayOf(int y, int m, int n)
{
   MqlDateTime w;
   if(n == 0)
   {
      datetime last = (m == 12 ? DateOf(y + 1, 1, 1) : DateOf(y, m + 1, 1)) - 86400;
      TimeToStruct(last, w);
      return last - w.day_of_week * 86400;
   }
   datetime first = DateOf(y, m, 1);
   TimeToStruct(first, w);
   return first + ((7 - w.day_of_week) % 7 + 7 * (n - 1)) * 86400;
}
// ora legale USA: dalla 2a domenica di marzo 07:00 UTC alla 1a domenica di novembre 06:00 UTC
bool IsUSDST(datetime utc)
{
   static datetime y0 = 1, y1 = 0, a = 0, b = 0;   // anno in memoria [y0, y1) e periodo di ora legale [a, b)
   if(utc < y0 || utc >= y1)
   {
      int y = YearOf(utc);
      y0 = DateOf(y, 1, 1); y1 = DateOf(y + 1, 1, 1);
      a = SundayOf(y, 3, 2) + 7 * 3600; b = SundayOf(y, 11, 1) + 6 * 3600;
   }
   return utc >= a && utc < b;
}
// ora legale europea: dall'ultima domenica di marzo all'ultima di ottobre, 01:00 UTC
bool IsEUDST(datetime utc)
{
   static datetime y0 = 1, y1 = 0, a = 0, b = 0;
   if(utc < y0 || utc >= y1)
   {
      int y = YearOf(utc);
      y0 = DateOf(y, 1, 1); y1 = DateOf(y + 1, 1, 1);
      a = SundayOf(y, 3, 0) + 3600; b = SundayOf(y, 10, 0) + 3600;
   }
   return utc >= a && utc < b;
}
int DstShift(datetime utc)
{
   if(InpServerDST == 1) return IsUSDST(utc) ? 3600 : 0;
   if(InpServerDST == 2) return IsEUDST(utc) ? 3600 : 0;
   return 0;
}
// dal vivo la differenza server - UTC e' misurata; nel tester viene dagli input
void UpdateOffset()
{
   if(MQLInfoInteger(MQL_TESTER)) { g_baseOff = InpTesterUTCOffset * 3600; return; }
   datetime gmt = TimeGMT();
   long diff = (long)TimeTradeServer() - (long)gmt;
   g_baseOff = (int)(MathRound(diff / 1800.0) * 1800) - DstShift(gmt);
}
// ogni orario viene convertito con l'ora legale della SUA data (lo storico attraversa i cambi d'ora)
datetime ToUTC(datetime srv)   { datetime u = (datetime)((long)srv - g_baseOff); return (datetime)((long)u - DstShift(u)); }
datetime UTCToNY(datetime utc) { return (datetime)((long)utc - (IsUSDST(utc) ? 4 : 5) * 3600); }
datetime SrvToNY(datetime srv) { return UTCToNY(ToUTC(srv)); }
int      MinOfDay(datetime t) { return (int)(((long)t % 86400) / 60); }
long     DayNum(datetime t) { return (long)t / 86400; }
long     TDay(datetime ny) { return DayNum((datetime)((long)ny + 6 * 3600)); }   // giorno di trading dalle 18:00 NY
int      DowOf(long daynum) { return (int)((daynum + 3) % 7); }                    // 0 = lunedi' (1970-01-01 era giovedi')
double   ServerUTCHours() { datetime now = TimeTradeServer(); return ((long)now - (long)ToUTC(now)) / 3600.0; }

//=== UTILITA' ======================================================
void Log(string what)
{
   if(!InpLogCsv) return;
   int h = FileOpen("FINANCIAL_BOT_log.csv", FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ';');
   if(h == INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);
   FileWrite(h, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), what);
   FileClose(h);
}

bool IsOurMagic(long m) { return m == InpMagic || m == InpMagic + 1; }   // +0 Nasdaq, +1 oro

int CountPositions(int which)  // -1 = tutte sul conto, 0 = nostre Nasdaq, 1 = nostre oro
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(which < 0) { n++; continue; }
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic + which && PositionGetString(POSITION_SYMBOL) == g_sym[which].name) n++;
   }
   return n;
}

void CloseAll(string why)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && IsOurMagic(PositionGetInteger(POSITION_MAGIC))) g_trade.PositionClose(t);
   }
   Log("CHIUDI_TUTTO;" + why);
}

string Money(double v) { return DoubleToString(v, 0); }

//=== SIMBOLI ========================================================
bool Tradeable(string s) { return SymbolInfoInteger(s, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_DISABLED; }

string FindSymbol(string preferred, const string &cands[])
{
   if(preferred != "" && SymbolSelect(preferred, true)) return preferred;
   int total = SymbolsTotal(false);
   // 1) nome esatto  2) nome che inizia con il candidato (suffissi del broker: .cash, .r, m, .pro, ...)
   for(int c = 0; c < ArraySize(cands); c++)
      for(int i = 0; i < total; i++)
      {
         string s = SymbolName(i, false);
         if(s == cands[c] && Tradeable(s)) { SymbolSelect(s, true); return s; }
      }
   for(int c = 0; c < ArraySize(cands); c++)
      for(int i = 0; i < total; i++)
      {
         string s = SymbolName(i, false);
         if(StringFind(s, cands[c]) == 0 && StringLen(s) <= StringLen(cands[c]) + 6 && Tradeable(s)) { SymbolSelect(s, true); return s; }
      }
   return "";
}

bool InitSymbol(int k, string name, bool gold)
{
   g_sym[k].name = name; g_sym[k].gold = gold; g_sym[k].ok = false;
   g_sym[k].lastBar = 0; g_sym[k].lastEntryBar = 0; g_sym[k].bars = 0;
   g_sym[k].sigDir = 0; g_sym[k].sigScore = 0; g_sym[k].sigInfo = ""; g_sym[k].sigTime = 0;
   g_sym[k].hEmaH1 = INVALID_HANDLE; g_sym[k].hEmaM15 = INVALID_HANDLE;
   if(name == "") return false;
   g_sym[k].hEmaH1 = iMA(name, PERIOD_H1, 50, 0, MODE_EMA, PRICE_CLOSE);
   g_sym[k].hEmaM15 = iMA(name, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   g_sym[k].ok = (g_sym[k].hEmaH1 != INVALID_HANDLE && g_sym[k].hEmaM15 != INVALID_HANDLE);
   g_sym[k].lastBar = iTime(name, PERIOD_M5, 0);        // la candela gia' in corso all'avvio non viene usata
   return g_sym[k].ok;
}

//=== INDICATORI (calcolati sulle candele M5 chiuse, come nella ricerca) ===
struct Feat
{
   bool   valid;
   datetime barTime;  // apertura della candela segnale
   double c, atr, atrSlow;
   double ret3, ret6, vwd;
   int    trH1, trM15, trD1, noise, noisePrev;
   int    nym;       // minuto NY di apertura della candela segnale
   int    dow;       // giorno di trading (0 = lunedi')
   bool   pullUp, pullDn;
   double spreadAtr;
};

// ATR di Wilder su tutto l'array (dal piu' vecchio al piu' recente)
void WilderATR(const MqlRates &r[], int n, int period, double &out[])
{
   ArrayResize(out, n);
   double a = r[0].high - r[0].low;
   out[0] = a;
   for(int i = 1; i < n; i++)
   {
      double pc = r[i - 1].close;
      double tr = MathMax(r[i].high - r[i].low, MathMax(MathAbs(r[i].high - pc), MathAbs(r[i].low - pc)));
      a += (tr - a) / period;
      out[i] = a;
   }
}

// stato "noise area" (Zarattini, Aziz, Barbon) per la candela i (0 = fuori sessione o dati insufficienti)
int NoiseState(const MqlRates &r[], const datetime &ny[], int i, int lookback = 14)
{
   int m = MinOfDay(ny[i]);
   if(m < 570 || m >= 960) return 0;
   long day = DayNum(ny[i]);
   // apertura di oggi: prima candela della sessione 9:30-16:00 di oggi
   double op = 0;
   for(int j = i; j >= 0; j--)
   {
      long dj = DayNum(ny[j]); int mj = MinOfDay(ny[j]);
      if(dj != day) break;
      if(mj >= 570 && mj < 960) op = r[j].open;
   }
   if(op <= 0) return 0;
   // giorni precedenti con sessione: chiusura alla stessa candela, apertura, ultima chiusura
   double moveSum = 0; int found = 0; double prevClose = 0;
   long curDay = day; double dOpen = 0, dAt = 0, dLast = 0; bool haveDay = false;
   for(int j = i - 1; j >= 0 && found <= lookback; j--)
   {
      long dj = DayNum(ny[j]); int mj = MinOfDay(ny[j]);
      if(dj == day || mj < 570 || mj >= 960) continue;
      if(!haveDay || dj != curDay)
      {
         if(haveDay)
         {   // chiude il giorno precedente raccolto
            if(found == 0) prevClose = dLast;
            if(dAt <= 0 || dOpen <= 0) return 0;      // manca la stessa candela in uno dei giorni: niente banda
            moveSum += MathAbs(dAt / dOpen - 1.0); found++;
            if(found == lookback) break;
         }
         curDay = dj; haveDay = true; dOpen = 0; dAt = 0; dLast = r[j].close;
      }
      dOpen = r[j].open;                                // l'ultima assegnazione e' la prima candela del giorno
      if(mj == m) dAt = r[j].close;
   }
   if(found < lookback) return 0;                       // storico insufficiente
   if(prevClose <= 0) return 0;
   double sig = moveSum / lookback;
   double up = MathMax(op, prevClose) * (1 + sig), dn = MathMin(op, prevClose) * (1 - sig);
   double c = r[i].close;
   return c > up ? 1 : (c < dn ? -1 : 0);
}

int TrendD1(string sym)
{
   MqlRates h[]; ArraySetAsSeries(h, false);
   int n = CopyRates(sym, PERIOD_H1, 1, 24 * 40, h);
   if(n < 24 * 22) return 0;
   double dc[]; long last = -1; int nd = 0;
   ArrayResize(dc, 0, 64);
   for(int i = 0; i < n; i++)
   {
      long td = TDay(SrvToNY(h[i].time));
      if(td != last) { ArrayResize(dc, nd + 1, 64); nd++; last = td; }
      dc[nd - 1] = h[i].close;
   }
   // oggi non e' concluso: si usa lo stato di ieri (come nella ricerca: .shift(1))
   if(last == TDay(SrvToNY(TimeTradeServer()))) nd--;
   if(nd < 20) return 0;
   double s = 0; for(int k = nd - 20; k < nd; k++) s += dc[k];
   double sma = s / 20.0, y = dc[nd - 1];
   return y > sma ? 1 : (y < sma ? -1 : 0);
}

bool ComputeFeatures(int k, Feat &f)
{
   f.valid = false;
   string sym = g_sym[k].name;
   MqlRates r[]; ArraySetAsSeries(r, false);
   int n = CopyRates(sym, PERIOD_M5, 1, NBARS, r);      // dal piu' vecchio; r[n-1] = candela appena chiusa
   g_sym[k].bars = n;
   if(n < MIN_BARS) return false;
   double atr[], atrS[];
   WilderATR(r, n, 14, atr); WilderATR(r, n, 288, atrS);
   datetime ny[]; ArrayResize(ny, n);
   for(int i = 0; i < n; i++) ny[i] = SrvToNY(r[i].time);
   int i = n - 1;
   f.barTime = r[i].time;
   f.c = r[i].close; f.atr = atr[i]; f.atrSlow = atrS[i];
   if(f.atr <= 0 || f.atrSlow <= 0) return false;
   f.ret3 = (r[i].close - r[i - 3].close) / f.atr;
   f.ret6 = (r[i].close - r[i - 6].close) / f.atr;
   // VWAP del giorno di trading (Nasdaq: peso uguale per candela; oro: tick volume, come nella ricerca)
   long td = TDay(ny[i]); double sum = 0, wsum = 0;
   for(int j = i; j >= 0 && TDay(ny[j]) == td; j--)
   {
      double w = g_sym[k].gold ? MathMax((double)r[j].tick_volume, 1.0) : 1.0;
      sum += (r[j].high + r[j].low + r[j].close) / 3.0 * w; wsum += w;
   }
   if(wsum <= 0) return false;
   f.vwd = (r[i].close - sum / wsum) / f.atr;
   // EMA20 M5
   double e = r[0].close, ePrev = e, k20 = 2.0 / 21.0;
   for(int j = 1; j < n; j++) { ePrev = e; e = r[j].close * k20 + e * (1 - k20); }
   // trend H1 e M15 (candele chiuse)
   double eh[1], em[3];
   if(CopyBuffer(g_sym[k].hEmaH1, 0, 1, 1, eh) < 1) return false;
   if(CopyBuffer(g_sym[k].hEmaM15, 0, 1, 3, em) < 3) return false;   // em[0] = 3 candele fa, em[2] = ultima chiusa
   double ch = iClose(sym, PERIOD_H1, 1);
   f.trH1 = ch > eh[0] ? 1 : (ch < eh[0] ? -1 : 0);
   f.trM15 = em[2] > em[0] ? 1 : (em[2] < em[0] ? -1 : 0);
   f.trD1 = TrendD1(sym);
   f.noise = NoiseState(r, ny, i);
   f.noisePrev = NoiseState(r, ny, i - 1);
   f.nym = MinOfDay(ny[i]);
   f.dow = DowOf(td);
   // pullback nella giornata di trend: la candela precedente tocca l'EMA20, questa riparte
   bool touchL = r[i - 1].low <= ePrev + 0.3 * atr[i - 1];
   bool touchS = r[i - 1].high >= ePrev - 0.3 * atr[i - 1];
   f.pullUp = (f.noise == 1) && touchL && (r[i].close > r[i - 1].high) && (r[i].close > e);
   f.pullDn = (f.noise == -1) && touchS && (r[i].close < r[i - 1].low) && (r[i].close < e);
   double sp = SymbolInfoDouble(sym, SYMBOL_ASK) - SymbolInfoDouble(sym, SYMBOL_BID);
   f.spreadAtr = sp / f.atr;
   f.valid = true;
   return true;
}

//=== SEGNALE E PUNTEGGIO ============================================
// restituisce la direzione (+1/-1/0), il numero di segnali concordi e il punteggio
int Signal(const Feat &f, int &ntrig, int &score, string &info)
{
   int t[5];
   t[0] = f.ret3 >= 1.5 ? 1 : (f.ret3 <= -1.5 ? -1 : 0);
   t[1] = f.ret6 >= 2.5 ? 1 : (f.ret6 <= -2.5 ? -1 : 0);
   t[2] = (f.vwd >= 2 && f.trH1 == 1) ? 1 : ((f.vwd <= -2 && f.trH1 == -1) ? -1 : 0);
   t[3] = f.pullUp ? 1 : (f.pullDn ? -1 : 0);
   t[4] = (f.noise == 1 && f.noisePrev != 1) ? 1 : ((f.noise == -1 && f.noisePrev != -1) ? -1 : 0);
   int pos = 0, neg = 0;
   for(int i = 0; i < 5; i++) { if(t[i] > 0) pos++; if(t[i] < 0) neg++; }
   int d = (pos > 0 && neg == 0) ? 1 : ((neg > 0 && pos == 0) ? -1 : 0);
   ntrig = (d > 0) ? pos : neg;
   score = 0; info = "";
   if(d == 0) return 0;
   int pB = BucketPts(f.nym), pN = NtrigPts(MathMin(ntrig, 4));
   int p6 = PtsFrom(E_MOM6, P_MOM6, f.ret6 * d), p3 = PtsFrom(E_MOM3, P_MOM3, f.ret3 * d);
   int pD = TrD1Pts(f.trD1 * d), pM = TrM15Pts(f.trM15 * d), pZ = NoisePts(f.noise * d);
   int pV = PtsFrom(E_VWD, P_VWD, f.vwd * d), pA = PtsFrom(E_ATRR, P_ATRR, f.atr / f.atrSlow), pW = DowPts(f.dow);
   score = pB + pN + p6 + p3 + pD + pM + pZ + pV + pA + pW;
   info = StringFormat("ora %+d | segnali %d:%+d | imp30 %+d | imp15 %+d | trendG %+d | M15 %+d | noise %+d | VWAP %+d | volat %+d | giorno %+d",
                       pB, ntrig, pN, p6, p3, pD, pM, pZ, pV, pA, pW);
   return d;
}

//=== STATO DELLA GIORNATA (dallo storico delle operazioni) ==========
struct DayStats
{
   int    trades;      // ingressi di oggi
   int    lossStreak;  // stop di fila (ultimi trade chiusi)
   int    winStreak;   // vincenti di fila
   double realized;    // P/L chiuso di oggi
   double peak;        // massimo del P/L chiuso di oggi
   datetime lastEntry;
};

void GetDayStats(DayStats &s, datetime from, datetime to)
{
   s.trades = 0; s.lossStreak = 0; s.winStreak = 0; s.realized = 0; s.peak = 0; s.lastEntry = 0;
   if(!HistorySelect(from, to)) return;
   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
   {
      ulong t = HistoryDealGetTicket(i);
      if(!IsOurMagic(HistoryDealGetInteger(t, DEAL_MAGIC))) continue;
      long entry = HistoryDealGetInteger(t, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_IN)
      {
         s.trades++;
         datetime tt = (datetime)HistoryDealGetInteger(t, DEAL_TIME);
         if(tt > s.lastEntry) s.lastEntry = tt;
      }
      else if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
      {
         double p = HistoryDealGetDouble(t, DEAL_PROFIT) + HistoryDealGetDouble(t, DEAL_SWAP) + HistoryDealGetDouble(t, DEAL_COMMISSION);
         s.realized += p;
         if(s.realized > s.peak) s.peak = s.realized;
         if(p < 0) { s.lossStreak++; s.winStreak = 0; }
         else      { s.winStreak++; s.lossStreak = 0; }
      }
   }
}

//=== RISCHIO ========================================================
double OpenRiskMoney()
{
   double risk = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !IsOurMagic(PositionGetInteger(POSITION_MAGIC))) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      double sl = PositionGetDouble(POSITION_SL), op = PositionGetDouble(POSITION_PRICE_OPEN), vol = PositionGetDouble(POSITION_VOLUME);
      if(sl <= 0) continue;
      double dist = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? op - sl : sl - op;
      if(dist <= 0) continue;                          // stop gia' in profitto: nessun rischio
      double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS), ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
      if(tv <= 0) tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
      if(tv > 0 && ts > 0) risk += dist / ts * tv * vol;
   }
   return risk;
}

// rischio in % per il prossimo trade (regola 'mode 3' della ricerca)
double TradeRiskPct(int score, bool gold, const DayStats &s)
{
   double cap = Capital(), bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double r = RiskPct();
   if(DynRisk())
   {
      double tier = score < 20 ? 0.5 : (score < 40 ? 1.0 : 1.5);
      r *= tier * MathMin(2.0, 1.0 + 0.25 * s.winStreak);
      double eq = (bal - cap) / cap * 100.0;
      if(eq < 0 && MaxLossPct() > 0) r *= MathMax(0.4, 1.0 + eq / MaxLossPct() * 1.2);
   }
   if(gold) r *= 0.5;
   // la perdita piena di tutte le posizioni aperte + questa non deve superare ne' il limite di oggi ne' quello totale
   double openPct = OpenRiskMoney() / cap * 100.0;
   double roomDay = (bal - g_dayStartBal) / cap * 100.0 + DailyLossPct() - openPct;
   double roomTot = (bal - cap) / cap * 100.0 + MaxLossPct() - openPct;
   r = MathMin(r, MathMin(roomDay, roomTot));
   if(r < 0.25 * RiskPct()) return 0;
   return r;
}

int VolumeDigits(double step) { int d = 0; while(d < 8 && MathAbs(step * MathPow(10, d) - MathRound(step * MathPow(10, d))) > 1e-9) d++; return d; }

double LotsFor(string sym, int d, double slDist, double riskMoney)
{
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0) tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(tv <= 0 || ts <= 0 || step <= 0 || slDist <= 0) return 0;
   double lots = MathFloor(riskMoney / (slDist / ts * tv) / step + 1e-9) * step;
   // margine: mai piu' dell'80% del margine libero
   double px = d > 0 ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID), m = 0;
   if(lots > 0 && OrderCalcMargin(d > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, sym, lots, px, m) && m > 0)
   {
      double free = AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.8;
      if(m > free) lots = MathFloor(lots * free / m / step + 1e-9) * step;
   }
   lots = NormalizeDouble(MathMin(lots, vmax), VolumeDigits(step));
   if(lots < vmin) return 0;                            // meglio saltare che rischiare piu' del previsto
   return lots;
}

//=== NOTIZIE ========================================================
bool CurrencyWanted(string cur)
{
   string parts[]; int n = StringSplit(InpNewsCurrencies, ',', parts);
   for(int i = 0; i < n; i++)
   {
      string p = parts[i]; StringTrimLeft(p); StringTrimRight(p); StringToUpper(p);
      if(p == cur) return true;
   }
   return false;
}

void NewsClear() { ArrayResize(g_newsTime, 0); ArrayResize(g_newsImp, 0); ArrayResize(g_newsName, 0); }
void NewsAdd(datetime utc, int imp, string name)
{
   int k = ArraySize(g_newsTime);
   ArrayResize(g_newsTime, k + 1, 256); ArrayResize(g_newsImp, k + 1, 256); ArrayResize(g_newsName, k + 1, 256);
   g_newsTime[k] = utc; g_newsImp[k] = imp; g_newsName[k] = name;
}
// ordina per orario (i dati arrivano gia' quasi ordinati) e toglie i doppioni
void NewsSort()
{
   int n = ArraySize(g_newsTime);
   for(int i = 1; i < n; i++)
   {
      datetime t = g_newsTime[i]; int im = g_newsImp[i]; string nm = g_newsName[i]; int j = i - 1;
      while(j >= 0 && g_newsTime[j] > t) { g_newsTime[j + 1] = g_newsTime[j]; g_newsImp[j + 1] = g_newsImp[j]; g_newsName[j + 1] = g_newsName[j]; j--; }
      g_newsTime[j + 1] = t; g_newsImp[j + 1] = im; g_newsName[j + 1] = nm;
   }
   int w = 0;
   for(int i = 0; i < n; i++)
   {
      if(w > 0 && g_newsTime[w - 1] == g_newsTime[i] && g_newsName[w - 1] == g_newsName[i]) continue;
      g_newsTime[w] = g_newsTime[i]; g_newsImp[w] = g_newsImp[i]; g_newsName[w] = g_newsName[i]; w++;
   }
   ArrayResize(g_newsTime, w); ArrayResize(g_newsImp, w); ArrayResize(g_newsName, w);
}
// primo evento con orario >= t (ricerca binaria)
int NewsFirstFrom(datetime t)
{
   int lo = 0, hi = ArraySize(g_newsTime);
   while(lo < hi) { int mid = (lo + hi) / 2; if(g_newsTime[mid] < t) lo = mid + 1; else hi = mid; }
   return lo;
}

// calendario economico integrato di MetaTrader 5 (gratuito, orari nel fuso del server)
int LoadNewsMT5(datetime fromSrv, datetime toSrv)
{
   string parts[]; int n = StringSplit(InpNewsCurrencies, ',', parts); int added = 0;
   for(int p = 0; p < n; p++)
   {
      string cur = parts[p]; StringTrimLeft(cur); StringTrimRight(cur); StringToUpper(cur);
      MqlCalendarValue vals[];
      ResetLastError();
      int cnt = CalendarValueHistory(vals, fromSrv, toSrv, NULL, cur);
      if(cnt <= 0) continue;
      for(int i = 0; i < cnt; i++)
      {
         MqlCalendarEvent ev;
         if(!CalendarEventById(vals[i].event_id, ev)) continue;
         int imp = 0;
         if(ev.importance == CALENDAR_IMPORTANCE_HIGH) imp = 3;
         else if(ev.importance == CALENDAR_IMPORTANCE_MODERATE) imp = 2;
         if(imp == 0) continue;
         NewsAdd(ToUTC(vals[i].time), imp, cur + " " + ev.name);
         added++;
      }
   }
   return added;
}

string JsonStr(string obj, string key)
{
   string k = "\"" + key + "\"";
   int a = StringFind(obj, k); if(a < 0) return "";
   a = StringFind(obj, ":", a + StringLen(k)); if(a < 0) return "";
   a = StringFind(obj, "\"", a + 1); if(a < 0) return "";
   int b = StringFind(obj, "\"", a + 1); if(b < 0) return "";
   return StringSubstr(obj, a + 1, b - a - 1);
}

// ForexFactory, settimana corrente (richiede l'URL in Strumenti > Opzioni > Expert Advisor > WebRequest)
int LoadNewsFF()
{
   string url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json";
   char post[], res[]; string hdr;
   ResetLastError();
   int code = WebRequest("GET", url, "", 5000, post, res, hdr);
   if(code != 200)
   {
      if(GetLastError() == 4014) Print("FINANCIAL BOT: per le notizie di riserva aggiungi https://nfs.faireconomy.media in Strumenti > Opzioni > Expert Advisor > WebRequest");
      return 0;
   }
   string js = CharArrayToString(res, 0, WHOLE_ARRAY, CP_UTF8);
   int added = 0, pos = 0;
   while(true)
   {
      int a = StringFind(js, "{", pos); if(a < 0) break;
      int b = StringFind(js, "}", a); if(b < 0) break;
      string obj = StringSubstr(js, a, b - a + 1); pos = b + 1;
      string title = JsonStr(obj, "title"), cur = JsonStr(obj, "country"), date = JsonStr(obj, "date"), impact = JsonStr(obj, "impact");
      int imp = impact == "High" ? 3 : (impact == "Medium" ? 2 : 0);
      if(imp == 0 || !CurrencyWanted(cur) || StringLen(date) < 25) continue;
      // formato: 2026-10-27T08:30:00-04:00
      string dt = StringSubstr(date, 0, 10) + " " + StringSubstr(date, 11, 8);
      StringReplace(dt, "-", ".");
      datetime local = StringToTime(dt);
      int sign = StringSubstr(date, 19, 1) == "-" ? -1 : 1;
      int oh = (int)StringToInteger(StringSubstr(date, 20, 2)), om = (int)StringToInteger(StringSubstr(date, 23, 2));
      datetime utc = (datetime)((long)local - sign * (oh * 3600 + om * 60));
      NewsAdd(utc, imp, cur + " " + title);
      added++;
   }
   return added;
}

// Strategy Tester: il calendario non esiste, si legge un file CSV (UTC;valuta;impatto;nome) dalla cartella comune
int LoadNewsCSV()
{
   int h = FileOpen("FINANCIAL_BOT_news_history.csv", FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON, ';');
   if(h == INVALID_HANDLE) return 0;
   int added = 0;
   while(!FileIsEnding(h))
   {
      string ts = FileReadString(h); if(FileIsEnding(h) && ts == "") break;
      string cur = FileReadString(h), imp = FileReadString(h), name = FileReadString(h);
      if(!CurrencyWanted(cur)) continue;
      int im = imp == "High" ? 3 : (imp == "Medium" ? 2 : 0);
      if(im == 0) continue;
      NewsAdd(StringToTime(ts), im, cur + " " + name);
      added++;
   }
   FileClose(h);
   return added;
}

// all'avvio, ogni lunedi' (scansione della settimana), ogni mezzanotte e ogni ora: aggiornamento
void RefreshNews(bool force)
{
   datetime now = TimeTradeServer();
   if(MQLInfoInteger(MQL_TESTER))
   {
      if(g_newsCsvDone) return;
      NewsClear(); int c = LoadNewsCSV(); NewsSort(); g_newsCsvDone = true;
      g_newsSource = c > 0 ? StringFormat("file storico (%d eventi)", c) : "nessuna (manca FINANCIAL_BOT_news_history.csv)";
      return;
   }
   if(!force && now - g_newsLoaded < 3600) return;
   MqlDateTime d; TimeToStruct(now, d);
   NewsClear();
   // dalla domenica della settimana corrente fino a 8 giorni avanti
   datetime from = now - (d.day_of_week + 1) * 86400, to = now + 8 * 86400;
   int n = LoadNewsMT5(from, to);
   g_newsSource = "calendario MT5";
   if(n == 0 && InpNewsWebFallback) { n = LoadNewsFF(); g_newsSource = "ForexFactory"; }
   if(n == 0) g_newsSource = "NON DISPONIBILE";
   NewsSort();
   g_newsLoaded = now;
   long week = (long)now / 604800;
   if(d.day_of_week == 1 && g_newsWeek != week) { g_newsWeek = (datetime)week; Log(StringFormat("NOTIZIE_SETTIMANA;%d eventi;%s", n, g_newsSource)); }
}

bool NewsOk(int i) { return g_newsImp[i] >= 3 || InpNewsMedium; }

// opzionale: niente posizioni aperte durante le notizie rosse (alcune prop lo richiedono sui conti finanziati)
void NewsCloseCheck()
{
   if(InpNewsCloseMin <= 0 || !NewsOn()) return;
   bool have = false;
   for(int i = PositionsTotal() - 1; i >= 0 && !have; i--) if(PositionGetTicket(i) > 0 && IsOurMagic(PositionGetInteger(POSITION_MAGIC))) have = true;
   if(!have) return;
   datetime utc = ToUTC(TimeTradeServer());
   for(int i = NewsFirstFrom(utc); i < ArraySize(g_newsTime) && g_newsTime[i] <= utc + InpNewsCloseMin * 60; i++)
      if(g_newsImp[i] >= 3) { CloseAll("notizia rossa tra pochi minuti: " + g_newsName[i]); return; }
}

bool NewsBlocked(datetime utc, string &why)
{
   why = "";
   if(!NewsOn()) return false;
   for(int i = NewsFirstFrom((datetime)((long)utc - InpNewsAfterMin * 60)); i < ArraySize(g_newsTime); i++)
   {
      if(g_newsTime[i] > utc + InpNewsBeforeMin * 60) break;
      if(NewsOk(i)) { why = g_newsName[i]; return true; }
   }
   return false;
}

string NextNews()
{
   datetime utc = ToUTC(TimeTradeServer());
   for(int i = NewsFirstFrom((datetime)((long)utc - InpNewsAfterMin * 60)); i < ArraySize(g_newsTime); i++)
   {
      if(!NewsOk(i)) continue;
      long dt = (long)g_newsTime[i] - (long)utc;
      string col = g_newsImp[i] == 3 ? "ROSSA" : "gialla";
      if(dt <= 0) return StringFormat("IN CORSO: %s (%s)", g_newsName[i], col);
      return StringFormat("%s (%s) tra %dh%02dm  [%s]", g_newsName[i], col, (int)(dt / 3600), (int)((dt % 3600) / 60), g_newsSource);
   }
   return "nessuna notizia in arrivo  [" + g_newsSource + "]";
}

//=== GIORNATA E LIMITI ==============================================
void DetectCapital()
{
   if(GlobalVariableCheck(GVN("CAP0"))) { g_capAuto = GlobalVariableGet(GVN("CAP0")); return; }
   double first = 0;
   if(HistorySelect(0, TimeCurrent() + 86400))
      for(int i = 0; i < HistoryDealsTotal(); i++)
      {
         ulong t = HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(t, DEAL_TYPE) == DEAL_TYPE_BALANCE && HistoryDealGetDouble(t, DEAL_PROFIT) > 0) { first = HistoryDealGetDouble(t, DEAL_PROFIT); break; }
      }
   if(first <= 0) first = AccountInfoDouble(ACCOUNT_BALANCE);
   g_capAuto = first;
   GlobalVariableSet(GVN("CAP0"), first);
   GlobalVariablesFlush();
}

void CleanupAtrVars()
{
   string pre = GVN("ATR_");
   for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)
   {
      string nm = GlobalVariableName(i);
      if(StringFind(nm, pre) != 0) continue;
      long id = StringToInteger(StringSubstr(nm, StringLen(pre)));
      bool alive = false;
      for(int p = PositionsTotal() - 1; p >= 0 && !alive; p--)
         if(PositionGetTicket(p) > 0 && PositionGetInteger(POSITION_IDENTIFIER) == id) alive = true;
      if(!alive) GlobalVariableDel(nm);
   }
}

void CheckNewDay()
{
   MqlDateTime d; TimeToStruct(TimeTradeServer(), d); d.hour = 0; d.min = 0; d.sec = 0;
   datetime ds = StructToTime(d);
   if(ds == g_dayStart) return;
   if(g_dayStart > 0)
   {   // riepilogo della giornata appena conclusa
      DayStats y; GetDayStats(y, g_dayStart, ds);
      Log(StringFormat("FINE_GIORNO;%s;trade %d;P/L %.2f (%+.2f%%)", TimeToString(g_dayStart, TIME_DATE), y.trades, y.realized, y.realized / Capital() * 100.0));
   }
   g_dayStart = ds;
   g_dayStartBal = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   if(GlobalVariableCheck(GVN("DAYKEY")) && (datetime)GlobalVariableGet(GVN("DAYKEY")) == ds) g_dayStartBal = GlobalVariableGet(GVN("DAYBAL"));
   else { GlobalVariableSet(GVN("DAYKEY"), (double)ds); GlobalVariableSet(GVN("DAYBAL"), g_dayStartBal); GlobalVariablesFlush(); }
   g_haltDay = false; g_haltLogged = false;
   if(!g_halted) g_haltReason = "";      // il fermo definitivo (obiettivo / perdita massima) resta fino al reset
   CleanupAtrVars();
   RefreshNews(true);
}

void CheckLimits(const DayStats &s)
{
   double cap = Capital(), eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!g_halted && GlobalVariableCheck(GVN("HALT")))
   {
      g_halted = true;
      g_haltReason = GlobalVariableGet(GVN("HALT")) == 2 ? "OBIETTIVO RAGGIUNTO" : "perdita massima raggiunta";
   }
   if(g_halted) return;
   if(MaxLossPct() > 0 && eq <= cap * (1 - MaxLossPct() / 100.0))
   {
      CloseAll("perdita massima"); GlobalVariableSet(GVN("HALT"), 1); GlobalVariablesFlush(); g_halted = true; g_haltReason = "perdita massima raggiunta";
      return;
   }
   if(TargetPct() > 0 && eq >= cap * (1 + TargetPct() / 100.0))
   {
      CloseAll("obiettivo");
      if(AccountInfoDouble(ACCOUNT_BALANCE) >= cap * (1 + TargetPct() / 100.0))
      { GlobalVariableSet(GVN("HALT"), 2); GlobalVariablesFlush(); g_halted = true; g_haltReason = "OBIETTIVO RAGGIUNTO"; return; }
   }
   if(!g_haltDay && DailyLossPct() > 0 && eq <= g_dayStartBal - cap * DailyLossPct() / 100.0)
   { CloseAll("perdita giornaliera"); g_haltDay = true; g_haltReason = "perdita giornaliera raggiunta"; }
   if(!g_haltDay && LossStreakMax() > 0 && s.lossStreak >= LossStreakMax())
   { g_haltDay = true; g_haltReason = StringFormat("%d stop loss di fila", s.lossStreak); }
   if(!g_haltDay && InpLockStartPct > 0)
   {
      double peakPct = s.peak / cap * 100.0, curPct = s.realized / cap * 100.0;
      if(peakPct >= InpLockStartPct && curPct <= peakPct * (1 - InpLockGivePct / 100.0))
      { g_haltDay = true; g_haltReason = StringFormat("protezione profitto (max %+.1f%%, ora %+.1f%%)", peakPct, curPct); }
   }
   if(g_haltDay && !g_haltLogged) { Log("STOP_GIORNATA;" + g_haltReason); g_haltLogged = true; }
}

//=== GIORNI MINIMI DI TRADING (dopo l'obiettivo) ====================
// giorni (orario server) con almeno un ingresso sul conto, da quando esiste
int TradingDays()
{
   if(g_tradeDaysAt == g_dayStart && g_tradeDaysAt > 0) return g_tradeDays;
   int n = 0; long last = -1;
   if(HistorySelect(0, TimeCurrent() + 60))
      for(int i = 0; i < HistoryDealsTotal(); i++)
      {
         ulong t = HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(t, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
         long tp = HistoryDealGetInteger(t, DEAL_TYPE);
         if(tp != DEAL_TYPE_BUY && tp != DEAL_TYPE_SELL) continue;
         long dn = DayNum((datetime)HistoryDealGetInteger(t, DEAL_TIME));
         if(dn != last) { n++; last = dn; }
      }
   g_tradeDays = n; g_tradeDaysAt = g_dayStart;
   return n;
}
bool TradedToday()
{
   if(!HistorySelect(g_dayStart, TimeCurrent() + 60)) return false;
   for(int i = 0; i < HistoryDealsTotal(); i++)
   {
      ulong t = HistoryDealGetTicket(i);
      long tp = HistoryDealGetInteger(t, DEAL_TYPE);
      if(HistoryDealGetInteger(t, DEAL_ENTRY) == DEAL_ENTRY_IN && (tp == DEAL_TYPE_BUY || tp == DEAL_TYPE_SELL)) return true;
   }
   return false;
}
// a obiettivo raggiunto: una posizione col lotto minimo (chiusa dopo 2 minuti) per contare il giorno di trading
void MinDaysTrade()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagic + 2 && TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME) >= 120)
         g_trade.PositionClose(t);
   }
   if(InpMinTradingDays <= 0 || Paused() || TradingDays() >= InpMinTradingDays || TradedToday()) return;
   int k = g_sym[0].ok ? 0 : (g_sym[1].ok ? 1 : -1);
   if(k < 0) return;
   datetime ny = SrvToNY(TimeTradeServer()); MqlDateTime d; TimeToStruct(ny, d);
   int m = MinOfDay(ny); string why;
   if(d.day_of_week < 1 || d.day_of_week > 5 || m < 600 || m >= 900 || NewsBlocked(ToUTC(TimeTradeServer()), why)) return;
   string sym = g_sym[k].name;
   double px = SymbolInfoDouble(sym, SYMBOL_ASK), vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   if(px <= 0) return;
   g_trade.SetExpertMagicNumber(InpMagic + 2);
   g_trade.SetTypeFillingBySymbol(sym);
   double sl = NormalizeDouble(px * 0.99, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));
   if(g_trade.Buy(vmin, sym, px, sl, 0, "FINBOT giorno minimo")) Log(StringFormat("GIORNO_MINIMO;%s;giorni di trading %d/%d", sym, TradingDays() + 1, InpMinTradingDays));
   g_tradeDaysAt = 0;
}

//=== GESTIONE POSIZIONI (trailing, tempo, chiusura di sessione) =====
void ManagePositions()
{
   datetime nowSrv = TimeCurrent();
   int nym = MinOfDay(SrvToNY(TimeTradeServer()));
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !IsOurMagic(PositionGetInteger(POSITION_MAGIC))) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      datetime ot = (datetime)PositionGetInteger(POSITION_TIME);
      bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      double op = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL), tp = PositionGetDouble(POSITION_TP);
      // 1) uscita a tempo: dopo 120 minuti oppure alle 16:50 di New York
      if(nowSrv - ot >= HOLD_MIN * 60 || (nym >= CLOSE_NY_MIN && nym < NOENTRY_B))
      {
         if(g_trade.PositionClose(t)) Log(StringFormat("USCITA_TEMPO;%s;%I64u", sym, t));
         continue;
      }
      // 2) trailing 3 ATR dal massimo/minimo dopo +4 ATR (ATR della candela di ingresso)
      string key = GVN("ATR_" + IntegerToString(PositionGetInteger(POSITION_IDENTIFIER)));
      double a = 0, d0 = buy ? op - sl : sl - op;
      if(GlobalVariableCheck(key)) a = GlobalVariableGet(key);
      else if(sl > 0 && d0 > 0) { a = d0 / SL_ATR; GlobalVariableSet(key, a); }   // ricostruito dallo stop iniziale
      if(a <= 0) continue;
      MqlRates m1[]; ArraySetAsSeries(m1, false);
      int n = CopyRates(sym, PERIOD_M1, (datetime)((long)ot - (long)ot % 60), nowSrv, m1);
      if(n <= 0) continue;
      double best = buy ? -DBL_MAX : DBL_MAX;
      for(int j = 0; j < n; j++)
      {
         if(m1[j].time + 60 > nowSrv) break;            // solo minuti chiusi (come nella ricerca)
         if(buy) best = MathMax(best, m1[j].high); else best = MathMin(best, m1[j].low);
      }
      if(best == -DBL_MAX || best == DBL_MAX) continue;
      double fav = buy ? best - op : op - best;
      if(fav < TRAIL_ON_ATR * a) continue;
      int dg = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
      double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
      double nsl = NormalizeDouble(buy ? best - TRAIL_ATR * a : best + TRAIL_ATR * a, dg);
      if((buy && nsl > sl + pt) || (!buy && (sl == 0 || nsl < sl - pt)))
      {
         if(g_trade.PositionModify(t, nsl, tp)) Log(StringFormat("TRAILING;%s;%I64u;%s", sym, t, DoubleToString(nsl, dg)));
      }
   }
}

//=== INGRESSI =======================================================
bool SendOrder(string sym, int d, double lots, double slDist, string cmt, ulong &ticket)
{
   int dg = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   for(int attempt = 0; attempt < 2; attempt++)
   {
      double px = d > 0 ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
      double sl = NormalizeDouble(d > 0 ? px - slDist : px + slDist, dg);
      bool ok = d > 0 ? g_trade.Buy(lots, sym, px, sl, 0, cmt) : g_trade.Sell(lots, sym, px, sl, 0, cmt);
      uint rc = g_trade.ResultRetcode();
      if(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL || rc == TRADE_RETCODE_PLACED)) { ticket = g_trade.ResultOrder(); return true; }
      Log(StringFormat("ORDINE_RIFIUTATO;%s;%u;%s", sym, rc, g_trade.ResultRetcodeDescription()));
      if(rc != TRADE_RETCODE_REQUOTE && rc != TRADE_RETCODE_PRICE_CHANGED && rc != TRADE_RETCODE_PRICE_OFF) return false;
   }
   return false;
}

void OnNewBar(int k)
{
   if(!g_sym[k].ok) return;
   if(k == 0 && !UseNasdaq()) return;
   if(k == 1 && !UseGold()) return;
   string sym = g_sym[k].name;
   bool gold = g_sym[k].gold;
   Feat f;
   if(!ComputeFeatures(k, f)) return;
   // solo la candela appena chiusa e solo nel primo minuto della nuova (dopo un buco nei dati il segnale e' vecchio)
   datetime curBar = iTime(sym, PERIOD_M5, 0);
   if(f.barTime + 300 != curBar || TimeCurrent() - curBar >= MAX_LATE_SEC) return;
   int ntrig, score; string info;
   int d = Signal(f, ntrig, score, info);
   g_sym[k].sigDir = d; g_sym[k].sigScore = score; g_sym[k].sigInfo = info; g_sym[k].sigTime = TimeCurrent();
   if(d == 0) return;

   // regole di sessione (ora del possibile ingresso = adesso)
   datetime nowNY = SrvToNY(TimeTradeServer());
   int m = MinOfDay(nowNY);
   MqlDateTime nd; TimeToStruct(nowNY, nd);
   if(m >= NOENTRY_A && m < NOENTRY_B) return;
   if(nd.day_of_week == 6 || (nd.day_of_week == 5 && m >= FRIDAY_LAST)) return;

   if(gold)
   {   // oro: solo shock di volatilita' nella sessione di New York, punteggio fisso
      double ratio = f.atr / f.atrSlow;
      g_sym[k].sigInfo = StringFormat("volatilita' %.2f volte la media (serve %.1f) | finestra 08:00-15:30 NY", ratio, GOLD_SHOCK);
      if(f.nym < GOLD_WIN_A || f.nym >= GOLD_WIN_B || ratio < GOLD_SHOCK) { g_sym[k].sigScore = 0; return; }
      score = 30; g_sym[k].sigScore = 30;
   }
   DayStats s; GetDayStats(s, g_dayStart, TimeCurrent() + 60);
   int thr = gold ? 30 : Threshold();
   if(!gold && InpIdleMinutes > 0 && (s.lastEntry == 0 || TimeCurrent() - s.lastEntry >= InpIdleMinutes * 60)) thr -= InpIdleRelax;
   string side = d > 0 ? "BUY" : "SELL";
   if(score < thr) { Log(StringFormat("SEGNALE_SCARTATO;%s;%s;punteggio %d < %d;%s", sym, side, score, thr, info)); return; }

   // filtri e limiti
   string why = "";
   int maxSym = g_netting ? 1 : (gold ? InpMaxGold : InpMaxNasdaq);
   if(Paused()) why = "in pausa";
   else if(g_halted) why = "fermo: " + g_haltReason;
   else if(g_haltDay) why = "fermo per oggi: " + g_haltReason;
   else if(NewsBlocked(ToUTC(TimeTradeServer()), why)) why = "notizia: " + why;
   else if(CountPositions(-1) >= InpMaxPositions) why = "gia' " + IntegerToString(InpMaxPositions) + " posizioni aperte sul conto";
   else if(CountPositions(k) >= maxSym) why = "limite posizioni del simbolo";
   else if(g_sym[k].lastEntryBar == g_sym[k].lastBar) why = "gia' entrato su questa candela";
   else if(f.spreadAtr > InpMaxSpreadAtr) why = StringFormat("spread alto (%.2f ATR)", f.spreadAtr);
   if(why != "") { Log(StringFormat("SEGNALE_BLOCCATO;%s;%s;punteggio %d;%s", sym, side, score, why)); return; }

   double rp = TradeRiskPct(score, gold, s);
   if(rp <= 0) { Log(StringFormat("SEGNALE_BLOCCATO;%s;%s;punteggio %d;margine di perdita esaurito", sym, side, score)); return; }
   double slDist = SL_ATR * f.atr;
   double minDist = (SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) + 1) * SymbolInfoDouble(sym, SYMBOL_POINT);
   if(slDist < minDist) { Log(StringFormat("SEGNALE_BLOCCATO;%s;%s;stop troppo vicino per il broker", sym, side)); return; }
   double lots = LotsFor(sym, d, slDist, Capital() * rp / 100.0);
   if(lots <= 0) { Log(StringFormat("SEGNALE_BLOCCATO;%s;%s;lotto sotto il minimo o margine insufficiente", sym, side)); return; }
   g_trade.SetExpertMagicNumber(InpMagic + k);
   g_trade.SetTypeFillingBySymbol(sym);
   string cmt = StringFormat("FINBOT %s s%d", gold ? "XAU" : "NAS", score);
   ulong ticket = 0;
   if(!SendOrder(sym, d, lots, slDist, cmt, ticket)) return;
   g_sym[k].lastEntryBar = g_sym[k].lastBar;
   // l'identificatore della posizione coincide con il ticket dell'ordine di apertura
   GlobalVariableSet(GVN("ATR_" + IntegerToString((long)ticket)), f.atr);
   Log(StringFormat("INGRESSO;%s;%s;lotti %s;rischio %.2f%%;punteggio %d;soglia %d;%s", sym, side, DoubleToString(lots, 2), rp, score, thr, info));
}

// un solo FINANCIAL BOT per conto: il secondo grafico non parte (evita trade doppi)
double InstanceId() { return (double)(ChartID() % 1000000000); }
void Heartbeat()
{
   static datetime last = 0;
   if(TimeLocal() - last < 5) return;
   last = TimeLocal();
   GlobalVariableSet(GVN("ALIVE"), (double)last); GlobalVariableSet(GVN("ALIVE_ID"), InstanceId());
}

void Process()
{
   Heartbeat();
   UpdateOffset();
   CheckNewDay();
   DayStats s; GetDayStats(s, g_dayStart, TimeCurrent() + 60);
   CheckLimits(s);
   ManagePositions();
   RefreshNews(false);
   NewsCloseCheck();
   if(g_halted && GlobalVariableGet(GVN("HALT")) == 2) MinDaysTrade();
   for(int k = 0; k < 2; k++)
   {
      if(!g_sym[k].ok) continue;
      datetime t = iTime(g_sym[k].name, PERIOD_M5, 0);
      if(t == 0 || t == g_sym[k].lastBar) continue;
      bool first = (g_sym[k].lastBar == 0);
      g_sym[k].lastBar = t;
      if(!first) OnNewBar(k);
   }
   if(PanelVisible() && GetTickCount() - g_lastDraw >= 1000) DrawPanel(s);
}

//=== PANNELLO =======================================================
#define P_ "FINBOT_"
bool PanelVisible() { return InpShowPanel && (!MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_VISUAL_MODE)); }

void Lbl(string n, int x, int y, string t, color c = clrWhite, int sz = 9)
{
   string o = P_ + n;
   if(ObjectFind(0, o) < 0) { ObjectCreate(0, o, OBJ_LABEL, 0, 0, 0); ObjectSetInteger(0, o, OBJPROP_CORNER, CORNER_LEFT_UPPER); ObjectSetString(0, o, OBJPROP_FONT, "Arial"); ObjectSetInteger(0, o, OBJPROP_SELECTABLE, false); }
   ObjectSetInteger(0, o, OBJPROP_XDISTANCE, x); ObjectSetInteger(0, o, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, o, OBJPROP_FONTSIZE, sz); ObjectSetInteger(0, o, OBJPROP_COLOR, c); ObjectSetString(0, o, OBJPROP_TEXT, t);
}
void Btn(string n, int x, int y, int w, int h, string t, color bg)
{
   string o = P_ + n;
   if(ObjectFind(0, o) < 0) { ObjectCreate(0, o, OBJ_BUTTON, 0, 0, 0); ObjectSetInteger(0, o, OBJPROP_CORNER, CORNER_LEFT_UPPER); ObjectSetInteger(0, o, OBJPROP_FONTSIZE, 8); }
   ObjectSetInteger(0, o, OBJPROP_XDISTANCE, x); ObjectSetInteger(0, o, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, o, OBJPROP_XSIZE, w); ObjectSetInteger(0, o, OBJPROP_YSIZE, h);
   ObjectSetString(0, o, OBJPROP_TEXT, t); ObjectSetInteger(0, o, OBJPROP_BGCOLOR, bg); ObjectSetInteger(0, o, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, o, OBJPROP_STATE, false);
}
void Edit(string n, int x, int y, int w, string t)
{
   string o = P_ + n;
   if(ObjectFind(0, o) < 0)
   {
      ObjectCreate(0, o, OBJ_EDIT, 0, 0, 0); ObjectSetInteger(0, o, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, o, OBJPROP_FONTSIZE, 9); ObjectSetString(0, o, OBJPROP_TEXT, t);
      ObjectSetInteger(0, o, OBJPROP_BGCOLOR, clrBlack); ObjectSetInteger(0, o, OBJPROP_COLOR, clrWhite);
   }
   ObjectSetInteger(0, o, OBJPROP_XDISTANCE, x); ObjectSetInteger(0, o, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, o, OBJPROP_XSIZE, w); ObjectSetInteger(0, o, OBJPROP_YSIZE, 18);
}
void Rect(string n, int x, int y, int w, int h)
{
   string o = P_ + n;
   if(ObjectFind(0, o) < 0)
   {
      ObjectCreate(0, o, OBJ_RECTANGLE_LABEL, 0, 0, 0); ObjectSetInteger(0, o, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, o, OBJPROP_BGCOLOR, C'20,24,32'); ObjectSetInteger(0, o, OBJPROP_BORDER_TYPE, BORDER_FLAT); ObjectSetInteger(0, o, OBJPROP_BACK, false);
      ObjectSetInteger(0, o, OBJPROP_SELECTABLE, false);
   }
   ObjectSetInteger(0, o, OBJPROP_XDISTANCE, x); ObjectSetInteger(0, o, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, o, OBJPROP_XSIZE, w); ObjectSetInteger(0, o, OBJPROP_YSIZE, h);
}

string CfgKeys[] = {"CAP", "FEE", "TGT", "MXL", "DLY", "RSK", "LSM"};
string CfgLbls[] = {"Capitale", "Costo challenge", "Obiettivo %", "Perdita max %", "Perdita giorno %", "Rischio base %", "Stop dopo N SL"};
double CfgVal(int i)
{
   switch(i)
   {
      case 0: return Capital();
      case 1: return ChallengeCost();
      case 2: return TargetPct();
      case 3: return MaxLossPct();
      case 4: return DailyLossPct();
      case 5: return RiskPct();
   }
   return LossStreakMax();
}

void DrawPanel(const DayStats &s)
{
   g_lastDraw = GetTickCount();
   int x = 8, y = 20, W = 560;
   Rect("bg", x - 4, y - 4, W, 388);
   Lbl("t", x, y, "FINANCIAL BOT  -  Nasdaq & Oro momentum", clrGold, 11); y += 22;
   double cap = Capital(), eq = AccountInfoDouble(ACCOUNT_EQUITY);
   string news = "";
   bool newsNow = NewsOn() && NewsBlocked(ToUTC(TimeTradeServer()), news);
   string st = Paused() ? "IN PAUSA" : (g_halted ? "FERMO: " + g_haltReason : (g_haltDay ? "FERMO PER OGGI: " + g_haltReason : (newsNow ? "ATTIVO - pausa notizia: " + news : "ATTIVO")));
   // vicino alla perdita massima il rischio minimo non ci sta piu': la challenge non e' piu' recuperabile in sicurezza
   double roomTot = (AccountInfoDouble(ACCOUNT_BALANCE) - cap) / cap * 100.0 + MaxLossPct() - OpenRiskMoney() / cap * 100.0;
   if(!g_halted && !Paused() && roomTot < 0.25 * RiskPct()) st = StringFormat("FERMO: margine fino alla perdita massima esaurito (%.2f%%)", roomTot);
   color sc = StringFind(st, "ATTIVO") == 0 ? clrLime : (g_halted && g_haltReason == "OBIETTIVO RAGGIUNTO" ? clrGold : clrTomato);
   if(g_halted && g_haltReason == "OBIETTIVO RAGGIUNTO" && InpMinTradingDays > 0)
      st += StringFormat("  (giorni di trading %d/%d%s)", TradingDays(), InpMinTradingDays, TradingDays() < InpMinTradingDays ? ": 1 micro-trade al giorno" : ": completati");
   Lbl("st", x, y, "Stato: " + st, sc, 10); y += 18;
   string fee = ChallengeCost() > 0 ? StringFormat("   Costo %s (%.2f%%)", Money(ChallengeCost()), ChallengeCost() / cap * 100) : "";
   Lbl("eq", x, y, StringFormat("Capitale %s   Equity %s   Totale %+.2f%%   Oggi %+.2f%%", Money(cap), DoubleToString(eq, 2), (eq - cap) / cap * 100, (eq - g_dayStartBal) / cap * 100) + fee); y += 16;
   string tg = TargetPct() > 0 ? StringFormat("Obiettivo %s (+%.1f%%)", Money(cap * (1 + TargetPct() / 100)), TargetPct()) : "Obiettivo: nessuno";
   Lbl("lv", x, y, tg + StringFormat("   Stop totale %s (-%.1f%%)   Stop oggi %s (-%.1f%%)", Money(cap * (1 - MaxLossPct() / 100)), MaxLossPct(),
       Money(g_dayStartBal - cap * DailyLossPct() / 100), DailyLossPct()), clrSilver); y += 16;
   Lbl("tr", x, y, StringFormat("Oggi: trade %d   SL di fila %d/%d   vincenti di fila %d   posizioni %d/%d   prossimo rischio ~%.2f%%",
       s.trades, s.lossStreak, LossStreakMax(), s.winStreak, CountPositions(-1), InpMaxPositions, TradeRiskPct(25, false, s))); y += 16;
   Lbl("nw", x, y, "Notizie: " + (NewsOn() ? NextNews() : "filtro DISATTIVATO"), clrSilver); y += 16;
   string warn = "";
   for(int k = 0; k < 2; k++) if(g_sym[k].ok && g_sym[k].bars > 0 && g_sym[k].bars < MIN_BARS) warn += StringFormat("  STORICO M5 INSUFFICIENTE su %s (%d candele)", g_sym[k].name, g_sym[k].bars);
   Lbl("sy", x, y, StringFormat("Nasdaq = %s   Oro = %s   Server UTC%+.0f%s", g_sym[0].name == "" ? "NON TROVATO" : g_sym[0].name, g_sym[1].name == "" ? "NON TROVATO" : g_sym[1].name,
       ServerUTCHours(), g_netting ? "   conto NETTING: 1 posizione per simbolo" : "") + warn, warn != "" ? clrTomato : clrSilver); y += 20;
   for(int i = 0; i < 7; i++)
   {
      int cx = x + (i % 4) * 138, cy = y + (i / 4) * 38;
      Lbl("cl" + IntegerToString(i), cx, cy, CfgLbls[i], clrSilver, 8);
      Edit("ce" + IntegerToString(i), cx, cy + 13, 128, DoubleToString(CfgVal(i), (i <= 1 || i == 6) ? 0 : 2));
   }
   y += 80;
   Btn("save", x, y, 176, 22, "Salva impostazioni", clrSeaGreen);
   Btn("mode", x + 184, y, 176, 22, "Modalita': " + ModeName(), clrSteelBlue);
   Btn("dyn", x + 368, y, 176, 22, DynRisk() ? "Rischio: DINAMICO" : "Rischio: FISSO", DynRisk() ? clrDarkOrange : clrSlateGray); y += 26;
   Btn("nas", x, y, 176, 22, UseNasdaq() ? "Nasdaq: ON" : "Nasdaq: OFF", UseNasdaq() ? clrSeaGreen : clrFireBrick);
   Btn("xau", x + 184, y, 176, 22, UseGold() ? "Oro: ON" : "Oro: OFF", UseGold() ? clrSeaGreen : clrFireBrick);
   Btn("nws", x + 368, y, 176, 22, NewsOn() ? "Filtro notizie: ON" : "Filtro notizie: OFF", NewsOn() ? clrSeaGreen : clrFireBrick); y += 26;
   Btn("pau", x, y, 176, 22, Paused() ? "RIPRENDI" : "PAUSA", Paused() ? clrSeaGreen : clrGoldenrod);
   Btn("cls", x + 184, y, 176, 22, "CHIUDI TUTTO", clrRed);
   Btn("rst", x + 368, y, 176, 22, "Reset blocco", clrDimGray); y += 30;
   for(int k = 0; k < 2; k++)
   {
      string tx;
      if(g_sym[k].sigTime == 0) tx = "in attesa della prossima candela M5";
      else if(g_sym[k].sigDir == 0) tx = "nessuna accelerazione sull'ultima candela (" + TimeToString(g_sym[k].sigTime, TIME_MINUTES) + ")";
      else if(k == 1 && g_sym[k].sigScore == 0) tx = StringFormat("accelerazione %s ma nessuno shock di volatilita' (%s)", g_sym[k].sigDir > 0 ? "BUY" : "SELL", TimeToString(g_sym[k].sigTime, TIME_MINUTES));
      else tx = StringFormat("%s punteggio %d (soglia %d) alle %s", g_sym[k].sigDir > 0 ? "BUY" : "SELL", g_sym[k].sigScore, k == 1 ? 30 : Threshold(), TimeToString(g_sym[k].sigTime, TIME_MINUTES));
      Lbl("sg" + IntegerToString(k), x, y, (k == 0 ? "Nasdaq: " : "Oro: ") + tx, clrWhite, 8); y += 14;
      Lbl("si" + IntegerToString(k), x, y, g_sym[k].sigDir == 0 ? "" : g_sym[k].sigInfo, clrGray, 7); y += 16;
   }
   ChartRedraw();
}

void SaveCfg()
{
   double v[7];
   for(int i = 0; i < 7; i++)
   {
      v[i] = StringToDouble(ObjectGetString(0, P_ + "ce" + IntegerToString(i), OBJPROP_TEXT));
      bool bad = (i == 0 && v[i] <= 0) || (i == 5 && (v[i] <= 0 || v[i] > 3)) || (i >= 1 && i <= 4 && v[i] < 0) || (i == 3 && v[i] > 50) || (i == 4 && v[i] > 20) || (i == 6 && v[i] < 0);
      if(bad) { MessageBox(CfgLbls[i] + ": valore non valido", "FINANCIAL BOT"); return; }
   }
   for(int i = 0; i < 7; i++) GlobalVariableSet(GVN(CfgKeys[i]), v[i]);
   GlobalVariablesFlush();
   Log(StringFormat("IMPOSTAZIONI_SALVATE;capitale %.0f;obiettivo %.2f;perdita max %.2f;perdita giorno %.2f;rischio %.2f;stop dopo %d SL", v[0], v[2], v[3], v[4], v[5], (int)v[6]));
}

void Toggle(string k, bool cur) { GlobalVariableSet(GVN(k), cur ? 0 : 1); }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id != CHARTEVENT_OBJECT_CLICK || StringFind(sparam, P_) != 0) return;
   string b = StringSubstr(sparam, StringLen(P_));
   if(b == "save") SaveCfg();
   else if(b == "mode") GlobalVariableSet(GVN("MOD"), (Mode() + 1) % 3);
   else if(b == "dyn") Toggle("DYN", DynRisk());
   else if(b == "nas") Toggle("NAS", UseNasdaq());
   else if(b == "xau") Toggle("XAU", UseGold());
   else if(b == "nws") Toggle("NWS", NewsOn());
   else if(b == "pau") Toggle("PAU", Paused());
   else if(b == "cls") { if(MessageBox("Chiudere tutte le posizioni del FINANCIAL BOT?", "FINANCIAL BOT", MB_YESNO) == IDYES) CloseAll("manuale"); }
   else if(b == "rst")
   {
      if(MessageBox("Rimuovere il blocco (obiettivo / perdita massima / giornata)? Fallo solo a inizio nuova fase o nuovo conto.", "FINANCIAL BOT", MB_YESNO) == IDYES)
      { GlobalVariableDel(GVN("HALT")); g_halted = false; g_haltDay = false; g_haltLogged = false; g_haltReason = ""; Log("RESET_BLOCCO"); }
   }
   else return;
   DayStats s; GetDayStats(s, g_dayStart, TimeCurrent() + 60);
   if(PanelVisible()) DrawPanel(s);
}

//=== EVENTI =========================================================
int OnInit()
{
   g_prefix = "FINBOT_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_" + IntegerToString(InpMagic) + "_";
   g_trade.SetDeviationInPoints(50);
   if(MQLInfoInteger(MQL_TESTER)) GlobalVariablesDeleteAll(g_prefix);
   else if(GlobalVariableCheck(GVN("ALIVE")) && TimeLocal() - (datetime)GlobalVariableGet(GVN("ALIVE")) < 15 && GlobalVariableGet(GVN("ALIVE_ID")) != InstanceId())
   {
      Alert("FINANCIAL BOT e' gia' attivo su un altro grafico di questo conto: ne basta uno (opera da solo Nasdaq e oro).");
      return INIT_FAILED;
   }
   SyncInput("CAP", InpCapital); SyncInput("FEE", InpChallengeCost); SyncInput("TGT", InpTargetPct); SyncInput("MXL", InpMaxLossPct);
   SyncInput("DLY", InpDailyLossPct); SyncInput("RSK", InpRiskPct); SyncInput("LSM", InpMaxLossStreak); SyncInput("MOD", InpMode);
   SyncInput("NAS", InpTradeNasdaq ? 1 : 0); SyncInput("XAU", InpTradeGold ? 1 : 0); SyncInput("DYN", InpDynamicRisk ? 1 : 0); SyncInput("NWS", InpNewsFilter ? 1 : 0);
   g_netting = AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
   UpdateOffset();
   DetectCapital();
   string nasC[] = {"NAS100", "US100", "USTEC", "NDX100", "NASDAQ100", "NAS100USD", "US100Cash", "NQ100", "USTECH", "TECH100", "NASDAQ", "NDX"};
   string xauC[] = {"XAUUSD", "GOLD", "XAUUSDm", "XAU/USD", "XAUUSD.", "GOLDUSD"};
   string nas = FindSymbol(InpNasdaqSymbol, nasC), xau = FindSymbol(InpGoldSymbol, xauC);
   InitSymbol(0, nas, false); InitSymbol(1, xau, true);
   if(!g_sym[0].ok && !g_sym[1].ok) { Alert("FINANCIAL BOT: nessun simbolo Nasdaq/oro trovato. Scrivi il nome negli input."); return INIT_FAILED; }
   if(!g_sym[0].ok) Print("FINANCIAL BOT: Nasdaq non trovato, opero solo l'oro.");
   if(!g_sym[1].ok) Print("FINANCIAL BOT: oro non trovato, opero solo il Nasdaq.");
   if(g_netting) Print("FINANCIAL BOT: conto NETTING, al massimo 1 posizione per simbolo.");
   PrintFormat("FINANCIAL BOT avviato. Nasdaq=%s Oro=%s capitale=%.2f server UTC%+.1f", nas, xau, Capital(), ServerUTCHours());
   CheckNewDay();                       // carica anche le notizie
   EventSetTimer(1);
   Log(StringFormat("AVVIO;Nasdaq=%s;Oro=%s;modalita'=%s;capitale=%.2f;rischio=%.2f%%;server UTC%+.1f", nas, xau, ModeName(), Capital(), RiskPct(), ServerUTCHours()));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(!MQLInfoInteger(MQL_TESTER) && GlobalVariableGet(GVN("ALIVE_ID")) == InstanceId()) GlobalVariableDel(GVN("ALIVE"));
   ObjectsDeleteAll(0, P_);
   for(int k = 0; k < 2; k++)
   {
      if(g_sym[k].hEmaH1 != INVALID_HANDLE) IndicatorRelease(g_sym[k].hEmaH1);
      if(g_sym[k].hEmaM15 != INVALID_HANDLE) IndicatorRelease(g_sym[k].hEmaM15);
   }
}

void OnTick()  { Process(); }
void OnTimer() { Process(); }
//+------------------------------------------------------------------+
