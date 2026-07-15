//+------------------------------------------------------------------+
//| EA_GapFade.mq5 — Overnight Gap Fade Strategy                     |
//| Symbol: NSDQ+, SP+, DOW+ (index CFDs)                           |
//| Period: M15  |  Style: Mean Reversion (gap fade)                  |
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| Overnight gaps in equity indices revert toward previous close     |
//| within the first 2-4 hours of the session. Larger gaps (>0.5%)   |
//| show higher fill rates. DOWN gaps have stronger reversion than    |
//| UP gaps (asymmetric fear/overreaction).                           |
//|                                                                   |
//| MECHANISM:                                                        |
//| Pre-market news/events create price dislocation. Regular session  |
//| open brings full liquidity — institutional rebalancing and        |
//| buy-the-dip flow compress the gap. 52% of 1%+ gaps fill          |
//| within 4 hours (Zhu & Da, 2024).                                  |
//|                                                                   |
//| COUNTERPARTY: Overnight panic sellers, pre-market momentum        |
//| traders who push prices beyond fair value.                        |
//|                                                                   |
//| Max | 2026-04-11 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_GapFade v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 401101;    // Magic Number
input int      InpDeviation     = 50;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Gap Detection ==="
input double   InpMinGapPct     = 0.30;      // Min gap size (% of prev close)
input double   InpMaxGapPct     = 3.00;      // Max gap size (skip massive gaps/news)
input bool     InpFadeDown      = true;      // Fade gap-down (BUY)
input bool     InpFadeUp        = true;      // Fade gap-up (SELL)

input group "=== Session (Server Time UTC+2/+3) ==="
input int      InpPrevCloseH    = 22;        // Previous session close hour
input int      InpOpenDetectH   = 1;         // Gap detection hour (after midnight)
input int      InpEntryH        = 16;        // Entry hour (US market open ~9:30 ET)
input int      InpEntryM        = 30;        // Entry minute
input int      InpExitH         = 21;        // Time exit hour (end of US session)
input int      InpExitM         = 0;         // Time exit minute

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;      // Risk per trade (%)
input double   InpMaxLot        = 1.00;      // Max lot
input double   InpSL_Pct        = 0.50;      // SL distance as % of price
input double   InpTP_Mode       = 0;         // 0=gap fill, 1=fixed RR
input double   InpRR            = 1.5;       // Fixed R:R (if mode 1)
input double   InpDailyDDPct    = 3.0;       // Daily DD kill (%)

input group "=== VIX Proxy Filter ==="
input bool     InpUseVolFilter  = false;     // Use ATR volatility filter
input int      InpATRPeriod     = 14;        // ATR period (D1)
input double   InpMinATRMult    = 1.2;       // Min ATR relative to 20-day avg

input group "=== Day Filters ==="
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;     // Skip Friday (weekend risk)

input group "=== Datalog ==="
input bool     InpDatalog       = true;

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hATR_D1;
datetime       g_lastBar;
datetime       g_todayDate;
double         g_dayStartBal;
bool           g_tradedToday;
double         g_prevClose;       // Previous session close price
double         g_gapOpenPrice;    // Today's open price after gap
double         g_gapPct;          // Gap size in percent
int            g_gapDir;          // +1=gap up, -1=gap down, 0=no gap
bool           g_gapDetected;
int            g_logHandle;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[GapFade] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR_D1 = iATR(_Symbol, PERIOD_D1, InpATRPeriod);
   if(g_hATR_D1 == INVALID_HANDLE)
   { Print("[GapFade] FATAL: ATR D1 init failed"); return INIT_FAILED; }

   g_lastBar       = 0;
   g_todayDate     = 0;
   g_dayStartBal   = AccountInfoDouble(ACCOUNT_BALANCE);
   g_tradedToday   = false;
   g_prevClose     = 0;
   g_gapOpenPrice  = 0;
   g_gapPct        = 0;
   g_gapDir        = 0;
   g_gapDetected   = false;

   if(InpDatalog)
   {
      string fname = "GapFade_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Date","GapDir","GapPct","PrevClose","OpenPrice",
            "Signal","EntryPrice","SL","TP","Lot","ATR","SkipReason");
   }

   PrintFormat("[GapFade] Init OK: %s %s Magic=%d MinGap=%.2f%% MaxGap=%.2f%%",
               _Symbol, EnumToString(_Period), InpMagic, InpMinGapPct, InpMaxGapPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR_D1 != INVALID_HANDLE) IndicatorRelease(g_hATR_D1);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
}

