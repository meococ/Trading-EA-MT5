//+------------------------------------------------------------------+
//|                         EA_JumpClusterDecayReversal.mq5          |
//| HYP-JCDR-EURUSD-M5-004: role-aware source feasibility probe     |
//|                                                                  |
//| IMPORTANT                                                        |
//| - This build is a NO-TRADE exporter.                             |
//| - JCDR is the sole event and direction source.                   |
//| - AIRD + QQE select continuation only when they agree.           |
//| - VRC + MBB describe regime/energy; they do not create entries.  |
//| - TB SMC owns only protected-stop and free-corridor geometry.     |
//| - Price OHLC is read only from shift 1 or older.                 |
//+------------------------------------------------------------------+
#property strict
#property version   "1.10"
#property description "Outcome-blind broker-native JCDR role-aware source exporter"
#property tester_indicator "AlphaFactory\\AI_Regime_Detection.ex5"
#property tester_indicator "AlphaFactory\\Volatility_Regime_Classifier_QuantRegime.ex5"
#property tester_indicator "AlphaFactory\\Modern_Bollinger_Bands_GBB.ex5"
#property tester_indicator "AlphaFactory\\QQE_MOD.ex5"
#property tester_indicator "AlphaFactory\\TB_Smart_Money_Concept_2026.ex5"

input string InpHypothesisId    = "HYP-JCDR-EURUSD-M5-004";
input string InpExpectedSymbol  = "EURUSD";
input bool   InpResearchAutoMode= false; // Must be explicitly enabled by preregistered probe.
input bool   InpEnableTelemetry = true;  // Mandatory for the no-trade feasibility run.
input string InpVariantTag      = "JCDR_ROLE_AWARE_SOURCE_V1";
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

// ABI/validity bits are diagnostics only.  Economic roles are expressed by
// the route fields below, avoiding the HYP-003 overlapping hard-veto failure.
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

