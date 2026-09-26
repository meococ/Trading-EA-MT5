//+------------------------------------------------------------------+
//|                                                   PA_Journal.mqh |
//|  PA-PRO EA lane - CSV journal, schema identical to the Python    |
//|  side so pa_fill.simulate / compare_parity.py can diff it.       |
//|                                                                  |
//|  Columns = lib/pa_fill.py:324-335 record keys, in order:         |
//|   sig,side,tag,symbol,status,order_type,fill_idx,fill,fill_raw,  |
//|   stop,sl,tp,exit_idx,exit_px,reason,r,bars_m1,gap_atr,          |
//|   cost_pips,cost_tier,exit_t,fill_t,sig_t                        |
//|                                                                  |
//|  SIGNAL_ONLY semantics: the EA emits plan-level rows -           |
//|   status: SIGNAL | VETO_FRIDAY | VETO_WEEKEND | VETO_SESSION |   |
//|           SPREAD | RISK_LOCK | NO_STOP | NO_PLAN                 |
//|   stop/sl/tp carry the planned order + bracket prices;           |
//|   fill_* / exit_* / r cells are left EMPTY (never simulated in   |
//|   the EA - M1-resolution fills belong to the Python comparator). |
//|                                                                  |
//|  No order, position or trade call exists in this header.         |
//+------------------------------------------------------------------+
#ifndef PA_JOURNAL_MQH
#define PA_JOURNAL_MQH

#include "PA_Types.mqh"
#include "PA_Session.mqh"
#include "PA_Trade.mqh"

#define PA_JNL_COLS "sig,side,tag,symbol,status,order_type,fill_idx,fill,fill_raw,stop,sl,tp,exit_idx,exit_px,reason,r,bars_m1,gap_atr,cost_pips,cost_tier,exit_t,fill_t,sig_t"

//+------------------------------------------------------------------+
//| CPaJournal - one CSV file under MQL5\Files\<folder>\             |
//+------------------------------------------------------------------+
class CPaJournal
  {
public:
   bool              on;
   int               fh;
   string            path;
   int               rows;

                     CPaJournal(void)
     {
      on=false; fh=INVALID_HANDLE; path=""; rows=0;
     }

   bool              Open(const string folder,const string fname)
     {
      if(fh!=INVALID_HANDLE)
         FileClose(fh);
      path=folder+"\\"+fname;
      fh=FileOpen(path,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
      if(fh==INVALID_HANDLE)
        {
         //--- fall back to the terminal-local Files folder
         fh=FileOpen(path,FILE_WRITE|FILE_TXT|FILE_ANSI);
        }
      if(fh==INVALID_HANDLE)
        {
         on=false;
         PrintFormat("PA-PRO journal: cannot open %s (err %d)",path,GetLastError());
         return(false);
        }
      FileWriteString(fh,PA_JNL_COLS+"\n");
      FileFlush(fh);
      on=true; rows=0;
      return(true);
     }

   void              Close(void)
     {
      if(fh!=INVALID_HANDLE)
        {
         FileClose(fh);
         fh=INVALID_HANDLE;
        }
      on=false;
     }

   //--- signal row: plan fields filled, fill/exit cells empty.
   //--- order_type: "stop" | "limit" | "market_next_open" | "" for vetoes
   void              Signal(const int sig_idx,const long sig_t,
                            const int side,const string tag,
                            const string symbol,const string status,
                            const string order_type,
                            const double stop,const double sl,const double tp,
                            const string reason)
     {
      if(!on || fh==INVALID_HANDLE)
         return;
      int dg=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
      string line=StringFormat("%d,%d,%s,%s,%s,%s,,,,%s,%s,%s,,,%s,,,,,,,%I64d",
                               sig_idx,side,tag,symbol,status,order_type,
                               (stop>0)?DoubleToString(stop,dg):"",
                               (sl>0)  ?DoubleToString(sl,dg)  :"",
                               (tp>0)  ?DoubleToString(tp,dg)  :"",
                               reason,sig_t);
      FileWriteString(fh,line+"\n");
      rows++;
      if((rows&63)==0)
         FileFlush(fh);                // flush every 64 rows
     }

   //--- convenience: journal a built plan (status = reason override)
   void              Plan(const int sig_idx,const PaPlan &p,
                          const string symbol,const string status)
     {
      string ot=(p.order_type==PA_ORD_STOP)?"stop":
                (p.order_type==PA_ORD_LIMIT)?"limit":"market_next_open";
      Signal(sig_idx,p.sig_t,p.side,p.setup,symbol,status,ot,
             p.entry,p.sl,p.tp,(status=="SIGNAL")?"":status);
     }

   void              Flush(void)
     {
      if(on && fh!=INVALID_HANDLE)
         FileFlush(fh);
     }
  };

#endif // PA_JOURNAL_MQH
