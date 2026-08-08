//+------------------------------------------------------------------+
//|                                    EA_FiveIndicatorAtomicV2.mq5  |
//| FIV2 Stage-0 zero-trade census / later atomic engines.           |
//| Campaign: FIV2-20260808-ATOMIC                                   |
//|                                                                  |
//| Authority: research-only. No economic claims from this binary    |
//| until a frozen Stage-0 PASS and subsequent prereg say otherwise. |
//| Closed-bar only. Fail-closed. No majority vote.                  |
//+------------------------------------------------------------------+
#property copyright "Workspace owner / Lead Quant FIV2"
#property version   "1.001"
#property strict
#property description "FIV2 atomic five-indicator Stage-0 zero-trade census"
#property tester_indicator "AlphaFactory\\AI_Regime_Detection.ex5"
#property tester_indicator "AlphaFactory\\Volatility_Regime_Classifier_QuantRegime.ex5"
#property tester_indicator "AlphaFactory\\Modern_Bollinger_Bands_GBB.ex5"
#property tester_indicator "AlphaFactory\\TB_Smart_Money_Concept_2026.ex5"
#property tester_indicator "AlphaFactory\\QQE_MOD.ex5"

#include <Trade\Trade.mqh>

//--- Research identity (fail-closed)
input group "Research identity"
input string   InpHypothesisId      = "UNREGISTERED_BUILD_ONLY"; // Must match frozen Stage-0 ID
input string   InpVariantTag        = "FIV2-STAGE0-R";           // Variant tag
input string   InpExpectedSymbol    = "EURUSD";                  // Expected symbol
input bool     InpResearchAutoMode  = false;                     // Must stay false unless task packet
input bool     InpEnableTelemetry   = true;                      // Required
input bool     InpAllowTrading      = false;                     // Stage-0 MUST be false

//--- Census window (server time)
input group "Stage-0 census window"
input datetime InpCensusFrom        = D'2016.01.01 00:00';        // DESIGN start
input datetime InpCensusTo          = D'2021.06.30 23:59';        // DESIGN end
input int      InpCensusFlushEvery  = 512;                       // Flush every N rows
input int      InpTbLookbackBars    = 3;                         // TB sweep window for ENGINE_R
input double   InpAirdConfFloor     = 0.45;                      // AIRD confidence floor
input double   InpQqeExtremeAbs     = 15.0;                      // |primary RSI| extreme threshold

//--- Handles
int g_aird = INVALID_HANDLE;
int g_vrc  = INVALID_HANDLE;
int g_mbb  = INVALID_HANDLE;
int g_tb   = INVALID_HANDLE;
int g_qqe  = INVALID_HANDLE;

datetime g_last_bar_time = 0;
long     g_closed_bars   = 0;
long     g_rows          = 0;
long     g_ready_rows    = 0;
long     g_raw_r_long    = 0;
long     g_raw_r_short   = 0;
long     g_snapshot_fail = 0;
int      g_file          = INVALID_HANDLE;
string   g_file_name     = "";
string   g_run_id        = "";

//+------------------------------------------------------------------+
bool IsFinite(const double v)
  {
   return(MathIsValidNumber(v) && v!=EMPTY_VALUE);
  }

//+------------------------------------------------------------------+
bool Copy1(const int handle,const int buf,double &out_value)
  {
   double a[];
   if(handle==INVALID_HANDLE) return(false);
   if(CopyBuffer(handle,buf,1,1,a)!=1) return(false);
   out_value=a[0];
   return(true);
  }

//+------------------------------------------------------------------+
bool Copy2(const int handle,const int buf,double &cur,double &prev)
  {
   double a[];
   if(handle==INVALID_HANDLE) return(false);
   if(CopyBuffer(handle,buf,1,2,a)!=2) return(false);
   // series: index 0 = shift1 (current closed), index 1 = shift2
   cur=a[0];
   prev=a[1];
   return(true);
  }

