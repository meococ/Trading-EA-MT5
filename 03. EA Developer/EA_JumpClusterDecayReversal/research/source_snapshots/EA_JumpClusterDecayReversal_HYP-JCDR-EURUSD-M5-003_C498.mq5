//+------------------------------------------------------------------+
//|                         EA_JumpClusterDecayReversal.mq5          |
//| HYP-JCDR-EURUSD-M5-003: outcome-blind router feasibility probe  |
//|                                                                  |
//| IMPORTANT                                                        |
//| - This build is a NO-TRADE exporter.                             |
//| - JCDR is the sole event and direction source.                   |
//| - AIRD/VRC/MBB/QQE are event-level vetoes only.                  |
//| - TB SMC only widens one shared causal stop distance.            |
//| - Price OHLC is read only from shift 1 or older.                 |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Outcome-blind broker-native JCDR indicator-router feasibility exporter"
#property tester_indicator "AlphaFactory\\AI_Regime_Detection.ex5"
#property tester_indicator "AlphaFactory\\Volatility_Regime_Classifier_QuantRegime.ex5"
#property tester_indicator "AlphaFactory\\Modern_Bollinger_Bands_GBB.ex5"
#property tester_indicator "AlphaFactory\\QQE_MOD.ex5"
#property tester_indicator "AlphaFactory\\TB_Smart_Money_Concept_2026.ex5"

input string InpHypothesisId    = "HYP-JCDR-EURUSD-M5-003";
input string InpExpectedSymbol  = "EURUSD";
input bool   InpResearchAutoMode= false; // Must be explicitly enabled by preregistered probe.
input bool   InpEnableTelemetry = true;  // Mandatory for the no-trade feasibility run.
input string InpVariantTag      = "JCDR_ROUTER_FEASIBILITY_V1";
input string InpAnalysisFrom    = "2016.01.04"; // Frozen event-surface start; tester may have a wider evidence envelope.
input string InpAnalysisTo      = "2020.12.31"; // Frozen event-surface end, inclusive in RESEARCH_CLOCK.

const int    JCDR_SCALE_RETURNS       = 48;
const int    JCDR_CLUSTER_BARS        = 15;
const int    JCDR_MIN_JUMPS           = 3;
const double JCDR_MIN_COHERENCE       = 0.80;
const double JCDR_MIN_DISPLACEMENT_PIP= 4.0;
const double JCDR_JUMP_FLOOR_PIP      = 1.20;
const double JCDR_JUMP_MULTIPLIER     = 3.0;
const int    JCDR_DECAY_MAX_BARS      = 10;
const double JCDR_RETRACE_MIN         = 0.25;
const double JCDR_RETRACE_MAX         = 1.00;
const double JCDR_MIN_STOP_PIP        = 6.0;
const double JCDR_STOP_BUFFER_PIP     = 0.50;
const double JCDR_COST_GEOMETRY_PIP   = 1.50;
const int    JCDR_HISTORY_CAPACITY    = 128;

const int VETO_AIRD_INVALID       = 1;
const int VETO_AIRD_HIGH_VOL      = 2;
const int VETO_AIRD_CONTINUATION  = 4;
const int VETO_VRC_INVALID        = 8;
const int VETO_VRC_HIGH_VOL       = 16;
const int VETO_VRC_COMPRESSION    = 32;
const int VETO_VRC_DISORDER       = 64;
const int VETO_MBB_INVALID        = 128;
const int VETO_MBB_SQUEEZE        = 256;
const int VETO_QQE_INVALID        = 512;
const int VETO_QQE_CONTINUATION   = 1024;
const int VETO_TB_INVALID         = 2048;

struct JcdrBar
  {
   datetime time;
   double   open;
   double   high;
   double   low;
   double   close;
   double   ret_pips;
   double   scale_pips;
   double   jump_threshold_pips;
   int      jump_sign;
   bool     jump_class_valid;
  };

struct PendingCluster
  {
   bool     active;
   datetime peak_time;
   int      dominant_sign;
   int      jump_count;
   double   coherence;
   double   anchor;
   double   extreme;
   double   signed_displacement_pips;
   double   scale_at_peak;
   double   threshold_at_peak;
   int      bars_after_peak;
  };

struct RouterSnapshot
  {
   int    veto_mask;
   bool   pass;
   double aird_valid;
   double aird_regime;
   double aird_confidence;
   double vrc_valid;
   double vrc_hurst;
   double vrc_chop;
   double vrc_vol_percentile;
   double vrc_regime;
   double vrc_high_vol;
   double mbb_dc_valid;
   double mbb_basis;
   double mbb_regime;
   double mbb_squeeze;
   double mbb_release;
   double qqe_primary;
   double qqe_secondary;
   double qqe_composite;
   double tb_swing_high;
   double tb_swing_low;
   double tb_closed_valid;
   double tb_atr;
   double tb_contract_version;
   double base_stop_pips;
   double tb_envelope_pips;
   double final_stop_pips;
  };

