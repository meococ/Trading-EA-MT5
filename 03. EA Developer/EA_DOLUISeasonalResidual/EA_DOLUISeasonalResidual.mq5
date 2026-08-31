//+------------------------------------------------------------------+
//|                              EA_DOLUISeasonalResidual.mq5        |
//| HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001                     |
//| Official DOL UI seasonal-residual delayed H1 continuation.     |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Hash-bound official DOL UI seasonal-residual H1 Model-0"

#include <Trade/Trade.mqh>
#include "resources/dolui_001_train_table.mqh"

input string InpHypothesisId       = "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001";
input string InpVariantTag         = "DOLUI_RESIDUAL_H1_DELAY4H_V1";
input bool   InpResearchAutoMode   = false;
input bool   InpEnableAudit        = true;
input bool   InpReverseComparator  = false;
input ulong  InpMagic              = 8132601;
input double InpExposurePercent    = 0.25;
input double InpSizingPips         = 40.0;
input double InpMaxLots            = 1.0;
input int    InpMaxEntryDelaySec   = 300;
input int    InpDeviationPoints    = 100;

const double AF_COMMISSION_ROUND_TURN_USD_PER_LOT=4.0;
const double AF_SLIPPAGE_SPREAD_MULTIPLIER=0.30;

CTrade g_trade;
int    g_next_event=0;
int    g_active_event=-1;
bool   g_runtime_failed=false;
string g_failure_reason="";
string g_role="PRIMARY";
string g_csv_name="";
string g_meta_name="";
int    g_csv=INVALID_HANDLE;

int g_completed=0;
int g_source_flat=0;
int g_missed_entry=0;
int g_bar_mismatch=0;
int g_weekend_skips=0;
int g_overlap_skips=0;
int g_entry_rejects=0;
int g_exit_rejects=0;
int g_max_concurrent=0;
int g_table_buy=0;
int g_table_sell=0;
int g_table_flat=0;

long   g_entry_tick_msc=0;
double g_entry_bid=0.0;
double g_entry_ask=0.0;
double g_entry_fill=0.0;
double g_entry_lots=0.0;
double g_entry_spread_pips=0.0;
double g_entry_pip_value_per_lot=0.0;
int    g_entry_direction=0;

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
   ArrayResize(payload,copied-1);
   ArrayResize(key,0);
   if(CryptEncode(CRYPT_HASH_SHA256,payload,key,digest)<=0)
      return(false);
   digest_hex=HexBytes(digest);
   return(StringLen(digest_hex)==64);
  }

void FailRuntime(const string reason)
  {
   if(!g_runtime_failed)
      Print("DOLUI001_RUNTIME_FAIL reason=",reason);
   g_runtime_failed=true;
   g_failure_reason=reason;
  }