//+------------------------------------------------------------------+
int CreateHandles()
  {
   // Empty EA contract string => indicator chart defaults (documented in contracts).
   g_aird=iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\AI_Regime_Detection","");
   g_vrc =iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\Volatility_Regime_Classifier_QuantRegime","");
   g_mbb =iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\Modern_Bollinger_Bands_GBB","");
   // TB: profile TV defaults first positional surface via empty contract if supported;
   // fall back to explicit TV profile 0 through EA custom path is not used here.
   g_tb  =iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\TB_Smart_Money_Concept_2026","");
   // QQE requires group labels in the positional ABI.
   g_qqe =iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\QQE_MOD",
                  "Primary QQE Settings",
                  6,5,3.0,3.0,PRICE_CLOSE,
                  "Secondary QQE Settings",
                  6,5,1.61,3.0,PRICE_CLOSE,
                  "Bollinger Bands Settings",
                  50,0.35);
   if(g_aird==INVALID_HANDLE || g_vrc==INVALID_HANDLE || g_mbb==INVALID_HANDLE ||
      g_tb==INVALID_HANDLE || g_qqe==INVALID_HANDLE)
     {
      PrintFormat("FIV2 handle fail aird=%d vrc=%d mbb=%d tb=%d qqe=%d err=%d",
                  g_aird,g_vrc,g_mbb,g_tb,g_qqe,GetLastError());
      return(INIT_FAILED);
     }
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void ReleaseHandles()
  {
   if(g_aird!=INVALID_HANDLE) { IndicatorRelease(g_aird); g_aird=INVALID_HANDLE; }
   if(g_vrc!=INVALID_HANDLE)  { IndicatorRelease(g_vrc);  g_vrc=INVALID_HANDLE; }
   if(g_mbb!=INVALID_HANDLE)  { IndicatorRelease(g_mbb);  g_mbb=INVALID_HANDLE; }
   if(g_tb!=INVALID_HANDLE)   { IndicatorRelease(g_tb);   g_tb=INVALID_HANDLE; }
   if(g_qqe!=INVALID_HANDLE)  { IndicatorRelease(g_qqe);  g_qqe=INVALID_HANDLE; }
  }

//+------------------------------------------------------------------+
bool OpenCensusFile()
  {
   g_run_id=StringFormat("FIV2_%s_%I64d",_Symbol,TimeCurrent());
   g_file_name=StringFormat("%s_FIV2_Stage0_%s.csv",_Symbol,g_run_id);
   g_file=FileOpen(g_file_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_file==INVALID_HANDLE) return(false);
   FileWrite(g_file,
      "bar_time_server","open","high","low","close","spread_points",
      "aird_valid","aird_regime","aird_conf","p_bull","p_bear","p_range","p_highvol",
      "vrc_valid","vrc_regime","vrc_dir","vrc_atr_pct","vrc_high_vol","vrc_low_vol",
      "mbb_basis","mbb_upper","mbb_lower","mbb_regime","mbb_squeeze","mbb_release",
      "s1_long","s1_short","s2_long","s2_short","s3_long","s3_short","mbb_priority",
      "tb_ready","tb_bias","tb_atr","tb_struct","tb_sweep_h","tb_sweep_l",
      "tb_disp_up","tb_disp_dn","tb_contract_ver",
      "qqe_primary","qqe_state","qqe_cross",
      "ready_all","engine_r_long","engine_r_short","engine_t_long","engine_t_short",
      "engine_b_long","engine_b_short","hypothesis_id","variant_tag","run_id");
   FileFlush(g_file);
   return(true);
  }

//+------------------------------------------------------------------+
struct Fiv2Snap
  {
   bool   ready;
   // AIRD
   double aird_valid,aird_regime,aird_conf,p_bull,p_bear,p_range,p_highvol;
   // VRC
   double vrc_valid,vrc_regime,vrc_dir,vrc_atr_pct,vrc_high,vrc_low;
   // MBB
   double mbb_basis,mbb_upper,mbb_lower,mbb_regime,mbb_squeeze,mbb_release;
   double s1l,s1s,s2l,s2s,s3l,s3s,mbb_priority;
   // TB
   double tb_ready,tb_bias,tb_atr,tb_struct,tb_sh,tb_sl,tb_du,tb_dd,tb_ver;
   // QQE
   double qqe_primary,qqe_state,qqe_cross;
   // Engine raw flags
   int    r_long,r_short,t_long,t_short,b_long,b_short;
  };

