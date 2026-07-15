//+------------------------------------------------------------------+
//| Portfolio_Risk.mqh — Portfolio-Level Risk Management              |
//| Peak equity DD guard, daily DD, kill-all                          |
//| Max | 2026-04-05                                                 |
//+------------------------------------------------------------------+
#ifndef PORTFOLIO_RISK_MQH
#define PORTFOLIO_RISK_MQH

#include "Portfolio_Common.mqh"

//--- State
double   PF_peakEquity     = 0;
double   PF_dayStartEquity = 0;
datetime PF_currentDay     = 0;
bool     PF_dailyKill      = false;

//+------------------------------------------------------------------+
//| Init risk tracking                                                |
//+------------------------------------------------------------------+
void PF_RiskInit()
{
   PF_peakEquity     = AccountInfoDouble(ACCOUNT_EQUITY);
   PF_dayStartEquity = PF_peakEquity;
   PF_currentDay     = 0;
   PF_dailyKill      = false;
}

//+------------------------------------------------------------------+
//| Daily reset — call every tick                                    |
//+------------------------------------------------------------------+
void PF_RiskDailyReset()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));

   if(today != PF_currentDay)
   {
      PF_currentDay     = today;
      PF_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      PF_dailyKill      = false;
   }

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > PF_peakEquity) PF_peakEquity = eq;
}

//+------------------------------------------------------------------+
//| Check portfolio DD from peak — NOT permanent kill                 |
//| Returns true if DD currently exceeds limit (close-all + pause)    |
//| Resumes automatically when DD recovers below threshold            |
//+------------------------------------------------------------------+
bool PF_IsPortfolioDDBreached(double maxPct)
{
   if(PF_peakEquity <= 0) return false;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (PF_peakEquity - eq) / PF_peakEquity * 100.0;
   if(dd >= maxPct)
   {
      static datetime lastWarn = 0;
      if(TimeCurrent() - lastWarn > 3600)
      {
         PrintFormat("[PORTFOLIO] DD PAUSE: %.1f%% >= %.1f%% — no new entries until recovery",
                     dd, maxPct);
         lastWarn = TimeCurrent();
      }
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Check daily DD — resets each new day                              |
//+------------------------------------------------------------------+
bool PF_IsDailyDDBreached(double maxPct)
{
   if(PF_dailyKill) return true;
   if(PF_dayStartEquity <= 0) return false;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (PF_dayStartEquity - eq) / PF_dayStartEquity * 100.0;
   if(dd >= maxPct)
   {
      PF_dailyKill = true;
      PrintFormat("[PORTFOLIO] DAILY DD KILL: %.1f%% >= %.1f%%", dd, maxPct);
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Close ALL portfolio positions                                     |
//+------------------------------------------------------------------+
void PF_CloseAllPortfolio(CTrade &trade, ulong baseMagic, int numModules)
{
   for(int m = 1; m <= numModules; m++)
      PF_CloseAll(trade, baseMagic + m);
}

#endif // PORTFOLIO_RISK_MQH