bool ValidateFrozenTable()
  {
   if(ArraySize(AF_DOLUI_EVENT_ID)!=AF_DOLUI_EVENT_COUNT ||
      ArraySize(AF_DOLUI_RELEASE_UTC)!=AF_DOLUI_EVENT_COUNT ||
      ArraySize(AF_DOLUI_RELEASE_SERVER)!=AF_DOLUI_EVENT_COUNT ||
      ArraySize(AF_DOLUI_DECISION_OPEN)!=AF_DOLUI_EVENT_COUNT ||
      ArraySize(AF_DOLUI_ENTRY_TARGET)!=AF_DOLUI_EVENT_COUNT ||
      ArraySize(AF_DOLUI_EXIT_TARGET)!=AF_DOLUI_EVENT_COUNT ||
      ArraySize(AF_DOLUI_RESIDUAL)!=AF_DOLUI_EVENT_COUNT ||
      ArraySize(AF_DOLUI_DIRECTION)!=AF_DOLUI_EVENT_COUNT ||
      ArraySize(AF_DOLUI_AVAILABLE)!=AF_DOLUI_EVENT_COUNT)
      return(false);

   string canonical="";
   for(int i=0;i<AF_DOLUI_EVENT_COUNT;i++)
     {
      if(AF_DOLUI_EVENT_ID[i]!=StringFormat("DOLUI%04d",i+1))
         return(false);
      if(i>0 && AF_DOLUI_RELEASE_SERVER[i]<=AF_DOLUI_RELEASE_SERVER[i-1])
         return(false);
      const long offset=AF_DOLUI_RELEASE_SERVER[i]-AF_DOLUI_RELEASE_UTC[i];
      if(offset!=7200 && offset!=10800)
         return(false);
      if(AF_DOLUI_RELEASE_SERVER[i]+1800!=AF_DOLUI_DECISION_OPEN[i] ||
         AF_DOLUI_DECISION_OPEN[i]+3600!=AF_DOLUI_ENTRY_TARGET[i] ||
         AF_DOLUI_ENTRY_TARGET[i]+14400!=AF_DOLUI_EXIT_TARGET[i])
         return(false);
      MqlDateTime release_parts;
      TimeToStruct((datetime)AF_DOLUI_RELEASE_SERVER[i],release_parts);
      if(release_parts.day_of_week!=3 && release_parts.day_of_week!=4)
         return(false);
      if(AF_DOLUI_DIRECTION[i]>0)
         g_table_buy++;
      else if(AF_DOLUI_DIRECTION[i]<0)
         g_table_sell++;
      else
         g_table_flat++;
      if(AF_DOLUI_AVAILABLE[i]==0 &&
         (AF_DOLUI_DIRECTION[i]!=0 || AF_DOLUI_RESIDUAL[i]!=0))
         return(false);
      canonical+=StringFormat("%s,%I64d,%I64d,%I64d,%I64d,%I64d,%I64d,%d,%d\n",
                              AF_DOLUI_EVENT_ID[i],AF_DOLUI_RELEASE_UTC[i],
                              AF_DOLUI_RELEASE_SERVER[i],AF_DOLUI_DECISION_OPEN[i],
                              AF_DOLUI_ENTRY_TARGET[i],AF_DOLUI_EXIT_TARGET[i],
                              AF_DOLUI_RESIDUAL[i],AF_DOLUI_DIRECTION[i],
                              AF_DOLUI_AVAILABLE[i]);
     }
   if(g_table_buy!=101 || g_table_sell!=157 || g_table_flat!=2)
      return(false);
   string actual="";
   if(!Sha256Utf8(canonical,actual) || actual!=AF_DOLUI_TABLE_SHA256)
     {
      PrintFormat("DOLUI001_TABLE_HASH_FAIL expected=%s actual=%s",
                  AF_DOLUI_TABLE_SHA256,actual);
      return(false);
     }
   PrintFormat("DOLUI001_SOURCE_BIND source_sha256=%s receipt_sha256=%s table_sha256=%s events=%d buy=%d sell=%d flat=%d",
               AF_DOLUI_SOURCE_SHA256,AF_DOLUI_SOURCE_RECEIPT_SHA256,actual,
               AF_DOLUI_EVENT_COUNT,g_table_buy,g_table_sell,g_table_flat);
   return(true);
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
   const double capped=MathMin(MathMin(raw,InpMaxLots),maximum);
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
      InpExposurePercent<=0.0 || InpSizingPips<=0.0 || InpMaxLots<=0.0)
      return(false);
   pip_value_per_lot=tick_value*pip/tick_size;
   if(pip_value_per_lot<=0.0 || !MathIsValidNumber(pip_value_per_lot))
      return(false);
   const double raw=(equity*InpExposurePercent/100.0)/
                    (InpSizingPips*pip_value_per_lot);
   lots=NormalizeLotsDown(raw);
   return(lots>0.0);
  }

bool ProfitForPrices(const int direction,const double lots,const double open_price,
                     const double close_price,double &profit)
  {
   const ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   return(OrderCalcProfit(type,_Symbol,lots,open_price,close_price,profit));
  }

void WriteEventRow(const string status,const int event_index,const int direction,
                   const long entry_msc,const long exit_msc,const double lots,
                   const double entry_bid,const double entry_ask,const double entry_fill,
                   const double exit_bid,const double exit_ask,const double exit_fill,
                   const double entry_spread_pips,const double exit_spread_pips,
                   const double pip_value_per_lot,const double raw_mid_pnl,
                   const double executable_pnl,const double observed_cost,
                   const double commission_usd,const double dynamic_slippage_usd,
                   const double complete_cost_usd,const double net_base,
                   const double net_x1_5,const double net_x2,const string detail)
  {
   if(g_csv==INVALID_HANDLE)
     {
      FailRuntime("AUDIT_HANDLE_INVALID");
      return;
     }
   FileWrite(g_csv,status,g_role,InpHypothesisId,InpVariantTag,
             AF_DOLUI_EVENT_ID[event_index],AF_DOLUI_RELEASE_UTC[event_index],
             AF_DOLUI_RELEASE_SERVER[event_index],AF_DOLUI_DECISION_OPEN[event_index],
             AF_DOLUI_ENTRY_TARGET[event_index],AF_DOLUI_EXIT_TARGET[event_index],
             AF_DOLUI_RESIDUAL[event_index],AF_DOLUI_DIRECTION[event_index],
             AF_DOLUI_AVAILABLE[event_index],direction,entry_msc,exit_msc,lots,
             entry_bid,entry_ask,entry_fill,exit_bid,exit_ask,exit_fill,
             entry_spread_pips,exit_spread_pips,pip_value_per_lot,raw_mid_pnl,
             executable_pnl,observed_cost,commission_usd,dynamic_slippage_usd,
             complete_cost_usd,net_base,net_x1_5,net_x2,detail);
   FileFlush(g_csv);
  }

