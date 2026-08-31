//+------------------------------------------------------------------+
//|                                      EA_EventDepthTransfer.mq5  |
//| HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009                    |
//| Frozen CME 6E levels-2-to-10 depth-transfer event scalp.     |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Hash-bound CME 6E post-wave depth-transfer DESIGN baseline"

#include <Trade/Trade.mqh>
#include "resources/event_depth_transfer_008_table.mqh"

input string InpHypothesisId       = "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009";
input string InpVariantTag         = "CME6E_DEPTH_TRANSFER_T60_HOLD60_V1";
input bool   InpResearchAutoMode   = false;
input bool   InpEnableAudit        = true;
input bool   InpReverseComparator  = false;
input ulong  InpMagic              = 8132609;
input double InpRiskPercent        = 0.25;
input double InpSizingStopPips     = 15.0;
input double InpMaxLots            = 1.0;
input int    InpDeviationPoints    = 100;

const long   AF_ENTRY_DELAY_MSC=60000;
const long   AF_EXIT_DELAY_MSC=120000;
const double AF_COMMISSION_ROUND_TURN_USD_PER_LOT=4.0;
const bool   AF_MAPPING_TERMINAL=true;

CTrade g_trade;
int    g_next_event=0;
int    g_active_event=-1;
bool   g_runtime_failed=false;
string g_failure_reason="";

int g_csv=INVALID_HANDLE;
string g_role="PRIMARY";
string g_csv_name="";
string g_meta_name="";

int g_completed=0;
int g_zero_source=0;
int g_missed_tick=0;
int g_overlap_skips=0;
int g_entry_rejects=0;
int g_exit_rejects=0;
int g_max_concurrent=0;
int g_table_buy=0;
int g_table_sell=0;
int g_table_zero=0;

long   g_entry_tick_msc=0;
double g_entry_bid=0.0;
double g_entry_ask=0.0;
double g_entry_fill=0.0;
double g_entry_lots=0.0;
double g_entry_spread_pips=0.0;
double g_entry_prior_median_pips=0.0;
double g_dynamic_slippage_pips=0.0;
double g_entry_pip_value_per_lot=0.0;
int    g_entry_direction=0;
double g_prior_entry_spreads[];

string BoolText(const bool value)
  {
   return(value ? "true" : "false");
  }

double PipSize()
  {
   return((_Digits==3 || _Digits==5) ? 10.0*_Point : _Point);
  }

string HexBytes(const uchar &bytes[])
  {
   string result="";
   for(int i=0;i<ArraySize(bytes);i++)
      result+=StringFormat("%02X",(int)bytes[i]);
   return(result);
  }

bool Sha256Utf8(const string value,string &digest_hex)
  {
   uchar payload[];
   uchar key[];
   uchar digest[];
   int copied=StringToCharArray(value,payload,0,WHOLE_ARRAY,CP_UTF8);
   if(copied<=0)
      return(false);
   // StringToCharArray includes the trailing NUL; the Python generator hashes
   // the UTF-8 payload only.
   ArrayResize(payload,copied-1);
   ArrayResize(key,0);
   if(CryptEncode(CRYPT_HASH_SHA256,payload,key,digest)<=0)
      return(false);
   digest_hex=HexBytes(digest);
   return(StringLen(digest_hex)==64);
  }

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property,
                       long &value)
  {
   value=0;
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property,value))
      return(false);
   return(GetLastError()==0);
  }

bool EmitD0SeriesProof()
  {
   long m5_synchronized=0;
   long m5_first_epoch=0;
   long m5_terminal_first_epoch=0;
   long m1_server_first_epoch=0;
   long m1_terminal_first_epoch=0;
   long m5_bars=0;
   if(!ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED,m5_synchronized) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,m5_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1_server_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT,m5_bars))
      return(false);

   ResetLastError();
   const long terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   datetime copytime_values[];
   ArraySetAsSeries(copytime_values,false);
   const datetime copytime_from=(datetime)m5_first_epoch;
   ResetLastError();
   const int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);
   const int copytime_error=GetLastError();
   const long copytime_first_epoch=(copytime_result==1 ? (long)copytime_values[0] : 0);

   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,m5_synchronized,m5_first_epoch,m5_terminal_first_epoch,
               m1_server_first_epoch,m1_terminal_first_epoch,m5_bars,terminal_maxbars,
               (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);
   return(m5_synchronized==1 && m5_first_epoch>0 && m5_terminal_first_epoch>0 &&
          m1_server_first_epoch>0 && m1_terminal_first_epoch>0 && m5_bars>0 &&
          terminal_maxbars>0 && terminal_error==0 && copytime_result==1 &&
          copytime_first_epoch==m5_first_epoch && copytime_error==0);
  }