JcdrBar       g_bars[];
PendingCluster g_pending;
datetime      g_last_open_time=0;
datetime      g_last_processed_time=0;
datetime      g_first_analysis_time=0;
datetime      g_last_analysis_time=0;
int           g_consumed_research_date=0;

int g_aird_handle=INVALID_HANDLE;
int g_vrc_handle =INVALID_HANDLE;
int g_mbb_handle =INVALID_HANDLE;
int g_qqe_handle =INVALID_HANDLE;
int g_tb_handle  =INVALID_HANDLE;
int g_csv_handle =INVALID_HANDLE;

bool g_handles_ok=false;
bool g_telemetry_fatal=false;
bool g_seen_pre_window=false;
bool g_seen_post_window=false;
bool g_seen_exact_first_bar=false;
bool g_seen_exact_last_bar=false;
int  g_raw_events=0;
int  g_arm_rows=0;
int  g_router_pass_events=0;
int  g_router_pass_arm_rows=0;
int  g_router_pass_long=0;
int  g_router_pass_short=0;
int  g_year_counts[5]={0,0,0,0,0};
int  g_gap_resets=0;
int  g_invalid_bar_resets=0;
int  g_cluster_peaks=0;
int  g_decay_expired=0;
int  g_jump_in_decay=0;
int  g_retrace_out_of_band=0;
int  g_daily_refractory=0;
int  g_indicator_read_failures=0;
int  g_tb_contract_mismatches=0;
int  g_telemetry_write_failures=0;
double g_pass_stops[];
double g_pass_cost_ratios[];

string g_csv_name="EURUSD_JCDR003_StateTelemetry_HYP_JCDR_EURUSD_M5_003.csv";
string g_meta_name="JCDR003_RunMeta_HYP_JCDR_EURUSD_M5_003.json";

bool IsUsable(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

double PipSize()
  {
   return((_Digits==3 || _Digits==5) ? 10.0*_Point : _Point);
  }

int ResearchDateKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

int ResearchYear(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year);
  }

int ResearchHour(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.hour);
  }

string TimeIso(const datetime stamp)
  {
   return(TimeToString(stamp,TIME_DATE|TIME_MINUTES));
  }

void ResetPending()
  {
   ZeroMemory(g_pending);
   g_pending.active=false;
  }

void ResetFormation()
  {
   ArrayResize(g_bars,0);
   ResetPending();
  }

bool ValidOhlc(const double open_price,const double high_price,const double low_price,const double close_price)
  {
   if(!IsUsable(open_price) || !IsUsable(high_price) || !IsUsable(low_price) || !IsUsable(close_price))
      return(false);
   return(high_price>=MathMax(open_price,close_price) && low_price<=MathMin(open_price,close_price) && high_price>=low_price);
  }

void AppendBar(const JcdrBar &bar)
  {
   int count=ArraySize(g_bars);
   if(count>=JCDR_HISTORY_CAPACITY)
     {
      for(int i=1;i<count;i++)
         g_bars[i-1]=g_bars[i];
      count--;
      ArrayResize(g_bars,count);
     }
   ArrayResize(g_bars,count+1);
   g_bars[count]=bar;
  }

bool PriorMedianAbs48(double &median_value)
  {
   double values[];
   ArrayResize(values,JCDR_SCALE_RETURNS);
   int found=0;
   for(int i=ArraySize(g_bars)-1;i>=0 && found<JCDR_SCALE_RETURNS;i--)
     {
      // Scale bootstrap uses every usable prior return, including ordinary
      // non-jumps. jump_class_valid is produced by this scale and must not be
      // a prerequisite, otherwise the first 48-value window can never form.
      if(!IsUsable(g_bars[i].ret_pips))
         continue;
      values[found++]=MathAbs(g_bars[i].ret_pips);
     }
   if(found!=JCDR_SCALE_RETURNS)
      return(false);
   ArraySort(values);
   median_value=(values[23]+values[24])/2.0;
   return(IsUsable(median_value));
  }

