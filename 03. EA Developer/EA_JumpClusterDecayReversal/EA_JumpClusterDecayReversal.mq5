//+------------------------------------------------------------------+
//|                         EA_JumpClusterDecayReversal.mq5          |
//| HYP-JCDR-EURUSD-M5-005: full-stage alignment diagnostic         |
//|                                                                  |
//| IMPORTANT                                                        |
//| - This build is a NO-TRADE exporter.                             |
//| - JCDR is the sole event clock; every raw event is exported.      |
//| - Indicators are observed as continuous/temporal state only.     |
//| - No route, entry direction, outcome or future price is exported.|
//| - TB SMC geometry is counterfactual for BOTH directions.          |
//| - Price OHLC is read only from shift 1 or older.                 |
//+------------------------------------------------------------------+
#property strict
#property version   "1.20"
#property description "Outcome-blind broker-native JCDR full-stage diagnostic exporter"
#property tester_indicator "AlphaFactory\\AI_Regime_Detection.ex5"
#property tester_indicator "AlphaFactory\\Volatility_Regime_Classifier_QuantRegime.ex5"
#property tester_indicator "AlphaFactory\\Modern_Bollinger_Bands_GBB.ex5"
#property tester_indicator "AlphaFactory\\QQE_MOD.ex5"
#property tester_indicator "AlphaFactory\\TB_Smart_Money_Concept_2026.ex5"

input string InpHypothesisId    = "HYP-JCDR-EURUSD-M5-005";
input string InpExpectedSymbol  = "EURUSD";
input bool   InpResearchAutoMode= false; // Must be explicitly enabled by preregistered probe.
input bool   InpEnableTelemetry = true;  // Mandatory for the no-trade feasibility run.
input string InpVariantTag      = "JCDR_STAGE_ALIGNMENT_V1";
input string InpAnalysisFrom    = "2016.01.04"; // Exact fixed-window tester and analysis start.
input string InpAnalysisTo      = "2020.12.31"; // Exact fixed-window tester and analysis end.

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

// ABI/validity bits are diagnostics only.  They explicitly distinguish an
// unavailable indicator observation from a numeric zero.
const int INVALID_AIRD = 1;
const int INVALID_VRC  = 2;
const int INVALID_MBB  = 4;
const int INVALID_QQE  = 8;
const int INVALID_TB   = 16;

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