bool ValidateFrozenTable()
  {
   if(ArraySize(AF_DEPTH_EVENT_ID)!=AF_DEPTH_EVENT_COUNT ||
      ArraySize(AF_DEPTH_UTC_MSC)!=AF_DEPTH_EVENT_COUNT ||
      ArraySize(AF_DEPTH_SERVER_MSC)!=AF_DEPTH_EVENT_COUNT ||
      ArraySize(AF_DEPTH_DIRECTION)!=AF_DEPTH_EVENT_COUNT)
      return(false);

   string canonical="";
   for(int i=0;i<AF_DEPTH_EVENT_COUNT;i++)
     {
      if(AF_DEPTH_EVENT_ID[i]!=StringFormat("EVT%04d",i+1))
         return(false);
      if(i>0 && AF_DEPTH_SERVER_MSC[i]<=AF_DEPTH_SERVER_MSC[i-1])
         return(false);
      const long offset=AF_DEPTH_SERVER_MSC[i]-AF_DEPTH_UTC_MSC[i];
      if(offset!=7200000 && offset!=10800000)
         return(false);
      if(AF_DEPTH_DIRECTION[i]>0)
         g_table_buy++;
      else if(AF_DEPTH_DIRECTION[i]<0)
         g_table_sell++;
      else
         g_table_zero++;
      canonical+=StringFormat("%s,%I64d,%I64d,%I64d\n",
                              AF_DEPTH_EVENT_ID[i],AF_DEPTH_UTC_MSC[i],
                              AF_DEPTH_SERVER_MSC[i],AF_DEPTH_DIRECTION[i]);
     }
   if(g_table_buy!=162 || g_table_sell!=156 || g_table_zero!=11)
      return(false);
   string actual="";
   if(!Sha256Utf8(canonical,actual) || actual!=AF_DEPTH_TABLE_SHA256)
     {
      PrintFormat("EVENTDEPTHTRANSFER009_TABLE_HASH_FAIL expected=%s actual=%s",
                  AF_DEPTH_TABLE_SHA256,actual);
      return(false);
     }
   PrintFormat("EVENTDEPTHTRANSFER009_SOURCE_BIND source_sha256=%s table_sha256=%s events=%d buy=%d sell=%d zero=%d",
               AF_DEPTH_SOURCE_SHA256,actual,AF_DEPTH_EVENT_COUNT,
               g_table_buy,g_table_sell,g_table_zero);
   return(true);
  }

void FailRuntime(const string reason)
  {
   if(!g_runtime_failed)
      Print("EVENTDEPTHTRANSFER009_RUNTIME_FAIL reason=",reason);
   g_runtime_failed=true;
   g_failure_reason=reason;
  }

int OwnedPositionCount(ulong &ticket)
  {
   ticket=0;
   int count=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong candidate=PositionGetTicket(i);
      if(candidate==0 || !PositionSelectByTicket(candidate))
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic)
        {
         FailRuntime("UNEXPECTED_SYMBOL_POSITION");
         continue;
        }
      ticket=candidate;
      count++;
     }
   if(count>g_max_concurrent)
      g_max_concurrent=count;
   if(count>1)
      FailRuntime("MORE_THAN_ONE_OWNED_POSITION");
   return(count);
  }

double NormalizeLotsDown(const double raw)
  {
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum)
      return(0.0);
   double capped=MathMin(MathMin(raw,InpMaxLots),maximum);
   double lots=MathFloor((capped+1e-12)/step)*step;
   if(lots<minimum)
      return(0.0);
   int digits=0;
   double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-10)
     {
      probe*=10.0;
      digits++;
     }
   return(NormalizeDouble(lots,digits));
  }

bool PositionSize(double &lots,double &pip_value_per_lot)
  {
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   const double tick_value=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   const double pip=PipSize();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(tick_size<=0.0 || tick_value<=0.0 || pip<=0.0 || equity<=0.0 ||
      InpRiskPercent<=0.0 || InpSizingStopPips<=0.0 || InpMaxLots<=0.0)
      return(false);
   pip_value_per_lot=tick_value*pip/tick_size;
   if(pip_value_per_lot<=0.0 || !MathIsValidNumber(pip_value_per_lot))
      return(false);
   const double raw=(equity*InpRiskPercent/100.0)/
                    (InpSizingStopPips*pip_value_per_lot);
   lots=NormalizeLotsDown(raw);
   return(lots>0.0);
  }

