#ifndef SNR_EXECUTION_MQH
#define SNR_EXECUTION_MQH

#include <Trade/Trade.mqh>
#include "SNR_Types.mqh"

int SnrScanOwnedPosition(const long magic,ulong &ticket)
  {
   ticket=0;
   int owned=0;
   const int total=PositionsTotal();
   for(int i=total-1;i>=0;i--)
     {
      const ulong current=PositionGetTicket(i);
      if(current==0 || !PositionSelectByTicket(current) ||
         (ulong)PositionGetInteger(POSITION_TICKET)!=current)
         return(SNR_SCAN_FAIL);
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if((long)PositionGetInteger(POSITION_MAGIC)!=magic)
         continue;
      ticket=current;
      owned++;
     }
   if(owned>1)
      return(SNR_SCAN_MULTI);
   if(owned==1)
      return(SNR_SCAN_OWNED);
   return(SNR_SCAN_FLAT);
  }

int SnrScanSymbolPositions(int &count)
  {
   count=0;
   const int total=PositionsTotal();
   for(int i=total-1;i>=0;i--)
     {
      const ulong current=PositionGetTicket(i);
      if(current==0 || !PositionSelectByTicket(current) ||
         (ulong)PositionGetInteger(POSITION_TICKET)!=current)
         return(SNR_SCAN_FAIL);
      if(PositionGetString(POSITION_SYMBOL)==_Symbol)
         count++;
     }
   return(SNR_SCAN_FLAT);
  }

int SnrScanSymbolPendings(int &count)
  {
   count=0;
   const int total=OrdersTotal();
   for(int i=total-1;i>=0;i--)
     {
      const ulong current=OrderGetTicket(i);
      if(current==0 || (ulong)OrderGetInteger(ORDER_TICKET)!=current)
         return(SNR_SCAN_FAIL);
      if(OrderGetString(ORDER_SYMBOL)==_Symbol)
         count++;
     }
   return(SNR_SCAN_FLAT);
  }

bool SnrCloseOwned(CTrade &trade,const long magic,const int deviation,
                   const string reason,SnrTelemetry &tel)
  {
   ulong ticket=0;
   const int scan=SnrScanOwnedPosition(magic,ticket);
   if(scan==SNR_SCAN_FLAT)
      return(true);
   if(scan!=SNR_SCAN_OWNED || ticket==0)
      return(false);
   tel.close_attempts++;
   trade.SetExpertMagicNumber(magic);
   trade.SetDeviationInPoints(deviation);
   if(!trade.PositionClose(ticket,deviation))
     {
      tel.close_rejects++;
      PrintFormat("SNR001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",
                  reason,ticket,trade.ResultRetcode());
      return(false);
     }
   const uint retcode=trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
     {
      tel.close_rejects++;
      PrintFormat("SNR001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",
                  reason,ticket,retcode);
      return(false);
     }
   tel.closes++;
   PrintFormat("SNR001_CLOSE_REQUEST reason=%s ticket=%I64u retcode=%u",
               reason,ticket,retcode);
   return(true);
  }

int SnrScanOwnedPendings(const long magic,ulong &ticket,int &count)
  {
   ticket=0;
   count=0;
   const int total=OrdersTotal();
   for(int i=total-1;i>=0;i--)
     {
      const ulong current=OrderGetTicket(i);
      if(current==0 || (ulong)OrderGetInteger(ORDER_TICKET)!=current)
         return(SNR_SCAN_FAIL);
      if(OrderGetString(ORDER_SYMBOL)!=_Symbol)
         continue;
      if((long)OrderGetInteger(ORDER_MAGIC)!=magic)
         continue;
      ticket=current;
      count++;
     }
   if(count>1)
      return(SNR_SCAN_MULTI);
   if(count==1)
      return(SNR_SCAN_OWNED);
   return(SNR_SCAN_FLAT);
  }

bool SnrCancelOwnedPendings(CTrade &trade,const long magic,const string reason)
  {
   ulong ticket=0;
   int count=0;
   const int scan=SnrScanOwnedPendings(magic,ticket,count);
   if(scan==SNR_SCAN_FLAT)
      return(true);
   if(scan==SNR_SCAN_FAIL)
      return(false);
   bool ok=true;
   const int total=OrdersTotal();
   for(int i=total-1;i>=0;i--)
     {
      const ulong current=OrderGetTicket(i);
      if(current==0 || (ulong)OrderGetInteger(ORDER_TICKET)!=current)
         return(false);
      if(OrderGetString(ORDER_SYMBOL)!=_Symbol)
         continue;
      if((long)OrderGetInteger(ORDER_MAGIC)!=magic)
         continue;
      if(!trade.OrderDelete(current))
        {
         PrintFormat("SNR001_PENDING_CANCEL_REJECT reason=%s ticket=%I64u retcode=%u",
                     reason,current,trade.ResultRetcode());
         ok=false;
        }
     }
   return(ok);
  }

bool SnrSendStop(CTrade &trade,const long magic,const int deviation,
                 const int direction,const SnrRiskPlan &plan,
                 const bool hard_stops,const string comment,
                 uint &retcode)
  {
   retcode=0;
   if(!plan.valid || direction==SNR_DIR_NONE || plan.entry<=0.0)
      return(false);
   trade.SetExpertMagicNumber(magic);
   trade.SetDeviationInPoints(deviation);
   trade.SetTypeFillingBySymbol(_Symbol);
   const double sl=(hard_stops ? plan.sl : 0.0);
   const double tp=(hard_stops ? plan.tp : 0.0);
   bool sent=false;
   if(direction>0)
      sent=trade.BuyStop(plan.volume,plan.entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,comment);
   else
      sent=trade.SellStop(plan.volume,plan.entry,_Symbol,sl,tp,ORDER_TIME_GTC,0,comment);
   retcode=trade.ResultRetcode();
   return(sent && (retcode==TRADE_RETCODE_DONE || retcode==TRADE_RETCODE_DONE_PARTIAL ||
                   retcode==TRADE_RETCODE_PLACED));
  }

bool SnrSendMarket(CTrade &trade,const long magic,const int deviation,
                   const int direction,const SnrRiskPlan &plan,
                   const bool hard_stops,const string comment,
                   uint &retcode)
  {
   retcode=0;
   if(!plan.valid || direction==SNR_DIR_NONE)
      return(false);
   trade.SetExpertMagicNumber(magic);
   trade.SetDeviationInPoints(deviation);
   trade.SetTypeFillingBySymbol(_Symbol);
   const ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const double sl=(hard_stops ? plan.sl : 0.0);
   const double tp=(hard_stops ? plan.tp : 0.0);
   const bool sent=trade.PositionOpen(_Symbol,order_type,plan.volume,plan.entry,sl,tp,comment);
   retcode=trade.ResultRetcode();
   return(sent && (retcode==TRADE_RETCODE_DONE || retcode==TRADE_RETCODE_DONE_PARTIAL));
  }

bool SnrDealOwned(const ulong deal,const long magic)
  {
   if(deal==0 || !HistoryDealSelect(deal))
      return(false);
   return(HistoryDealGetString(deal,DEAL_SYMBOL)==_Symbol &&
          (long)HistoryDealGetInteger(deal,DEAL_MAGIC)==magic);
  }

#endif
