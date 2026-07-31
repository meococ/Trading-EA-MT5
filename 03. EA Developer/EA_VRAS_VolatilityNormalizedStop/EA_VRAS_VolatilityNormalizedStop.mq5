#property copyright "AlphaFactory research"
#property version   "1.20"
#property strict
#property description "HYP006 stop experiment plus HYP007/HYP008 full-horizon diagnostics"
#property description "Closed-bar H1 EMA200 plus rolling M5 VWAP path entry"

enum ENUM_VRAS_SIGNAL
  {
   SIGNAL_NONE=0,
   SIGNAL_BUY=1,
   SIGNAL_SELL=-1
  };

input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-VRAS-EURUSD-M5-006";
input string InpVariantTag="CHALLENGER_ATR_STRUCTURAL";
input long   InpMagic=5600756;
input bool   InpUseVolatilityNormalizedStop=true;
input bool   InpDiagnosticDisableAccountDDEntryHalt=false;

input int    InpH1EmaPeriod=200;
input int    InpRollingVwapBars=48;
input int    InpSwingLookbackBars=10;
input double InpSlBufferPips=1.5;
input double InpControlMinSlPips=4.0;
input double InpControlMaxSlPips=15.0;
input int    InpAtrPeriod=14;
input double InpAtrFloorMultiple=1.0;
input double InpMaxStructuralAtrMultiple=3.0;
input double InpRiskRewardRatio=1.5;
input double InpBreakEvenTriggerR=1.0;
input double InpBreakEvenOffsetPips=0.5;

input double InpRiskPercent=0.25;
input double InpMaxSpreadPips=1.20;
input int    InpMaxTradesPerDay=5;
input double InpDailyLossPct=1.50;
input double InpMaxAccountDrawdownPct=6.00;
input int    InpMaxHoldBars=24;
input bool   InpRequireNewsGuard=false;

const string EA_NAME="EA_VRAS_VolatilityNormalizedStop";
const string TELEMETRY_PROFILE="lifecycle-v3";

datetime g_last_m5_bar=0;
int g_h1_ema_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;

string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
string g_decision_name="";
int g_lifecycle_handle=INVALID_HANDLE;
int g_decision_handle=INVALID_HANDLE;

double g_initial_equity=0.0;
double g_day_start_equity=0.0;
int g_day_key=-1;
int g_trades_today=0;
bool g_account_halt=false;
bool g_account_dd_threshold_breached=false;
double g_peak_equity=0.0;
double g_max_initial_equity_dd_pct=0.0;
double g_max_peak_equity_dd_pct=0.0;

ulong g_position_id=0;
double g_initial_entry=0.0;
double g_initial_stop=0.0;
double g_initial_target=0.0;
double g_initial_risk_account=0.0;
double g_position_net=0.0;
bool g_break_even_applied=false;

double g_pending_stop=0.0;
double g_pending_target=0.0;
double g_pending_risk_account=0.0;

long g_bars_seen=0;
long g_signals=0;
long g_entries_attempted=0;
long g_entries_opened=0;
long g_structure_rejections=0;
long g_guard_rejections=0;
long g_risk_rejections=0;

double PipSize()
  {
   return (_Digits==3 || _Digits==5) ? 10.0*_Point : _Point;
  }

int BrokerDateKey(const datetime when)
  {
   MqlDateTime parts;
   TimeToStruct(when,parts);
   return parts.year*1000+parts.day_of_year;
  }

void ResetRiskDayIfNeeded(const datetime when)
  {
   int key=BrokerDateKey(when);
   if(key==g_day_key)
      return;
   g_day_key=key;
   g_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_trades_today=0;
  }

