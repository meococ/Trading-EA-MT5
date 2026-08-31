//+------------------------------------------------------------------+
//| EA_ICTVisualEdge.mq5                                              |
//| Real-tick MT5 cross-check of the offline visual-discovery probe.  |
//| Generous M5 sweep-reversion, closed-bar (shift>=1), 2R, one       |
//| position at a time, broker-side SL/TP + time exit. Lean research  |
//| scaffold: measures REAL-spread economics of the killed object.    |
//| NOT promotion-ready.                                              |
//+------------------------------------------------------------------+
#property copyright "EA_ICTVisualEdge research cross-check"
#property version   "1.00"
#property strict
#property description "Generous M5 sweep, closed-bar, 2R, one-position. Real-tick cost validation of HYP-ICTVIS-EURUSD-M5-001 offline KILL."

#include <Trade\Trade.mqh>

input long   InpMagic          = 26071801;
input string InpComment        = "ICTVis";
input int    InpSweepLookback  = 12;      // matches offline probe
input double InpStopBufferPips  = 2.0;    // beyond swept extreme
input double InpTargetR         = 2.0;
input int    InpMaxHoldBars     = 48;     // M5 bars
input double InpLot             = 0.10;   // fixed lot (PF is lot-invariant)
input bool   InpBothDirections  = true;

CTrade   trade;
datetime g_last_bar = 0;
datetime g_entry_bar_time = 0;

double PipSize()
{
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return (dg == 3 || dg == 5) ? pt * 10.0 : pt;
}

int OpenCount()
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         c++;
   }
   return c;
}

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

// Dump every closed deal to CSV for offline-probe parity comparison.
void OnDeinit(const int reason)
{
   HistorySelect(0, TimeCurrent());
   int total = HistoryDealsTotal();
   int fh = FileOpen("ictvis_deals.csv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(fh == INVALID_HANDLE) { Print("CSV open failed ", GetLastError()); return; }
   FileWrite(fh, "deal_time","type","entry_exit","price","volume","profit","commission","swap","comment");
   for(int i = 0; i < total; i++)
   {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0) continue;
      if(HistoryDealGetInteger(tk, DEAL_MAGIC) != InpMagic) continue;
      FileWrite(fh,
         (long)HistoryDealGetInteger(tk, DEAL_TIME),
         (long)HistoryDealGetInteger(tk, DEAL_TYPE),
         (long)HistoryDealGetInteger(tk, DEAL_ENTRY),
         HistoryDealGetDouble(tk, DEAL_PRICE),
         HistoryDealGetDouble(tk, DEAL_VOLUME),
         HistoryDealGetDouble(tk, DEAL_PROFIT),
         HistoryDealGetDouble(tk, DEAL_COMMISSION),
         HistoryDealGetDouble(tk, DEAL_SWAP),
         HistoryDealGetString(tk, DEAL_COMMENT));
   }
   FileClose(fh);
   Print("Dumped ", total, " deals to common/ictvis_deals.csv");
}

// Manage time-based exit of the single open position.
void ManageOpen()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      datetime opent = (datetime)PositionGetInteger(POSITION_TIME);
      int bars = iBarShift(_Symbol, PERIOD_M5, opent) ; // bars since entry
      if(bars >= InpMaxHoldBars)
         trade.PositionClose(tk);
   }
}

void OnTick()
{
   // act once per new closed M5 bar
   datetime t0 = iTime(_Symbol, PERIOD_M5, 0);
   if(t0 == g_last_bar) { ManageOpen(); return; }
   g_last_bar = t0;

   ManageOpen();
   if(OpenCount() > 0) return;               // one position at a time

   int need = InpSweepLookback + 2;
   if(Bars(_Symbol, PERIOD_M5) < need + 2) return;

   // signal bar = shift 1 (last closed). prior window = shift 2..(1+lookback)
   double sigHigh = iHigh(_Symbol, PERIOD_M5, 1);
   double sigLow  = iLow (_Symbol, PERIOD_M5, 1);
   double sigClose= iClose(_Symbol, PERIOD_M5, 1);
   double priorLow = DBL_MAX, priorHigh = -DBL_MAX;
   for(int s = 2; s <= 1 + InpSweepLookback; s++)
   {
      double h = iHigh(_Symbol, PERIOD_M5, s);
      double l = iLow (_Symbol, PERIOD_M5, s);
      if(h > priorHigh) priorHigh = h;
      if(l < priorLow)  priorLow  = l;
   }

   double pip = PipSize();
   int    dir = 0;
   double swept = 0.0;
   if(sigLow < priorLow && sigClose > priorLow)        { dir = 1;  swept = sigLow;  }   // long sweep+reclaim
   else if(InpBothDirections && sigHigh > priorHigh && sigClose < priorHigh) { dir = -1; swept = sigHigh; }

   if(dir == 0) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (dir > 0) ? ask : bid;
   double stop  = swept - dir * InpStopBufferPips * pip;
   double risk  = MathAbs(entry - stop);
   if(risk <= pip * 0.5) return;             // degenerate
   double tp    = entry + dir * InpTargetR * risk;

   int dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   stop = NormalizeDouble(stop, dg);
   tp   = NormalizeDouble(tp, dg);

   if(dir > 0) trade.Buy (InpLot, _Symbol, 0.0, stop, tp, InpComment);
   else        trade.Sell(InpLot, _Symbol, 0.0, stop, tp, InpComment);
}
