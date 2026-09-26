//+------------------------------------------------------------------+
//|                                                     PA_Trade.mqh |
//|  PA-PRO EA lane - order plan + the single gated execution fn.    |
//|                                                                  |
//|  Semantics ported from lib/pa_fill.py DEFAULT_SPEC:              |
//|   - order_type "stop": entry = signal-bar extreme + buf_pips     |
//|     (BUY stop = h + buf, SELL stop = l - buf);                   |
//|   - expiry: v_bars M5 bars (session_cancel truncates at the      |
//|     session end - CPaSession supplies the vetoes);               |
//|   - SL at structure: zone far edge + sl_pad_pips; fallback       |
//|     S_pips; TP = tp_mult x SL distance;                          |
//|   - optional break-even after be_move_pips;                      |
//|   - spread guard: skip when spread > max_spread_pips.            |
//|                                                                  |
//|  HARD WALL: every order API in the EA lives inside               |
//|  PaExecutePlan(), whose FIRST statement is the SIGNAL_ONLY gate. |
//|  mql5/tests/test_signal_only.py greps this file to prove it.     |
//+------------------------------------------------------------------+
#ifndef PA_TRADE_MQH
#define PA_TRADE_MQH

#include "PA_Types.mqh"
#include "PA_Session.mqh"

enum ENUM_PA_ORD
  {
   PA_ORD_STOP = 0,        // stop entry beyond the signal bar
   PA_ORD_LIMIT,           // limit entry at order_px
   PA_ORD_MKT              // market at next bar open
  };

struct PaPlan
  {
   bool              ok;
   int               side;         // +1 / -1
   int               order_type;
   double            entry;
   double            sl;
   double            tp;
   double            lots;
   int               expire_bars;
   long              sig_t;
   int               sig_idx;
   int               veto;         // ENUM_PA_VETO
   double            inv_px;       // invalidation level (optional)
   bool              inv_on;
   int               zone_zid;
   string            setup;        // setup module tag
   string            reason;       // journal note
  };

void PaPlanClear(PaPlan &p)
  {
   p.ok=false; p.side=0; p.order_type=PA_ORD_STOP;
   p.entry=0; p.sl=0; p.tp=0; p.lots=0; p.expire_bars=0;
   p.sig_t=0; p.sig_idx=-1; p.veto=PA_VETO_NONE;
   p.inv_px=0; p.inv_on=false; p.zone_zid=0; p.setup=""; p.reason="";
  }