bool TryFormCluster(PendingCluster &cluster)
  {
   const int count=ArraySize(g_bars);
   if(count<JCDR_CLUSTER_BARS || !g_bars[count-1].jump_class_valid || g_bars[count-1].jump_sign==0)
      return(false);

   const int first=count-JCDR_CLUSTER_BARS;
   int jump_count=0;
   int up_count=0;
   int down_count=0;
   int first_jump=-1;
   for(int i=first;i<count;i++)
     {
      if(!g_bars[i].jump_class_valid)
         return(false);
      if(g_bars[i].jump_sign!=0)
        {
         if(first_jump<0) first_jump=i;
         jump_count++;
         if(g_bars[i].jump_sign>0) up_count++;
         else down_count++;
        }
     }
   if(jump_count<JCDR_MIN_JUMPS || first_jump<0)
      return(false);

   const int dominant=(up_count>=down_count ? 1 : -1);
   const int dominant_count=MathMax(up_count,down_count);
   const double coherence=(double)dominant_count/(double)jump_count;
   if(coherence<JCDR_MIN_COHERENCE)
      return(false);

   const double pip=PipSize();
   const double anchor=g_bars[first_jump].open;
   const double signed_displacement=dominant*(g_bars[count-1].close-anchor)/pip;
   if(signed_displacement<JCDR_MIN_DISPLACEMENT_PIP)
      return(false);

   double extreme=(dominant>0 ? g_bars[first].high : g_bars[first].low);
   for(int i=first+1;i<count;i++)
     {
      if(dominant>0) extreme=MathMax(extreme,g_bars[i].high);
      else extreme=MathMin(extreme,g_bars[i].low);
     }

   ZeroMemory(cluster);
   cluster.active=true;
   cluster.peak_time=g_bars[count-1].time;
   cluster.dominant_sign=dominant;
   cluster.jump_count=jump_count;
   cluster.coherence=coherence;
   cluster.anchor=anchor;
   cluster.extreme=extreme;
   cluster.signed_displacement_pips=signed_displacement;
   cluster.scale_at_peak=g_bars[count-1].scale_pips;
   cluster.threshold_at_peak=g_bars[count-1].jump_threshold_pips;
   cluster.bars_after_peak=0;
   return(true);
  }

bool ThreeClosedBarsNoJump()
  {
   const int count=ArraySize(g_bars);
   if(count<3) return(false);
   for(int i=count-3;i<count;i++)
     {
      if(!g_bars[i].jump_class_valid || g_bars[i].jump_sign!=0)
         return(false);
     }
   return(true);
  }

double RetracementFraction(const double decision_close)
  {
   const double distance=MathAbs(g_pending.extreme-g_pending.anchor);
   if(!IsUsable(distance) || distance<=0.0)
      return(EMPTY_VALUE);
   if(g_pending.dominant_sign>0)
      return((g_pending.extreme-decision_close)/distance);
   return((decision_close-g_pending.extreme)/distance);
  }

bool ReadBufferValue(const int handle,const int buffer,const int shift,double &value)
  {
   double data[1];
   value=EMPTY_VALUE;
   if(handle==INVALID_HANDLE || CopyBuffer(handle,buffer,shift,1,data)!=1)
     {
      g_indicator_read_failures++;
      return(false);
     }
   value=data[0];
   return(true);
  }

bool IsExactFlag(const double value)
  {
   return(IsUsable(value) && (value==0.0 || value==1.0));
  }

bool IsExactTernary(const double value)
  {
   return(IsUsable(value) && (value==-1.0 || value==0.0 || value==1.0));
  }

string VetoText(const int mask)
  {
   if(mask==0) return("PASS");
   string out="";
   if((mask&VETO_AIRD_INVALID)!=0)      out+="AIRD_INVALID|";
   if((mask&VETO_AIRD_HIGH_VOL)!=0)     out+="AIRD_HIGH_VOL|";
   if((mask&VETO_AIRD_CONTINUATION)!=0) out+="AIRD_CONTINUATION|";
   if((mask&VETO_VRC_INVALID)!=0)       out+="VRC_INVALID|";
   if((mask&VETO_VRC_HIGH_VOL)!=0)      out+="VRC_HIGH_VOL|";
   if((mask&VETO_VRC_COMPRESSION)!=0)   out+="VRC_COMPRESSION|";
   if((mask&VETO_VRC_DISORDER)!=0)      out+="VRC_DISORDER|";
   if((mask&VETO_MBB_INVALID)!=0)       out+="MBB_INVALID|";
   if((mask&VETO_MBB_SQUEEZE)!=0)       out+="MBB_SQUEEZE|";
   if((mask&VETO_QQE_INVALID)!=0)       out+="QQE_INVALID|";
   if((mask&VETO_QQE_CONTINUATION)!=0)  out+="QQE_CONTINUATION|";
   if((mask&VETO_TB_INVALID)!=0)        out+="TB_INVALID|";
   if(StringLen(out)>0) out=StringSubstr(out,0,StringLen(out)-1);
   return(out);
  }

