// Esegue il codice VERO di FINANCIAL_BOT.mq5 (tradotto da mq5tocpp.py) su dati storici M1, con un broker simulato:
// un tick all'apertura di ogni minuto, stop lato server sul massimo/minimo del minuto, spread = costo della ricerca.
// Uso: harness --from 2014-01-01 --to 2026-10-01 --out dir [--deposit 100000] [--set Inp=val]... [--stop-on-halt]
#include "FINANCIAL_BOT.run.hpp"
#include <sys/stat.h>
#include <chrono>

static bool us_dst(long long utc)
{
   MqlDateTime d; TimeToStruct(utc, d);
   auto sunday = [](int y, int m, int nth) {
      long long first = sim_days_from_civil(y, (unsigned)m, 1);
      int wd = (int)(((first % 7) + 11) % 7);   // 0 = domenica
      return (first + (7 - wd) % 7 + 7 * (nth - 1)) * 86400;
   };
   long long a = sunday(d.year, 3, 2) + 7 * 3600, b = sunday(d.year, 11, 1) + 6 * 3600;
   return utc >= a && utc < b;
}

static long long parse_date(const std::string& s)
{
   int y, m, d; if(std::sscanf(s.c_str(), "%d-%d-%d", &y, &m, &d) != 3) throw std::runtime_error("data non valida " + s);
   return sim_days_from_civil(y, (unsigned)m, (unsigned)d) * 86400;
}

// file binario: int64 n, poi n record {int64 t_utc, double o, h, l, c, v}
static void load_bin(const std::string& path, sim::Symbol& s, int utc_off, long long from_utc, long long to_utc)
{
   std::FILE* f = std::fopen(path.c_str(), "rb"); if(!f) throw std::runtime_error("manca " + path);
   long long n = 0; if(std::fread(&n, 8, 1, f) != 1) throw std::runtime_error("file vuoto");
   struct Rec { long long t; double o, h, l, c, v; };
   std::vector<Rec> rec((size_t)n); if(std::fread(rec.data(), sizeof(Rec), (size_t)n, f) != (size_t)n) throw std::runtime_error("file troncato");
   std::fclose(f);
   s.m1.reserve((size_t)n);
   for(auto& r : rec)
   {
      if(r.t < from_utc) continue;
      if(r.t >= to_utc) break;
      MqlRates b; b.time = r.t + utc_off * 3600 + (us_dst(r.t) ? 3600 : 0);
      b.open = r.o; b.high = r.h; b.low = r.l; b.close = r.c; b.tick_volume = (long)std::max(1.0, std::round(r.v)); b.spread = 0; b.real_volume = 0;
      if(!s.m1.empty() && b.time <= s.m1.back().time) continue;   // salto dell'ora (non succede: i dati sono in UTC)
      s.m1.push_back(b);
   }
}