//+------------------------------------------------------------------+
bool ReadSnap(Fiv2Snap &s)
  {
   ZeroMemory(s);
   s.ready=false;
   // AIRD buffers: 11 valid, 12 regime, 5 conf, 7..10 probs
   if(!Copy1(g_aird,11,s.aird_valid)) return(false);
   if(!Copy1(g_aird,12,s.aird_regime)) return(false);
   if(!Copy1(g_aird,5,s.aird_conf)) return(false);
   if(!Copy1(g_aird,7,s.p_bull)) return(false);
   if(!Copy1(g_aird,8,s.p_bear)) return(false);
   if(!Copy1(g_aird,9,s.p_range)) return(false);
   if(!Copy1(g_aird,10,s.p_highvol)) return(false);
   // VRC: 31 valid, 23 regime, 22 dir, 19 atr pct, 26/27 high/low vol
   if(!Copy1(g_vrc,31,s.vrc_valid)) return(false);
   if(!Copy1(g_vrc,23,s.vrc_regime)) return(false);
   if(!Copy1(g_vrc,22,s.vrc_dir)) return(false);
   if(!Copy1(g_vrc,19,s.vrc_atr_pct)) return(false);
   if(!Copy1(g_vrc,26,s.vrc_high)) return(false);
   if(!Copy1(g_vrc,27,s.vrc_low)) return(false);
   // MBB: 7 basis, 3 upper, 5 lower, 20 regime, 22 squeeze, 24 release,
   // 25..30 S flags, 31 priority
   if(!Copy1(g_mbb,7,s.mbb_basis)) return(false);
   if(!Copy1(g_mbb,3,s.mbb_upper)) return(false);
   if(!Copy1(g_mbb,5,s.mbb_lower)) return(false);
   if(!Copy1(g_mbb,20,s.mbb_regime)) return(false);
   if(!Copy1(g_mbb,22,s.mbb_squeeze)) return(false);
   if(!Copy1(g_mbb,24,s.mbb_release)) return(false);
   if(!Copy1(g_mbb,25,s.s1l)) return(false);
   if(!Copy1(g_mbb,26,s.s1s)) return(false);
   if(!Copy1(g_mbb,27,s.s2l)) return(false);
   if(!Copy1(g_mbb,28,s.s2s)) return(false);
   if(!Copy1(g_mbb,29,s.s3l)) return(false);
   if(!Copy1(g_mbb,30,s.s3s)) return(false);
   if(!Copy1(g_mbb,31,s.mbb_priority)) return(false);
   // TB: 26 ready, 2 bias, 28 atr, 27 structure, 7/8 sweeps, 11/12 disp, 43 ver
   if(!Copy1(g_tb,26,s.tb_ready)) return(false);
   if(!Copy1(g_tb,2,s.tb_bias)) return(false);
   if(!Copy1(g_tb,28,s.tb_atr)) return(false);
   if(!Copy1(g_tb,27,s.tb_struct)) return(false);
   if(!Copy1(g_tb,7,s.tb_sh)) return(false);
   if(!Copy1(g_tb,8,s.tb_sl)) return(false);
   if(!Copy1(g_tb,11,s.tb_du)) return(false);
   if(!Copy1(g_tb,12,s.tb_dd)) return(false);
   if(!Copy1(g_tb,43,s.tb_ver)) return(false);
   // QQE: 3 primary, 8 state, 9 cross
   if(!Copy1(g_qqe,3,s.qqe_primary)) return(false);
   if(!Copy1(g_qqe,8,s.qqe_state)) return(false);
   if(!Copy1(g_qqe,9,s.qqe_cross)) return(false);

   const bool aird_ok=(s.aird_valid>=0.5);
   const bool vrc_ok =(s.vrc_valid>=0.5);
   const bool mbb_ok =IsFinite(s.mbb_basis) && IsFinite(s.mbb_upper) && IsFinite(s.mbb_lower);
   const bool tb_ok  =(s.tb_ready>=0.5) && (s.tb_ver>=2.0);
   const bool qqe_ok =IsFinite(s.qqe_primary);
   s.ready=aird_ok && vrc_ok && mbb_ok && tb_ok && qqe_ok;
   if(!s.ready) return(true);

   // --- ENGINE_R raw (outcome-blind structural conjunction) ---
   // Event: S1 edge flags
   // Context: AIRD ranging(2), conf floor; VRC in {2,3,7}
   // Structure: sweep same side within lookback (current bar only for Stage-0 density)
   // Timing: |primary| was extreme or cross-back
   const bool aird_range=((int)MathRound(s.aird_regime)==2) && (s.aird_conf>=InpAirdConfFloor);
   const int  vrc_reg=(int)MathRound(s.vrc_regime);
   const bool vrc_mr=(vrc_reg==2 || vrc_reg==3 || vrc_reg==7);
   const bool qqe_timing_long =(s.qqe_cross>0.0) || (s.qqe_primary<=-InpQqeExtremeAbs) || (s.qqe_state>=0.0 && s.qqe_primary<0.0);
   const bool qqe_timing_short=(s.qqe_cross<0.0) || (s.qqe_primary>= InpQqeExtremeAbs) || (s.qqe_state<=0.0 && s.qqe_primary>0.0);
   const bool sweep_low =(s.tb_sl>0.5);
   const bool sweep_high=(s.tb_sh>0.5);

   if(aird_range && vrc_mr && (s.s1l>0.5) && sweep_low && qqe_timing_long)
      s.r_long=1;
   if(aird_range && vrc_mr && (s.s1s>0.5) && sweep_high && qqe_timing_short)
      s.r_short=1;

   // --- ENGINE_T raw (telemetry only in Stage-0; not scored for HYP-001) ---
   const bool aird_bull=((int)MathRound(s.aird_regime)==0) && (s.aird_conf>=InpAirdConfFloor);
   const bool aird_bear=((int)MathRound(s.aird_regime)==1) && (s.aird_conf>=InpAirdConfFloor);
   const bool vrc_trend=(vrc_reg>=4 && vrc_reg<=6) || (vrc_reg<=1 && vrc_reg>=-1);
   const bool bos_up=(s.tb_struct>0.0);
   const bool bos_dn=(s.tb_struct<0.0);
   if(aird_bull && vrc_trend && (s.s2l>0.5) && bos_up && (s.qqe_state>0.0))
      s.t_long=1;
   if(aird_bear && vrc_trend && (s.s2s>0.5) && bos_dn && (s.qqe_state<0.0))
      s.t_short=1;

   // --- ENGINE_B raw (telemetry only) ---
   const bool release=(s.mbb_release>0.5);
   if(release && (s.s3l>0.5) && (s.tb_du>0.5) && (s.qqe_state>0.0) && (s.vrc_high<0.5))
      s.b_long=1;
   if(release && (s.s3s>0.5) && (s.tb_dd>0.5) && (s.qqe_state<0.0) && (s.vrc_high<0.5))
      s.b_short=1;

   return(true);
  }

