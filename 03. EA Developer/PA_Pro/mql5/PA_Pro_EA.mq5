//+------------------------------------------------------------------+
//|                                                    PA_Pro_EA.mq5 |
//|  PA-PRO causal zone-perception EA - the Owner mandate lane.      |
//|                                                                  |
//|  HARD WALL: SIGNAL_ONLY defaults true - the EA draws and logs    |
//|  signals but sends no orders.  Only the Owner flips it.  The     |
//|  single order path is PaExecutePlan() in PA_Trade.mqh, gated on  |
//|  InpSignalOnly as its first statement; mql5/tests/               |
//|  test_signal_only.py proves no order API is reachable otherwise. |
//|                                                                  |
//|  Event-driven: the engine steps exactly once per CLOSED M5 bar.  |
//|  Per-bar pipeline (mirrors sf_ctx.run_pass + pa_fill.simulate):  |
//|    StepBar -> zone export -> setup Detect -> entry veto ->       |
//|    session window -> risk lock -> plan build -> journal -> draw  |
//+------------------------------------------------------------------+
#property strict
#property version   "0.20"
#property description "PA-PRO zone perception EA (SIGNAL_ONLY mandate)"
#property copyright "PA-PRO lane"

#include "PA_Types.mqh"
#include "PA_Clock.mqh"
#include "PA_Zones.mqh"
#include "PA_Session.mqh"
#include "PA_Risk.mqh"
#include "PA_Trade.mqh"
#include "PA_Setups.mqh"
#include "PA_Journal.mqh"
#include "PA_Visual.mqh"
#include "PA_Export.mqh"
#include "PA_SelfTest.mqh"

//--- inputs ------------------------------------------------------------
input group "Master"
input bool   InpSignalOnly   = true;      // SIGNAL_ONLY: draw+log, no orders
input bool   InpDrawZones    = true;      // draw armed zones on chart
input bool   InpJournal      = true;      // CSV journal to MQL5\Files
input bool   InpSelfTest     = false;     // run golden-vector self test, then stop
input group "Perception"
input bool   InpGenLine1     = true;      // line1_cluster
input bool   InpGenFractal   = true;      // fractal_h1
input bool   InpGenKde       = true;      // kde_swing
input bool   InpGenProfile   = true;      // profile_va
input bool   InpGenSdBase    = true;      // sd_base
input bool   InpGenRefs      = true;      // ref_levels
input int    InpArmTopK      = 0;         // SF02 hook: top-k armed per side
                                         // by salience (0 = off, parity)
input int    InpSalienceMode = 0;         // SF02 score: 0=strength (parity),
                                         // 1=AUTOPSY_PLAN A3 a-priori formula
input group "Setups (stub modules - Setup Factory survivors drop in)"
input bool   InpSetupF1      = true;      // f1_zone_rejection stub
input bool   InpSetupF2      = true;      // f2_break_retest stub
input group "Order plan (pa_fill DEFAULT_SPEC)"
input double InpBufPips      = 1.0;       // stop entry beyond signal bar
input int    InpVBars        = 3;         // pending-order expiry, M5 bars
input double InpSPips        = 8.0;       // fallback SL when no structure
input double InpTpMult       = 2.0;       // TP = tp_mult x SL distance
input double InpSlPadPips    = 0.5;       // structural SL padding
input double InpMaxSpreadPips= 3.0;       // spread guard (0 = off)
input group "Risk (all fractions of equity)"
input double InpRiskFrac     = 0.005;     // 0.5% per trade
input double InpDailyLock    = 0.04;      // daily-loss lock 4%
input double InpDdLock       = 0.08;      // max-drawdown lock 8%
input group "Session / flats (pa_fill DEFAULT_SPEC)"
input bool   InpSessEU       = true;      // EU window 05:00-11:00 UTC
input bool   InpSessUS       = true;      // US window 11:30-17:30 UTC
input int    InpFlatDailyH   = 22;        // daily flat, server hour
input int    InpFlatFridayH  = 20;        // Friday flat, server hour
input bool   InpWeekendVeto  = true;      // no new signals Sat/Sun server
input group "Parity export (EA writes zone CSV for comparator)"
input bool   InpExportZones  = false;     // export armed zones per bar to CSV
input int    InpExportFrom   = 0;         // first M5 bar index
input int    InpExportTo     = 0;         // last M5 bar index (0=all loaded)
input string InpExportFolder = "PA_Pro";  // folder under MQL5\Files

//--- engine state ------------------------------------------------------
CPaPerception g_pa;
CPaSession    g_sess;
CPaRisk       g_risk;
CPaTrade      g_trade;
CPaSetups     g_setups;
CPaJournal    g_jnl;
CPaVisual     g_vis;
CPaExport     g_exp;
int           g_bars_loaded = 0;
long          g_last_pushed = 0;      // epoch of the newest bar in ctx.b
string        g_last_sig    = "";
int           g_last_live_t = -1;         // newest stepped bar

