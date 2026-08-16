#ifndef SNR_CONTEXT_SCAN_MQH
#define SNR_CONTEXT_SCAN_MQH

#include "SNR_Types.mqh"

int SnrContextOpenCsv(const bool enabled)
  {
   if(!enabled)
      return(INVALID_HANDLE);
   const int h=FileOpen("SNR_CONTEXT_OVERLAY.csv",
                        FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ);
   if(h==INVALID_HANDLE)
      return(INVALID_HANDLE);
   FileSeek(h,0,SEEK_END);
   if(FileTell(h)==0)
      FileWrite(h,
                "bar_time","close","atr",
                "wave_geom","dragon_angle_side","trend_side",
                "sr_runway_whq","pva_class","session_bucket",
                "dragon_mid","ema89","tick_volume","vol_avg","fired");
   return(h);
  }

void SnrContextWrite(const int handle,const SnrSignalDecision &sig,const SnrClassicCfg &cfg)
  {
   if(handle==INVALID_HANDLE || !sig.session.valid)
      return;
   const int wave_geom=((sig.wave.valid && sig.wave.break_or_reject) ? 1 : 0);
   int dragon_side=sig.dragon.side;
   if(sig.dragon.valid && SnrFinite(sig.signal_close) && SnrFinite(sig.dragon.mid))
     {
      if(sig.signal_close>sig.dragon.mid)
         dragon_side=SNR_DIR_LONG;
      else if(sig.signal_close<sig.dragon.mid)
         dragon_side=SNR_DIR_SHORT;
     }
   const int trend_side=sig.trend.side;
   const double runway_pips=(cfg.pip_size>0.0 ? sig.sr.distance/cfg.pip_size : 0.0);
   FileWrite(handle,
             TimeToString(sig.decision_time,TIME_DATE|TIME_MINUTES),
             sig.signal_close,
             sig.atr,
             wave_geom,
             dragon_side,
             trend_side,
             runway_pips,
             sig.pvsra.cls,
             sig.session.zone,
             sig.dragon.mid,
             sig.trend.ema,
             sig.pvsra.volume,
             sig.pvsra.average,
             (sig.fired ? 1 : 0));
  }

#endif
