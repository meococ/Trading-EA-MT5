#property strict
#property version "1.000"

// Forensic replay wrapper for the immutable terminal RSF source.  The macro
// aliases preserve every strategy function while allowing this file to add a
// closed-bar indicator snapshot after the base OnTick has finished.  It never
// changes a decision, order, stop, target or risk value.
#define OnInit   RsfBaseOnInit
#define OnDeinit RsfBaseOnDeinit
#define OnTick   RsfBaseOnTick
#include "..\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5"
#undef OnInit
#undef OnDeinit
#undef OnTick

input group "Forensic replay - diagnostic only"
input string InpForensicCaptureWindows="FROZEN_13_V1"; // immutable window-set identity; dates are hard-bound below

int g_forensic_handle=INVALID_HANDLE;
string g_forensic_name="";
datetime g_capture_from[];
datetime g_capture_to[];

bool ParseCaptureWindows()
  {
   ArrayResize(g_capture_from,0);
   ArrayResize(g_capture_to,0);
   if(InpForensicCaptureWindows!="FROZEN_13_V1") return(false);
   string starts[]={
      "2018.10.31 00:55","2019.06.03 23:55","2019.09.04 00:15","2019.09.05 00:10",
      "2019.10.09 01:20","2019.11.29 01:05","2020.04.20 05:05","2020.10.12 00:50",
      "2020.10.15 05:35","2020.11.19 23:15","2020.12.16 00:25","2021.10.28 00:30",
      "2022.06.13 00:00"};
   string ends[]={
      "2018.10.31 16:37","2019.06.04 14:59","2019.09.04 16:59","2019.09.05 15:31",
      "2019.10.09 18:52","2019.11.29 16:36","2020.04.20 22:06","2020.10.12 17:28",
      "2020.10.16 14:59","2020.11.20 14:42","2020.12.16 15:30","2021.10.28 15:38",
      "2022.06.13 15:00"};
   int count=ArraySize(starts);
   if(count!=13 || ArraySize(ends)!=count) return(false);
   for(int i=0;i<count;i++)
     {
      datetime from=StringToTime(starts[i]);
      datetime to=StringToTime(ends[i]);
      if(from<=0 || to<=from) return(false);
      int n=ArraySize(g_capture_from);
      ArrayResize(g_capture_from,n+1);
      ArrayResize(g_capture_to,n+1);
      g_capture_from[n]=from;
      g_capture_to[n]=to;
     }
   return(ArraySize(g_capture_from)>0);
  }

bool IsCaptureTime(const datetime value)
  {
   for(int i=0;i<ArraySize(g_capture_from);i++)
      if(value>=g_capture_from[i] && value<=g_capture_to[i]) return(true);
   return(false);
  }

string Flag(const bool value) { return(value ? "1" : "0"); }

bool OpenForensicTelemetry()
  {
   g_forensic_name=StringFormat("%s_RSFForensic_%s.csv",_Symbol,g_run_id);
   g_forensic_handle=FileOpen(g_forensic_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_forensic_handle==INVALID_HANDLE) return(false);
   FileWrite(g_forensic_handle,
      "decision_time_server","decision_time_utc","source_bar_time_server","source_bar_time_utc",
      "open","high","low","close","spread_points","entry_fired","position_id","engine_name",
      "aird_regime","aird_confidence","p_bull","p_bear","p_range","p_highvol",
      "vrc_regime","vrc_previous_regime","vrc_direction","vrc_vol_percentile","vrc_high_vol","vrc_low_vol",
      "mbb_upper","mbb_lower","mbb_basis","mbb_squeeze","mbb_release",
      "s1_long","s1_short","s2_long","s2_short","s3_long","s3_short",
      "tb_bias","tb_atr","tb_swing_high","tb_swing_low","tb_cell_top","tb_cell_bottom","tb_cell_side",
      "tb_void_top","tb_void_bottom","tb_void_side","tb_structure_level",
      "tb_sweep_high","tb_sweep_low","tb_sweep_high_price","tb_sweep_low_price",
      "tb_structure_up","tb_structure_down","tb_displacement_up","tb_displacement_down",
      "qqe_primary","qqe_primary_prev","qqe_secondary","qqe_secondary_prev","qqe_state",
      "source_hash","hypothesis_id","variant_tag");
   FileFlush(g_forensic_handle);
   return(true);
  }

