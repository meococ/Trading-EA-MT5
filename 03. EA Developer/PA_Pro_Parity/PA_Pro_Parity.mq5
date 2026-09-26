//+------------------------------------------------------------------+
//|                                                PA_Pro_Parity.mq5 |
//|  PA-PRO parity script - headless zone exporter.                  |
//|                                                                  |
//|  Compile:  alpha.ps1 compile "PA_Pro_Parity"                     |
//|  Run:      drop on a chart (or run in the Strategy Tester as a   |
//|            script) -> loads M5 history, steps the SAME zone      |
//|            engine the EA uses (PA_Zones.mqh), writes armed-view  |
//|            CSV rows to MQL5\Files\<InpFolder>\zones_<sym>.csv    |
//|            (FILE_COMMON -> <Terminal>\Common\Files\...).         |
//|                                                                  |
//|  Compare with mql5/parity/compare_parity.py against              |
//|  mql5/parity/out/zones_<sym>_py.csv (export_zones.py).           |
//|                                                                  |
//|  HARD WALL: this script never trades - it contains no order,     |
//|  position or trade call.  The gate in PA_Trade.mqh is not even   |
//|  included here.                                                  |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property script_show_inputs

#include "..\PA_Pro\mql5\PA_Types.mqh"
#include "..\PA_Pro\mql5\PA_Clock.mqh"
#include "..\PA_Pro\mql5\PA_Zones.mqh"
#include "..\PA_Pro\mql5\PA_Export.mqh"

input int    InpMaxBars   = 100000;   // M5 bars to load (CopyRates)
input int    InpExportFrom= 0;        // first bar index to export
input int    InpExportTo  = 0;        // last bar index (0 = all)
input string InpFolder    = "PA_Pro"; // folder under MQL5\Files
input int    InpArmTopK   = 0;        // SF02 hook; MUST stay 0 for parity
input int    InpSalienceMode = 0;     // SF02 score; MUST stay 0 for parity

int PaParityLoad(const string sym,const int max_bars,PaBar &out[])
  {
   MqlRates r[];
   int got=CopyRates(sym,PERIOD_M5,1,max_bars,r);   // shift 1: CLOSED bars only
   if(got<=0)
      return(0);
   ArraySetAsSeries(r,true);
   ArrayResize(out,got);
   for(int i=0;i<got;i++)
     {
      PaBar b;
      b.t=(long)r[got-1-i].time;
      b.o=r[got-1-i].open;
      b.h=r[got-1-i].high;
      b.l=r[got-1-i].low;
      b.c=r[got-1-i].close;
      PaBarClock(b,300);
      out[i]=b;
     }
   return(got);
  }

void OnStart()
  {
   PaBar bars[];
   int n=PaParityLoad(_Symbol,InpMaxBars,bars);
   if(n<=0)
     {
      Print("PA-PARITY: no M5 history for ",_Symbol);
      return;
     }
   bool gen_on[PA_GEN_COUNT];
   for(int i=0;i<PA_GEN_COUNT;i++)
      gen_on[i]=true;
   CPaPerception pa;
   if(!pa.Init(bars,n,PaPipSize(_Symbol),_Symbol,gen_on))
     {
      Print("PA-PARITY: engine init failed");
      return;
     }
   for(int g=0;g<PA_GEN_COUNT;g++)
      if(pa.gen[g]!=NULL)
        {
         pa.gen[g].cfg_arm_topk=InpArmTopK;
         pa.gen[g].cfg_salience_mode=InpSalienceMode;
        }
   CPaExport exp;
   if(!exp.Open(InpFolder,"zones_"+_Symbol+".csv"))
      return;
   int last=n-1;                       // all loaded bars are closed
   int hi=(InpExportTo>0)?MathMin(InpExportTo,last):last;
   for(int t=0;t<=last;t++)
     {
      pa.StepBar(t);
      if(t>=InpExportFrom && t<=hi)
         exp.BarZones(pa,t);
     }
   exp.Close();
   PrintFormat("PA-PARITY: %d bars stepped, export rows=%d -> %s\\zones_%s.csv",
               n,exp.rows,InpFolder,_Symbol);
  }
//+------------------------------------------------------------------+