struct RouterSnapshot
  {
   int    invalid_mask;
   string route;
   int    primary_sign;
   bool   routed;
   bool   aird_follow;
   bool   qqe_follow;
   bool   vrc_disorder;
   bool   vrc_high_or_compression;
   bool   unreleased_squeeze;
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
   double planned_stop_level;
   double planned_stop_pips;
   double corridor_pips;
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
int  g_arm_rows=0;
int  g_routed_events=0;
int  g_primary_long=0;
int  g_primary_short=0;
int  g_route_reversal=0;
int  g_route_follow=0;
int  g_abstain_invalid=0;
int  g_abstain_squeeze=0;
int  g_abstain_regime_conflict=0;
int  g_abstain_corridor=0;
int  g_stop_too_tight=0;
int  g_corridor_too_short=0;
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
int  g_unaccounted_router_failures=0;
int  g_telemetry_write_failures=0;
double g_routed_stops[];
double g_routed_cost_ratios[];

string g_csv_name="EURUSD_JCDR004_StateTelemetry_HYP_JCDR_EURUSD_M5_004.csv";
string g_meta_name="JCDR004_RunMeta_HYP_JCDR_EURUSD_M5_004.json";

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

bool ReadClosedBufferValue(const int handle,const int buffer,double &value)
  {
   double data[1];
   value=EMPTY_VALUE;
   if(handle==INVALID_HANDLE || CopyBuffer(handle,buffer,1,1,data)!=1)
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

void BuildRouterSnapshot(const int cluster_sign,const double decision_close,RouterSnapshot &s)
  {
   // RouterSnapshot owns a string, so ZeroMemory is deliberately forbidden.
   // Explicit initialization keeps MQL string descriptors valid and makes
   // every unfilled diagnostic value visibly unusable rather than zero.
   s.invalid_mask=0;
   s.route="ABSTAIN_INVALID";
   s.primary_sign=0;
   s.routed=false;
   s.aird_follow=false;
   s.qqe_follow=false;
   s.vrc_disorder=false;
   s.vrc_high_or_compression=false;
   s.unreleased_squeeze=false;
   s.aird_valid=EMPTY_VALUE;
   s.aird_regime=EMPTY_VALUE;
   s.aird_confidence=EMPTY_VALUE;
   s.vrc_valid=EMPTY_VALUE;
   s.vrc_hurst=EMPTY_VALUE;
   s.vrc_chop=EMPTY_VALUE;
   s.vrc_vol_percentile=EMPTY_VALUE;
   s.vrc_regime=EMPTY_VALUE;
   s.vrc_high_vol=EMPTY_VALUE;
   s.mbb_dc_valid=EMPTY_VALUE;
   s.mbb_basis=EMPTY_VALUE;
   s.mbb_regime=EMPTY_VALUE;
   s.mbb_squeeze=EMPTY_VALUE;
   s.mbb_release=EMPTY_VALUE;
   s.qqe_primary=EMPTY_VALUE;
   s.qqe_secondary=EMPTY_VALUE;
   s.qqe_composite=EMPTY_VALUE;
   s.tb_swing_high=EMPTY_VALUE;
   s.tb_swing_low=EMPTY_VALUE;
   s.tb_closed_valid=EMPTY_VALUE;
   s.tb_atr=EMPTY_VALUE;
   s.tb_contract_version=EMPTY_VALUE;
   s.planned_stop_level=EMPTY_VALUE;
   s.planned_stop_pips=EMPTY_VALUE;
   s.corridor_pips=EMPTY_VALUE;

   bool aird_read=true;
   aird_read&=ReadClosedBufferValue(g_aird_handle,11,s.aird_valid);
   aird_read&=ReadClosedBufferValue(g_aird_handle,12,s.aird_regime);
   aird_read&=ReadClosedBufferValue(g_aird_handle,5,s.aird_confidence);
   if(!aird_read || s.aird_valid!=1.0 || !IsUsable(s.aird_regime) || !IsUsable(s.aird_confidence))
      s.invalid_mask|=INVALID_AIRD;
   else
     {
      const int regime=(int)MathRound(s.aird_regime);
      const int continuation_regime=(cluster_sign>0 ? 0 : 1);
      if(regime==continuation_regime && s.aird_confidence>=80.0)
         s.aird_follow=true;
     }

   bool vrc_read=true;
   vrc_read&=ReadClosedBufferValue(g_vrc_handle,31,s.vrc_valid);
   vrc_read&=ReadClosedBufferValue(g_vrc_handle,14,s.vrc_hurst);
   vrc_read&=ReadClosedBufferValue(g_vrc_handle,18,s.vrc_chop);
   vrc_read&=ReadClosedBufferValue(g_vrc_handle,19,s.vrc_vol_percentile);
   vrc_read&=ReadClosedBufferValue(g_vrc_handle,23,s.vrc_regime);
   vrc_read&=ReadClosedBufferValue(g_vrc_handle,26,s.vrc_high_vol);
   if(!vrc_read || s.vrc_valid!=1.0 || !IsUsable(s.vrc_hurst) || !IsUsable(s.vrc_chop) ||
      !IsUsable(s.vrc_vol_percentile) || !IsUsable(s.vrc_regime) || !IsExactFlag(s.vrc_high_vol))
      s.invalid_mask|=INVALID_VRC;
   else
     {
      s.vrc_high_or_compression=(s.vrc_high_vol==1.0 || (int)MathRound(s.vrc_regime)==7);
      s.vrc_disorder=(s.vrc_chop>=61.8 && s.vrc_hurst>0.45);
     }

   bool mbb_read=true;
   mbb_read&=ReadClosedBufferValue(g_mbb_handle,16,s.mbb_dc_valid);
   mbb_read&=ReadClosedBufferValue(g_mbb_handle,7,s.mbb_basis);
   mbb_read&=ReadClosedBufferValue(g_mbb_handle,20,s.mbb_regime);
   mbb_read&=ReadClosedBufferValue(g_mbb_handle,23,s.mbb_squeeze);
   mbb_read&=ReadClosedBufferValue(g_mbb_handle,24,s.mbb_release);
   const bool mbb_regime_ok=(IsUsable(s.mbb_regime) && (s.mbb_regime==0.0 || s.mbb_regime==1.0));
   if(!mbb_read || s.mbb_dc_valid!=1.0 || !IsUsable(s.mbb_basis) || !mbb_regime_ok ||
      !IsExactFlag(s.mbb_squeeze) || !IsExactFlag(s.mbb_release))
      s.invalid_mask|=INVALID_MBB;
   else
      s.unreleased_squeeze=(s.mbb_squeeze==1.0 && s.mbb_release!=1.0);

   bool qqe_read=true;
   qqe_read&=ReadClosedBufferValue(g_qqe_handle,3,s.qqe_primary);
   qqe_read&=ReadClosedBufferValue(g_qqe_handle,4,s.qqe_secondary);
   qqe_read&=ReadClosedBufferValue(g_qqe_handle,8,s.qqe_composite);
   if(!qqe_read || !IsUsable(s.qqe_primary) || !IsUsable(s.qqe_secondary) || !IsExactTernary(s.qqe_composite))
      s.invalid_mask|=INVALID_QQE;
   else
      s.qqe_follow=((cluster_sign>0 && s.qqe_composite==1.0) ||
                    (cluster_sign<0 && s.qqe_composite==-1.0));

   bool tb_read=true;
   tb_read&=ReadClosedBufferValue(g_tb_handle,13,s.tb_swing_high);
   tb_read&=ReadClosedBufferValue(g_tb_handle,14,s.tb_swing_low);
   tb_read&=ReadClosedBufferValue(g_tb_handle,26,s.tb_closed_valid);
   tb_read&=ReadClosedBufferValue(g_tb_handle,28,s.tb_atr);
   tb_read&=ReadClosedBufferValue(g_tb_handle,43,s.tb_contract_version);
   const bool tb_values_ok=(IsUsable(s.tb_swing_high) && IsUsable(s.tb_swing_low) &&
                            s.tb_swing_low<s.tb_swing_high && IsUsable(s.tb_atr) && s.tb_atr>0.0);
   if(IsUsable(s.tb_contract_version) && s.tb_contract_version!=3.0)
      g_tb_contract_mismatches++;
   if(!tb_read || s.tb_closed_valid!=1.0 || s.tb_contract_version!=3.0 || !tb_values_ok)
      s.invalid_mask|=INVALID_TB;

   // Route selection is ordered and frozen.  Indicators cannot manufacture
   // an event; they only classify the already-formed JCDR event.
   if(s.invalid_mask!=0)
      return;
   if(s.unreleased_squeeze)
     {
      s.route="ABSTAIN_SQUEEZE";
      return;
     }
   const bool follow_energy=(s.vrc_high_vol==1.0 || s.mbb_regime==1.0 || s.mbb_release==1.0);
   if(s.aird_follow && s.qqe_follow && follow_energy)
     {
      s.route="FOLLOW_CONTROL";
      s.primary_sign=cluster_sign;
     }
   else if(!s.vrc_high_or_compression && !s.vrc_disorder)
     {
      s.route="TRUE_REVERSAL";
      s.primary_sign=-cluster_sign;
     }
   else
     {
      s.route="ABSTAIN_REGIME_CONFLICT";
      return;
     }

   // TB SMC supplies only causal geometry.  The stop sits behind the protected
   // cluster/structure extreme; the opposite confirmed swing must leave >=1R.
   const double pip=PipSize();
   if(s.primary_sign>0)
     {
      s.planned_stop_level=MathMin(MathMin(g_pending.anchor,g_pending.extreme),s.tb_swing_low)-JCDR_STOP_BUFFER_PIP*pip;
      s.corridor_pips=(s.tb_swing_high-decision_close)/pip;
     }
   else
     {
      s.planned_stop_level=MathMax(MathMax(g_pending.anchor,g_pending.extreme),s.tb_swing_high)+JCDR_STOP_BUFFER_PIP*pip;
      s.corridor_pips=(decision_close-s.tb_swing_low)/pip;
     }
   s.planned_stop_pips=MathAbs(decision_close-s.planned_stop_level)/pip;
   if(!IsUsable(s.planned_stop_pips) || s.planned_stop_pips<JCDR_MIN_STOP_PIP ||
      !IsUsable(s.corridor_pips) || s.corridor_pips<s.planned_stop_pips)
     {
      s.route="ABSTAIN_CORRIDOR";
      return;
     }
   s.routed=true;
  }

void AddRoutedStop(const double stop_pips)
  {
   const int n=ArraySize(g_routed_stops);
   ArrayResize(g_routed_stops,n+1);
   g_routed_stops[n]=stop_pips;
   const int m=ArraySize(g_routed_cost_ratios);
   ArrayResize(g_routed_cost_ratios,m+1);
   g_routed_cost_ratios[m]=JCDR_COST_GEOMETRY_PIP/stop_pips;
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
             s.route,s.invalid_mask,InvalidText(s.invalid_mask),(s.routed ? 1 : 0),
             (s.aird_follow ? 1 : 0),(s.qqe_follow ? 1 : 0),
             (s.vrc_disorder ? 1 : 0),(s.vrc_high_or_compression ? 1 : 0),(s.unreleased_squeeze ? 1 : 0),
             s.aird_valid,s.aird_regime,s.aird_confidence,
             s.vrc_valid,s.vrc_hurst,s.vrc_chop,s.vrc_vol_percentile,s.vrc_regime,s.vrc_high_vol,
             s.mbb_dc_valid,s.mbb_basis,s.mbb_regime,s.mbb_squeeze,s.mbb_release,
             s.qqe_primary,s.qqe_secondary,s.qqe_composite,
             s.tb_swing_high,s.tb_swing_low,s.tb_closed_valid,s.tb_atr,s.tb_contract_version,
             s.planned_stop_level,s.planned_stop_pips,s.corridor_pips,
             (IsUsable(s.planned_stop_pips) ? JCDR_COST_GEOMETRY_PIP/s.planned_stop_pips : EMPTY_VALUE));
   if(written==0)
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR004 fail-closed: candidate telemetry row write failed for ",signal_id,"/",arm);
      return(false);
     }
   return(true);
  }

