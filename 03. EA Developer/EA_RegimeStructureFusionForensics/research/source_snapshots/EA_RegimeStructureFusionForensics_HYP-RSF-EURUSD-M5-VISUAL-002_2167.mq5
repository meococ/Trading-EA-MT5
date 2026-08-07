#property strict
#property version "1.000"

// Forensic replay wrapper for the immutable terminal RSF source.  The macro
// aliases preserve every strategy function while allowing this file to add a
// closed-bar indicator snapshot after the base OnTick has finished.  It never
// changes a decision, order, stop, target or risk value.
#define OnInit   RsfBaseOnInit
#define OnDeinit RsfBaseOnDeinit
#define OnTick   RsfBaseOnTick
#define OnTradeTransaction RsfBaseOnTradeTransaction
#include "..\EA_RegimeStructureFusion\EA_RegimeStructureFusion.mq5"
#undef OnInit
#undef OnDeinit
#undef OnTick
#undef OnTradeTransaction

input group "Forensic replay - diagnostic only"
input string InpForensicCaptureWindows="FROZEN_13_V1"; // immutable window-set identity; dates are hard-bound below
input bool   InpForensicVisualScreenshots=false;        // Diagnostic only; requires alpha.ps1 -Visual
input bool   InpForensicAttachM5Indicators=true;        // Attach MBB/TB/QQE handles to visual chart where MT5 allows it
input int    InpForensicShotWidth=1600;
input int    InpForensicShotHeight=900;

int g_forensic_handle=INVALID_HANDLE;
int g_visual_handle=INVALID_HANDLE;
string g_forensic_name="";
string g_visual_name="";
datetime g_capture_from[];
datetime g_capture_to[];

// Queue screenshot metadata from OnTradeTransaction and render it on a later
// tick.  This lets the visual tester paint the native deal marker and keeps the
// original SL/TP/engine values even after the base EA clears a closed trade.
struct VisualShotEvent
  {
   ulong deal;
   ulong order_id;
   ulong position_id;
   ulong queued_tick;
   datetime event_time;
   ENUM_DEAL_TYPE deal_type;
   string action;
   string case_id;
   string engine_name;
   double price;
   double sl;
   double tp;
  };
VisualShotEvent g_visual_pending[];

// Pre-chart selection copied from the hash-bound selection manifest.  Windows
// still export surrounding telemetry, but PNG evidence is restricted to these
// 14 paired loser/winner positions so nearby trades cannot enter post hoc.
bool LookupFrozenVisualCase(const ulong position_id,string &case_id)
  {
   ulong ids[]={342,424,782,808,500,1052,832,774,456,422,604,780,1222,246};
   string names[]={
      "RSF-C16-BREAKOUT-LONG-L","RSF-C16-BREAKOUT-LONG-W",
      "RSF-C16-BREAKOUT-SHORT-L","RSF-C16-BREAKOUT-SHORT-W",
      "RSF-C16-RANGE-LONG-L","RSF-C16-RANGE-LONG-W",
      "RSF-C16-RANGE-SHORT-L","RSF-C16-RANGE-SHORT-W",
      "RSF-C16-TREND-LONG-L","RSF-C16-TREND-LONG-W",
      "RSF-C16-TREND-SHORT-L","RSF-C16-TREND-SHORT-W",
      "RSF-C16-EXTREME-LOSS","RSF-C16-EXTREME-WIN"};
   for(int i=0;i<ArraySize(ids);i++)
      if(position_id==ids[i])
        {
         case_id=names[i];
         return(true);
        }
   case_id="";
   return(false);
  }

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

bool OpenVisualTelemetry()
  {
   if(!InpForensicVisualScreenshots) return(true);
   g_visual_name=StringFormat("%s_VisualShots_%s.csv",_Symbol,g_run_id);
   g_visual_handle=FileOpen(g_visual_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_visual_handle==INVALID_HANDLE) return(false);
   FileWrite(g_visual_handle,
      "event_time_server","event_time_utc","case_id","action","deal","order","position_id","deal_type",
      "price","sl","tp","engine_name","filename","screenshot_ok","last_error",
      "symbol","timeframe","hypothesis_id","variant_tag","run_id");
   FileFlush(g_visual_handle);
   return(true);
  }

void AttachVisualIndicators()
  {
   if(!InpForensicVisualScreenshots || !InpForensicAttachM5Indicators || !MQLInfoInteger(MQL_VISUAL_MODE)) return;
   ResetLastError();
   ChartSetInteger(0,CHART_SHOW_TRADE_LEVELS,true);
   if(g_mbb!=INVALID_HANDLE) ChartIndicatorAdd(0,0,g_mbb);
   if(g_tb!=INVALID_HANDLE) ChartIndicatorAdd(0,0,g_tb);
   if(g_qqe!=INVALID_HANDLE) ChartIndicatorAdd(0,1,g_qqe);
   ChartRedraw(0);
  }

