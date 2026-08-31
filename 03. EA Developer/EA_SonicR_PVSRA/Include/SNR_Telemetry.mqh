#ifndef SNR_TELEMETRY_MQH
#define SNR_TELEMETRY_MQH

#include "SNR_Types.mqh"

void SnrTelemetryReset(SnrTelemetry &tel)
  {
   ZeroMemory(tel);
   tel.csv_handle=INVALID_HANDLE;
  }

void SnrTelemetryOpenCsv(SnrTelemetry &tel,const bool enabled)
  {
   tel.csv_handle=INVALID_HANDLE;
   if(!enabled)
      return;
   const int h=FileOpen("EA_SonicR_PVSRA_decisions.csv",
                        FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ);
   if(h==INVALID_HANDLE)
     {
      Print("SNR001_TEL file_open_fail");
      return;
     }
   FileSeek(h,0,SEEK_END);
   if(FileTell(h)==0)
      FileWrite(h,
                "time","decision_bar","direction","close","ema89","ema89_slope",
                "dragon_high","dragon_mid","dragon_low","dragon_slope_atr","dragon_angled",
                "wave_quality","overlap","impulse","pullback","pvsra_class","vol","vol_avg",
                "sr_blocked","sr_level","session","spread","fired","reject_reason");
   tel.csv_handle=h;
  }

void SnrTelemetryCloseCsv(SnrTelemetry &tel)
  {
   if(tel.csv_handle!=INVALID_HANDLE)
     {
      FileClose(tel.csv_handle);
      tel.csv_handle=INVALID_HANDLE;
     }
  }

void SnrTelemetryWriteDecision(SnrTelemetry &tel,const bool enabled,
                               const SnrSignalDecision &sig,const double spread)
  {
   if(!enabled || tel.csv_handle==INVALID_HANDLE)
      return;
   FileWrite(tel.csv_handle,
             TimeToString(sig.availability_time,TIME_DATE|TIME_SECONDS),
             TimeToString(sig.decision_time,TIME_DATE|TIME_MINUTES),
             sig.direction,
             sig.signal_close,
             sig.trend.ema,
             sig.trend.slope,
             sig.dragon.high,
             sig.dragon.mid,
             sig.dragon.low,
             sig.dragon.slope_atr,
             (sig.dragon.angled ? 1 : 0),
             sig.wave.quality,
             sig.wave.overlap_ratio,
             sig.wave.impulse_extreme,
             sig.wave.pullback_price,
             sig.pvsra.cls,
             sig.pvsra.volume,
             sig.pvsra.average,
             (sig.sr.blocked ? 1 : 0),
             sig.sr.level,
             sig.session.zone,
             spread,
             (sig.fired ? 1 : 0),
             sig.reject_reason);
  }

void SnrNoteReject(SnrTelemetry &tel,const SnrSignalDecision &sig)
  {
   if(sig.data_fail)
     {
      tel.data_fails++;
      return;
     }
   if(sig.reject_reason=="TREND")
      tel.trend_rejects++;
   else if(sig.reject_reason=="DRAGON")
      tel.dragon_rejects++;
   else if(sig.reject_reason=="WAVE")
      tel.wave_rejects++;
   else if(sig.reject_reason=="PVSRA")
      tel.pvsra_vetoes++;
   else if(sig.reject_reason=="SR_RUNWAY")
      tel.sr_blocks++;
   else if(sig.reject_reason=="SESSION")
      tel.window_skips++;
  }

void SnrTelemetrySummary(const SnrTelemetry &tel,const int reason,const bool runtime_failed)
  {
   PrintFormat("SNR001_SUMMARY reason=%d failed=%s closed_bars=%I64d signals=%I64d long=%I64d short=%I64d entries=%I64d entry_rej=%I64d spread_rej=%I64d risk_skip=%I64d vol_rej=%I64d window_skip=%I64d sr_block=%I64d wave_rej=%I64d dragon_rej=%I64d trend_rej=%I64d pvsra_veto=%I64d pvsra_ok=%I64d closes=%I64d close_rej=%I64d postfill=%I64d data_fail=%I64d",
               reason,(runtime_failed ? "true" : "false"),tel.closed_bars,tel.signals,
               tel.long_signals,tel.short_signals,tel.entries,tel.entry_rejects,
               tel.spread_rejects,tel.risk_lock_skips,tel.volume_rejects,tel.window_skips,
               tel.sr_blocks,tel.wave_rejects,tel.dragon_rejects,tel.trend_rejects,
               tel.pvsra_vetoes,tel.pvsra_supports,tel.closes,tel.close_rejects,
               tel.postfill_closes,tel.data_fails);
  }

#endif
