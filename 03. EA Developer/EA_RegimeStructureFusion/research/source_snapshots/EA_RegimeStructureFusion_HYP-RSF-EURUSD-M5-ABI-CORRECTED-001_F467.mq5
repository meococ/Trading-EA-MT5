#property strict
#property description "Research-only multi-mode fusion of AIRD, VRC, MBB, TB SMC and QQE"
#property tester_indicator "AlphaFactory\\AI_Regime_Detection.ex5"
#property tester_indicator "AlphaFactory\\Volatility_Regime_Classifier_QuantRegime.ex5"
#property tester_indicator "AlphaFactory\\Modern_Bollinger_Bands_GBB.ex5"
#property tester_indicator "AlphaFactory\\TB_Smart_Money_Concept_2026.ex5"
#property tester_indicator "AlphaFactory\\QQE_MOD.ex5"

// EA_RegimeStructureFusion (RSF)
// --------------------------------
// Research contract:
//   * M5 entry decisions are evaluated once, on the first tick of a new bar.
//   * Every indicator value used by a decision is read at shift >= 1.
//   * AIRD/VRC are context routers, MBB is the setup engine, TB SMC supplies
//     structural state/price geometry, and QQE supplies timing. They are not
//     treated as five equal votes because their price-derived features overlap.
//   * The executable is tester-only and fail-closed. It cannot be attached to
//     a chart to mutate a live/demo account.
//   * AUTO_SYMBOL_PROFILE contains research priors, not profitable settings.
//     Per-symbol values may be promoted only by the preregistered WFA process.

// Mirror the custom-indicator enums so iCustom receives an enum-typed value
// instead of an untyped int.  MQL5 validates the runtime parameter signature,
// not only the numeric value; using ints here can make an otherwise valid
// indicator repeatedly enter INIT_PARAMETERS_INCORRECT in Strategy Tester.
enum ENUM_AIRD_KERNEL
  {
   AIRD_KERNEL_LORENTZIAN=0,
   AIRD_KERNEL_GAUSSIAN=1
  };

enum ENUM_AIRD_DASH_POSITION
  {
   AIRD_TOP_RIGHT=0,
   AIRD_TOP_LEFT=1,
   AIRD_BOTTOM_RIGHT=2,
   AIRD_BOTTOM_LEFT=3
  };

enum ENUM_AIRD_TEXT_SIZE
  {
   AIRD_TEXT_TINY=0,
   AIRD_TEXT_SMALL=1,
   AIRD_TEXT_NORMAL=2
  };

enum ENUM_VRC_DASH_POSITION
  {
   VRC_TOP_LEFT=0,
   VRC_TOP_RIGHT=1,
   VRC_BOTTOM_LEFT=2,
   VRC_BOTTOM_RIGHT=3,
   VRC_MIDDLE_RIGHT=4
  };

enum ENUM_VRC_DASH_SIZE
  {
   VRC_SIZE_SMALL=0,
   VRC_SIZE_NORMAL=1,
   VRC_SIZE_LARGE=2
  };

enum ENUM_MBB_LENGTH_MODE
  {
   MBB_LENGTH_ADAPTIVE=0,
   MBB_LENGTH_FIXED=1
  };

enum ENUM_MBB_BASIS_MODE
  {
   MBB_BASIS_KAMA=0,
   MBB_BASIS_SMA=1
  };

enum ENUM_MBB_BAND_MODE
  {
   MBB_BANDS_ROBUST=0,
   MBB_BANDS_STDEV=1
  };

enum ENUM_TB_ENGINE_PROFILE
  {
   TB_PROFILE_TV_2026_2_0=0,
   TB_PROFILE_EA_CUSTOM=1
  };

enum ENUM_TB_VOID_RETENTION
  {
   TB_VOID_TV_HALF_PARITY=0,
   TB_VOID_EA_WHOLE_ZONE=1
  };

enum ENUM_RSF_CLOCK_PROFILE
  {
   RSF_CLOCK_EET_EEST=0, // Broker server UTC+2 winter / UTC+3 Europe DST
   RSF_CLOCK_FIXED=1     // Explicit fixed server offset
  };

enum ENUM_RSF_PROFILE_MODE
  {
   RSF_PROFILE_AUTO_SYMBOL=0,
   RSF_PROFILE_MANUAL=1
  };

enum ENUM_RSF_SIGNAL
  {
   RSF_SIGNAL_NONE=0,
   RSF_RANGE_LONG=1,
   RSF_RANGE_SHORT=-1,
   RSF_TREND_LONG=2,
   RSF_TREND_SHORT=-2,
   RSF_BREAKOUT_LONG=3,
   RSF_BREAKOUT_SHORT=-3
  };

const int RSF_MODE_RANGE=1;
const int RSF_MODE_TREND=2;
const int RSF_MODE_BREAKOUT=4;
const int RSF_SESSION_ASIA=1;
const int RSF_SESSION_LONDON=2;
const int RSF_SESSION_OVERLAP=4;
const int RSF_SESSION_NEW_YORK=8;
const int RSF_SESSION_OFF_HOURS=16;
const int RSF_SESSION_WEEKEND=32;
const int RSF_TB_CONTRACT_VERSION_BUFFER=43;
const double RSF_REQUIRED_TB_CONTRACT_VERSION=2.0;

input group "Research authority - fail closed"
input bool   InpResearchAutoMode=false;                  // Must be true in Strategy Tester
input bool   InpEnableTelemetry=true;                    // Required for execution
input string InpHypothesisId="UNREGISTERED_BUILD_ONLY"; // Must start HYP-RSF-
input string InpVariantTag="ENGINEERING_BASELINE";
input string InpExpectedSymbol="EURUSD";
input long   InpMagic=5867201;

input group "Timeframe, symbol and market-clock profile"
input ENUM_TIMEFRAMES InpContextTimeframe=PERIOD_M15;
input ENUM_RSF_PROFILE_MODE InpProfileMode=RSF_PROFILE_AUTO_SYMBOL;
input ENUM_RSF_CLOCK_PROFILE InpClockProfile=RSF_CLOCK_EET_EEST;
input int InpFixedServerUtcOffsetMinutes=120;
input int InpManualSessionMask=6; // LONDON | OVERLAP
input int InpManualModeMask=7;    // RANGE | TREND | BREAKOUT
input double InpManualRiskScale=1.0;

input group "Execution and account-risk controls"
input double InpRiskPercent=0.20;
input double InpHighVolRiskScale=0.50;
input double InpMaxDailyLossPct=3.0;
input double InpMaxAccountDrawdownPct=8.0;
input double InpMinPostTradeMarginLevelPct=150.0; // Percent-mode and generic margin floor
input double InpMoneyStopoutBufferPct=5.0;        // Equity buffer above a money-mode stop-out floor
input int    InpMaxTradesPerDay=3;
input int    InpEntryCooldownBars=5;
input int    InpMaxHoldBars=48;
input int    InpFridayFlattenMinutesUtc=1200;
input double InpMaxSpreadToStop=0.15;
input int    InpDeviationPoints=20;

input group "Decision router and trade geometry"
input bool   InpAllowRangeMode=true;
input bool   InpAllowTrendMode=true;
input bool   InpAllowBreakoutMode=true;
// Block-1 ablations are decision-path controls, not indicator unload switches.
// All engines remain initialized so every cell shares one warm-up/data contract.
input bool   InpUseContextRouter=true; // AIRD confidence/state + VRC regime
input bool   InpUseTbStructure=true;   // TB entry filters and structural anchors
input bool   InpUseQqeTiming=true;     // QQE side/reacceleration/extreme timing
input double InpMinAirdConfidence=0.45;
input double InpMinAirdStateProbability=0.35;
input double InpRangeQQEExtreme=3.0;
input double InpTrendQQEMin=0.0;
input int    InpStructureEventMaxAgeBars=3;
input double InpMbbHalfWidthStopMult=1.0;
input double InpMinStopAtr=0.35;
input double InpMaxStopAtr=4.0;
input double InpStructureBufferAtr=0.10;
input double InpRewardRisk=1.50;

