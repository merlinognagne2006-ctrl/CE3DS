// prove delle parti che funzionano solo dal vivo: fuso del server, calendario MT5, ForexFactory
#include "FINANCIAL_BOT.run.hpp"
static datetime T(int y, int m, int d, int h, int mi) { MqlDateTime s{}; s.year = y; s.mon = m; s.day = d; s.hour = h; s.min = mi; return StructToTime(s); }
static int fails = 0;
static void check(bool ok, const char* what) { std::printf("%s %s\n", ok ? "OK  " : "FAIL", what); if(!ok) fails++; }
int main()
{
   auto& st = sim::S(); st.tester = false; st.quiet = true; st.files_dir = ".";
   sim::Symbol n; n.name = "US100.cash"; st.syms.push_back(n);
   // estate (ora legale USA): server GMT+3
   st.now = T(2026, 7, 15, 17, 0); st.gmt_off = 3 * 3600;
   MQLProgram* P = new MQLProgram(); P->UpdateOffset();
   check(P->g_baseOff == 2 * 3600, "estate: offset di base del server = UTC+2");
   check(P->ServerUTCHours() == 3.0, "estate: server UTC+3");
   check(P->ToUTC(T(2026, 1, 15, 17, 0)) == T(2026, 1, 15, 15, 0), "candela d'inverno convertita con UTC+2");
   check(P->ToUTC(T(2026, 7, 15, 17, 0)) == T(2026, 7, 15, 14, 0), "candela d'estate convertita con UTC+3");
   check(P->MinOfDay(P->SrvToNY(T(2026, 7, 15, 16, 30))) == 570, "16:30 server d'estate = 09:30 New York");
   check(P->MinOfDay(P->SrvToNY(T(2026, 1, 15, 16, 30))) == 570, "16:30 server d'inverno = 09:30 New York");
   // settimana di marzo in cui gli USA sono gia' in ora legale e l'Europa no: il server USA-DST resta allineato a NY
   check(P->MinOfDay(P->SrvToNY(T(2026, 3, 16, 16, 30))) == 570, "marzo (USA in ora legale): 09:30 New York");
   // inverno: server GMT+2
   st.now = T(2026, 12, 1, 12, 0); st.gmt_off = 2 * 3600; P->UpdateOffset();
   check(P->g_baseOff == 2 * 3600 && P->ServerUTCHours() == 2.0, "inverno: server UTC+2");
   // calendario MT5: un evento USD rosso alle 15:30 server (estate) = 12:30 UTC
   st.now = T(2026, 7, 15, 10, 0); st.gmt_off = 3 * 3600; P->UpdateOffset();
   MqlCalendarEvent ev{}; ev.id = 7; ev.importance = CALENDAR_IMPORTANCE_HIGH; ev.name = "Nonfarm Payrolls"; st.cal_evs.push_back(ev);
   MqlCalendarEvent ev2{}; ev2.id = 8; ev2.importance = CALENDAR_IMPORTANCE_LOW; ev2.name = "Bassa"; st.cal_evs.push_back(ev2);
   MqlCalendarValue v{}; v.event_id = 7; v.time = T(2026, 7, 15, 15, 30); st.cal_vals.push_back(v); st.cal_cur.push_back("USD");
   MqlCalendarValue v2{}; v2.event_id = 8; v2.time = T(2026, 7, 15, 16, 0); st.cal_vals.push_back(v2); st.cal_cur.push_back("USD");
   P->RefreshNews(true);
   check(ArraySize(P->g_newsTime) == 1 && P->g_newsTime[0] == T(2026, 7, 15, 12, 30), "calendario MT5: evento rosso alle 12:30 UTC, quello a basso impatto ignorato");
   string why;
   st.now = T(2026, 7, 15, 15, 26); check(P->NewsBlocked(P->ToUTC(TimeTradeServer()), why), "4 minuti prima: ingressi bloccati");
   st.now = T(2026, 7, 15, 15, 24); check(!P->NewsBlocked(P->ToUTC(TimeTradeServer()), why), "6 minuti prima: libero");
   st.now = T(2026, 7, 15, 15, 35); check(P->NewsBlocked(P->ToUTC(TimeTradeServer()), why), "5 minuti dopo: ancora bloccato");
   st.now = T(2026, 7, 15, 15, 36); check(!P->NewsBlocked(P->ToUTC(TimeTradeServer()), why), "6 minuti dopo: libero");
   // ForexFactory quando il calendario MT5 non risponde
   st.cal_vals.clear(); st.cal_cur.clear(); st.now = T(2026, 10, 27, 10, 0); st.gmt_off = 2 * 3600;
   st.web_json = "[{\"title\":\"CB Consumer Confidence\",\"country\":\"USD\",\"date\":\"2026-10-27T10:00:00-04:00\",\"impact\":\"High\",\"forecast\":\"93.4\",\"previous\":\"94.2\"},"
                 "{\"title\":\"German Ifo\",\"country\":\"EUR\",\"date\":\"2026-10-27T04:00:00-04:00\",\"impact\":\"High\",\"forecast\":\"\",\"previous\":\"\"},"
                 "{\"title\": \"Richmond Manufacturing Index\", \"country\": \"USD\", \"date\": \"2026-10-27T10:00:00-04:00\", \"impact\": \"Medium\"},"
                 "{\"title\":\"Bank Holiday\",\"country\":\"USD\",\"date\":\"2026-10-28T00:00:00-04:00\",\"impact\":\"Holiday\"}]";
   P->UpdateOffset(); P->RefreshNews(true);
   check(P->g_newsSource == "ForexFactory", "fonte di riserva: ForexFactory");
   check(ArraySize(P->g_newsTime) == 2 && P->g_newsTime[0] == T(2026, 10, 27, 14, 0) && P->g_newsImp[0] + P->g_newsImp[1] == 5, "ForexFactory: 2 eventi USD (rosso e giallo) alle 14:00 UTC, EUR e festivita' scartati");
   std::printf("prossima notizia: %s\n", P->NextNews().c_str());
   return fails ? 1 : 0;
}
