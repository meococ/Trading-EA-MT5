//+------------------------------------------------------------------+
//| IB_Module.mqh — Inside Bar Breakout Module for EA_Portfolio      |
//| Extracted from EA_InsideBar v1.10                                |
//| Dual-symbol capable: each instance uses its own IB_State struct  |
//|                                                                  |
//| EDGE: Inside bar (single-candle compression) during Kill Zones   |
//| + H4 EMA bias. Breakout of IB range = institutional direction.   |
//|                                                                  |
//| DEPLOYED ON: USDJPY H1 (magic A) and GBPUSD H1 (magic B)        |
//| Day filters passed in by master EA:                              |
//|   USDJPY  → skipMon=false, skipWed=false                         |
//|   GBPUSD  → skipMon=true,  skipWed=true                          |
//|                                                                  |
//| All per-instance state lives in IB_State (NO module globals).    |
//| Max | 2026-04-01                                                 |
//+------------------------------------------------------------------+
#ifndef IB_MODULE_MQH
#define IB_MODULE_MQH

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include "Portfolio_Common.mqh"

//+------------------------------------------------------------------+
//| Compile-time parameters (shared across both instances)           |
//+------------------------------------------------------------------+

// Kill Zones (broker GMT+2 / GMT+3 DST)
#define IB_KZ1_START       9
#define IB_KZ1_END        12
#define IB_KZ2_START      15
#define IB_KZ2_END        18

// Inside bar detection
#define IB_MIN_IB_RANGE   0.20   // Min IB range as ATR multiple
#define IB_MAX_IB_RANGE   0.80   // Max IB range as ATR multiple
#define IB_BREAK_BUFFER   0.05   // Breakout must exceed IB H/L by this ATR multiple
#define IB_MIN_BREAK_BODY 0.50   // Breakout candle min body/range ratio

// HTF bias
#define IB_USE_BIAS       true
#define IB_H4_EMA_PERIOD  50

// SL/TP
#define IB_SL_BUFFER      0.20   // SL buffer beyond IB opposite side (ATR×)
#define IB_MIN_SL_PIPS    5.0
#define IB_MAX_SL_PIPS    40.0
#define IB_TP_RR          1.50

// Risk management
#define IB_MAX_TRADES_DAY 2
#define IB_MAX_SPREAD_PIPS 5.0
#define IB_MAX_DAILY_DD   3.0    // % daily drawdown limit
#define IB_MAX_TOTAL_DD   10.0   // % total drawdown limit (from peak)
#define IB_SKIP_FRIDAY    true

// Session
#define IB_SESSION_CLOSE_HOUR 21
#define IB_SESSION_CLOSE_MIN   0

//+------------------------------------------------------------------+
//| Per-instance state — one per symbol (USDJPY / GBPUSD)            |
//+------------------------------------------------------------------+
struct IB_State
{
   // Bar tracking (new-bar gate)
   datetime lastBar;

   // Daily trade counter
   int      todayTrades;
   datetime todayDate;

   // Drawdown tracking
   double   dayStartEquity;
   double   peakEquity;

   // Indicator handles (per-symbol)
   int      hATR;       // ATR(14) on H1
   int      hH4EMA;     // EMA(50) on H4

   // Trade execution object (per-symbol magic)
   CTrade   trade;

   // Cached symbol properties (set at init)
   double   pt;         // SYMBOL_POINT
   double   pipSize;    // 1 pip in price units

   // Module tag for logging
   string   tag;        // e.g. "[IB-UJ]" or "[IB-GU]"
};

//+------------------------------------------------------------------+
//| Internal helpers                                                  |
//+------------------------------------------------------------------+
int IB_CountPositions(const string symbol, ulong magic)
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != magic) continue;
      if(PositionGetString(POSITION_SYMBOL) != symbol) continue;
      c++;
   }
   return c;
}