// AIRD parameters are passed positionally to the custom indicator. The
// defaults reproduce the reviewed indicator; only declared axes may be swept.
input group "AIRD context engine"
input double InpAirdPersistence=0.92;
input double InpAirdTransitionRate=0.010;
input double InpAirdEmissionRate=0.010;
input bool   InpAirdAdaptive=true;
input ENUM_AIRD_KERNEL InpAirdKernel=AIRD_KERNEL_LORENTZIAN;
input double InpAirdSwitchMargin=0.05;
input int    InpAirdConfirmBars=1;
input double InpAirdTemperature=2.0;
input int    InpAirdCorrelationLength=50;
input int    InpAirdRsiLength=14;
input int    InpAirdVolatilityLength=20;
input int    InpAirdVolRankLength=300;
input int    InpAirdDriftLength=14;

input group "VRC context engine"
input int    InpVrcHurstLength=100;
input int    InpVrcAdxLength=14;
input int    InpVrcAdxSmoothing=14;
input int    InpVrcChopLength=14;
input int    InpVrcVolatilityLength=20;
input int    InpVrcVolPercentileLength=100;
input double InpVrcAdxTrendThreshold=25.0;
input double InpVrcAdxStrongThreshold=40.0;
input double InpVrcChopRangeThreshold=61.8;
input double InpVrcHurstTrendThreshold=0.55;
input double InpVrcHurstMrThreshold=0.45;
input double InpVrcVolHighPercentile=80.0;
input double InpVrcVolLowPercentile=20.0;

input group "MBB setup engine"
input ENUM_MBB_LENGTH_MODE InpMbbLengthMode=MBB_LENGTH_ADAPTIVE;
input int    InpMbbFixedLength=20;
input ENUM_MBB_BASIS_MODE InpMbbBasisMode=MBB_BASIS_KAMA;
input ENUM_MBB_BAND_MODE InpMbbBandMode=MBB_BANDS_ROBUST;
input double InpMbbStdevMultiplier=2.0;
input double InpMbbRobustUpperPct=97.5;
input double InpMbbRobustLowerPct=2.5;
input int    InpMbbRobustWindowMult=4;
input int    InpMbbRobustWindowFloor=80;
input int    InpMbbKamaFast=2;
input int    InpMbbKamaSlow=30;
input int    InpMbbKerLength=20;
input int    InpMbbRankLength=252;
input double InpMbbTrendEnter=70.0;
input double InpMbbTrendExit=55.0;
input double InpMbbSqueezeThreshold=20.0;
input int    InpMbbSqueezeMinBars=5;
input double InpMbbBasisTouchFraction=0.25;

input group "TB SMC structural engine"
input int    InpTbSwingLength=5;
input double InpTbDisplacementAtr=0.45;
input int    InpTbCellsKept=3;
input int    InpTbVoidsKept=4;
input double InpTbSweepReclaimAtr=0.05;
input double InpTbMinimumVoidAtr=0.0;
input double InpTbMinimumCellAtr=0.0;
input int    InpTbMaximumCellAgeBars=0;
input int    InpTbMaximumVoidAgeBars=0;
input bool   InpTbSweepsRequireLiveSwing=false;
input bool   InpTbRequireBothSwings=true;
input bool   InpTbEnableStructure=true;
input bool   InpTbEnableCells=true;
input bool   InpTbEnableVoids=true;
input bool   InpTbEnableSweeps=true;
input ENUM_TB_VOID_RETENTION InpTbVoidRetention=TB_VOID_EA_WHOLE_ZONE;

input group "QQE timing engine"
input int    InpQqePrimaryRsiLength=6;
input int    InpQqePrimarySmoothing=5;
input double InpQqePrimaryFactor=3.0;
input double InpQqePrimaryThreshold=3.0;
input ENUM_APPLIED_PRICE InpQqePrimarySource=PRICE_CLOSE;
input int    InpQqeSecondaryRsiLength=6;
input int    InpQqeSecondarySmoothing=5;
input double InpQqeSecondaryFactor=1.61;
input double InpQqeSecondaryThreshold=3.0;
input ENUM_APPLIED_PRICE InpQqeSecondarySource=PRICE_CLOSE;
input int    InpQqeBollingerLength=50;
input double InpQqeBollingerMultiplier=0.35;

const string RSF_EA_NAME="EA_RegimeStructureFusion";
const string RSF_TELEMETRY_PROFILE="lifecycle-v3";

int g_aird=INVALID_HANDLE;
int g_vrc=INVALID_HANDLE;
int g_mbb=INVALID_HANDLE;
int g_tb=INVALID_HANDLE;
int g_qqe=INVALID_HANDLE;
datetime g_last_bar_time=0;
datetime g_last_entry_bar_time=0;

int g_day_key=0;
double g_day_start_equity=0.0;
double g_peak_equity=0.0;
int g_trades_today=0;
bool g_daily_locked=false;
bool g_account_locked=false;

string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
int g_lifecycle_handle=INVALID_HANDLE;

long g_ticks_seen=0;
long g_closed_bars_seen=0;
long g_indicator_ready=0;
long g_indicator_not_ready=0;
long g_reject_session=0;
long g_reject_setup=0;
long g_reject_context=0;
long g_reject_structure=0;
long g_reject_timing=0;
long g_reject_risk=0;
long g_reject_execution=0;
long g_range_setups=0;
long g_trend_setups=0;
long g_breakout_setups=0;
long g_entries_opened=0;
long g_final_closes=0;
string g_last_reason="NONE";

ENUM_RSF_SIGNAL g_pending_signal=RSF_SIGNAL_NONE;
double g_pending_sl=0.0;
double g_pending_tp=0.0;
double g_pending_risk_account=0.0;
ulong g_active_position_id=0;
ENUM_RSF_SIGNAL g_active_signal=RSF_SIGNAL_NONE;
double g_active_entry=0.0;
double g_active_sl=0.0;
double g_active_tp=0.0;
double g_active_risk_account=0.0;

struct SymbolProfile
  {
   int sessions;
   int modes;
   double risk_scale;
  };

struct RsfSnapshot
  {
   bool ready;
   int aird_regime;
   double aird_confidence;
   double p_bull;
   double p_bear;
   double p_range;
   double p_highvol;
   int vrc_regime;
   int vrc_previous_regime;
   double vrc_direction;
   double vrc_vol_percentile;
   bool vrc_high_vol;
   bool vrc_low_vol;
   double mbb_upper;
   double mbb_lower;
   double mbb_basis;
   double mbb_squeeze;
   bool mbb_release;
   bool s1_long;
   bool s1_short;
   bool s2_long;
   bool s2_short;
   bool s3_long;
   bool s3_short;
   int tb_bias;
   double tb_atr;
   double tb_swing_high;
   double tb_swing_low;
   double tb_cell_top;
   double tb_cell_bottom;
   int tb_cell_side;
   double tb_void_top;
   double tb_void_bottom;
   int tb_void_side;
   double tb_structure_level;
   bool tb_sweep_high;
   bool tb_sweep_low;
   double tb_sweep_high_price;
   double tb_sweep_low_price;
   bool tb_structure_up;
   bool tb_structure_down;
   bool tb_displacement_up;
   bool tb_displacement_down;
   double qqe_primary;
   double qqe_primary_prev;
   double qqe_secondary;
   double qqe_secondary_prev;
   int qqe_state;
  };

struct TradeDecision
  {
   bool fired;
   int direction;
   ENUM_RSF_SIGNAL signal;
   double stop;
   double target;
   double risk_scale;
   string reason;
  };

