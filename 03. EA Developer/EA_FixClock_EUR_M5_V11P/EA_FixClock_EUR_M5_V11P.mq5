//+------------------------------------------------------------------+
//| EA_FixClock_EUR_M5_V11P.mq5                                    |
//| HYP-FIXCLK-EURUSD-M5-001: broker DST convention preflight       |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "No-trade EURUSD M5 broker-clock preflight for WMR London fix research"

input group "--- Frozen authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-FIXCLK-EURUSD-M5-001";
input string InpVariantTag="CLOCK_PREFLIGHT_ONLY";
input bool   InpCollectionOnly=true;
input int    InpGapThresholdHours=30;
input int    InpMaxOpenMinute=10;
input int    InpRequiredMismatchWeeks=3;
input long   InpMagic=5605701;

const string EA_NAME="EA_FixClock_EUR_M5_V11P";
const string EXPECTED_HYPOTHESIS="HYP-FIXCLK-EURUSD-M5-001";
const string EXPECTED_VARIANT="CLOCK_PREFLIGHT_ONLY";

datetime g_last_bar_open=0;
long g_new_bars=0,g_copy_failures=0,g_weekend_gaps=0,g_mismatch_weeks=0;
long g_mismatch_monday_midnight=0,g_mismatch_sunday_23=0,g_mismatch_other=0;
long g_standard_weeks=0,g_standard_monday_midnight=0,g_standard_other=0;
bool g_runtime_failed=false;

bool InputsAreFrozen()
  {
   return(InpResearchAutoMode&&InpEnableTelemetry&&InpHypothesisId==EXPECTED_HYPOTHESIS&&
          InpVariantTag==EXPECTED_VARIANT&&InpCollectionOnly&&InpGapThresholdHours==30&&
          InpMaxOpenMinute==10&&InpRequiredMismatchWeeks==3&&InpMagic==5605701);
  }

bool EmitSeriesProof()
  {
   long sync=0,m5first=0,m5terminal=0,m1server=0,m1terminal=0,bars=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,sync)||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5first)||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5terminal)||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1server)||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1terminal)||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,bars))return(false);
   const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   datetime a[];ArraySetAsSeries(a,false);ResetLastError();
   const int n=CopyTime(_Symbol,PERIOD_M5,(datetime)m5first,1,a);
   const int err=GetLastError();
   const long copied=(n==1?(long)a[0]:0);
   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",_Symbol,sync,m5first,m5terminal,m1server,m1terminal,bars,maxbars,m5first,n,copied,err);
   return(sync==1&&m5first>0&&m5terminal>0&&m1server>0&&m1terminal>0&&bars>0&&maxbars>0&&n==1&&copied==m5first&&err==0);
  }

datetime MakeDate(const int year,const int month,const int day)
  {
   MqlDateTime p;ZeroMemory(p);p.year=year;p.mon=month;p.day=day;
   return(StructToTime(p));
  }

int FirstSunday(const int year,const int month)
  {
   MqlDateTime p;TimeToStruct(MakeDate(year,month,1),p);
   return(1+((7-p.day_of_week)%7));
  }

int LastSunday(const int year,const int month)
  {
   const int next_month=(month==12?1:month+1);
   const int next_year=(month==12?year+1:year);
   const datetime last=MakeDate(next_year,next_month,1)-86400;
   MqlDateTime p;TimeToStruct(last,p);
   return(p.day-p.day_of_week);
  }

bool IsUkUsDstMismatchSunday(const datetime sunday)
  {
   MqlDateTime p;TimeToStruct(sunday,p);
   const datetime us_start=MakeDate(p.year,3,FirstSunday(p.year,3)+7);
   const datetime uk_start=MakeDate(p.year,3,LastSunday(p.year,3));
   const datetime uk_end=MakeDate(p.year,10,LastSunday(p.year,10));
   const datetime us_end=MakeDate(p.year,11,FirstSunday(p.year,11));
   return((sunday>=us_start&&sunday<uk_start)||(sunday>=uk_end&&sunday<us_end));
  }