double PriorSpreadMedian()
  {
   const int count=ArraySize(g_prior_entry_spreads);
   if(count<=0)
      return(0.0);
   const int take=MathMin(10,count);
   double values[];
   ArrayResize(values,take);
   for(int i=0;i<take;i++)
      values[i]=g_prior_entry_spreads[count-take+i];
   ArraySort(values);
   if((take%2)==1)
      return(values[take/2]);
   return((values[take/2-1]+values[take/2])/2.0);
  }

void RememberEntrySpread(const double spread_pips)
  {
   const int count=ArraySize(g_prior_entry_spreads);
   ArrayResize(g_prior_entry_spreads,count+1);
   g_prior_entry_spreads[count]=spread_pips;
  }

void WriteEventRow(const string status,const int event_index,const int direction,
                   const long entry_msc,const long exit_msc,
                   const double lots,const double entry_bid,const double entry_ask,
                   const double entry_fill,const double exit_bid,const double exit_ask,
                   const double exit_fill,const double entry_spread_pips,
                   const double exit_spread_pips,const double prior_median_pips,
                   const double dynamic_slippage_pips,const double pip_value_per_lot,
                   const double raw_mid_pnl,const double executable_pnl,
                   const double commission_usd,const double complete_cost_usd,
                   const double net_base,const double net_x1_5,const double net_x2,
                   const string detail)
  {
   if(g_csv==INVALID_HANDLE)
     {
      FailRuntime("AUDIT_HANDLE_INVALID");
      return;
     }
   FileWrite(g_csv,status,g_role,InpHypothesisId,InpVariantTag,
             AF_DEPTH_EVENT_ID[event_index],AF_DEPTH_UTC_MSC[event_index],
             AF_DEPTH_SERVER_MSC[event_index],AF_DEPTH_DIRECTION[event_index],direction,
             AF_DEPTH_SERVER_MSC[event_index]+AF_ENTRY_DELAY_MSC,
             AF_DEPTH_SERVER_MSC[event_index]+AF_EXIT_DELAY_MSC,
             entry_msc,exit_msc,lots,entry_bid,entry_ask,entry_fill,
             exit_bid,exit_ask,exit_fill,entry_spread_pips,exit_spread_pips,
             prior_median_pips,dynamic_slippage_pips,pip_value_per_lot,
             raw_mid_pnl,executable_pnl,commission_usd,complete_cost_usd,
             net_base,net_x1_5,net_x2,detail);
   FileFlush(g_csv);
  }

void WriteTerminalSkip(const string status,const int event_index,const int direction,
                       const long tick_msc,const string detail)
  {
   WriteEventRow(status,event_index,direction,tick_msc,0,0.0,
                 0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,
                 0.0,0.0,0.0,0.0,0.0,0.0,0.0,detail);
  }

bool ProfitForPrices(const int direction,const double lots,const double open_price,
                     const double close_price,double &profit)
  {
   const ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   return(OrderCalcProfit(type,_Symbol,lots,open_price,close_price,profit));
  }