void WriteTerminalSkip(const string status,const int event_index,const int direction,
                       const long tick_msc,const string detail)
  {
   WriteEventRow(status,event_index,direction,tick_msc,0,0.0,
                 0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,
                 0.0,0.0,0.0,0.0,0.0,0.0,0.0,detail);
  }

bool ClosedDecisionBarMatches(const int event_index)
  {
   const datetime expected=(datetime)AF_DOLUI_DECISION_OPEN[event_index];
   const datetime actual=iTime(_Symbol,PERIOD_H1,1);
   return(actual>0 && actual==expected);
  }

bool IsWeekendUnsafe(const int event_index)
  {
   MqlDateTime entry_parts;
   MqlDateTime exit_parts;
   TimeToStruct((datetime)AF_DOLUI_ENTRY_TARGET[event_index],entry_parts);
   TimeToStruct((datetime)AF_DOLUI_EXIT_TARGET[event_index],exit_parts);
   return(entry_parts.day_of_week==0 || entry_parts.day_of_week>=5 ||
          exit_parts.day_of_week==0 || exit_parts.day_of_week>=5 ||
          entry_parts.year!=exit_parts.year || entry_parts.day_of_year!=exit_parts.day_of_year);
  }

bool OpenEvent(const int event_index,const MqlTick &tick)
  {
   const int source_direction=AF_DOLUI_DIRECTION[event_index];
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
   const string comment=StringFormat("DOLUI001_%s_%s",g_role,AF_DOLUI_EVENT_ID[event_index]);
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
   if(OwnedPositionCount(ticket)!=1 || ticket==0)
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
   g_entry_pip_value_per_lot=pip_value;
   g_entry_direction=direction;
   PrintFormat("DOLUI001_ENTRY role=%s event=%s release=%I64d decision=%I64d target=%I64d tick_msc=%I64d residual=%I64d direction=%d lots=%.2f fill=%.5f spread_pips=%.3f",
               g_role,AF_DOLUI_EVENT_ID[event_index],AF_DOLUI_RELEASE_SERVER[event_index],
               AF_DOLUI_DECISION_OPEN[event_index],AF_DOLUI_ENTRY_TARGET[event_index],
               tick.time_msc,AF_DOLUI_RESIDUAL[event_index],direction,lots,
               g_entry_fill,spread_pips);
   return(true);
  }

bool CloseActiveEvent(const MqlTick &tick)
  {
   if(g_active_event<0)
      return(true);
   ulong ticket=0;
   if(OwnedPositionCount(ticket)!=1 || ticket==0)
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
                    (tick.ask-tick.bid)/PipSize(),g_entry_pip_value_per_lot,
                    0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,
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
   const double exit_spread_pips=(tick.ask-tick.bid)/PipSize();
   const double observed_cost=MathMax(0.0,raw_mid_pnl-executable_pnl);
   const double commission=AF_COMMISSION_ROUND_TURN_USD_PER_LOT*g_entry_lots;
   const double dynamic_slippage=AF_SLIPPAGE_SPREAD_MULTIPLIER*
      (g_entry_spread_pips+exit_spread_pips)*g_entry_pip_value_per_lot*g_entry_lots;
   const double complete_cost=observed_cost+commission+dynamic_slippage;
   const double net_base=raw_mid_pnl-complete_cost;
   const double net_x1_5=raw_mid_pnl-1.5*complete_cost;
   const double net_x2=raw_mid_pnl-2.0*complete_cost;
   WriteEventRow("CLOSED",event_index,g_entry_direction,g_entry_tick_msc,tick.time_msc,
                 g_entry_lots,g_entry_bid,g_entry_ask,g_entry_fill,tick.bid,tick.ask,
                 exit_fill,g_entry_spread_pips,exit_spread_pips,
                 g_entry_pip_value_per_lot,raw_mid_pnl,executable_pnl,observed_cost,
                 commission,dynamic_slippage,complete_cost,net_base,net_x1_5,
                 net_x2,"OK");
   PrintFormat("DOLUI001_CLOSE role=%s event=%s entry_msc=%I64d exit_msc=%I64d target=%I64d raw=%.2f base=%.2f x1_5=%.2f x2=%.2f",
               g_role,AF_DOLUI_EVENT_ID[event_index],g_entry_tick_msc,tick.time_msc,
               AF_DOLUI_EXIT_TARGET[event_index],raw_mid_pnl,net_base,net_x1_5,net_x2);
   g_completed++;
   g_active_event=-1;
   return(true);
  }

