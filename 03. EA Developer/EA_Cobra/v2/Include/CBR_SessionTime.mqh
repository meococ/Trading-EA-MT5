//+------------------------------------------------------------------+
//| CBR_SessionTime.mqh — Kill Zone, Time & Level Building           |
//| v2: Adds Asian Range + PrevDay H/L level tracking                |
//+------------------------------------------------------------------+
#ifndef CBR_SESSIONTIME_MQH
#define CBR_SESSIONTIME_MQH

#include "CBR_Config.mqh"
#include "CBR_Types.mqh"

//--- Global level set
CBR_LevelSet g_cbrLevels;

//+------------------------------------------------------------------+
//| Detect current Kill Zone from hour                                |
//+------------------------------------------------------------------+
ENUM_CBR_KILLZONE CBR_GetKillZone(int hour, int ldnStart, int ldnEnd,
                                   int nyStart, int nyEnd,
                                   int nycStart, int nycEnd)
{
   if(hour >= ldnStart && hour < ldnEnd)
      return CBR_KZ_LDN;
   if(hour >= nyStart && hour < nyEnd)
      return CBR_KZ_NY;
   if(hour >= nycStart && hour < nycEnd)
      return CBR_KZ_NYC;
   return CBR_KZ_NONE;
}

//+------------------------------------------------------------------+
//| Kill Zone name for logging                                       |
//+------------------------------------------------------------------+
string CBR_KillZoneName(ENUM_CBR_KILLZONE kz)
{
   switch(kz)
   {
      case CBR_KZ_LDN:  return "LDN";
      case CBR_KZ_NY:   return "NY";
      case CBR_KZ_NYC:  return "NYC";
      default:          return "NONE";
   }
}

//+------------------------------------------------------------------+
//| Entry mode name for logging                                      |
//+------------------------------------------------------------------+
string CBR_EntryModeName(ENUM_CBR_ENTRY_MODE mode)
{
   switch(mode)
   {
      case CBR_ENTRY_BREAKOUT: return "BREAK";
      case CBR_ENTRY_BOUNCE:   return "BOUNCE";
      default:                 return "NONE";
   }
}

//+------------------------------------------------------------------+
//| Level type name for logging                                      |
//+------------------------------------------------------------------+
string CBR_LevelTypeName(ENUM_CBR_LEVEL_TYPE lvl)
{
   switch(lvl)
   {
      case CBR_LVL_ASIAN_HI: return "ASIA_HI";
      case CBR_LVL_ASIAN_LO: return "ASIA_LO";
      case CBR_LVL_PREV_HI:  return "PREV_HI";
      case CBR_LVL_PREV_LO:  return "PREV_LO";
      default:               return "NONE";
   }
}

//+------------------------------------------------------------------+
//| Get R:R target by Kill Zone                                       |
//+------------------------------------------------------------------+
double CBR_GetRR(ENUM_CBR_KILLZONE kz)
{
   switch(kz)
   {
      case CBR_KZ_LDN:  return CBR_TP_RR_LDN;
      case CBR_KZ_NY:   return CBR_TP_RR_NY;
      case CBR_KZ_NYC:  return CBR_TP_RR_NYC;
      default:          return 2.0;
   }
}

//+------------------------------------------------------------------+
//| Get day-of-week risk multiplier                                  |
//+------------------------------------------------------------------+
double CBR_GetDayRiskMult(int dow)
{
   switch(dow)
   {
      case 1:  return CBR_MON_RISK_MULT;
      case 3:  return CBR_WED_RISK_MULT;
      default: return 1.0;
   }
}

//+------------------------------------------------------------------+
//| Check if Friday flatten time                                      |
//+------------------------------------------------------------------+
bool CBR_IsFridayFlatten(int dow, int hour)
{
   return (dow == 5 && hour >= CBR_FRIDAY_CLOSE_H);
}

//+------------------------------------------------------------------+
//| Check if weekend                                                  |
//+------------------------------------------------------------------+
bool CBR_IsWeekend(int dow)
{
   return (dow == 0 || dow == 6);
}