bool QueueVisualDeal(const ulong deal,const bool after_base)
  {
   if(!InpForensicVisualScreenshots || !MQLInfoInteger(MQL_VISUAL_MODE)) return(false);
   if(!HistoryDealSelect(deal)) return(false);
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) return(false);
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   bool is_open=(entry==DEAL_ENTRY_IN);
   bool is_close=(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY);
   if(!is_open && !is_close) return(false);
   // OPEN needs promoted pending state; CLOSE needs state before final cleanup.
   if(is_open!=after_base) return(false);
   datetime event_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   if(event_time<=0 || !IsCaptureTime(event_time)) return(false);
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   string case_id="";
   if(!LookupFrozenVisualCase(position_id,case_id)) return(false);
   VisualShotEvent item;
   item.deal=deal;
   item.order_id=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
   item.position_id=position_id;
   item.queued_tick=(ulong)g_ticks_seen;
   item.event_time=event_time;
   item.deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   item.action=is_open ? "OPEN" : "CLOSE";
   item.case_id=case_id;
   item.engine_name=SignalName(g_active_signal);
   item.price=HistoryDealGetDouble(deal,DEAL_PRICE);
   item.sl=g_active_sl;
   item.tp=g_active_tp;
   int n=ArraySize(g_visual_pending);
   ArrayResize(g_visual_pending,n+1);
   g_visual_pending[n]=item;
   return(true);
  }

void CaptureQueuedVisualShots(const bool force=false)
  {
   if(!InpForensicVisualScreenshots || !MQLInfoInteger(MQL_VISUAL_MODE)) return;
   int pending=ArraySize(g_visual_pending);
   if(pending<=0) return;
   int keep=0;
   for(int i=0;i<pending;i++)
     {
      VisualShotEvent item=g_visual_pending[i];
      if(!force && (ulong)g_ticks_seen<=item.queued_tick)
        {
         g_visual_pending[keep++]=item;
         continue;
        }
      string filename=StringFormat("RSFV_%s_%I64u_%I64u_%s_M5.png",_Symbol,item.position_id,item.deal,item.action);
      ChartRedraw(0);
      ResetLastError();
      bool ok=ChartScreenShot(0,filename,InpForensicShotWidth,InpForensicShotHeight,ALIGN_RIGHT);
      int err=GetLastError();
      if(g_visual_handle!=INVALID_HANDLE)
        {
         FileWrite(g_visual_handle,
            TimeToString(item.event_time,TIME_DATE|TIME_SECONDS),
            TimeToString(ServerToUtc(item.event_time),TIME_DATE|TIME_SECONDS),item.case_id,item.action,
            StringFormat("%I64u",item.deal),StringFormat("%I64u",item.order_id),StringFormat("%I64u",item.position_id),
            EnumToString(item.deal_type),DoubleToString(item.price,_Digits),DoubleToString(item.sl,_Digits),
            DoubleToString(item.tp,_Digits),item.engine_name,filename,ok ? "1" : "0",IntegerToString(err),
            _Symbol,"M5",InpHypothesisId,InpVariantTag,g_run_id);
         FileFlush(g_visual_handle);
        }
     }
   ArrayResize(g_visual_pending,keep);
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
   if(!OpenVisualTelemetry())
     {
      RsfBaseOnDeinit(REASON_INITFAILED);
      return(INIT_FAILED);
     }
   AttachVisualIndicators();
   return(INIT_SUCCEEDED);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
  {
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0) QueueVisualDeal(trans.deal,false);
   RsfBaseOnTradeTransaction(trans,request,result);
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0) QueueVisualDeal(trans.deal,true);
  }

void OnTick()
  {
   long before=g_closed_bars_seen;
   RsfBaseOnTick();
   if(g_closed_bars_seen>before) ExportClosedBarSnapshot();
   CaptureQueuedVisualShots(false);
  }

void OnDeinit(const int reason)
  {
   CaptureQueuedVisualShots(true);
   if(g_forensic_handle!=INVALID_HANDLE)
     {
      FileFlush(g_forensic_handle);
      FileClose(g_forensic_handle);
      g_forensic_handle=INVALID_HANDLE;
     }
   if(g_visual_handle!=INVALID_HANDLE)
     {
      FileFlush(g_visual_handle);
      FileClose(g_visual_handle);
      g_visual_handle=INVALID_HANDLE;
     }
   RsfBaseOnDeinit(reason);
  }