void ExportClosedBarSnapshot()
  {
   if(g_forensic_handle==INVALID_HANDLE || !IsCaptureTime(g_last_bar_time)) return;
   RsfSnapshot s;
   if(!ReadSnapshot(s)) return;
   datetime source_time=iTime(_Symbol,PERIOD_M5,1);
   MqlTick tick;
   double spread_points=0.0;
   if(SymbolInfoTick(_Symbol,tick) && _Point>0.0) spread_points=(tick.ask-tick.bid)/_Point;
   bool entry_fired=(g_last_entry_bar_time==g_last_bar_time && g_active_position_id>0);
   FileWrite(g_forensic_handle,
      TimeToString(g_last_bar_time,TIME_DATE|TIME_SECONDS),
      TimeToString(ServerToUtc(g_last_bar_time),TIME_DATE|TIME_SECONDS),
      TimeToString(source_time,TIME_DATE|TIME_SECONDS),
      TimeToString(ServerToUtc(source_time),TIME_DATE|TIME_SECONDS),
      DoubleToString(iOpen(_Symbol,PERIOD_M5,1),_Digits),
      DoubleToString(iHigh(_Symbol,PERIOD_M5,1),_Digits),
      DoubleToString(iLow(_Symbol,PERIOD_M5,1),_Digits),
      DoubleToString(iClose(_Symbol,PERIOD_M5,1),_Digits),
      DoubleToString(spread_points,2),Flag(entry_fired),
      entry_fired ? StringFormat("%I64u",g_active_position_id) : "0",
      entry_fired ? SignalName(g_active_signal) : "NONE",
      IntegerToString(s.aird_regime),DoubleToString(s.aird_confidence,8),
      DoubleToString(s.p_bull,8),DoubleToString(s.p_bear,8),DoubleToString(s.p_range,8),DoubleToString(s.p_highvol,8),
      IntegerToString(s.vrc_regime),IntegerToString(s.vrc_previous_regime),DoubleToString(s.vrc_direction,8),
      DoubleToString(s.vrc_vol_percentile,8),Flag(s.vrc_high_vol),Flag(s.vrc_low_vol),
      DoubleToString(s.mbb_upper,_Digits),DoubleToString(s.mbb_lower,_Digits),DoubleToString(s.mbb_basis,_Digits),
      DoubleToString(s.mbb_squeeze,8),Flag(s.mbb_release),
      Flag(s.s1_long),Flag(s.s1_short),Flag(s.s2_long),Flag(s.s2_short),Flag(s.s3_long),Flag(s.s3_short),
      IntegerToString(s.tb_bias),DoubleToString(s.tb_atr,_Digits),DoubleToString(s.tb_swing_high,_Digits),
      DoubleToString(s.tb_swing_low,_Digits),DoubleToString(s.tb_cell_top,_Digits),DoubleToString(s.tb_cell_bottom,_Digits),
      IntegerToString(s.tb_cell_side),DoubleToString(s.tb_void_top,_Digits),DoubleToString(s.tb_void_bottom,_Digits),
      IntegerToString(s.tb_void_side),DoubleToString(s.tb_structure_level,_Digits),
      Flag(s.tb_sweep_high),Flag(s.tb_sweep_low),DoubleToString(s.tb_sweep_high_price,_Digits),
      DoubleToString(s.tb_sweep_low_price,_Digits),Flag(s.tb_structure_up),Flag(s.tb_structure_down),
      Flag(s.tb_displacement_up),Flag(s.tb_displacement_down),
      DoubleToString(s.qqe_primary,8),DoubleToString(s.qqe_primary_prev,8),
      DoubleToString(s.qqe_secondary,8),DoubleToString(s.qqe_secondary_prev,8),IntegerToString(s.qqe_state),
      "E40F29431E8ADA440302F7DEDB7ACD8EBCB48C1308EB6B43936849C128E959D0",InpHypothesisId,InpVariantTag);
   FileFlush(g_forensic_handle);
  }

int OnInit()
  {
   if(!ParseCaptureWindows())
     {
      Print("RSF forensic replay requires frozen capture windows.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   int result=RsfBaseOnInit();
   if(result!=INIT_SUCCEEDED) return(result);
   if(!OpenForensicTelemetry())
     {
      RsfBaseOnDeinit(REASON_INITFAILED);
      return(INIT_FAILED);
     }
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   long before=g_closed_bars_seen;
   RsfBaseOnTick();
   if(g_closed_bars_seen>before) ExportClosedBarSnapshot();
  }

void OnDeinit(const int reason)
  {
   if(g_forensic_handle!=INVALID_HANDLE)
     {
      FileFlush(g_forensic_handle);
      FileClose(g_forensic_handle);
      g_forensic_handle=INVALID_HANDLE;
     }
   RsfBaseOnDeinit(reason);
  }