//+------------------------------------------------------------------+
//| CPaTrade - plan builder knobs                                    |
//+------------------------------------------------------------------+
class CPaTrade
  {
public:
   double            pip;
   double            buf_pips;       // 1.0
   int               v_bars;         // 3
   double            s_pips;         // 8.0 fallback SL
   double            tp_mult;        // 2.0
   double            sl_pad_pips;    // structural SL padding
   double            max_spread_pips;// spread guard (0 = off)
   double            be_move_pips;   // break-even trigger (0 = off)

                     CPaTrade(void)
     {
      pip=0.0001;
      buf_pips=PA_ORD_BUF_PIPS;
      v_bars=PA_ORD_V_BARS;
      s_pips=PA_ORD_S_PIPS;
      tp_mult=PA_ORD_TP_MULT;
      sl_pad_pips=0.5;
      max_spread_pips=3.0;
      be_move_pips=0.0;
     }

   //--- Volman stop-entry plan (pa_fill.py:217-235 shape).
   //--- zone_lo/zone_hi: the armed zone traded; use zone_hi (far edge for a
   //--- buy's SL sits below the zone) as the structural stop reference.
   //--- spread_pips: live spread for the guard.
   bool BuildStop(const PaBar &sig,const int sig_idx,const int side,
                  const double zone_lo,const double zone_hi,
                  const int zone_zid,const string setup,
                  const double spread_pips,PaPlan &p) const
     {
      PaPlanClear(p);
      p.sig_t=sig.t; p.sig_idx=sig_idx; p.side=side;
      p.order_type=PA_ORD_STOP; p.setup=setup; p.zone_zid=zone_zid;
      p.expire_bars=v_bars;
      if(side!=1 && side!=-1)
        {
         p.reason="BAD_SIDE";
         return(false);
        }
      if(max_spread_pips>0.0 && spread_pips>max_spread_pips)
        {
         p.reason="SPREAD";
         return(false);
        }
      double buf=buf_pips*pip;
      double sl_pad=sl_pad_pips*pip;
      if(side>0)
        {
         p.entry=sig.h+buf;
         p.sl=(zone_lo>0.0) ? zone_lo-sl_pad : p.entry-s_pips*pip;
        }
      else
        {
         p.entry=sig.l-buf;
         p.sl=(zone_hi>0.0) ? zone_hi+sl_pad : p.entry+s_pips*pip;
        }
      double sl_d=MathAbs(p.entry-p.sl);
      if(sl_d<=0.0)
        {
         p.reason="NO_STOP";
         return(false);
        }
      p.tp=(side>0) ? p.entry+tp_mult*sl_d : p.entry-tp_mult*sl_d;
      p.ok=true;
      p.reason="OK";
      return(true);
     }

   //--- next-open market plan
   bool BuildMarket(const PaBar &next_bar,const int sig_idx,const int side,
                    const double zone_lo,const double zone_hi,
                    const int zone_zid,const string setup,
                    const double spread_pips,PaPlan &p) const
     {
      PaPlanClear(p);
      p.sig_t=next_bar.t; p.sig_idx=sig_idx; p.side=side;
      p.order_type=PA_ORD_MKT; p.setup=setup; p.zone_zid=zone_zid;
      p.expire_bars=0;
      if(max_spread_pips>0.0 && spread_pips>max_spread_pips)
        {
         p.reason="SPREAD";
         return(false);
        }
      double sl_pad=sl_pad_pips*pip;
      p.entry=next_bar.o;
      if(side>0)
         p.sl=(zone_lo>0.0) ? zone_lo-sl_pad : p.entry-s_pips*pip;
      else
         p.sl=(zone_hi>0.0) ? zone_hi+sl_pad : p.entry+s_pips*pip;
      double sl_d=MathAbs(p.entry-p.sl);
      if(sl_d<=0.0)
        {
         p.reason="NO_STOP";
         return(false);
        }
      p.tp=(side>0) ? p.entry+tp_mult*sl_d : p.entry-tp_mult*sl_d;
      p.ok=true; p.reason="OK";
      return(true);
     }
  };

//+------------------------------------------------------------------+
//| PaExecutePlan - THE ONLY function that may touch an order API.   |
//| The SIGNAL_ONLY gate is the first statement; mql5/tests/         |
//| test_signal_only.py asserts every order-API token in this file   |
//| sits inside this function body and behind this gate.             |
//+------------------------------------------------------------------+
bool PaExecutePlan(const PaPlan &p,const bool signal_only,
                   const string sym,const string comment)
  {
   if(signal_only)
      return(false);                  // HARD WALL: never reachable to orders
   if(!p.ok)
      return(false);
   //--- Owner-only path.  Kept minimal and explicit: pending stop/limit
   //--- order with expiry v_bars later; market order at the next open.
   //--- (CTrade intentionally NOT used - raw MqlTradeRequest keeps the
   //--- audit surface small and grep-able.)
   MqlTradeRequest req;
   MqlTradeResult  res;
   ZeroMemory(req);
   ZeroMemory(res);
   req.symbol=sym;
   req.volume=p.lots;
   req.deviation=8;
   req.comment=comment;
   req.magic=20260921;
   if(p.order_type==PA_ORD_MKT)
     {
      req.action=TRADE_ACTION_DEAL;
      req.type=(p.side>0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      req.price=(p.side>0) ? SymbolInfoDouble(sym,SYMBOL_ASK)
                         : SymbolInfoDouble(sym,SYMBOL_BID);
     }
   else
     {
      req.action=TRADE_ACTION_PENDING;
      if(p.order_type==PA_ORD_STOP)
         req.type=(p.side>0) ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
      else
         req.type=(p.side>0) ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
      req.price=p.entry;
      req.expiration=(datetime)(p.sig_t+p.expire_bars*300);
      req.type_time=ORDER_TIME_SPECIFIED;
     }
   req.sl=p.sl;
   req.tp=p.tp;
   return(OrderSend(req,res) && (res.retcode==TRADE_RETCODE_DONE ||
                                 res.retcode==TRADE_RETCODE_PLACED));
  }

#endif // PA_TRADE_MQH
