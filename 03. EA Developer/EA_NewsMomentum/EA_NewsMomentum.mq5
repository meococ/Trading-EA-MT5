//+------------------------------------------------------------------+
//| EA_NewsMomentum.mq5                                              |
//| Post-event momentum on scheduled macro releases                 |
//| Reads news_events.csv from Files/                               |
//| S703 baseline test                                               |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Inputs: Signal
input string   InpEventsFile    = "news_events.csv";  // CSV file in Files/
input double   InpMinMovePips   = 15.0;   // Min event-bar move (pips) to trigger
input int      InpPostBars      = 1;      // Bars after event to enter (1=next bar)
input string   InpEventTypes    = "NonFarm Payrolls,CPI,FOMC Rate Decision,BOJ Rate Decision,GDP,Core PCE Price Index"; // Event types to trade

//--- Inputs: Risk
input double   InpRiskPct       = 0.5;    // Risk per trade (% of balance)
input double   InpRR            = 2.0;    // Reward:Risk ratio
input double   InpMaxSpreadPips = 5.0;    // Max spread allowed (pips)
input int      InpMaxBarHold    = 8;      // Max bars to hold (M15 = 2 hours)

//--- Inputs: Filters
input bool     InpTradeNFP      = true;   // Trade NFP
input bool     InpTradeCPI      = true;   // Trade CPI
input bool     InpTradeFOMC     = true;   // Trade FOMC
input bool     InpTradeBOJ      = false;  // Trade BOJ (disabled by default - small effect)
input bool     InpTradeGDP      = true;   // Trade GDP
input bool     InpTradePCE      = true;   // Trade Core PCE
input int      InpMaxTradesDay  = 1;      // Max trades per day
input double   InpMaxDDPct      = 3.0;    // Daily drawdown kill switch (%)

//--- Inputs: EA
input int      InpMagic         = 703001; // Magic number
input int      InpSlippage      = 20;     // Max slippage (points)

//--- Structures
struct NewsEvent
{
   datetime time;
   string   event_type;
   string   currency;
   int      importance;
};

//--- Globals
CTrade         m_trade;
CPositionInfo  m_pos;
CSymbolInfo    m_sym;

NewsEvent      m_events[];
int            m_eventCount;
datetime       m_lastBarTime;
int            m_tradesToday;
double         m_dayStartBalance;
datetime       m_lastTradeDay;
double         m_pipSize;

//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(InpMagic);
   m_trade.SetDeviationInPoints(InpSlippage);

   if(!m_sym.Name(_Symbol))
   {
      Print("Symbol init failed");
      return INIT_FAILED;
   }

   // Pip size
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(digits == 3 || digits == 5)
      m_pipSize = _Point * 10.0;
   else if(digits == 2)
      m_pipSize = _Point * 10.0; // Gold: 1 pip = $0.10
   else
      m_pipSize = _Point;

   // Fill mode
   long fillType = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((fillType & SYMBOL_FILLING_FOK) != 0)
      m_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fillType & SYMBOL_FILLING_IOC) != 0)
      m_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      m_trade.SetTypeFilling(ORDER_FILLING_RETURN);

   // Load events
   m_eventCount = LoadEvents(InpEventsFile);
   if(m_eventCount == 0)
   {
      Print("WARNING: No events loaded from ", InpEventsFile);
      return INIT_FAILED;
   }
   Print("Loaded ", m_eventCount, " events from ", InpEventsFile);

   m_lastBarTime = 0;
   m_tradesToday = 0;
   m_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   m_lastTradeDay = 0;

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ArrayFree(m_events);
}