void IB_CloseAll(IB_State &state, const string symbol)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != state.trade.RequestMagic()) continue;
      if(PositionGetString(POSITION_SYMBOL) != symbol) continue;

      bool closed = false;
      for(int attempt = 1; attempt <= 3; attempt++)
      {
         if(state.trade.PositionClose(ticket))
         {
            uint rc = state.trade.ResultRetcode();
            if(rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED)
            {
               PrintFormat("%s Closed #%I64u OK", state.tag, ticket);
               closed = true;
               break;
            }
         }
         PrintFormat("%s CLOSE RETRY %d/3 #%I64u — err=%d %s",
                     state.tag, attempt, ticket,
                     state.trade.ResultRetcode(),
                     state.trade.ResultRetcodeDescription());
         if(attempt < 3) Sleep(200);
      }
      if(!closed)
         PrintFormat("%s CLOSE FAILED #%I64u after 3 attempts", state.tag, ticket);
   }
}

//+------------------------------------------------------------------+
//| IB_Init — call once per symbol instance from OnInit              |
//| Returns true if initialisation succeeded.                        |
//+------------------------------------------------------------------+
bool IB_Init(IB_State &state, const string symbol, ulong magic, int deviation)
{
   string logTag = StringFormat("[IB-%s]", StringSubstr(symbol, 0, 2));
   state.tag = logTag;

   // Point and pip size
   state.pt = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(state.pt <= 0)
   {
      PrintFormat("%s INIT FAILED: SYMBOL_POINT=0 for %s", logTag, symbol);
      return false;
   }
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(digits <= 2)
      state.pipSize = state.pt * 100.0;   // gold / JPY 2-digit
   else if(digits == 3 || digits == 5)
      state.pipSize = state.pt * 10.0;    // standard forex
   else
      state.pipSize = state.pt;

   // ATR handle — explicitly H1
   state.hATR = iATR(symbol, PERIOD_H1, 14);
   if(state.hATR == INVALID_HANDLE)
   {
      PrintFormat("%s INIT FAILED: iATR handle invalid for %s", logTag, symbol);
      return false;
   }

   // H4 EMA handle
   state.hH4EMA = INVALID_HANDLE;
   if(IB_USE_BIAS)
   {
      state.hH4EMA = iMA(symbol, PERIOD_H4, IB_H4_EMA_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
      if(state.hH4EMA == INVALID_HANDLE)
      {
         PrintFormat("%s INIT FAILED: iMA H4 EMA handle invalid for %s", logTag, symbol);
         return false;
      }
   }

   // Trade object
   PF_SetupTrade(state.trade, magic, symbol, deviation);

   // State reset
   state.lastBar       = 0;
   state.todayTrades   = 0;
   state.todayDate     = 0;
   state.dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   state.peakEquity    = state.dayStartEquity;

   PrintFormat("%s IB_Init OK | symbol=%s magic=%I64u risk=from-master | ATR=%d H4EMA=%d",
               logTag, symbol, magic, state.hATR, state.hH4EMA);
   return true;
}

//+------------------------------------------------------------------+
//| IB_Deinit — release indicator handles                            |
//+------------------------------------------------------------------+
void IB_Deinit(IB_State &state)
{
   if(state.hATR   != INVALID_HANDLE) { IndicatorRelease(state.hATR);   state.hATR   = INVALID_HANDLE; }
   if(state.hH4EMA != INVALID_HANDLE) { IndicatorRelease(state.hH4EMA); state.hH4EMA = INVALID_HANDLE; }
}

//+------------------------------------------------------------------+
//| IB_OnTick — call on every tick from master EA OnTick             |
//|                                                                  |
//| Parameters:                                                      |
//|   state    — per-symbol IB_State (modified in place)            |
//|   symbol   — trading symbol for this instance                    |
//|   magic    — magic number for this instance                      |
//|   riskPct  — risk % per trade (from master, per-symbol)         |
//|   maxLot   — hard lot cap                                        |
//|   skipMon  — skip Monday trades (GBPUSD=true, USDJPY=false)     |
//|   skipWed  — skip Wednesday trades (GBPUSD=true, USDJPY=false)  |
//+------------------------------------------------------------------+
void IB_OnTick(IB_State &state,
               const string symbol,
               ulong        magic,
               double       riskPct,
               double       maxLot,
               bool         skipMon,
               bool         skipWed)
{
   // ---------------------------------------------------------------
   // 1. New-bar gate (H1 closed-bar logic, PERIOD_H1 explicit)
   // ---------------------------------------------------------------
   datetime barTime = iTime(symbol, PERIOD_H1, 0);
   if(barTime == 0 || barTime == state.lastBar) return;
   state.lastBar = barTime;

   if(Bars(symbol, PERIOD_H1) < 50) return;

   // ---------------------------------------------------------------
   // 2. Time context
   // ---------------------------------------------------------------
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int hour = dt.hour;
   int min_ = dt.min;
   int dow  = dt.day_of_week;

   // ---------------------------------------------------------------
   // 3. Daily reset
   // ---------------------------------------------------------------
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != state.todayDate)
   {
      state.todayDate     = today;
      state.todayTrades   = 0;
      state.dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   }

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > state.peakEquity) state.peakEquity = equity;

   // ---------------------------------------------------------------
   // 4. Session-end force close (runs BEFORE day/DD filter)
   // ---------------------------------------------------------------
   if(hour > IB_SESSION_CLOSE_HOUR ||
      (hour == IB_SESSION_CLOSE_HOUR && min_ >= IB_SESSION_CLOSE_MIN))
   {
      if(IB_CountPositions(symbol, magic) > 0)
      {
         PrintFormat("%s SESSION CLOSE at %02d:%02d — flattening", state.tag, hour, min_);
         IB_CloseAll(state, symbol);
      }
      return;
   }

   // ---------------------------------------------------------------
   // 5. Weekend / day-of-week filter
   // ---------------------------------------------------------------
   if(dow == 0 || dow == 6) return;
   if(IB_SKIP_FRIDAY && dow == 5) return;
   if(skipMon && dow == 1) return;
   // skipTue / skipThu not used by either symbol, kept as false
   if(skipWed && dow == 3) return;

   // ---------------------------------------------------------------
   // 6. Drawdown guards
   // ---------------------------------------------------------------
   if(state.dayStartEquity > 0)
   {
      double dailyDD = (state.dayStartEquity - equity) / state.dayStartEquity * 100.0;
      if(dailyDD > IB_MAX_DAILY_DD)
      {
         PrintFormat("%s DAILY DD GUARD %.2f%% > %.2f%% — closing", state.tag, dailyDD, IB_MAX_DAILY_DD);
         IB_CloseAll(state, symbol);
         return;
      }
   }
   if(state.peakEquity > 0)
   {
      double totalDD = (state.peakEquity - equity) / state.peakEquity * 100.0;
      if(totalDD > IB_MAX_TOTAL_DD)
      {
         PrintFormat("%s TOTAL DD GUARD %.2f%% > %.2f%% — closing", state.tag, totalDD, IB_MAX_TOTAL_DD);
         IB_CloseAll(state, symbol);
         return;
      }
   }

   // ---------------------------------------------------------------
   // 7. Entry gates
   // ---------------------------------------------------------------
   bool inKZ = (hour >= IB_KZ1_START && hour < IB_KZ1_END) ||
               (hour >= IB_KZ2_START && hour < IB_KZ2_END);
   if(!inKZ) return;
   if(state.todayTrades >= IB_MAX_TRADES_DAY) return;
   if(IB_CountPositions(symbol, magic) > 0) return;   // Max 1 open

   // ---------------------------------------------------------------
   // 8. ATR (H1, shift=1 — closed bar)
   // ---------------------------------------------------------------
   double atrBuf[];
   ArraySetAsSeries(atrBuf, true);
   if(CopyBuffer(state.hATR, 0, 1, 1, atrBuf) < 1) return;
   double atr = atrBuf[0];
   if(atr <= 0) return;

   // ---------------------------------------------------------------
   // 9. Inside bar detection
   //    bar[2] = inside bar candidate (range inside bar[3])
   //    bar[3] = mother bar
   // ---------------------------------------------------------------
   double h2 = iHigh(symbol,  PERIOD_H1, 2);
   double l2 = iLow(symbol,   PERIOD_H1, 2);
   double h3 = iHigh(symbol,  PERIOD_H1, 3);
   double l3 = iLow(symbol,   PERIOD_H1, 3);

   if(h2 <= 0 || l2 <= 0 || h3 <= 0 || l3 <= 0) return;

   // Strict inside: bar[2] H/L fully inside bar[3] H/L
   if(h2 >= h3 || l2 <= l3) return;

   double ibRange = h2 - l2;
   if(ibRange < IB_MIN_IB_RANGE * atr) return;   // Too tiny — noise
   if(ibRange > IB_MAX_IB_RANGE * atr) return;   // Too large — no compression

   // ---------------------------------------------------------------
   // 10. Breakout detection
   //     bar[1] = breakout candle (fully closed)
   // ---------------------------------------------------------------
   double h1 = iHigh(symbol,  PERIOD_H1, 1);
   double l1 = iLow(symbol,   PERIOD_H1, 1);
   double c1 = iClose(symbol, PERIOD_H1, 1);
   double o1 = iOpen(symbol,  PERIOD_H1, 1);
   if(h1 <= 0 || l1 <= 0) return;

   double body1  = MathAbs(c1 - o1);
   double range1 = h1 - l1;
   if(range1 <= 0) return;

   // Breakout candle must have meaningful body (directional close)
   if(body1 / range1 < IB_MIN_BREAK_BODY) return;

   double breakBuf  = IB_BREAK_BUFFER * atr;
   bool   breakUp   = (c1 > h2 + breakBuf && c1 > o1);
   bool   breakDown = (c1 < l2 - breakBuf && c1 < o1);

   if(!breakUp && !breakDown) return;

   // ---------------------------------------------------------------
   // 11. H4 EMA bias filter
   // ---------------------------------------------------------------
   if(IB_USE_BIAS && state.hH4EMA != INVALID_HANDLE)
   {
      double emaBuf[];
      ArraySetAsSeries(emaBuf, true);
      if(CopyBuffer(state.hH4EMA, 0, 1, 1, emaBuf) < 1) return;
      double h4Close = iClose(symbol, PERIOD_H4, 1);
      if(h4Close <= 0) return;

      if(breakUp   && h4Close < emaBuf[0]) return;   // Only long above EMA
      if(breakDown && h4Close > emaBuf[0]) return;   // Only short below EMA
   }

   // ---------------------------------------------------------------
   // 12. Spread guard
   // ---------------------------------------------------------------
   double ask       = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid       = SymbolInfoDouble(symbol, SYMBOL_BID);
   double spreadPts = ask - bid;
   double spreadPips = spreadPts / state.pipSize;
   if(spreadPips > IB_MAX_SPREAD_PIPS)
   {
      PrintFormat("%s SKIP spread=%.1f > max=%.1f pips", state.tag, spreadPips, IB_MAX_SPREAD_PIPS);
      return;
   }

   // ---------------------------------------------------------------
   // 13. SL / TP calculation
   // ---------------------------------------------------------------
   int    dig        = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double entryPrice = breakUp ? ask : bid;

   double slDist;
   if(breakUp)
      slDist = entryPrice - l2 + IB_SL_BUFFER * atr;   // SL below IB low
   else
      slDist = h2 - entryPrice + IB_SL_BUFFER * atr;   // SL above IB high

   double slPips = slDist / state.pipSize;
   if(slPips < IB_MIN_SL_PIPS) slDist = IB_MIN_SL_PIPS * state.pipSize;
   if(slPips > IB_MAX_SL_PIPS)
   {
      PrintFormat("%s SKIP slPips=%.1f > max=%.1f", state.tag, slPips, IB_MAX_SL_PIPS);
      return;
   }

   double tpDist = slDist * IB_TP_RR;

   double sl = breakUp ? NormalizeDouble(entryPrice - slDist, dig)
                       : NormalizeDouble(entryPrice + slDist, dig);
   double tp = breakUp ? NormalizeDouble(entryPrice + tpDist, dig)
                       : NormalizeDouble(entryPrice - tpDist, dig);

   // Stop level check
   long   stopLevelPts = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minStopDist  = (double)stopLevelPts * state.pt;
   if(MathAbs(entryPrice - sl) < minStopDist)
   {
      PrintFormat("%s SKIP stop level violation: need %d pts", state.tag, (int)stopLevelPts);
      return;
   }

   // ---------------------------------------------------------------
   // 14. Lot sizing (equity-based, consistent with Portfolio_Common)
   // ---------------------------------------------------------------
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0)
   {
      PrintFormat("%s SKIP: tickValue or tickSize invalid", state.tag);
      return;
   }

   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * riskPct / 100.0;
   double lotRaw    = riskMoney / (slDist / tickSize * tickValue);
   double lotMin    = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double lotMaxS   = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lotStep   = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double lots      = MathFloor(lotRaw / lotStep) * lotStep;
   lots = MathMax(lotMin, MathMin(lots, MathMin(lotMaxS, maxLot)));

   if(lots <= 0)
   {
      PrintFormat("%s SKIP: lots=0 after sizing", state.tag);
      return;
   }

   // ---------------------------------------------------------------
   // 15. Execute with retry (3 attempts, exponential backoff)
   // ---------------------------------------------------------------
   string kzLabel = (hour >= IB_KZ1_START && hour < IB_KZ1_END) ? "LDN" : "NY";
   bool   filled  = false;
   uint   retcode = 0;

   for(int attempt = 1; attempt <= 3; attempt++)
   {
      bool ok = breakUp
         ? state.trade.Buy(lots, symbol, 0, sl, tp, StringFormat("IB-%s", kzLabel))
         : state.trade.Sell(lots, symbol, 0, sl, tp, StringFormat("IB-%s", kzLabel));

      retcode = state.trade.ResultRetcode();

      if(ok && (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_PLACED))
      {
         filled = true;
         break;
      }

      // Non-transient error — stop immediately
      if(retcode != TRADE_RETCODE_REQUOTE &&
         retcode != TRADE_RETCODE_PRICE_OFF &&
         retcode != TRADE_RETCODE_TIMEOUT &&
         retcode != TRADE_RETCODE_CONNECTION)
      {
         PrintFormat("%s ORDER REJECTED attempt %d/3 — err=%d %s (non-transient)",
                     state.tag, attempt, retcode,
                     state.trade.ResultRetcodeDescription());
         break;
      }

      PrintFormat("%s RETRY %d/3 — err=%d %s",
                  state.tag, attempt, retcode,
                  state.trade.ResultRetcodeDescription());
      if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
   }

   // ---------------------------------------------------------------
   // 16. Post-fill logging
   // ---------------------------------------------------------------
   if(filled)
   {
      state.todayTrades++;
      PrintFormat("%s ENTRY %s @ %s | lots=%.2f | SL=%s | TP=%s | "
                  "IB: %s-%s | Mother: %s-%s | spread=%.1f pips | KZ=%s | trades_today=%d",
                  state.tag,
                  breakUp ? "BUY" : "SELL",
                  DoubleToString(state.trade.ResultPrice(), dig),
                  lots,
                  DoubleToString(sl, dig), DoubleToString(tp, dig),
                  DoubleToString(l2, dig), DoubleToString(h2, dig),
                  DoubleToString(l3, dig), DoubleToString(h3, dig),
                  spreadPips, kzLabel, state.todayTrades);
   }
   else
   {
      PrintFormat("%s ORDER FAILED FINAL — retcode=%d %s | %s @ %s | lots=%.2f | spread=%.1f pips",
                  state.tag,
                  retcode, state.trade.ResultRetcodeDescription(),
                  breakUp ? "BUY" : "SELL",
                  DoubleToString(entryPrice, dig),
                  lots, spreadPips);
   }
}

#endif // IB_MODULE_MQH
//+------------------------------------------------------------------+
