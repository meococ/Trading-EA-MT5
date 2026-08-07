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
input bool   InpForensicAttachM5Indicators=true;        // Add display-only MBB/TB/QQE handles; calculation handles stay hidden
input int    InpForensicShotWidth=1600;
input int    InpForensicShotHeight=900;
input int    InpForensicShotVerifyTicks=20;             // Fail closed if PNG is not readable after this many tester ticks
input int    InpForensicShotSettleMs=250;               // Diagnostic-only UI settle time after ChartScreenShot request
input datetime InpForensicSmokeShotTime=0;               // Optional server-time screenshot probe; never enters or changes a trade
input bool   InpForensicCleanChart=true;                 // Display only: suppress TB cells/voids/trail; buffers remain available in CSV
input string InpForensicReferenceCaseId="";              // Frozen case label drawn on the native chart; never used by strategy logic
input int    InpForensicReferenceDirection=0;            // +1 long, -1 short, 0 no reference marker
input double InpForensicReferenceEntry=0.0;              // Frozen original entry price
input double InpForensicReferenceSl=0.0;                 // Frozen original stop price
input double InpForensicReferenceTp=0.0;                 // Frozen original target price
input int    InpForensicExternalCapturePauseMs=0;        // Visual tester only; bounded pause for external native-window capture
input string InpForensicNativeLossSchedule="";           // Also accepts FROZEN_ROLE_AWARE_003_OUTCOMES_V1
input int    InpForensicNativeCaseIndex=0;                // 0 all, 1..8 one frozen reference case (diagnostic only)

int g_forensic_handle=INVALID_HANDLE;
int g_visual_handle=INVALID_HANDLE;
int g_visual_mbb=INVALID_HANDLE;
int g_visual_tb=INVALID_HANDLE;
int g_visual_qqe=INVALID_HANDLE;
string g_forensic_name="";
string g_visual_name="";
bool g_visual_smoke_queued=false;
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
   bool request_issued;
   bool request_ok;
   int request_error;
   ulong issued_tick;
   string filename;
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
       "request_ok","request_error","file_verified","file_size_bytes","verify_ticks","verify_timeout",
       "qqe_probe_mask","qqe_hist","qqe_trend_line","qqe_primary","qqe_secondary","qqe_state",
       "qqe_neutral_mirror","qqe_up_mirror","qqe_down_mirror",
       "symbol","timeframe","hypothesis_id","variant_tag","run_id");
   FileFlush(g_visual_handle);
   return(true);
  }

