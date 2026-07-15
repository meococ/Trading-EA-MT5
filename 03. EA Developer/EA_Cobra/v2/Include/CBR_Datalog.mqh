//+------------------------------------------------------------------+
//| CBR_Datalog.mqh — CSV Trade Logging (v2)                         |
//| Updated: includes level type + entry mode columns                 |
//+------------------------------------------------------------------+
#ifndef CBR_DATALOG_MQH
#define CBR_DATALOG_MQH

#include "CBR_Config.mqh"
#include "CBR_Types.mqh"
#include "CBR_SessionTime.mqh"

int    g_cbrLogHandle = INVALID_HANDLE;
string g_cbrTradeCsvFile = "";
bool   g_cbrTradeCsvHeaderWritten = false;

//+------------------------------------------------------------------+
void CBR_InitTradeCsv(ulong magic)
{
   g_cbrTradeCsvFile = "PaperDeploy/EA_Cobra/trades_" + IntegerToString((int)magic) + ".csv";
   g_cbrTradeCsvHeaderWritten = FileIsExist(g_cbrTradeCsvFile, FILE_COMMON);
}

//+------------------------------------------------------------------+
void CBR_AppendTradeCsv(ulong deal, ulong magic, string symbol)
{
   if(!HistoryDealSelect(deal)) return;
   if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != magic) return;
   if(HistoryDealGetString(deal, DEAL_SYMBOL) != symbol) return;

   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_INOUT) return;

   int handle = FileOpen(g_cbrTradeCsvFile,
                         FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_COMMON,
                         ',');
   if(handle == INVALID_HANDLE) return;

   if(!g_cbrTradeCsvHeaderWritten)
   {
      FileWrite(handle, "timestamp", "symbol", "magic", "direction", "profit", "comment");
      g_cbrTradeCsvHeaderWritten = true;
   }
   FileSeek(handle, 0, SEEK_END);

   long dealType = HistoryDealGetInteger(deal, DEAL_TYPE);
   string direction = (dealType == DEAL_TYPE_BUY || dealType == DEAL_TYPE_BUY_CANCELED) ? "buy" : "sell";
   double profit = HistoryDealGetDouble(deal, DEAL_PROFIT)
                 + HistoryDealGetDouble(deal, DEAL_SWAP)
                 + HistoryDealGetDouble(deal, DEAL_COMMISSION);
   string comment = HistoryDealGetString(deal, DEAL_COMMENT);
   datetime t = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);

   FileWrite(handle,
             TimeToString(t, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
             symbol,
             IntegerToString((int)magic),
             direction,
             DoubleToString(profit, 2),
             comment);
   FileClose(handle);
}

//+------------------------------------------------------------------+
void CBR_CloseTradeCsv()
{
   g_cbrTradeCsvFile = "";
   g_cbrTradeCsvHeaderWritten = false;
}

//+------------------------------------------------------------------+

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

   FileWrite(g_cbrLogHandle,
      "DateTime", "BarTime", "KillZone", "EntryMode", "LevelType",
      "LevelPrice", "LevelDist", "Direction",
      "BodyRatio", "CloseLoc", "BarRangeATR", "BBW_Pct",
      "Bias", "EMA_Fast", "EMA_Slow", "ATR",
      "SL_Pts", "RR", "Result", "RejectReason");

   return true;
}

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
      CBR_EntryModeName(sig.entryMode),
      CBR_LevelTypeName(sig.levelType),
      DoubleToString(sig.levelPrice, 2),
      DoubleToString(sig.levelDist, 0),
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
void CBR_DeinitDatalog()
{
   if(g_cbrLogHandle != INVALID_HANDLE)
   {
      FileClose(g_cbrLogHandle);
      g_cbrLogHandle = INVALID_HANDLE;
   }
}

#endif // CBR_DATALOG_MQH
