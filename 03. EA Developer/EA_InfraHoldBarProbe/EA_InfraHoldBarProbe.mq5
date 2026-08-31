//+------------------------------------------------------------------+
//| EA_InfraHoldBarProbe.mq5                                         |
//| Infra SO probe: H1 same/hold-bar, M5 hold-1-bar, M5 cross-H1.    |
//| Not a strategy.                                                  |
//+------------------------------------------------------------------+
#property strict
#property version   "1.03"
#property description "Infra-only EURUSD SO probe (H1/M5). Not a strategy."

#include <Trade/Trade.mqh>

input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-INFRA-SAMEBAR-EURUSD-H1-001";
input long   InpMagic=16081602;
input double InpLot=0.01;
input int    InpHoldBars=0;
input bool   InpSameBarClose=true;
input bool   InpCrossH1Hold=false;
input int    InpDeviationPoints=20;
input int    InpFridayFlattenHour=20;

const string EA_NAME="EA_InfraHoldBarProbe";
const string EXPECTED_HOLDBAR="HYP-INFRA-HOLDBAR-EURUSD-H1-001";
const string EXPECTED_HOLDBAR_MQ="HYP-INFRA-HOLDBAR-EURUSD-H1-002";
const string EXPECTED_SAMEBAR="HYP-INFRA-SAMEBAR-EURUSD-H1-001";
const string EXPECTED_HOLDBAR_M5="HYP-INFRA-HOLDBAR-EURUSD-M5-001";
const string EXPECTED_CROSSH1_M5="HYP-INFRA-CROSSH1-EURUSD-M5-001";

CTrade g_trade;
datetime g_last_bar_open=0;
datetime g_entry_bar_open=0;
datetime g_entry_h1_open=0;
int g_held_closed_bars=0;
bool g_opened=false;
bool g_closed=false;
bool g_closed_same_bar=false;
bool g_runtime_failed=false;
long g_closed_bars=0;
long g_entries=0;
long g_entry_rejects=0;
long g_closes=0;
long g_close_rejects=0;

bool IsFinite(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

bool SymbolAllowed()
  {
   return(StringFind(_Symbol,"EURUSD")==0);
  }

bool CurrentBarOpen(datetime &bar_open)
  {
   bar_open=iTime(_Symbol,_Period,0);
   return(bar_open>0);
  }

bool FridayFlattenNow(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.day_of_week==5 && p.hour>=InpFridayFlattenHour);
  }

bool EntryWeekdayOk(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.day_of_week>=1 && p.day_of_week<=4);
  }

bool LastMinuteOfHour(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.min>=59);
  }

bool EntryMinuteCrossH1(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.min>=50 && p.min<=55);
  }

void PrintAccountState(const string tag)
  {
   PrintFormat("%s balance=%.2f equity=%.2f margin=%.2f free=%.2f level=%.2f so_mode=%d so_so=%.2f so_call=%.2f",
               tag,
               AccountInfoDouble(ACCOUNT_BALANCE),
               AccountInfoDouble(ACCOUNT_EQUITY),
               AccountInfoDouble(ACCOUNT_MARGIN),
               AccountInfoDouble(ACCOUNT_MARGIN_FREE),
               AccountInfoDouble(ACCOUNT_MARGIN_LEVEL),
               (int)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE),
               AccountInfoDouble(ACCOUNT_MARGIN_SO_SO),
               AccountInfoDouble(ACCOUNT_MARGIN_SO_CALL));
  }

bool ScanOwnedPosition(ulong &ticket,bool &found)
  {
   found=false;
   ticket=0;
   const int total=PositionsTotal();
   if(total<0)
      return(false);
   for(int i=0;i<total;i++)
     {
      const ulong candidate=PositionGetTicket(i);
      if(candidate==0 || !PositionSelectByTicket(candidate))
         return(false);
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         continue;
      if(found)
         return(false);
      found=true;
      ticket=candidate;
     }
   return(true);
  }

double NormalizeVolume(const double raw)
  {
   const double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(!IsFinite(vmin) || !IsFinite(vmax) || !IsFinite(step) || vmin<=0.0 || step<=0.0)
      return(0.0);
   double volume=MathFloor(raw/step)*step;
   if(volume<vmin)
      volume=vmin;
   if(volume>vmax)
      volume=vmax;
   const int digits=(step>=1.0 ? 0 : (int)MathRound(-MathLog10(step)));
   return(NormalizeDouble(volume,MathMax(digits,0)));
  }