int DaysInMonth(const int year,const int month)
  {
   if(month==2) return(((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11) return(30);
   return(31);
  }

datetime MakeDateTime(const int year,const int month,const int day,const int hour,const int minute=0)
  {
   MqlDateTime p; ZeroMemory(p);
   p.year=year; p.mon=month; p.day=day; p.hour=hour; p.min=minute;
   return(StructToTime(p));
  }

datetime LastSunday(const int year,const int month,const int hour)
  {
   datetime value=MakeDateTime(year,month,DaysInMonth(year,month),hour);
   MqlDateTime p; TimeToStruct(value,p);
   return(value-p.day_of_week*86400);
  }

datetime NthSunday(const int year,const int month,const int nth,const int hour)
  {
   datetime first=MakeDateTime(year,month,1,hour);
   MqlDateTime p; TimeToStruct(first,p);
   int first_sunday=1+((7-p.day_of_week)%7);
   return(MakeDateTime(year,month,first_sunday+(nth-1)*7,hour));
  }

bool IsEuropeDstUtc(const datetime utc_time)
  {
   MqlDateTime p; TimeToStruct(utc_time,p);
   return(utc_time>=LastSunday(p.year,3,1) && utc_time<LastSunday(p.year,10,1));
  }

bool IsNewYorkDstUtc(const datetime utc_time)
  {
   MqlDateTime p; TimeToStruct(utc_time,p);
   return(utc_time>=NthSunday(p.year,3,2,7) && utc_time<NthSunday(p.year,11,1,6));
  }

datetime ServerToUtc(const datetime server_time)
  {
   if(InpClockProfile==RSF_CLOCK_FIXED)
      return(server_time-InpFixedServerUtcOffsetMinutes*60);
   datetime winter_candidate=server_time-2*3600;
   int hours=2+(IsEuropeDstUtc(winter_candidate) ? 1 : 0);
   return(server_time-hours*3600);
  }

int MinuteOfDay(const datetime value)
  {
   MqlDateTime p; TimeToStruct(value,p);
   return(p.hour*60+p.min);
  }

int DateKey(const datetime value)
  {
   MqlDateTime p; TimeToStruct(value,p);
   return(p.year*10000+p.mon*100+p.day);
  }

bool IsWithin(const int minute,const int from_minute,const int to_minute)
  {
   return(minute>=from_minute && minute<to_minute);
  }

int SessionMaskAtUtc(const datetime utc_time)
  {
   MqlDateTime utc; TimeToStruct(utc_time,utc);
   int bits=0;
   if(utc.day_of_week==0 || utc.day_of_week==6) bits|=RSF_SESSION_WEEKEND;

   datetime tokyo=utc_time+9*3600;
   datetime london=utc_time+(IsEuropeDstUtc(utc_time) ? 3600 : 0);
   datetime new_york=utc_time+(-5+(IsNewYorkDstUtc(utc_time) ? 1 : 0))*3600;
   int t=MinuteOfDay(tokyo),l=MinuteOfDay(london),n=MinuteOfDay(new_york);
   if(IsWithin(t,8*60,16*60)) bits|=RSF_SESSION_ASIA;
   if(IsWithin(l,7*60,12*60)) bits|=RSF_SESSION_LONDON;
   bool overlap=IsWithin(l,12*60,16*60) && IsWithin(n,8*60,12*60);
   if(overlap) bits|=RSF_SESSION_OVERLAP;
   if(IsWithin(n,8*60,16*60)) bits|=RSF_SESSION_NEW_YORK;
   if((bits&(RSF_SESSION_ASIA|RSF_SESSION_LONDON|RSF_SESSION_OVERLAP|RSF_SESSION_NEW_YORK))==0)
      bits|=RSF_SESSION_OFF_HOURS;
   return(bits);
  }

void ResolveProfile(SymbolProfile &profile)
  {
   profile.sessions=InpManualSessionMask;
   profile.modes=InpManualModeMask;
   profile.risk_scale=InpManualRiskScale;
   if(InpProfileMode==RSF_PROFILE_MANUAL) return;

   string symbol=_Symbol;
   profile.modes=RSF_MODE_RANGE|RSF_MODE_TREND|RSF_MODE_BREAKOUT;
   profile.risk_scale=1.0;
   if(StringFind(symbol,"EURUSD")>=0 || StringFind(symbol,"USDCHF")>=0)
      profile.sessions=RSF_SESSION_LONDON|RSF_SESSION_OVERLAP;
   else if(StringFind(symbol,"GBPUSD")>=0)
      profile.sessions=RSF_SESSION_LONDON|RSF_SESSION_OVERLAP|RSF_SESSION_NEW_YORK;
   else if(StringFind(symbol,"USDJPY")>=0)
      profile.sessions=RSF_SESSION_ASIA|RSF_SESSION_LONDON|RSF_SESSION_NEW_YORK;
   else if(StringFind(symbol,"USDCAD")>=0)
      profile.sessions=RSF_SESSION_OVERLAP|RSF_SESSION_NEW_YORK;
   else if(StringFind(symbol,"AUDUSD")>=0 || StringFind(symbol,"NZDUSD")>=0)
      profile.sessions=RSF_SESSION_ASIA|RSF_SESSION_LONDON;
   else if(StringFind(symbol,"XAUUSD")>=0)
     {
      profile.sessions=RSF_SESSION_LONDON|RSF_SESSION_OVERLAP|RSF_SESSION_NEW_YORK;
      profile.modes=RSF_MODE_TREND|RSF_MODE_BREAKOUT;
      profile.risk_scale=0.75;
     }
   else if(StringFind(symbol,"BTCUSD")>=0)
     {
      profile.sessions=RSF_SESSION_ASIA|RSF_SESSION_LONDON|RSF_SESSION_OVERLAP|RSF_SESSION_NEW_YORK|RSF_SESSION_OFF_HOURS|RSF_SESSION_WEEKEND;
      profile.risk_scale=0.50;
     }
  }

bool IsUsable(const double value)
  {
   return(MathIsValidNumber(value) && value!=EMPTY_VALUE && MathAbs(value)<DBL_MAX*0.5);
  }

bool ReadClosed1(const int handle,const int buffer,double &value)
  {
   double data[1];
   if(CopyBuffer(handle,buffer,1,1,data)!=1 || !IsUsable(data[0])) return(false);
   value=data[0];
   return(true);
  }

bool ReadClosed2(const int handle,const int buffer,double &value)
  {
   double data[1];
   if(CopyBuffer(handle,buffer,2,1,data)!=1 || !IsUsable(data[0])) return(false);
   value=data[0];
   return(true);
  }

double OptionalClosed1(const int handle,const int buffer,const double fallback=0.0)
  {
   double value=0.0;
   return(ReadClosed1(handle,buffer,value) ? value : fallback);
  }

bool RecentFlag(const int handle,const int buffer,const int max_age,int &age,double &marker,const int marker_buffer=-1)
  {
   age=0; marker=0.0;
   int count=MathMax(1,max_age);
   double flags[]; ArrayResize(flags,count);
   if(CopyBuffer(handle,buffer,1,count,flags)!=count) return(false);
   double markers[];
   if(marker_buffer>=0)
     {
      ArrayResize(markers,count);
      if(CopyBuffer(handle,marker_buffer,1,count,markers)!=count) ArrayInitialize(markers,0.0);
     }
   // CopyBuffer writes the oldest requested value at index zero. Scan from
   // newest closed bar (shift 1) toward older bars without ever requesting 0.
   for(int shift=1;shift<=count;shift++)
     {
      int index=count-shift;
      if(IsUsable(flags[index]) && flags[index]>0.5)
        {
         age=shift;
         if(marker_buffer>=0 && IsUsable(markers[index])) marker=markers[index];
         return(true);
        }
     }
   return(false);
  }

bool ReadSnapshot(RsfSnapshot &s)
  {
   ZeroMemory(s); s.ready=false;
   if(BarsCalculated(g_aird)<310 || BarsCalculated(g_vrc)<160 || BarsCalculated(g_mbb)<310 ||
      BarsCalculated(g_tb)<80 || BarsCalculated(g_qqe)<60) return(false);

   double aird_valid=0.0,aird_regime=0.0,aird_conf_pct=0.0;
   double vrc_valid=0.0,vrc_regime=0.0,vrc_previous=0.0,vrc_high=0.0,vrc_low=0.0;
   double tb_valid=0.0,tb_contract=0.0,tb_bias=0.0,tb_cell_side=0.0,tb_void_side=0.0;
   double s1l=0.0,s1s=0.0,s2l=0.0,s2s=0.0,s3l=0.0,s3s=0.0,release=0.0,state=0.0;
   if(!ReadClosed1(g_aird,11,aird_valid) || !ReadClosed1(g_aird,12,aird_regime) ||
      !ReadClosed1(g_aird,5,aird_conf_pct) || !ReadClosed1(g_aird,7,s.p_bull) ||
      !ReadClosed1(g_aird,8,s.p_bear) || !ReadClosed1(g_aird,9,s.p_range) ||
      !ReadClosed1(g_aird,10,s.p_highvol) ||
      !ReadClosed1(g_vrc,31,vrc_valid) || !ReadClosed1(g_vrc,23,vrc_regime) ||
      !ReadClosed2(g_vrc,23,vrc_previous) || !ReadClosed1(g_vrc,22,s.vrc_direction) ||
      !ReadClosed1(g_vrc,19,s.vrc_vol_percentile) || !ReadClosed1(g_vrc,26,vrc_high) ||
      !ReadClosed1(g_vrc,27,vrc_low) ||
      !ReadClosed1(g_mbb,3,s.mbb_upper) || !ReadClosed1(g_mbb,5,s.mbb_lower) ||
      !ReadClosed1(g_mbb,7,s.mbb_basis) || !ReadClosed1(g_mbb,22,s.mbb_squeeze) ||
      !ReadClosed1(g_mbb,24,release) || !ReadClosed1(g_mbb,25,s1l) ||
      !ReadClosed1(g_mbb,26,s1s) || !ReadClosed1(g_mbb,27,s2l) ||
      !ReadClosed1(g_mbb,28,s2s) || !ReadClosed1(g_mbb,29,s3l) || !ReadClosed1(g_mbb,30,s3s) ||
      !ReadClosed1(g_tb,26,tb_valid) || !ReadClosed1(g_tb,43,tb_contract) ||
      !ReadClosed1(g_tb,2,tb_bias) || !ReadClosed1(g_tb,28,s.tb_atr) ||
      !ReadClosed1(g_qqe,3,s.qqe_primary) || !ReadClosed2(g_qqe,3,s.qqe_primary_prev) ||
      !ReadClosed1(g_qqe,4,s.qqe_secondary) || !ReadClosed2(g_qqe,4,s.qqe_secondary_prev) ||
      !ReadClosed1(g_qqe,8,state)) return(false);

   if(aird_valid<0.5 || vrc_valid<0.5 || tb_valid<0.5 || tb_contract+1e-9<RSF_REQUIRED_TB_CONTRACT_VERSION ||
      aird_regime<0.0 || aird_regime>3.0 || s.mbb_upper<=s.mbb_lower || s.tb_atr<=0.0) return(false);

   s.aird_regime=(int)MathRound(aird_regime);
   s.aird_confidence=aird_conf_pct/100.0;
   s.vrc_regime=(int)MathRound(vrc_regime);
   s.vrc_previous_regime=(int)MathRound(vrc_previous);
   s.vrc_high_vol=vrc_high>0.5;
   s.vrc_low_vol=vrc_low>0.5;
   s.mbb_release=release>0.5;
   s.s1_long=s1l>0.5; s.s1_short=s1s>0.5;
   s.s2_long=s2l>0.5; s.s2_short=s2s>0.5;
   s.s3_long=s3l>0.5; s.s3_short=s3s>0.5;
   s.tb_bias=(int)MathRound(tb_bias);
   s.qqe_state=(int)MathRound(state);

   s.tb_swing_high=OptionalClosed1(g_tb,13,0.0);
   s.tb_swing_low=OptionalClosed1(g_tb,14,0.0);
   s.tb_cell_top=OptionalClosed1(g_tb,19,0.0);
   s.tb_cell_bottom=OptionalClosed1(g_tb,20,0.0);
   tb_cell_side=OptionalClosed1(g_tb,21,0.0); s.tb_cell_side=(int)MathRound(tb_cell_side);
   s.tb_void_top=OptionalClosed1(g_tb,32,OptionalClosed1(g_tb,22,0.0));
   s.tb_void_bottom=OptionalClosed1(g_tb,33,OptionalClosed1(g_tb,23,0.0));
   tb_void_side=OptionalClosed1(g_tb,25,0.0); s.tb_void_side=(int)MathRound(tb_void_side);
   s.tb_structure_level=OptionalClosed1(g_tb,29,0.0);

   int age=0; double marker=0.0;
   s.tb_sweep_high=RecentFlag(g_tb,7,InpStructureEventMaxAgeBars,age,marker,0);
   s.tb_sweep_high_price=marker;
   s.tb_sweep_low=RecentFlag(g_tb,8,InpStructureEventMaxAgeBars,age,marker,1);
   s.tb_sweep_low_price=marker;
   bool bos_up=RecentFlag(g_tb,3,InpStructureEventMaxAgeBars,age,marker);
   bool mss_up=RecentFlag(g_tb,4,InpStructureEventMaxAgeBars,age,marker);
   bool bos_down=RecentFlag(g_tb,5,InpStructureEventMaxAgeBars,age,marker);
   bool mss_down=RecentFlag(g_tb,6,InpStructureEventMaxAgeBars,age,marker);
   s.tb_structure_up=bos_up||mss_up;
   s.tb_structure_down=bos_down||mss_down;
   s.tb_displacement_up=RecentFlag(g_tb,11,InpStructureEventMaxAgeBars,age,marker);
   s.tb_displacement_down=RecentFlag(g_tb,12,InpStructureEventMaxAgeBars,age,marker);
   s.ready=true;
   return(true);
  }

string SignalName(const ENUM_RSF_SIGNAL signal)
  {
   if(signal==RSF_RANGE_LONG) return("RANGE_LONG");
   if(signal==RSF_RANGE_SHORT) return("RANGE_SHORT");
   if(signal==RSF_TREND_LONG) return("TREND_LONG");
   if(signal==RSF_TREND_SHORT) return("TREND_SHORT");
   if(signal==RSF_BREAKOUT_LONG) return("BREAKOUT_LONG");
   if(signal==RSF_BREAKOUT_SHORT) return("BREAKOUT_SHORT");
   return("NONE");
  }

bool HasForeignSymbolPosition()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket) || PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      if((long)PositionGetInteger(POSITION_MAGIC)!=InpMagic) return(true);
     }
   return(false);
  }

