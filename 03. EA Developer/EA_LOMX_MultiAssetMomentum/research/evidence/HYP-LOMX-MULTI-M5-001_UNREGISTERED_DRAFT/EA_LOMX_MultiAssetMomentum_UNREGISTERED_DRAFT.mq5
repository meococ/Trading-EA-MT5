//+------------------------------------------------------------------+
//|                                EA_LOMX_MultiAssetMomentum.mq5    |
//|                 Copyright 2026, Lead Quant & AlphaFactory Engine   |
//|        HYP-LOMX-MULTI-M5-001: Dual-Engine London/NY Momentum     |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory Engine"
#property link      "https://alphafactory.quant"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//--- Input Parameters
input group "--- Strategy Configuration ---"
input string   InpVariantTag        = "MODEL0_PRIMARY"; // Variant Tag
input double   InpRiskPercent       = 0.5;       // Risk Per Trade (%)
input double   InpMaxDailyLossPct   = 3.5;       // Daily Hard Loss Cutoff (%)
input double   InpMaxSpreadPips     = 2.5;       // Max Allowed Spread (Pips)
input int      InpATRPeriod         = 14;        // ATR Period
input double   InpSweepEpsilonMult  = 0.3;       // Sweep Buffer ATR Multiplier
input double   InpVolumeThreshold   = 1.5;       // Volume Spike StdDev Multiplier

input group "--- Session Hours (UTC) ---"
input int      InpAsianStartHour    = 0;         // Asian Session Start Hour
input int      InpAsianEndHour      = 6;         // Asian Session End Hour
input int      InpTradeStartHour    = 7;         // Active Trading Start Hour
input int      InpTradeEndHour      = 16;        // Active Trading End Hour

//--- Global Handles & State Variables
CTrade         m_trade;
datetime       m_last_bar_time;
double         m_asian_high;
double         m_asian_low;
double         m_start_day_equity;
datetime       m_current_day;
bool           m_daily_lockout;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(777001);
   m_last_bar_time = 0;
   m_asian_high = 0.0;
   m_asian_low = 0.0;
   m_start_day_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   m_current_day = 0;
   m_daily_lockout = false;
   
   Print("EA_LOMX_MultiAssetMomentum initialized under HYP-LOMX-MULTI-M5-001. Tag: ", InpVariantTag);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("EA_LOMX_MultiAssetMomentum deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| IsNewBar Check                                                   |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   datetime current_bar_time = iTime(_Symbol, _Period, 0);
   if(current_bar_time != m_last_bar_time)
   {
      m_last_bar_time = current_bar_time;
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Update Daily Risk & Asian Session Ranges                         |
//+------------------------------------------------------------------+
void UpdateSessionState()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   datetime today = StructToTime(dt) - (dt.hour * 3600 + dt.min * 60 + dt.sec);
   
   // Reset daily starting equity
   if(today != m_current_day)
   {
      m_current_day = today;
      m_start_day_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_daily_lockout = false;
   }
   
   // Check Daily Loss Hard Lock (3.5%)
   double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(m_start_day_equity > 0 && ((m_start_day_equity - current_equity) / m_start_day_equity * 100.0) >= InpMaxDailyLossPct)
   {
      m_daily_lockout = true;
      // Close all open positions if daily limit breached
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol)
         {
            m_trade.PositionClose(ticket);
         }
      }
   }
   
   // Calculate Asian Session High/Low (00:00 to 06:00 UTC)
   if(dt.hour >= InpAsianEndHour)
   {
      double h = 0.0;
      double l = 999999.0;
      for(int b = 1; b <= 72; b++) // ~6 hours of M5 bars
      {
         datetime bar_t = iTime(_Symbol, _Period, b);
         MqlDateTime bar_dt;
         TimeToStruct(bar_t, bar_dt);
         if(bar_dt.hour >= InpAsianStartHour && bar_dt.hour < InpAsianEndHour)
         {
            double high_val = iHigh(_Symbol, _Period, b);
            double low_val  = iLow(_Symbol, _Period, b);
            if(high_val > h) h = high_val;
            if(low_val < l)  l = low_val;
         }
      }
      if(h > 0 && l < 999999.0)
      {
         m_asian_high = h;
         m_asian_low = l;
      }
   }
}

