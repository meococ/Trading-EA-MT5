//+------------------------------------------------------------------+
//| EA_MultiAssetTSMOMContractProbeV1.mq5                            |
//| Source/spec probe only: emits broker symbol and swap contracts.  |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "No-order broker contract probe for HYP-MULTI-TSMOM-D1-004"

input bool  InpResearchAutoMode=true;
input ulong InpMagic=260812007;

const string HYPOTHESIS_ID="HYP-MULTI-TSMOM-D1-004-CONTRACT-PROBE";
const string EXPECTED_SYMBOL="EURUSD";
#define SYMBOL_COUNT 9
string g_symbols[SYMBOL_COUNT]={"EURUSD","GBPUSD","AUDUSD","NZDUSD",
                                "USDJPY","USDCAD","USDCHF","XAUUSD","BTCUSD"};
long g_ticks=0;

void EmitSymbolContract(const string symbol)
  {
   ResetLastError();
   const bool selected=SymbolSelect(symbol,true);
   const int select_error=GetLastError();
   long digits=0,swap_mode=0,rollover=0,calc_mode=0,trade_mode=0;
   double point=0.0,tick_size=0.0,tick_value=0.0,contract=0.0;
   double volume_min=0.0,volume_max=0.0,volume_step=0.0;
   double swap_long=0.0,swap_short=0.0;
   const bool integer_ok=
      SymbolInfoInteger(symbol,SYMBOL_DIGITS,digits) &&
      SymbolInfoInteger(symbol,SYMBOL_SWAP_MODE,swap_mode) &&
      SymbolInfoInteger(symbol,SYMBOL_SWAP_ROLLOVER3DAYS,rollover) &&
      SymbolInfoInteger(symbol,SYMBOL_TRADE_CALC_MODE,calc_mode) &&
      SymbolInfoInteger(symbol,SYMBOL_TRADE_MODE,trade_mode);
   const bool double_ok=
      SymbolInfoDouble(symbol,SYMBOL_POINT,point) &&
      SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE,tick_size) &&
      SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_VALUE,tick_value) &&
      SymbolInfoDouble(symbol,SYMBOL_TRADE_CONTRACT_SIZE,contract) &&
      SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN,volume_min) &&
      SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX,volume_max) &&
      SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP,volume_step) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_LONG,swap_long) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_SHORT,swap_short);
   const string base=SymbolInfoString(symbol,SYMBOL_CURRENCY_BASE);
   const string profit=SymbolInfoString(symbol,SYMBOL_CURRENCY_PROFIT);
   const string margin=SymbolInfoString(symbol,SYMBOL_CURRENCY_MARGIN);
   MqlTick tick;
   const bool tick_ok=SymbolInfoTick(symbol,tick) && tick.time_msc>0 &&
                      tick.bid>0.0 && tick.ask>=tick.bid;
   PrintFormat("MTS004_CONTRACT symbol=%s selected=%s select_error=%d integer_ok=%s double_ok=%s tick_ok=%s digits=%I64d point=%.12f tick_size=%.12f tick_value=%.12f contract=%.8f volume_min=%.8f volume_max=%.8f volume_step=%.8f swap_mode=%I64d swap_long=%.12f swap_short=%.12f rollover3=%I64d calc_mode=%I64d trade_mode=%I64d base=%s profit=%s margin=%s bid=%.12f ask=%.12f tick_time_msc=%I64d",
               symbol,(string)selected,select_error,(string)integer_ok,(string)double_ok,
               (string)tick_ok,digits,point,tick_size,tick_value,contract,
               volume_min,volume_max,volume_step,swap_mode,swap_long,swap_short,
               rollover,calc_mode,trade_mode,base,profit,margin,
               tick_ok ? tick.bid : 0.0,tick_ok ? tick.ask : 0.0,
               tick_ok ? tick.time_msc : 0);
  }

int OnInit()
  {
   if(_Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_H1 || !InpResearchAutoMode ||
      InpMagic!=260812007)
     {
      PrintFormat("MTS004_CONTRACT_IDENTITY_FAIL symbol=%s period=%d",
                  _Symbol,(int)_Period);
      return INIT_FAILED;
     }
   for(int i=0;i<SYMBOL_COUNT;i++)
      EmitSymbolContract(g_symbols[i]);
   PrintFormat("MTS004_CONTRACT_PROBE_READY hypothesis_id=%s economics_authorized=false",
               HYPOTHESIS_ID);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   g_ticks++;
  }

void OnDeinit(const int reason)
  {
   PrintFormat("MTS004_CONTRACT_PROBE_SUMMARY hypothesis_id=%s ticks=%I64d reason=%d orders=0 performance_metrics_authorized=false economics_authorized=false",
               HYPOTHESIS_ID,g_ticks,reason);
  }
//+------------------------------------------------------------------+