ulong OwnedPositionTicket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (long)PositionGetInteger(POSITION_MAGIC)==InpMagic) return(ticket);
     }
   return(0);
  }

ENUM_ORDER_TYPE_FILLING ResolveFilling()
  {
   long flags=SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE);
   if((flags&ORDER_FILLING_FOK)==ORDER_FILLING_FOK) return(ORDER_FILLING_FOK);
   if((flags&ORDER_FILLING_IOC)==ORDER_FILLING_IOC) return(ORDER_FILLING_IOC);
   return(ORDER_FILLING_RETURN);
  }

double NormalizeVolumeDown(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || maximum<=0.0) return(0.0);
   double volume=MathFloor(MathMin(raw,maximum)/step+1e-9)*step;
   if(volume<minimum-1e-9) return(0.0);
   int digits=0; double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-9) { probe*=10.0; digits++; }
   return(NormalizeDouble(volume,digits));
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,const double risk_scale,double &risk_account)
  {
   risk_account=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0*risk_scale;
   double profit=0.0;
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(risk_account<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,profit) || profit>=0.0) return(0.0);
   double volume=NormalizeVolumeDown(risk_account/MathAbs(profit));
   if(volume<=0.0) return(0.0);
   double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double used_margin=AccountInfoDouble(ACCOUNT_MARGIN);
   ENUM_ACCOUNT_STOPOUT_MODE so_mode=(ENUM_ACCOUNT_STOPOUT_MODE)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE);
   double stopout_level=AccountInfoDouble(ACCOUNT_MARGIN_SO_SO);
   double required_margin_level=InpMinPostTradeMarginLevelPct;
   if(so_mode==ACCOUNT_STOPOUT_MODE_PERCENT && stopout_level>0.0)
      required_margin_level=MathMax(required_margin_level,stopout_level*1.25);
   // Money-mode stop-out is expressed in account currency and is applied to
   // free margin, not to equity.  Keep both a percentage-of-equity cushion and
   // two planned losses above that broker floor.  This is intentionally checked
   // for every candidate volume because stepping volume down releases margin.
   double money_buffer=MathMax(equity*InpMoneyStopoutBufferPct/100.0,risk_account*2.0);
   double required_free_margin=(so_mode==ACCOUNT_STOPOUT_MODE_MONEY && stopout_level>0.0 ? stopout_level+money_buffer : 0.0);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double margin=0.0;
   bool margin_ok=false;
   while(volume>=minimum-1e-9)
     {
      if(OrderCalcMargin(type,_Symbol,volume,entry,margin) && margin<=free_margin*0.50)
        {
         double projected_margin=used_margin+margin;
         double projected_level=(projected_margin>0.0 ? equity/projected_margin*100.0 : DBL_MAX);
         double projected_free_margin=free_margin-margin;
         bool level_ok=projected_level+1e-9>=required_margin_level;
         bool money_ok=(required_free_margin<=0.0 || projected_free_margin+1e-9>=required_free_margin);
         if(level_ok && money_ok) { margin_ok=true; break; }
        }
      volume=NormalizeVolumeDown(volume-step);
     }
   if(!margin_ok || volume<minimum-1e-9 || margin>free_margin*0.50) return(0.0);
   risk_account=MathAbs(profit)*volume;
   return(volume);
  }