struct DiagnosticSnapshot
  {
   int    invalid_mask;
   double aird_valid;
   double aird_held_regime;
   double aird_held_confidence;
   double aird_raw_regime;
   double aird_raw_probability;
   double aird_p_bull;
   double aird_p_bear;
   double aird_p_range;
   double aird_p_highvol;
   double aird_trend_corr;
   double aird_momentum;
   double aird_vol_percentile;
   double aird_drift;
   double aird_changed;
   double aird_regime_age;
   double aird_aligned_probability;
   double aird_opposite_probability;
   double vrc_valid;
   double vrc_hurst;
   double vrc_adx;
   double vrc_di_plus;
   double vrc_di_minus;
   double vrc_chop;
   double vrc_vol_percentile;
   double vrc_atr;
   double vrc_composite;
   double vrc_direction;
   double vrc_regime;
   double vrc_changed;
   double vrc_high_vol;
   double vrc_low_vol;
   double vrc_trend_score;
   double vrc_chop_score;
   double vrc_hurst_score;
   int    vrc_change_age;
   double vrc_cluster_alignment;
   double mbb_dc_valid;
   double mbb_adaptive_length;
   double mbb_ker;
   double mbb_ker_percentile;
   double mbb_regime;
   double mbb_bandwidth;
   double mbb_squeeze_score;
   double mbb_squeeze_state;
   double mbb_release;
   double mbb_priority_signal;
   int    mbb_squeeze_age;
   int    mbb_release_age;
   double mbb_signal_alignment;
   double qqe_primary;
   double qqe_secondary;
   double qqe_composite;
   double qqe_zero_cross;
   double qqe_primary_alignment;
   double qqe_secondary_alignment;
   int    qqe_composite_change_age;
   int    qqe_zero_cross_age;
   double tb_closed_valid;
   double tb_contract_version;
   double tb_bias;
   double tb_structure_event;
   double tb_sweep_high;
   double tb_sweep_low;
   double tb_void_bull;
   double tb_void_bear;
   double tb_displacement_bull;
   double tb_displacement_bear;
   double tb_swing_high;
   double tb_swing_low;
   double tb_atr;
   double tb_break_level;
   double tb_cell_age;
   double tb_void_age;
   double tb_displacement_ratio;
   double tb_void_size_atr;
   double tb_cell_size_atr;
   double tb_ready_mask;
   double tb_nearest_liquidity_high;
   double tb_nearest_liquidity_low;
   double tb_has_liquidity_high;
   double tb_has_liquidity_low;
   int    tb_structure_age;
   int    tb_sweep_high_age;
   int    tb_sweep_low_age;
   double long_stop_level;
   double long_stop_pips;
   double long_corridor_pips;
   int    long_geometry_pass;
   double short_stop_level;
   double short_stop_pips;
   double short_corridor_pips;
   int    short_geometry_pass;
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
bool g_seen_first_date=false;
bool g_seen_last_date=false;
bool g_series_proof_ok=false;
int  g_raw_events=0;
int  g_diagnostic_rows=0;
int  g_invalid_core_rows=0;
int  g_complete_rows=0;
int  g_tb_both_geometry_rows=0;
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
int  g_accounted_indicator_read_failures=0;
int  g_accounted_tb_contract_mismatches=0;
int  g_unaccounted_diagnostic_failures=0;
int  g_telemetry_write_failures=0;

string g_csv_name="EURUSD_JCDR005_StageTelemetry_HYP_JCDR_EURUSD_M5_005.csv";
string g_meta_name="JCDR005_RunMeta_HYP_JCDR_EURUSD_M5_005.json";

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

bool ReadBufferValueAt(const int handle,const int buffer,const int shift,double &value)
  {
   double data[];
   value=EMPTY_VALUE;
   // HYP005 invariant: the forming bar (shift 0) is never observable.
   if(shift<1 || handle==INVALID_HANDLE)
     {
      g_indicator_read_failures++;
      return(false);
     }
   ArrayResize(data,shift);
   // start_pos is deliberately the literal closed-bar shift 1. CopyBuffer
   // stores the oldest requested element at data[0], so requesting `shift`
   // values makes data[0] exactly the requested historical closed bar.
   if(CopyBuffer(handle,buffer,1,shift,data)!=shift)
     {
      g_indicator_read_failures++;
      return(false);
     }
   value=data[0];
   return(true);
  }

bool ReadClosedBufferValue(const int handle,const int buffer,double &value)
  {
   return(ReadBufferValueAt(handle,buffer,1,value));
  }

bool IsExactFlag(const double value)
  {
   return(IsUsable(value) && (value==0.0 || value==1.0));
  }

bool IsExactTernary(const double value)
  {
   return(IsUsable(value) && (value==-1.0 || value==0.0 || value==1.0));
  }

string InvalidText(const int mask)
  {
   if(mask==0) return("NONE");
   string out="";
   if((mask&INVALID_AIRD)!=0) out+="AIRD_INVALID|";
   if((mask&INVALID_VRC )!=0) out+="VRC_INVALID|";
   if((mask&INVALID_MBB )!=0) out+="MBB_INVALID|";
   if((mask&INVALID_QQE )!=0) out+="QQE_INVALID|";
   if((mask&INVALID_TB  )!=0) out+="TB_INVALID|";
   if(StringLen(out)>0) out=StringSubstr(out,0,StringLen(out)-1);
   return(out);
  }

int LatestFlagAge(const int handle,const int buffer,const int max_age,bool &ok)
  {
   for(int shift=1;shift<=max_age;shift++)
     {
      double value=EMPTY_VALUE;
      if(!ReadBufferValueAt(handle,buffer,shift,value) || !IsExactTernary(value))
        {
         ok=false;
         return(max_age);
        }
      if(value!=0.0)
         return(shift-1);
     }
   return(max_age);
  }

int LatestEventAge(const int handle,const int buffer,const int max_age,bool &ok)
  {
   // Event-code buffers may carry magnitudes above one (TB MSS is +/-2), so
   // only finiteness and non-zero occurrence are required here.
   for(int shift=1;shift<=max_age;shift++)
     {
      double value=EMPTY_VALUE;
      if(!ReadBufferValueAt(handle,buffer,shift,value) || !IsUsable(value))
        {
         ok=false;
         return(max_age);
        }
      if(value!=0.0)
         return(shift-1);
     }
   return(max_age);
  }

int StateChangeAge(const int handle,const int buffer,const double current,const int max_age,bool &ok)
  {
   if(!IsUsable(current))
     {
      ok=false;
      return(max_age);
     }
   for(int shift=2;shift<=max_age+1;shift++)
     {
      double value=EMPTY_VALUE;
      if(!ReadBufferValueAt(handle,buffer,shift,value) || !IsUsable(value))
        {
         ok=false;
         return(max_age);
        }
      if(value!=current)
         return(shift-2);
     }
   return(max_age);
  }

int ConsecutiveFlagAge(const int handle,const int buffer,const double current,const int max_age,bool &ok)
  {
   if(!IsExactFlag(current))
     {
      ok=false;
      return(-1);
     }
   if(current==0.0)
      return(-1);
   for(int shift=2;shift<=max_age+1;shift++)
     {
      double value=EMPTY_VALUE;
      if(!ReadBufferValueAt(handle,buffer,shift,value) || !IsExactFlag(value))
        {
         ok=false;
         return(max_age);
        }
      if(value==0.0)
         return(shift-2);
     }
   return(max_age);
  }

void InitializeDiagnostic(DiagnosticSnapshot &s)
  {
   ZeroMemory(s);
   s.aird_valid=EMPTY_VALUE; s.aird_held_regime=EMPTY_VALUE; s.aird_held_confidence=EMPTY_VALUE;
   s.aird_raw_regime=EMPTY_VALUE; s.aird_raw_probability=EMPTY_VALUE;
   s.aird_p_bull=EMPTY_VALUE; s.aird_p_bear=EMPTY_VALUE; s.aird_p_range=EMPTY_VALUE; s.aird_p_highvol=EMPTY_VALUE;
   s.aird_trend_corr=EMPTY_VALUE; s.aird_momentum=EMPTY_VALUE; s.aird_vol_percentile=EMPTY_VALUE;
   s.aird_drift=EMPTY_VALUE; s.aird_changed=EMPTY_VALUE; s.aird_regime_age=EMPTY_VALUE;
   s.aird_aligned_probability=EMPTY_VALUE; s.aird_opposite_probability=EMPTY_VALUE;
   s.vrc_valid=EMPTY_VALUE; s.vrc_hurst=EMPTY_VALUE; s.vrc_adx=EMPTY_VALUE; s.vrc_di_plus=EMPTY_VALUE;
   s.vrc_di_minus=EMPTY_VALUE; s.vrc_chop=EMPTY_VALUE; s.vrc_vol_percentile=EMPTY_VALUE; s.vrc_atr=EMPTY_VALUE;
   s.vrc_composite=EMPTY_VALUE; s.vrc_direction=EMPTY_VALUE; s.vrc_regime=EMPTY_VALUE; s.vrc_changed=EMPTY_VALUE;
   s.vrc_high_vol=EMPTY_VALUE; s.vrc_low_vol=EMPTY_VALUE; s.vrc_trend_score=EMPTY_VALUE;
   s.vrc_chop_score=EMPTY_VALUE; s.vrc_hurst_score=EMPTY_VALUE; s.vrc_change_age=-1; s.vrc_cluster_alignment=EMPTY_VALUE;
   s.mbb_dc_valid=EMPTY_VALUE; s.mbb_adaptive_length=EMPTY_VALUE; s.mbb_ker=EMPTY_VALUE;
   s.mbb_ker_percentile=EMPTY_VALUE; s.mbb_regime=EMPTY_VALUE; s.mbb_bandwidth=EMPTY_VALUE;
   s.mbb_squeeze_score=EMPTY_VALUE; s.mbb_squeeze_state=EMPTY_VALUE; s.mbb_release=EMPTY_VALUE;
   s.mbb_priority_signal=EMPTY_VALUE; s.mbb_squeeze_age=-1; s.mbb_release_age=-1; s.mbb_signal_alignment=EMPTY_VALUE;
   s.qqe_primary=EMPTY_VALUE; s.qqe_secondary=EMPTY_VALUE; s.qqe_composite=EMPTY_VALUE; s.qqe_zero_cross=EMPTY_VALUE;
   s.qqe_primary_alignment=EMPTY_VALUE; s.qqe_secondary_alignment=EMPTY_VALUE;
   s.qqe_composite_change_age=-1; s.qqe_zero_cross_age=-1;
   s.tb_closed_valid=EMPTY_VALUE; s.tb_contract_version=EMPTY_VALUE; s.tb_bias=EMPTY_VALUE;
   s.tb_structure_event=EMPTY_VALUE; s.tb_sweep_high=EMPTY_VALUE; s.tb_sweep_low=EMPTY_VALUE;
   s.tb_void_bull=EMPTY_VALUE; s.tb_void_bear=EMPTY_VALUE; s.tb_displacement_bull=EMPTY_VALUE;
   s.tb_displacement_bear=EMPTY_VALUE; s.tb_swing_high=EMPTY_VALUE; s.tb_swing_low=EMPTY_VALUE;
   s.tb_atr=EMPTY_VALUE; s.tb_break_level=EMPTY_VALUE; s.tb_cell_age=EMPTY_VALUE; s.tb_void_age=EMPTY_VALUE;
   s.tb_displacement_ratio=EMPTY_VALUE; s.tb_void_size_atr=EMPTY_VALUE; s.tb_cell_size_atr=EMPTY_VALUE;
   s.tb_ready_mask=EMPTY_VALUE; s.tb_nearest_liquidity_high=EMPTY_VALUE; s.tb_nearest_liquidity_low=EMPTY_VALUE;
   s.tb_has_liquidity_high=EMPTY_VALUE; s.tb_has_liquidity_low=EMPTY_VALUE;
   s.tb_structure_age=-1; s.tb_sweep_high_age=-1; s.tb_sweep_low_age=-1;
   s.long_stop_level=EMPTY_VALUE; s.long_stop_pips=EMPTY_VALUE; s.long_corridor_pips=EMPTY_VALUE;
   s.short_stop_level=EMPTY_VALUE; s.short_stop_pips=EMPTY_VALUE; s.short_corridor_pips=EMPTY_VALUE;
   s.long_geometry_pass=-1; s.short_geometry_pass=-1; // -1 means TB geometry unavailable, never a silent false.
  }

void BuildDiagnosticSnapshot(const int cluster_sign,const double decision_close,DiagnosticSnapshot &s)
  {
   InitializeDiagnostic(s);

   bool aird_ok=true;
   aird_ok&=ReadClosedBufferValue(g_aird_handle,11,s.aird_valid);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,12,s.aird_held_regime);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,5,s.aird_held_confidence);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,14,s.aird_raw_regime);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,15,s.aird_raw_probability);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,7,s.aird_p_bull);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,8,s.aird_p_bear);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,9,s.aird_p_range);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,10,s.aird_p_highvol);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,16,s.aird_trend_corr);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,17,s.aird_momentum);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,18,s.aird_vol_percentile);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,19,s.aird_drift);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,13,s.aird_changed);
   aird_ok&=ReadClosedBufferValue(g_aird_handle,22,s.aird_regime_age);
   if(!aird_ok || s.aird_valid!=1.0 || !IsUsable(s.aird_held_regime) ||
      !IsUsable(s.aird_held_confidence) || !IsUsable(s.aird_raw_regime) ||
      !IsUsable(s.aird_raw_probability) || !IsUsable(s.aird_p_bull) || !IsUsable(s.aird_p_bear) ||
      !IsUsable(s.aird_p_range) || !IsUsable(s.aird_p_highvol) || !IsExactFlag(s.aird_changed))
      s.invalid_mask|=INVALID_AIRD;
   else
     {
      s.aird_aligned_probability=(cluster_sign>0 ? s.aird_p_bull : s.aird_p_bear);
      s.aird_opposite_probability=(cluster_sign>0 ? s.aird_p_bear : s.aird_p_bull);
     }

   bool vrc_ok=true;
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,31,s.vrc_valid);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,14,s.vrc_hurst);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,15,s.vrc_adx);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,16,s.vrc_di_plus);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,17,s.vrc_di_minus);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,18,s.vrc_chop);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,19,s.vrc_vol_percentile);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,20,s.vrc_atr);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,21,s.vrc_composite);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,22,s.vrc_direction);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,23,s.vrc_regime);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,24,s.vrc_changed);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,26,s.vrc_high_vol);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,27,s.vrc_low_vol);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,32,s.vrc_trend_score);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,33,s.vrc_chop_score);
   vrc_ok&=ReadClosedBufferValue(g_vrc_handle,34,s.vrc_hurst_score);
   s.vrc_change_age=LatestFlagAge(g_vrc_handle,24,12,vrc_ok);
   if(!vrc_ok || s.vrc_valid!=1.0 || !IsUsable(s.vrc_hurst) || !IsUsable(s.vrc_adx) ||
      !IsUsable(s.vrc_di_plus) || !IsUsable(s.vrc_di_minus) || !IsUsable(s.vrc_chop) ||
      !IsUsable(s.vrc_vol_percentile) || !IsUsable(s.vrc_atr) || !IsUsable(s.vrc_composite) ||
      !IsUsable(s.vrc_direction) || !IsUsable(s.vrc_regime) || !IsExactFlag(s.vrc_changed) ||
      !IsExactFlag(s.vrc_high_vol) || !IsExactFlag(s.vrc_low_vol))
      s.invalid_mask|=INVALID_VRC;
   else
      s.vrc_cluster_alignment=cluster_sign*s.vrc_direction;

   bool mbb_ok=true;
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,16,s.mbb_dc_valid);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,17,s.mbb_adaptive_length);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,18,s.mbb_ker);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,19,s.mbb_ker_percentile);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,20,s.mbb_regime);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,21,s.mbb_bandwidth);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,22,s.mbb_squeeze_score);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,23,s.mbb_squeeze_state);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,24,s.mbb_release);
   mbb_ok&=ReadClosedBufferValue(g_mbb_handle,31,s.mbb_priority_signal);
   s.mbb_squeeze_age=ConsecutiveFlagAge(g_mbb_handle,23,s.mbb_squeeze_state,20,mbb_ok);
   s.mbb_release_age=LatestFlagAge(g_mbb_handle,24,20,mbb_ok);
   if(!mbb_ok || s.mbb_dc_valid!=1.0 || !IsUsable(s.mbb_adaptive_length) || !IsUsable(s.mbb_ker) ||
      !IsUsable(s.mbb_ker_percentile) || !IsUsable(s.mbb_regime) || !IsUsable(s.mbb_bandwidth) ||
      !IsUsable(s.mbb_squeeze_score) || !IsExactFlag(s.mbb_squeeze_state) ||
      !IsExactFlag(s.mbb_release) || !IsUsable(s.mbb_priority_signal))
      s.invalid_mask|=INVALID_MBB;
   else
      s.mbb_signal_alignment=cluster_sign*s.mbb_priority_signal;

   bool qqe_ok=true;
   qqe_ok&=ReadClosedBufferValue(g_qqe_handle,3,s.qqe_primary);
   qqe_ok&=ReadClosedBufferValue(g_qqe_handle,4,s.qqe_secondary);
   qqe_ok&=ReadClosedBufferValue(g_qqe_handle,8,s.qqe_composite);
   qqe_ok&=ReadClosedBufferValue(g_qqe_handle,9,s.qqe_zero_cross);
   s.qqe_composite_change_age=StateChangeAge(g_qqe_handle,8,s.qqe_composite,12,qqe_ok);
   s.qqe_zero_cross_age=LatestFlagAge(g_qqe_handle,9,12,qqe_ok);
   if(!qqe_ok || !IsUsable(s.qqe_primary) || !IsUsable(s.qqe_secondary) ||
      !IsExactTernary(s.qqe_composite) || !IsExactTernary(s.qqe_zero_cross))
      s.invalid_mask|=INVALID_QQE;
   else
     {
      s.qqe_primary_alignment=cluster_sign*s.qqe_primary;
      s.qqe_secondary_alignment=cluster_sign*s.qqe_secondary;
     }

   bool tb_ok=true;
   tb_ok&=ReadClosedBufferValue(g_tb_handle,26,s.tb_closed_valid);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,43,s.tb_contract_version);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,2,s.tb_bias);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,27,s.tb_structure_event);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,7,s.tb_sweep_high);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,8,s.tb_sweep_low);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,9,s.tb_void_bull);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,10,s.tb_void_bear);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,11,s.tb_displacement_bull);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,12,s.tb_displacement_bear);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,13,s.tb_swing_high);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,14,s.tb_swing_low);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,28,s.tb_atr);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,29,s.tb_break_level);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,34,s.tb_cell_age);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,35,s.tb_void_age);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,36,s.tb_displacement_ratio);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,37,s.tb_void_size_atr);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,38,s.tb_cell_size_atr);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,39,s.tb_ready_mask);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,44,s.tb_nearest_liquidity_high);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,45,s.tb_nearest_liquidity_low);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,46,s.tb_has_liquidity_high);
   tb_ok&=ReadClosedBufferValue(g_tb_handle,47,s.tb_has_liquidity_low);
   s.tb_structure_age=LatestEventAge(g_tb_handle,27,20,tb_ok);
   s.tb_sweep_high_age=LatestFlagAge(g_tb_handle,7,20,tb_ok);
   s.tb_sweep_low_age=LatestFlagAge(g_tb_handle,8,20,tb_ok);
   if(IsUsable(s.tb_contract_version) && s.tb_contract_version!=3.0)
      g_tb_contract_mismatches++;
   const bool tb_geometry_values=(IsUsable(s.tb_swing_high) && IsUsable(s.tb_swing_low) &&
                                  s.tb_swing_low<s.tb_swing_high && IsUsable(s.tb_atr) && s.tb_atr>0.0);
   if(!tb_ok || s.tb_closed_valid!=1.0 || s.tb_contract_version!=3.0 || !tb_geometry_values)
      s.invalid_mask|=INVALID_TB;
   else
     {
      const double pip=PipSize();
      s.long_stop_level=MathMin(MathMin(g_pending.anchor,g_pending.extreme),s.tb_swing_low)-JCDR_STOP_BUFFER_PIP*pip;
      s.long_stop_pips=MathAbs(decision_close-s.long_stop_level)/pip;
      s.long_corridor_pips=(s.tb_swing_high-decision_close)/pip;
      s.long_geometry_pass=(s.long_stop_pips>=JCDR_MIN_STOP_PIP && s.long_corridor_pips>=s.long_stop_pips ? 1 : 0);
      s.short_stop_level=MathMax(MathMax(g_pending.anchor,g_pending.extreme),s.tb_swing_high)+JCDR_STOP_BUFFER_PIP*pip;
      s.short_stop_pips=MathAbs(s.short_stop_level-decision_close)/pip;
      s.short_corridor_pips=(decision_close-s.tb_swing_low)/pip;
      s.short_geometry_pass=(s.short_stop_pips>=JCDR_MIN_STOP_PIP && s.short_corridor_pips>=s.short_stop_pips ? 1 : 0);
     }
  }

