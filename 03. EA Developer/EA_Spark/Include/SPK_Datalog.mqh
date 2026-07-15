//+------------------------------------------------------------------+
//| SPK_Datalog.mqh - Signal/Trade logging for AlphaFactory          |
//+------------------------------------------------------------------+
#ifndef SPK_DATALOG_MQH
#define SPK_DATALOG_MQH

int g_hSignalLog = INVALID_HANDLE;

//+------------------------------------------------------------------+
void SPK_OpenLogs(bool enabled, long magic)
{
   if(!enabled) return;
   string folder = "EA_Spark";
   string sigFile = folder + "/signals_" + IntegerToString(magic) + ".csv";
   g_hSignalLog = FileOpen(sigFile, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ, ',');
   if(g_hSignalLog != INVALID_HANDLE)
      FileWrite(g_hSignalLog,
         "Time","Session","Accepted","SkipReason",
         "Dir","AsianHi","AsianLo","RangePts","ATR",
         "Spread","BodyRatio","TrendBias");
}

//+------------------------------------------------------------------+
void SPK_CloseLogs()
{
   if(g_hSignalLog != INVALID_HANDLE)
   {
      FileClose(g_hSignalLog);
      g_hSignalLog = INVALID_HANDLE;
   }
}

//+------------------------------------------------------------------+
void SPK_LogSignal(datetime time, string session,
                   bool accepted, string skipReason,
                   int direction, double asianHi, double asianLo,
                   double rangePts, double atr, int spread,
                   double bodyRatio, int trendBias)
{
   if(g_hSignalLog == INVALID_HANDLE) return;
   FileWrite(g_hSignalLog,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      session,
      (accepted ? "1" : "0"), skipReason,
      IntegerToString(direction),
      DoubleToString(asianHi, _Digits),
      DoubleToString(asianLo, _Digits),
      DoubleToString(rangePts, 1),
      DoubleToString(atr, _Digits),
      IntegerToString(spread),
      DoubleToString(bodyRatio, 3),
      IntegerToString(trendBias));
}

#endif