void ConsiderAnchor(const int direction,const double entry,const double candidate,double &anchor,bool &valid)
  {
   if(candidate<=0.0) return;
   if(direction>0 && candidate<entry && (!valid || candidate<anchor)) { anchor=candidate; valid=true; }
   if(direction<0 && candidate>entry && (!valid || candidate>anchor)) { anchor=candidate; valid=true; }
  }

bool BuildDecision(const RsfSnapshot &s,const SymbolProfile &profile,TradeDecision &d)
  {
   ZeroMemory(d); d.signal=RSF_SIGNAL_NONE; d.fired=false;
   bool qqe_rising=s.qqe_primary>s.qqe_primary_prev && s.qqe_secondary>s.qqe_secondary_prev;
   bool qqe_falling=s.qqe_primary<s.qqe_primary_prev && s.qqe_secondary<s.qqe_secondary_prev;
   bool qqe_long=s.qqe_primary>InpTrendQQEMin && s.qqe_secondary>InpTrendQQEMin && s.qqe_state>=0;
   bool qqe_short=s.qqe_primary<-InpTrendQQEMin && s.qqe_secondary<-InpTrendQQEMin && s.qqe_state<=0;

   bool context_confident=!InpUseContextRouter || s.aird_confidence+1e-12>=InpMinAirdConfidence;
   bool range_context=!InpUseContextRouter || (context_confident &&
                      (s.vrc_regime==2 || s.vrc_regime==3) &&
                      (s.aird_regime==2 || s.p_range/100.0>=InpMinAirdStateProbability));
   bool bull_context=!InpUseContextRouter || (context_confident &&
                     (s.vrc_regime>=4 && s.vrc_regime<=6 && s.vrc_direction>0.0) &&
                     (s.aird_regime==0 || s.p_bull/100.0>=InpMinAirdStateProbability));
   bool bear_context=!InpUseContextRouter || (context_confident &&
                     (s.vrc_regime>=-1 && s.vrc_regime<=1 && s.vrc_direction<0.0) &&
                     (s.aird_regime==1 || s.p_bear/100.0>=InpMinAirdStateProbability));
   // Context-off removes VRC compression state; MBB release remains mandatory.
   bool compression_origin=InpUseContextRouter ?
                           (s.vrc_previous_regime==7 || s.vrc_low_vol || s.mbb_release) : s.mbb_release;
   bool zone_long=(s.tb_cell_side>0 || s.tb_void_side>0);
   bool zone_short=(s.tb_cell_side<0 || s.tb_void_side<0);
   bool saw_setup=false,failed_context=false,failed_structure=false,failed_timing=false;

   // Breakout has priority because its release event is short-lived.
   if(InpAllowBreakoutMode && (profile.modes&RSF_MODE_BREAKOUT)!=0 && (s.s3_long || s.s3_short))
     {
      saw_setup=true;
      int direction=(s.s3_long ? 1 : -1);
      bool context_ok=compression_origin && context_confident;
      bool structure_ok=!InpUseTbStructure || (direction>0 ? (s.tb_structure_up && s.tb_displacement_up) : (s.tb_structure_down && s.tb_displacement_down));
      bool timing_ok=!InpUseQqeTiming || (direction>0 ? qqe_long : qqe_short);
      if(!context_ok) failed_context=true;
      else if(!structure_ok) failed_structure=true;
      else if(!timing_ok) failed_timing=true;
      else d.signal=(direction>0 ? RSF_BREAKOUT_LONG : RSF_BREAKOUT_SHORT);
      if(d.signal!=RSF_SIGNAL_NONE) g_breakout_setups++;
     }

   if(d.signal==RSF_SIGNAL_NONE && InpAllowTrendMode && (profile.modes&RSF_MODE_TREND)!=0 && (s.s2_long || s.s2_short))
     {
      saw_setup=true;
      int direction=(s.s2_long ? 1 : -1);
      bool context_ok=(direction>0 ? bull_context : bear_context);
      bool structure_ok=!InpUseTbStructure || (direction>0 ? (s.tb_bias>0 && (s.tb_structure_up||zone_long)) : (s.tb_bias<0 && (s.tb_structure_down||zone_short)));
      bool timing_ok=!InpUseQqeTiming || (direction>0 ? qqe_long : qqe_short);
      if(!context_ok) failed_context=true;
      else if(!structure_ok) failed_structure=true;
      else if(!timing_ok) failed_timing=true;
      else d.signal=(direction>0 ? RSF_TREND_LONG : RSF_TREND_SHORT);
      if(d.signal!=RSF_SIGNAL_NONE) g_trend_setups++;
     }

   if(d.signal==RSF_SIGNAL_NONE && InpAllowRangeMode && (profile.modes&RSF_MODE_RANGE)!=0 && (s.s1_long || s.s1_short))
     {
      saw_setup=true;
      int direction=(s.s1_long ? 1 : -1);
      bool context_ok=range_context;
      bool structure_ok=!InpUseTbStructure || (direction>0 ? s.tb_sweep_low : s.tb_sweep_high);
      bool timing_ok=!InpUseQqeTiming || (direction>0 ? (qqe_rising && MathMin(s.qqe_primary,s.qqe_secondary)<=-InpRangeQQEExtreme) : (qqe_falling && MathMax(s.qqe_primary,s.qqe_secondary)>=InpRangeQQEExtreme));
      if(!context_ok) failed_context=true;
      else if(!structure_ok) failed_structure=true;
      else if(!timing_ok) failed_timing=true;
      else d.signal=(direction>0 ? RSF_RANGE_LONG : RSF_RANGE_SHORT);
      if(d.signal!=RSF_SIGNAL_NONE) g_range_setups++;
     }

   if(d.signal==RSF_SIGNAL_NONE)
     {
      if(!saw_setup) g_reject_setup++;
      else if(failed_timing) g_reject_timing++;
      else if(failed_structure) g_reject_structure++;
      else if(failed_context) g_reject_context++;
      else g_reject_setup++;
      return(false);
     }
   d.direction=(d.signal>0 ? 1 : -1);

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return(false);
   double entry=d.direction>0 ? tick.ask : tick.bid;
   double spread=tick.ask-tick.bid;
   double half_width=(s.mbb_upper-s.mbb_lower)*0.5;
   long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double minimum_distance=MathMax((stops_level+2)*_Point,MathMax(spread*3.0,s.tb_atr*InpMinStopAtr));
   double risk_distance=MathMax(minimum_distance,half_width*InpMbbHalfWidthStopMult);

   double anchor=0.0; bool anchor_valid=false;
   if(InpUseTbStructure && (d.signal==RSF_RANGE_LONG || d.signal==RSF_RANGE_SHORT))
     {
      ConsiderAnchor(d.direction,entry,d.direction>0 ? s.tb_sweep_low_price : s.tb_sweep_high_price,anchor,anchor_valid);
      ConsiderAnchor(d.direction,entry,d.direction>0 ? s.tb_swing_low : s.tb_swing_high,anchor,anchor_valid);
     }
   else if(InpUseTbStructure && (d.signal==RSF_TREND_LONG || d.signal==RSF_TREND_SHORT))
     {
      ConsiderAnchor(d.direction,entry,d.direction>0 ? s.tb_cell_bottom : s.tb_cell_top,anchor,anchor_valid);
      ConsiderAnchor(d.direction,entry,d.direction>0 ? s.tb_void_bottom : s.tb_void_top,anchor,anchor_valid);
     }
   else if(InpUseTbStructure)
      ConsiderAnchor(d.direction,entry,s.tb_structure_level,anchor,anchor_valid);

   if(anchor_valid)
      risk_distance=MathMax(risk_distance,MathAbs(entry-anchor)+s.tb_atr*InpStructureBufferAtr);
   if(risk_distance<=0.0 || risk_distance>s.tb_atr*InpMaxStopAtr || spread/risk_distance>InpMaxSpreadToStop)
     { g_reject_risk++; return(false); }

   d.stop=NormalizeDouble(entry-d.direction*risk_distance,_Digits);
   d.target=NormalizeDouble(entry+d.direction*risk_distance*InpRewardRisk,_Digits);
   if((d.direction>0 && (d.stop>=tick.bid || d.target<=tick.ask)) ||
      (d.direction<0 && (d.stop<=tick.ask || d.target>=tick.bid)))
     { g_reject_risk++; return(false); }
   bool high_vol=(s.aird_regime==3 || s.vrc_high_vol);
   d.risk_scale=profile.risk_scale*(high_vol ? InpHighVolRiskScale : 1.0);
   d.reason=SignalName(d.signal);
   d.fired=true;
   return(true);
  }