void BuildRouterSnapshot(const int cluster_sign,const double decision_close,RouterSnapshot &s)
  {
   ZeroMemory(s);
   s.veto_mask=0;

   bool aird_read=true;
   aird_read&=ReadBufferValue(g_aird_handle,11,1,s.aird_valid);
   aird_read&=ReadBufferValue(g_aird_handle,12,1,s.aird_regime);
   aird_read&=ReadBufferValue(g_aird_handle,5,1,s.aird_confidence);
   if(!aird_read || s.aird_valid!=1.0 || !IsUsable(s.aird_regime) || !IsUsable(s.aird_confidence))
      s.veto_mask|=VETO_AIRD_INVALID;
   else
     {
      const int regime=(int)MathRound(s.aird_regime);
      if(regime==3) s.veto_mask|=VETO_AIRD_HIGH_VOL;
      const int continuation_regime=(cluster_sign>0 ? 0 : 1);
      if(regime==continuation_regime && s.aird_confidence>=80.0)
         s.veto_mask|=VETO_AIRD_CONTINUATION;
     }

   bool vrc_read=true;
   vrc_read&=ReadBufferValue(g_vrc_handle,31,1,s.vrc_valid);
   vrc_read&=ReadBufferValue(g_vrc_handle,14,1,s.vrc_hurst);
   vrc_read&=ReadBufferValue(g_vrc_handle,18,1,s.vrc_chop);
   vrc_read&=ReadBufferValue(g_vrc_handle,19,1,s.vrc_vol_percentile);
   vrc_read&=ReadBufferValue(g_vrc_handle,23,1,s.vrc_regime);
   vrc_read&=ReadBufferValue(g_vrc_handle,26,1,s.vrc_high_vol);
   if(!vrc_read || s.vrc_valid!=1.0 || !IsUsable(s.vrc_hurst) || !IsUsable(s.vrc_chop) ||
      !IsUsable(s.vrc_vol_percentile) || !IsUsable(s.vrc_regime) || !IsExactFlag(s.vrc_high_vol))
      s.veto_mask|=VETO_VRC_INVALID;
   else
     {
      if(s.vrc_high_vol==1.0) s.veto_mask|=VETO_VRC_HIGH_VOL;
      if((int)MathRound(s.vrc_regime)==7) s.veto_mask|=VETO_VRC_COMPRESSION;
      if(s.vrc_chop>=61.8 && s.vrc_hurst>0.45) s.veto_mask|=VETO_VRC_DISORDER;
     }

   bool mbb_read=true;
   mbb_read&=ReadBufferValue(g_mbb_handle,16,1,s.mbb_dc_valid);
   mbb_read&=ReadBufferValue(g_mbb_handle,7,1,s.mbb_basis);
   mbb_read&=ReadBufferValue(g_mbb_handle,20,1,s.mbb_regime);
   mbb_read&=ReadBufferValue(g_mbb_handle,23,1,s.mbb_squeeze);
   mbb_read&=ReadBufferValue(g_mbb_handle,24,1,s.mbb_release);
   const bool mbb_regime_ok=(IsUsable(s.mbb_regime) && (s.mbb_regime==0.0 || s.mbb_regime==1.0));
   if(!mbb_read || s.mbb_dc_valid!=1.0 || !IsUsable(s.mbb_basis) || !mbb_regime_ok ||
      !IsExactFlag(s.mbb_squeeze) || !IsExactFlag(s.mbb_release))
      s.veto_mask|=VETO_MBB_INVALID;
   else if(s.mbb_squeeze==1.0 && s.mbb_release!=1.0)
      s.veto_mask|=VETO_MBB_SQUEEZE;

   bool qqe_read=true;
   qqe_read&=ReadBufferValue(g_qqe_handle,3,1,s.qqe_primary);
   qqe_read&=ReadBufferValue(g_qqe_handle,4,1,s.qqe_secondary);
   qqe_read&=ReadBufferValue(g_qqe_handle,8,1,s.qqe_composite);
   if(!qqe_read || !IsUsable(s.qqe_primary) || !IsUsable(s.qqe_secondary) || !IsExactTernary(s.qqe_composite))
      s.veto_mask|=VETO_QQE_INVALID;
   else if((cluster_sign>0 && s.qqe_composite==1.0) || (cluster_sign<0 && s.qqe_composite==-1.0))
      s.veto_mask|=VETO_QQE_CONTINUATION;

   bool tb_read=true;
   tb_read&=ReadBufferValue(g_tb_handle,13,1,s.tb_swing_high);
   tb_read&=ReadBufferValue(g_tb_handle,14,1,s.tb_swing_low);
   tb_read&=ReadBufferValue(g_tb_handle,26,1,s.tb_closed_valid);
   tb_read&=ReadBufferValue(g_tb_handle,28,1,s.tb_atr);
   tb_read&=ReadBufferValue(g_tb_handle,43,1,s.tb_contract_version);
   const bool tb_values_ok=(IsUsable(s.tb_swing_high) && IsUsable(s.tb_swing_low) &&
                            s.tb_swing_low<s.tb_swing_high && IsUsable(s.tb_atr) && s.tb_atr>0.0);
   if(IsUsable(s.tb_contract_version) && s.tb_contract_version!=3.0)
      g_tb_contract_mismatches++;
   if(!tb_read || s.tb_closed_valid!=1.0 || s.tb_contract_version!=3.0 || !tb_values_ok)
      s.veto_mask|=VETO_TB_INVALID;

   s.base_stop_pips=MathMax(JCDR_MIN_STOP_PIP,
                            MathAbs(g_pending.extreme-g_pending.anchor)/PipSize()+JCDR_STOP_BUFFER_PIP);
   s.tb_envelope_pips=EMPTY_VALUE;
   s.final_stop_pips=EMPTY_VALUE;
   if((s.veto_mask&VETO_TB_INVALID)==0)
     {
      const double upper_distance=MathAbs((s.tb_swing_high+JCDR_STOP_BUFFER_PIP*PipSize())-decision_close)/PipSize();
      const double lower_distance=MathAbs(decision_close-(s.tb_swing_low-JCDR_STOP_BUFFER_PIP*PipSize()))/PipSize();
      s.tb_envelope_pips=MathMax(upper_distance,lower_distance);
      s.final_stop_pips=MathMax(s.base_stop_pips,s.tb_envelope_pips);
     }
   s.pass=(s.veto_mask==0 && IsUsable(s.final_stop_pips) && s.final_stop_pips>=JCDR_MIN_STOP_PIP);
  }

