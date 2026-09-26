//+------------------------------------------------------------------+
//| LSW_Levels.mqh                                                   |
//| Reference levels where resting stop orders cluster (Osler 2003). |
//|                                                                  |
//| CAUSALITY DOCTRINE (CONTRACT.md §3):                             |
//|  - Every level is a pure function of a time window that had      |
//|    ALREADY ELAPSED when the sweep bar opened. No mutable "freeze  |
//|    flag" is trusted; the Asia range and the opening range are     |
//|    recomputed from their fixed windows, so they are frozen by     |
//|    construction and a mid-day restart reproduces them exactly.    |
//|  - Range scans stop at (window_end - one M5 bar), which is always |
//|    strictly older than the forming bar, so the incomplete bar can |
//|    never enter a level.                                           |
//|  - Every CopyRates return value is checked; a failure is reported |
//|    as data_fail, never swallowed into an empty level set.         |
//+------------------------------------------------------------------+
#ifndef LSW_LEVELS_MQH
#define LSW_LEVELS_MQH

#include "LSW_Types.mqh"
#include "LSW_Session.mqh"

//--- Recomputation cache. Keys are window identities, so a stale entry is
//--- impossible: a different window is a different key.
struct LswLevelCache
  {
   int               asia_day_key;
   bool              asia_valid;
   double            asia_high;
   double            asia_low;
   datetime          or_key;
   bool              or_valid;
   double            or_high;
   double            or_low;
   datetime          pd_key;
   bool              pd_valid;
   double            pd_high;
   double            pd_low;
  };

void LswLevelCacheReset(LswLevelCache &cache)
  {
   ZeroMemory(cache);
   cache.asia_day_key=-1;
   cache.or_key=0;
   cache.pd_key=0;
  }

//--- High/low over closed M5 bars whose OPEN time lies in [from,to] (server).
//--- Returns: 1 ok, 0 no bars in window (normal on holidays), -1 terminal error.
int LswClosedRangeHighLow(const string symbol,const datetime from,const datetime to,
                          double &hi,double &lo)
  {
   hi=0.0;
   lo=0.0;
   if(from<=0 || to<from)
      return(0);
   // Closed bars only, proven inside the callee: a bar is closed iff its open
   // time is <= the open of the last closed M5 bar. Clamp `to` so the range
   // can never include the forming bar, regardless of caller.
   const datetime last_closed_open=iTime(symbol,PERIOD_M5,1);
   datetime to_eff=to;
   if(to_eff>last_closed_open)
      to_eff=last_closed_open;
   MqlRates rates[];
   // Index direction is irrelevant here: this is a min/max reduction over the
   // whole array. Flag is still set explicitly so the intent is not implicit.
   ArraySetAsSeries(rates,false);
   ResetLastError();
   const int copied=CopyRates(symbol,PERIOD_M5,from,to_eff,rates);
   if(copied<0)
      return(-1);
   if(copied==0)
      return(0);
   hi=rates[0].high;
   lo=rates[0].low;
   for(int i=1;i<copied;i++)
     {
      if(rates[i].high>hi)
         hi=rates[i].high;
      if(rates[i].low<lo)
         lo=rates[i].low;
     }
   if(!LswFinite(hi) || !LswFinite(lo) || hi<lo)
      return(-1);
   return(1);
  }

void LswPushLevel(LswLevelSet &set,const double price,const LSW_FAMILY family,
                  const bool is_high)
  {
   if(set.count>=LSW_MAX_LEVELS || !LswFinite(price) || price<=0.0)
      return;
   set.items[set.count].price=price;
   set.items[set.count].family=family;
   set.items[set.count].is_high=is_high;
   set.count++;
  }

//--- Prior COMPLETED D1 bar. Guarded so the D1 bar is proven to have closed
//--- before the sweep bar opened: iTime(D1,0) is the open of the current D1 bar,
//--- which is exactly the close of D1 shift 1.
bool LswPrevDayLevels(const string symbol,const datetime sweep_bar_time,
                      LswLevelCache &cache,bool &data_fail)
  {
   if(iBars(symbol,PERIOD_D1)<2)
      return(false);
   MqlRates d1[];
   // as-series TRUE with shift 1 => d1[0] is the last COMPLETED D1 bar; the
   // forming D1 bar is never read.
   ArraySetAsSeries(d1,true);
   ResetLastError();
   if(CopyRates(symbol,PERIOD_D1,1,1,d1)!=1)
     {
      data_fail=true;
      return(false);
     }
   // d1[0] closed at d1[0].time + one D1 day; if that close is after the sweep
   // bar opened, the level was not yet complete when the sweep printed.
   if(d1[0].time+PeriodSeconds(PERIOD_D1)>sweep_bar_time)
      return(false);
   if(!LswFinite(d1[0].high) || !LswFinite(d1[0].low) || d1[0].high<d1[0].low)
     {
      data_fail=true;
      return(false);
     }
   if(cache.pd_key!=d1[0].time || !cache.pd_valid)
     {
      cache.pd_key=d1[0].time;
      cache.pd_high=d1[0].high;
      cache.pd_low=d1[0].low;
      cache.pd_valid=true;
     }
   return(true);
  }