bool SubmitBuy(const datetime bar_open)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !IsFinite(tick.ask) || !IsFinite(tick.bid) ||
      tick.ask<=tick.bid || tick.bid<=0.0)
      return(false);
   const double volume=NormalizeVolume(InpLot);
   if(volume<=0.0)
      return(false);
   double margin=0.0;
   if(!OrderCalcMargin(ORDER_TYPE_BUY,_Symbol,volume,tick.ask,margin) ||
      !IsFinite(margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     {
      g_entry_rejects++;
      PrintFormat("INFRA_HOLD_ENTRY_REJECT reason=MARGIN vol=%.2f ask=%.5f margin=%.2f",
                  volume,tick.ask,margin);
      return(false);
     }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,ORDER_TYPE_BUY,volume,tick.ask,0.0,0.0,"INFRA_PROBE");
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("INFRA_HOLD_ENTRY_REJECT vol=%.2f ask=%.5f retcode=%u",volume,tick.ask,retcode);
      return(false);
     }
   g_opened=true;
   g_entries++;
   g_entry_bar_open=bar_open;
   g_held_closed_bars=0;
   PrintFormat("INFRA_HOLD_ENTRY vol=%.2f price=%.5f retcode=%u",
               volume,(g_trade.ResultPrice()>0.0 ? g_trade.ResultPrice() : tick.ask),retcode);
   PrintAccountState("INFRA_HOLD_ENTRY_ACCT");
   return(true);
  }

bool CloseOwned(const string reason,const bool require_found)
  {
   ulong ticket=0;
   bool found=false;
   if(!ScanOwnedPosition(ticket,found))
     {
      g_runtime_failed=true;
      Print("INFRA_HOLD_FATAL reason=POSITION_SCAN");
      return(false);
     }
   if(!found)
     {
      if(require_found)
        {
         g_runtime_failed=true;
         PrintFormat("INFRA_HOLD_FATAL reason=CLOSE_NOT_FOUND want=%s",reason);
         return(false);
        }
      return(true);
     }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionClose(ticket);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_close_rejects++;
      PrintFormat("INFRA_HOLD_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u closed_same_bar=false",
                  reason,ticket,retcode);
      return(false);
     }
   g_closed=true;
   g_closes++;
   if(InpSameBarClose && StringFind(reason,"SAME_BAR")==0)
      g_closed_same_bar=true;
   PrintFormat("INFRA_HOLD_CLOSE reason=%s ticket=%I64u held_closed_bars=%d retcode=%u closed_same_bar=%s",
               reason,ticket,g_held_closed_bars,retcode,(g_closed_same_bar ? "true" : "false"));
   PrintAccountState("INFRA_HOLD_CLOSE_ACCT");
   return(true);
  }

void MarkVanished()
  {
   Print("INFRA_HOLD_VANISHED possible_so=true");
   PrintAccountState("INFRA_HOLD_VANISHED_ACCT");
   g_closed=true;
  }

int OnInit()
  {
   if(!SymbolAllowed() || InpLot<=0.0)
      return(INIT_PARAMETERS_INCORRECT);
   if(InpSameBarClose)
     {
      if(_Period!=PERIOD_H1 || InpHypothesisId!=EXPECTED_SAMEBAR ||
         InpHoldBars!=0 || InpCrossH1Hold)
         return(INIT_PARAMETERS_INCORRECT);
     }
   else if(InpCrossH1Hold)
     {
      if(_Period!=PERIOD_M5 || InpHypothesisId!=EXPECTED_CROSSH1_M5 ||
         InpHoldBars!=0)
         return(INIT_PARAMETERS_INCORRECT);
     }
   else if(InpHypothesisId==EXPECTED_HOLDBAR || InpHypothesisId==EXPECTED_HOLDBAR_MQ)
     {
      if(_Period!=PERIOD_H1 || InpHoldBars<1)
         return(INIT_PARAMETERS_INCORRECT);
     }
   else if(InpHypothesisId==EXPECTED_HOLDBAR_M5)
     {
      if(_Period!=PERIOD_M5 || InpHoldBars!=1)
         return(INIT_PARAMETERS_INCORRECT);
     }
   else
      return(INIT_PARAMETERS_INCORRECT);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0)
      return(INIT_FAILED);
   PrintFormat("INFRA_HOLD_INIT ea=%s hyp=%s symbol=%s tf=%s lot=%.2f hold_bars=%d same_bar_close=%s cross_h1=%s",
               EA_NAME,InpHypothesisId,_Symbol,EnumToString(_Period),InpLot,InpHoldBars,
               (InpSameBarClose ? "true" : "false"),(InpCrossH1Hold ? "true" : "false"));
   PrintAccountState("INFRA_HOLD_INIT_ACCT");
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   PrintFormat("INFRA_HOLD_SUMMARY reason=%d failed=%s closed_bars=%I64d entries=%I64d entry_rej=%I64d closes=%I64d close_rej=%I64d held=%d closed_same_bar=%s",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,g_entries,
               g_entry_rejects,g_closes,g_close_rejects,g_held_closed_bars,
               (g_closed_same_bar ? "true" : "false"));
   PrintAccountState("INFRA_HOLD_DEINIT_ACCT");
  }