void AddPassStop(const double stop_pips)
  {
   const int n=ArraySize(g_pass_stops);
   ArrayResize(g_pass_stops,n+1);
   g_pass_stops[n]=stop_pips;
   const int m=ArraySize(g_pass_cost_ratios);
   ArrayResize(g_pass_cost_ratios,m+1);
   g_pass_cost_ratios[m]=JCDR_COST_GEOMETRY_PIP/stop_pips;
  }

bool WriteArmRow(const string signal_id,const string arm,const string direction,
                 const datetime decision_time,const datetime availability_time,
                 const double retracement,const RouterSnapshot &s)
  {
   if(g_csv_handle==INVALID_HANDLE)
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      return(false);
     }
   const uint written=FileWrite(g_csv_handle,
             "CANDIDATE",InpHypothesisId,InpVariantTag,signal_id,arm,direction,
             TimeIso(g_pending.peak_time),TimeIso(decision_time),TimeIso(availability_time),
             ResearchDateKey(decision_time),ResearchYear(decision_time),ResearchHour(decision_time),
             g_pending.dominant_sign,g_pending.jump_count,g_pending.coherence,
             g_pending.anchor,g_pending.extreme,g_pending.signed_displacement_pips,
             g_pending.scale_at_peak,g_pending.threshold_at_peak,retracement,
             s.veto_mask,VetoText(s.veto_mask),(s.pass ? 1 : 0),
             s.aird_valid,s.aird_regime,s.aird_confidence,
             s.vrc_valid,s.vrc_hurst,s.vrc_chop,s.vrc_vol_percentile,s.vrc_regime,s.vrc_high_vol,
             s.mbb_dc_valid,s.mbb_basis,s.mbb_regime,s.mbb_squeeze,s.mbb_release,
             s.qqe_primary,s.qqe_secondary,s.qqe_composite,
             s.tb_swing_high,s.tb_swing_low,s.tb_closed_valid,s.tb_atr,s.tb_contract_version,
             s.base_stop_pips,s.tb_envelope_pips,s.final_stop_pips,
             (IsUsable(s.final_stop_pips) ? JCDR_COST_GEOMETRY_PIP/s.final_stop_pips : EMPTY_VALUE));
   if(written==0)
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR003 fail-closed: candidate telemetry row write failed for ",signal_id,"/",arm);
      return(false);
     }
   return(true);
  }

bool ExportDecision(const datetime decision_time,const datetime availability_time,const double retracement)
  {
   RouterSnapshot snapshot;
   const double decision_close=g_bars[ArraySize(g_bars)-1].close;
   BuildRouterSnapshot(g_pending.dominant_sign,decision_close,snapshot);

   const int candidate_index=g_raw_events+1;
   const string signal_id=StringFormat("JCDR003-SRC-%I64d-%06d",(long)decision_time,candidate_index);
   const string true_direction=(g_pending.dominant_sign>0 ? "SHORT" : "LONG");
   const string follow_direction=(g_pending.dominant_sign>0 ? "LONG" : "SHORT");
   const bool true_written=WriteArmRow(signal_id,"TRUE_REVERSAL",true_direction,decision_time,availability_time,retracement,snapshot);
   const bool follow_written=WriteArmRow(signal_id,"FOLLOW_CONTROL",follow_direction,decision_time,availability_time,retracement,snapshot);
   if(!true_written || !follow_written)
      return(false);

   // Commit counters as one matched event only after both arm rows exist.
   g_raw_events++;
   g_arm_rows+=2;

   if(snapshot.pass)
     {
      g_router_pass_events++;
      g_router_pass_arm_rows+=2;
      if(true_direction=="LONG") g_router_pass_long++;
      else g_router_pass_short++;
      const int year=ResearchYear(decision_time);
      if(year>=2016 && year<=2020) g_year_counts[year-2016]++;
      AddPassStop(snapshot.final_stop_pips);
     }
   FileFlush(g_csv_handle);
   return(true);
  }