string CsvDouble(const double value)
  {
   return(IsUsable(value) ? DoubleToString(value,12) : "");
  }

void CsvAddString(string &row,const string value) { row+=","+value; }
void CsvAddInt(string &row,const int value)       { row+=","+IntegerToString(value); }
void CsvAddDouble(string &row,const double value) { row+=","+CsvDouble(value); }

bool WriteDiagnosticRow(const string event_id,const datetime decision_time,const datetime availability_time,
                        const double retracement,const double decision_close,const DiagnosticSnapshot &s)
  {
   if(g_csv_handle==INVALID_HANDLE)
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      return(false);
     }
   string row="EVENT_DIAGNOSTIC";
   CsvAddString(row,InpHypothesisId); CsvAddString(row,InpVariantTag); CsvAddString(row,event_id);
   CsvAddString(row,TimeIso(g_pending.peak_time)); CsvAddString(row,TimeIso(decision_time)); CsvAddString(row,TimeIso(availability_time));
   CsvAddInt(row,ResearchDateKey(decision_time)); CsvAddInt(row,ResearchYear(decision_time)); CsvAddInt(row,ResearchHour(decision_time));
   CsvAddInt(row,g_pending.dominant_sign); CsvAddInt(row,g_pending.jump_count); CsvAddDouble(row,g_pending.coherence);
   CsvAddDouble(row,g_pending.anchor); CsvAddDouble(row,g_pending.extreme); CsvAddDouble(row,g_pending.signed_displacement_pips);
   CsvAddDouble(row,g_pending.scale_at_peak); CsvAddDouble(row,g_pending.threshold_at_peak); CsvAddDouble(row,retracement); CsvAddDouble(row,decision_close);
   CsvAddInt(row,s.invalid_mask); CsvAddString(row,InvalidText(s.invalid_mask));
   CsvAddDouble(row,s.aird_valid); CsvAddDouble(row,s.aird_held_regime); CsvAddDouble(row,s.aird_held_confidence);
   CsvAddDouble(row,s.aird_raw_regime); CsvAddDouble(row,s.aird_raw_probability); CsvAddDouble(row,s.aird_p_bull);
   CsvAddDouble(row,s.aird_p_bear); CsvAddDouble(row,s.aird_p_range); CsvAddDouble(row,s.aird_p_highvol);
   CsvAddDouble(row,s.aird_trend_corr); CsvAddDouble(row,s.aird_momentum); CsvAddDouble(row,s.aird_vol_percentile);
   CsvAddDouble(row,s.aird_drift); CsvAddDouble(row,s.aird_changed); CsvAddDouble(row,s.aird_regime_age);
   CsvAddDouble(row,s.aird_aligned_probability); CsvAddDouble(row,s.aird_opposite_probability);
   CsvAddDouble(row,s.vrc_valid); CsvAddDouble(row,s.vrc_hurst); CsvAddDouble(row,s.vrc_adx); CsvAddDouble(row,s.vrc_di_plus);
   CsvAddDouble(row,s.vrc_di_minus); CsvAddDouble(row,s.vrc_chop); CsvAddDouble(row,s.vrc_vol_percentile); CsvAddDouble(row,s.vrc_atr);
   CsvAddDouble(row,s.vrc_composite); CsvAddDouble(row,s.vrc_direction); CsvAddDouble(row,s.vrc_regime); CsvAddDouble(row,s.vrc_changed);
   CsvAddDouble(row,s.vrc_high_vol); CsvAddDouble(row,s.vrc_low_vol); CsvAddDouble(row,s.vrc_trend_score);
   CsvAddDouble(row,s.vrc_chop_score); CsvAddDouble(row,s.vrc_hurst_score); CsvAddInt(row,s.vrc_change_age); CsvAddDouble(row,s.vrc_cluster_alignment);
   CsvAddDouble(row,s.mbb_dc_valid); CsvAddDouble(row,s.mbb_adaptive_length); CsvAddDouble(row,s.mbb_ker); CsvAddDouble(row,s.mbb_ker_percentile);
   CsvAddDouble(row,s.mbb_regime); CsvAddDouble(row,s.mbb_bandwidth); CsvAddDouble(row,s.mbb_squeeze_score);
   CsvAddDouble(row,s.mbb_squeeze_state); CsvAddDouble(row,s.mbb_release); CsvAddDouble(row,s.mbb_priority_signal);
   CsvAddInt(row,s.mbb_squeeze_age); CsvAddInt(row,s.mbb_release_age); CsvAddDouble(row,s.mbb_signal_alignment);
   CsvAddDouble(row,s.qqe_primary); CsvAddDouble(row,s.qqe_secondary); CsvAddDouble(row,s.qqe_composite); CsvAddDouble(row,s.qqe_zero_cross);
   CsvAddDouble(row,s.qqe_primary_alignment); CsvAddDouble(row,s.qqe_secondary_alignment);
   CsvAddInt(row,s.qqe_composite_change_age); CsvAddInt(row,s.qqe_zero_cross_age);
   CsvAddDouble(row,s.tb_closed_valid); CsvAddDouble(row,s.tb_contract_version); CsvAddDouble(row,s.tb_bias); CsvAddDouble(row,s.tb_structure_event);
   CsvAddDouble(row,s.tb_sweep_high); CsvAddDouble(row,s.tb_sweep_low); CsvAddDouble(row,s.tb_void_bull); CsvAddDouble(row,s.tb_void_bear);
   CsvAddDouble(row,s.tb_displacement_bull); CsvAddDouble(row,s.tb_displacement_bear); CsvAddDouble(row,s.tb_swing_high); CsvAddDouble(row,s.tb_swing_low);
   CsvAddDouble(row,s.tb_atr); CsvAddDouble(row,s.tb_break_level); CsvAddDouble(row,s.tb_cell_age); CsvAddDouble(row,s.tb_void_age);
   CsvAddDouble(row,s.tb_displacement_ratio); CsvAddDouble(row,s.tb_void_size_atr); CsvAddDouble(row,s.tb_cell_size_atr); CsvAddDouble(row,s.tb_ready_mask);
   CsvAddDouble(row,s.tb_nearest_liquidity_high); CsvAddDouble(row,s.tb_nearest_liquidity_low);
   CsvAddDouble(row,s.tb_has_liquidity_high); CsvAddDouble(row,s.tb_has_liquidity_low);
   CsvAddInt(row,s.tb_structure_age); CsvAddInt(row,s.tb_sweep_high_age); CsvAddInt(row,s.tb_sweep_low_age);
   CsvAddDouble(row,s.long_stop_level); CsvAddDouble(row,s.long_stop_pips); CsvAddDouble(row,s.long_corridor_pips); CsvAddInt(row,s.long_geometry_pass);
   CsvAddDouble(row,s.short_stop_level); CsvAddDouble(row,s.short_stop_pips); CsvAddDouble(row,s.short_corridor_pips); CsvAddInt(row,s.short_geometry_pass);
   const uint written=FileWriteString(g_csv_handle,row+"\r\n");
   if(written<(uint)(StringLen(row)+2))
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR005 fail-closed: diagnostic telemetry row write failed for ",event_id);
      return(false);
     }
   return(true);
  }

