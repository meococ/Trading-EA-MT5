//+------------------------------------------------------------------+
//| AF_ExecutionKernel.mqh                                           |
//| One in-flight async market request per symbol/magic/strategy.    |
//| Callback order is not assumed; active-operation deals are deduped.|
//+------------------------------------------------------------------+
#ifndef ALPHAFACTORY_EXECUTION_KERNEL_MQH
#define ALPHAFACTORY_EXECUTION_KERNEL_MQH

// Deliberate compile-time interlock.  This shared kernel has compile evidence
// only; an adopting EA must explicitly opt into experimental mutation.
#ifndef AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED
#define AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED 0
#endif

enum AF_EXEC_STATE
  {
   AF_EXEC_IDLE=0,
   AF_EXEC_PENDING_NEW=1,
   AF_EXEC_ORDER_PLACED=2,
   AF_EXEC_PARTIALLY_FILLED=3,
   AF_EXEC_FILLED=4,
   AF_EXEC_REJECTED=5,
   AF_EXEC_RECOVERING_AMBIGUOUS=6
  };

class CAFExecutionKernel
  {
private:
   string            m_symbol;
   string            m_strategy_id;
   ulong             m_magic;
   AF_EXEC_STATE      m_state;
   uint               m_request_id;
   ulong              m_order_ticket;
   ulong              m_position_identifier;
   double             m_requested_volume;
   double             m_filled_volume;
   uint               m_last_retcode;
   ulong              m_send_tick_ms;
   long               m_send_time_msc;
   ENUM_ORDER_TYPE    m_order_type;
   string             m_active_comment;
   ulong              m_seen_deals[];

   bool IsAcceptedRetcode(const uint retcode)
     {
      return(retcode==TRADE_RETCODE_PLACED ||
             retcode==TRADE_RETCODE_DONE ||
             retcode==TRADE_RETCODE_DONE_PARTIAL);
     }

   bool CommentMatches(const string comment)
     {
      if(StringLen(m_strategy_id)==0)
         return(true);
      return(comment==m_strategy_id || StringFind(comment,m_strategy_id+"-")==0);
     }

   bool IsSelectedOrderOwned()
     {
      if(OrderGetString(ORDER_SYMBOL)!=m_symbol)
         return(false);
      if((ulong)OrderGetInteger(ORDER_MAGIC)!=m_magic)
         return(false);
      return(CommentMatches(OrderGetString(ORDER_COMMENT)));
     }

   bool IsSelectedPositionOwned()
     {
      if(PositionGetString(POSITION_SYMBOL)!=m_symbol)
         return(false);
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=m_magic)
         return(false);
      return(CommentMatches(PositionGetString(POSITION_COMMENT)));
     }

   bool IsSelectedDealOwned(const ulong deal_ticket)
     {
      if(HistoryDealGetString(deal_ticket,DEAL_SYMBOL)!=m_symbol)
         return(false);
      if((ulong)HistoryDealGetInteger(deal_ticket,DEAL_MAGIC)!=m_magic)
         return(false);
      return(CommentMatches(HistoryDealGetString(deal_ticket,DEAL_COMMENT)));
     }

   bool ActiveCommentMatches(const string comment)
     {
      return(StringLen(m_active_comment)>0 && comment==m_active_comment);
     }

   bool DealWasSeen(const ulong deal_ticket)
     {
      const int count=ArraySize(m_seen_deals);
      for(int i=0;i<count;i++)
        {
         if(m_seen_deals[i]==deal_ticket)
            return(true);
        }
      return(false);
     }

   void RememberDeal(const ulong deal_ticket)
     {
      if(DealWasSeen(deal_ticket))
         return;
      const int old_size=ArraySize(m_seen_deals);
      ArrayResize(m_seen_deals,old_size+1);
      m_seen_deals[old_size]=deal_ticket;
     }

   bool ResolveFillingMode(ENUM_ORDER_TYPE_FILLING &mode)
     {
      long filling=0;
      if(!SymbolInfoInteger(m_symbol,SYMBOL_FILLING_MODE,filling))
         return(false);
      if((filling & SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
        {
         mode=ORDER_FILLING_IOC;
         return(true);
        }
      if((filling & SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
        {
         mode=ORDER_FILLING_FOK;
         return(true);
        }
      return(false);
     }

   void ApplyDeal(const ulong deal_ticket)
     {
      if(deal_ticket==0 || DealWasSeen(deal_ticket))
         return;
      if(m_state!=AF_EXEC_PENDING_NEW && m_state!=AF_EXEC_ORDER_PLACED &&
         m_state!=AF_EXEC_PARTIALLY_FILLED &&
         !(m_state==AF_EXEC_RECOVERING_AMBIGUOUS && m_requested_volume>0.0 &&
           StringLen(m_active_comment)>0))
         return;
      if(!HistoryDealSelect(deal_ticket))
        {
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return;
        }
      if(!IsSelectedDealOwned(deal_ticket))
         return;
      if(!ActiveCommentMatches(HistoryDealGetString(deal_ticket,DEAL_COMMENT)))
        {
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return;
        }
      const ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal_ticket,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_INOUT)
        {
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return;
        }
      if(entry!=DEAL_ENTRY_IN)
         return;
      const ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal_ticket,DEAL_TYPE);
      if((m_order_type==ORDER_TYPE_BUY && deal_type!=DEAL_TYPE_BUY) ||
         (m_order_type==ORDER_TYPE_SELL && deal_type!=DEAL_TYPE_SELL))
        {
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return;
        }
      const ulong deal_order=(ulong)HistoryDealGetInteger(deal_ticket,DEAL_ORDER);
      if(m_order_ticket!=0 && deal_order!=m_order_ticket)
        {
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return;
        }
      if(m_order_ticket==0)
         m_order_ticket=deal_order;
      const long deal_time_msc=(long)HistoryDealGetInteger(deal_ticket,DEAL_TIME_MSC);
      if(m_send_time_msc>0 && deal_time_msc<m_send_time_msc)
        {
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return;
        }
      const double volume=HistoryDealGetDouble(deal_ticket,DEAL_VOLUME);
      if(volume<=0.0)
        {
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return;
        }
      RememberDeal(deal_ticket);
      m_filled_volume+=volume;
      const double volume_step=MathMax(SymbolInfoDouble(m_symbol,SYMBOL_VOLUME_STEP),0.00000001);
      if(m_filled_volume+volume_step*0.5>=m_requested_volume)
         m_state=AF_EXEC_FILLED;
      else
         m_state=AF_EXEC_PARTIALLY_FILLED;
     }

public:
                     CAFExecutionKernel()
     {
      m_symbol="";
      m_strategy_id="";
      m_magic=0;
      m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
      m_request_id=0;
      m_order_ticket=0;
      m_position_identifier=0;
      m_requested_volume=0.0;
      m_filled_volume=0.0;
      m_last_retcode=0;
      m_send_tick_ms=0;
      m_send_time_msc=0;
      m_order_type=(ENUM_ORDER_TYPE)-1;
      m_active_comment="";
      ArrayResize(m_seen_deals,0);
     }

   bool Configure(const string symbol,const ulong magic,const string strategy_id)
     {
      if(StringLen(symbol)==0 || magic==0 || StringLen(strategy_id)==0 || StringLen(strategy_id)>16)
         return(false);
      m_symbol=symbol;
      m_magic=magic;
      m_strategy_id=strategy_id;
      m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
      return(true);
     }

   AF_EXEC_STATE State()
     {
      return(m_state);
     }

   uint RequestId()
     {
      return(m_request_id);
     }

   ulong OrderTicket()
     {
      return(m_order_ticket);
     }

   double RequestedVolume()
     {
      return(m_requested_volume);
     }

   double FilledVolume()
     {
      return(m_filled_volume);
     }

   uint LastRetcode()
     {
      return(m_last_retcode);
     }

   bool TimedOut(const ulong timeout_ms)
     {
      if(m_state!=AF_EXEC_PENDING_NEW && m_state!=AF_EXEC_ORDER_PLACED &&
         m_state!=AF_EXEC_PARTIALLY_FILLED)
         return(false);
      return(GetTickCount64()-m_send_tick_ms>timeout_ms);
     }

   bool SubmitMarket(const ENUM_ORDER_TYPE order_type,
                     const double volume,
                     const double stop_loss,
                     const double take_profit,
                     const ulong deviation_points)
     {
      if(m_state!=AF_EXEC_IDLE)
         return(false);
      if(AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED==0)
        {
         m_state=AF_EXEC_REJECTED;
         return(false);
        }
      if(order_type!=ORDER_TYPE_BUY && order_type!=ORDER_TYPE_SELL)
         return(false);
      if(volume<=0.0)
         return(false);

      MqlTick tick;
      if(!SymbolInfoTick(m_symbol,tick))
         return(false);

      const ENUM_ACCOUNT_MARGIN_MODE margin_mode=
         (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
      if(margin_mode==ACCOUNT_MARGIN_MODE_RETAIL_NETTING ||
         margin_mode==ACCOUNT_MARGIN_MODE_EXCHANGE)
        {
         for(int i=0;i<PositionsTotal();i++)
           {
            const ulong existing_ticket=PositionGetTicket(i);
            if(existing_ticket==0)
              {
               m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
               return(false);
              }
            if(PositionGetString(POSITION_SYMBOL)==m_symbol)
              {
               m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
               return(false);
              }
           }
        }

      MqlTradeRequest request;
      MqlTradeCheckResult check;
      MqlTradeResult result;
      ZeroMemory(request);
      ZeroMemory(check);
      ZeroMemory(result);
      request.action=TRADE_ACTION_DEAL;
      request.symbol=m_symbol;
      request.magic=m_magic;
      request.volume=volume;
      request.type=order_type;
      request.price=(order_type==ORDER_TYPE_BUY ? tick.ask : tick.bid);
      request.sl=stop_loss;
      request.tp=take_profit;
      request.deviation=deviation_points;
      ENUM_ORDER_TYPE_FILLING filling_mode;
      if(!ResolveFillingMode(filling_mode))
        {
         m_state=AF_EXEC_REJECTED;
         return(false);
        }
      request.type_filling=filling_mode;
      request.type_time=ORDER_TIME_GTC;
      m_active_comment=StringFormat("%s-%08u",m_strategy_id,
                                    (uint)(GetTickCount64()%100000000));
      request.comment=m_active_comment;

      // MqlTradeCheckResult uses 0 for a successful check; 10009 belongs to
      // MqlTradeResult and must not be reused here.
      if(!OrderCheck(request,check) || check.retcode!=0)
        {
         m_last_retcode=check.retcode;
         m_state=AF_EXEC_REJECTED;
         return(false);
        }

      // Intent is visible before the async request can produce transactions.
      m_state=AF_EXEC_PENDING_NEW;
      m_request_id=0;
      m_order_ticket=0;
      m_position_identifier=0;
      m_requested_volume=volume;
      m_filled_volume=0.0;
      m_last_retcode=0;
      m_send_tick_ms=GetTickCount64();
      m_send_time_msc=(long)TimeTradeServer()*1000;
      m_order_type=order_type;
      ArrayResize(m_seen_deals,0);

      if(!OrderSendAsync(request,result))
        {
         m_last_retcode=result.retcode;
         m_state=AF_EXEC_REJECTED;
         return(false);
        }
      m_request_id=result.request_id;
      m_last_retcode=result.retcode;
      if(result.order>0)
        {
         m_order_ticket=result.order;
         m_state=AF_EXEC_ORDER_PLACED;
        }
      if(!IsAcceptedRetcode(result.retcode))
        {
         m_state=AF_EXEC_REJECTED;
         return(false);
        }
      return(true);
     }

   // Call directly from the EA's global OnTradeTransaction handler.
   void OnTradeTransaction(const MqlTradeTransaction &trans,
                           const MqlTradeRequest &request,
                           const MqlTradeResult &result)
     {
      if(trans.type==TRADE_TRANSACTION_REQUEST)
        {
         if(request.symbol!=m_symbol || request.magic!=m_magic)
            return;
         if(!ActiveCommentMatches(request.comment))
            return;
         if(m_request_id!=0 && result.request_id!=0 && result.request_id!=m_request_id)
            return;
         if(result.request_id!=0)
            m_request_id=result.request_id;
         m_last_retcode=result.retcode;
         if(result.order>0)
            m_order_ticket=result.order;
         if(!IsAcceptedRetcode(result.retcode))
           {
            if(m_state==AF_EXEC_FILLED)
               return;
            m_state=(m_filled_volume>0.0 ? AF_EXEC_RECOVERING_AMBIGUOUS : AF_EXEC_REJECTED);
           }
         else if(m_state==AF_EXEC_PENDING_NEW && m_order_ticket>0)
            m_state=AF_EXEC_ORDER_PLACED;
         return;
        }

      if(trans.type==TRADE_TRANSACTION_ORDER_ADD ||
         trans.type==TRADE_TRANSACTION_ORDER_UPDATE)
        {
         if(trans.order==0 || !OrderSelect(trans.order) || !IsSelectedOrderOwned() ||
            !ActiveCommentMatches(OrderGetString(ORDER_COMMENT)))
            return;
         m_order_ticket=trans.order;
         if(m_state==AF_EXEC_PENDING_NEW)
            m_state=AF_EXEC_ORDER_PLACED;
         return;
        }

      if(trans.type==TRADE_TRANSACTION_DEAL_ADD)
        {
         ApplyDeal(trans.deal);
         return;
        }

      if(trans.type==TRADE_TRANSACTION_ORDER_DELETE && trans.order==m_order_ticket)
        {
         // Do not infer rejection: deal and delete callbacks may arrive in any order.
         m_order_ticket=0;
        }
     }

   // Bounded timer/startup reconciliation. Never auto-resends after timeout.
   bool Reconcile()
     {
      const AF_EXEC_STATE prior_state=m_state;
      int owned_orders=0;
      int owned_positions=0;
      bool identity_collision=false;
      ulong recovered_order=0;
      ulong recovered_position=0;

      for(int i=0;i<OrdersTotal();i++)
        {
         const ulong ticket=OrderGetTicket(i);
         if(ticket==0)
           {
            m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
            return(false);
           }
         if(OrderGetString(ORDER_SYMBOL)==m_symbol &&
            (ulong)OrderGetInteger(ORDER_MAGIC)==m_magic)
           {
            const string order_comment=OrderGetString(ORDER_COMMENT);
            if(!CommentMatches(order_comment) ||
               (StringLen(m_active_comment)>0 && !ActiveCommentMatches(order_comment)))
               identity_collision=true;
            else
              {
               owned_orders++;
               recovered_order=ticket;
              }
           }
         else if(IsSelectedOrderOwned())
           {
            owned_orders++;
            recovered_order=ticket;
           }
        }
      for(int i=0;i<PositionsTotal();i++)
        {
         const ulong ticket=PositionGetTicket(i);
         if(ticket==0)
           {
            m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
            return(false);
           }
         const ENUM_ACCOUNT_MARGIN_MODE margin_mode=
            (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
         const bool netting=(margin_mode==ACCOUNT_MARGIN_MODE_RETAIL_NETTING ||
                             margin_mode==ACCOUNT_MARGIN_MODE_EXCHANGE);
         if(netting && PositionGetString(POSITION_SYMBOL)==m_symbol &&
            !IsSelectedPositionOwned())
            identity_collision=true;
         else if(PositionGetString(POSITION_SYMBOL)==m_symbol &&
                 (ulong)PositionGetInteger(POSITION_MAGIC)==m_magic)
           {
            const string position_comment=PositionGetString(POSITION_COMMENT);
            if(!CommentMatches(position_comment) ||
               (StringLen(m_active_comment)>0 && !ActiveCommentMatches(position_comment)))
               identity_collision=true;
            else
              {
               owned_positions++;
               recovered_position=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
              }
           }
         else if(IsSelectedPositionOwned())
           {
            owned_positions++;
            recovered_position=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
           }
        }

      if(identity_collision || owned_orders>1 || owned_positions>1)
        {
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return(false);
        }
      if(owned_positions==1)
        {
         if(m_requested_volume<=0.0 || StringLen(m_active_comment)==0)
           {
            m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
            return(false);
           }
         if(m_filled_volume<=0.0)
           {
            // A live position without a correlated deal set is not enough to
            // claim FILLED or reconstruct idempotent partial-fill volume.
            m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
            return(false);
           }
         m_position_identifier=recovered_position;
         m_order_ticket=(owned_orders==1 ? recovered_order : 0);
         m_state=(owned_orders==1 ? AF_EXEC_PARTIALLY_FILLED : AF_EXEC_FILLED);
         return(true);
        }
      if(owned_orders==1)
        {
         if(m_requested_volume<=0.0 || StringLen(m_active_comment)==0)
           {
            m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
            return(false);
           }
         m_order_ticket=recovered_order;
         m_state=AF_EXEC_ORDER_PLACED;
         return(true);
        }

      if(prior_state==AF_EXEC_PENDING_NEW || prior_state==AF_EXEC_ORDER_PLACED ||
         prior_state==AF_EXEC_PARTIALLY_FILLED || prior_state==AF_EXEC_FILLED)
        {
         // An empty live scan cannot prove an async request's terminal outcome.
         m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
         return(false);
        }

      // Only a clean startup scan with no unresolved intent can reach IDLE.
      m_order_ticket=0;
      m_position_identifier=0;
      if(m_requested_volume==0.0 && ArraySize(m_seen_deals)==0)
        {
         m_state=AF_EXEC_IDLE;
         return(true);
        }
      m_state=AF_EXEC_RECOVERING_AMBIGUOUS;
      return(false);
     }
  };

#endif