void ProcessClosedBar(const datetime availability_time)
  {
   JcdrBar bar;
   ZeroMemory(bar);
   bar.time=iTime(_Symbol,PERIOD_M5,1);

   // AlphaFactory's no-performance collection authority validates an
   // all-available tester envelope.  The hypothesis population remains the
   // prospectively frozen 2016-2020 window: outside it we do not read OHLC,
   // carry formation state, emit rows or alter any feasibility denominator.
   const datetime analysis_from=D'2016.01.04 00:00';
   const datetime analysis_to=D'2020.12.31 23:55';
   if(bar.time<=0)
     {
      g_invalid_bar_resets++;
      ResetFormation();
      g_last_processed_time=0;
      return;
     }
   if(bar.time<analysis_from || bar.time>analysis_to)
     {
      if(bar.time<analysis_from) g_seen_pre_window=true;
      if(bar.time>analysis_to)   g_seen_post_window=true;
      ResetFormation();
      g_last_processed_time=0;
      return;
     }
   if(g_first_analysis_time==0) g_first_analysis_time=bar.time;
   g_last_analysis_time=bar.time;
   if(bar.time==analysis_from) g_seen_exact_first_bar=true;
   if(bar.time==analysis_to)   g_seen_exact_last_bar=true;

   bar.open=iOpen(_Symbol,PERIOD_M5,1);
   bar.high=iHigh(_Symbol,PERIOD_M5,1);
   bar.low=iLow(_Symbol,PERIOD_M5,1);
   bar.close=iClose(_Symbol,PERIOD_M5,1);
   bar.ret_pips=EMPTY_VALUE;
   bar.scale_pips=EMPTY_VALUE;
   bar.jump_threshold_pips=EMPTY_VALUE;
   bar.jump_sign=0;
   bar.jump_class_valid=false;

   if(!ValidOhlc(bar.open,bar.high,bar.low,bar.close))
     {
      g_invalid_bar_resets++;
      ResetFormation();
      g_last_processed_time=bar.time;
      return;
     }

   if(g_last_processed_time>0 && (long)(bar.time-g_last_processed_time)!=300)
     {
      g_gap_resets++;
      ResetFormation();
     }

   const int prior_count=ArraySize(g_bars);
   if(prior_count>0)
     {
      bar.ret_pips=(bar.close-g_bars[prior_count-1].close)/PipSize();
      double scale=EMPTY_VALUE;
      if(PriorMedianAbs48(scale))
        {
         bar.scale_pips=scale;
         bar.jump_threshold_pips=MathMax(JCDR_JUMP_FLOOR_PIP,JCDR_JUMP_MULTIPLIER*scale);
         bar.jump_class_valid=true;
         if(MathAbs(bar.ret_pips)>=bar.jump_threshold_pips)
            bar.jump_sign=(bar.ret_pips>0.0 ? 1 : -1);
        }
     }
   AppendBar(bar);
   g_last_processed_time=bar.time;

   PendingCluster new_cluster;
   if(TryFormCluster(new_cluster))
     {
      g_pending=new_cluster;
      g_cluster_peaks++;
      return;
     }

   if(!g_pending.active)
      return;
   g_pending.bars_after_peak++;
   if(g_pending.bars_after_peak>JCDR_DECAY_MAX_BARS)
     {
      g_decay_expired++;
      ResetPending();
      return;
     }
   if(!ThreeClosedBarsNoJump())
     {
      g_jump_in_decay++;
      return;
     }

   const double retracement=RetracementFraction(bar.close);
   if(!IsUsable(retracement) || retracement<JCDR_RETRACE_MIN || retracement>JCDR_RETRACE_MAX)
     {
      g_retrace_out_of_band++;
      return;
     }

   const int date_key=ResearchDateKey(bar.time);
   if(date_key==g_consumed_research_date)
     {
      g_daily_refractory++;
      ResetPending();
      return;
     }
   if(ExportDecision(bar.time,availability_time,retracement))
      g_consumed_research_date=date_key;
   ResetPending();
  }

double MedianArray(const double &source[])
  {
   const int count=ArraySize(source);
   if(count<=0) return(EMPTY_VALUE);
   double values[];
   ArrayCopy(values,source);
   ArraySort(values);
   if((count%2)==1) return(values[count/2]);
   return((values[count/2-1]+values[count/2])/2.0);
  }