//+------------------------------------------------------------------+
void OnTick()
{
   // New bar gate (M15)
   datetime barTime = iTime(_Symbol, PERIOD_M15, 0);
   if(barTime == m_lastBarTime) return;
   m_lastBarTime = barTime;

   if(!m_sym.RefreshRates()) return;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);

   // Daily reset
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != m_lastTradeDay)
   {
      m_tradesToday = 0;
      m_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      m_lastTradeDay = today;
   }

   // DD kill switch
   double currentEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(m_dayStartBalance > 0 && (m_dayStartBalance - currentEquity) / m_dayStartBalance * 100.0 > InpMaxDDPct)
      return;

   // Check for time-based exit on open positions
   CheckTimeExit(barTime);

   // Already have a position?
   if(HasPosition()) return;

   // Max trades check
   if(m_tradesToday >= InpMaxTradesDay) return;

   // Check if a news event occurred InpPostBars bars ago
   datetime eventBarTime = iTime(_Symbol, PERIOD_M15, InpPostBars);
   datetime eventBarEnd  = eventBarTime + PeriodSeconds(PERIOD_M15);

   int eventIdx = FindEventInBar(eventBarTime, eventBarEnd);
   if(eventIdx < 0) return;

   // Check if this event type is enabled
   if(!IsEventEnabled(m_events[eventIdx].event_type)) return;

   // Get the event bar's OHLC
   double eventOpen  = iOpen(_Symbol, PERIOD_M15, InpPostBars);
   double eventClose = iClose(_Symbol, PERIOD_M15, InpPostBars);
   double eventHigh  = iHigh(_Symbol, PERIOD_M15, InpPostBars);
   double eventLow   = iLow(_Symbol, PERIOD_M15, InpPostBars);

   // Calculate event bar move
   double movePips = MathAbs(eventClose - eventOpen) / m_pipSize;
   if(movePips < InpMinMovePips) return;

   // Spread check
   double spreadPips = m_sym.Spread() * _Point / m_pipSize;
   if(spreadPips > InpMaxSpreadPips) return;

   // Determine direction: trade WITH the event bar's direction
   bool isBuy = (eventClose > eventOpen);

   // Entry: current bar open (market order)
   double entryPrice = isBuy ? m_sym.Ask() : m_sym.Bid();

   // SL: beyond the event bar's opposite extreme + buffer
   double slBuffer = 2.0 * m_pipSize; // 2 pip buffer
   double sl, tp;

   if(isBuy)
   {
      sl = eventLow - slBuffer;
      double riskDist = entryPrice - sl;
      tp = entryPrice + riskDist * InpRR;
   }
   else
   {
      sl = eventHigh + slBuffer;
      double riskDist = sl - entryPrice;
      tp = entryPrice - riskDist * InpRR;
   }

   // Validate stop level
   double stopLevel = m_sym.StopsLevel() * _Point;
   if(stopLevel > 0)
   {
      if(isBuy)
      {
         if(entryPrice - sl < stopLevel)
            sl = entryPrice - stopLevel - _Point;
         if(tp - entryPrice < stopLevel)
            tp = entryPrice + stopLevel + _Point;
      }
      else
      {
         if(sl - entryPrice < stopLevel)
            sl = entryPrice + stopLevel + _Point;
         if(entryPrice - tp < stopLevel)
            tp = entryPrice - stopLevel - _Point;
      }
   }

   // Lot sizing
   double lots = CalcLots(entryPrice, sl);
   if(lots <= 0) return;

   // Execute
   string comment = StringFormat("NM_%s", m_events[eventIdx].event_type);
   bool ok;
   if(isBuy)
      ok = m_trade.Buy(lots, _Symbol, 0, sl, tp, comment);
   else
      ok = m_trade.Sell(lots, _Symbol, 0, sl, tp, comment);

   if(ok)
   {
      m_tradesToday++;
      Print("NEWS TRADE: ", (isBuy ? "BUY" : "SELL"), " ", lots, " lots | Event: ",
            m_events[eventIdx].event_type, " | Move: ", DoubleToString(movePips, 1), " pips");
   }
}

//+------------------------------------------------------------------+
int LoadEvents(string filename)
{
   int handle = FileOpen(filename, FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("Cannot open ", filename, " Error: ", GetLastError());
      return 0;
   }

   int count = 0;

   // Skip header
   if(!FileIsEnding(handle))
   {
      FileReadString(handle); // date
      FileReadString(handle); // time_utc
      FileReadString(handle); // event_type
      FileReadString(handle); // currency
      FileReadString(handle); // importance
   }

   while(!FileIsEnding(handle))
   {
      string dateStr = FileReadString(handle);
      if(StringLen(dateStr) == 0) break;

      string timeStr = FileReadString(handle);
      string eventType = FileReadString(handle);
      string currency = FileReadString(handle);
      string impStr = FileReadString(handle);

      // Parse datetime (format: YYYY.MM.DD HH:MM)
      datetime dt = StringToTime(dateStr + " " + timeStr);
      if(dt == 0) continue;

      ArrayResize(m_events, count + 1, 100);
      m_events[count].time = dt;
      m_events[count].event_type = eventType;
      m_events[count].currency = currency;
      m_events[count].importance = (int)StringToInteger(impStr);
      count++;
   }

   FileClose(handle);
   m_eventCount = count;
   return count;
}

//+------------------------------------------------------------------+
int FindEventInBar(datetime barStart, datetime barEnd)
{
   for(int i = 0; i < m_eventCount; i++)
   {
      if(m_events[i].time >= barStart && m_events[i].time < barEnd)
         return i;
   }
   return -1;
}

//+------------------------------------------------------------------+
bool IsEventEnabled(string eventType)
{
   if(InpTradeNFP && StringFind(eventType, "NonFarm") >= 0) return true;
   if(InpTradeCPI && StringFind(eventType, "CPI") >= 0) return true;
   if(InpTradeFOMC && StringFind(eventType, "FOMC") >= 0) return true;
   if(InpTradeBOJ && StringFind(eventType, "BOJ") >= 0) return true;
   if(InpTradeGDP && StringFind(eventType, "GDP") >= 0) return true;
   if(InpTradePCE && StringFind(eventType, "PCE") >= 0) return true;
   return false;
}

//+------------------------------------------------------------------+
double CalcLots(double entry, double sl)
{
   double riskDist = MathAbs(entry - sl);
   if(riskDist <= 0) return 0;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * InpRiskPct / 100.0;

   double tickVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0 || tickSize <= 0) return 0;

   double lots = riskAmount / (riskDist / tickSize * tickVal);

   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMax(lots, minLot);
   lots = MathMin(lots, maxLot);

   return lots;
}

//+------------------------------------------------------------------+
bool HasPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_pos.SelectByIndex(i))
      {
         if(m_pos.Magic() == InpMagic && m_pos.Symbol() == _Symbol)
            return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
void CheckTimeExit(datetime currentBarTime)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!m_pos.SelectByIndex(i)) continue;
      if(m_pos.Magic() != InpMagic || m_pos.Symbol() != _Symbol) continue;

      datetime openTime = m_pos.Time();
      int barsHeld = (int)((currentBarTime - openTime) / PeriodSeconds(PERIOD_M15));

      if(barsHeld >= InpMaxBarHold)
      {
         m_trade.PositionClose(m_pos.Ticket());
         Print("TIME EXIT: Position held ", barsHeld, " bars");
      }
   }
}
//+------------------------------------------------------------------+