bool AttachVisualIndicators()
  {
   if(!InpForensicVisualScreenshots || !InpForensicAttachM5Indicators || !MQLInfoInteger(MQL_VISUAL_MODE))
      return(true);

   // The base EA's five iCustom handles are decision inputs.  They are created
   // while TesterHideIndicators(true) is active so MT5 cannot auto-attach them.
   // These three separate handles reuse the exact same engine contracts but
   // disable alerts and use a forensic display profile.  This prevents the
   // duplicated QQE panes and heavy MBB heat-fill observed in VISUAL-002's
   // first native failure screenshot without changing any trading buffer.
   string mbb_contract="RSF1|"+ContractInt(InpMbbLengthMode)+"|"+ContractInt(InpMbbFixedLength)+"|"
            +ContractInt(InpMbbBasisMode)+"|"+ContractInt(InpMbbBandMode)+"|"+ContractDouble(InpMbbStdevMultiplier)+"|"
            +ContractDouble(InpMbbRobustUpperPct)+"|"+ContractDouble(InpMbbRobustLowerPct)+"|"
            +ContractInt(InpMbbRobustWindowMult)+"|"+ContractInt(InpMbbRobustWindowFloor)+"|"
            +ContractInt(InpMbbKamaFast)+"|"+ContractInt(InpMbbKamaSlow)+"|"+ContractInt(InpMbbKerLength)+"|"
            +ContractInt(InpMbbRankLength)+"|"+ContractDouble(InpMbbTrendEnter)+"|"+ContractDouble(InpMbbTrendExit)+"|"
            +ContractDouble(InpMbbSqueezeThreshold)+"|"+ContractInt(InpMbbSqueezeMinBars)+"|"
            +ContractDouble(InpMbbBasisTouchFraction);
   g_visual_mbb=iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\Modern_Bollinger_Bands_GBB",
      mbb_contract,
      "Adaptive length",
      InpMbbLengthMode,InpMbbFixedLength,
      "Basis / bands",
      InpMbbBasisMode,InpMbbBandMode,InpMbbStdevMultiplier,
      InpMbbRobustUpperPct,InpMbbRobustLowerPct,InpMbbRobustWindowMult,InpMbbRobustWindowFloor,
      InpMbbKamaFast,InpMbbKamaSlow,
      "Regime / squeeze",
      InpMbbKerLength,InpMbbRankLength,InpMbbTrendEnter,InpMbbTrendExit,
      InpMbbSqueezeThreshold,InpMbbSqueezeMinBars,
      "Signals",InpMbbBasisTouchFraction,
      "Display",
      true,false,false,false,5,C'61,165,232',C'232,163,61',C'125,220,130',C'220,125,125',
      "Closed-bar alerts",false,false,false,
      "Parity",false,D'2023.01.01 00:00');

   const int visual_cells_kept=1;
   const int visual_voids_kept=1;
   string tb_contract="RSF1|"+ContractInt(TB_PROFILE_EA_CUSTOM)+"|"+ContractInt(InpTbSwingLength)+"|"
            +ContractDouble(InpTbDisplacementAtr)+"|"+ContractInt(visual_cells_kept)+"|"+ContractInt(visual_voids_kept)+"|"
            +ContractDouble(InpTbSweepReclaimAtr)+"|"+ContractDouble(InpTbMinimumVoidAtr)+"|"
            +ContractDouble(InpTbMinimumCellAtr)+"|"+ContractInt(InpTbMaximumCellAgeBars)+"|"
            +ContractInt(InpTbMaximumVoidAgeBars)+"|"+ContractBool(InpTbSweepsRequireLiveSwing)+"|"
            +ContractBool(InpTbRequireBothSwings)+"|"+ContractBool(InpTbEnableStructure)+"|"
            +ContractBool(InpTbEnableCells)+"|"+ContractBool(InpTbEnableVoids)+"|"
            +ContractBool(InpTbEnableSweeps)+"|"+ContractInt(InpTbVoidRetention);
   g_visual_tb=iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\TB_Smart_Money_Concept_2026",
       tb_contract,"EA Engine Contract - iCustom inputs first",
       TB_PROFILE_EA_CUSTOM,InpTbSwingLength,InpTbDisplacementAtr,visual_cells_kept,visual_voids_kept,
      InpTbSweepReclaimAtr,InpTbMinimumVoidAtr,InpTbMinimumCellAtr,InpTbMaximumCellAgeBars,InpTbMaximumVoidAgeBars,
      InpTbSweepsRequireLiveSwing,InpTbRequireBothSwings,InpTbEnableStructure,InpTbEnableCells,InpTbEnableVoids,
      InpTbEnableSweeps,InpTbVoidRetention,
      "TB SMC 2026 - Look",
      C'45,212,191',C'251,113,133',C'129,140,248',C'100,116,139',true,
      "TB SMC 2026 - Map",
      true,!InpForensicCleanChart,!InpForensicCleanChart,true,!InpForensicCleanChart,true,
      "Closed-Bar Alerts",false,false,false);

   // Group headers are positional iCustom parameters too.  Bind the first
   // three groups explicitly; later visual/alert inputs safely keep defaults.
   g_visual_qqe=iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\QQE_MOD",
      "Primary QQE Settings",
      InpQqePrimaryRsiLength,InpQqePrimarySmoothing,InpQqePrimaryFactor,InpQqePrimaryThreshold,InpQqePrimarySource,
      "Secondary QQE Settings",
      InpQqeSecondaryRsiLength,InpQqeSecondarySmoothing,InpQqeSecondaryFactor,InpQqeSecondaryThreshold,
      InpQqeSecondarySource,"Bollinger Bands Settings",InpQqeBollingerLength,InpQqeBollingerMultiplier);

   if(g_visual_mbb==INVALID_HANDLE || g_visual_tb==INVALID_HANDLE || g_visual_qqe==INVALID_HANDLE)
     {
      PrintFormat("RSF forensic display handle failure mbb=%d tb=%d qqe=%d error=%d",
                  g_visual_mbb,g_visual_tb,g_visual_qqe,GetLastError());
      return(false);
     }
   ResetLastError();
   ChartSetInteger(0,CHART_SHOW_TRADE_LEVELS,true);
   bool ok=true;
   if(!ChartIndicatorAdd(0,0,g_visual_mbb)) ok=false;
   if(!ChartIndicatorAdd(0,0,g_visual_tb)) ok=false;
   if(!ChartIndicatorAdd(0,1,g_visual_qqe)) ok=false;
   ChartRedraw(0);
   return(ok);
  }

bool QueueVisualDeal(const ulong deal,const bool after_base)
  {
   if(!InpForensicVisualScreenshots || !MQLInfoInteger(MQL_VISUAL_MODE)) return(false);
   // The scheduled native-loss batch marks immutable original positions by
   // timestamp/price.  Its Model-1 diagnostic trade IDs are unrelated and must
   // never be mistaken for the frozen Model-0 position IDs.
   if(InpForensicNativeLossSchedule!="") return(false);
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
   item.request_issued=false;
   item.request_ok=false;
   item.request_error=0;
   item.issued_tick=0;
   item.filename="";
   int n=ArraySize(g_visual_pending);
   ArrayResize(g_visual_pending,n+1);
   g_visual_pending[n]=item;
   return(true);
  }