int AccountedEvents()
  {
   return(g_completed+g_source_flat+g_missed_entry+g_bar_mismatch+
          g_weekend_skips+g_overlap_skips+g_entry_rejects);
  }

void WriteRunMeta(const int reason)
  {
   const int handle=FileOpen(g_meta_name,FILE_COMMON|FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
     {
      Print("DOLUI001_RUNMETA_FAIL error=",GetLastError());
      return;
     }
   string json=StringFormat(
      "{\"schema_version\":\"dolui_001_run_meta.v1\",\"hypothesis_id\":\"%s\",\"role\":\"%s\",\"source_sha256\":\"%s\",\"source_receipt_sha256\":\"%s\",\"table_sha256\":\"%s\",\"events\":%d,\"next_event\":%d,\"accounted\":%d,\"completed\":%d,\"source_flat\":%d,\"missed_entry\":%d,\"bar_mismatch\":%d,\"weekend_skips\":%d,\"overlap_skips\":%d,\"entry_rejects\":%d,\"exit_rejects\":%d,\"max_concurrent\":%d,\"active_event\":%d,\"runtime_failed\":%s,\"failure_reason\":\"%s\",\"deinit_reason\":%d}",
      InpHypothesisId,g_role,AF_DOLUI_SOURCE_SHA256,
      AF_DOLUI_SOURCE_RECEIPT_SHA256,AF_DOLUI_TABLE_SHA256,
      AF_DOLUI_EVENT_COUNT,g_next_event,AccountedEvents(),g_completed,
      g_source_flat,g_missed_entry,g_bar_mismatch,g_weekend_skips,
      g_overlap_skips,g_entry_rejects,g_exit_rejects,g_max_concurrent,
      g_active_event,BoolText(g_runtime_failed),g_failure_reason,reason);
   FileWriteString(handle,json);
   FileClose(handle);
  }

int OnInit()
  {
   if(_Symbol!="EURUSD" || _Period!=PERIOD_H1 ||
      InpHypothesisId!="HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001" ||
      InpVariantTag!="DOLUI_RESIDUAL_H1_DELAY4H_V1" ||
      !InpResearchAutoMode || !InpEnableAudit || !MQLInfoInteger(MQL_TESTER))
     {
      PrintFormat("DOLUI001_INIT_FAIL symbol=%s period=%d hypothesis=%s auto=%s audit=%s tester=%s",
                  _Symbol,_Period,InpHypothesisId,BoolText(InpResearchAutoMode),
                  BoolText(InpEnableAudit),BoolText((bool)MQLInfoInteger(MQL_TESTER)));
      return(INIT_FAILED);
     }
   if(InpExposurePercent!=0.25 || InpSizingPips!=40.0 || InpMaxLots!=1.0 ||
      InpMaxEntryDelaySec!=300 || InpDeviationPoints!=100 || !ValidateFrozenTable())
     {
      Print("DOLUI001_INIT_FAIL frozen input/table mismatch");
      return(INIT_FAILED);
     }
   g_role=(InpReverseComparator ? "REVERSE" : "PRIMARY");
   g_csv_name=StringFormat("EURUSD_DOLUI001_Trades_%s.csv",g_role);
   g_meta_name=StringFormat("DOLUI001_RunMeta_%s.json",g_role);
   g_csv=FileOpen(g_csv_name,FILE_COMMON|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_csv==INVALID_HANDLE)
     {
      Print("DOLUI001_INIT_FAIL audit file error=",GetLastError());
      return(INIT_FAILED);
     }
   FileWrite(g_csv,"status","role","hypothesis_id","variant","event_id",
             "release_utc","release_server","decision_open","entry_target",
             "exit_target","seasonal_residual","source_direction",
             "source_available","direction","entry_tick_msc","exit_tick_msc",
             "lots","entry_bid","entry_ask","entry_fill","exit_bid","exit_ask",
             "exit_fill","entry_spread_pips","exit_spread_pips",
             "pip_value_per_lot","raw_mid_pnl_usd","executable_pnl_usd",
             "observed_spread_fill_cost_usd","commission_usd",
             "dynamic_slippage_usd","complete_cost_usd","net_base_usd",
             "net_x1_5_usd","net_x2_usd","detail");
   FileFlush(g_csv);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetAsyncMode(false);
   PrintFormat("DOLUI001_INIT_OK role=%s source_sha256=%s table_sha256=%s",
               g_role,AF_DOLUI_SOURCE_SHA256,AF_DOLUI_TABLE_SHA256);
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   if(g_runtime_failed)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.time_msc<=0 || tick.bid<=0.0 ||
      tick.ask<=tick.bid || !MathIsValidNumber(tick.bid) || !MathIsValidNumber(tick.ask))
     {
      FailRuntime("INVALID_TICK");
      return;
     }

   if(g_active_event>=0)
     {
      const long exit_target=AF_DOLUI_EXIT_TARGET[g_active_event];
      if((long)tick.time>=exit_target && !CloseActiveEvent(tick))
         return;
     }
   if(g_active_event>=0)
      return;

   while(g_next_event<AF_DOLUI_EVENT_COUNT)
     {
      const int event_index=g_next_event;
      const long entry_target=AF_DOLUI_ENTRY_TARGET[event_index];
      if((long)tick.time<entry_target)
         break;
      g_next_event++;
      const int source_direction=AF_DOLUI_DIRECTION[event_index];
      const int direction=(InpReverseComparator ? -source_direction : source_direction);
      if(AF_DOLUI_AVAILABLE[event_index]==0 || source_direction==0)
        {
         g_source_flat++;
         WriteTerminalSkip("SKIP_SOURCE_FLAT",event_index,0,tick.time_msc,
                           "EXPECTED_NOT_PUBLISHED_OR_ZERO");
         continue;
        }
      if((long)tick.time>entry_target+InpMaxEntryDelaySec)
        {
         g_missed_entry++;
         WriteTerminalSkip("SKIP_MISSED_ENTRY",event_index,direction,tick.time_msc,
                           "FIRST_TICK_LATER_THAN_FIVE_MINUTES");
         continue;
        }
      if(IsWeekendUnsafe(event_index))
        {
         g_weekend_skips++;
         WriteTerminalSkip("SKIP_WEEKEND_UNSAFE",event_index,direction,tick.time_msc,
                           "ENTRY_OR_EXIT_NOT_SAME_WEDNESDAY_THURSDAY");
         continue;
        }
      if(!ClosedDecisionBarMatches(event_index))
        {
         g_bar_mismatch++;
         WriteTerminalSkip("SKIP_DECISION_BAR_MISMATCH",event_index,direction,
                           tick.time_msc,"LAST_CLOSED_H1_OPEN_MISMATCH");
         continue;
        }
      ulong ticket=0;
      if(OwnedPositionCount(ticket)>0)
        {
         g_overlap_skips++;
         WriteTerminalSkip("SKIP_OVERLAP",event_index,direction,tick.time_msc,
                           "ONE_POSITION_ONLY");
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
   if(g_next_event!=AF_DOLUI_EVENT_COUNT)
      FailRuntime("NOT_ALL_EVENTS_REACHED");
   if(AccountedEvents()!=AF_DOLUI_EVENT_COUNT)
      FailRuntime("EVENT_ACCOUNTING_MISMATCH");
   if(g_source_flat!=2)
      FailRuntime("SOURCE_FLAT_COUNT_MISMATCH");
   if(g_csv!=INVALID_HANDLE)
     {
      FileFlush(g_csv);
      FileClose(g_csv);
      g_csv=INVALID_HANDLE;
     }
   WriteRunMeta(reason);
   PrintFormat("DOLUI001_SUMMARY role=%s events=%d accounted=%d completed=%d source_flat=%d missed=%d bar_mismatch=%d weekend=%d overlap=%d entry_reject=%d exit_reject=%d max_concurrent=%d runtime_failed=%s reason=%s",
               g_role,AF_DOLUI_EVENT_COUNT,AccountedEvents(),g_completed,
               g_source_flat,g_missed_entry,g_bar_mismatch,g_weekend_skips,
               g_overlap_skips,g_entry_rejects,g_exit_rejects,g_max_concurrent,
               BoolText(g_runtime_failed),g_failure_reason);
  }