//+------------------------------------------------------------------+
void ExportBar()
  {
   if(g_file==INVALID_HANDLE) return;
   datetime t=iTime(_Symbol,PERIOD_M5,1);
   if(t<=0) return;
   if(t<InpCensusFrom || t>InpCensusTo) return;

   Fiv2Snap s;
   if(!ReadSnap(s))
     {
      g_snapshot_fail++;
      return;
     }

   MqlTick tick;
   double spread_points=0.0;
   if(SymbolInfoTick(_Symbol,tick) && _Point>0.0)
      spread_points=(tick.ask-tick.bid)/_Point;

   FileWrite(g_file,
      TimeToString(t,TIME_DATE|TIME_SECONDS),
      DoubleToString(iOpen(_Symbol,PERIOD_M5,1),_Digits),
      DoubleToString(iHigh(_Symbol,PERIOD_M5,1),_Digits),
      DoubleToString(iLow(_Symbol,PERIOD_M5,1),_Digits),
      DoubleToString(iClose(_Symbol,PERIOD_M5,1),_Digits),
      DoubleToString(spread_points,2),
      DoubleToString(s.aird_valid,0),DoubleToString(s.aird_regime,0),DoubleToString(s.aird_conf,8),
      DoubleToString(s.p_bull,8),DoubleToString(s.p_bear,8),DoubleToString(s.p_range,8),DoubleToString(s.p_highvol,8),
      DoubleToString(s.vrc_valid,0),DoubleToString(s.vrc_regime,0),DoubleToString(s.vrc_dir,8),
      DoubleToString(s.vrc_atr_pct,8),DoubleToString(s.vrc_high,0),DoubleToString(s.vrc_low,0),
      DoubleToString(s.mbb_basis,_Digits),DoubleToString(s.mbb_upper,_Digits),DoubleToString(s.mbb_lower,_Digits),
      DoubleToString(s.mbb_regime,0),DoubleToString(s.mbb_squeeze,8),DoubleToString(s.mbb_release,0),
      DoubleToString(s.s1l,0),DoubleToString(s.s1s,0),DoubleToString(s.s2l,0),DoubleToString(s.s2s,0),
      DoubleToString(s.s3l,0),DoubleToString(s.s3s,0),DoubleToString(s.mbb_priority,0),
      DoubleToString(s.tb_ready,0),DoubleToString(s.tb_bias,0),DoubleToString(s.tb_atr,_Digits),
      DoubleToString(s.tb_struct,0),DoubleToString(s.tb_sh,0),DoubleToString(s.tb_sl,0),
      DoubleToString(s.tb_du,0),DoubleToString(s.tb_dd,0),DoubleToString(s.tb_ver,1),
      DoubleToString(s.qqe_primary,8),DoubleToString(s.qqe_state,0),DoubleToString(s.qqe_cross,0),
      IntegerToString(s.ready?1:0),
      IntegerToString(s.r_long),IntegerToString(s.r_short),
      IntegerToString(s.t_long),IntegerToString(s.t_short),
      IntegerToString(s.b_long),IntegerToString(s.b_short),
      InpHypothesisId,InpVariantTag,g_run_id);

   g_rows++;
   if(s.ready) g_ready_rows++;
   if(s.r_long==1)  g_raw_r_long++;
   if(s.r_short==1) g_raw_r_short++;
   if(g_rows%InpCensusFlushEvery==0) FileFlush(g_file);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpAllowTrading)
     {
      Print("FIV2 fail-closed: InpAllowTrading must be false for Stage-0.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!InpEnableTelemetry)
     {
      Print("FIV2 fail-closed: telemetry required.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(StringFind(InpHypothesisId,"UNREGISTERED")>=0)
     {
      Print("FIV2 fail-closed: register a hypothesis id.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(_Symbol!=InpExpectedSymbol)
     {
      PrintFormat("FIV2 fail-closed: symbol %s != expected %s",_Symbol,InpExpectedSymbol);
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(_Period!=PERIOD_M5)
     {
      Print("FIV2 fail-closed: Stage-0 HYP-001 is M5-only.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpCensusFrom<=0 || InpCensusTo<=InpCensusFrom)
     {
      Print("FIV2 fail-closed: invalid census window.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   if(CreateHandles()!=INIT_SUCCEEDED) return(INIT_FAILED);
   if(!OpenCensusFile())
     {
      ReleaseHandles();
      return(INIT_FAILED);
     }

   PrintFormat("FIV2 Stage-0 init OK hyp=%s window=%s..%s file=%s",
               InpHypothesisId,
               TimeToString(InpCensusFrom,TIME_DATE),
               TimeToString(InpCensusTo,TIME_DATE),
               g_file_name);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(g_file!=INVALID_HANDLE)
     {
      FileFlush(g_file);
      FileClose(g_file);
      g_file=INVALID_HANDLE;
     }
   ReleaseHandles();
   PrintFormat("FIV2 deinit reason=%d bars=%I64d rows=%I64d ready=%I64d Rlong=%I64d Rshort=%I64d snap_fail=%I64d",
               reason,g_closed_bars,g_rows,g_ready_rows,g_raw_r_long,g_raw_r_short,g_snapshot_fail);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // Absolute no-trade guard
   if(InpAllowTrading) return;
   if(PositionsTotal()>0 || OrdersTotal()>0) return;

   datetime t=iTime(_Symbol,PERIOD_M5,0);
   if(t<=0 || t==g_last_bar_time) return;
   // New bar => previous bar is closed at shift 1
   g_last_bar_time=t;
   g_closed_bars++;
   ExportBar();
  }

//+------------------------------------------------------------------+
//| No trading callbacks intentionally empty.                        |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   // Stage-0: ignore; trading is disabled.
  }
//+------------------------------------------------------------------+