bool ExportDecision(const datetime decision_time,const datetime availability_time,const double retracement)
  {
   DiagnosticSnapshot snapshot;
   const double decision_close=g_bars[ArraySize(g_bars)-1].close;
   const int read_failures_before=g_indicator_read_failures;
   const int tb_mismatches_before=g_tb_contract_mismatches;
   BuildDiagnosticSnapshot(g_pending.dominant_sign,decision_close,snapshot);
   const int read_failure_delta=g_indicator_read_failures-read_failures_before;
   const int tb_mismatch_delta=g_tb_contract_mismatches-tb_mismatches_before;

   // Every technical failure must be visible in the same row's invalid mask.
   if(read_failure_delta>0)
     {
      if(snapshot.invalid_mask!=0) g_accounted_indicator_read_failures+=read_failure_delta;
      else g_unaccounted_diagnostic_failures+=read_failure_delta;
     }
   if(tb_mismatch_delta>0)
     {
      if((snapshot.invalid_mask&INVALID_TB)!=0) g_accounted_tb_contract_mismatches+=tb_mismatch_delta;
      else g_unaccounted_diagnostic_failures+=tb_mismatch_delta;
     }

   g_raw_events++;
   const string event_id=StringFormat("JCDR005-EVT-%I64d-%06d",(long)decision_time,g_raw_events);
   if(!WriteDiagnosticRow(event_id,decision_time,availability_time,retracement,decision_close,snapshot))
      return(false);
   g_diagnostic_rows++;
   if(snapshot.invalid_mask!=0) g_invalid_core_rows++;
   // A valid all-zero value is distinguishable from missing data through the
   // explicit mask, so every written row satisfies schema completeness.
   if(snapshot.invalid_mask!=0 || (IsUsable(snapshot.aird_p_bull) && IsUsable(snapshot.vrc_hurst) &&
                                  IsUsable(snapshot.mbb_squeeze_score) && IsUsable(snapshot.qqe_primary)))
      g_complete_rows++;
   if((snapshot.invalid_mask&INVALID_TB)==0 && IsUsable(snapshot.long_stop_pips) &&
      IsUsable(snapshot.long_corridor_pips) && IsUsable(snapshot.short_stop_pips) &&
      IsUsable(snapshot.short_corridor_pips))
      g_tb_both_geometry_rows++;
   const int year=ResearchYear(decision_time);
   if(year>=2016 && year<=2020) g_year_counts[year-2016]++;
   FileFlush(g_csv_handle);
   return(true);
  }

