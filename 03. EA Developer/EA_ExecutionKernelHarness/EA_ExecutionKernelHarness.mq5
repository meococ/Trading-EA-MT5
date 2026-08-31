#property strict
#property version   "1.00"
#property description "Compile/runtime harness for the AlphaFactory async execution kernel"

#include "..\_Shared\Execution\AF_ExecutionKernel.mqh"
#include "..\_Shared\MarketData\AF_TickCursor.mqh"

input bool  InpAllowOrderMutation=false;
input ulong InpMagic=82602001;
input string InpStrategyId="AFExecHarness";

CAFExecutionKernel g_execution;
CAFTickCursor       g_tick_cursor;

int OnInit()
  {
   if(InpAllowOrderMutation)
     {
      Print("Harness is compile/reconciliation-only; order mutation is intentionally disabled.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!g_execution.Configure(_Symbol,InpMagic,InpStrategyId))
      return(INIT_PARAMETERS_INCORRECT);
   if(!g_execution.Reconcile())
      Print("Execution ownership recovery is ambiguous; kernel remains fail-closed.");

   MqlTick current;
   if(SymbolInfoTick(_Symbol,current))
     {
      MqlTick bootstrap_ticks[];
      const int bootstrap_count=CopyTicksRange(_Symbol,bootstrap_ticks,COPY_TICKS_ALL,
                                                current.time_msc,current.time_msc);
      if(bootstrap_count>=0)
         g_tick_cursor.Reset(current.time_msc,bootstrap_count);
      else
         PrintFormat("Tick cursor bootstrap failed terminal_error=%d",GetLastError());
     }
   EventSetMillisecondTimer(500);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

void OnTick()
  {
   // Signal code is deliberately absent. Closed-bar strategies remain separate.
  }

void OnTimer()
  {
   g_execution.Reconcile();
   if(!g_tick_cursor.Initialized())
      return;
   MqlTick recovered[];
   const int copied=g_tick_cursor.Drain(_Symbol,recovered,4096,60000);
   if(copied<0)
      PrintFormat("Tick cursor fail-closed code=%d terminal_error=%d",
                  copied,g_tick_cursor.LastErrorCode());
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   g_execution.OnTradeTransaction(trans,request,result);
  }