void StyleReferenceLevel(const string name,const color line_color,const ENUM_LINE_STYLE style)
  {
   ObjectSetInteger(0,name,OBJPROP_COLOR,line_color);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,name,OBJPROP_BACK,false);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
  }

// Draw the immutable original-trade geometry as native MT5 chart objects.  It
// is intentionally isolated from every order/decision variable and exists only
// so an external screen capture can join price action to the frozen case row.
void DrawReferenceTradeAt(const string case_id,const int direction,
                          const double entry,const double sl,const double tp,
                          const datetime event_time)
  {
   if(case_id=="" || direction==0 || entry<=0.0)
      return;
   string prefix="RSF_REF_"+SafeToken(case_id)+"_";
   string entry_name=prefix+"ENTRY";
   string sl_name=prefix+"SL";
   string tp_name=prefix+"TP";
   string arrow_name=prefix+"ARROW";
   string text_name=prefix+"TEXT";
   ObjectCreate(0,entry_name,OBJ_HLINE,0,event_time,entry);
   StyleReferenceLevel(entry_name,C'80,180,255',STYLE_SOLID);
   if(sl>0.0)
     {
      ObjectCreate(0,sl_name,OBJ_HLINE,0,event_time,sl);
      StyleReferenceLevel(sl_name,C'255,80,100',STYLE_DASH);
     }
   if(tp>0.0)
     {
      ObjectCreate(0,tp_name,OBJ_HLINE,0,event_time,tp);
      StyleReferenceLevel(tp_name,C'80,220,130',STYLE_DASH);
     }
   ENUM_OBJECT arrow_type=(direction>0 ? OBJ_ARROW_BUY : OBJ_ARROW_SELL);
   ObjectCreate(0,arrow_name,arrow_type,0,event_time,entry);
   ObjectSetInteger(0,arrow_name,OBJPROP_COLOR,C'255,215,0');
   ObjectSetInteger(0,arrow_name,OBJPROP_WIDTH,2);
   ObjectSetInteger(0,arrow_name,OBJPROP_SELECTABLE,false);
   ObjectCreate(0,text_name,OBJ_TEXT,0,event_time,entry);
   ObjectSetString(0,text_name,OBJPROP_TEXT,case_id+"  ENTRY / SL / TP");
   ObjectSetInteger(0,text_name,OBJPROP_COLOR,C'255,255,255');
   ObjectSetInteger(0,text_name,OBJPROP_FONTSIZE,9);
   ObjectSetInteger(0,text_name,OBJPROP_ANCHOR,ANCHOR_LEFT_LOWER);
   ObjectSetInteger(0,text_name,OBJPROP_SELECTABLE,false);
   ChartRedraw(0);
  }

void DrawReferenceTrade(const datetime event_time)
  {
   DrawReferenceTradeAt(InpForensicReferenceCaseId,InpForensicReferenceDirection,
                        InpForensicReferenceEntry,InpForensicReferenceSl,
                        InpForensicReferenceTp,event_time);
  }

// Outcome evidence must show where the frozen losing trade actually closed.
// This marker is display-only and is never read by the base strategy.
void DrawReferenceExitAt(const string case_id,const int direction,
                         const double exit_price,const double net_r,
                         const datetime exit_time)
  {
   if(case_id=="" || direction==0 || exit_price<=0.0 || exit_time<=0)
      return;
   string prefix="RSF_REF_"+SafeToken(case_id)+"_";
   string arrow_name=prefix+"EXIT_ARROW";
   string text_name=prefix+"EXIT_TEXT";
   ENUM_OBJECT arrow_type=(direction>0 ? OBJ_ARROW_SELL : OBJ_ARROW_BUY);
   ObjectCreate(0,arrow_name,arrow_type,0,exit_time,exit_price);
   ObjectSetInteger(0,arrow_name,OBJPROP_COLOR,C'255,80,100');
   ObjectSetInteger(0,arrow_name,OBJPROP_WIDTH,3);
   ObjectSetInteger(0,arrow_name,OBJPROP_SELECTABLE,false);
   ObjectCreate(0,text_name,OBJ_TEXT,0,exit_time,exit_price);
   ObjectSetString(0,text_name,OBJPROP_TEXT,
                   case_id+"  EXIT "+DoubleToString(net_r,2)+"R");
   ObjectSetInteger(0,text_name,OBJPROP_COLOR,C'255,130,140');
   ObjectSetInteger(0,text_name,OBJPROP_FONTSIZE,9);
   ObjectSetInteger(0,text_name,OBJPROP_ANCHOR,ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0,text_name,OBJPROP_SELECTABLE,false);
  }

void DeleteReferenceTrade(const string case_id)
  {
   string prefix="RSF_REF_"+SafeToken(case_id)+"_";
   ObjectDelete(0,prefix+"ENTRY");
   ObjectDelete(0,prefix+"SL");
   ObjectDelete(0,prefix+"TP");
   ObjectDelete(0,prefix+"ARROW");
   ObjectDelete(0,prefix+"TEXT");
   ObjectDelete(0,prefix+"EXIT_ARROW");
   ObjectDelete(0,prefix+"EXIT_TEXT");
  }

