//+------------------------------------------------------------------+
//| CBR_Datalog.mqh — CSV Trade Logging                              |
//+------------------------------------------------------------------+
#ifndef CBR_DATALOG_MQH
#define CBR_DATALOG_MQH

#include "CBR_Config.mqh"
#include "CBR_Types.mqh"

//--- Global log handle
int g_cbrLogHandle = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Open CSV log file                                                 |
//+------------------------------------------------------------------+
bool CBR_InitDatalog(string symbol)
{
   string fname = CBR_EA_NAME + "_" + symbol + "_signals.csv";
   g_cbrLogHandle = FileOpen(fname, FILE_WRITE | FILE_CSV | FILE_ANSI, '\t');
   if(g_cbrLogHandle == INVALID_HANDLE)
   {
      PrintFormat("[CBR] WARN: Cannot open log file: %s", fname);
      return false;
   }

   // Header
   FileWrite(g_cbrLogHandle,
      "DateTime", "BarTime", "KillZone", "Direction",
      "BodyRatio", "CloseLoc", "BarRangeATR", "BBW_Pct",
      "Bias", "EMA_Fast", "EMA_Slow", "ATR",
      "SL_Pts", "RR", "Result", "RejectReason");

   return true;
}

//+------------------------------------------------------------------+
//| Log a signal (both valid and rejected)                           |
//+------------------------------------------------------------------+
void CBR_LogSignal(CBR_Signal &sig, bool executed)
{
   if(g_cbrLogHandle == INVALID_HANDLE) return;

   string dir = "NONE";
   if(sig.valid)
      dir = (sig.type == ORDER_TYPE_BUY) ? "BUY" : "SELL";

   string result = "REJECT";
   if(sig.valid && executed) result = "EXECUTED";
   if(sig.valid && !executed) result = "BLOCKED";

   FileWrite(g_cbrLogHandle,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES),
      TimeToString(iTime(_Symbol, PERIOD_CURRENT, 1), TIME_DATE | TIME_MINUTES),
      CBR_KillZoneName(sig.killZone),
      dir,
      DoubleToString(sig.bodyRatio, 3),
      DoubleToString(sig.closeLoc, 3),
      DoubleToString(sig.barRangeAtr, 3),
      DoubleToString(sig.bbwPctile, 1),
      IntegerToString(sig.bias),
      DoubleToString(sig.emaFast, 2),
      DoubleToString(sig.emaSlow, 2),
      DoubleToString(sig.atr / g_cbrPt, 1),
      DoubleToString(sig.slPts, 0),
      DoubleToString(sig.rrRatio, 1),
      result,
      sig.rejectReason);
}

//+------------------------------------------------------------------+
//| Close log file                                                    |
//+------------------------------------------------------------------+
void CBR_DeinitDatalog()
{
   if(g_cbrLogHandle != INVALID_HANDLE)
   {
      FileClose(g_cbrLogHandle);
      g_cbrLogHandle = INVALID_HANDLE;
   }
}

#endif // CBR_DATALOG_MQH