void UpdateRiskState()
  {
   ResetRiskDayIfNeeded(TimeCurrent());
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_peak_equity<=0.0 || equity>g_peak_equity)
      g_peak_equity=equity;
   if(g_initial_equity>0.0)
     {
      double initial_dd_pct=100.0*(g_initial_equity-equity)/g_initial_equity;
      g_max_initial_equity_dd_pct=MathMax(g_max_initial_equity_dd_pct,initial_dd_pct);
     }
   if(g_peak_equity>0.0)
     {
      double peak_dd_pct=100.0*(g_peak_equity-equity)/g_peak_equity;
      g_max_peak_equity_dd_pct=MathMax(g_max_peak_equity_dd_pct,peak_dd_pct);
     }
   if(g_initial_equity>0.0 &&
      equity<=g_initial_equity*(1.0-InpMaxAccountDrawdownPct/100.0))
     {
      g_account_dd_threshold_breached=true;
      if(!InpDiagnosticDisableAccountDDEntryHalt)
         g_account_halt=true;
     }
  }

bool DailyLossHit()
  {
   return g_day_start_equity>0.0 &&
          AccountInfoDouble(ACCOUNT_EQUITY)<=
          g_day_start_equity*(1.0-InpDailyLossPct/100.0);
  }

double CurrentSpreadPips()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return -1.0;
   return (tick.ask-tick.bid)/PipSize();
  }

ulong OwnedPositionTicket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (long)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return ticket;
     }
   return 0;
  }

bool AnySymbolExposure()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0)
         return true;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol)
         return true;
     }
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0)
         return true;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol)
         return true;
     }
   return false;
  }

bool EntryGuardsAllow(string &status)
  {
   ResetRiskDayIfNeeded(TimeCurrent());
   if(!InpResearchAutoMode || !MQLInfoInteger(MQL_TESTER))
     {
      status="RESEARCH_MODE_REJECT";
      return false;
     }
   if(InpRequireNewsGuard)
     {
      status="NEWS_SOURCE_UNAVAILABLE_REJECT";
      return false;
     }
   if(g_account_halt)
     {
      status="ACCOUNT_DD_REJECT";
      return false;
     }
   if(DailyLossHit())
     {
      status="DAILY_LOSS_REJECT";
      return false;
     }
   if(g_trades_today>=InpMaxTradesPerDay)
     {
      status="TRADE_LIMIT_REJECT";
      return false;
     }
   if(AnySymbolExposure())
     {
      status="EXPOSURE_REJECT";
      return false;
     }
   double spread=CurrentSpreadPips();
   if(spread<=0.0 || spread>InpMaxSpreadPips)
     {
      status="SPREAD_REJECT";
      return false;
     }
   status="ALLOW";
   return true;
  }

double NormalizeVolumeDown(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<minimum || step<=0.0)
      return 0.0;
   double volume=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   if(volume<minimum)
      return 0.0;
   return NormalizeDouble(volume,8);
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,
                       double &planned_risk_account)
  {
   planned_risk_account=0.0;
   double budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   if(budget<=0.0)
      return 0.0;
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot_result))
      return 0.0;
   double loss_per_lot=MathAbs(one_lot_result);
   if(loss_per_lot<=0.0 || !MathIsValidNumber(loss_per_lot))
      return 0.0;
   double volume=NormalizeVolumeDown(budget/loss_per_lot);
   if(volume<=0.0)
      return 0.0;
   planned_risk_account=loss_per_lot*volume;
   if(planned_risk_account<=0.0 || planned_risk_account>budget*(1.0+1e-8))
      return 0.0;
   return volume;
  }