bool SubmitEntry(const TradeDecision &d)
  {
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return(false);
   double entry=d.direction>0 ? tick.ask : tick.bid;
   double risk_account=0.0;
   double volume=RiskSizedVolume(d.direction,entry,d.stop,d.risk_scale,risk_account);
   if(volume<=0.0) { g_reject_risk++; return(false); }

   MqlTradeRequest request; MqlTradeCheckResult check; MqlTradeResult result;
   ZeroMemory(request); ZeroMemory(check); ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL; request.magic=(ulong)InpMagic; request.symbol=_Symbol;
   request.volume=volume; request.type=d.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=entry; request.sl=d.stop; request.tp=d.target;
   request.deviation=(ulong)InpDeviationPoints; request.type_filling=ResolveFilling();
   request.comment=d.reason;
   ResetLastError();
   if(!OrderCheck(request,check)) { g_reject_execution++; g_last_reason="ORDER_CHECK"; return(false); }
   g_pending_signal=d.signal; g_pending_sl=d.stop; g_pending_tp=d.target; g_pending_risk_account=risk_account;
   if(!OrderSend(request,result) || (result.retcode!=TRADE_RETCODE_DONE && result.retcode!=TRADE_RETCODE_PLACED && result.retcode!=TRADE_RETCODE_DONE_PARTIAL))
     { g_reject_execution++; g_last_reason=StringFormat("ORDER_SEND_%u",result.retcode); g_pending_signal=RSF_SIGNAL_NONE; return(false); }
   g_last_entry_bar_time=g_last_bar_time; g_last_reason=d.reason;
   return(true);
  }

bool CloseOwnedPosition(const ulong ticket,const string reason)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket)) return(false);
   long type=PositionGetInteger(POSITION_TYPE);
   double volume=PositionGetDouble(POSITION_VOLUME);
   MqlTick tick; if(volume<=0.0 || !SymbolInfoTick(_Symbol,tick)) return(false);
   MqlTradeRequest request; MqlTradeResult result; ZeroMemory(request); ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL; request.magic=(ulong)InpMagic; request.position=ticket;
   request.symbol=_Symbol; request.volume=volume;
   request.type=type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)InpDeviationPoints; request.type_filling=ResolveFilling(); request.comment=reason;
   return(OrderSend(request,result) && (result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL || result.retcode==TRADE_RETCODE_PLACED));
  }

bool RemainingVolumeThroughDeal(const ulong position_id,const ulong target_deal,double &remaining)
  {
   remaining=0.0; if(!HistorySelect(0,TimeCurrent()+60)) return(false);
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong deal=HistoryDealGetTicket(i); if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id) continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      double volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT) remaining+=volume;
      if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY || entry==DEAL_ENTRY_INOUT) remaining-=volume;
      if(deal==target_deal) break;
     }
   return(true);
  }

double NetProfitThroughDeal(const ulong position_id,const ulong target_deal)
  {
   double net=0.0; if(!HistorySelect(0,TimeCurrent()+60)) return(0.0);
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong deal=HistoryDealGetTicket(i); if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id) continue;
      net+=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_FEE);
      if(deal==target_deal) break;
     }
   return(net);
  }

string JsonEscape(string value)
  {
   StringReplace(value,"\\","\\\\"); StringReplace(value,"\"","\\\""); return(value);
  }

string SafeToken(string value)
  {
   StringReplace(value," ","_"); StringReplace(value,"/","_"); StringReplace(value,"\\","_"); StringReplace(value,":","_"); return(value);
  }

// The forensic EA includes this engine source directly.  MQL_PROGRAM_NAME is
// therefore the only reliable identity for lifecycle telemetry: it resolves
// to the parent EA in normal runs and to the wrapper in forensic runs.  Keep
// the constant only as a defensive fallback for unusual tester environments.
string RuntimeEAName()
  {
   string name=MQLInfoString(MQL_PROGRAM_NAME);
   return(name=="" ? RSF_EA_NAME : name);
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="") return(true);
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE) return(false);
   SymbolProfile effective_profile; ResolveProfile(effective_profile);
   string payload="{";
   payload+="\"schema_version\":\"alphafactory_run_meta.v1\",";
   payload+="\"run_id\":\""+JsonEscape(g_run_id)+"\",\"ea_name\":\""+JsonEscape(RuntimeEAName())+"\",";
   payload+="\"symbol\":\""+JsonEscape(_Symbol)+"\",\"hypothesis_id\":\""+JsonEscape(InpHypothesisId)+"\",";
   payload+="\"variant_tag\":\""+JsonEscape(InpVariantTag)+"\",\"telemetry_profile\":\""+RSF_TELEMETRY_PROFILE+"\",";
   payload+="\"clock_profile\":\""+(InpClockProfile==RSF_CLOCK_EET_EEST ? "EET_EEST_EU_DST" : "FIXED_OFFSET")+"\",";
   payload+="\"economic_claims_authorized\":false,\"promotion_eligible\":false,\"closed_bar\":true,";
   payload+=StringFormat("\"effective_session_mask\":%d,\"effective_mode_mask\":%d,",effective_profile.sessions,effective_profile.modes);
   payload+="\"use_context_router\":"+(InpUseContextRouter ? "true" : "false")+",\"use_tb_structure\":"+(InpUseTbStructure ? "true" : "false")+",\"use_qqe_timing\":"+(InpUseQqeTiming ? "true" : "false")+",";
   payload+=StringFormat("\"account_margin_so_mode\":%d,\"account_margin_so_call\":%.8f,\"account_margin_so_stopout\":%.8f,",(int)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE),AccountInfoDouble(ACCOUNT_MARGIN_SO_CALL),AccountInfoDouble(ACCOUNT_MARGIN_SO_SO));
   payload+=StringFormat("\"risk_margin_level_floor_pct\":%.8f,\"money_stopout_buffer_pct\":%.8f,",InpMinPostTradeMarginLevelPct,InpMoneyStopoutBufferPct);
   payload+="\"funnel\":{";
   payload+=StringFormat("\"ticks_seen\":%I64d,\"closed_bars_seen\":%I64d,\"indicator_ready\":%I64d,\"indicator_not_ready\":%I64d,",g_ticks_seen,g_closed_bars_seen,g_indicator_ready,g_indicator_not_ready);
   payload+=StringFormat("\"range_setups\":%I64d,\"trend_setups\":%I64d,\"breakout_setups\":%I64d,",g_range_setups,g_trend_setups,g_breakout_setups);
   payload+=StringFormat("\"reject_session\":%I64d,\"reject_setup\":%I64d,\"reject_context\":%I64d,\"reject_structure\":%I64d,\"reject_timing\":%I64d,",g_reject_session,g_reject_setup,g_reject_context,g_reject_structure,g_reject_timing);
   payload+=StringFormat("\"reject_risk\":%I64d,\"reject_execution\":%I64d,\"entries_opened\":%I64d,\"final_closes\":%I64d,",g_reject_risk,g_reject_execution,g_entries_opened,g_final_closes);
   payload+="\"last_reason\":\""+JsonEscape(g_last_reason)+"\"}}";
   FileWriteString(handle,payload); FileClose(handle); return(true);
  }

