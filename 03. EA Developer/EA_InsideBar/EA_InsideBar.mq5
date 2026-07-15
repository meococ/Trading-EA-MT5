//+------------------------------------------------------------------+
//| EA_InsideBar.mq5                                                   |
//| Inside Bar Breakout during Kill Zones                              |
//| v1.0 — Research prototype                                         |
//|                                                                    |
//| HYPOTHESIS: Inside bars (H < prev_H AND L > prev_L) represent    |
//| institutional compression/accumulation. When the NEXT bar breaks  |
//| out of the inside bar range during a KZ, it signals institutional |
//| direction. This is a DIFFERENT structural edge from:              |
//| - FVG (gap structure) or range breakout (session H/L)             |
//| - Inside bar = SINGLE CANDLE compression, not session range       |
//|                                                                    |
//| ENTRY: On M15, detect inside bar at shift=2. If shift=1 breaks   |
//| above/below the inside bar range → enter.                         |
//| With D1 trend bias and H4 EMA confirmation.                       |
//|                                                                    |
//| Expected frequency: Inside bars are common (~1-3/day on M15)      |
//| but KZ + trend filter reduces to viable count.                    |
//+------------------------------------------------------------------+
#property copyright "Max"
#property version   "1.10"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <ExecQualityLog.mqh>
#include <HolidayCalendar.mqh>
#include <PartialClose.mqh>

//+------------------------------------------------------------------+
//| INPUTS                                                             |
//+------------------------------------------------------------------+
input group "=== Core ==="
input bool   InpEnabled       = true;
input bool   InpKillSwitch    = false;   // Kill Switch - disable new trades (keeps DD guards)
input double InpRiskPct       = 1.0;
input int    InpMagic         = 20260391;
input string InpComment       = "IB1";

input group "=== Kill Zones (Broker GMT+2) ==="
input int    InpKZ1_Start     = 9;
input int    InpKZ1_End       = 12;
input int    InpKZ2_Start     = 15;
input int    InpKZ2_End       = 18;

input group "=== Inside Bar Detection ==="
input double InpMinIBRange    = 0.20;        // Min inside bar range (ATR×) — avoid tiny bars
input double InpMaxIBRange    = 0.80;        // Max inside bar range (ATR×) — avoid noisy bars
input double InpBreakBuffer   = 0.05;        // Break must exceed IB H/L by this (ATR×)
input double InpMinBreakBody  = 0.50;        // Break candle min body ratio

input group "=== HTF Bias ==="
input bool   InpUseBias       = true;
input int    InpH4_EMA        = 50;

input group "=== SL/TP ==="
input double InpSL_Buffer     = 0.20;        // SL buffer beyond IB opposite side (ATR×)
input double InpMinSL_Pips    = 5.0;
input double InpMaxSL_Pips    = 40.0;
input double InpTP_RR         = 1.50;

input group "=== Risk Management ==="
input int    InpMaxTradesPerDay = 2;
input double InpMaxSpreadPips   = 5.0;
input double InpMaxDailyDD_Pct  = 3.0;
input double InpMaxTotalDD_Pct  = 10.0;
input bool   InpSkipFriday      = true;
input bool   InpSkipMon         = false;     // Skip Monday
input bool   InpSkipTue         = false;     // Skip Tuesday
input bool   InpSkipWed         = false;     // Skip Wednesday
input bool   InpSkipThu         = false;     // Skip Thursday
input int    InpDeviation       = 30;
input int    InpSessionCloseHour = 21;   // Force close all positions at this hour
input int    InpSessionCloseMin  = 0;    // Force close minute

input group "=== Partial Close ==="
input bool   InpPartialClose    = false;   // Enable partial close at N×R
input double InpPCL_TriggerR    = 1.0;     // Partial close trigger (R multiple)
input double InpPCL_ClosePct    = 0.50;    // Fraction to close (0.50 = 50%)

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade        g_trade;
CPositionInfo g_pos;
CSymbolInfo   g_sym;

int    g_hATR, g_hH4EMA;
double g_pt, g_pipSize;

int    g_tradesToday;
datetime g_lastDay;
double g_dayStartEquity, g_peakEquity;
string g_tradeCsvFile;
bool   g_tradeCsvHeaderWritten;

//+------------------------------------------------------------------+
void IB_InitTradeCsv()
{
   FolderCreate("PaperDeploy", FILE_COMMON);
   FolderCreate("PaperDeploy/EA_InsideBar", FILE_COMMON);
   g_tradeCsvFile = "PaperDeploy/EA_InsideBar/trades_" + IntegerToString(InpMagic) + ".csv";
   g_tradeCsvHeaderWritten = FileIsExist(g_tradeCsvFile, FILE_COMMON);
}

