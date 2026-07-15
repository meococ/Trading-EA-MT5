//+------------------------------------------------------------------+
//| FVG_Execution.mqh — CTrade entry + 1R manage (BE / partial / trail)|
//+------------------------------------------------------------------+
#ifndef FVG_EXECUTION_MQH
#define FVG_EXECUTION_MQH

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include "FVG_Types.mqh"
#include "FVG_Risk.mqh"

struct SPosManage
{
   ulong  ticket;
   double initial_sl_dist;
   double entry;
   bool   partial_done;
   bool   be_done;
};

bool FVG_OpenTrade(CTrade &trade,
                   const bool is_buy,
                   const double lots,
                   double sl,
                   double tp,
                   const long magic,
                   const string comment,
                   const int deviation)
{
   if(lots <= 0.0 || sl <= 0.0)
      return false;

   trade.SetExpertMagicNumber(magic);
   trade.SetDeviationInPoints(deviation);
   trade.SetTypeFillingBySymbol(_Symbol);

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = is_buy ? ask : bid;

   if(!FVG_ValidateStops(is_buy, entry, sl, tp))
   {
      Print("FVG_Exec: stop validation failed entry=", entry, " sl=", sl, " tp=", tp);
      return false;
   }

   bool ok = false;
   if(is_buy)
      ok = trade.Buy(lots, _Symbol, entry, sl, tp, comment);
   else
      ok = trade.Sell(lots, _Symbol, entry, sl, tp, comment);

   if(!ok)
   {
      Print("FVG_Exec: order failed retcode=", trade.ResultRetcode(),
            " ", trade.ResultRetcodeDescription());
      return false;
   }
   uint rc = trade.ResultRetcode();
   if(rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED && rc != TRADE_RETCODE_DONE_PARTIAL)
   {
      Print("FVG_Exec: unexpected retcode=", rc, " ", trade.ResultRetcodeDescription());
      return false;
   }
   return true;
}

bool FVG_SelectOurPosition(CPositionInfo &pos, const long magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!pos.SelectByIndex(i))
         continue;
      if(pos.Symbol() != _Symbol)
         continue;
      if(pos.Magic() != magic)
         continue;
      return true;
   }
   return false;
}

void FVG_ManageOpen(CTrade &trade,
                    CPositionInfo &pos,
                    SPosManage &st,
                    const long magic,
                    const bool use_partial,
                    const double partial_pct,
                    const bool use_be,
                    const double be_trigger_r,
                    const bool use_trail,
                    const double trail_start_r,
                    const double trail_step_r)
{
   if(!FVG_SelectOurPosition(pos, magic))
   {
      st.ticket = 0;
      st.partial_done = false;
      st.be_done = false;
      st.initial_sl_dist = 0.0;
      return;
   }

   ulong ticket = pos.Ticket();
   if(st.ticket != ticket)
   {
      st.ticket = ticket;
      st.entry = pos.PriceOpen();
      st.partial_done = false;
      st.be_done = false;
      double sl0 = pos.StopLoss();
      st.initial_sl_dist = MathAbs(st.entry - sl0);
      if(st.initial_sl_dist <= 0.0)
         st.initial_sl_dist = MathAbs(st.entry - pos.PriceCurrent());
   }

   if(st.initial_sl_dist <= 0.0)
      return;

   bool is_buy = (pos.PositionType() == POSITION_TYPE_BUY);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double px = is_buy ? bid : ask;
   double favor = is_buy ? (px - st.entry) : (st.entry - px);
   double r_mult = favor / st.initial_sl_dist;

   // Partial close 50% at 1R
   if(use_partial && !st.partial_done && r_mult >= 1.0)
   {
      double vol = pos.Volume();
      double close_vol = FVG_NormalizeVolume(vol * partial_pct);
      double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      if(close_vol >= vmin && close_vol < vol)
      {
         trade.SetExpertMagicNumber(magic);
         if(trade.PositionClosePartial(ticket, close_vol))
         {
            st.partial_done = true;
            Print("FVG_Exec: partial close ", close_vol, " at ~1R ticket=", ticket);
         }
         else
            Print("FVG_Exec: partial failed ", trade.ResultRetcode(),
                  " ", trade.ResultRetcodeDescription());
      }
      else
         st.partial_done = true; // can't partial — mark done
   }

   // Move BE at 1R
   if(use_be && !st.be_done && r_mult >= be_trigger_r)
   {
      double be = FVG_NormalizePrice(st.entry);
      double cur_sl = pos.StopLoss();
      bool need = is_buy ? (cur_sl < be) : (cur_sl > be || cur_sl == 0.0);
      if(need)
      {
         trade.SetExpertMagicNumber(magic);
         double tp = pos.TakeProfit();
         if(trade.PositionModify(ticket, be, tp))
         {
            st.be_done = true;
            Print("FVG_Exec: BE moved ticket=", ticket);
         }
         else
            Print("FVG_Exec: BE modify failed ", trade.ResultRetcode());
      }
      else
         st.be_done = true;
   }

   // Trail remainder
   if(use_trail && r_mult >= trail_start_r && trail_step_r > 0.0)
   {
      double step = st.initial_sl_dist * trail_step_r;
      double cur_sl = pos.StopLoss();
      double new_sl = cur_sl;
      if(is_buy)
      {
         double cand = FVG_NormalizePrice(px - step);
         if(cand > cur_sl && cand < px)
            new_sl = cand;
      }
      else
      {
         double cand = FVG_NormalizePrice(px + step);
         if((cur_sl == 0.0 || cand < cur_sl) && cand > px)
            new_sl = cand;
      }
      if(new_sl != cur_sl && new_sl > 0.0)
      {
         trade.SetExpertMagicNumber(magic);
         if(!trade.PositionModify(ticket, new_sl, pos.TakeProfit()))
            Print("FVG_Exec: trail modify failed ", trade.ResultRetcode());
      }
   }
}

#endif