bool OpenTelemetry()
  {
   g_run_id=StringFormat("%s_%I64u",SafeToken(InpHypothesisId),GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_lifecycle_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE) return(false);
   FileWrite(g_lifecycle_handle,"event_time","utc_time","tag","action","order_type","volume","price","sl","tp","reason","deal","order","symbol","position_id","entry_price","initial_sl","initial_tp","risk_pts","initial_risk_account","achievedr","net_profit","deal_net","is_final_close","engine_name","hypothesis_id");
   FileFlush(g_lifecycle_handle); return(WriteRunMeta());
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal) || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY) return;
   datetime event_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   double volume=HistoryDealGetDouble(deal,DEAL_VOLUME),price=HistoryDealGetDouble(deal,DEAL_PRICE);
   if(event_time<=0 || volume<=0.0 || price<=0.0) return;
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   ulong order_id=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
   ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   bool is_open=entry==DEAL_ENTRY_IN; bool is_final=false;
   if(is_open)
     {
      g_active_position_id=position_id; g_active_signal=g_pending_signal; g_active_entry=price;
      g_active_sl=g_pending_sl; g_active_tp=g_pending_tp; g_active_risk_account=g_pending_risk_account;
      g_entries_opened++; g_trades_today++;
     }
   else
     {
      double remaining=0.0;
      if(RemainingVolumeThroughDeal(position_id,deal,remaining))
         is_final=remaining<=MathMax(1e-8,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP)*0.5);
     }
   double deal_net=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_FEE);
   double aggregate_net=is_open ? deal_net : NetProfitThroughDeal(position_id,deal);
   double achieved_r=g_active_risk_account>0.0 ? aggregate_net/g_active_risk_account : 0.0;
   double risk_points=(g_active_entry>0.0 && g_active_sl>0.0) ? MathAbs(g_active_entry-g_active_sl)/_Point : 0.0;
   if(g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileWrite(g_lifecycle_handle,TimeToString(event_time,TIME_DATE|TIME_SECONDS),TimeToString(ServerToUtc(event_time),TIME_DATE|TIME_SECONDS),InpVariantTag,is_open?"OPEN":(is_final?"CLOSE":"CLOSE_PARTIAL"),deal_type==DEAL_TYPE_BUY?"BUY":"SELL",DoubleToString(volume,8),DoubleToString(price,_Digits),DoubleToString(g_active_sl,_Digits),DoubleToString(g_active_tp,_Digits),EnumToString((ENUM_DEAL_REASON)HistoryDealGetInteger(deal,DEAL_REASON)),StringFormat("%I64u",deal),StringFormat("%I64u",order_id),_Symbol,StringFormat("%I64u",position_id),DoubleToString(g_active_entry,_Digits),DoubleToString(g_active_sl,_Digits),DoubleToString(g_active_tp,_Digits),DoubleToString(risk_points,4),DoubleToString(g_active_risk_account,8),DoubleToString(achieved_r,8),DoubleToString(aggregate_net,8),DoubleToString(deal_net,8),is_final?"1":"0",SignalName(g_active_signal),InpHypothesisId);
      FileFlush(g_lifecycle_handle);
     }
   if(is_final)
     {
      g_final_closes++; g_active_position_id=0; g_active_signal=RSF_SIGNAL_NONE;
      g_active_entry=0.0; g_active_sl=0.0; g_active_tp=0.0; g_active_risk_account=0.0;
     }
   if(is_open) g_pending_signal=RSF_SIGNAL_NONE;
   WriteRunMeta();
  }

void RefreshRiskLocks(const datetime utc_now)
  {
   int key=DateKey(utc_now); double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_day_key!=key) { g_day_key=key; g_day_start_equity=equity; g_trades_today=0; g_daily_locked=false; }
   if(g_peak_equity<=0.0 || equity>g_peak_equity) g_peak_equity=equity;
   if(g_day_start_equity>0.0 && 100.0*(g_day_start_equity-equity)/g_day_start_equity>=InpMaxDailyLossPct) g_daily_locked=true;
   if(g_peak_equity>0.0 && 100.0*(g_peak_equity-equity)/g_peak_equity>=InpMaxAccountDrawdownPct) g_account_locked=true;
  }

void ManagePosition(const datetime utc_now)
  {
   ulong ticket=OwnedPositionTicket(); if(ticket==0 || !PositionSelectByTicket(ticket)) return;
   MqlDateTime p; TimeToStruct(utc_now,p); int minute=p.hour*60+p.min;
   if(p.day_of_week==5 && minute>=InpFridayFlattenMinutesUtc) { CloseOwnedPosition(ticket,"FRIDAY_FLAT"); return; }
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(opened>0 && TimeCurrent()-opened>=InpMaxHoldBars*PeriodSeconds(PERIOD_M5)) CloseOwnedPosition(ticket,"MAX_HOLD");
  }

void DetectNewEntryBar(bool &is_new)
  {
   is_new=false;
   datetime current_bar=iTime(_Symbol,PERIOD_M5,0);
   if(current_bar==g_last_bar_time) { return; }
   if(current_bar<=0) return;
   g_last_bar_time=current_bar;
   is_new=true;
  }

bool ValidateInputs()
  {
   if(!InpResearchAutoMode || !InpEnableTelemetry || !MQLInfoInteger(MQL_TESTER) || _Period!=PERIOD_M5) return(false);
   if(InpExpectedSymbol!=_Symbol || StringFind(InpHypothesisId,"HYP-RSF-")!=0 || InpHypothesisId=="UNREGISTERED_BUILD_ONLY") return(false);
   if(InpMagic<=0 || InpRiskPercent<=0.0 || InpRiskPercent>1.0 || InpHighVolRiskScale<=0.0 || InpHighVolRiskScale>1.0) return(false);
   if(InpMaxDailyLossPct<=0.0 || InpMaxDailyLossPct>3.5 || InpMaxAccountDrawdownPct<=0.0 || InpMaxAccountDrawdownPct>8.0) return(false);
   if(InpMinPostTradeMarginLevelPct<100.0 || InpMinPostTradeMarginLevelPct>1000000.0) return(false);
   if(InpMoneyStopoutBufferPct<0.0 || InpMoneyStopoutBufferPct>50.0) return(false);
   if(InpMaxTradesPerDay<1 || InpMaxTradesPerDay>5 || InpMaxHoldBars<1 || InpMaxHoldBars>288 || InpEntryCooldownBars<0) return(false);
   if(InpMinAirdConfidence<0.25 || InpMinAirdConfidence>0.90 || InpMinAirdStateProbability<0.25 || InpMinAirdStateProbability>0.90) return(false);
   if(InpStructureEventMaxAgeBars<1 || InpStructureEventMaxAgeBars>12 || InpRewardRisk<0.5 || InpRewardRisk>4.0) return(false);
   if(InpMinStopAtr<=0.0 || InpMaxStopAtr<=InpMinStopAtr || InpMbbHalfWidthStopMult<=0.0 || InpMaxSpreadToStop<=0.0) return(false);
   if(InpProfileMode==RSF_PROFILE_MANUAL && (InpManualSessionMask<=0 || InpManualModeMask<=0 || InpManualRiskScale<=0.0 || InpManualRiskScale>1.0)) return(false);
   return(true);
  }

// AIRD/VRC/MBB/TB expose a versioned string as their first input.  It is a
// stable primitive ABI across separately compiled EX5 modules and leaves all
// chart-facing inputs untouched when empty.  The EA still exposes every engine
// field independently; only the transport across iCustom is packed.
string ContractInt(const long value) { return(IntegerToString((int)value)); }
string ContractBool(const bool value) { return(value ? "1" : "0"); }
string ContractDouble(const double value) { return(DoubleToString(value,8)); }

