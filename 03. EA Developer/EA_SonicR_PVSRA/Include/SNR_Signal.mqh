#ifndef SNR_SIGNAL_MQH
#define SNR_SIGNAL_MQH

#include "SNR_Types.mqh"
#include "SNR_Dragon.mqh"
#include "SNR_Trend.mqh"
#include "SNR_ClassicWave.mqh"
#include "SNR_PVSRA.mqh"
#include "SNR_SRLevels.mqh"
#include "SNR_Session.mqh"

bool SnrBuildClassicSignal(const string symbol,const ENUM_TIMEFRAMES tf,
                           const SnrHandles &handles,const SnrClassicCfg &cfg,
                           const datetime availability_time,SnrSignalDecision &out)
  {
   ZeroMemory(out);
   out.availability_time=availability_time;
   out.reject_reason="NONE";
   if(SNR_SCOUT_ENABLED)
     {
      out.data_fail=true;
      out.reject_reason="SCOUT_FORBIDDEN";
      return(false);
     }
   if(!SnrHandlesReady(handles) || availability_time<=0 || cfg.lookback<32)
     {
      out.data_fail=true;
      out.reject_reason="HANDLE_OR_CFG";
      return(false);
     }

   MqlRates rates[];
   double d_high[],d_mid[],d_low[],trend[],atr[];
   if(!SnrCopyClosedRates(symbol,tf,cfg.lookback,rates) ||
      !SnrCopyClosedBuffer(handles.dragon_high,cfg.lookback,d_high) ||
      !SnrCopyClosedBuffer(handles.dragon_mid,cfg.lookback,d_mid) ||
      !SnrCopyClosedBuffer(handles.dragon_low,cfg.lookback,d_low) ||
      !SnrCopyClosedBuffer(handles.trend,cfg.lookback,trend) ||
      !SnrCopyClosedBuffer(handles.atr,cfg.lookback,atr))
     {
      out.data_fail=true;
      out.reject_reason="COPY_FAIL";
      return(false);
     }
   if(rates[0].time<=0 || rates[0].time>=availability_time ||
      !SnrFinite(rates[0].close) || !SnrFinite(atr[0]) || atr[0]<=0.0)
     {
      out.data_fail=true;
      out.reject_reason="STALE_OR_EMPTY";
      return(false);
     }

   out.decision_time=rates[0].time;
   out.signal_high=rates[0].high;
   out.signal_low=rates[0].low;
   out.signal_close=rates[0].close;
   out.atr=atr[0];

   if(!SnrDragonReadClosed(d_high,d_mid,d_low,atr,cfg.dragon_slope_bars,
                           cfg.dragon_min_slope_atr,out.dragon))
     {
      out.data_fail=true;
      out.reject_reason="DRAGON_READ";
      return(false);
     }
   if(!SnrTrendReadClosed(trend,rates[0].close,cfg.trend_slope_bars,out.trend))
     {
      out.data_fail=true;
      out.reject_reason="TREND_READ";
      return(false);
     }
   const datetime server_now=TimeCurrent();
   const datetime gmt_now=TimeGMT();
   const datetime signal_gmt=rates[0].time-(server_now-gmt_now);
   if(!SnrSessionRead(signal_gmt,cfg,out.session))
     {
      out.data_fail=true;
      out.reject_reason="SESSION_READ";
      return(false);
     }
   if(!out.session.entry_allowed)
     {
      out.reject_reason="SESSION";
      return(true);
     }

   const int direction=out.trend.side;
   if(direction==SNR_DIR_NONE)
     {
      out.reject_reason="TREND";
      return(true);
     }
   const bool dragon_ok=((direction>0 && d_mid[0]>=d_mid[cfg.dragon_slope_bars]) ||
                         (direction<0 && d_mid[0]<=d_mid[cfg.dragon_slope_bars]));
   if(!dragon_ok)
     {
      out.reject_reason="DRAGON";
      return(true);
     }
   out.direction=direction;

   if(!SnrClassicWaveReadClosed(rates,d_high,d_low,direction,cfg,out.wave))
     {
      out.data_fail=true;
      out.reject_reason="WAVE_READ";
      return(false);
     }
   if(!out.wave.valid || !out.wave.break_or_reject)
     {
      out.reject_reason="WAVE";
      return(true);
     }

   SnrPvsraReadClosed(rates,direction,cfg.vol_avg_bars,cfg.vol_rising_mult,
                      cfg.vol_climax_mult,out.pvsra);

   if(!SnrSrReadClosed(rates[0].close,direction,atr[0],cfg.round_whole,
                       cfg.sr_runway_atr,out.sr))
     {
      out.data_fail=true;
      out.reject_reason="SR_READ";
      return(false);
     }

   out.fired=true;
   out.reject_reason="PASS";
   return(true);
  }

