//+------------------------------------------------------------------+
//| ParityDump.mq5 — dump iATR/iADX/iRSI closed-bar values to CSV    |
//| Harness utility (no trading, no strategy). Runs as a chart       |
//| Script via [StartUp] config; writes to MQL5\Files on the         |
//| portable data root, then closes the terminal.                    |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int InpBars      = 30000; // closed bars to dump (from bar 1)
input int InpAtrPeriod = 14;
input int InpAdxPeriod = 14;
input int InpRsiPeriod = 14;

bool WaitReady(const int handle, const int need)
  {
   for(int k = 0; k < 600; k++)
     {
      if(BarsCalculated(handle) >= need)
         return true;
      Sleep(100);
     }
   return false;
  }

void OnStart()
  {
   const int have = Bars(_Symbol, _Period);
   int count = MathMin(InpBars, have - 2);
   if(count < 100)
     {
      Print("ParityDump: not enough bars: ", have);
      TerminalClose(1);
      return;
     }

   int hAtr = iATR(_Symbol, _Period, InpAtrPeriod);
   int hAdx = iADX(_Symbol, _Period, InpAdxPeriod);
   int hRsi = iRSI(_Symbol, _Period, InpRsiPeriod, PRICE_CLOSE);
   if(hAtr == INVALID_HANDLE || hAdx == INVALID_HANDLE || hRsi == INVALID_HANDLE)
     {
      Print("ParityDump: handle failure");
      TerminalClose(1);
      return;
     }
   if(!WaitReady(hAtr, count) || !WaitReady(hAdx, count) || !WaitReady(hRsi, count))
     {
      Print("ParityDump: indicators not ready");
      TerminalClose(1);
      return;
     }

   MqlRates rates[];
   double atr[], adx[], rsi[];
   // start=1 -> closed bars only (bar 0 is forming)
   if(CopyRates(_Symbol, _Period, 1, count, rates) != count ||
      CopyBuffer(hAtr, 0, 1, count, atr) != count ||
      CopyBuffer(hAdx, 0, 1, count, adx) != count ||
      CopyBuffer(hRsi, 0, 1, count, rsi) != count)
     {
      Print("ParityDump: copy failure");
      TerminalClose(1);
      return;
     }
   ArraySetAsSeries(rates, true);
   ArraySetAsSeries(atr, true);
   ArraySetAsSeries(adx, true);
   ArraySetAsSeries(rsi, true);

   string name = StringFormat("parity_dump_%s_%s.csv", _Symbol, EnumToString(_Period));
   int fh = FileOpen(name, FILE_WRITE | FILE_ANSI);
   if(fh == INVALID_HANDLE)
     {
      Print("ParityDump: file open failed: ", GetLastError());
      TerminalClose(1);
      return;
     }
   FileWriteString(fh, "time,close,atr,adx,rsi\r\n");
   for(int i = count - 1; i >= 0; i--) // oldest first
      FileWriteString(fh, StringFormat("%I64d,%.10f,%.10f,%.10f,%.10f\r\n",
                      (long)rates[i].time, rates[i].close, atr[i], adx[i], rsi[i]));
   FileClose(fh);
   Print("ParityDump: wrote ", count, " rows to ", name);
   TerminalClose(0);
  }
//+------------------------------------------------------------------+