int CreateAirdHandle()
  {
   string c="RSF1|"+ContractDouble(InpAirdPersistence)+"|"+ContractDouble(InpAirdTransitionRate)+"|"
            +ContractDouble(InpAirdEmissionRate)+"|"+ContractBool(InpAirdAdaptive)+"|"+ContractInt(InpAirdKernel)+"|"
            +ContractDouble(InpAirdSwitchMargin)+"|"+ContractInt(InpAirdConfirmBars)+"|"+ContractDouble(InpAirdTemperature)+"|"
            +ContractInt(InpAirdCorrelationLength)+"|"+ContractInt(InpAirdRsiLength)+"|"+ContractInt(InpAirdVolatilityLength)+"|"
            +ContractInt(InpAirdVolRankLength)+"|"+ContractInt(InpAirdDriftLength);
   return(iCustom(_Symbol,InpContextTimeframe,"AlphaFactory\\AI_Regime_Detection",c));
  }

int CreateVrcHandle()
  {
   string c="RSF1|"+ContractInt(InpVrcHurstLength)+"|"+ContractInt(InpVrcAdxLength)+"|"
            +ContractInt(InpVrcAdxSmoothing)+"|"+ContractInt(InpVrcChopLength)+"|"+ContractInt(InpVrcVolatilityLength)+"|"
            +ContractInt(InpVrcVolPercentileLength)+"|"+ContractDouble(InpVrcAdxTrendThreshold)+"|"
            +ContractDouble(InpVrcAdxStrongThreshold)+"|"+ContractDouble(InpVrcChopRangeThreshold)+"|"
            +ContractDouble(InpVrcHurstTrendThreshold)+"|"+ContractDouble(InpVrcHurstMrThreshold)+"|"
            +ContractDouble(InpVrcVolHighPercentile)+"|"+ContractDouble(InpVrcVolLowPercentile);
   return(iCustom(_Symbol,InpContextTimeframe,"AlphaFactory\\Volatility_Regime_Classifier_QuantRegime",c));
  }

int CreateMbbHandle()
  {
   string c="RSF1|"+ContractInt(InpMbbLengthMode)+"|"+ContractInt(InpMbbFixedLength)+"|"
            +ContractInt(InpMbbBasisMode)+"|"+ContractInt(InpMbbBandMode)+"|"+ContractDouble(InpMbbStdevMultiplier)+"|"
            +ContractDouble(InpMbbRobustUpperPct)+"|"+ContractDouble(InpMbbRobustLowerPct)+"|"
            +ContractInt(InpMbbRobustWindowMult)+"|"+ContractInt(InpMbbRobustWindowFloor)+"|"
            +ContractInt(InpMbbKamaFast)+"|"+ContractInt(InpMbbKamaSlow)+"|"+ContractInt(InpMbbKerLength)+"|"
            +ContractInt(InpMbbRankLength)+"|"+ContractDouble(InpMbbTrendEnter)+"|"+ContractDouble(InpMbbTrendExit)+"|"
            +ContractDouble(InpMbbSqueezeThreshold)+"|"+ContractInt(InpMbbSqueezeMinBars)+"|"
            +ContractDouble(InpMbbBasisTouchFraction);
   return(iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\Modern_Bollinger_Bands_GBB",c));
  }

int CreateTbHandle()
  {
   string c="RSF1|"+ContractInt(TB_PROFILE_EA_CUSTOM)+"|"+ContractInt(InpTbSwingLength)+"|"
            +ContractDouble(InpTbDisplacementAtr)+"|"+ContractInt(InpTbCellsKept)+"|"+ContractInt(InpTbVoidsKept)+"|"
            +ContractDouble(InpTbSweepReclaimAtr)+"|"+ContractDouble(InpTbMinimumVoidAtr)+"|"
            +ContractDouble(InpTbMinimumCellAtr)+"|"+ContractInt(InpTbMaximumCellAgeBars)+"|"
            +ContractInt(InpTbMaximumVoidAgeBars)+"|"+ContractBool(InpTbSweepsRequireLiveSwing)+"|"
            +ContractBool(InpTbRequireBothSwings)+"|"+ContractBool(InpTbEnableStructure)+"|"
            +ContractBool(InpTbEnableCells)+"|"+ContractBool(InpTbEnableVoids)+"|"
            +ContractBool(InpTbEnableSweeps)+"|"+ContractInt(InpTbVoidRetention);
   return(iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\TB_Smart_Money_Concept_2026",c));
  }

int CreateQqeHandle()
  {
   // MQL5 compiles every `input group` declaration into the positional
   // iCustom ABI.  Keep the group strings in the call or all following values
   // shift left (for example SecondaryThreshold receives BollingerLength).
   return(iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\QQE_MOD",
                  "Primary QQE Settings",
                  InpQqePrimaryRsiLength,InpQqePrimarySmoothing,InpQqePrimaryFactor,InpQqePrimaryThreshold,
                  InpQqePrimarySource,
                  "Secondary QQE Settings",
                  InpQqeSecondaryRsiLength,InpQqeSecondarySmoothing,InpQqeSecondaryFactor,
                  InpQqeSecondaryThreshold,InpQqeSecondarySource,
                  "Bollinger Bands Settings",
                  InpQqeBollingerLength,InpQqeBollingerMultiplier));
  }

int OnInit()
  {
   if(!ValidateInputs())
     {
      Print("RSF fail-closed: tester-only registered hypothesis, matching symbol, telemetry and M5 are mandatory.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   g_aird=CreateAirdHandle();
   g_vrc=CreateVrcHandle();
   g_mbb=CreateMbbHandle();
   g_tb=CreateTbHandle();
   g_qqe=CreateQqeHandle();
   if(g_aird==INVALID_HANDLE || g_vrc==INVALID_HANDLE || g_mbb==INVALID_HANDLE || g_tb==INVALID_HANDLE || g_qqe==INVALID_HANDLE)
     {
      PrintFormat("RSF indicator handle failure aird=%d vrc=%d mbb=%d tb=%d qqe=%d error=%d",g_aird,g_vrc,g_mbb,g_tb,g_qqe,GetLastError());
      return(INIT_FAILED);
     }
   g_last_bar_time=0;
   bool seeded=false;
   DetectNewEntryBar(seeded);
   RefreshRiskLocks(ServerToUtc(TimeCurrent()));
   if(!OpenTelemetry()) return(INIT_FAILED);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   WriteRunMeta();
   if(g_lifecycle_handle!=INVALID_HANDLE) { FileFlush(g_lifecycle_handle); FileClose(g_lifecycle_handle); }
   if(g_aird!=INVALID_HANDLE) IndicatorRelease(g_aird);
   if(g_vrc!=INVALID_HANDLE) IndicatorRelease(g_vrc);
   if(g_mbb!=INVALID_HANDLE) IndicatorRelease(g_mbb);
   if(g_tb!=INVALID_HANDLE) IndicatorRelease(g_tb);
   if(g_qqe!=INVALID_HANDLE) IndicatorRelease(g_qqe);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
  {
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0) LogLifecycleDeal(trans.deal);
  }

void OnTick()
  {
   g_ticks_seen++;
   bool is_new=false;
   DetectNewEntryBar(is_new);
   if(!is_new) return;
   g_closed_bars_seen++;

   datetime utc_now=ServerToUtc(TimeCurrent());
   RefreshRiskLocks(utc_now); ManagePosition(utc_now);
   if(OwnedPositionTicket()!=0 || HasForeignSymbolPosition() || g_daily_locked || g_account_locked || g_trades_today>=InpMaxTradesPerDay) return;
   if(InpEntryCooldownBars>0 && g_last_entry_bar_time>0 && g_last_bar_time-g_last_entry_bar_time<InpEntryCooldownBars*PeriodSeconds(PERIOD_M5)) return;

   SymbolProfile profile; ResolveProfile(profile);
   int session=SessionMaskAtUtc(utc_now);
   if((session&profile.sessions)==0) { g_reject_session++; return; }

   RsfSnapshot snapshot;
   if(!ReadSnapshot(snapshot)) { g_indicator_not_ready++; return; }
   g_indicator_ready++;
   TradeDecision decision;
   if(BuildDecision(snapshot,profile,decision) && decision.fired) SubmitEntry(decision);
  }