void ProcessClosedBar(const datetime availability_time)
  {
   JcdrBar bar;
   ZeroMemory(bar);
   bar.time=iTime(_Symbol,PERIOD_M5,1);

   // HYP-005 analyzes the exact frozen window while the tester envelope ends
   // on 2021.01.01 so the final 2020.12.31 M5 bar is actually observable.
   // accidental state carry or price reads if the tester config drifts.
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
      ResetFormation();
      g_last_processed_time=0;
      return;
     }
   if(g_first_analysis_time==0) g_first_analysis_time=bar.time;
   g_last_analysis_time=bar.time;
   const int observed_date=ResearchDateKey(bar.time);
   if(observed_date==20160104) g_seen_first_date=true;
   if(observed_date==20201231) g_seen_last_date=true;

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

string BoolJson(const bool value)
  {
   return(value ? "true" : "false");
  }

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property_id,
                       const string field_name,long &value)
  {
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property_id,value))
     {
      PrintFormat("JCDR005_SERIES_FAIL field=%s timeframe=%d error=%d",field_name,(int)timeframe,GetLastError());
      return(false);
     }
   return(true);
  }

bool EmitDataEpochSeriesProof()
  {
   long m5_synchronized=0;
   long m5_first_epoch=0;
   long m5_terminal_first_epoch=0;
   long m1_server_first_epoch=0;
   long m1_terminal_first_epoch=0;
   long m5_bars=0;
   long terminal_maxbars=0;
   if(!ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED,"m5_synchronized",m5_synchronized) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,"m5_first_epoch",m5_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,"m5_terminal_first_epoch",m5_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,"m1_server_first_epoch",m1_server_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,"m1_terminal_first_epoch",m1_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT,"m5_bars",m5_bars))
      return(false);

   ResetLastError();
   terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();

   datetime copytime_values[];
   ArraySetAsSeries(copytime_values,false);
   const datetime copytime_from=(datetime)m5_first_epoch;
   ResetLastError();
   const int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);
   const int copytime_error=GetLastError();
   long copytime_first_epoch=0;
   if(copytime_result==1)
      copytime_first_epoch=(long)copytime_values[0];

   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,m5_synchronized,m5_first_epoch,m5_terminal_first_epoch,
               m1_server_first_epoch,m1_terminal_first_epoch,m5_bars,terminal_maxbars,
               (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);

   if(m5_synchronized!=1 || m5_first_epoch<=0 || m5_terminal_first_epoch<=0 ||
      m1_server_first_epoch<=0 || m1_terminal_first_epoch<=0 || m5_bars<=0 ||
      terminal_maxbars<=0 || terminal_error!=0 || copytime_result!=1 ||
      copytime_first_epoch!=m5_first_epoch || copytime_error!=0)
      return(false);
   return(true);
  }