//--- Asia range 00:00-07:00 GMT of the sweep bar's GMT day. Only published once
//--- 07:00 GMT has passed, and never recomputed with any later bar.
bool LswAsiaLevels(const string symbol,const LswClock &clk,LswLevelCache &cache,
                   bool &data_fail)
  {
   if(clk.gmt_hour<LSW_ASIA_END_GMT)
      return(false);
   const int day_key=LswDayKey(clk.gmt_day_start);
   if(cache.asia_valid && cache.asia_day_key==day_key)
      return(true);

   const long offset=(long)clk.server_time-(long)clk.gmt_time;
   const datetime from=(datetime)((long)clk.gmt_day_start+
                                  LSW_ASIA_START_GMT*LSW_SEC_PER_HOUR+offset);
   const datetime to=(datetime)((long)clk.gmt_day_start+
                                LSW_ASIA_END_GMT*LSW_SEC_PER_HOUR+offset-LSW_SEC_PER_M5);
   double hi=0.0,lo=0.0;
   const int rc=LswClosedRangeHighLow(symbol,from,to,hi,lo);
   if(rc<0)
     {
      data_fail=true;
      return(false);
     }
   cache.asia_day_key=day_key;
   cache.asia_valid=(rc==1);
   cache.asia_high=hi;
   cache.asia_low=lo;
   return(cache.asia_valid);
  }

//--- Opening range: first cfg.or_bars M5 bars after the active session open.
//--- Published only once the whole window has elapsed.
bool LswOpenRangeLevels(const string symbol,const LswClock &clk,const LswConfig &cfg,
                        LswLevelCache &cache,bool &data_fail)
  {
   if(clk.session_open_gmt<=0 || cfg.or_bars<=0)
      return(false);
   const datetime window_end=(datetime)((long)clk.session_open_gmt+
                                        (long)cfg.or_bars*LSW_SEC_PER_M5);
   if(clk.gmt_time<window_end)
      return(false);                     // range not complete yet
   if(cache.or_valid && cache.or_key==clk.session_open_gmt)
      return(true);

   const long offset=(long)clk.server_time-(long)clk.gmt_time;
   const datetime from=(datetime)((long)clk.session_open_gmt+offset);
   const datetime to=(datetime)((long)window_end+offset-LSW_SEC_PER_M5);
   double hi=0.0,lo=0.0;
   const int rc=LswClosedRangeHighLow(symbol,from,to,hi,lo);
   if(rc<0)
     {
      data_fail=true;
      return(false);
     }
   cache.or_key=clk.session_open_gmt;
   cache.or_valid=(rc==1);
   cache.or_high=hi;
   cache.or_low=lo;
   return(cache.or_valid);
  }

//--- Build the full level set for one sweep bar.
//--- Returns false only on a data failure. count==0 is a normal outcome.
bool LswBuildLevels(const string symbol,const datetime sweep_bar_time,
                    const double sweep_high,const double sweep_low,
                    const LswConfig &cfg,const LswClock &clk,
                    LswLevelCache &cache,LswLevelSet &out)
  {
   ZeroMemory(out);
   bool data_fail=false;

   if(cfg.use_prev_day && LswPrevDayLevels(symbol,sweep_bar_time,cache,data_fail))
     {
      LswPushLevel(out,cache.pd_high,LSW_FAM_PREV_DAY,true);
      LswPushLevel(out,cache.pd_low,LSW_FAM_PREV_DAY,false);
     }
   if(cfg.use_asia && LswAsiaLevels(symbol,clk,cache,data_fail))
     {
      LswPushLevel(out,cache.asia_high,LSW_FAM_ASIA,true);
      LswPushLevel(out,cache.asia_low,LSW_FAM_ASIA,false);
     }
   if(cfg.use_open_range && LswOpenRangeLevels(symbol,clk,cfg,cache,data_fail))
     {
      LswPushLevel(out,cache.or_high,LSW_FAM_OPEN_RANGE,true);
      LswPushLevel(out,cache.or_low,LSW_FAM_OPEN_RANGE,false);
     }
   //--- Round numbers: take the multiple actually straddled by the sweep bar,
   //--- i.e. the highest multiple at or below the bar high (stops rest above it)
   //--- and the lowest multiple at or above the bar low.
   if(cfg.round_step>0.0 && LswFinite(sweep_high) && LswFinite(sweep_low))
     {
      const double up=MathFloor(sweep_high/cfg.round_step+1e-9)*cfg.round_step;
      const double dn=MathCeil(sweep_low/cfg.round_step-1e-9)*cfg.round_step;
      //--- Only publish a grid line the bar actually straddles. The grid itself
      //--- is fixed and known ex ante; the bar only selects which line to test.
      if(up>0.0 && up>=sweep_low)
         LswPushLevel(out,up,LSW_FAM_ROUND,true);
      if(dn>0.0 && dn<=sweep_high)
         LswPushLevel(out,dn,LSW_FAM_ROUND,false);
     }
   return(!data_fail);
  }

#endif