//+------------------------------------------------------------------+
bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpTradeMon; case 2: return InpTradeTue;
      case 3: return InpTradeWed; case 4: return InpTradeThu;
      case 5: return InpTradeFri; default: return false;
   }
}

//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
double CalcLotSize(double slPoints)
{
   if(slPoints <= 0) return 0;
   double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmt  = balance * InpRiskPct / 100.0;
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double point    = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(tickSize == 0 || tickVal == 0 || point == 0) return 0;
   double pointVal = tickVal * point / tickSize;
   double lot = riskAmt / (slPoints * pointVal);
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lot = MathMax(lot, minLot);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, maxLot);
   if(lotStep > 0) lot = MathFloor(lot / lotStep) * lotStep;
   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));

   //--- Day reset
   if(today != g_todayDate)
   {
      g_todayDate    = today;
      g_tradedToday  = false;
      g_dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);
      g_gapDetected  = false;
      g_gapDir       = 0;
      g_gapPct       = 0;
      g_gapOpenPrice = 0;
   }

   //--- Manage time exit on open positions
   if(CountMyPositions() > 0)
   {
      if(dt.hour >= InpExitH && dt.min >= InpExitM)
      {
         for(int i = PositionsTotal()-1; i >= 0; i--)
         {
            ulong ticket = PositionGetTicket(i);
            if(ticket == 0) continue;
            if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
            if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
            g_trade.PositionClose(ticket);
            Print("[GapFade] Time exit");
         }
      }
      return;
   }

   if(g_tradedToday) return;

   //--- Phase 1: Capture previous close price
   // Use D1 bar[1] close as "previous session close"
   if(g_prevClose == 0)
   {
      double d1Close = iClose(_Symbol, PERIOD_D1, 1);
      if(d1Close > 0) g_prevClose = d1Close;
   }

   //--- Phase 2: Detect gap at session open
   // After midnight detection — compare current price to prev close
   if(!g_gapDetected && g_prevClose > 0 && dt.hour >= InpOpenDetectH && dt.hour < InpEntryH)
   {
      double open0 = iOpen(_Symbol, PERIOD_CURRENT, 0);
      if(open0 > 0 && g_prevClose > 0)
      {
         g_gapPct = (open0 - g_prevClose) / g_prevClose * 100.0;
         g_gapOpenPrice = open0;

         if(g_gapPct > InpMinGapPct)
         {
            g_gapDir = 1;  // Gap UP
            g_gapDetected = true;
         }
         else if(g_gapPct < -InpMinGapPct)
         {
            g_gapDir = -1; // Gap DOWN
            g_gapDetected = true;
         }

         // Check max gap
         if(g_gapDetected && MathAbs(g_gapPct) > InpMaxGapPct)
         {
            LogData(today, g_gapDir, g_gapPct, "SKIP", 0, 0, 0, 0, 0, "GAP_TOO_LARGE");
            g_tradedToday = true;
            return;
         }

         if(g_gapDetected)
            PrintFormat("[GapFade] Gap detected: %s %.2f%% PrevClose=%.2f Open=%.2f",
                        g_gapDir > 0 ? "UP" : "DOWN", g_gapPct, g_prevClose, g_gapOpenPrice);
      }
   }

   //--- Phase 3: Entry at US market open
   if(!g_gapDetected || g_gapDir == 0) return;
   if(!IsTradingDay(dt.day_of_week)) return;

   int nowMins = dt.hour * 60 + dt.min;
   int entryMins = InpEntryH * 60 + InpEntryM;
   if(nowMins < entryMins || nowMins > entryMins + 15) return; // 15-min entry window

   // Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Determine trade direction (FADE the gap)
   int signal = 0;
   if(g_gapDir == -1 && InpFadeDown) signal = 1;   // Gap down → BUY (fade)
   if(g_gapDir == 1 && InpFadeUp)    signal = -1;  // Gap up → SELL (fade)
   if(signal == 0) return;

   // VIX proxy filter (ATR regime)
   if(InpUseVolFilter)
   {
      double atr[];
      if(CopyBuffer(g_hATR_D1, 0, 1, 1, atr) < 1) return;

      // Get 20-day ATR average as proxy
      double atrArr[20];
      if(CopyBuffer(g_hATR_D1, 0, 1, 20, atrArr) < 20) return;

      double avgATR = 0;
      for(int i = 0; i < 20; i++) avgATR += atrArr[i];
      avgATR /= 20.0;

      if(avgATR > 0 && atr[0] < avgATR * InpMinATRMult)
      {
         LogData(today, g_gapDir, g_gapPct, "SKIP", 0, 0, 0, 0, atr[0], "LOW_VOL");
         g_tradedToday = true;
         return;
      }
   }

   // Calculate SL/TP
   double price, sl, tp;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   if(signal == 1) // BUY (fade gap-down)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl = NormalizeDouble(price * (1.0 - InpSL_Pct / 100.0), digits);

      if(InpTP_Mode == 0)
         tp = NormalizeDouble(g_prevClose, digits);  // TP = previous close (gap fill)
      else
         tp = NormalizeDouble(price + MathAbs(price - sl) * InpRR, digits);
   }
   else // SELL (fade gap-up)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl = NormalizeDouble(price * (1.0 + InpSL_Pct / 100.0), digits);

      if(InpTP_Mode == 0)
         tp = NormalizeDouble(g_prevClose, digits);
      else
         tp = NormalizeDouble(price - MathAbs(sl - price) * InpRR, digits);
   }

   // Validate TP direction
   if(signal == 1 && tp <= price)
   {
      LogData(today, g_gapDir, g_gapPct, "SKIP_BUY", price, sl, tp, 0, 0, "TP_BELOW_ENTRY");
      g_tradedToday = true;
      return;
   }
   if(signal == -1 && tp >= price)
   {
      LogData(today, g_gapDir, g_gapPct, "SKIP_SELL", price, sl, tp, 0, 0, "TP_ABOVE_ENTRY");
      g_tradedToday = true;
      return;
   }

   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0)
   {
      LogData(today, g_gapDir, g_gapPct, "SKIP", price, sl, tp, 0, 0, "LOT_ZERO");
      g_tradedToday = true;
      return;
   }

   // Execute
   ENUM_ORDER_TYPE orderType = (signal == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   string comment = StringFormat("GapFade|%.1f%%|%s", g_gapPct, g_gapDir > 0 ? "UP" : "DN");

   bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
   if(ok)
   {
      g_tradedToday = true;
      PrintFormat("[GapFade] %s %.2f @ %.2f SL=%.2f TP=%.2f Gap=%.2f%%",
                  signal > 0 ? "BUY" : "SELL", lot, price, sl, tp, g_gapPct);
      LogData(today, g_gapDir, g_gapPct, signal > 0 ? "BUY" : "SELL",
              price, sl, tp, lot, 0, "EXECUTED");
   }

   // Reset prev close for next day
   g_prevClose = 0;
}

//+------------------------------------------------------------------+
void LogData(datetime date, int gapDir, double gapPct, string sig,
             double price, double sl, double tp, double lot,
             double atr, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   FileWrite(g_logHandle,
      TimeToString(date, TIME_DATE),
      gapDir > 0 ? "UP" : "DOWN",
      DoubleToString(gapPct, 3),
      DoubleToString(g_prevClose, 2),
      DoubleToString(g_gapOpenPrice, 2),
      sig,
      DoubleToString(price, 2),
      DoubleToString(sl, 2),
      DoubleToString(tp, 2),
      DoubleToString(lot, 2),
      DoubleToString(atr, 2),
      reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