bool SnrBuildBandSignal(const string symbol,const ENUM_TIMEFRAMES tf,
                        const SnrHandles &handles,const SnrClassicCfg &cfg,
                        const datetime availability_time,SnrSignalDecision &out)
  {
   ZeroMemory(out);
   out.availability_time=availability_time;
   out.reject_reason="NONE";
   if(SNR_SCOUT_ENABLED)
     {
      out.data_fail=true;
      out.reject_reason="SCOUT_FORBIDDEN";
      return(false);
     }
   if(!SnrHandlesReady(handles) || availability_time<=0 || cfg.lookback<32)
     {
      out.data_fail=true;
      out.reject_reason="HANDLE_OR_CFG";
      return(false);
     }

   MqlRates rates[];
   double d_high[],d_mid[],d_low[],trend[],atr[];
   if(!SnrCopyClosedRates(symbol,tf,cfg.lookback,rates) ||
      !SnrCopyClosedBuffer(handles.dragon_high,cfg.lookback,d_high) ||
      !SnrCopyClosedBuffer(handles.dragon_mid,cfg.lookback,d_mid) ||
      !SnrCopyClosedBuffer(handles.dragon_low,cfg.lookback,d_low) ||
      !SnrCopyClosedBuffer(handles.trend,cfg.lookback,trend) ||
      !SnrCopyClosedBuffer(handles.atr,cfg.lookback,atr))
     {
      out.data_fail=true;
      out.reject_reason="COPY_FAIL";
      return(false);
     }
   if(ArraySize(rates)<8 || rates[0].time<=0 || rates[0].time>=availability_time ||
      !SnrFinite(rates[0].close) || !SnrFinite(atr[0]) || atr[0]<=0.0)
     {
      out.data_fail=true;
      out.reject_reason="STALE_OR_EMPTY";
      return(false);
     }

   out.decision_time=rates[0].time;
   out.signal_high=rates[0].high;
   out.signal_low=rates[0].low;
   out.signal_close=rates[0].close;
   out.atr=atr[0];

   if(!SnrDragonReadClosed(d_high,d_mid,d_low,atr,cfg.dragon_slope_bars,
                           cfg.dragon_min_slope_atr,out.dragon))
     {
      out.data_fail=true;
      out.reject_reason="DRAGON_READ";
      return(false);
     }
   if(!SnrTrendReadClosed(trend,rates[0].close,cfg.trend_slope_bars,out.trend))
     {
      out.data_fail=true;
      out.reject_reason="TREND_READ";
      return(false);
     }
   const datetime server_now=TimeCurrent();
   const datetime gmt_now=TimeGMT();
   const datetime signal_gmt=rates[0].time-(server_now-gmt_now);
   if(!SnrSessionRead(signal_gmt,cfg,out.session))
     {
      out.data_fail=true;
      out.reject_reason="SESSION_READ";
      return(false);
     }
   if(!out.session.entry_allowed)
     {
      out.reject_reason="SESSION";
      return(true);
     }

   const int direction=out.trend.side;
   if(direction==SNR_DIR_NONE)
     {
      out.reject_reason="TREND";
      return(true);
     }
   const bool dragon_ok=((direction>0 && d_mid[0]>=d_mid[cfg.dragon_slope_bars]) ||
                         (direction<0 && d_mid[0]<=d_mid[cfg.dragon_slope_bars]));
   if(!dragon_ok)
     {
      out.reject_reason="DRAGON";
      return(true);
     }
   out.direction=direction;

   const bool now_out=(direction>0
                       ? (rates[0].close>d_high[0] && rates[0].close>rates[0].open)
                       : (rates[0].close<d_low[0] && rates[0].close<rates[0].open));
   const bool was_in=(direction>0 ? rates[1].close<=d_high[1]
                                  : rates[1].close>=d_low[1]);
   if(!now_out || !was_in)
     {
      out.reject_reason="BAND";
      return(true);
     }

   double structure=rates[0].low;
   if(direction<0)
      structure=rates[0].high;
   const int scan=MathMin(8,ArraySize(rates)-1);
   for(int i=1;i<=scan;i++)
     {
      if(direction>0 && rates[i].low<structure)
         structure=rates[i].low;
      if(direction<0 && rates[i].high>structure)
         structure=rates[i].high;
     }

   out.wave.valid=true;
   out.wave.direction=direction;
   out.wave.break_or_reject=true;
   out.wave.first_break=true;
   out.wave.quality=SNR_WAVE_CLEAN;
   out.wave.structure_swing=structure;
   out.wave.impulse_extreme=(direction>0 ? rates[0].high : rates[0].low);
   out.wave.pullback_price=structure;

   SnrPvsraReadClosed(rates,direction,cfg.vol_avg_bars,cfg.vol_rising_mult,
                      cfg.vol_climax_mult,out.pvsra);
   if(!SnrSrReadClosed(rates[0].close,direction,atr[0],cfg.round_whole,
                       cfg.sr_runway_atr,out.sr))
     {
      out.data_fail=true;
      out.reject_reason="SR_READ";
      return(false);
     }

   out.fired=true;
   out.reject_reason="PASS";
   return(true);
  }