void WriteRuntimeSummary()
  {
   const double elapsed_weeks=(double)(D'2020.12.31'-D'2016.01.04')/604800.0;
   const double cadence=(elapsed_weeks>0.0 ? (double)g_router_pass_events/elapsed_weeks : 0.0);
   int max_year_count=0;
   for(int i=0;i<5;i++) max_year_count=MathMax(max_year_count,g_year_counts[i]);
   const double max_year_share=(g_router_pass_events>0 ? (double)max_year_count/g_router_pass_events : 1.0);
   const double median_stop=MedianArray(g_pass_stops);
   const double median_cost_ratio=MedianArray(g_pass_cost_ratios);
   const int first_analysis_date=(g_first_analysis_time>0 ? ResearchDateKey(g_first_analysis_time) : 0);
   const int last_analysis_date=(g_last_analysis_time>0 ? ResearchDateKey(g_last_analysis_time) : 0);

   const bool history_selected=HistorySelect(0,TimeCurrent());
   const int deals=(history_selected ? HistoryDealsTotal() : -1);
   const int historical_orders=(history_selected ? HistoryOrdersTotal() : -1);
   const int current_orders=OrdersTotal();
   const int positions=PositionsTotal();
   const bool gate_no_trade=(history_selected && deals==0 && historical_orders==0 && current_orders==0 && positions==0);
   const bool gate_telemetry=(!g_telemetry_fatal && g_telemetry_write_failures==0);
   const bool gate_coverage=(g_seen_pre_window && g_seen_post_window &&
                             g_seen_exact_first_bar && g_seen_exact_last_bar &&
                             first_analysis_date==20160104 && last_analysis_date==20201231);
   const bool gate_handles=(g_handles_ok && g_tb_contract_mismatches==0);
   const bool gate_raw=(g_raw_events>=500);
   const bool gate_pass=(g_router_pass_events>=150);
   const bool gate_cadence=(cadence>=0.55 && cadence<=4.0);
   const bool gate_sides=(g_router_pass_long>=40 && g_router_pass_short>=40);
   const bool gate_year=(max_year_share<=0.40);
   const bool gate_match=(g_arm_rows==2*g_raw_events && g_router_pass_arm_rows==2*g_router_pass_events);
   const bool gate_stop=(IsUsable(median_stop) && median_stop>=6.0 && IsUsable(median_cost_ratio) && median_cost_ratio<=0.25);
   const bool runtime_all=(gate_no_trade && gate_telemetry && gate_coverage && gate_handles && gate_raw && gate_pass && gate_cadence && gate_sides && gate_year && gate_match && gate_stop);

   const string payload=StringFormat(
      "{\"schema_version\":\"jcdr003.router_probe_summary.v1\",\"hypothesis_id\":\"%s\",\"variant\":\"%s\",\"evidence_class\":\"OUTCOME_BLIND_ROUTER_FEASIBILITY_ONLY\",\"raw_events\":%d,\"arm_rows\":%d,\"router_pass_events\":%d,\"router_pass_arm_rows\":%d,\"router_pass_long\":%d,\"router_pass_short\":%d,\"elapsed_weeks\":%s,\"cadence_per_week\":%s,\"max_year_share\":%s,\"median_stop_pips\":%s,\"median_cost_to_stop\":%s,\"gap_resets\":%d,\"invalid_bar_resets\":%d,\"cluster_peaks\":%d,\"decay_expired\":%d,\"jump_in_decay\":%d,\"retrace_out_of_band\":%d,\"daily_refractory\":%d,\"indicator_read_failures\":%d,\"tb_contract_mismatches\":%d,\"telemetry_write_failures\":%d,\"first_analysis_date\":%d,\"last_analysis_date\":%d,\"seen_pre_window\":%s,\"seen_post_window\":%s,\"seen_exact_first_bar\":%s,\"seen_exact_last_bar\":%s,\"history_select_ok\":%s,\"deals\":%d,\"historical_orders\":%d,\"current_orders\":%d,\"positions\":%d,\"gates\":{\"no_trade\":%s,\"telemetry_integrity\":%s,\"coverage\":%s,\"handles_contract\":%s,\"raw_count\":%s,\"router_pass_count\":%s,\"cadence\":%s,\"sides\":%s,\"year_share\":%s,\"matched_arms\":%s,\"stop_geometry\":%s},\"runtime_all_pass\":%s,\"post_availability_price_reads\":0,\"performance_metrics_computed\":0,\"economics_executed\":false}",
      InpHypothesisId,InpVariantTag,g_raw_events,g_arm_rows,g_router_pass_events,g_router_pass_arm_rows,
      g_router_pass_long,g_router_pass_short,DoubleToString(elapsed_weeks,9),DoubleToString(cadence,9),
      DoubleToString(max_year_share,9),DoubleToString(median_stop,9),DoubleToString(median_cost_ratio,9),
      g_gap_resets,g_invalid_bar_resets,g_cluster_peaks,g_decay_expired,g_jump_in_decay,g_retrace_out_of_band,
      g_daily_refractory,g_indicator_read_failures,g_tb_contract_mismatches,g_telemetry_write_failures,
      first_analysis_date,last_analysis_date,(g_seen_pre_window?"true":"false"),(g_seen_post_window?"true":"false"),
      (g_seen_exact_first_bar?"true":"false"),(g_seen_exact_last_bar?"true":"false"),
      (history_selected?"true":"false"),deals,historical_orders,current_orders,positions,
      (gate_no_trade?"true":"false"),(gate_telemetry?"true":"false"),(gate_coverage?"true":"false"),
      (gate_handles?"true":"false"),(gate_raw?"true":"false"),
      (gate_pass?"true":"false"),(gate_cadence?"true":"false"),(gate_sides?"true":"false"),
      (gate_year?"true":"false"),(gate_match?"true":"false"),(gate_stop?"true":"false"),
      (runtime_all?"true":"false"));

   int meta=FileOpen(g_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(meta==INVALID_HANDLE)
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR003 fail-closed: RunMeta file could not be opened.");
      return;
     }
   const uint meta_written=FileWriteString(meta,payload);
   FileClose(meta);
   if(meta_written<(uint)StringLen(payload))
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR003 fail-closed: RunMeta payload write was incomplete.");
      return;
     }
   Print("JCDR003_SUMMARY|",payload);
  }

