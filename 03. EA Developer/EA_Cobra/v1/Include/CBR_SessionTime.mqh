//+------------------------------------------------------------------+
//| CBR_SessionTime.mqh — Kill Zone & Time Management                |
//+------------------------------------------------------------------+
#ifndef CBR_SESSIONTIME_MQH
#define CBR_SESSIONTIME_MQH

#include "CBR_Config.mqh"
#include "CBR_Types.mqh"

//+------------------------------------------------------------------+
//| Detect current Kill Zone from hour                                |
//+------------------------------------------------------------------+
ENUM_CBR_KILLZONE CBR_GetKillZone(int hour, int ldnStart, int ldnEnd,
                                   int nyStart, int nyEnd,
                                   int nycStart, int nycEnd)
{
   // London Open Kill Zone
   if(hour >= ldnStart && hour < ldnEnd)
      return CBR_KZ_LDN;

   // NY Open Kill Zone
   if(hour >= nyStart && hour < nyEnd)
      return CBR_KZ_NY;

   // NY Close Kill Zone
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
//| Get R:R target by Kill Zone                                       |
//+------------------------------------------------------------------+
double CBR_GetRR(ENUM_CBR_KILLZONE kz)
{
   switch(kz)
   {
      case CBR_KZ_LDN:  return CBR_TP_RR_LDN;     // 3.0
      case CBR_KZ_NY:   return CBR_TP_RR_NY;       // 2.5
      case CBR_KZ_NYC:  return CBR_TP_RR_NYC;      // 2.0
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
      case 1:  return CBR_MON_RISK_MULT;   // Monday 0.85
      case 3:  return CBR_WED_RISK_MULT;   // Wednesday 0.70
      default: return 1.0;
   }
}

//+------------------------------------------------------------------+
//| Check if Friday flatten time reached                              |
//+------------------------------------------------------------------+
bool CBR_IsFridayFlatten(int dow, int hour)
{
   return (dow == 5 && hour >= CBR_FRIDAY_CLOSE_H);
}

//+------------------------------------------------------------------+
//| Check if weekend (no trading)                                     |
//+------------------------------------------------------------------+
bool CBR_IsWeekend(int dow)
{
   return (dow == 0 || dow == 6);
}

#endif // CBR_SESSIONTIME_MQH
