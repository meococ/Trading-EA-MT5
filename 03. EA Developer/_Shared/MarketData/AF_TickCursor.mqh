//+------------------------------------------------------------------+
//| AF_TickCursor.mqh                                                |
//| Optional bounded recovery of terminal tick history.              |
//+------------------------------------------------------------------+
#ifndef ALPHAFACTORY_TICK_CURSOR_MQH
#define ALPHAFACTORY_TICK_CURSOR_MQH

class CAFTickCursor
  {
private:
   ulong             m_last_time_msc;
   ulong             m_scan_from_msc;
   int               m_consumed_at_last_msc;
   bool              m_initialized;
   int               m_last_error;

public:
                     CAFTickCursor()
     {
      m_last_time_msc=0;
      m_scan_from_msc=0;
      m_consumed_at_last_msc=0;
      m_initialized=false;
      m_last_error=0;
     }

   void Reset(const ulong last_time_msc,const int consumed_at_last_msc=0)
     {
      m_last_time_msc=last_time_msc;
      m_scan_from_msc=last_time_msc;
      m_consumed_at_last_msc=MathMax(consumed_at_last_msc,0);
      m_initialized=true;
      m_last_error=0;
     }

   bool Initialized()
     {
      return(m_initialized);
     }

   ulong LastTimeMsc()
     {
      return(m_last_time_msc);
     }

   int LastErrorCode()
     {
      return(m_last_error);
     }

   // Returns copied new ticks, -1 on terminal/history error, -2 on page overflow.
   int Drain(const string symbol,MqlTick &out_ticks[],const int max_ticks=4096,
             const ulong max_window_ms=60000)
     {
      ArrayResize(out_ticks,0);
      m_last_error=0;
      if(!m_initialized || StringLen(symbol)==0 || max_ticks<=0 ||
         max_ticks>8192 || max_window_ms==0)
        {
         m_last_error=ERR_INVALID_PARAMETER;
         return(-1);
        }
      MqlTick current;
      if(!SymbolInfoTick(symbol,current))
        {
         m_last_error=GetLastError();
         return(-1);
        }
      ulong to_msc=(ulong)current.time_msc;
      if(to_msc<m_scan_from_msc)
         return(0);
      if(to_msc-m_scan_from_msc>max_window_ms)
         to_msc=m_scan_from_msc+max_window_ms;

      MqlTick page[8192];
      ResetLastError();
      const int copied=CopyTicksRange(symbol,page,COPY_TICKS_ALL,m_scan_from_msc,to_msc);
      if(copied<0)
        {
         m_last_error=GetLastError();
         return(-1);
        }
      if(copied>=8192)
        {
         m_last_error=ERR_ARRAY_RESIZE_ERROR;
         return(-2);
        }

      ArrayResize(out_ticks,max_ticks);
      int written=0;
      ulong active_msc=m_last_time_msc;
      int seen_at_active=0;
      for(int i=0;i<copied;i++)
        {
         if((ulong)page[i].time_msc<m_last_time_msc)
            continue;
         if((ulong)page[i].time_msc==m_last_time_msc)
           {
            seen_at_active++;
            if(seen_at_active<=m_consumed_at_last_msc)
               continue;
           }
         else if((ulong)page[i].time_msc!=active_msc)
           {
            active_msc=(ulong)page[i].time_msc;
            seen_at_active=1;
           }
         if(written>=max_ticks)
           {
            ArrayResize(out_ticks,0);
            m_last_error=ERR_ARRAY_RESIZE_ERROR;
            return(-2);
           }
         out_ticks[written]=page[i];
         written++;
        }

      if(copied>0)
        {
         const ulong final_msc=(ulong)page[copied-1].time_msc;
         int final_count=0;
         for(int i=copied-1;i>=0 && (ulong)page[i].time_msc==final_msc;i--)
            final_count++;
         if(final_msc==m_last_time_msc)
            m_consumed_at_last_msc+=written;
         else
           {
            m_last_time_msc=final_msc;
            m_consumed_at_last_msc=final_count;
           }
        }
      // Completed catch-up windows are immutable and can advance past their
      // boundary.  At the live frontier keep the final millisecond inclusive;
      // the consumed ordinal prevents duplicates while allowing a later tick
      // with the same time_msc to be recovered.
      if(to_msc<(ulong)current.time_msc)
         m_scan_from_msc=to_msc+1;
      else
         m_scan_from_msc=to_msc;
      ArrayResize(out_ticks,written);
      return(written);
     }
  };

#endif