//+------------------------------------------------------------------+
//| load the closed M5 history into PaBar[] (ascending time)          |
//+------------------------------------------------------------------+
int PaLoadM5(const string sym,const int max_bars,PaBar &out[])
  {
   MqlRates r[];
   int got=CopyRates(sym,PERIOD_M5,1,max_bars,r);   // shift 1: CLOSED bars only
   if(got<=0)
      return(0);
   ArraySetAsSeries(r,true);              // r[0] = newest
   int n=got;
   ArrayResize(out,n);
   for(int i=0;i<n;i++)
     {
      PaBar b;
      b.t=(long)r[n-1-i].time;
      b.o=r[n-1-i].open;
      b.h=r[n-1-i].high;
      b.l=r[n-1-i].low;
      b.c=r[n-1-i].close;
      PaBarClock(b,300);
      out[i]=b;
     }
   return(n);
  }

//+------------------------------------------------------------------+
//| one-bar pipeline: step -> export -> detect -> veto -> plan ->     |
//| journal.  `live` also draws and touches the gated execute path.   |
//+------------------------------------------------------------------+
void PaProcessBar(const int t,const bool live)
  {
   g_pa.StepBar(t);
   g_last_live_t=t;
   //--- parity export: armed views of this bar
   if(g_exp.fh!=INVALID_HANDLE &&
      t>=InpExportFrom && (InpExportTo<=0 || t<=InpExportTo))
      g_exp.BarZones(g_pa,t);
   //--- setup detection on the closed bar
   PaSetupSignal sig;
   if(!g_setups.Detect(t,sig))
      return;                             // no signal -> nothing more
   const PaBar b=g_pa.ctx.b[t];
   string status="";
   string order_type="stop";
   //--- entry vetoes (pa_fill.py:196-215 order)
   int veto=g_sess.EntryVeto(b.t);
   if(!g_pa.ctx.AtrOk(t))
      { status="VETO_WARMUP"; veto=PA_VETO_WARMUP; }
   else if(veto!=PA_VETO_NONE)
      status=PaVetoName(veto);
   else if(!g_sess.InSessionUtcMin(b.utc_min))
      status="VETO_SESSION";
   else if(live && g_risk.Locked())
      status="RISK_LOCK";
   PaPlan plan;
   double entry=0,sl=0,tp=0;
   if(status=="")
     {
      double spread_pips=0.0;
      if(live)
         spread_pips=(double)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)
                     *_Point/PaPipSize(_Symbol);
      if(g_trade.BuildStop(b,t,sig.side,sig.zone_lo,sig.zone_hi,
                           sig.zid,sig.tag,spread_pips,plan))
        {
         status="SIGNAL";
         entry=plan.entry; sl=plan.sl; tp=plan.tp;
         if(live)
            plan.lots=g_risk.Lots(_Symbol,MathAbs(plan.entry-plan.sl),
                                  AccountInfoDouble(ACCOUNT_EQUITY));
        }
      else
         status=(plan.reason=="")?"NO_PLAN":plan.reason;
     }
   g_last_sig=StringFormat("t%d %s %s %s",t,sig.tag,
                           (sig.side>0)?"BUY":"SELL",status);
   //--- pa_fill veto rows carry only {sig,side,tag,symbol,status} — the
   //--- reason column stays empty so the journal shape matches Python
   g_jnl.Signal(t,b.t,sig.side,sig.tag,_Symbol,status,
                (status=="SIGNAL")?order_type:"",
                entry,sl,tp,"");
   if(live)
     {
      if(status=="SIGNAL")
        {
         g_vis.DrawPlan(plan,_Symbol);
         //--- gated execution: InpSignalOnly is the ONLY flag ever passed
         PaExecutePlan(plan,InpSignalOnly,_Symbol,"PAP "+sig.tag);
        }
      else
         g_vis.DrawSkip(b.t,b.c,status);
     }
  }