void ObserveNewBar(const datetime current_open)
  {
   datetime times[];ArraySetAsSeries(times,true);
   if(CopyTime(_Symbol,PERIOD_M5,0,2,times)!=2){g_copy_failures++;return;}
   const datetime now_open=times[0],prev_open=times[1];
   if(now_open!=current_open||prev_open<=0||now_open<=prev_open){g_copy_failures++;return;}
   g_new_bars++;
   const long gap=(long)(now_open-prev_open);
   if(gap<(long)InpGapThresholdHours*3600)return;
   g_weekend_gaps++;

   MqlDateTime open_dt;TimeToStruct(now_open,open_dt);
   datetime sunday=now_open-3600;
   MqlDateTime sun_dt;TimeToStruct(sunday,sun_dt);
   sunday=MakeDate(sun_dt.year,sun_dt.mon,sun_dt.day);
   const bool mismatch=IsUkUsDstMismatchSunday(sunday);
   const bool monday_midnight=(open_dt.day_of_week==1&&open_dt.hour==0&&open_dt.min<=InpMaxOpenMinute);
   const bool sunday_23=(open_dt.day_of_week==0&&open_dt.hour==23&&open_dt.min<=InpMaxOpenMinute);
   if(mismatch)
     {
      g_mismatch_weeks++;
      if(monday_midnight)g_mismatch_monday_midnight++;
      else if(sunday_23)g_mismatch_sunday_23++;
      else g_mismatch_other++;
     }
   else
     {
      g_standard_weeks++;
      if(monday_midnight)g_standard_monday_midnight++;
      else g_standard_other++;
     }
  }

int OnInit()
  {
   if(_Symbol!="EURUSD"||_Period!=PERIOD_M5||!InputsAreFrozen())return(INIT_PARAMETERS_INCORRECT);
   if(!EmitSeriesProof())return(INIT_FAILED);
   long raw=0;if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE,raw)||raw<=0)return(INIT_FAILED);
   g_last_bar_open=(datetime)raw;
   PrintFormat("FIXCLK001_INIT ea=%s hypothesis=%s symbol=%s timeframe=M5 server=%s collection_only=true",EA_NAME,InpHypothesisId,_Symbol,AccountInfoString(ACCOUNT_SERVER));
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   long raw=0;if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE,raw)||raw<=0)return;
   const datetime bar=(datetime)raw;
   if(bar==g_last_bar_open)return;
   g_last_bar_open=bar;
   ObserveNewBar(bar);
  }

void OnDeinit(const int reason)
  {
   string result="DATA_FRONTIER_BLOCKED_TIMEZONE";
   string convention="UNRESOLVED";
   if(g_mismatch_weeks>=InpRequiredMismatchWeeks&&g_mismatch_other==0)
     {
      if(g_mismatch_monday_midnight==g_mismatch_weeks){result="PASS";convention="US_DST_NY_CLOSE";}
      else if(g_mismatch_sunday_23==g_mismatch_weeks){result="PASS";convention="EU_DST";}
     }
   PrintFormat("FIXCLK001_PREFLIGHT_RESULT result=%s convention=%s new_bars=%I64d copy_failures=%I64d weekend_gaps=%I64d mismatch_weeks=%I64d mismatch_monday_midnight=%I64d mismatch_sunday_23=%I64d mismatch_other=%I64d standard_weeks=%I64d standard_monday_midnight=%I64d standard_other=%I64d trading_enabled=false",result,convention,g_new_bars,g_copy_failures,g_weekend_gaps,g_mismatch_weeks,g_mismatch_monday_midnight,g_mismatch_sunday_23,g_mismatch_other,g_standard_weeks,g_standard_monday_midnight,g_standard_other);
   PrintFormat("FIXCLK001_SUMMARY reason=%d runtime_failed=%s result=%s convention=%s",reason,(g_runtime_failed?"true":"false"),result,convention);
  }
