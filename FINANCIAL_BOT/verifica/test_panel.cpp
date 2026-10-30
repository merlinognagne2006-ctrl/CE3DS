// esegue l'EA in modalita' visuale: disegna il pannello, prova tutti i pulsanti e salva gli oggetti per il disegno
#include "FINANCIAL_BOT.run.hpp"
#include <fstream>
static void load(const char* path, sim::Symbol& s, long long from, long long to)
{
   std::FILE* f = std::fopen(path, "rb"); long long n; std::fread(&n, 8, 1, f);
   struct Rec { long long t; double o, h, l, c, v; }; Rec r;
   for(long long i = 0; i < n; i++)
   {
      std::fread(&r, sizeof(r), 1, f); if(r.t < from) continue; if(r.t >= to) break;
      MqlRates b{}; b.time = r.t + 2 * 3600; b.open = r.o; b.high = r.h; b.low = r.l; b.close = r.c; b.tick_volume = (long)std::max(1.0, r.v); s.m1.push_back(b);
   }
   std::fclose(f);
}
static void dump(const char* path)
{
   auto& st = sim::S(); std::ofstream o(path);
   for(auto& kv : st.obj_i)
   {
      auto& s = st.obj_s[kv.first]; auto gi = [&](int p) { auto it = kv.second.find(p); return it == kv.second.end() ? 0LL : it->second; };
      std::string txt = s.count(OBJPROP_TEXT) ? s[OBJPROP_TEXT] : ""; for(auto& c : txt) if(c == '\t') c = ' ';
      o << kv.first << '\t' << gi(OBJPROP_XDISTANCE) << '\t' << gi(OBJPROP_YDISTANCE) << '\t' << gi(OBJPROP_XSIZE) << '\t' << gi(OBJPROP_YSIZE) << '\t'
        << gi(OBJPROP_COLOR) << '\t' << gi(OBJPROP_BGCOLOR) << '\t' << gi(OBJPROP_FONTSIZE) << '\t' << txt << '\n';
   }
}
int main()
{
   auto& st = sim::S(); st.tester = true; st.visual = true; st.quiet = true; st.keep_prints = true;
   st.files_dir = "."; st.common_dir = "common";
   sim::Symbol n; n.name = "US100.cash"; n.tick_value = 0.01; n.spread_rel = 0.00006;
   sim::Symbol g; g.name = "XAUUSD"; g.tick_value = 1.0; g.contract = 100; g.vmax = 50; g.spread_rel = 0.0001;
   long long from = 1704067200 - 40 * 86400, to = 1704326400;   // dati fino al 2024-01-04
   load("data/NAS_M1.bin", n, from, to); load("data/XAU_M1.bin", g, from, to);
   st.syms.push_back(n); st.syms.push_back(g);
   std::vector<datetime> tl; for(auto& s : st.syms) for(auto& b : s.m1) if(b.time >= 1704153600 + 7200) tl.push_back(b.time);
   std::sort(tl.begin(), tl.end()); tl.erase(std::unique(tl.begin(), tl.end()), tl.end());
   sim::advance(tl[0]); sim::deposit(100000);
   MQLProgram* P = new MQLProgram(); P->__set_input("InpChallengeCost", "540");
   if(P->OnInit() != INIT_SUCCEEDED) { std::printf("OnInit fallito\n"); return 1; }
   long long stop = 1704204000;  // 2024-01-02 14:00 UTC
   try
   {
      for(datetime t : tl) { if(t > stop + 7200) break; sim::advance(t); sim::process_sl(true); P->OnTick(); sim::process_sl(false); }
      dump("panel_attivo.tsv");
      // prova dei pulsanti
      auto click = [&](const char* b) { P->OnChartEvent(CHARTEVENT_OBJECT_CLICK, 0, 0.0, string("FINBOT_") + b); };
      ObjectSetString(0, "FINBOT_ce0", OBJPROP_TEXT, "50000"); click("save");
      std::printf("dopo Salva: capitale %.0f\n", P->Capital());
      ObjectSetString(0, "FINBOT_ce5", OBJPROP_TEXT, "7"); click("save");
      std::printf("rischio 7%% rifiutato: rischio %.2f\n", P->RiskPct());
      click("mode"); std::printf("modalita' -> %s\n", P->ModeName().c_str());
      click("mode"); click("mode");
      click("dyn"); std::printf("rischio dinamico %d\n", (int)P->DynRisk()); click("dyn");
      click("nas"); click("xau"); click("nws"); std::printf("nasdaq %d oro %d notizie %d\n", (int)P->UseNasdaq(), (int)P->UseGold(), (int)P->NewsOn());
      click("nas"); click("xau"); click("nws");
      click("pau"); std::printf("pausa %d\n", (int)P->Paused()); click("pau");
      click("cls"); std::printf("posizioni dopo CHIUDI TUTTO: %d\n", PositionsTotal());
      click("rst"); click("ce3");
      ObjectSetString(0, "FINBOT_ce0", OBJPROP_TEXT, "100000"); ObjectSetString(0, "FINBOT_ce5", OBJPROP_TEXT, "0.25"); click("save");
      for(datetime t : tl) { if(t <= stop + 7200) continue; sim::advance(t); sim::process_sl(true); P->OnTick(); sim::process_sl(false); }
      MQLProgram::DayStats s; P->GetDayStats(s, P->g_dayStart, TimeCurrent() + 60); P->DrawPanel(s);
   }
   catch(const std::exception& e) { std::printf("ERRORE: %s\n", e.what()); return 2; }
   dump("panel_fine.tsv");
   std::printf("ok, oggetti: %zu\n", st.obj_i.size());
   return 0;
}
