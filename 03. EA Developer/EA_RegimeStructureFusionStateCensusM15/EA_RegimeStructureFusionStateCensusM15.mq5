
#property strict
#property version "1.100"

// Zero-trade research wrapper. The canonical RSF engine owns all five custom
// indicator handles and closed-bar snapshot semantics. This wrapper rejects
// every trading route and exports one discovery row per completed M15 bar.
#define OnInit   RsfBaseOnInit
#define OnDeinit RsfBaseOnDeinit
#define OnTick   RsfBaseOnTick
#define OnTradeTransaction RsfBaseOnTradeTransaction
#define PERIOD_M5 PERIOD_M15
#include "..\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5"
#undef PERIOD_M5
#undef OnInit
#undef OnDeinit
#undef OnTick
#undef OnTradeTransaction

input group "State census - zero trade"
input datetime InpCensusFrom=0;
input datetime InpCensusTo=0;
input int      InpCensusFlushEveryRows=512;

int g_census_handle=INVALID_HANDLE;
long g_census_rows=0;
string g_census_name="";

string CensusFlag(const bool value) { return(value ? "1" : "0"); }

bool CensusInputsValid()
  {
   if(InpCensusFrom<=0 || InpCensusTo<=InpCensusFrom) return(false);
   if(InpCensusFlushEveryRows<1 || InpCensusFlushEveryRows>100000) return(false);
   // A mis-bound task packet must fail before the base EA can submit an order.
   if(InpAllowRangeMode || InpAllowTrendMode || InpAllowBreakoutMode) return(false);
   if(InpUseTemporalSequence || InpUseRoleAwareSequence || InpUseStructuralEventSequence || InpUsePathManagement) return(false);
   return(true);
  }

bool OpenCensus()
  {
   g_census_name=StringFormat("%s_RSFStateCensus_%s.csv",_Symbol,g_run_id);
   g_census_handle=FileOpen(g_census_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_census_handle==INVALID_HANDLE) return(false);
   FileWrite(g_census_handle,
      "decision_time_server","decision_time_utc","source_bar_time_server","source_bar_time_utc",
      "open","high","low","close","spread_points",
      "aird_regime","aird_confidence","p_bull","p_bear","p_range","p_highvol",
      "vrc_regime","vrc_previous_regime","vrc_direction","vrc_vol_percentile","vrc_high_vol","vrc_low_vol",
      "mbb_upper","mbb_lower","mbb_basis","mbb_squeeze","mbb_release",
      "s1_long","s1_short","s2_long","s2_short","s3_long","s3_short",
      "tb_bias","tb_atr","tb_swing_high","tb_swing_low","tb_cell_top","tb_cell_bottom","tb_cell_side",
      "tb_void_top","tb_void_bottom","tb_void_side","tb_structure_level",
      "tb_sweep_high","tb_sweep_low","tb_sweep_high_price","tb_sweep_low_price",
      "tb_structure_up","tb_structure_down","tb_displacement_up","tb_displacement_down",
      "qqe_primary","qqe_primary_prev","qqe_secondary","qqe_secondary_prev","qqe_state",
      "hypothesis_id","variant_tag");
   FileFlush(g_census_handle);
   return(true);
  }