void QueueReferenceVisualEvent(const string case_id,const datetime event_time,
                               const int direction,const double entry,
                               const double sl,const double tp,
                               const string action="REFERENCE_ENTRY",
                               const double observed_price=0.0)
  {
   VisualShotEvent item;
   item.deal=0;
   item.order_id=0;
   item.position_id=0;
   item.queued_tick=(ulong)g_ticks_seen;
   item.event_time=event_time;
   item.deal_type=(direction>0 ? DEAL_TYPE_BUY : DEAL_TYPE_SELL);
   item.action=action;
   item.case_id=case_id;
   item.engine_name="FROZEN_ORIGINAL_CASE";
   item.price=(observed_price>0.0 ? observed_price : entry);
   item.sl=sl;
   item.tp=tp;
   item.request_issued=false;
   item.request_ok=false;
   item.request_error=0;
   item.issued_tick=0;
   item.filename="";
   int n=ArraySize(g_visual_pending);
   ArrayResize(g_visual_pending,n+1);
   g_visual_pending[n]=item;
  }

void WriteNativeCaptureFlag(const string case_id,const datetime event_time)
  {
   int handle=FileOpen("RSF_NATIVE_CAPTURE.flag",FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE) return;
   FileWriteString(handle,case_id+"|"+TimeToString(event_time,TIME_DATE|TIME_SECONDS));
   FileFlush(handle);
   FileClose(handle);
  }

// The seven loser timestamps/prices were frozen before this native replay.
// Model-1 is permitted only for visual indicator/price anatomy; no execution or
// economic metric from the batch can be consumed.  A flag in the tester agent
// sandbox lets the external capture lane join each actual MT5 window to its ID.
void ProcessNativeLossSchedule()
  {
   const bool entry_mode=(InpForensicNativeLossSchedule=="FROZEN_7_LOSERS_V1");
   const bool outcome_mode=(InpForensicNativeLossSchedule=="FROZEN_7_LOSER_OUTCOMES_V1");
   if((!entry_mode && !outcome_mode) ||
      !InpForensicVisualScreenshots || !MQLInfoInteger(MQL_VISUAL_MODE))
      return;
   datetime entry_times[]={D'2019.06.04 09:55',D'2019.10.09 11:20',D'2019.11.29 11:05',
                           D'2020.04.20 15:05',D'2020.10.16 09:25',D'2020.12.16 10:25',
                           D'2022.06.13 10:00'};
   datetime exit_times[]={D'2019.06.04 09:59:59',D'2019.10.09 13:52:31',D'2019.11.29 11:36:27',
                          D'2020.04.20 17:06:40',D'2020.10.16 09:59:15',D'2020.12.16 10:30:12',
                          D'2022.06.13 10:00:42'};
   string ids[]={"RSF-C16-BREAKOUT-LONG-L","RSF-C16-TREND-LONG-L","RSF-C16-RANGE-LONG-L",
                 "RSF-C16-TREND-SHORT-L","RSF-C16-BREAKOUT-SHORT-L","RSF-C16-RANGE-SHORT-L",
                 "RSF-C16-EXTREME-LOSS"};
   int directions[]={1,1,1,-1,-1,-1,-1};
   double entries[]={1.12696,1.09892,1.10081,1.08519,1.16972,1.21654,1.04701};
   double exits[]={1.12638,1.09760,1.10046,1.08712,1.17022,1.21735,1.04813};
   double stops[]={1.12639,1.09760,1.10046,1.08710,1.17022,1.21734,1.04796};
   double targets[]={1.12781,1.10090,1.10133,1.08232,1.16898,1.21534,1.04559};
   double net_rs[]={-1.08771930,-1.03030303,-1.11428571,-1.03141361,-1.08000000,-1.06250000,-1.22105263};
   static bool captured[7]={false,false,false,false,false,false,false};
   for(int i=0;i<7;i++)
     {
      if(InpForensicNativeCaseIndex>0 && i!=(InpForensicNativeCaseIndex-1))
         continue;
      // One completed M5 bar after exit makes the failure path visible while
      // keeping every frozen price and timestamp independent of this replay.
      datetime capture_time=(outcome_mode ? exit_times[i]+PeriodSeconds(PERIOD_M5) : entry_times[i]);
      if(captured[i] || TimeCurrent()<capture_time) continue;
      captured[i]=true;
      DrawReferenceTradeAt(ids[i],directions[i],entries[i],stops[i],targets[i],entry_times[i]);
      if(outcome_mode)
         DrawReferenceExitAt(ids[i],directions[i],exits[i],net_rs[i],exit_times[i]);

      // The former lane omitted this navigation, so genuine native screenshots
      // could end 25-100 minutes before the frozen entry. Keep the current bar
      // at the right edge and use a wide scale before either capture mechanism.
      ChartSetInteger(0,CHART_AUTOSCROLL,true);
      // Outcome evidence needs the newest completed bar at the right edge. A
      // shifted chart wastes capture width and can hide the price path.
      ChartSetInteger(0,CHART_SHIFT,false);
      ChartSetInteger(0,CHART_SCALE,1);
      ChartNavigate(0,CHART_END,0);
      ChartRedraw(0);

      QueueReferenceVisualEvent(ids[i],outcome_mode ? exit_times[i] : entry_times[i],
                                directions[i],entries[i],stops[i],targets[i],
                                outcome_mode ? "REFERENCE_OUTCOME" : "REFERENCE_ENTRY",
                                outcome_mode ? exits[i] : entries[i]);
      // ChartScreenShot is asynchronous. The wrapper's normal end-of-OnTick
      // path will keep this event pending on the queue, issue on a later tick,
      // and verify only after the file is readable.
      WriteNativeCaptureFlag(ids[i],capture_time);
      ChartRedraw(0);
      // Sleep() is intentionally not used here: Strategy Tester may advance it
      // in simulated time, making the flag disappear before an external native
      // window capture can observe it.  GetMicrosecondCount() is a wall-clock
      // monotonic counter, so this bounded spin keeps the real MT5 chart and
      // flag stable for the exact operator-controlled capture interval.
      if(InpForensicExternalCapturePauseMs>0)
        {
         const ulong wait_us=(ulong)InpForensicExternalCapturePauseMs*1000ULL;
         const ulong started_us=GetMicrosecondCount();
         uint spins=0;
         while(!IsStopped() && GetMicrosecondCount()-started_us<wait_us)
           {
            // Periodic redraw keeps native objects responsive without changing
            // prices, indicator buffers, bar timing, or trading decisions.
            spins++;
            if((spins%100000U)==0U) ChartRedraw(0);
           }
        }
      FileDelete("RSF_NATIVE_CAPTURE.flag");
      // Keep the frozen objects until the asynchronous screenshot has been
      // requested and verified on subsequent ticks. Each short replay selects
      // one case, so retained objects are bounded and removed with the chart.
      ChartRedraw(0);
      break;
     }
  }