bool OpenTelemetry()
  {
   g_csv_handle=FileOpen(g_csv_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_csv_handle==INVALID_HANDLE) return(false);
   const uint header_written=FileWrite(g_csv_handle,
      "record_type","hypothesis_id","variant","signal_id","arm","direction",
      "cluster_peak_research_clock","decision_research_clock","availability_research_clock",
      "research_date","research_year","research_hour","cluster_sign","jump_count","coherence",
      "anchor","extreme","signed_displacement_pips","scale_at_peak_pips","threshold_at_peak_pips","retracement",
      "veto_mask","veto_reasons","router_pass","aird_valid","aird_regime","aird_confidence_pct",
      "vrc_valid","vrc_hurst","vrc_chop","vrc_vol_percentile","vrc_regime","vrc_high_vol",
      "mbb_dc_valid","mbb_basis","mbb_regime","mbb_squeeze","mbb_release",
      "qqe_primary","qqe_secondary","qqe_composite","tb_swing_high","tb_swing_low","tb_closed_valid",
      "tb_atr","tb_contract_version","base_stop_pips","tb_envelope_pips","final_stop_pips","cost_to_stop_ratio");
   if(header_written==0)
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      FileClose(g_csv_handle);
      g_csv_handle=INVALID_HANDLE;
      return(false);
     }
   FileFlush(g_csv_handle);
   return(true);
  }

int OnInit()
  {
   if(_Symbol!=InpExpectedSymbol || _Period!=PERIOD_M5 || InpHypothesisId!="HYP-JCDR-EURUSD-M5-003")
     {
      Print("JCDR003 fail-closed: exact EURUSD/M5/hypothesis binding required.");
      return(INIT_FAILED);
     }
   if(InpAnalysisFrom!="2016.01.04" || InpAnalysisTo!="2020.12.31")
     {
      Print("JCDR003 fail-closed: frozen 2016.01.04-2020.12.31 analysis window required.");
      return(INIT_FAILED);
     }
   if(!MQLInfoInteger(MQL_TESTER) || !InpResearchAutoMode || !InpEnableTelemetry)
     {
      Print("JCDR003 fail-closed: tester, explicit research mode and telemetry are mandatory.");
      return(INIT_FAILED);
     }

   g_aird_handle=iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\AI_Regime_Detection");
   g_vrc_handle =iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\Volatility_Regime_Classifier_QuantRegime");
   g_mbb_handle =iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\Modern_Bollinger_Bands_GBB");
   g_qqe_handle =iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\QQE_MOD");
   g_tb_handle  =iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\TB_Smart_Money_Concept_2026");
   g_handles_ok=(g_aird_handle!=INVALID_HANDLE && g_vrc_handle!=INVALID_HANDLE &&
                 g_mbb_handle!=INVALID_HANDLE && g_qqe_handle!=INVALID_HANDLE && g_tb_handle!=INVALID_HANDLE);
   if(!g_handles_ok)
     {
      Print("JCDR003 fail-closed: one or more indicator handles are invalid.");
      return(INIT_FAILED);
     }
   if(!OpenTelemetry())
     {
      Print("JCDR003 fail-closed: telemetry sidecar could not be opened.");
      return(INIT_FAILED);
     }

   ArrayResize(g_bars,0);
   ArrayResize(g_pass_stops,0);
   ArrayResize(g_pass_cost_ratios,0);
   ResetPending();
   g_last_open_time=iTime(_Symbol,PERIOD_M5,0); // Timestamp only; skip pre-window shift-1 bar.
   Print("JCDR003_INIT|NO_TRADE_EXPORTER|",InpHypothesisId,"|",InpVariantTag);
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   if(g_telemetry_fatal)
      return;
   const datetime current_open=iTime(_Symbol,PERIOD_M5,0); // Timestamp only; no forming-bar price read.
   if(current_open<=0 || current_open==g_last_open_time)
      return;
   g_last_open_time=current_open;
   ProcessClosedBar(current_open);
  }

void OnDeinit(const int reason)
  {
   WriteRuntimeSummary();
   if(g_csv_handle!=INVALID_HANDLE)
     {
      FileFlush(g_csv_handle);
      FileClose(g_csv_handle);
      g_csv_handle=INVALID_HANDLE;
     }
   if(g_aird_handle!=INVALID_HANDLE) IndicatorRelease(g_aird_handle);
   if(g_vrc_handle !=INVALID_HANDLE) IndicatorRelease(g_vrc_handle);
   if(g_mbb_handle !=INVALID_HANDLE) IndicatorRelease(g_mbb_handle);
   if(g_qqe_handle !=INVALID_HANDLE) IndicatorRelease(g_qqe_handle);
   if(g_tb_handle  !=INVALID_HANDLE) IndicatorRelease(g_tb_handle);
  }
