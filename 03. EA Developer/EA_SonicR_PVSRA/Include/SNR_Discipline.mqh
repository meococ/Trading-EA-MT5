#ifndef SNR_DISCIPLINE_MQH
#define SNR_DISCIPLINE_MQH

#include "SNR_Types.mqh"
#include "SNR_Risk.mqh"

#define SNR_MAX_TRADES_WEEK 5

int SnrIsoWeekKey(const datetime gmt)
  {
   if(gmt<=0)
      return(0);
   MqlDateTime t;
   TimeToStruct(gmt,t);
   const int iso_dow=(t.day_of_week==0 ? 7 : t.day_of_week);
   const datetime nearest_thu=gmt+(4-iso_dow)*86400;
   MqlDateTime th;
   TimeToStruct(nearest_thu,th);
   MqlDateTime jan1;
   ZeroMemory(jan1);
   jan1.year=th.year;
   jan1.mon=1;
   jan1.day=4;
   jan1.hour=12;
   const datetime week1=StructToTime(jan1);
   const int week=1+(int)((nearest_thu-week1)/604800);
   return(th.year*100+week);
  }

string SnrDisciplineFileName(const long magic)
  {
   return(StringFormat("SNR_DISC_%s_%I64d.csv",_Symbol,magic));
  }

void SnrDisciplineSave(const SnrRiskState &state,const long magic)
  {
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
      return;
   const int h=FileOpen(SnrDisciplineFileName(magic),
                        FILE_WRITE|FILE_CSV|FILE_ANSI);
   if(h==INVALID_HANDLE)
     {
      Print("SNR001_DISC persist_write_fail");
      return;
     }
   FileWrite(h,state.day_key,state.week_key,state.peak_equity,state.day_start_equity,
             (state.dd_locked?1:0),(state.day_locked?1:0),state.daily_entries,state.week_entries);
   FileClose(h);
  }

void SnrDisciplineLoad(SnrRiskState &state,const long magic)
  {
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
      return;
   const int h=FileOpen(SnrDisciplineFileName(magic),
                        FILE_READ|FILE_CSV|FILE_ANSI);
   if(h==INVALID_HANDLE)
      return;
   state.day_key=(int)FileReadNumber(h);
   state.week_key=(int)FileReadNumber(h);
   state.peak_equity=FileReadNumber(h);
   state.day_start_equity=FileReadNumber(h);
   state.dd_locked=((int)FileReadNumber(h)!=0);
   state.day_locked=((int)FileReadNumber(h)!=0);
   state.daily_entries=(int)FileReadNumber(h);
   state.week_entries=(int)FileReadNumber(h);
   FileClose(h);
  }

void SnrDisciplineRefresh(SnrRiskState &state,const datetime gmt_now,
                          const datetime server_now,
                          const double max_daily_loss_pct,const double max_dd_pct)
  {
   SnrRiskRefresh(state,server_now,max_daily_loss_pct,max_dd_pct);
   const int week=SnrIsoWeekKey(gmt_now);
   if(state.week_key!=week)
     {
      state.week_key=week;
      state.week_entries=0;
     }
  }

bool SnrDisciplineAllowNewRisk(const SnrRiskState &state,const int max_trades_per_day,
                               const int max_trades_per_week,string &reason)
  {
   reason="NONE";
   if(state.dd_locked)
     {
      reason="DD_LOCK";
      return(false);
     }
   if(state.day_locked)
     {
      reason="DAY_LOCK";
      return(false);
     }
   if(max_trades_per_day>0 && state.daily_entries>=max_trades_per_day)
     {
      reason="DAY_CAP";
      return(false);
     }
   if(max_trades_per_week>0 && state.week_entries>=max_trades_per_week)
     {
      reason="WEEK_CAP";
      return(false);
     }
   return(true);
  }

void SnrDisciplineNoteEntry(SnrRiskState &state,const long magic)
  {
   state.daily_entries++;
   state.week_entries++;
   SnrDisciplineSave(state,magic);
  }

#endif