//+------------------------------------------------------------------+
//| Calculate ATR Helper                                             |
//+------------------------------------------------------------------+
double GetATR(int period, int shift)
{
   int handle = iATR(_Symbol, _Period, period);
   if(handle == INVALID_HANDLE) return 0.0010;
   double val[1];
   if(CopyBuffer(handle, 0, shift, 1, val) > 0)
   {
      IndicatorRelease(handle);
      return val[0];
   }
   IndicatorRelease(handle);
   return 0.0010;
}

//+------------------------------------------------------------------+
//| Calculate Volume Spike Threshold                                 |
//+------------------------------------------------------------------+
bool IsVolumeSpike(int bar)
{
   long vol1 = iTickVolume(_Symbol, _Period, bar);
   double sum = 0;
   for(int i = bar + 1; i <= bar + 20; i++)
   {
      sum += (double)iTickVolume(_Symbol, _Period, i);
   }
   double avg = sum / 20.0;
   
   double var_sum = 0;
   for(int i = bar + 1; i <= bar + 20; i++)
   {
      double diff = (double)iTickVolume(_Symbol, _Period, i) - avg;
      var_sum += diff * diff;
   }
   double std_dev = MathSqrt(var_sum / 20.0);
   
   return ((double)vol1 > (avg + InpVolumeThreshold * std_dev));
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Always update session state
   UpdateSessionState();
   
   // Check lockout or existing positions
   if(m_daily_lockout || PositionsTotal() > 0) return;
   
   // Closed-bar execution only
   if(!IsNewBar()) return;
   
   MqlDateTime dt;
   TimeCurrent(dt);
   
   // Active session window check (07:00 - 16:00 UTC)
   if(dt.hour < InpTradeStartHour || dt.hour >= InpTradeEndHour) return;
   
   // Spread Check
   double current_spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
   double max_spread = InpMaxSpreadPips * _Point * 10;
   if(current_spread > max_spread) return;
   
   if(m_asian_high == 0.0 || m_asian_low == 0.0) return;
   
   double atr = GetATR(InpATRPeriod, 1);
   double close1 = iClose(_Symbol, _Period, 1);
   double high1  = iHigh(_Symbol, _Period, 1);
   double low1   = iLow(_Symbol, _Period, 1);
   
   double sweep_eps = InpSweepEpsilonMult * atr;
   
   // Engine A: London Liquidity Sweep Reclaim
   bool is_vol_spike = IsVolumeSpike(1);
   
   // Buy Sweep Reclaim Signal
   if(low1 < (m_asian_low - sweep_eps) && close1 > m_asian_low && is_vol_spike)
   {
      double sl = low1 - (0.2 * atr);
      double sl_dist = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - sl;
      if(sl_dist > 0)
      {
         double tp = SymbolInfoDouble(_Symbol, SYMBOL_ASK) + (sl_dist * 1.8);
         double lot = (AccountInfoDouble(ACCOUNT_BALANCE) * (InpRiskPercent / 100.0)) / (sl_dist / _Point * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE));
         lot = MathMin(MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)), SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
         lot = NormalizeDouble(lot, 2);
         
         m_trade.Buy(lot, _Symbol, SymbolInfoDouble(_Symbol, SYMBOL_ASK), sl, tp, "LOMX_Sweep_Buy");
         return;
      }
   }
   
   // Sell Sweep Reclaim Signal
   if(high1 > (m_asian_high + sweep_eps) && close1 < m_asian_high && is_vol_spike)
   {
      double sl = high1 + (0.2 * atr);
      double sl_dist = sl - SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(sl_dist > 0)
      {
         double tp = SymbolInfoDouble(_Symbol, SYMBOL_BID) - (sl_dist * 1.8);
         double lot = (AccountInfoDouble(ACCOUNT_BALANCE) * (InpRiskPercent / 100.0)) / (sl_dist / _Point * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE));
         lot = MathMin(MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN)), SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
         lot = NormalizeDouble(lot, 2);
         
         m_trade.Sell(lot, _Symbol, SymbolInfoDouble(_Symbol, SYMBOL_BID), sl, tp, "LOMX_Sweep_Sell");
         return;
      }
   }
}