void ExportCensusClosedBar()
  {
   if(g_census_handle==INVALID_HANDLE) return;
   datetime source_time=iTime(_Symbol,PERIOD_M15,1);
   if(source_time<InpCensusFrom || source_time>InpCensusTo) return;
   RsfSnapshot s;
   if(!ReadSnapshot(s)) return;
   MqlTick tick;
   double spread_points=0.0;
   if(SymbolInfoTick(_Symbol,tick) && _Point>0.0) spread_points=(tick.ask-tick.bid)/_Point;
   FileWrite(g_census_handle,
      TimeToString(g_last_bar_time,TIME_DATE|TIME_SECONDS),TimeToString(ServerToUtc(g_last_bar_time),TIME_DATE|TIME_SECONDS),
      TimeToString(source_time,TIME_DATE|TIME_SECONDS),TimeToString(ServerToUtc(source_time),TIME_DATE|TIME_SECONDS),
      DoubleToString(iOpen(_Symbol,PERIOD_M15,1),_Digits),DoubleToString(iHigh(_Symbol,PERIOD_M15,1),_Digits),
      DoubleToString(iLow(_Symbol,PERIOD_M15,1),_Digits),DoubleToString(iClose(_Symbol,PERIOD_M15,1),_Digits),DoubleToString(spread_points,2),
      IntegerToString(s.aird_regime),DoubleToString(s.aird_confidence,8),
      DoubleToString(s.p_bull,8),DoubleToString(s.p_bear,8),DoubleToString(s.p_range,8),DoubleToString(s.p_highvol,8),
      IntegerToString(s.vrc_regime),IntegerToString(s.vrc_previous_regime),DoubleToString(s.vrc_direction,8),
      DoubleToString(s.vrc_vol_percentile,8),CensusFlag(s.vrc_high_vol),CensusFlag(s.vrc_low_vol),
      DoubleToString(s.mbb_upper,_Digits),DoubleToString(s.mbb_lower,_Digits),DoubleToString(s.mbb_basis,_Digits),
      DoubleToString(s.mbb_squeeze,8),CensusFlag(s.mbb_release),
      CensusFlag(s.s1_long),CensusFlag(s.s1_short),CensusFlag(s.s2_long),CensusFlag(s.s2_short),CensusFlag(s.s3_long),CensusFlag(s.s3_short),
      IntegerToString(s.tb_bias),DoubleToString(s.tb_atr,_Digits),DoubleToString(s.tb_swing_high,_Digits),DoubleToString(s.tb_swing_low,_Digits),
      DoubleToString(s.tb_cell_top,_Digits),DoubleToString(s.tb_cell_bottom,_Digits),IntegerToString(s.tb_cell_side),
      DoubleToString(s.tb_void_top,_Digits),DoubleToString(s.tb_void_bottom,_Digits),IntegerToString(s.tb_void_side),DoubleToString(s.tb_structure_level,_Digits),
      CensusFlag(s.tb_sweep_high),CensusFlag(s.tb_sweep_low),DoubleToString(s.tb_sweep_high_price,_Digits),DoubleToString(s.tb_sweep_low_price,_Digits),
      CensusFlag(s.tb_structure_up),CensusFlag(s.tb_structure_down),CensusFlag(s.tb_displacement_up),CensusFlag(s.tb_displacement_down),
      DoubleToString(s.qqe_primary,8),DoubleToString(s.qqe_primary_prev,8),DoubleToString(s.qqe_secondary,8),
      DoubleToString(s.qqe_secondary_prev,8),IntegerToString(s.qqe_state),InpHypothesisId,InpVariantTag);
   g_census_rows++;
   if(g_census_rows%InpCensusFlushEveryRows==0) FileFlush(g_census_handle);
  }

int OnInit()
  {
   if(!CensusInputsValid()) return(INIT_PARAMETERS_INCORRECT);
   int result=RsfBaseOnInit();
   if(result!=INIT_SUCCEEDED) return(result);
   if(!OpenCensus())
     {
      RsfBaseOnDeinit(INIT_FAILED);
      return(INIT_FAILED);
     }
   return(INIT_SUCCEEDED);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
  {
   RsfBaseOnTradeTransaction(trans,request,result);
  }

void OnTick()
  {
   long before=g_closed_bars_seen;
   RsfBaseOnTick();
   if(g_closed_bars_seen>before) ExportCensusClosedBar();
  }

void OnDeinit(const int reason)
  {
   if(g_census_handle!=INVALID_HANDLE)
     {
      FileFlush(g_census_handle);
      FileClose(g_census_handle);
      g_census_handle=INVALID_HANDLE;
     }
   RsfBaseOnDeinit(reason);
  }