bool OpenEvent(const int event_index,const MqlTick &tick)
  {
   const int source_direction=AF_DEPTH_DIRECTION[event_index];
   const int direction=(InpReverseComparator ? -source_direction : source_direction);
   double lots=0.0;
   double pip_value=0.0;
   if(!PositionSize(lots,pip_value))
     {
      g_entry_rejects++;
      WriteTerminalSkip("ENTRY_REJECT",event_index,direction,tick.time_msc,"INVALID_POSITION_SIZE");
      return(false);
     }

   const double spread_pips=(tick.ask-tick.bid)/PipSize();
   const double prior_median=PriorSpreadMedian();
   const double dynamic_slippage=MathMax(0.0,spread_pips-prior_median);
   const string comment=StringFormat("AFD009_%s_%s",g_role,AF_DEPTH_EVENT_ID[event_index]);
   bool sent=false;
   if(direction>0)
      sent=g_trade.Buy(lots,_Symbol,0.0,0.0,0.0,comment);
   else
      sent=g_trade.Sell(lots,_Symbol,0.0,0.0,0.0,comment);

   if(!sent)
     {
      g_entry_rejects++;
      WriteTerminalSkip("ENTRY_REJECT",event_index,direction,tick.time_msc,
                        StringFormat("RETCODE_%u",g_trade.ResultRetcode()));
      return(false);
     }
   ulong ticket=0;
   const int position_count=OwnedPositionCount(ticket);
   if(g_runtime_failed || position_count!=1 || ticket==0)
     {
      FailRuntime("ENTRY_SUCCESS_WITHOUT_ONE_POSITION");
      return(false);
     }
   g_active_event=event_index;
   g_entry_tick_msc=tick.time_msc;
   g_entry_bid=tick.bid;
   g_entry_ask=tick.ask;
   g_entry_fill=g_trade.ResultPrice();
   if(g_entry_fill<=0.0)
      g_entry_fill=(direction>0 ? tick.ask : tick.bid);
   g_entry_lots=lots;
   g_entry_spread_pips=spread_pips;
   g_entry_prior_median_pips=prior_median;
   g_dynamic_slippage_pips=dynamic_slippage;
   g_entry_pip_value_per_lot=pip_value;
   g_entry_direction=direction;
   RememberEntrySpread(spread_pips);
   PrintFormat("EVENTDEPTHTRANSFER009_ENTRY role=%s event=%s tick_msc=%I64d target_msc=%I64d source_direction=%d direction=%d lots=%.2f fill=%.5f spread_pips=%.3f",
               g_role,AF_DEPTH_EVENT_ID[event_index],tick.time_msc,
               AF_DEPTH_SERVER_MSC[event_index]+AF_ENTRY_DELAY_MSC,
               AF_DEPTH_DIRECTION[event_index],direction,lots,g_entry_fill,spread_pips);
   return(true);
  }

bool CloseActiveEvent(const MqlTick &tick)
  {
   if(g_active_event<0)
      return(true);
   ulong ticket=0;
   const int position_count=OwnedPositionCount(ticket);
   if(g_runtime_failed || position_count!=1 || ticket==0)
     {
      FailRuntime("ACTIVE_EVENT_POSITION_MISSING");
      return(false);
     }
   const int event_index=g_active_event;
   if(!g_trade.PositionClose(ticket,InpDeviationPoints))
     {
      g_exit_rejects++;
      WriteEventRow("EXIT_REJECT",event_index,g_entry_direction,g_entry_tick_msc,
                    tick.time_msc,g_entry_lots,g_entry_bid,g_entry_ask,g_entry_fill,
                    tick.bid,tick.ask,0.0,g_entry_spread_pips,
                    (tick.ask-tick.bid)/PipSize(),g_entry_prior_median_pips,
                    g_dynamic_slippage_pips,g_entry_pip_value_per_lot,
                    0.0,0.0,0.0,0.0,0.0,0.0,0.0,
                    StringFormat("RETCODE_%u",g_trade.ResultRetcode()));
      FailRuntime("EXIT_REQUEST_REJECTED");
      return(false);
     }

   double exit_fill=g_trade.ResultPrice();
   if(exit_fill<=0.0)
      exit_fill=(g_entry_direction>0 ? tick.bid : tick.ask);
   const double entry_mid=(g_entry_bid+g_entry_ask)/2.0;
   const double exit_mid=(tick.bid+tick.ask)/2.0;
   double raw_mid_pnl=0.0;
   double executable_pnl=0.0;
   if(!ProfitForPrices(g_entry_direction,g_entry_lots,entry_mid,exit_mid,raw_mid_pnl) ||
      !ProfitForPrices(g_entry_direction,g_entry_lots,g_entry_fill,exit_fill,executable_pnl))
     {
      FailRuntime("ORDER_CALC_PROFIT_FAILED");
      return(false);
     }
   const double commission=AF_COMMISSION_ROUND_TURN_USD_PER_LOT*g_entry_lots;
   const double dynamic_cost=g_dynamic_slippage_pips*g_entry_pip_value_per_lot*g_entry_lots;
   const double complete_cost=(raw_mid_pnl-executable_pnl)+commission+dynamic_cost;
   const double net_base=raw_mid_pnl-complete_cost;
   const double net_x1_5=raw_mid_pnl-1.5*complete_cost;
   const double net_x2=raw_mid_pnl-2.0*complete_cost;
   const double exit_spread_pips=(tick.ask-tick.bid)/PipSize();
   WriteEventRow("CLOSED",event_index,g_entry_direction,g_entry_tick_msc,tick.time_msc,
                 g_entry_lots,g_entry_bid,g_entry_ask,g_entry_fill,
                 tick.bid,tick.ask,exit_fill,g_entry_spread_pips,exit_spread_pips,
                 g_entry_prior_median_pips,g_dynamic_slippage_pips,
                 g_entry_pip_value_per_lot,raw_mid_pnl,executable_pnl,commission,
                 complete_cost,net_base,net_x1_5,net_x2,"OK");
   PrintFormat("EVENTDEPTHTRANSFER009_CLOSE role=%s event=%s entry_msc=%I64d exit_msc=%I64d target_msc=%I64d raw=%.2f base=%.2f x1_5=%.2f x2=%.2f",
               g_role,AF_DEPTH_EVENT_ID[event_index],g_entry_tick_msc,tick.time_msc,
               AF_DEPTH_SERVER_MSC[event_index]+AF_EXIT_DELAY_MSC,
               raw_mid_pnl,net_base,net_x1_5,net_x2);
   g_completed++;
   g_active_event=-1;
   return(true);
  }