// Paired worst-loss / best-win cases for every route that actually executed in
// ROLE-AWARE-003. Selection is frozen in the source run's lifecycle CSV and is
// diagnostic only: this replay cannot create, remove or evaluate a trade.
void ProcessRoleAware003VisualSchedule()
  {
   if(InpForensicNativeLossSchedule!="FROZEN_ROLE_AWARE_003_OUTCOMES_V1" ||
      !InpForensicVisualScreenshots || !MQLInfoInteger(MQL_VISUAL_MODE))
      return;

   datetime entry_times[]={D'2018.04.23 10:20',D'2020.12.17 15:20',
                           D'2020.06.04 09:45',D'2020.05.11 11:10',
                           D'2019.01.11 13:45',D'2018.05.30 11:55',
                           D'2019.07.25 12:05',D'2018.02.05 15:45'};
   datetime exit_times[]={D'2018.04.23 10:23:31',D'2020.12.17 15:29:39',
                          D'2020.06.04 09:59:05',D'2020.05.11 11:16:37',
                          D'2019.01.11 14:52:40',D'2018.05.30 14:09:05',
                          D'2019.07.25 13:15:27',D'2018.02.05 16:11:03'};
   string ids[]={"RA003-C01-BREAKOUT-LONG-LOSS","RA003-C02-BREAKOUT-LONG-WIN",
                 "RA003-C03-BREAKOUT-SHORT-LOSS","RA003-C04-BREAKOUT-SHORT-WIN",
                 "RA003-C05-TREND-LONG-LOSS","RA003-C06-TREND-LONG-WIN",
                 "RA003-C07-TREND-SHORT-LOSS","RA003-C08-TREND-SHORT-WIN"};
   int directions[]={1,1,-1,-1,1,1,-1,-1};
   double entries[]={1.22826,1.22458,1.12056,1.08341,1.15290,1.15973,1.11281,1.24426};
   double exits[]={1.22753,1.22561,1.12115,1.08242,1.15218,1.16397,1.11349,1.24109};
   double stops[]={1.22757,1.22390,1.12114,1.08407,1.15223,1.15691,1.11349,1.24636};
   double targets[]={1.22929,1.22560,1.11970,1.08242,1.15390,1.16396,1.11179,1.24110};
   double net_rs[]={-1.11594203,1.45588235,-1.08620690,1.43939394,
                    -1.13432836,1.48936170,-1.05882353,1.49047619};
   static bool captured[8]={false,false,false,false,false,false,false,false};

   for(int i=0;i<8;i++)
     {
      if(InpForensicNativeCaseIndex>0 && i!=(InpForensicNativeCaseIndex-1))
         continue;
      datetime capture_time=exit_times[i]+PeriodSeconds(PERIOD_M5);
      if(captured[i] || TimeCurrent()<capture_time) continue;
      captured[i]=true;

      DrawReferenceTradeAt(ids[i],directions[i],entries[i],stops[i],targets[i],entry_times[i]);
      DrawReferenceExitAt(ids[i],directions[i],exits[i],net_rs[i],exit_times[i]);
      ChartSetInteger(0,CHART_AUTOSCROLL,true);
      ChartSetInteger(0,CHART_SHIFT,false);
      ChartSetInteger(0,CHART_SCALE,1);
      ChartNavigate(0,CHART_END,0);
      ChartRedraw(0);
      QueueReferenceVisualEvent(ids[i],exit_times[i],directions[i],entries[i],stops[i],targets[i],
                                "REFERENCE_OUTCOME",exits[i]);
      WriteNativeCaptureFlag(ids[i],capture_time);
      ChartRedraw(0);
      if(InpForensicExternalCapturePauseMs>0)
        {
         const ulong wait_us=(ulong)InpForensicExternalCapturePauseMs*1000ULL;
         const ulong started_us=GetMicrosecondCount();
         uint spins=0;
         while(!IsStopped() && GetMicrosecondCount()-started_us<wait_us)
           {
            spins++;
            if((spins%100000U)==0U) ChartRedraw(0);
           }
        }
      FileDelete("RSF_NATIVE_CAPTURE.flag");
      ChartRedraw(0);
      break;
     }
  }