ENUM_ORDER_TYPE_FILLING FillingMode()
  {
   long flags=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,flags))
      return ORDER_FILLING_FOK;
   if((flags & SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
      return ORDER_FILLING_FOK;
   if((flags & SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

double CalculateRollingVwap()
  {
   double sum_pv=0.0;
   double sum_v=0.0;
   MqlRates history[];
   ArraySetAsSeries(history,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,InpRollingVwapBars,history)!=InpRollingVwapBars)
      return 0.0;
   for(int index=0;index<InpRollingVwapBars;index++)
     {
      double typical=(history[index].high+history[index].low+
                      history[index].close)/3.0;
      long volume=history[index].tick_volume;
      if(volume<=0)
         continue;
      sum_pv+=typical*(double)volume;
      sum_v+=(double)volume;
     }
   return sum_v>0.0 ? sum_pv/sum_v : 0.0;
  }

bool ReadClosedIndicators(double &h1_close,double &h1_ema,double &atr)
  {
   double ema_buffer[1];
   double atr_buffer[1];
   if(CopyBuffer(g_h1_ema_handle,0,1,1,ema_buffer)!=1)
      return false;
   if(CopyBuffer(g_atr_handle,0,1,1,atr_buffer)!=1)
      return false;
   h1_close=iClose(_Symbol,PERIOD_H1,1);
   h1_ema=ema_buffer[0];
   atr=atr_buffer[0];
   return h1_close>0.0 && h1_ema>0.0 && atr>0.0;
  }

ENUM_VRAS_SIGNAL EvaluateClosedBarSignal(MqlRates &bars[],const double h1_close,
                                         const double h1_ema,const double vwap)
  {
   if(vwap<=0.0)
      return SIGNAL_NONE;
   if(h1_close>h1_ema && bars[0].low<=vwap && bars[0].close>vwap &&
      bars[0].close>bars[1].high)
      return SIGNAL_BUY;
   if(h1_close<h1_ema && bars[0].high>=vwap && bars[0].close<vwap &&
      bars[0].close<bars[1].low)
      return SIGNAL_SELL;
   return SIGNAL_NONE;
  }

bool BuildStopGeometry(const int direction,const double entry,const double atr,
                       double &stop,double &target,string &status)
  {
   double extrema[];
   ArraySetAsSeries(extrema,true);
   int copied=direction>0 ?
              CopyLow(_Symbol,PERIOD_M5,1,InpSwingLookbackBars,extrema) :
              CopyHigh(_Symbol,PERIOD_M5,1,InpSwingLookbackBars,extrema);
   if(copied!=InpSwingLookbackBars)
     {
      status="SWING_LOOKUP_REJECT";
      return false;
     }
   int index=direction>0 ? ArrayMinimum(extrema) : ArrayMaximum(extrema);
   if(index<0)
      return false;
   double raw_stop=direction>0 ?
                   extrema[index]-InpSlBufferPips*PipSize() :
                   extrema[index]+InpSlBufferPips*PipSize();
   double raw_distance=direction*(entry-raw_stop);
   if(raw_distance<=0.0 || !MathIsValidNumber(raw_distance))
     {
      status="RAW_GEOMETRY_REJECT";
      return false;
     }
   double final_distance=raw_distance;
   if(InpUseVolatilityNormalizedStop)
     {
      if(raw_distance>atr*InpMaxStructuralAtrMultiple)
        {
         status="STRUCTURE_TOO_WIDE_REJECT";
         g_structure_rejections++;
         return false;
        }
      final_distance=MathMax(raw_distance,atr*InpAtrFloorMultiple);
     }
   else
     {
      final_distance=MathMax(InpControlMinSlPips*PipSize(),
                             MathMin(raw_distance,InpControlMaxSlPips*PipSize()));
     }
   stop=NormalizeDouble(entry-direction*final_distance,_Digits);
   target=NormalizeDouble(entry+direction*final_distance*InpRiskRewardRatio,_Digits);
   if(direction*(entry-stop)<=0.0 || direction*(target-entry)<=0.0)
     {
      status="FINAL_GEOMETRY_REJECT";
      return false;
     }
   status="GEOMETRY_OK";
   return true;
  }

void WriteDecision(const datetime when,const string status,const int direction,
                   const double h1_close,const double h1_ema,const double vwap,
                   const double atr,const double entry,const double stop,
                   const double target)
  {
   if(!InpEnableTelemetry || g_decision_handle==INVALID_HANDLE)
      return;
   FileWrite(g_decision_handle,TimeToString(when,TIME_DATE|TIME_SECONDS),
             InpVariantTag,status,direction,
             DoubleToString(h1_close,_Digits),DoubleToString(h1_ema,_Digits),
             DoubleToString(vwap,_Digits),DoubleToString(atr,_Digits),
             DoubleToString(entry,_Digits),DoubleToString(stop,_Digits),
             DoubleToString(target,_Digits),DoubleToString(CurrentSpreadPips(),4));
   FileFlush(g_decision_handle);
  }

bool TryOpenTrade(const int direction,const double h1_close,const double h1_ema,
                  const double vwap,const double atr)
  {
   g_entries_attempted++;
   string status="";
   if(!EntryGuardsAllow(status))
     {
      g_guard_rejections++;
      WriteDecision(TimeCurrent(),status,direction,h1_close,h1_ema,vwap,atr,0.0,0.0,0.0);
      return false;
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   double entry=direction>0 ? tick.ask : tick.bid;
   double stop=0.0;
   double target=0.0;
   if(!BuildStopGeometry(direction,entry,atr,stop,target,status))
     {
      WriteDecision(TimeCurrent(),status,direction,h1_close,h1_ema,vwap,atr,entry,stop,target);
      return false;
     }
   long stops_level=0;
   long freeze_level=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL,stops_level) ||
      !SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL,freeze_level))
      return false;
   double minimum_distance=MathMax((double)stops_level,(double)freeze_level)*_Point;
   if(MathAbs(entry-stop)<minimum_distance || MathAbs(target-entry)<minimum_distance)
     {
      g_risk_rejections++;
      WriteDecision(TimeCurrent(),"BROKER_DISTANCE_REJECT",direction,h1_close,h1_ema,
                    vwap,atr,entry,stop,target);
      return false;
     }
   double risk_account=0.0;
   double volume=RiskSizedVolume(direction,entry,stop,risk_account);
   if(volume<=0.0 || risk_account<=0.0)
     {
      g_risk_rejections++;
      WriteDecision(TimeCurrent(),"SIZING_REJECT",direction,h1_close,h1_ema,
                    vwap,atr,entry,stop,target);
      return false;
     }

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=10;
   request.type_filling=FillingMode();
   request.type_time=ORDER_TIME_GTC;
   request.comment=StringSubstr(InpHypothesisId,0,30);
   if(!OrderCheck(request,check))
     {
      g_risk_rejections++;
      WriteDecision(TimeCurrent(),"ORDER_CHECK_REJECT",direction,h1_close,h1_ema,
                    vwap,atr,entry,stop,target);
      return false;
     }

   g_pending_stop=stop;
   g_pending_target=target;
   g_pending_risk_account=risk_account;
   if(!OrderSend(request,result) ||
      (result.retcode!=TRADE_RETCODE_DONE &&
       result.retcode!=TRADE_RETCODE_DONE_PARTIAL &&
       result.retcode!=TRADE_RETCODE_PLACED))
     {
      g_pending_stop=0.0;
      g_pending_target=0.0;
      g_pending_risk_account=0.0;
      g_risk_rejections++;
      WriteDecision(TimeCurrent(),"ORDER_SEND_REJECT",direction,h1_close,h1_ema,
                    vwap,atr,entry,stop,target);
      return false;
     }
   WriteDecision(TimeCurrent(),"ORDER_ACCEPTED",direction,h1_close,h1_ema,
                 vwap,atr,entry,stop,target);
   return true;
  }

bool PositionIdentifierExists(const ulong identifier)
  {
   if(identifier==0)
      return false;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if((ulong)PositionGetInteger(POSITION_IDENTIFIER)==identifier)
         return true;
     }
   return false;
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong identifier)
  {
   if(!HistorySelect(0,TimeCurrent()))
      return ORDER_TYPE_BUY;
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 ||
         (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=identifier)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN)
         return HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ?
                ORDER_TYPE_SELL : ORDER_TYPE_BUY;
     }
   return ORDER_TYPE_BUY;
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal))
      return;
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   bool is_open=(entry==DEAL_ENTRY_IN);
   bool final_close=(!is_open && !PositionIdentifierExists(position_id));
   ENUM_ORDER_TYPE order_type=is_open ?
      (HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY) :
      EntryTypeForPosition(position_id);
   double volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
   double price=HistoryDealGetDouble(deal,DEAL_PRICE);
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   double net=profit+commission+swap+fee;
   if(is_open)
     {
      g_position_id=position_id;
      g_initial_entry=price;
      g_initial_stop=g_pending_stop;
      g_initial_target=g_pending_target;
      double actual_loss=0.0;
      if(OrderCalcProfit(order_type,_Symbol,volume,g_initial_entry,g_initial_stop,actual_loss))
         g_initial_risk_account=MathAbs(actual_loss);
      else
         g_initial_risk_account=g_pending_risk_account;
      g_position_net=0.0;
      g_break_even_applied=false;
      g_entries_opened++;
      g_trades_today++;
      g_pending_stop=0.0;
      g_pending_target=0.0;
      g_pending_risk_account=0.0;
     }
   g_position_net+=net;
   double risk_points=MathAbs(g_initial_entry-g_initial_stop)/_Point;
   if(InpEnableTelemetry && g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileWrite(g_lifecycle_handle,
                TimeToString((datetime)HistoryDealGetInteger(deal,DEAL_TIME),
                             TIME_DATE|TIME_SECONDS),
                is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"),
                order_type==ORDER_TYPE_SELL ? "SELL" : "BUY",
                DoubleToString(volume,8),DoubleToString(price,_Digits),_Symbol,
                StringFormat("%I64u",position_id),DoubleToString(risk_points,8),
                DoubleToString(g_initial_risk_account,8),StringFormat("%I64u",deal),
                DoubleToString(profit,8),DoubleToString(commission,8),
                DoubleToString(swap,8),DoubleToString(fee,8),
                DoubleToString(net,8),final_close ? "1" : "0");
      FileFlush(g_lifecycle_handle);
     }
   if(final_close)
     {
      g_position_id=0;
      g_initial_entry=0.0;
      g_initial_stop=0.0;
      g_initial_target=0.0;
      g_initial_risk_account=0.0;
      g_position_net=0.0;
      g_break_even_applied=false;
     }
  }