void WriteRunMeta(const int reason)
  {
   const int handle=FileOpen(g_meta_name,FILE_COMMON|FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
     {
      Print("EVENTDEPTHTRANSFER009_RUNMETA_FAIL error=",GetLastError());
      return;
     }
   const int accounted=g_completed+g_zero_source+g_missed_tick+g_overlap_skips+g_entry_rejects;
   string json=StringFormat(
      "{\"schema_version\":\"event_depth_transfer_009_run_meta.v1\",\"hypothesis_id\":\"%s\",\"role\":\"%s\",\"source_sha256\":\"%s\",\"table_sha256\":\"%s\",\"events\":%d,\"next_event\":%d,\"accounted\":%d,\"completed\":%d,\"zero_source\":%d,\"missed_tick\":%d,\"overlap_skips\":%d,\"entry_rejects\":%d,\"exit_rejects\":%d,\"max_concurrent\":%d,\"active_event\":%d,\"runtime_failed\":%s,\"failure_reason\":\"%s\",\"deinit_reason\":%d}",
      InpHypothesisId,g_role,AF_DEPTH_SOURCE_SHA256,AF_DEPTH_TABLE_SHA256,
      AF_DEPTH_EVENT_COUNT,g_next_event,accounted,g_completed,g_zero_source,
      g_missed_tick,g_overlap_skips,g_entry_rejects,g_exit_rejects,
      g_max_concurrent,g_active_event,BoolText(g_runtime_failed),g_failure_reason,reason);
   FileWriteString(handle,json);
   FileClose(handle);
  }

int OnInit()
  {
   if(AF_MAPPING_TERMINAL)
     {
      Print("EVENTDEPTHTRANSFER009_INIT_BLOCKED terminal frozen mapping; rerun forbidden");
      return(INIT_FAILED);
     }
   if(_Symbol!="EURUSD" || InpHypothesisId!="HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009" ||
      !InpResearchAutoMode || !InpEnableAudit || !MQLInfoInteger(MQL_TESTER))
     {
      PrintFormat("EVENTDEPTHTRANSFER009_INIT_FAIL symbol=%s hypothesis=%s auto=%s audit=%s tester=%s",
                  _Symbol,InpHypothesisId,BoolText(InpResearchAutoMode),
                  BoolText(InpEnableAudit),BoolText((bool)MQLInfoInteger(MQL_TESTER)));
      return(INIT_FAILED);
     }
   if(InpRiskPercent!=0.25 || InpSizingStopPips!=15.0 || InpMaxLots!=1.0 ||
      InpDeviationPoints!=100 || !EmitD0SeriesProof() || !ValidateFrozenTable())
     {
      Print("EVENTDEPTHTRANSFER009_INIT_FAIL frozen input/table/data-proof mismatch");
      return(INIT_FAILED);
     }
   g_role=(InpReverseComparator ? "REVERSE" : "PRIMARY");
   g_csv_name=StringFormat("EURUSD_EVENTDEPTHTRANSFER009_Trades_%s.csv",g_role);
   g_meta_name=StringFormat("EVENTDEPTHTRANSFER009_RunMeta_%s.json",g_role);
   g_csv=FileOpen(g_csv_name,FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_csv==INVALID_HANDLE)
     {
      Print("EVENTDEPTHTRANSFER009_INIT_FAIL audit file error=",GetLastError());
      return(INIT_FAILED);
     }
   FileWrite(g_csv,"status","role","hypothesis_id","variant","event_id",
             "event_utc_msc","event_server_msc","source_direction","direction",
             "entry_target_msc","exit_target_msc","entry_tick_msc","exit_tick_msc",
             "lots","entry_bid","entry_ask","entry_fill","exit_bid","exit_ask",
             "exit_fill","entry_spread_pips","exit_spread_pips",
             "prior_10_entry_spread_median_pips","dynamic_slippage_pips",
             "pip_value_per_lot","raw_mid_pnl_usd","executable_pnl_usd",
             "commission_usd","complete_cost_usd","net_base_usd",
             "net_x1_5_usd","net_x2_usd","detail");
   FileFlush(g_csv);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetAsyncMode(false);
   PrintFormat("EVENTDEPTHTRANSFER009_INIT_OK role=%s source_sha256=%s table_sha256=%s",
               g_role,AF_DEPTH_SOURCE_SHA256,AF_DEPTH_TABLE_SHA256);
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   if(g_runtime_failed)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.time_msc<=0 || tick.bid<=0.0 ||
      tick.ask<=tick.bid)
     {
      FailRuntime("INVALID_TICK");
      return;
     }

   if(g_active_event>=0)
     {
      const long exit_target=AF_DEPTH_SERVER_MSC[g_active_event]+AF_EXIT_DELAY_MSC;
      if(tick.time_msc>=exit_target && !CloseActiveEvent(tick))
         return;
     }
   if(g_active_event>=0)
      return;

   while(g_next_event<AF_DEPTH_EVENT_COUNT)
     {
      const int event_index=g_next_event;
      const long entry_target=AF_DEPTH_SERVER_MSC[event_index]+AF_ENTRY_DELAY_MSC;
      const long exit_target=AF_DEPTH_SERVER_MSC[event_index]+AF_EXIT_DELAY_MSC;
      if(tick.time_msc<entry_target)
         break;
      g_next_event++;
      if(AF_DEPTH_DIRECTION[event_index]==0)
        {
         g_zero_source++;
         WriteTerminalSkip("SKIP_ZERO",event_index,0,tick.time_msc,"SOURCE_INVALID_AMBIGUOUS_OR_UNAVAILABLE");
         continue;
        }
      const int source_direction=AF_DEPTH_DIRECTION[event_index];
      const int direction=(InpReverseComparator ? -source_direction : source_direction);
      if(tick.time_msc>=exit_target)
        {
         g_missed_tick++;
         WriteTerminalSkip("SKIP_MISSED_TICK",event_index,direction,tick.time_msc,
                           "FIRST_ELIGIBLE_TICK_NOT_BEFORE_EXIT_BOUNDARY");
         continue;
        }
      ulong ticket=0;
      const int position_count=OwnedPositionCount(ticket);
      if(g_runtime_failed)
         return;
      if(position_count>0)
        {
         g_overlap_skips++;
         WriteTerminalSkip("SKIP_OVERLAP",event_index,direction,tick.time_msc,"ONE_POSITION_ONLY");
         continue;
        }
      OpenEvent(event_index,tick);
      break;
     }
  }