bool SnrShouldRideExit(const string symbol,const ENUM_TIMEFRAMES tf,
                       const SnrHandles &handles,const int direction,
                       const datetime availability_time,bool &data_fail)
  {
   data_fail=false;
   if(direction==SNR_DIR_NONE || availability_time<=0 || !SnrHandlesReady(handles))
      return(false);
   MqlRates rates[];
   double d_high[],d_low[];
   if(!SnrCopyClosedRates(symbol,tf,8,rates) ||
      !SnrCopyClosedBuffer(handles.dragon_high,8,d_high) ||
      !SnrCopyClosedBuffer(handles.dragon_low,8,d_low))
     {
      data_fail=true;
      return(false);
     }
   if(rates[0].time<=0 || rates[0].time>=availability_time ||
      !SnrFinite(rates[0].close) || !SnrFinite(d_high[0]) || !SnrFinite(d_low[0]))
     {
      data_fail=true;
      return(false);
     }
   if(direction>0)
      return(rates[0].close<d_low[0]);
   return(rates[0].close>d_high[0]);
  }

bool SnrBuildPullSignal(const string symbol,const ENUM_TIMEFRAMES tf,
                        const SnrHandles &handles,const SnrClassicCfg &cfg,
                        const datetime availability_time,SnrSignalDecision &out)
  {
   ZeroMemory(out);
   out.availability_time=availability_time;
   out.reject_reason="NONE";
   if(SNR_SCOUT_ENABLED)
     {
      out.data_fail=true;
      out.reject_reason="SCOUT_FORBIDDEN";
      return(false);
     }
   if(!SnrHandlesReady(handles) || availability_time<=0 || cfg.lookback<32)
     {
      out.data_fail=true;
      out.reject_reason="HANDLE_OR_CFG";
      return(false);
     }

   MqlRates rates[];
   double d_high[],d_mid[],d_low[],trend[],atr[];
   if(!SnrCopyClosedRates(symbol,tf,cfg.lookback,rates) ||
      !SnrCopyClosedBuffer(handles.dragon_high,cfg.lookback,d_high) ||
      !SnrCopyClosedBuffer(handles.dragon_mid,cfg.lookback,d_mid) ||
      !SnrCopyClosedBuffer(handles.dragon_low,cfg.lookback,d_low) ||
      !SnrCopyClosedBuffer(handles.trend,cfg.lookback,trend) ||
      !SnrCopyClosedBuffer(handles.atr,cfg.lookback,atr))
     {
      out.data_fail=true;
      out.reject_reason="COPY_FAIL";
      return(false);
     }
   if(ArraySize(rates)<4 || rates[0].time<=0 || rates[0].time>=availability_time ||
      !SnrFinite(rates[0].close) || !SnrFinite(atr[0]) || atr[0]<=0.0)
     {
      out.data_fail=true;
      out.reject_reason="STALE_OR_EMPTY";
      return(false);
     }

   out.decision_time=rates[0].time;
   out.signal_high=rates[0].high;
   out.signal_low=rates[0].low;
   out.signal_close=rates[0].close;
   out.atr=atr[0];

   if(!SnrDragonReadClosed(d_high,d_mid,d_low,atr,cfg.dragon_slope_bars,
                           cfg.dragon_min_slope_atr,out.dragon))
     {
      out.data_fail=true;
      out.reject_reason="DRAGON_READ";
      return(false);
     }
   if(!SnrTrendReadClosed(trend,rates[0].close,cfg.trend_slope_bars,out.trend))
     {
      out.data_fail=true;
      out.reject_reason="TREND_READ";
      return(false);
     }
   const datetime server_now=TimeCurrent();
   const datetime gmt_now=TimeGMT();
   const datetime signal_gmt=rates[0].time-(server_now-gmt_now);
   if(!SnrSessionRead(signal_gmt,cfg,out.session))
     {
      out.data_fail=true;
      out.reject_reason="SESSION_READ";
      return(false);
     }
   if(!out.session.entry_allowed)
     {
      out.reject_reason="SESSION";
      return(true);
     }

   const int direction=out.trend.side;
   if(direction==SNR_DIR_NONE)
     {
      out.reject_reason="TREND";
      return(true);
     }
   const bool dragon_ok=((direction>0 && d_mid[0]>=d_mid[cfg.dragon_slope_bars]) ||
                         (direction<0 && d_mid[0]<=d_mid[cfg.dragon_slope_bars]));
   if(!dragon_ok)
     {
      out.reject_reason="DRAGON";
      return(true);
     }
   out.direction=direction;

   const double touch=MathMax(cfg.dragon_touch_atr,0.05)*atr[0];
   const int tag_window=MathMax(cfg.max_pullback_age,1);
   bool tagged=false;
   for(int i=0;i<tag_window && i<ArraySize(rates);i++)
     {
      if(direction>0 && rates[i].low<=d_mid[0]+touch)
         tagged=true;
      if(direction<0 && rates[i].high>=d_mid[0]-touch)
         tagged=true;
     }
   const int prior=MathMin(tag_window,ArraySize(rates)-1);
   const bool not_already_on=(direction>0
                              ? rates[prior].low>d_mid[0]+touch
                              : rates[prior].high<d_mid[0]-touch);
   const bool reclaim=(direction>0
                       ? (rates[0].close>d_mid[0] && rates[0].close>rates[0].open)
                       : (rates[0].close<d_mid[0] && rates[0].close<rates[0].open));
   const bool not_break=(direction>0 ? rates[0].close<=d_high[0]
                                    : rates[0].close>=d_low[0]);
   if(!tagged || !not_already_on || !reclaim || !not_break)
     {
      out.reject_reason="PULL";
      return(true);
     }

   out.wave.valid=true;
   out.wave.direction=direction;
   out.wave.into_dragon=true;
   out.wave.break_or_reject=true;
   out.wave.first_break=false;
   out.wave.quality=SNR_WAVE_CLEAN;
   out.wave.structure_swing=(direction>0 ? MathMin(rates[0].low,rates[1].low)
                                        : MathMax(rates[0].high,rates[1].high));
   out.wave.pullback_price=out.wave.structure_swing;
   out.wave.impulse_extreme=(direction>0 ? rates[0].high : rates[0].low);

   SnrPvsraReadClosed(rates,direction,cfg.vol_avg_bars,cfg.vol_rising_mult,
                      cfg.vol_climax_mult,out.pvsra);
   if(!SnrSrReadClosed(rates[0].close,direction,atr[0],cfg.round_whole,
                       cfg.sr_runway_atr,out.sr))
     {
      out.data_fail=true;
      out.reject_reason="SR_READ";
      return(false);
     }

   out.fired=true;
   out.reject_reason="PASS";
   return(true);
  }