void CountDealTypes(const bool history_selected,int &total_deals,int &trading_deals,
                    int &balance_operations,int &other_deals)
  {
   total_deals=(history_selected ? HistoryDealsTotal() : -1);
   trading_deals=0;
   balance_operations=0;
   other_deals=0;
   if(!history_selected)
      return;
   for(int i=0;i<total_deals;i++)
     {
      const ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0)
        {
         other_deals++;
         continue;
        }
      const ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(ticket,DEAL_TYPE);
      if(type==DEAL_TYPE_BUY || type==DEAL_TYPE_SELL)
         trading_deals++;
      else if(type==DEAL_TYPE_BALANCE)
         balance_operations++;
      else
         other_deals++;
     }
  }

void WriteRuntimeSummary()
  {
   int max_year_count=0;
   for(int i=0;i<5;i++) max_year_count=MathMax(max_year_count,g_year_counts[i]);
   const double max_year_share=(g_raw_events>0 ? (double)max_year_count/g_raw_events : 1.0);
   const double invalid_core_share=(g_diagnostic_rows>0 ? (double)g_invalid_core_rows/g_diagnostic_rows : 1.0);
   const int first_analysis_date=(g_first_analysis_time>0 ? ResearchDateKey(g_first_analysis_time) : 0);
   const int last_analysis_date=(g_last_analysis_time>0 ? ResearchDateKey(g_last_analysis_time) : 0);

   const bool history_selected=HistorySelect(0,TimeCurrent());
   int total_deals=0;
   int trading_deals=0;
   int balance_operations=0;
   int other_deals=0;
   CountDealTypes(history_selected,total_deals,trading_deals,balance_operations,other_deals);
   const int historical_orders=(history_selected ? HistoryOrdersTotal() : -1);
   const int current_orders=OrdersTotal();
   const int positions=PositionsTotal();
   const bool gate_no_trade=(history_selected && trading_deals==0 && other_deals==0 &&
                             balance_operations<=1 && historical_orders==0 && current_orders==0 && positions==0);
   const bool gate_telemetry=(!g_telemetry_fatal && g_telemetry_write_failures==0);
   const bool gate_coverage=(g_series_proof_ok && g_seen_first_date && g_seen_last_date &&
                             first_analysis_date==20160104 && last_analysis_date==20201231);
   const bool gate_handles=(g_handles_ok && g_unaccounted_diagnostic_failures==0 &&
                            g_accounted_indicator_read_failures==g_indicator_read_failures &&
                            g_accounted_tb_contract_mismatches==g_tb_contract_mismatches);
   const bool gate_raw=(g_raw_events>=900);
   const bool gate_one_row=(g_diagnostic_rows==g_raw_events);
   const bool gate_invalid_share=(invalid_core_share<=0.05);
   const bool gate_complete=(g_complete_rows>=900);
   const bool gate_tb_geometry=(g_tb_both_geometry_rows>=850);
   const bool gate_year=(max_year_share<=0.30);
   const bool runtime_all=(gate_no_trade && gate_telemetry && gate_coverage && gate_handles &&
                           gate_raw && gate_one_row && gate_invalid_share && gate_complete &&
                           gate_tb_geometry && gate_year);

   string payload="{\"schema_version\":\"jcdr005.stage_alignment_summary.v1\"";
   payload+=",\"hypothesis_id\":\""+InpHypothesisId+"\",\"variant\":\""+InpVariantTag+"\"";
   payload+=",\"evidence_class\":\"OUTCOME_BLIND_FULL_STAGE_DIAGNOSTIC_ONLY\"";
   payload+=",\"raw_events\":"+IntegerToString(g_raw_events)+",\"diagnostic_rows\":"+IntegerToString(g_diagnostic_rows);
   payload+=",\"invalid_core_rows\":"+IntegerToString(g_invalid_core_rows)+",\"invalid_core_share\":"+DoubleToString(invalid_core_share,9);
   payload+=",\"complete_rows\":"+IntegerToString(g_complete_rows)+",\"tb_both_geometry_rows\":"+IntegerToString(g_tb_both_geometry_rows);
   payload+=",\"max_year_share\":"+DoubleToString(max_year_share,9);
   payload+=",\"gap_resets\":"+IntegerToString(g_gap_resets)+",\"invalid_bar_resets\":"+IntegerToString(g_invalid_bar_resets)+",\"cluster_peaks\":"+IntegerToString(g_cluster_peaks);
   payload+=",\"decay_expired\":"+IntegerToString(g_decay_expired)+",\"jump_in_decay\":"+IntegerToString(g_jump_in_decay)+",\"retrace_out_of_band\":"+IntegerToString(g_retrace_out_of_band)+",\"daily_refractory\":"+IntegerToString(g_daily_refractory);
   payload+=",\"indicator_read_failures\":"+IntegerToString(g_indicator_read_failures)+",\"tb_contract_mismatches\":"+IntegerToString(g_tb_contract_mismatches)+",\"telemetry_write_failures\":"+IntegerToString(g_telemetry_write_failures);
   payload+=",\"accounted_indicator_read_failures\":"+IntegerToString(g_accounted_indicator_read_failures)+",\"accounted_tb_contract_mismatches\":"+IntegerToString(g_accounted_tb_contract_mismatches)+",\"unaccounted_diagnostic_failures\":"+IntegerToString(g_unaccounted_diagnostic_failures);
   payload+=",\"first_analysis_date\":"+IntegerToString(first_analysis_date)+",\"last_analysis_date\":"+IntegerToString(last_analysis_date)+",\"seen_first_date\":"+BoolJson(g_seen_first_date)+",\"seen_last_date\":"+BoolJson(g_seen_last_date)+",\"series_proof_ok\":"+BoolJson(g_series_proof_ok);
   payload+=",\"history_select_ok\":"+BoolJson(history_selected)+",\"total_deals\":"+IntegerToString(total_deals)+",\"trading_deals\":"+IntegerToString(trading_deals)+",\"balance_operations\":"+IntegerToString(balance_operations)+",\"other_deals\":"+IntegerToString(other_deals);
   payload+=",\"historical_orders\":"+IntegerToString(historical_orders)+",\"current_orders\":"+IntegerToString(current_orders)+",\"positions\":"+IntegerToString(positions);
   payload+=",\"gates\":{\"no_trade\":"+BoolJson(gate_no_trade)+",\"telemetry_integrity\":"+BoolJson(gate_telemetry)+",\"coverage\":"+BoolJson(gate_coverage)+",\"handles_contract\":"+BoolJson(gate_handles);
   payload+=",\"raw_count\":"+BoolJson(gate_raw)+",\"one_row_per_event\":"+BoolJson(gate_one_row)+",\"invalid_share\":"+BoolJson(gate_invalid_share);
   payload+=",\"schema_completeness\":"+BoolJson(gate_complete)+",\"tb_both_geometry\":"+BoolJson(gate_tb_geometry)+",\"year_share\":"+BoolJson(gate_year)+"}";
   payload+=",\"runtime_all_pass\":"+BoolJson(runtime_all)+",\"post_availability_price_reads\":0,\"outcomes_observed\":false,\"economics_executed\":false}";

   int meta=FileOpen(g_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(meta==INVALID_HANDLE)
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR005 fail-closed: RunMeta file could not be opened.");
      return;
     }
   const uint meta_written=FileWriteString(meta,payload);
   FileClose(meta);
   if(meta_written<(uint)StringLen(payload))
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR005 fail-closed: RunMeta payload write was incomplete.");
      return;
     }
   Print("JCDR005_SUMMARY|",payload);
  }

