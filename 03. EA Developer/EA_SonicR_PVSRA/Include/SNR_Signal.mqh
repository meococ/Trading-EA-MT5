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

#endif