//+------------------------------------------------------------------+
//| Build Asian Range — scan bars from 00:00 to 06:59                |
//| Call once per day when first bar >= 07:00 arrives                 |
//+------------------------------------------------------------------+
void CBR_BuildAsianRange(string symbol, int asianStartH, int asianEndH,
                          double pt)
{
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   datetime today = StringToTime(IntegerToString(now.year) + "." +
                                  IntegerToString(now.mon) + "." +
                                  IntegerToString(now.day));

   // Only rebuild once per day
   if(g_cbrLevels.asianBuildDay == today)
      return;

   double hi = -999999.0;
   double lo =  999999.0;
   int barCount = 0;

   // Scan recent bars to find Asian session bars for today
   for(int i = 1; i <= 200; i++)
   {
      datetime barT = iTime(symbol, PERIOD_M15, i);
      if(barT == 0) break;

      MqlDateTime bt;
      TimeToStruct(barT, bt);

      // Must be same day
      datetime barDay = StringToTime(IntegerToString(bt.year) + "." +
                                      IntegerToString(bt.mon) + "." +
                                      IntegerToString(bt.day));

      if(barDay != today) break;  // Went to previous day

      // Must be in Asian session hours
      if(bt.hour >= asianStartH && bt.hour < asianEndH)
      {
         double h = iHigh(symbol, PERIOD_M15, i);
         double l = iLow(symbol, PERIOD_M15, i);
         if(h > hi) hi = h;
         if(l < lo) lo = l;
         barCount++;
      }
   }

   if(barCount >= 4 && hi > lo)  // At least 4 bars (1 hour of M15)
   {
      g_cbrLevels.asianHi    = hi;
      g_cbrLevels.asianLo    = lo;
      g_cbrLevels.asianRange = (hi - lo) / pt;
      g_cbrLevels.asianValid = (g_cbrLevels.asianRange >= CBR_ASIAN_RANGE_MIN &&
                                 g_cbrLevels.asianRange <= CBR_ASIAN_RANGE_MAX);
      g_cbrLevels.asianBuildDay = today;

      PrintFormat("[CBR] ASIAN RANGE BUILT: Hi=%.5f Lo=%.5f Range=%.0f pts Valid=%s",
                  hi, lo, g_cbrLevels.asianRange,
                  g_cbrLevels.asianValid ? "YES" : "NO");
   }
   else
   {
      g_cbrLevels.asianValid    = false;
      g_cbrLevels.asianBuildDay = today;
      PrintFormat("[CBR] ASIAN RANGE SKIP: bars=%d (need >=4)", barCount);
   }
}

//+------------------------------------------------------------------+
//| Build Previous Day H/L — scan D1 bar[1]                          |
//+------------------------------------------------------------------+
void CBR_BuildPrevDayLevels(string symbol)
{
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   datetime today = StringToTime(IntegerToString(now.year) + "." +
                                  IntegerToString(now.mon) + "." +
                                  IntegerToString(now.day));

   // Only rebuild once per day
   if(g_cbrLevels.prevDayDate == today)
      return;

   double prevH = iHigh(symbol, PERIOD_D1, 1);
   double prevL = iLow(symbol, PERIOD_D1, 1);

   if(prevH > 0.0 && prevL > 0.0 && prevH > prevL)
   {
      g_cbrLevels.prevDayHi    = prevH;
      g_cbrLevels.prevDayLo    = prevL;
      g_cbrLevels.prevDayValid = true;
      g_cbrLevels.prevDayDate  = today;

      PrintFormat("[CBR] PREV DAY LEVELS: Hi=%.5f Lo=%.5f", prevH, prevL);
   }
   else
   {
      g_cbrLevels.prevDayValid = false;
      g_cbrLevels.prevDayDate  = today;
   }
}

//+------------------------------------------------------------------+
//| Init levels (call in OnInit)                                      |
//+------------------------------------------------------------------+
void CBR_InitLevels()
{
   ZeroMemory(g_cbrLevels);
   g_cbrLevels.asianValid   = false;
   g_cbrLevels.prevDayValid = false;
}

#endif // CBR_SESSIONTIME_MQH