bool ExportDecision(const datetime decision_time,const datetime availability_time,const double retracement)
  {
   RouterSnapshot snapshot;
   const double decision_close=g_bars[ArraySize(g_bars)-1].close;
   const int read_failures_before=g_indicator_read_failures;
   const int tb_mismatches_before=g_tb_contract_mismatches;
   BuildRouterSnapshot(g_pending.dominant_sign,decision_close,snapshot);
   const int read_failure_delta=g_indicator_read_failures-read_failures_before;
   const int tb_mismatch_delta=g_tb_contract_mismatches-tb_mismatches_before;

   // Prereg gate 4 permits technical failures only when the same event is
   // explicitly converted to ABSTAIN_INVALID.  Anything else remains a fatal
   // run-level contract failure.
   if(read_failure_delta>0)
     {
      if(snapshot.route=="ABSTAIN_INVALID" && snapshot.invalid_mask!=0)
         g_accounted_indicator_read_failures+=read_failure_delta;
      else
         g_unaccounted_router_failures+=read_failure_delta;
     }
   if(tb_mismatch_delta>0)
     {
      if(snapshot.route=="ABSTAIN_INVALID" && (snapshot.invalid_mask&INVALID_TB)!=0)
         g_accounted_tb_contract_mismatches+=tb_mismatch_delta;
      else
         g_unaccounted_router_failures+=tb_mismatch_delta;
     }

   g_raw_events++;
   const int candidate_index=g_raw_events;
   if(!snapshot.routed)
     {
      if(snapshot.route=="ABSTAIN_INVALID") g_abstain_invalid++;
      else if(snapshot.route=="ABSTAIN_SQUEEZE") g_abstain_squeeze++;
      else if(snapshot.route=="ABSTAIN_REGIME_CONFLICT") g_abstain_regime_conflict++;
      else
        {
         g_abstain_corridor++;
         if(!IsUsable(snapshot.planned_stop_pips) || snapshot.planned_stop_pips<JCDR_MIN_STOP_PIP)
            g_stop_too_tight++;
         if(!IsUsable(snapshot.corridor_pips) || !IsUsable(snapshot.planned_stop_pips) ||
            snapshot.corridor_pips<snapshot.planned_stop_pips)
            g_corridor_too_short++;
        }
      return(true);
     }

   const string signal_id=StringFormat("JCDR004-SRC-%I64d-%06d",(long)decision_time,candidate_index);
   const string primary_direction=(snapshot.primary_sign>0 ? "LONG" : "SHORT");
   const string inverse_direction =(snapshot.primary_sign>0 ? "SHORT" : "LONG");
   const bool primary_written=WriteArmRow(signal_id,"ROLE_PRIMARY",primary_direction,decision_time,availability_time,retracement,snapshot);
   const bool inverse_written=WriteArmRow(signal_id,"INVERSE_CONTROL",inverse_direction,decision_time,availability_time,retracement,snapshot);
   if(!primary_written || !inverse_written)
      return(false);

   // Commit matched-pair counters only after both adjacent rows are present.
   g_routed_events++;
   g_arm_rows+=2;
   if(primary_direction=="LONG") g_primary_long++;
   else g_primary_short++;
   if(snapshot.route=="TRUE_REVERSAL") g_route_reversal++;
   else if(snapshot.route=="FOLLOW_CONTROL") g_route_follow++;
   const int year=ResearchYear(decision_time);
   if(year>=2016 && year<=2020) g_year_counts[year-2016]++;
   AddRoutedStop(snapshot.planned_stop_pips);
   FileFlush(g_csv_handle);
   return(true);
  }