// Symmetric worst/best achieved-R pair for each route in the terminal
// STRUCTURAL-EVENT-004 development run.  Selection excludes risk-account
// values below 10 so the broker money-stopout floor cannot choose the charts.
// These reference drawings are diagnostic only and never affect the included
// strategy source, orders, stops, targets or economic verdict.
void ProcessStructuralEvent004VisualSchedule()
  {
   if(InpForensicNativeLossSchedule!="FROZEN_STRUCTURAL_EVENT_004_OUTCOMES_V1" ||
      !InpForensicVisualScreenshots || !MQLInfoInteger(MQL_VISUAL_MODE))
      return;

   datetime entry_times[]={D'2019.05.07 13:20',D'2018.10.16 09:55',
                           D'2018.01.04 10:10',D'2018.06.05 13:40',
                           D'2018.07.26 15:45',D'2018.03.06 12:55',
                           D'2019.09.24 09:25',D'2019.03.28 12:45'};
   datetime exit_times[]={D'2019.05.07 14:51:17',D'2018.10.16 10:27:42',
                          D'2018.01.04 11:49:20',D'2018.06.05 15:10:43',
                          D'2018.07.26 15:55:21',D'2018.03.06 13:23:43',
                          D'2019.09.24 09:31:14',D'2019.03.28 13:27:41'};
   string ids[]={"SE004-C01-BREAKOUT-LONG-LOSS","SE004-C02-BREAKOUT-LONG-WIN",
                 "SE004-C03-BREAKOUT-SHORT-LOSS","SE004-C04-BREAKOUT-SHORT-WIN",
                 "SE004-C05-TREND-LONG-LOSS","SE004-C06-TREND-LONG-WIN",
                 "SE004-C07-TREND-SHORT-LOSS","SE004-C08-TREND-SHORT-WIN"};
   int directions[]={1,1,-1,-1,1,1,-1,-1};
   double entries[]={1.12027,1.15781,1.20235,1.16912,1.17192,1.23469,1.09876,1.12489};
   double exits[]={1.11914,1.15946,1.20393,1.16718,1.16983,1.23719,1.09911,1.12335};
   double stops[]={1.11923,1.15674,1.20380,1.17037,1.16999,1.23315,1.09911,1.12589};
   double targets[]={1.12183,1.15942,1.20017,1.16724,1.17481,1.23700,1.09824,1.12339};
   double net_rs[]={-1.12500000,1.50467290,-1.11724138,1.52000000,
                    -1.10362694,1.59740260,-1.11428571,1.50000000};
   static bool captured[8]={false,false,false,false,false,false,false,false};

   for(int i=0;i<8;i++)
     {
      if(InpForensicNativeCaseIndex>0 && i!=(InpForensicNativeCaseIndex-1))
         continue;
      datetime capture_time=exit_times[i]+PeriodSeconds(PERIOD_M5);
      if(captured[i] || TimeCurrent()<capture_time) continue;
      captured[i]=true;

      DrawReferenceTradeAt(ids[i],directions[i],entries[i],stops[i],targets[i],entry_times[i]);
      DrawReferenceExitAt(ids[i],directions[i],exits[i],net_rs[i],exit_times[i]);
      ChartSetInteger(0,CHART_AUTOSCROLL,true);
      ChartSetInteger(0,CHART_SHIFT,false);
      ChartSetInteger(0,CHART_SCALE,1);
      ChartNavigate(0,CHART_END,0);
      ChartRedraw(0);
      QueueReferenceVisualEvent(ids[i],exit_times[i],directions[i],entries[i],stops[i],targets[i],
                                "REFERENCE_OUTCOME",exits[i]);
      WriteNativeCaptureFlag(ids[i],capture_time);
      ChartRedraw(0);
      if(InpForensicExternalCapturePauseMs>0)
        {
         const ulong wait_us=(ulong)InpForensicExternalCapturePauseMs*1000ULL;
         const ulong started_us=GetMicrosecondCount();
         uint spins=0;
         while(!IsStopped() && GetMicrosecondCount()-started_us<wait_us)
           {
            spins++;
            if((spins%100000U)==0U) ChartRedraw(0);
           }
        }
      FileDelete("RSF_NATIVE_CAPTURE.flag");
      ChartRedraw(0);
      break;
     }
  }