bool ModifyOwnedStops(const ulong ticket,const double stop,const double target)
  {
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   request.action=TRADE_ACTION_SLTP;
   request.position=ticket;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.sl=NormalizeDouble(stop,_Digits);
   request.tp=NormalizeDouble(target,_Digits);
   if(!OrderSend(request,result))
      return false;
   return result.retcode==TRADE_RETCODE_DONE ||
          result.retcode==TRADE_RETCODE_NO_CHANGES;
  }

bool CloseOwnedPosition(const ulong ticket)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.position=ticket;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=PositionGetDouble(POSITION_VOLUME);
   request.type=type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=10;
   request.type_filling=FillingMode();
   request.comment="VRAS HYP006 time exit";
   if(!OrderCheck(request,check) || !OrderSend(request,result))
      return false;
   return result.retcode==TRADE_RETCODE_DONE ||
          result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
          result.retcode==TRADE_RETCODE_PLACED;
  }

void ManageOwnedPosition()
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   int direction=type==POSITION_TYPE_BUY ? 1 : -1;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   double current=direction>0 ? tick.bid : tick.ask;
   double initial_distance=MathAbs(g_initial_entry-g_initial_stop);
   if(!g_break_even_applied && initial_distance>0.0 &&
      direction*(current-g_initial_entry)>=initial_distance*InpBreakEvenTriggerR)
     {
      double new_stop=g_initial_entry+
                      direction*InpBreakEvenOffsetPips*PipSize();
      if(ModifyOwnedStops(ticket,new_stop,PositionGetDouble(POSITION_TP)))
         g_break_even_applied=true;
     }
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   int held_bars=iBarShift(_Symbol,PERIOD_M5,opened,false);
   if(held_bars>=InpMaxHoldBars)
      CloseOwnedPosition(ticket);
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\","
      "\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\","
      "\"hypothesis_id\":\"%s\",\"variant_tag\":\"%s\",\"magic\":%I64d,"
      "\"promotion_eligible\":false,\"volatility_normalized_stop\":%s,"
      "\"cost_status\":\"UNVERIFIED_DIAGNOSTIC_ONLY\","
      "\"news_status\":\"DISABLED_MATCHED\",\"diagnostic\":{\"bars_seen\":%I64d,"
      "\"signals\":%I64d,\"entries_attempted\":%I64d,\"entries_opened\":%I64d,"
      "\"structure_rejections\":%I64d,\"guard_rejections\":%I64d,"
      "\"risk_rejections\":%I64d,\"account_dd_entry_halt_enabled\":%s,"
      "\"account_dd_threshold_pct\":%.8f,\"account_dd_threshold_breached\":%s,"
      "\"max_initial_equity_dd_pct\":%.8f,\"max_peak_equity_dd_pct\":%.8f,"
      "\"account_halt\":%s}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,InpHypothesisId,InpVariantTag,
      InpMagic,InpUseVolatilityNormalizedStop ? "true" : "false",
      g_bars_seen,g_signals,g_entries_attempted,g_entries_opened,
      g_structure_rejections,g_guard_rejections,g_risk_rejections,
      InpDiagnosticDisableAccountDDEntryHalt ? "false" : "true",
      InpMaxAccountDrawdownPct,g_account_dd_threshold_breached ? "true" : "false",
      g_max_initial_equity_dd_pct,g_max_peak_equity_dd_pct,
      g_account_halt ? "true" : "false");
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenTelemetry()
  {
   if(!InpEnableTelemetry)
      return true;
   g_run_id=StringFormat("%s_%I64u",InpHypothesisId,GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_decision_name=StringFormat("%s_DecisionTelemetry_%s.csv",_Symbol,g_run_id);
   g_lifecycle_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_lifecycle_handle,"event_time","action","order_type","volume","price",
             "symbol","position_id","risk_pts","initial_risk_account","deal",
             "deal_profit","deal_commission","deal_swap","deal_fee","deal_net",
             "is_final_close");
   FileFlush(g_lifecycle_handle);
   g_decision_handle=FileOpen(g_decision_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_decision_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_decision_handle,"server_time","variant","status","direction",
             "h1_close","h1_ema","rolling_vwap_48","atr14","entry","stop",
             "target","spread_pips");
   FileFlush(g_decision_handle);
   return WriteRunMeta();
  }