int main(int argc, char** argv)
{
   std::string from_s = "2014-01-01", to_s = "2026-10-01", out = "out", nas = "data/NAS_M1.bin", xau = "data/XAU_M1.bin", common = "common";
   double deposit = 100000; bool stop_on_halt = false, quiet = true; int utc_off = 2; double nas_spread = 0.00006, xau_spread = 0.0001;
   double prop_daily = 0, prop_max = 0, payout_split = 0; int max_days = 0, warmup_days = 150;
   std::vector<std::pair<std::string, std::string>> sets;
   for(int i = 1; i < argc; i++)
   {
      std::string a = argv[i];
      auto next = [&]() { if(i + 1 >= argc) throw std::runtime_error("manca il valore di " + a); return std::string(argv[++i]); };
      if(a == "--from") from_s = next(); else if(a == "--to") to_s = next(); else if(a == "--out") out = next();
      else if(a == "--deposit") deposit = std::stod(next()); else if(a == "--nas") nas = next(); else if(a == "--xau") xau = next();
      else if(a == "--common") common = next(); else if(a == "--stop-on-halt") stop_on_halt = true; else if(a == "--verbose") quiet = false;
      else if(a == "--nas-spread") nas_spread = std::stod(next()); else if(a == "--xau-spread") xau_spread = std::stod(next());
      else if(a == "--prop-daily") prop_daily = std::stod(next()); else if(a == "--prop-max") prop_max = std::stod(next());
      else if(a == "--payout") payout_split = std::stod(next()); else if(a == "--max-days") max_days = std::stoi(next());
      else if(a == "--warmup-days") warmup_days = std::stoi(next());
      else if(a == "--set") { std::string kv = next(); size_t e = kv.find('='); sets.push_back({kv.substr(0, e), kv.substr(e + 1)}); }
      else throw std::runtime_error("argomento sconosciuto " + a);
   }
   long long from_utc = parse_date(from_s), to_utc = parse_date(to_s);
   for(size_t k = 1; k <= out.size(); k++) if(k == out.size() || out[k] == '/') mkdir(out.substr(0, k).c_str(), 0755);
   mkdir((out + "/files").c_str(), 0755);
   auto& st = sim::S();
   st.files_dir = out + "/files"; st.common_dir = common; st.quiet = quiet; st.tester = true;
   std::remove((st.files_dir + "/FINANCIAL_BOT_log.csv").c_str());

   // simboli: nomi come su FTMO, piu' due esche (NAS100 disattivato, EURUSD) per provare il riconoscimento automatico
   sim::Symbol dec1; dec1.name = "EURUSD"; st.syms.push_back(dec1);
   sim::Symbol dec2; dec2.name = "NAS100"; dec2.tradeable = false; st.syms.push_back(dec2);
   sim::Symbol n; n.name = "US100.cash"; n.digits = 2; n.point = 0.01; n.tick_size = 0.01; n.tick_value = 0.01; n.contract = 1; n.vmax = 100; n.spread_rel = nas_spread;
   sim::Symbol g; g.name = "XAUUSD"; g.digits = 2; g.point = 0.01; g.tick_size = 0.01; g.tick_value = 1.0; g.contract = 100; g.vmax = 50; g.spread_rel = xau_spread;
   // storico precedente: 150 giorni bastano (6000 candele M5 = ~21 giorni, EMA50 H1 e trend giornaliero a regime)
   long long load_from = warmup_days > 0 ? from_utc - warmup_days * 86400LL : 0;
   load_bin(nas, n, utc_off, load_from, to_utc + 3 * 86400);
   if(xau != "none") load_bin(xau, g, utc_off, load_from, to_utc + 3 * 86400);
   st.syms.push_back(n); st.syms.push_back(g);

   // calendario dei minuti: unione dei due simboli nel periodo richiesto (orario server)
   long long from_srv = from_utc + utc_off * 3600, to_srv = to_utc + utc_off * 3600;
   std::vector<datetime> tl;
   for(auto& s : st.syms) for(auto& b : s.m1) if(b.time >= from_srv && b.time < to_srv) tl.push_back(b.time);
   std::sort(tl.begin(), tl.end()); tl.erase(std::unique(tl.begin(), tl.end()), tl.end());
   if(tl.empty()) throw std::runtime_error("nessun dato nel periodo");

   sim::advance(tl[0]);
   sim::deposit(deposit);
   MQLProgram* P = new MQLProgram();
   for(auto& kv : sets) if(!P->__set_input(kv.first, kv.second)) throw std::runtime_error("input sconosciuto " + kv.first);
   int rc = P->OnInit();
   if(rc != INIT_SUCCEEDED) { std::fprintf(stderr, "OnInit fallito (%d)\n", rc); return 2; }

   std::FILE* fd = std::fopen((out + "/daily.csv").c_str(), "w");
   if(!fd) throw std::runtime_error("impossibile scrivere in " + out);
   std::fprintf(fd, "day,balance,equity_min,trades_closed\n");
   long long day = tl[0] / 86400; double eq_min = deposit; size_t closed_mark = 0;
   std::string halt = ""; datetime halt_t = 0;
   double day_start = deposit, payouts = 0, worst_daily = 0, worst_total = 0; int n_payouts = 0;
   auto month_of = [](datetime t) { MqlDateTime d; TimeToStruct(t, d); return d.year * 12 + d.mon; };
   int cur_month = month_of(tl[0]);
   auto t0 = std::chrono::steady_clock::now();
   try
   {
      for(datetime t : tl)
      {
         if(t / 86400 != day)
         {
            std::fprintf(fd, "%s,%.2f,%.2f,%zu\n", TimeToString(day * 86400, TIME_DATE).c_str(), st.balance, eq_min, st.closed.size() - closed_mark);
            closed_mark = st.closed.size(); day = t / 86400;
            // pagamento mensile (conto finanziato): si preleva il profitto, il conto torna al capitale iniziale
            if(payout_split > 0 && month_of(t) != cur_month)
            {
               cur_month = month_of(t);
               if(st.pos.empty() && st.balance > deposit) { payouts += (st.balance - deposit) * payout_split; n_payouts++; sim::withdraw(st.balance - deposit); }
            }
            day_start = std::max(st.balance, sim::equity()); eq_min = sim::equity();
         }
         sim::advance(t);
         sim::process_sl(true);
         P->OnTick();
         sim::process_sl(false);
         double weq = sim::worst_equity();
         eq_min = std::min(eq_min, weq);
         worst_daily = std::max(worst_daily, (day_start - weq) / deposit * 100); worst_total = std::max(worst_total, (deposit - weq) / deposit * 100);
         if(prop_daily > 0 && weq < day_start - prop_daily / 100 * deposit) { halt = "prop_daily"; halt_t = t; break; }
         if(prop_max > 0 && weq < deposit * (1 - prop_max / 100)) { halt = "prop_max"; halt_t = t; break; }
         if(max_days > 0 && t - tl[0] > max_days * 86400LL) { halt = "timeout"; halt_t = t; break; }
         if(stop_on_halt)
         {
            for(auto& kv : st.gv) if(kv.first.size() > 5 && kv.first.compare(kv.first.size() - 5, 5, "_HALT") == 0) { halt = kv.second == 2 ? "target" : "maxloss"; break; }
            if(!halt.empty()) { halt_t = t; break; }
         }
      }
   }
   catch(const std::exception& e)
   {
      std::fprintf(stderr, "%s\n", e.what()); return 3;
   }
   std::fprintf(fd, "%s,%.2f,%.2f,%zu\n", TimeToString(day * 86400, TIME_DATE).c_str(), st.balance, eq_min, st.closed.size() - closed_mark);
   std::fclose(fd);
   P->OnDeinit(0);
   double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

   std::FILE* ft = std::fopen((out + "/trades.csv").c_str(), "w");
   std::fprintf(ft, "ticket,sym,magic,type,vol,t_open,open,sl0,t_close,close,profit,risk_money,R,reason,comment\n");
   for(auto& c : st.closed)
      std::fprintf(ft, "%lu,%s,%ld,%d,%.2f,%s,%.3f,%.3f,%s,%.3f,%.2f,%.2f,%.4f,%d,%s\n", c.ticket, c.sym.c_str(), c.magic, c.type, c.vol,
                   TimeToString(c.t_open, TIME_DATE | TIME_SECONDS).c_str(), c.open, c.sl0, TimeToString(c.t_close, TIME_DATE | TIME_SECONDS).c_str(), c.close,
                   c.profit, c.risk_money, c.risk_money > 0 ? c.profit / c.risk_money : 0.0, c.reason, c.comment.c_str());
   std::fclose(ft);
   std::FILE* fs = std::fopen((out + "/summary.json").c_str(), "w");
   std::fprintf(fs, "{\"from\": \"%s\", \"to\": \"%s\", \"end\": \"%s\", \"deposit\": %.2f, \"balance\": %.2f, \"equity\": %.2f, \"trades\": %zu, \"open_positions\": %zu, \"halt\": \"%s\", "
                "\"payouts\": %.2f, \"n_payouts\": %d, \"worst_daily_pct\": %.3f, \"worst_total_pct\": %.3f, \"seconds\": %.1f}\n",
                from_s.c_str(), to_s.c_str(), TimeToString(halt_t ? halt_t : st.now, TIME_DATE | TIME_MINUTES).c_str(), deposit, st.balance, sim::equity(), st.closed.size(), st.pos.size(), halt.c_str(),
                payouts, n_payouts, worst_daily, worst_total, secs);
   std::fclose(fs);
   std::printf("%s -> %s: saldo %.2f, %zu trade, fermo '%s', %.1f s\n", from_s.c_str(), TimeToString(halt_t ? halt_t : st.now, TIME_DATE).c_str(), st.balance, st.closed.size(), halt.c_str(), secs);
   return 0;
}