void QueueVisualSmokeIfDue()
  {
   if(g_visual_smoke_queued || InpForensicSmokeShotTime<=0 ||
      !InpForensicVisualScreenshots || !MQLInfoInteger(MQL_VISUAL_MODE) ||
      TimeCurrent()<InpForensicSmokeShotTime)
      return;

   VisualShotEvent item;
   item.deal=0;
   item.order_id=0;
   item.position_id=0;
   item.queued_tick=(ulong)g_ticks_seen;
   item.event_time=TimeCurrent();
   item.deal_type=DEAL_TYPE_BUY;
   item.action="SMOKE";
   item.case_id="VISUAL-SCREENSHOT-SMOKE";
   item.engine_name="DISPLAY_ONLY";
   item.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   item.sl=0.0;
   item.tp=0.0;
   item.request_issued=false;
   item.request_ok=false;
   item.request_error=0;
   item.issued_tick=0;
   item.filename="";
   int n=ArraySize(g_visual_pending);
   ArrayResize(g_visual_pending,n+1);
   g_visual_pending[n]=item;
   g_visual_smoke_queued=true;
   DrawReferenceTrade(InpForensicSmokeShotTime);
   if(InpForensicExternalCapturePauseMs>0)
     {
      ChartRedraw(0);
      Sleep(InpForensicExternalCapturePauseMs);
     }
  }

long VisualFileSize(const string filename)
  {
   if(!FileIsExist(filename)) return(0);
   ResetLastError();
   int handle=FileOpen(filename,FILE_READ|FILE_BIN|FILE_SHARE_READ);
   if(handle==INVALID_HANDLE) return(0);
   ulong size=FileSize(handle);
   FileClose(handle);
   return((long)size);
  }

// Probe the exact display handle, not the parent EA's decision handle.  The
// closed bar (shift 1) makes the diagnostic deterministic and non-repainting.
// A bit mask written beside the values distinguishes a legitimate zero from a
// failed CopyBuffer call or EMPTY_VALUE during indicator warm-up.
bool ReadVisualQqeBuffer(const int buffer,double &value)
  {
   value=0.0;
   if(g_visual_qqe==INVALID_HANDLE) return(false);
   double data[1];
   ResetLastError();
   if(CopyBuffer(g_visual_qqe,buffer,1,1,data)!=1) return(false);
   if(!MathIsValidNumber(data[0]) || data[0]==EMPTY_VALUE) return(false);
   value=data[0];
   return(true);
  }