bool ValidateInputs()
  {
   if(_Symbol!="EURUSD" || _Period!=PERIOD_M5)
      return false;
   bool is_hyp006=(InpHypothesisId=="HYP-VRAS-EURUSD-M5-006");
   bool is_hyp007=(InpHypothesisId=="HYP-VRAS-EURUSD-M5-007");
   bool is_hyp008=(InpHypothesisId=="HYP-VRAS-EURUSD-M5-008");
   if(!is_hyp006 && !is_hyp007 && !is_hyp008)
      return false;
   if(InpDiagnosticDisableAccountDDEntryHalt && !MQLInfoInteger(MQL_TESTER))
      return false;
   if(is_hyp006)
     {
      if(InpMagic!=5600756 || InpDiagnosticDisableAccountDDEntryHalt ||
         MathAbs(InpRiskPercent-0.25)>1e-9)
         return false;
      if(InpUseVolatilityNormalizedStop)
        {
         if(InpVariantTag!="CHALLENGER_ATR_STRUCTURAL")
            return false;
        }
      else if(InpVariantTag!="CONTROL_FIXED_CLAMP")
         return false;
     }
   else if(is_hyp007)
     {
      if(InpMagic!=5600757 || !InpDiagnosticDisableAccountDDEntryHalt ||
         MathAbs(InpRiskPercent-0.05)>1e-9 ||
         MathAbs(InpMaxAccountDrawdownPct-6.0)>1e-9)
         return false;
      if(InpUseVolatilityNormalizedStop)
        {
         if(InpVariantTag!="CHALLENGER_ATR_STRUCTURAL_FULL_HORIZON")
            return false;
        }
      else if(InpVariantTag!="CONTROL_FIXED_CLAMP_FULL_HORIZON")
         return false;
     }
   else
     {
      if(InpMagic!=5600758 || !InpDiagnosticDisableAccountDDEntryHalt ||
         MathAbs(InpRiskPercent-0.01)>1e-9 ||
         MathAbs(InpMaxAccountDrawdownPct-6.0)>1e-9)
         return false;
      if(InpUseVolatilityNormalizedStop)
        {
         if(InpVariantTag!="CHALLENGER_ATR_STRUCTURAL_FULL_HORIZON_V2")
            return false;
        }
      else if(InpVariantTag!="CONTROL_FIXED_CLAMP_FULL_HORIZON_V2")
         return false;
     }
   if(InpH1EmaPeriod<2 || InpRollingVwapBars<2 || InpSwingLookbackBars<2 ||
      InpSlBufferPips<=0.0 || InpControlMinSlPips<=0.0 ||
      InpControlMaxSlPips<=InpControlMinSlPips || InpAtrPeriod<2 ||
      InpAtrFloorMultiple<=0.0 ||
      InpMaxStructuralAtrMultiple<=InpAtrFloorMultiple ||
      InpRiskRewardRatio<=0.0 || InpBreakEvenTriggerR<=0.0 ||
      InpBreakEvenOffsetPips<0.0 || InpRiskPercent<=0.0 ||
      InpRiskPercent>0.50 || InpMaxSpreadPips<=0.0 ||
      InpMaxTradesPerDay<1 || InpDailyLossPct<=0.0 ||
      InpMaxAccountDrawdownPct<=0.0 || InpMaxHoldBars<1 ||
      InpRequireNewsGuard)
      return false;
   return true;
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   g_h1_ema_handle=iMA(_Symbol,PERIOD_H1,InpH1EmaPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpAtrPeriod);
   if(g_h1_ema_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE)
      return INIT_FAILED;
   g_initial_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity=g_initial_equity;
   ResetRiskDayIfNeeded(TimeCurrent());
   g_last_m5_bar=0;
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("VRAS init hypothesis=%s variant=%s normalized_stop=%s account_dd_entry_halt_enabled=%s closed_bar=true promotion=false",
               InpHypothesisId,InpVariantTag,
               InpUseVolatilityNormalizedStop ? "true" : "false",
               InpDiagnosticDisableAccountDDEntryHalt ? "false" : "true");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   WriteRunMeta();
   if(g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileFlush(g_lifecycle_handle);
      FileClose(g_lifecycle_handle);
     }
   if(g_decision_handle!=INVALID_HANDLE)
     {
      FileFlush(g_decision_handle);
      FileClose(g_decision_handle);
     }
   if(g_h1_ema_handle!=INVALID_HANDLE)
      IndicatorRelease(g_h1_ema_handle);
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0)
      LogLifecycleDeal(trans.deal);
  }

void OnTick()
  {
   UpdateRiskState();
   ManageOwnedPosition();
   datetime current_bar=iTime(_Symbol,PERIOD_M5,0);
   if(current_bar<=0)
      return;
   if(current_bar==g_last_m5_bar)
     {
      return;
     }
   g_last_m5_bar=current_bar;
   g_bars_seen++;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,3,bars)!=3)
      return;
   double h1_close=0.0;
   double h1_ema=0.0;
   double atr=0.0;
   if(!ReadClosedIndicators(h1_close,h1_ema,atr))
      return;
   double vwap=CalculateRollingVwap();
   ENUM_VRAS_SIGNAL signal=EvaluateClosedBarSignal(bars,h1_close,h1_ema,vwap);
   if(signal==SIGNAL_NONE)
      return;
   g_signals++;
   TryOpenTrade((int)signal,h1_close,h1_ema,vwap,atr);
  }