//+------------------------------------------------------------------+
//| draw the overlay for the newest stepped bar                       |
//+------------------------------------------------------------------+
void PaDraw(const int t)
  {
   if(!InpDrawZones || t<0)
      return;
   ObjectsDeleteAll(0,PA_OBJ_PREFIX "Z"); // zones only - plans accumulate
   g_vis.DrawZones(g_pa,t,12);
   int live=0,armed=0;
   PaZoneView vv[];
   for(int g=0;g<PA_GEN_COUNT;g++)
      if(g_pa.gen[g]!=NULL)
        {
         live+=ArraySize(g_pa.gen[g].m_live);
         armed+=g_pa.ViewsAt(g,t,true,vv);
        }
   g_vis.DrawHud(t,live,armed,g_last_sig,g_risk.LockReason());
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   //--- session policy from inputs
   g_sess.eu_on=InpSessEU;
   g_sess.us_on=InpSessUS;
   g_sess.daily_flat_hour=InpFlatDailyH;
   g_sess.friday_flat_hour=InpFlatFridayH;
   g_sess.weekend_veto=InpWeekendVeto;
   g_sess.legacy_flats=false;          // hard-wired off (R00 Thursday bug)
   if(InpSelfTest)
     {
      int fail=PaRunClockSelfTest(g_sess);
      //--- incremental PushBar vs batch Init on real M5 history
      PaBar tb[];
      int tn=PaLoadM5(_Symbol,8000,tb);
      int fail2=(tn>2500)?PaRunCtxSelfTest(tb,tn,tn-1500):-1;
      //--- zone-level: same engine, Init(k0)+PushBar vs Init(n) stepped
      int fail3=(tn>1500)?PaRunZoneSelfTest(tb,tn,tn-720):-1;
      PrintFormat("PA-PRO SELFTEST: clock %d vectors/%d failures; "
                  "ctx incremental %d mismatches; zones incremental %d "
                  "mismatches -> %s",
                  PA_NV,fail,fail2,fail3,
                  (fail==0 && fail2==0 && fail3==0)?"PASS":"FAIL");
      return(INIT_FAILED);            // self-test mode never trades
     }
   //--- trade plan knobs
   g_trade.pip=PaPipSize(_Symbol);
   g_trade.buf_pips=InpBufPips;
   g_trade.v_bars=InpVBars;
   g_trade.s_pips=InpSPips;
   g_trade.tp_mult=InpTpMult;
   g_trade.sl_pad_pips=InpSlPadPips;
   g_trade.max_spread_pips=InpMaxSpreadPips;
   //--- risk knobs
   g_risk.risk_frac=InpRiskFrac;
   g_risk.daily_lock=InpDailyLock;
   g_risk.dd_lock=InpDdLock;
   //--- generator switches
   bool gen_on[PA_GEN_COUNT];
   gen_on[PA_GEN_LINE1]  =InpGenLine1;
   gen_on[PA_GEN_FRACTAL]=InpGenFractal;
   gen_on[PA_GEN_KDE]    =InpGenKde;
   gen_on[PA_GEN_PROFILE]=InpGenProfile;
   gen_on[PA_GEN_SD_BASE]=InpGenSdBase;
   gen_on[PA_GEN_REFS]   =InpGenRefs;
   //--- load history + build the perception engine
   PaBar bars[];
   g_bars_loaded=PaLoadM5(_Symbol,100000,bars);
   if(g_bars_loaded<=0)
     {
      Print("PA-PRO: no M5 history for ",_Symbol);
      return(INIT_FAILED);
     }
   if(!g_pa.Init(bars,g_bars_loaded,PaPipSize(_Symbol),_Symbol,gen_on))
      return(INIT_FAILED);
   //--- SF02 salience hook (LEAD R1): per-side top-k arming, off by default
   for(int g=0;g<PA_GEN_COUNT;g++)
      if(g_pa.gen[g]!=NULL)
        {
         g_pa.gen[g].cfg_arm_topk=InpArmTopK;
         g_pa.gen[g].cfg_salience_mode=InpSalienceMode;
        }
   //--- setup modules bound to the engine + session policy
   if(InpSetupF1)
     {
      CPaSetupF1 *m=new CPaSetupF1();
      m.Bind(GetPointer(g_pa),GetPointer(g_sess));
      g_setups.Add(m);
     }
   if(InpSetupF2)
     {
      CPaSetupF2 *m=new CPaSetupF2();
      m.Bind(GetPointer(g_pa),GetPointer(g_sess));
      g_setups.Add(m);
     }
   //--- journal + parity export
   if(InpJournal)
      g_jnl.Open(InpExportFolder,"pa_journal.csv");
   if(InpExportZones)
      g_exp.Open(InpExportFolder,"zones_"+_Symbol+".csv");
   //--- step all loaded history (every loaded bar is closed)
   int last=g_bars_loaded-1;
   for(int t=0;t<=last;t++)
      PaProcessBar(t,false);
   g_last_pushed=g_pa.ctx.b[last].t;
   PaDraw(last);
   g_jnl.Flush();
   g_exp.Close();                      // export covers the loaded window only
   PrintFormat("PA-PRO: %d M5 bars loaded, engine stepped to %d, "
               "journal rows=%d, export rows=%d",
               g_bars_loaded,last,g_jnl.rows,g_exp.rows);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   //--- push EVERY closed M5 bar newer than the last processed (catch-up
   //--- covers bars that closed while OnInit was still stepping history)
   MqlRates r[];
   int got=CopyRates(_Symbol,PERIOD_M5,1,16,r);   // closed, newest first
   if(got<=0)
      return;
   for(int i=got-1;i>=0;i--)                       // oldest -> newest
     {
      if((long)r[i].time<=g_last_pushed)
         continue;
      PaBar b;
      b.t=(long)r[i].time; b.o=r[i].open; b.h=r[i].high;
      b.l=r[i].low;        b.c=r[i].close;
      PaBarClock(b,300);
      //--- causal extension: H1 buckets / ATRs / h1_idx / pivot watermarks
      int n=g_pa.ctx.PushBar(b);
      g_last_pushed=b.t;
      //--- risk bookkeeping on live bars only (equity is meaningless in the
      //--- history replay loop)
      g_risk.Roll(b.t,AccountInfoDouble(ACCOUNT_EQUITY));
      PaProcessBar(n,true);
      PaDraw(n);
     }
   g_jnl.Flush();
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   g_jnl.Close();
   g_exp.Close();
   g_vis.Wipe();
  }
//+------------------------------------------------------------------+