void OnDeinit(const int reason)
  {
   ulong ticket=0;
   const int positions=OwnedPositionCount(ticket);
   if(g_active_event>=0 || positions!=0)
      FailRuntime("NONFLAT_OR_ACTIVE_AT_DEINIT");
   if(g_next_event!=AF_DEPTH_EVENT_COUNT)
      FailRuntime("NOT_ALL_EVENTS_REACHED");
   const int accounted=g_completed+g_zero_source+g_missed_tick+g_overlap_skips+g_entry_rejects;
   if(accounted!=AF_DEPTH_EVENT_COUNT)
      FailRuntime("EVENT_ACCOUNTING_MISMATCH");
   if(g_csv!=INVALID_HANDLE)
     {
      FileFlush(g_csv);
      FileClose(g_csv);
      g_csv=INVALID_HANDLE;
     }
   WriteRunMeta(reason);
   PrintFormat("EVENTDEPTHTRANSFER009_SUMMARY role=%s events=%d accounted=%d completed=%d zero=%d missed=%d overlap=%d entry_reject=%d exit_reject=%d max_concurrent=%d runtime_failed=%s reason=%s",
               g_role,AF_DEPTH_EVENT_COUNT,accounted,g_completed,g_zero_source,
               g_missed_tick,g_overlap_skips,g_entry_rejects,g_exit_rejects,
               g_max_concurrent,BoolText(g_runtime_failed),g_failure_reason);
  }