void WriteVisualShotResult(const VisualShotEvent &item,const bool file_verified,
                           const long file_size,const int verify_ticks,const bool verify_timeout)
  {
   if(g_visual_handle==INVALID_HANDLE) return;
   double qqe_hist=0.0,qqe_trend=0.0,qqe_primary=0.0,qqe_secondary=0.0,qqe_state=0.0;
   double qqe_neutral=0.0,qqe_up=0.0,qqe_down=0.0;
   int qqe_probe_mask=0;
   if(ReadVisualQqeBuffer(0,qqe_hist))       qqe_probe_mask|=1;
   if(ReadVisualQqeBuffer(2,qqe_trend))      qqe_probe_mask|=2;
   if(ReadVisualQqeBuffer(3,qqe_primary))    qqe_probe_mask|=4;
   if(ReadVisualQqeBuffer(4,qqe_secondary))  qqe_probe_mask|=8;
   if(ReadVisualQqeBuffer(8,qqe_state))      qqe_probe_mask|=16;
   if(ReadVisualQqeBuffer(10,qqe_neutral))   qqe_probe_mask|=32;
   if(ReadVisualQqeBuffer(11,qqe_up))        qqe_probe_mask|=64;
   if(ReadVisualQqeBuffer(12,qqe_down))      qqe_probe_mask|=128;
   FileWrite(g_visual_handle,
      TimeToString(item.event_time,TIME_DATE|TIME_SECONDS),
      TimeToString(ServerToUtc(item.event_time),TIME_DATE|TIME_SECONDS),item.case_id,item.action,
      StringFormat("%I64u",item.deal),StringFormat("%I64u",item.order_id),StringFormat("%I64u",item.position_id),
      EnumToString(item.deal_type),DoubleToString(item.price,_Digits),DoubleToString(item.sl,_Digits),
      DoubleToString(item.tp,_Digits),item.engine_name,item.filename,file_verified ? "1" : "0",
      IntegerToString(item.request_error),item.request_ok ? "1" : "0",IntegerToString(item.request_error),
      file_verified ? "1" : "0",StringFormat("%I64d",file_size),IntegerToString(verify_ticks),
      verify_timeout ? "1" : "0",IntegerToString(qqe_probe_mask),
      DoubleToString(qqe_hist,8),DoubleToString(qqe_trend,8),DoubleToString(qqe_primary,8),
      DoubleToString(qqe_secondary,8),DoubleToString(qqe_state,0),DoubleToString(qqe_neutral,8),
      DoubleToString(qqe_up,8),DoubleToString(qqe_down,8),
      _Symbol,"M5",InpHypothesisId,InpVariantTag,g_run_id);
   FileFlush(g_visual_handle);
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
       if(!item.request_issued && !force && (ulong)g_ticks_seen<=item.queued_tick)
         {
          g_visual_pending[keep++]=item;
          continue;
         }

       if(!item.request_issued)
         {
          item.filename=StringFormat("RSFV_%s_%s_%I64u_%I64u_%s_M5.png",_Symbol,
                                     SafeToken(item.case_id),item.position_id,item.deal,item.action);
          ChartRedraw(0);
          ResetLastError();
          item.request_ok=ChartScreenShot(0,item.filename,InpForensicShotWidth,InpForensicShotHeight,ALIGN_RIGHT);
          item.request_error=GetLastError();
          item.request_issued=true;
          item.issued_tick=(ulong)g_ticks_seen;
          if(item.request_ok && InpForensicShotSettleMs>0)
            {
             Sleep(InpForensicShotSettleMs);
             ChartRedraw(0);
            }
         }

       long file_size=VisualFileSize(item.filename);
       bool file_verified=(item.request_ok && file_size>0);
       int verify_ticks=(int)((ulong)g_ticks_seen-item.issued_tick);
       bool verify_timeout=(force || !item.request_ok || verify_ticks>=InpForensicShotVerifyTicks);
       if(!file_verified && !verify_timeout)
         {
          g_visual_pending[keep++]=item;
          continue;
         }
       WriteVisualShotResult(item,file_verified,file_size,verify_ticks,verify_timeout);
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
   if(InpForensicShotWidth<320 || InpForensicShotHeight<240 ||
      InpForensicShotVerifyTicks<1 || InpForensicShotVerifyTicks>100000 ||
      InpForensicShotSettleMs<0 || InpForensicShotSettleMs>5000 ||
      InpForensicExternalCapturePauseMs<0 || InpForensicExternalCapturePauseMs>30000 ||
      InpForensicNativeCaseIndex<0 || InpForensicNativeCaseIndex>8 ||
      InpForensicReferenceDirection<-1 || InpForensicReferenceDirection>1)
      return(INIT_PARAMETERS_INCORRECT);
   if(InpForensicNativeLossSchedule!="" &&
      InpForensicNativeLossSchedule!="FROZEN_7_LOSERS_V1" &&
       InpForensicNativeLossSchedule!="FROZEN_7_LOSER_OUTCOMES_V1" &&
       InpForensicNativeLossSchedule!="FROZEN_ROLE_AWARE_003_OUTCOMES_V1" &&
       InpForensicNativeLossSchedule!="FROZEN_STRUCTURAL_EVENT_004_OUTCOMES_V1")
      return(INIT_PARAMETERS_INCORRECT);
   if(!ParseCaptureWindows())
     {
      Print("RSF forensic replay requires frozen capture windows.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   bool native_visual=(InpForensicVisualScreenshots && MQLInfoInteger(MQL_VISUAL_MODE));
   if(native_visual) TesterHideIndicators(true);
   int result=RsfBaseOnInit();
   if(result!=INIT_SUCCEEDED)
     {
      if(native_visual) TesterHideIndicators(false);
      return(result);
     }
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
   if(!AttachVisualIndicators())
     {
      if(native_visual) TesterHideIndicators(false);
      RsfBaseOnDeinit(REASON_INITFAILED);
      return(INIT_FAILED);
     }
   if(native_visual) TesterHideIndicators(false);
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
   QueueVisualSmokeIfDue();
    ProcessNativeLossSchedule();
    ProcessRoleAware003VisualSchedule();
    ProcessStructuralEvent004VisualSchedule();
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
   if(g_visual_mbb!=INVALID_HANDLE) { IndicatorRelease(g_visual_mbb); g_visual_mbb=INVALID_HANDLE; }
   if(g_visual_tb!=INVALID_HANDLE)  { IndicatorRelease(g_visual_tb);  g_visual_tb=INVALID_HANDLE; }
   if(g_visual_qqe!=INVALID_HANDLE) { IndicatorRelease(g_visual_qqe); g_visual_qqe=INVALID_HANDLE; }
   RsfBaseOnDeinit(reason);
  }