void ProcessClosedBar(const datetime availability_time)
  {
   JcdrBar bar;
   ZeroMemory(bar);
   bar.time=iTime(_Symbol,PERIOD_M5,1);

   // HYP-004 runs the exact frozen fixed window.  This guard still prevents
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
      PrintFormat("JCDR004_SERIES_FAIL field=%s timeframe=%d error=%d",field_name,(int)timeframe,GetLastError());
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
   const double elapsed_weeks=260.43;
   const double cadence=(elapsed_weeks>0.0 ? (double)g_routed_events/elapsed_weeks : 0.0);
   int max_year_count=0;
   for(int i=0;i<5;i++) max_year_count=MathMax(max_year_count,g_year_counts[i]);
   const double max_year_share=(g_routed_events>0 ? (double)max_year_count/g_routed_events : 1.0);
   const double median_stop=MedianArray(g_routed_stops);
   const double median_cost_ratio=MedianArray(g_routed_cost_ratios);
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
   const bool gate_handles=(g_handles_ok && g_unaccounted_router_failures==0 &&
                            g_accounted_indicator_read_failures==g_indicator_read_failures &&
                            g_accounted_tb_contract_mismatches==g_tb_contract_mismatches);
   const bool gate_raw=(g_raw_events>=500);
   const bool gate_routed=(g_routed_events>=180);
   const bool gate_cadence=(cadence>=0.70 && cadence<=2.00);
   const bool gate_sides=(g_primary_long>=80 && g_primary_short>=80);
   const bool gate_routes=(g_route_reversal>=80 && g_route_follow>=80);
   const bool gate_year=(max_year_share<=0.30);
   const bool gate_match=(g_arm_rows==2*g_routed_events);
   const bool gate_stop=(IsUsable(median_stop) && median_stop>=6.0 && IsUsable(median_cost_ratio) && median_cost_ratio<=0.25);
   const bool runtime_all=(gate_no_trade && gate_telemetry && gate_coverage && gate_handles && gate_raw &&
                           gate_routed && gate_cadence && gate_sides && gate_routes && gate_year && gate_match && gate_stop);

   string payload="{\"schema_version\":\"jcdr004.role_aware_source_summary.v1\"";
   payload+=",\"hypothesis_id\":\""+InpHypothesisId+"\",\"variant\":\""+InpVariantTag+"\"";
   payload+=",\"evidence_class\":\"OUTCOME_BLIND_SOURCE_FEASIBILITY_ONLY\"";
   payload+=",\"raw_events\":"+IntegerToString(g_raw_events)+",\"routed_events\":"+IntegerToString(g_routed_events)+",\"arm_rows\":"+IntegerToString(g_arm_rows);
   payload+=",\"primary_long\":"+IntegerToString(g_primary_long)+",\"primary_short\":"+IntegerToString(g_primary_short);
   payload+=",\"route_reversal\":"+IntegerToString(g_route_reversal)+",\"route_follow\":"+IntegerToString(g_route_follow);
   payload+=",\"abstain_invalid\":"+IntegerToString(g_abstain_invalid)+",\"abstain_squeeze\":"+IntegerToString(g_abstain_squeeze);
   payload+=",\"abstain_regime_conflict\":"+IntegerToString(g_abstain_regime_conflict)+",\"abstain_corridor\":"+IntegerToString(g_abstain_corridor);
   payload+=",\"stop_too_tight\":"+IntegerToString(g_stop_too_tight)+",\"corridor_too_short\":"+IntegerToString(g_corridor_too_short);
   payload+=",\"elapsed_weeks\":"+DoubleToString(elapsed_weeks,9)+",\"cadence_per_week\":"+DoubleToString(cadence,9);
   payload+=",\"max_year_share\":"+DoubleToString(max_year_share,9)+",\"median_stop_pips\":"+DoubleToString(median_stop,9)+",\"median_cost_to_stop\":"+DoubleToString(median_cost_ratio,9);
   payload+=",\"gap_resets\":"+IntegerToString(g_gap_resets)+",\"invalid_bar_resets\":"+IntegerToString(g_invalid_bar_resets)+",\"cluster_peaks\":"+IntegerToString(g_cluster_peaks);
   payload+=",\"decay_expired\":"+IntegerToString(g_decay_expired)+",\"jump_in_decay\":"+IntegerToString(g_jump_in_decay)+",\"retrace_out_of_band\":"+IntegerToString(g_retrace_out_of_band)+",\"daily_refractory\":"+IntegerToString(g_daily_refractory);
   payload+=",\"indicator_read_failures\":"+IntegerToString(g_indicator_read_failures)+",\"tb_contract_mismatches\":"+IntegerToString(g_tb_contract_mismatches)+",\"telemetry_write_failures\":"+IntegerToString(g_telemetry_write_failures);
   payload+=",\"accounted_indicator_read_failures\":"+IntegerToString(g_accounted_indicator_read_failures)+",\"accounted_tb_contract_mismatches\":"+IntegerToString(g_accounted_tb_contract_mismatches)+",\"unaccounted_router_failures\":"+IntegerToString(g_unaccounted_router_failures);
   payload+=",\"first_analysis_date\":"+IntegerToString(first_analysis_date)+",\"last_analysis_date\":"+IntegerToString(last_analysis_date)+",\"seen_first_date\":"+BoolJson(g_seen_first_date)+",\"seen_last_date\":"+BoolJson(g_seen_last_date)+",\"series_proof_ok\":"+BoolJson(g_series_proof_ok);
   payload+=",\"history_select_ok\":"+BoolJson(history_selected)+",\"total_deals\":"+IntegerToString(total_deals)+",\"trading_deals\":"+IntegerToString(trading_deals)+",\"balance_operations\":"+IntegerToString(balance_operations)+",\"other_deals\":"+IntegerToString(other_deals);
   payload+=",\"historical_orders\":"+IntegerToString(historical_orders)+",\"current_orders\":"+IntegerToString(current_orders)+",\"positions\":"+IntegerToString(positions);
   payload+=",\"gates\":{\"no_trade\":"+BoolJson(gate_no_trade)+",\"telemetry_integrity\":"+BoolJson(gate_telemetry)+",\"coverage\":"+BoolJson(gate_coverage)+",\"handles_contract\":"+BoolJson(gate_handles);
   payload+=",\"raw_count\":"+BoolJson(gate_raw)+",\"routed_count\":"+BoolJson(gate_routed)+",\"cadence\":"+BoolJson(gate_cadence)+",\"sides\":"+BoolJson(gate_sides)+",\"routes\":"+BoolJson(gate_routes)+",\"year_share\":"+BoolJson(gate_year)+",\"matched_arms\":"+BoolJson(gate_match)+",\"stop_geometry\":"+BoolJson(gate_stop)+"}";
   payload+=",\"runtime_all_pass\":"+BoolJson(runtime_all)+",\"post_availability_price_reads\":0,\"performance_metrics_computed\":0,\"economics_executed\":false}";

   int meta=FileOpen(g_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(meta==INVALID_HANDLE)
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR004 fail-closed: RunMeta file could not be opened.");
      return;
     }
   const uint meta_written=FileWriteString(meta,payload);
   FileClose(meta);
   if(meta_written<(uint)StringLen(payload))
     {
      g_telemetry_write_failures++;
      g_telemetry_fatal=true;
      Print("JCDR004 fail-closed: RunMeta payload write was incomplete.");
      return;
     }
   Print("JCDR004_SUMMARY|",payload);
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
      "route","invalid_mask","invalid_reasons","routed","aird_follow","qqe_follow",
      "vrc_disorder","vrc_high_or_compression","unreleased_squeeze",
      "aird_valid","aird_regime","aird_confidence_pct",
      "vrc_valid","vrc_hurst","vrc_chop","vrc_vol_percentile","vrc_regime","vrc_high_vol",
      "mbb_dc_valid","mbb_basis","mbb_regime","mbb_squeeze","mbb_release",
      "qqe_primary","qqe_secondary","qqe_composite","tb_swing_high","tb_swing_low","tb_closed_valid",
      "tb_atr","tb_contract_version","planned_stop_level","planned_stop_pips","corridor_pips","cost_to_stop_ratio");
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
   if(_Symbol!=InpExpectedSymbol || _Period!=PERIOD_M5 || InpHypothesisId!="HYP-JCDR-EURUSD-M5-004")
     {
      Print("JCDR004 fail-closed: exact EURUSD/M5/hypothesis binding required.");
      return(INIT_FAILED);
     }
   if(InpAnalysisFrom!="2016.01.04" || InpAnalysisTo!="2020.12.31")
     {
      Print("JCDR004 fail-closed: exact frozen 2016.01.04-2020.12.31 window required.");
      return(INIT_FAILED);
     }
   if(!MQLInfoInteger(MQL_TESTER) || !InpResearchAutoMode || !InpEnableTelemetry)
     {
      Print("JCDR004 fail-closed: tester, explicit research mode and telemetry are mandatory.");
      return(INIT_FAILED);
     }

   g_series_proof_ok=EmitDataEpochSeriesProof();
   if(!g_series_proof_ok)
     {
      Print("JCDR004 fail-closed: fixed-window D0 series proof is invalid.");
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
      Print("JCDR004 fail-closed: one or more indicator handles are invalid.");
      return(INIT_FAILED);
     }
   if(!OpenTelemetry())
     {
      Print("JCDR004 fail-closed: telemetry sidecar could not be opened.");
      return(INIT_FAILED);
     }

   ArrayResize(g_bars,0);
   ArrayResize(g_routed_stops,0);
   ArrayResize(g_routed_cost_ratios,0);
   ResetPending();
   g_last_open_time=0;
   Print("JCDR004_INIT|NO_TRADE_ROLE_AWARE_EXPORTER|",InpHypothesisId,"|",InpVariantTag);
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