bool OpenTelemetry()
  {
   g_csv_handle=FileOpen(g_csv_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(g_csv_handle==INVALID_HANDLE) return(false);
   string header="record_type,hypothesis_id,variant,event_id,cluster_peak_research_clock,decision_research_clock,availability_research_clock";
   header+=",research_date,research_year,research_hour,cluster_sign,jump_count,coherence,anchor,extreme,signed_displacement_pips,scale_at_peak_pips,threshold_at_peak_pips,retracement,decision_close";
   header+=",invalid_mask,invalid_reasons,aird_valid,aird_held_regime,aird_held_confidence_pct,aird_raw_regime,aird_raw_probability_01";
   header+=",aird_p_bull_pct,aird_p_bear_pct,aird_p_range_pct,aird_p_highvol_pct,aird_trend_corr,aird_momentum,aird_vol_percentile_01,aird_drift,aird_changed,aird_regime_age,aird_aligned_probability_pct,aird_opposite_probability_pct";
   header+=",vrc_valid,vrc_hurst,vrc_adx,vrc_di_plus,vrc_di_minus,vrc_chop,vrc_vol_percentile_pct,vrc_atr,vrc_composite,vrc_direction,vrc_regime,vrc_changed,vrc_high_vol,vrc_low_vol,vrc_trend_score,vrc_chop_score,vrc_hurst_score,vrc_change_age,vrc_cluster_alignment";
   header+=",mbb_dc_valid,mbb_adaptive_length,mbb_ker,mbb_ker_percentile_pct,mbb_regime,mbb_bandwidth,mbb_squeeze_score_pct,mbb_squeeze_state,mbb_release,mbb_priority_signal,mbb_squeeze_age,mbb_release_age,mbb_signal_alignment";
   header+=",qqe_primary,qqe_secondary,qqe_composite,qqe_zero_cross,qqe_primary_alignment,qqe_secondary_alignment,qqe_composite_change_age,qqe_zero_cross_age";
   header+=",tb_closed_valid,tb_contract_version,tb_bias,tb_structure_event,tb_sweep_high,tb_sweep_low,tb_void_bull,tb_void_bear,tb_displacement_bull,tb_displacement_bear,tb_swing_high,tb_swing_low,tb_atr,tb_break_level,tb_cell_age,tb_void_age,tb_displacement_ratio,tb_void_size_atr,tb_cell_size_atr,tb_ready_mask,tb_nearest_liquidity_high,tb_nearest_liquidity_low,tb_has_liquidity_high,tb_has_liquidity_low,tb_structure_age,tb_sweep_high_age,tb_sweep_low_age";
   header+=",long_stop_level,long_stop_pips,long_corridor_pips,long_geometry_pass,short_stop_level,short_stop_pips,short_corridor_pips,short_geometry_pass";
   const uint header_written=FileWriteString(g_csv_handle,header+"\r\n");
   if(header_written<(uint)(StringLen(header)+2))
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
   if(_Symbol!="EURUSD" || InpExpectedSymbol!="EURUSD" || _Symbol!=InpExpectedSymbol ||
      _Period!=PERIOD_M5 || InpHypothesisId!="HYP-JCDR-EURUSD-M5-005" ||
      InpVariantTag!="JCDR_STAGE_ALIGNMENT_V1")
     {
      Print("JCDR005 fail-closed: exact EURUSD/M5/hypothesis/variant binding required.");
      return(INIT_FAILED);
     }
   if(InpAnalysisFrom!="2016.01.04" || InpAnalysisTo!="2020.12.31")
     {
      Print("JCDR005 fail-closed: exact frozen 2016.01.04-2020.12.31 analysis window required.");
      return(INIT_FAILED);
     }
   if(!MQLInfoInteger(MQL_TESTER) || !InpResearchAutoMode || !InpEnableTelemetry)
     {
      Print("JCDR005 fail-closed: tester, explicit research mode and telemetry are mandatory.");
      return(INIT_FAILED);
     }

   g_series_proof_ok=EmitDataEpochSeriesProof();
   if(!g_series_proof_ok)
     {
      Print("JCDR005 fail-closed: fixed-window D0 series proof is invalid.");
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
      Print("JCDR005 fail-closed: one or more indicator handles are invalid.");
      return(INIT_FAILED);
     }
   if(!OpenTelemetry())
     {
      Print("JCDR005 fail-closed: telemetry sidecar could not be opened.");
      return(INIT_FAILED);
     }

   ArrayResize(g_bars,0);
   ResetPending();
   g_last_open_time=0;
   Print("JCDR005_INIT|NO_TRADE_FULL_STAGE_DIAGNOSTIC|",InpHypothesisId,"|",InpVariantTag);
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   if(g_telemetry_fatal)
      return;
   const datetime current_open=iTime(_Symbol,PERIOD_M5,0); // Timestamp only; no forming-bar price read.
   if(current_open<=0)
      return;
   if(current_open==g_last_open_time)
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
