//+------------------------------------------------------------------+
//| FVG_Risk.mqh — sizing, daily guards, symbol packs                  |
//+------------------------------------------------------------------+
#ifndef FVG_RISK_MQH
#define FVG_RISK_MQH

#include "FVG_Types.mqh"
#include "FVG_Detect.mqh"
#include "FVG_Session.mqh"

void FVG_ResolvePack(const ENUM_SYMBOL_PACK pack_in, SSymbolPack &out_pack)
{
   ENUM_SYMBOL_PACK kind = pack_in;
   string sym = _Symbol;
   StringToUpper(sym);

   if(kind == PACK_AUTO)
   {
      if(StringFind(sym, "XAU") >= 0 || StringFind(sym, "GOLD") >= 0)
         kind = PACK_XAUUSD;
      else if(StringFind(sym, "GBPUSD") >= 0)
         kind = PACK_GBPUSD;
      else
         kind = PACK_EURUSD; // default / EURUSD family
   }

   out_pack.use_atr_min_gap = false;
   out_pack.atr_min_gap_mult = 0.0;

   if(kind == PACK_GBPUSD)
   {
      out_pack.name = "GBPUSD";
      out_pack.min_gap_pips = 12.0;
      out_pack.sl_buffer_pips = 5.0;
   }
   else if(kind == PACK_XAUUSD)
   {
      out_pack.name = "XAUUSD";
      out_pack.min_gap_pips = 25.0;
      out_pack.sl_buffer_pips = 15.0;
      out_pack.use_atr_min_gap = true;
      out_pack.atr_min_gap_mult = 0.35;
   }
   else
   {
      out_pack.name = "EURUSD";
      out_pack.min_gap_pips = 10.0;   // 8-12 band default 10
      out_pack.sl_buffer_pips = 4.0;  // 3-5 band default 4
   }
}

double FVG_NormalizeVolume(double lots)
{
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      step = 0.01;
   lots = MathFloor(lots / step) * step;
   if(lots < vmin)
      lots = 0.0;
   if(lots > vmax)
      lots = vmax;
   int vol_digits = 2;
   if(step >= 1.0)
      vol_digits = 0;
   else if(step >= 0.1)
      vol_digits = 1;
   else if(step >= 0.01)
      vol_digits = 2;
   else
      vol_digits = 3;
   return NormalizeDouble(lots, vol_digits);
}

double FVG_NormalizePrice(const double price)
{
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return NormalizeDouble(price, digits);
}

double FVG_StopsLevelPrice()
{
   long stops = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   return (double)stops * pt;
}

bool FVG_ValidateStops(const bool is_buy, const double entry, double &sl, double &tp)
{
   double level = FVG_StopsLevelPrice();
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(level <= 0.0)
      level = pt * 10.0;

   if(is_buy)
   {
      if(sl >= entry)
         return false;
      if(entry - sl < level)
         sl = FVG_NormalizePrice(entry - level);
      if(tp > 0.0 && tp - entry < level)
         tp = FVG_NormalizePrice(entry + level);
   }
   else
   {
      if(sl <= entry)
         return false;
      if(sl - entry < level)
         sl = FVG_NormalizePrice(entry + level);
      if(tp > 0.0 && entry - tp < level)
         tp = FVG_NormalizePrice(entry - level);
   }
   sl = FVG_NormalizePrice(sl);
   if(tp > 0.0)
      tp = FVG_NormalizePrice(tp);
   return (sl > 0.0);
}

double FVG_LotsForRisk(const double risk_pct,
                       const double entry,
                       const double sl,
                       const double max_lot)
{
   if(risk_pct <= 0.0 || entry <= 0.0 || sl <= 0.0)
      return 0.0;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_money = equity * (risk_pct / 100.0);
   double sl_dist = MathAbs(entry - sl);
   if(sl_dist <= 0.0)
      return 0.0;

   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tick_size <= 0.0 || tick_value <= 0.0)
      return 0.0;

   double loss_per_lot = (sl_dist / tick_size) * tick_value;
   if(loss_per_lot <= 0.0)
      return 0.0;

   double lots = risk_money / loss_per_lot;
   if(max_lot > 0.0 && lots > max_lot)
      lots = max_lot;
   return FVG_NormalizeVolume(lots);
}

struct SRiskState
{
   int      trades_today;
   int      day_key;
   double   day_start_equity;
   double   peak_equity;
   bool     day_loss_locked;
};

void FVG_RiskResetDay(SRiskState &st)
{
   int key = FVG_DayOfYear(FVG_BrokerNow());
   if(st.day_key != key)
   {
      st.day_key = key;
      st.trades_today = 0;
      st.day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      st.day_loss_locked = false;
   }
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > st.peak_equity)
      st.peak_equity = eq;
}

bool FVG_DailyLossHit(SRiskState &st, const double daily_loss_pct)
{
   FVG_RiskResetDay(st);
   if(daily_loss_pct <= 0.0)
      return false;
   if(st.day_start_equity <= 0.0)
      st.day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (st.day_start_equity - eq) / st.day_start_equity * 100.0;
   if(dd >= daily_loss_pct)
   {
      st.day_loss_locked = true;
      return true;
   }
   return st.day_loss_locked;
}

int FVG_CountOpenPositions(const long magic, const bool one_per_symbol)
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(!PositionSelectByTicket(ticket))
         continue;
      if((long)PositionGetInteger(POSITION_MAGIC) != magic)
         continue;
      if(one_per_symbol && PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(!one_per_symbol && PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      count++;
   }
   return count;
}

double FVG_MinGapPrice(const SSymbolPack &pack, const double atr)
{
   double gap = FVG_PipsToPrice(pack.min_gap_pips);
   if(pack.use_atr_min_gap && atr > 0.0)
   {
      double atr_floor = atr * pack.atr_min_gap_mult;
      if(atr_floor > gap)
         gap = atr_floor;
   }
   return gap;
}

#endif