//+------------------------------------------------------------------+
void IB_AppendTradeCsv(ulong deal)
{
   if(!HistoryDealSelect(deal)) return;
   if((long)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic) return;
   if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) return;

   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_INOUT) return;

   int handle = FileOpen(g_tradeCsvFile,
                         FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_COMMON,
                         ',');
   if(handle == INVALID_HANDLE) return;

   if(!g_tradeCsvHeaderWritten)
   {
      FileWrite(handle, "timestamp", "symbol", "magic", "direction", "profit", "comment");
      g_tradeCsvHeaderWritten = true;
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
             _Symbol,
             IntegerToString(InpMagic),
             direction,
             DoubleToString(profit, 2),
             comment);
   FileClose(handle);
}

//+------------------------------------------------------------------+
void IB_CloseTradeCsv()
{
   g_tradeCsvHeaderWritten = false;
}

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING DetectFillMode()
{
   long fm = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((fm & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
   if((fm & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}

int OnInit()
{
   //--- H1 timeframe enforcement
   if(Period() != PERIOD_H1)
   {
      PrintFormat("[IB] FATAL: Requires H1 timeframe, attached to %s. EA disabled.",
                  EnumToString(Period()));
      return INIT_FAILED;
   }

   //--- Input validation
   if(InpRiskPct <= 0 || InpRiskPct > 5.0)
   { Print("[IB] FATAL: InpRiskPct must be 0-5%"); return INIT_FAILED; }
   if(InpMagic <= 0)
   { Print("[IB] FATAL: InpMagic must be > 0"); return INIT_FAILED; }
   if(InpKZ1_Start >= InpKZ1_End || InpKZ2_Start >= InpKZ2_End)
   { Print("[IB] FATAL: KZ start must be < end"); return INIT_FAILED; }
   if(InpMinSL_Pips <= 0 || InpMaxSL_Pips <= 0 || InpMinSL_Pips >= InpMaxSL_Pips)
   { Print("[IB] FATAL: Invalid SL pip range"); return INIT_FAILED; }
   if(InpTP_RR <= 0)
   { Print("[IB] FATAL: InpTP_RR must be > 0"); return INIT_FAILED; }
   if(InpMaxTradesPerDay <= 0)
   { Print("[IB] FATAL: InpMaxTradesPerDay must be > 0"); return INIT_FAILED; }

   g_sym.Name(_Symbol);
   g_pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(digits <= 2)      g_pipSize = g_pt * 100.0;
   else if(digits == 3 || digits == 5) g_pipSize = g_pt * 10.0;
   else                 g_pipSize = g_pt;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(DetectFillMode());

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE) return INIT_FAILED;

   g_hH4EMA = INVALID_HANDLE;
   if(InpUseBias)
   {
      g_hH4EMA = iMA(_Symbol, PERIOD_H4, InpH4_EMA, 0, MODE_EMA, PRICE_CLOSE);
      if(g_hH4EMA == INVALID_HANDLE) return INIT_FAILED;
   }

   g_lastDay = 0;
   g_tradesToday = 0;
   g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   IB_InitTradeCsv();
   EQL_Init("EA_InsideBar", InpMagic, "IB1", g_pipSize, true);

   PrintFormat("[IB] EA_InsideBar v1.1 | %s H1 | Magic=%d | Risk=%.2f%% | Kill=%s | SessionClose=%02d:%02d",
              _Symbol, InpMagic, InpRiskPct,
              (InpKillSwitch ? "ON" : "OFF"),
              InpSessionCloseHour, InpSessionCloseMin);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   IB_CloseTradeCsv();
   if(g_hATR   != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hH4EMA != INVALID_HANDLE) IndicatorRelease(g_hH4EMA);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled) return;

   static datetime lastBar = 0;
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == lastBar) return;
   lastBar = barTime;

   if(Bars(_Symbol, PERIOD_CURRENT) < 50) return;

   MqlDateTime dt;
   TimeCurrent(dt);
   int hour = dt.hour;
   int min  = dt.min;
   int dow  = dt.day_of_week;

   // Day reset
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != g_lastDay)
   {
      g_lastDay = today;
      g_tradesToday = 0;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   }

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > g_peakEquity) g_peakEquity = equity;

   //--- Session-end force close (runs BEFORE any other logic)
   if(hour > InpSessionCloseHour || (hour == InpSessionCloseHour && min >= InpSessionCloseMin))
   {
      if(CountPos() > 0)
      {
         PrintFormat("[IB] SESSION CLOSE at %02d:%02d — flattening all positions", hour, min);
         CloseAll();
      }
      return;
   }

   //--- Partial close management (runs regardless of day filter / kill switch)
   if(InpPartialClose && CountPos() > 0)
   {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(!g_pos.SelectByIndex(i)) continue;
         if(g_pos.Magic() != InpMagic || g_pos.Symbol() != _Symbol) continue;

         bool isBuy = (g_pos.PositionType() == POSITION_TYPE_BUY);
         g_sym.RefreshRates();
         double curPx = isBuy ? g_sym.Bid() : g_sym.Ask();

         PCL_CheckPartialClose(g_trade, g_pos.Ticket(), isBuy,
                               g_pos.PriceOpen(), g_pos.StopLoss(), g_pos.TakeProfit(),
                               curPx, g_pos.Volume(), _Symbol,
                               InpPCL_TriggerR, InpPCL_ClosePct, "[IB]");
      }
   }

   if(dow == 0 || dow == 6) return;
   if(InpSkipFriday && dow == 5) return;
   if(InpSkipMon && dow == 1) return;
   if(InpSkipTue && dow == 2) return;
   if(InpSkipWed && dow == 3) return;
   if(InpSkipThu && dow == 4) return;

   // DD guards
   if(g_dayStartEquity > 0 && (g_dayStartEquity - equity) / g_dayStartEquity * 100.0 > InpMaxDailyDD_Pct)
   { CloseAll(); return; }
   if(g_peakEquity > 0 && (g_peakEquity - equity) / g_peakEquity * 100.0 > InpMaxTotalDD_Pct)
   { CloseAll(); return; }

   //--- Kill switch: block new entries, keep DD guards and session close active
   if(InpKillSwitch) return;
   if(IsMarketHoliday()) return;

   // KZ check
   bool inKZ = (hour >= InpKZ1_Start && hour < InpKZ1_End) ||
               (hour >= InpKZ2_Start && hour < InpKZ2_End);
   if(!inKZ) return;
   if(g_tradesToday >= InpMaxTradesPerDay) return;
   if(CountPos() > 0) return;

   // ATR
   double atrBuf[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atrBuf) < 1) return;
   double atr = atrBuf[0];
   if(atr <= 0) return;

   // === INSIDE BAR DETECTION ===
   // Bar[2] = inside bar candidate (its range fits WITHIN bar[3])
   double h2 = iHigh(_Symbol, PERIOD_CURRENT, 2);
   double l2 = iLow(_Symbol, PERIOD_CURRENT, 2);
   double h3 = iHigh(_Symbol, PERIOD_CURRENT, 3);
   double l3 = iLow(_Symbol, PERIOD_CURRENT, 3);

   // Inside bar: bar[2] range is INSIDE bar[3] range
   if(h2 >= h3 || l2 <= l3) return;  // Not inside bar

   double ibRange = h2 - l2;
   if(ibRange < InpMinIBRange * atr) return;   // Too tiny
   if(ibRange > InpMaxIBRange * atr) return;   // Too large/noisy

   // === BREAKOUT DETECTION ===
   // Bar[1] = breakout candle. Must break above h2 or below l2
   double h1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double l1 = iLow(_Symbol, PERIOD_CURRENT, 1);
   double c1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double o1 = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double body1 = MathAbs(c1 - o1);
   double range1 = h1 - l1;
   if(range1 <= 0) return;

   if(body1 / range1 < InpMinBreakBody) return;

   double breakBuf = InpBreakBuffer * atr;
   bool breakUp   = (c1 > h2 + breakBuf && c1 > o1);  // Close above IB high
   bool breakDown = (c1 < l2 - breakBuf && c1 < o1);  // Close below IB low

   if(!breakUp && !breakDown) return;

   // H4 EMA bias
   if(InpUseBias && g_hH4EMA != INVALID_HANDLE)
   {
      double emaBuf[];
      if(CopyBuffer(g_hH4EMA, 0, 1, 1, emaBuf) < 1) return;
      double h4Close = iClose(_Symbol, PERIOD_H4, 1);
      if(breakUp   && h4Close < emaBuf[0]) return;  // Only long in uptrend
      if(breakDown && h4Close > emaBuf[0]) return;  // Only short in downtrend
   }

   // Spread check
   g_sym.RefreshRates();
   double spreadPips = g_sym.Spread() * g_pt / g_pipSize;
   if(spreadPips > InpMaxSpreadPips)
   {
      PrintFormat("[IB] SKIP spread=%.1f > max=%.1f pips", spreadPips, InpMaxSpreadPips);
      return;
   }

   double entryPrice = breakUp ? g_sym.Ask() : g_sym.Bid();
   int dig = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   // SL beyond the opposite side of inside bar + buffer
   double slDist;
   if(breakUp)
      slDist = entryPrice - l2 + InpSL_Buffer * atr;  // SL below IB low
   else
      slDist = h2 - entryPrice + InpSL_Buffer * atr;  // SL above IB high

   double slPips = slDist / g_pipSize;
   if(slPips < InpMinSL_Pips) slDist = InpMinSL_Pips * g_pipSize;
   if(slPips > InpMaxSL_Pips)
   {
      PrintFormat("[IB] SKIP slPips=%.1f > max=%.1f", slPips, InpMaxSL_Pips);
      return;
   }

   double tpDist = slDist * InpTP_RR;

   double sl = breakUp ? NormalizeDouble(entryPrice - slDist, dig) :
                          NormalizeDouble(entryPrice + slDist, dig);
   double tp = breakUp ? NormalizeDouble(entryPrice + tpDist, dig) :
                          NormalizeDouble(entryPrice - tpDist, dig);

   long stopLevelPts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(MathAbs(entryPrice - sl) < (double)stopLevelPts * g_pt)
   {
      PrintFormat("[IB] SKIP stop level violation: need %d pts", (int)stopLevelPts);
      return;
   }

   // Sizing
   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPct / 100.0;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0)
   {
      Print("[IB] SKIP: tickValue or tickSize <= 0");
      return;
   }

   double lotRaw = riskMoney / (slDist / tickSize * tickValue);
   double lotMin  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotMax  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double lots = MathFloor(lotRaw / lotStep) * lotStep;
   lots = MathMax(lotMin, MathMin(lots, lotMax));

   //--- Execute with retry (3 attempts, exponential backoff)
   string kzLabel = (hour >= InpKZ1_Start && hour < InpKZ1_End) ? "LDN" : "NY";
   EQL_SetContext(entryPrice, spreadPips, kzLabel);
   bool filled = false;
   uint retcode = 0;

   for(int attempt = 1; attempt <= 3; attempt++)
   {
      bool ok = breakUp ? g_trade.Buy(lots, _Symbol, 0, sl, tp, InpComment) :
                           g_trade.Sell(lots, _Symbol, 0, sl, tp, InpComment);

      retcode = g_trade.ResultRetcode();

      if(ok && (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_PLACED))
      {
         EQL_RecordFill(retcode);
         filled = true;
         break;
      }

      //--- Non-transient error: stop retrying
      if(retcode != TRADE_RETCODE_REQUOTE &&
         retcode != TRADE_RETCODE_PRICE_OFF &&
         retcode != TRADE_RETCODE_TIMEOUT &&
         retcode != TRADE_RETCODE_CONNECTION)
      {
         PrintFormat("[IB] ORDER REJECTED attempt %d/3 — err=%d %s (non-transient)",
                     attempt, retcode, g_trade.ResultRetcodeDescription());
         break;
      }

      PrintFormat("[IB] RETRY %d/3 — err=%d %s",
                  attempt, retcode, g_trade.ResultRetcodeDescription());
      EQL_RecordRetry(retcode);
      if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
   }

   if(filled)
   {
      g_tradesToday++;
      PrintFormat("[IB] ENTRY %s @ %s | lots=%.2f | SL=%s | TP=%s | IB: %s-%s | Mother: %s-%s",
                  breakUp ? "BUY" : "SELL",
                  DoubleToString(g_trade.ResultPrice(), dig),
                  lots,
                  DoubleToString(sl, dig), DoubleToString(tp, dig),
                  DoubleToString(l2, dig), DoubleToString(h2, dig),
                  DoubleToString(l3, dig), DoubleToString(h3, dig));
   }
   else
   {
      PrintFormat("[IB] ORDER FAILED FINAL — retcode=%d %s | %s @ %s | lots=%.2f | spread=%.1f pips",
                  retcode, g_trade.ResultRetcodeDescription(),
                  breakUp ? "BUY" : "SELL",
                  DoubleToString(entryPrice, dig),
                  lots, spreadPips);
   }
}

//+------------------------------------------------------------------+
int CountPos()
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(g_pos.SelectByIndex(i))
         if(g_pos.Magic() == InpMagic && g_pos.Symbol() == _Symbol) c++;
   return c;
}

void CloseAll()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i)) continue;
      if(g_pos.Magic() != InpMagic || g_pos.Symbol() != _Symbol) continue;

      ulong ticket = g_pos.Ticket();
      bool closed = false;
      for(int attempt = 1; attempt <= 3; attempt++)
      {
         if(g_trade.PositionClose(ticket))
         {
            uint rc = g_trade.ResultRetcode();
            if(rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED)
            {
               PrintFormat("[IB] Closed #%I64u OK", ticket);
               closed = true;
               break;
            }
         }
         PrintFormat("[IB] CLOSE RETRY %d/3 #%I64u — err=%d %s",
                     attempt, ticket,
                     g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
         if(attempt < 3) Sleep(200);
      }
      if(!closed)
         PrintFormat("[IB] CLOSE FAILED #%I64u after 3 attempts", ticket);
   }
}

//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   ulong deal = trans.deal;
   if(deal == 0) return;
   IB_AppendTradeCsv(deal);
   EQL_OnDeal(deal);
}
//+------------------------------------------------------------------+