bool SnrBuildEnvSignal(const string symbol,const ENUM_TIMEFRAMES tf,
                       const SnrHandles &handles,const SnrClassicCfg &cfg,
                       const datetime availability_time,SnrSignalDecision &out)
  {
   ZeroMemory(out);
   out.availability_time=availability_time;
   out.reject_reason="NONE";
   if(SNR_SCOUT_ENABLED)
     {
      out.data_fail=true;
      out.reject_reason="SCOUT_FORBIDDEN";
      return(false);
     }
   if(!SnrHandlesReady(handles) || availability_time<=0 || cfg.lookback<32)
     {
      out.data_fail=true;
      out.reject_reason="HANDLE_OR_CFG";
      return(false);
     }

   MqlRates rates[];
   double d_high[],d_mid[],d_low[],trend[],atr[];
   if(!SnrCopyClosedRates(symbol,tf,cfg.lookback,rates) ||
      !SnrCopyClosedBuffer(handles.dragon_high,cfg.lookback,d_high) ||
      !SnrCopyClosedBuffer(handles.dragon_mid,cfg.lookback,d_mid) ||
      !SnrCopyClosedBuffer(handles.dragon_low,cfg.lookback,d_low) ||
      !SnrCopyClosedBuffer(handles.trend,cfg.lookback,trend) ||
      !SnrCopyClosedBuffer(handles.atr,cfg.lookback,atr))
     {
      out.data_fail=true;
      out.reject_reason="COPY_FAIL";
      return(false);
     }
   if(ArraySize(rates)<4 || rates[0].time<=0 || rates[0].time>=availability_time ||
      !SnrFinite(rates[0].close) || !SnrFinite(atr[0]) || atr[0]<=0.0)
     {
      out.data_fail=true;
      out.reject_reason="STALE_OR_EMPTY";
      return(false);
     }

   out.decision_time=rates[0].time;
   out.signal_high=rates[0].high;
   out.signal_low=rates[0].low;
   out.signal_close=rates[0].close;
   out.atr=atr[0];

   if(!SnrDragonReadClosed(d_high,d_mid,d_low,atr,cfg.dragon_slope_bars,
                           cfg.dragon_min_slope_atr,out.dragon))
     {
      out.data_fail=true;
      out.reject_reason="DRAGON_READ";
      return(false);
     }
   if(!SnrTrendReadClosed(trend,rates[0].close,cfg.trend_slope_bars,out.trend))
     {
      out.data_fail=true;
      out.reject_reason="TREND_READ";
      return(false);
     }
   const datetime server_now=TimeCurrent();
   const datetime gmt_now=TimeGMT();
   const datetime signal_gmt=rates[0].time-(server_now-gmt_now);
   if(!SnrSessionRead(signal_gmt,cfg,out.session))
     {
      out.data_fail=true;
      out.reject_reason="SESSION_READ";
      return(false);
     }
   if(!out.session.entry_allowed)
     {
      out.reject_reason="SESSION";
      return(true);
     }

   const int direction=out.trend.side;
   if(direction==SNR_DIR_NONE)
     {
      out.reject_reason="TREND";
      return(true);
     }
   const bool dragon_ok=((direction>0 && d_mid[0]>=d_mid[cfg.dragon_slope_bars]) ||
                         (direction<0 && d_mid[0]<=d_mid[cfg.dragon_slope_bars]));
   if(!dragon_ok)
     {
      out.reject_reason="DRAGON";
      return(true);
     }
   out.direction=direction;

   const double touch=MathMax(cfg.dragon_touch_atr,0.05)*atr[0];
   const bool fresh_env=(direction>0
                         ? (rates[0].low<=d_low[0]+touch && rates[1].low>d_low[0]+touch)
                         : (rates[0].high>=d_high[0]-touch && rates[1].high<d_high[0]-touch));
   const bool reclaim=(direction>0
                       ? (rates[0].close>d_mid[0] && rates[0].close>rates[0].open)
                       : (rates[0].close<d_mid[0] && rates[0].close<rates[0].open));
   const bool inside_band=(direction>0 ? rates[0].close<=d_high[0]
                                       : rates[0].close>=d_low[0]);
   if(!fresh_env || !reclaim || !inside_band)
     {
      out.reject_reason="ENV";
      return(true);
     }

   const double structure=(direction>0 ? MathMin(rates[0].low,d_low[0])
                                       : MathMax(rates[0].high,d_high[0]));
   out.wave.valid=true;
   out.wave.direction=direction;
   out.wave.into_dragon=true;
   out.wave.break_or_reject=true;
   out.wave.first_break=false;
   out.wave.quality=SNR_WAVE_CLEAN;
   out.wave.structure_swing=structure;
   out.wave.pullback_price=structure;
   out.wave.impulse_extreme=(direction>0 ? rates[0].high : rates[0].low);

   SnrPvsraReadClosed(rates,direction,cfg.vol_avg_bars,cfg.vol_rising_mult,
                      cfg.vol_climax_mult,out.pvsra);
   if(!SnrSrReadClosed(rates[0].close,direction,atr[0],cfg.round_whole,
                       cfg.sr_runway_atr,out.sr))
     {
      out.data_fail=true;
      out.reject_reason="SR_READ";
      return(false);
     }

   out.fired=true;
   out.reject_reason="PASS";
   return(true);
  }

#endif
