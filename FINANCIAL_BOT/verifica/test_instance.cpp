// prova: un secondo FINANCIAL_BOT sullo stesso conto non deve partire; dopo la rimozione del primo si'
#include "FINANCIAL_BOT.run.hpp"
int main()
{
   auto& st = sim::S(); st.tester = false; st.quiet = true; st.keep_prints = true; st.files_dir = "."; st.now = 1767225600;  // 2026-01-01
   sim::Symbol n; n.name = "US100.cash"; MqlRates r{}; r.time = st.now - 60; r.open = r.high = r.low = r.close = 25000; n.m1.push_back(r); st.syms.push_back(n);
   sim::advance(st.now); sim::deposit(100000);
   MQLProgram* a = new MQLProgram(); int ra = a->OnInit(); a->OnTick();
   st.chart_id = 999; MQLProgram* b = new MQLProgram(); int rb = b->OnInit();
   st.chart_id = 132456789012345678L; a->OnDeinit(0); st.chart_id = 999; MQLProgram* c = new MQLProgram(); int rc = c->OnInit();
   st.chart_id = 132456789012345678L; st.now += 3600; MQLProgram* d = new MQLProgram(); st.chart_id = 5; int rd = d->OnInit();  // il terzo e' vivo da <15 s? no: e' passato 1 h senza battito
   std::printf("primo %d (atteso 0), secondo %d (atteso 1), dopo rimozione %d (atteso 0), battito scaduto %d (atteso 0)\n", ra, rb, rc, rd);
   for(auto& p : st.prints) std::printf("  %s\n", p.c_str());
   return (ra == 0 && rb == 1 && rc == 0 && rd == 0) ? 0 : 1;
}
