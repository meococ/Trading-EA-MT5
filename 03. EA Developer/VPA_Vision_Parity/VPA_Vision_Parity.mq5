//+------------------------------------------------------------------+
//|                                          VPA_Vision_Parity.mq5   |
//|  T-VPA-VIS-1 parity harness (script).                            |
//|                                                                  |
//|  Rebuilds the DR3 detector view over a fixed M5 window and writes |
//|  three CSVs so the Python side (PLAN/vis1/compare_parity.py) can  |
//|  diff the two implementations bar for bar:                        |
//|                                                                  |
//|    MQL5\Files\<InpFolder>\VPA_Vision_bars.csv                     |
//|    MQL5\Files\<InpFolder>\VPA_Vision_events.csv                   |
//|    MQL5\Files\<InpFolder>\VPA_Vision_barriers.csv                 |
//|                                                                  |
//|  The bars CSV holds the exact closed bars the detector consumed,  |
//|  so the comparator re-runs the frozen Python detector on the SAME |
//|  series: any diff is a logic diff, never a data diff.             |
//|                                                                  |
//|  VISUAL/FORENSIC ONLY: this script cannot place orders.           |
//|  Run it once, on any EURUSD M5 chart, in the same terminal whose  |
//|  M5 history you want to compare.                                  |
//+------------------------------------------------------------------+
#property copyright "Trading-EA-MT5 / T-VPA-VIS-1"
#property version   "1.00"
#property script_show_inputs
#property description "Exports VPA_Vision DR3 detections for the parity diff (EURUSD M5 by default)."

#include "../VPA_Vision/VPA_Core.mqh"

input string          InpSymbol    = "";                 // empty = chart symbol
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M5;          // detector is M5-frozen
input string          InpFrom      = "2019.02.01 00:00"; // window start (server time)
input string          InpTo        = "2019.04.01 00:00"; // window end (server time)
input string          InpFolder    = "vis1";             // MQL5\Files\<folder>
input string          InpPrefix    = "VPA_Vision";       // CSV basename

void OnStart()
  {
   string sym=(StringLen(InpSymbol)>0) ? InpSymbol : _Symbol;
   datetime t0=StringToTime(InpFrom);
   datetime t1=StringToTime(InpTo);
   if(t0<=0 || t1<=0 || t1<=t0)
     {
      Print("VPA_Vision_Parity: invalid window '",InpFrom,"' .. '",InpTo,"'");
      return;
     }
   string msg="";
   if(VpaExportWindow(sym,InpTimeframe,t0,t1,InpFolder,InpPrefix,msg))
      Print("VPA_Vision_Parity OK: ",msg);
   else
      Print("VPA_Vision_Parity FAILED: ",msg);
   Print("Folder: ",TerminalInfoString(TERMINAL_DATA_PATH),"\\MQL5\\Files\\",InpFolder);
  }