void OnTick()
  {
   datetime current_bar_open=0;
   if(!CurrentBarOpen(current_bar_open) || current_bar_open<=0)
      return;
   const datetime server_now=TimeCurrent();
   ulong ticket=0;
   bool found=false;
   if(!ScanOwnedPosition(ticket,found))
     {
      g_runtime_failed=true;
      return;
     }
   if(InpSameBarClose)
     {
      if(found)
        {
         if(g_entry_bar_open>0 && current_bar_open!=g_entry_bar_open)
           {
            g_runtime_failed=true;
            CloseOwned("LEAKED_NEW_BAR",true);
            return;
           }
         CloseOwned("SAME_BAR",true);
         return;
        }
      if(g_opened && !g_closed)
        {
         MarkVanished();
         return;
        }
      if(g_runtime_failed || g_opened || g_closed)
         return;
      if(current_bar_open==g_last_bar_open)
         return;
      g_last_bar_open=current_bar_open;
      g_closed_bars++;
      if(iTime(_Symbol,_Period,1)<=0)
         return;
      if(!EntryWeekdayOk(current_bar_open) || FridayFlattenNow(server_now))
         return;
      if(!SubmitBuy(current_bar_open))
         return;
      if(LastMinuteOfHour(server_now))
        {
         if(!CloseOwned("SAME_BAR_LAST_MINUTE",true))
            g_runtime_failed=true;
         return;
        }
      return;
     }
   if(InpCrossH1Hold)
     {
      if(found && FridayFlattenNow(server_now))
         CloseOwned("FRIDAY_FLAT",false);
      if(found)
        {
         const datetime h1_open=iTime(_Symbol,PERIOD_H1,0);
         if(g_entry_h1_open>0 && h1_open>0 && h1_open!=g_entry_h1_open)
           {
            g_held_closed_bars++;
            PrintFormat("INFRA_HOLD_CROSS_H1 held_closed_bars=%d ticket=%I64u",g_held_closed_bars,ticket);
            PrintAccountState("INFRA_HOLD_CROSS_H1_ACCT");
            CloseOwned("CROSS_H1",true);
           }
         return;
        }
      if(g_opened && !g_closed)
        {
         MarkVanished();
         return;
        }
      if(g_runtime_failed || g_opened || g_closed)
         return;
      if(iTime(_Symbol,PERIOD_H1,0)<=0 || iTime(_Symbol,PERIOD_H1,1)<=0 ||
         iTime(_Symbol,PERIOD_M5,1)<=0)
         return;
      if(!EntryWeekdayOk(server_now) || FridayFlattenNow(server_now))
         return;
      if(!EntryMinuteCrossH1(server_now))
         return;
      if(!SubmitBuy(current_bar_open))
         return;
      g_entry_h1_open=iTime(_Symbol,PERIOD_H1,0);
      return;
     }
   if(found && FridayFlattenNow(server_now))
      CloseOwned("FRIDAY_FLAT",false);
   if(current_bar_open==g_last_bar_open)
      return;
   g_last_bar_open=current_bar_open;
   g_closed_bars++;
   if(found)
     {
      g_held_closed_bars++;
      PrintFormat("INFRA_HOLD_BAR held_closed_bars=%d ticket=%I64u",g_held_closed_bars,ticket);
      PrintAccountState("INFRA_HOLD_BAR_ACCT");
      if(g_held_closed_bars>=InpHoldBars)
         CloseOwned("TIME_STOP",true);
      return;
     }
   if(g_opened && !g_closed)
     {
      MarkVanished();
      return;
     }
   if(g_runtime_failed || g_opened || g_closed)
      return;
   if(iTime(_Symbol,_Period,1)<=0)
      return;
   if(!EntryWeekdayOk(current_bar_open) || FridayFlattenNow(server_now))
      return;
   SubmitBuy(current_bar_open);
  }
//+------------------------------------------------------------------+
