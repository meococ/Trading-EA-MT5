//+------------------------------------------------------------------+
//| EA_ProspectiveCalendarPITMQDemo.mq5 collector v1.5.1                  |
//| HistoryByEvent snapshot watcher. No Last*, no prices, no orders. |
//| One Calendar API call per timer. Tester fail-closed.             |
//+------------------------------------------------------------------+
#property copyright "Prospective calendar PIT MQDemo v1.5.1 â€” not a trading system"
#property version   "1.501"
#property description "HistoryByEvent scheduled snapshot watcher; trading disabled"

#define COLLECTOR_VER  "1.5.1"
#define SCHEMA_VER     "mqdemo001"
#define CAL_UNSET      -9223372036854775808
#define FOLDER         "calendar_pit_mqdemo_001/"
#define N_CCY          8
#define DUE_CAP        64
#define PRE_SEC        21600
#define POST_SEC       21600
#define HORIZON_SEC    172800

input int InpTimerMs      = 1000;
input int InpHeartbeatSec = 60;

string g_ccy[N_CCY] = {"USD","EUR","JPY","GBP","CHF","CAD","AUD","NZD"};

struct CountryRec { ulong id; string code; string currency; string name; };
struct EventRec
{
   ulong  event_id;
   string currencies;
   ulong  country_id;
   string name;
   string code;
   int    importance;
   int    etype;
   int    time_mode;
   int    unit;
   int    multiplier;
};
struct OccRec
{
   ulong    event_id;
   ulong    value_id;
   long     scheduled;
   long     period;
   int      revision;
   long     forecast;
   long     actual;
   long     prevv;
   long     revised_prev;
   ulong    payload_hash;
   datetime first_obs;
   datetime last_obs;
   datetime last_poll;
   int      obs_count;
   bool     gap;
   bool     future_emitted;
   bool     idle_emitted;
};

CountryRec g_co[];
int        g_nco = 0;
bool       g_countries_ok = false;

EventRec   g_ev[];
int        g_nev = 0;
int        g_nall = 0;
int        g_nall_ccy[N_CCY];
int        g_nsel_ccy[N_CCY];
ulong      g_catalog_hash = 0;
bool       g_frozen = false;

bool       g_enum_ok[N_CCY];
int        g_enum_ix = 0;

OccRec     g_oc[];
int        g_noc = 0;

int        g_rr = 0;
int        g_due_rr = 0;
ulong      g_force_eid = 0;
ulong      g_force_vid = 0;
long       g_force_sched = 0;
long       g_force_period = 0;
ulong      g_force_hash = 0;

ulong      g_polls = 0;
ulong      g_obs = 0;
ulong      g_mut = 0;
ulong      g_gaps = 0;
ulong      g_errors = 0;
ulong      g_future_ok = 0;
ulong      g_idle_ok = 0;
datetime   g_last_ok = 0;
datetime   g_hb_last = 0;
int        g_last_due_n = 0;
int        g_last_future_n = 0;
bool       g_timer_ms = false;
bool       g_fatal = false;

string Esc(string s)
{
   StringReplace(s,"\\","\\\\"); StringReplace(s,"\"","\\\"");
   StringReplace(s,"\n"," "); StringReplace(s,"\r","");
   return s;
}
string CsvQ(string s){ StringReplace(s,"\"","\"\""); return "\""+s+"\""; }
string Iso(const datetime t){ return TimeToString(t,TIME_DATE|TIME_SECONDS); }
string Ljs(const long v){ return (v==CAL_UNSET ? "null" : IntegerToString(v)); }
string Lcsv(const long v){ return (v==CAL_UNSET ? "" : IntegerToString(v)); }
string I64(const ulong v){ return IntegerToString((long)v); }
string B01(const bool v){ return (v?"true":"false"); }
string StateField(string s)
{
   StringReplace(s,"\t"," "); StringReplace(s,"\n"," "); StringReplace(s,"\r"," ");
   return s;
}

ulong Fnv(const string s)
{
   ulong h=1469598103934665603;
   ushort ch[];
   int n=StringToShortArray(s,ch);
   if(n>0) n--;
   for(int i=0;i<n;i++){ h^=(ulong)ch[i]; h*=1099511628211; }
   return h;
}

ulong PayloadHash(const int rev,const long f,const long a,const long p,const long r)
{
   return Fnv(IntegerToString(rev)+"|"+IntegerToString(f)+"|"+IntegerToString(a)+"|"+IntegerToString(p)+"|"+IntegerToString(r));
}

string SafetyJson()
{
   return "\"hypothesis_id\":\"HYP-CALENDAR-PIT-MQDEMO-001\","
        +"\"expected_server\":\"MetaQuotes-Demo\","
        +"\"schema_version\":\""+SCHEMA_VER+"\","
        +"\"collector_version\":\""+COLLECTOR_VER+"\","
        +"\"terminal_build\":"+IntegerToString(TerminalInfoInteger(TERMINAL_BUILD))+","
        +"\"account_server\":\""+Esc(AccountInfoString(ACCOUNT_SERVER))+"\","
        +"\"recv_clock\":\"terminal_observation_not_official_first_public\","
        +"\"outcome_accessed\":false,\"prices_read\":false,\"orders\":false,\"trading_disabled\":true";
}

int OpenApp(const string name,const bool hdr,const string header)
{
   string p=FOLDER+name;
   bool exists=FileIsExist(p,FILE_COMMON);
   int h=FileOpen(p,FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) h=FileOpen(p,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return INVALID_HANDLE;
   FileSeek(h,0,SEEK_END);
   if(!exists && hdr)
   {
      uchar bom[3]; bom[0]=0xEF; bom[1]=0xBB; bom[2]=0xBF;
      FileWriteArray(h,bom,0,3);
      FileWriteString(h,header+"\n");
   }
   return h;
}

bool Jline(const string obj)
{
   int h=OpenApp("calendar_pit_mqdemo001.jsonl",false,"");
   if(h==INVALID_HANDLE) return false;
   uint written=FileWriteString(h,obj+"\n");
   FileFlush(h);
   FileClose(h);
   return (written>0);
}

const string CSV_HDR=
   "kind,ts_local,ts_server,ts_current,tick64,"
   "event_id,value_id,scheduled_unix,period_unix,revision,"
   "old_forecast,old_actual,old_prev,old_revised_prev,"
   "new_forecast,new_actual,new_prev,new_revised_prev,"
   "payload_hash,latency_sec,due_set,api_error,gap,"
   "importance,event_name,event_code,source_currencies,recv_clock";

bool CsvRow(const string line)
{
   int h=OpenApp("calendar_pit_mqdemo001.csv",true,CSV_HDR);
   if(h==INVALID_HANDLE) return false;
   uint written=FileWriteString(h,line+"\n");
   FileFlush(h);
   FileClose(h);
   return (written>0);
}

bool Emit(const string kind,const string extra)
{
   return Jline("{\"kind\":\""+kind+"\",\"ts_local\":\""+Iso(TimeLocal())+"\","
         +"\"ts_server\":\""+Iso(TimeTradeServer())+"\","
         +"\"ts_current\":\""+Iso(TimeCurrent())+"\","
         +"\"tick64\":"+I64(GetTickCount64())+","
         +SafetyJson()+extra+"}");
}

void ResetMemory()
{
   ArrayResize(g_co,0); g_nco=0; g_countries_ok=false;
   ArrayResize(g_ev,0); g_nev=0; g_nall=0; g_catalog_hash=0; g_frozen=false;
   ArrayResize(g_oc,0); g_noc=0;
   for(int i=0;i<N_CCY;i++){ g_enum_ok[i]=false; g_nall_ccy[i]=0; g_nsel_ccy[i]=0; }
   g_enum_ix=0; g_rr=0; g_due_rr=0;
   g_force_eid=0; g_force_vid=0; g_force_sched=0; g_force_period=0; g_force_hash=0;
   g_polls=0; g_obs=0; g_mut=0; g_gaps=0; g_errors=0; g_future_ok=0; g_idle_ok=0;
   g_last_ok=0; g_hb_last=0; g_last_due_n=0; g_last_future_n=0;
   g_timer_ms=false; g_fatal=false;
}

int FindEvent(const ulong id)
{
   for(int i=0;i<g_nev;i++) if(g_ev[i].event_id==id) return i;
   return -1;
}
int FindCountry(const ulong id)
{
   for(int i=0;i<g_nco;i++) if(g_co[i].id==id) return i;
   return -1;
}
int FindOcc(const ulong eid,const ulong vid,const long sch,const long per)
{
   for(int i=0;i<g_noc;i++)
      if(g_oc[i].event_id==eid && g_oc[i].value_id==vid && g_oc[i].scheduled==sch && g_oc[i].period==per)
         return i;
   return -1;
}

bool HasDupEventIds()
{
   for(int i=0;i<g_nev;i++)
   {
      if(g_ev[i].event_id==0) return true;
      for(int j=i+1;j<g_nev;j++) if(g_ev[i].event_id==g_ev[j].event_id) return true;
   }
   return false;
}

ulong ComputeCatalogHash()
{
   ulong ids[];
   ArrayResize(ids,g_nev);
   for(int i=0;i<g_nev;i++) ids[i]=g_ev[i].event_id;
   for(int i=0;i<g_nev;i++)
      for(int j=i+1;j<g_nev;j++)
         if(ids[j]<ids[i]){ ulong t=ids[i]; ids[i]=ids[j]; ids[j]=t; }
   string s="";
   for(int i=0;i<g_nev;i++){ if(i>0) s+=","; s+=I64(ids[i]); }
   return Fnv(s);
}

int CountFutureOcc(const datetime nows)
{
   int n=0;
   long n0=(long)nows;
   for(int i=0;i<g_noc;i++)
      if(g_oc[i].scheduled>n0 && g_oc[i].scheduled<=n0+HORIZON_SEC) n++;
   return n;
}

void BuildDue(int &due[],int &ndue,int &nover,const datetime nows)
{
   ndue=0; nover=0;
   long n0=(long)nows;
   ArrayResize(due,0);
   for(int i=0;i<g_noc;i++)
   {
      if(g_oc[i].scheduled<n0-PRE_SEC || g_oc[i].scheduled>n0+POST_SEC) continue;
      if(ndue<DUE_CAP)
      {
         ArrayResize(due,ndue+1);
         due[ndue++]=i;
      }
      else nover++;
   }
}

void SaveCountries()
{
   int h=FileOpen(FOLDER+"countries_mqdemo001.txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return;
   FileWriteString(h,"schema="+SCHEMA_VER+"\n");
   FileWriteString(h,"n="+IntegerToString(g_nco)+"\n");
   for(int i=0;i<g_nco;i++)
      FileWriteString(h,I64(g_co[i].id)+"\t"+StateField(g_co[i].code)+"\t"+StateField(g_co[i].currency)+"\t"+StateField(g_co[i].name)+"\n");
   FileFlush(h); FileClose(h);
}

void SaveCatalog()
{
   g_catalog_hash=ComputeCatalogHash();
   int h=FileOpen(FOLDER+"catalog_state_mqdemo001.txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return;
   FileWriteString(h,"schema="+SCHEMA_VER+"\n");
   FileWriteString(h,"version="+COLLECTOR_VER+"\n");
   FileWriteString(h,"frozen="+(g_frozen?"1":"0")+"\n");
   FileWriteString(h,"n_all="+IntegerToString(g_nall)+"\n");
   FileWriteString(h,"n_sel="+IntegerToString(g_nev)+"\n");
   FileWriteString(h,"catalog_hash="+I64(g_catalog_hash)+"\n");
   FileWriteString(h,"rr="+IntegerToString(g_rr)+"\n");
   string eok="";
   for(int i=0;i<N_CCY;i++){ if(i>0) eok+=","; eok+=(g_enum_ok[i]?"1":"0"); }
   FileWriteString(h,"enum_ok="+eok+"\n");
   for(int i=0;i<g_nev;i++)
   {
      FileWriteString(h,"E\t"+I64(g_ev[i].event_id)+"\t"+StateField(g_ev[i].currencies)+"\t"
         +I64(g_ev[i].country_id)+"\t"+IntegerToString(g_ev[i].importance)+"\t"
         +IntegerToString(g_ev[i].etype)+"\t"+IntegerToString(g_ev[i].time_mode)+"\t"
         +IntegerToString(g_ev[i].unit)+"\t"+IntegerToString(g_ev[i].multiplier)+"\t"
         +StateField(g_ev[i].code)+"\t"+StateField(g_ev[i].name)+"\n");
   }
   FileFlush(h); FileClose(h);

   int c=FileOpen(FOLDER+"event_catalog_mqdemo001.csv",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(c==INVALID_HANDLE) return;
   uchar bom[3]; bom[0]=0xEF; bom[1]=0xBB; bom[2]=0xBF;
   FileWriteArray(c,bom,0,3);
   FileWriteString(c,"event_id,source_currencies,country_id,importance,event_type,time_mode,unit,multiplier,event_code,event_name\n");
   for(int i=0;i<g_nev;i++)
      FileWriteString(c,I64(g_ev[i].event_id)+","+CsvQ(g_ev[i].currencies)+","
         +I64(g_ev[i].country_id)+","+IntegerToString(g_ev[i].importance)+","
         +IntegerToString(g_ev[i].etype)+","+IntegerToString(g_ev[i].time_mode)+","
         +IntegerToString(g_ev[i].unit)+","+IntegerToString(g_ev[i].multiplier)+","
         +CsvQ(g_ev[i].code)+","+CsvQ(g_ev[i].name)+"\n");
   FileFlush(c); FileClose(c);
}

bool SaveOcc()
{
   int h=FileOpen(FOLDER+"occurrence_mqdemo001.txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return false;
   bool ok=(FileWriteString(h,"schema="+SCHEMA_VER+"\n")>0);
   ok=(FileWriteString(h,"n_occ="+IntegerToString(g_noc)+"\n")>0 && ok);
   for(int i=0;i<g_noc;i++)
   {
      ok=(FileWriteString(h,"O\t"+I64(g_oc[i].event_id)+"\t"+I64(g_oc[i].value_id)+"\t"
         +IntegerToString(g_oc[i].scheduled)+"\t"+IntegerToString(g_oc[i].period)+"\t"
         +IntegerToString(g_oc[i].revision)+"\t"
         +IntegerToString(g_oc[i].forecast)+"\t"+IntegerToString(g_oc[i].actual)+"\t"
         +IntegerToString(g_oc[i].prevv)+"\t"+IntegerToString(g_oc[i].revised_prev)+"\t"
         +I64(g_oc[i].payload_hash)+"\t"
         +IntegerToString((long)g_oc[i].first_obs)+"\t"+IntegerToString((long)g_oc[i].last_obs)+"\t"
         +IntegerToString((long)g_oc[i].last_poll)+"\t"+IntegerToString(g_oc[i].obs_count)+"\t"
         +(g_oc[i].gap?"1":"0")+"\t"+(g_oc[i].future_emitted?"1":"0")+"\t"
         +(g_oc[i].idle_emitted?"1":"0")+"\n")>0 && ok);
   }
   FileFlush(h); FileClose(h);
   return ok;
}

bool LoadCountries()
{
   int h=FileOpen(FOLDER+"countries_mqdemo001.txt",FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return true;
   int declared=-1;
   g_nco=0; ArrayResize(g_co,0);
   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringFind(line,"n=")==0) declared=(int)StringToInteger(StringSubstr(line,2));
      else if(StringFind(line,"schema=")==0)
      { if(StringSubstr(line,7)!=SCHEMA_VER){ FileClose(h); return false; } }
      else
      {
         string p[];
         if(StringSplit(line,'\t',p)<4) continue;
         ulong id=(ulong)StringToInteger(p[0]);
         if(id==0){ FileClose(h); return false; }
         int n=g_nco; ArrayResize(g_co,n+1);
         g_co[n].id=id; g_co[n].code=p[1]; g_co[n].currency=p[2]; g_co[n].name=p[3];
         g_nco++;
      }
   }
   FileClose(h);
   if(declared>=0 && declared!=g_nco) return false;
   if(g_nco>0) g_countries_ok=true;
   return true;
}

bool LoadCatalog()
{
   int h=FileOpen(FOLDER+"catalog_state_mqdemo001.txt",FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return true;
   int declared=-1;
   g_nev=0; ArrayResize(g_ev,0);
   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringFind(line,"schema=")==0)
      { if(StringSubstr(line,7)!=SCHEMA_VER){ FileClose(h); return false; } }
      else if(StringFind(line,"version=")==0)
      { if(StringSubstr(line,8)!=COLLECTOR_VER){ FileClose(h); return false; } }
      else if(StringFind(line,"frozen=")==0) g_frozen=(StringSubstr(line,7)=="1");
      else if(StringFind(line,"n_all=")==0) g_nall=(int)StringToInteger(StringSubstr(line,6));
      else if(StringFind(line,"n_sel=")==0) declared=(int)StringToInteger(StringSubstr(line,6));
      else if(StringFind(line,"catalog_hash=")==0) g_catalog_hash=(ulong)StringToInteger(StringSubstr(line,13));
      else if(StringFind(line,"rr=")==0) g_rr=(int)StringToInteger(StringSubstr(line,3));
      else if(StringFind(line,"enum_ok=")==0)
      {
         string p[]; int np=StringSplit(StringSubstr(line,8),',',p);
         for(int i=0;i<np && i<N_CCY;i++) g_enum_ok[i]=(p[i]=="1");
      }
      else if(StringFind(line,"E\t")==0)
      {
         string p[]; int np=StringSplit(line,'\t',p);
         if(np<10){ FileClose(h); return false; }
         ulong id=(ulong)StringToInteger(p[1]);
         if(id==0){ FileClose(h); return false; }
         int n=g_nev; ArrayResize(g_ev,n+1);
         ZeroMemory(g_ev[n]);
         g_ev[n].event_id=id;
         g_ev[n].currencies=p[2];
         g_ev[n].country_id=(ulong)StringToInteger(p[3]);
         g_ev[n].importance=(int)StringToInteger(p[4]);
         g_ev[n].etype=(int)StringToInteger(p[5]);
         g_ev[n].time_mode=(int)StringToInteger(p[6]);
         g_ev[n].unit=(int)StringToInteger(p[7]);
         g_ev[n].multiplier=(int)StringToInteger(p[8]);
         g_ev[n].code=p[9];
         if(np>10) g_ev[n].name=p[10];
         g_nev++;
      }
   }
   FileClose(h);
   if(declared>=0 && declared!=g_nev) return false;
   if(HasDupEventIds()) return false;
   if(g_nev>0 && ComputeCatalogHash()!=g_catalog_hash && g_catalog_hash!=0) return false;
   if(g_frozen && (CountEnumOk()!=N_CCY || g_nev<=0 || g_catalog_hash==0)) return false;
   return true;
}

bool LoadOcc()
{
   int h=FileOpen(FOLDER+"occurrence_mqdemo001.txt",FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return true;
   int declared=-1;
   g_noc=0; ArrayResize(g_oc,0);
   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringFind(line,"schema=")==0)
      { if(StringSubstr(line,7)!=SCHEMA_VER){ FileClose(h); return false; } }
      else if(StringFind(line,"n_occ=")==0) declared=(int)StringToInteger(StringSubstr(line,6));
      else if(StringFind(line,"O\t")==0)
      {
         string p[]; int np=StringSplit(line,'\t',p);
         if(np<18){ FileClose(h); return false; }
         ulong eid=(ulong)StringToInteger(p[1]);
         ulong vid=(ulong)StringToInteger(p[2]);
         if(eid==0 || vid==0 || StringToInteger(p[3])<=0){ FileClose(h); return false; }
         if(FindOcc(eid,vid,StringToInteger(p[3]),StringToInteger(p[4]))>=0){ FileClose(h); return false; }
         int n=g_noc; ArrayResize(g_oc,n+1);
         ZeroMemory(g_oc[n]);
         g_oc[n].event_id=eid;
         g_oc[n].value_id=vid;
         g_oc[n].scheduled=StringToInteger(p[3]);
         g_oc[n].period=StringToInteger(p[4]);
         g_oc[n].revision=(int)StringToInteger(p[5]);
         g_oc[n].forecast=StringToInteger(p[6]);
         g_oc[n].actual=StringToInteger(p[7]);
         g_oc[n].prevv=StringToInteger(p[8]);
         g_oc[n].revised_prev=StringToInteger(p[9]);
         g_oc[n].payload_hash=(ulong)StringToInteger(p[10]);
         g_oc[n].first_obs=(datetime)StringToInteger(p[11]);
         g_oc[n].last_obs=(datetime)StringToInteger(p[12]);
         g_oc[n].last_poll=(datetime)StringToInteger(p[13]);
         g_oc[n].obs_count=(int)StringToInteger(p[14]);
         if(np>15) g_oc[n].gap=(p[15]=="1");
         if(np>16) g_oc[n].future_emitted=(p[16]=="1");
         if(np>17) g_oc[n].idle_emitted=(p[17]=="1");
         g_noc++;
      }
   }
   FileClose(h);
   if(declared>=0 && declared!=g_noc) return false;
   return true;
}

void TagCcy(EventRec &e,const string ccy)
{
   if(StringFind("|"+e.currencies+"|","|"+ccy+"|")>=0) return;
   if(e.currencies=="") e.currencies=ccy;
   else e.currencies=e.currencies+"|"+ccy;
}

int AddSelected(const MqlCalendarEvent &src,const string ccy)
{
   int ix=FindEvent(src.id);
   if(ix>=0){ TagCcy(g_ev[ix],ccy); return 0; }
   if((int)src.importance < (int)CALENDAR_IMPORTANCE_MODERATE) return -2;
   int n=g_nev; ArrayResize(g_ev,n+1);
   ZeroMemory(g_ev[n]);
   g_ev[n].event_id=src.id;
   g_ev[n].currencies=ccy;
   g_ev[n].country_id=src.country_id;
   g_ev[n].name=src.name;
   g_ev[n].code=src.event_code;
   g_ev[n].importance=(int)src.importance;
   g_ev[n].etype=(int)src.type;
   g_ev[n].time_mode=(int)src.time_mode;
   g_ev[n].unit=(int)src.unit;
   g_ev[n].multiplier=(int)src.multiplier;
   g_nev++;
   return 1;
}

int CountEnumOk()
{
   int n=0; for(int i=0;i<N_CCY;i++) if(g_enum_ok[i]) n++; return n;
}

void Heartbeat()
{
   datetime now=TimeLocal();
   if(now-g_hb_last<InpHeartbeatSec) return;
   g_hb_last=now;
   datetime ns=TimeTradeServer();
   long age=(g_last_ok==0?-1:(long)(now-g_last_ok));
   Emit("HEARTBEAT",
      ",\"discovery_ok\":"+IntegerToString(CountEnumOk())+
      ",\"discovery_total\":8"+
      ",\"catalog_frozen\":"+B01(g_frozen)+
      ",\"n_all_defs\":"+IntegerToString(g_nall)+
      ",\"selected_events\":"+IntegerToString(g_nev)+
      ",\"catalog_hash\":\""+I64(g_catalog_hash)+"\""+
      ",\"future_occurrences\":"+IntegerToString(CountFutureOcc(ns))+
      ",\"due_set\":"+IntegerToString(g_last_due_n)+
      ",\"future_history_successes\":"+I64(g_future_ok)+
      ",\"idle_proofs\":"+I64(g_idle_ok)+
      ",\"observations\":"+I64(g_obs)+
      ",\"mutations\":"+I64(g_mut)+
      ",\"gaps\":"+I64(g_gaps)+
      ",\"api_errors\":"+I64(g_errors)+
      ",\"last_success_age_sec\":"+IntegerToString(age)+
      ",\"polls\":"+I64(g_polls));
}

void DoCountries()
{
   MqlCalendarCountry cs[];
   ResetLastError();
   int n=CalendarCountries(cs);
   int err=GetLastError();
   if(n<0 || err!=0)
   {
      g_errors++;
      Emit("API_ERROR_COUNTRIES",",\"n\":"+IntegerToString(n)+",\"api_error\":"+IntegerToString(err));
      return;
   }
   g_nco=0; ArrayResize(g_co,0);
   for(int i=0;i<n;i++)
   {
      ArrayResize(g_co,g_nco+1);
      g_co[g_nco].id=cs[i].id;
      g_co[g_nco].code=cs[i].code;
      g_co[g_nco].currency=cs[i].currency;
      g_co[g_nco].name=cs[i].name;
      g_nco++;
   }
   g_countries_ok=true;
   g_last_ok=TimeLocal();
   SaveCountries();
   Emit("DISCOVERY_COUNTRIES",",\"n\":"+IntegerToString(g_nco));
}

void FreezeCatalog()
{
   g_frozen=true;
   g_catalog_hash=ComputeCatalogHash();
   SaveCatalog();
   Emit("CATALOG_FROZEN",
        ",\"n_all_defs\":"+IntegerToString(g_nall)+
        ",\"n_selected\":"+IntegerToString(g_nev)+
        ",\"catalog_hash\":\""+I64(g_catalog_hash)+"\""+
        ",\"importance_min\":\"CALENDAR_IMPORTANCE_MODERATE\""+
        ",\"outcome_used\":false");
}

void DoEnumOne()
{
   int pick=-1;
   for(int k=0;k<N_CCY;k++)
   {
      int i=(g_enum_ix+k)%N_CCY;
      if(!g_enum_ok[i]){ pick=i; break; }
   }
   if(pick<0){ if(!g_frozen) FreezeCatalog(); return; }
   g_enum_ix=(pick+1)%N_CCY;
   string ccy=g_ccy[pick];
   MqlCalendarEvent evs[];
   ResetLastError();
   int n=CalendarEventByCurrency(ccy,evs);
   int err=GetLastError();
   if(n<0 || err!=0)
   {
      g_errors++;
      Emit("API_ERROR_ENUM",",\"currency\":\""+ccy+"\",\"n\":"+IntegerToString(n)+",\"api_error\":"+IntegerToString(err));
      return;
   }
   int n_all=0,n_new=0,n_dup=0,n_skip=0;
   for(int i=0;i<n;i++)
   {
      if(evs[i].id==0) continue;
      n_all++;
      int r=AddSelected(evs[i],ccy);
      if(r==1) n_new++;
      else if(r==0) n_dup++;
      else n_skip++;
   }
   g_nall+=n_all;
   g_nall_ccy[pick]=n_all;
   g_nsel_ccy[pick]=n_new;
   g_enum_ok[pick]=true;
   g_last_ok=TimeLocal();
   SaveCatalog();
   Emit("DISCOVERY_EVENT_DEFS",
        ",\"currency\":\""+ccy+"\",\"n_all_defs\":"+IntegerToString(n_all)+
        ",\"n_selected_new\":"+IntegerToString(n_new)+
        ",\"n_dup_id\":"+IntegerToString(n_dup)+
        ",\"n_below_moderate\":"+IntegerToString(n_skip)+
        ",\"selected_total\":"+IntegerToString(g_nev)+
        ",\"all_defs_total\":"+IntegerToString(g_nall)+
        ",\"outcome_used\":false");
   if(CountEnumOk()==N_CCY) FreezeCatalog();
}

bool WriteTape(const string kind,const int eix,const OccRec &oldv,const OccRec &nw,
               const long latency,const int duesz,const bool isgap)
{
   bool csv_ok=CsvRow(kind+","+Iso(TimeLocal())+","+Iso(TimeTradeServer())+","+Iso(TimeCurrent())+","
      +I64(GetTickCount64())+","
      +I64(nw.event_id)+","+I64(nw.value_id)+","
      +IntegerToString(nw.scheduled)+","+IntegerToString(nw.period)+","
      +IntegerToString(nw.revision)+","
      +Lcsv(oldv.forecast)+","+Lcsv(oldv.actual)+","+Lcsv(oldv.prevv)+","+Lcsv(oldv.revised_prev)+","
      +Lcsv(nw.forecast)+","+Lcsv(nw.actual)+","+Lcsv(nw.prevv)+","+Lcsv(nw.revised_prev)+","
      +I64(nw.payload_hash)+","+IntegerToString(latency)+","+IntegerToString(duesz)+",,"
      +(isgap?"1":"0")+","
      +IntegerToString(eix>=0?g_ev[eix].importance:0)+","
      +CsvQ(eix>=0?g_ev[eix].name:"")+","+CsvQ(eix>=0?g_ev[eix].code:"")+","
      +CsvQ(eix>=0?g_ev[eix].currencies:"")+","
      +"terminal_observation_not_official_first_public");

   bool json_ok=Jline("{\"kind\":\""+kind+"\",\"ts_local\":\""+Iso(TimeLocal())+"\","
      +"\"ts_server\":\""+Iso(TimeTradeServer())+"\","
      +"\"ts_current\":\""+Iso(TimeCurrent())+"\","
      +"\"tick64\":"+I64(GetTickCount64())+","
      +"\"event_id\":"+I64(nw.event_id)+","
      +"\"value_id\":"+I64(nw.value_id)+","
      +"\"scheduled_unix\":"+IntegerToString(nw.scheduled)+","
      +"\"period_unix\":"+IntegerToString(nw.period)+","
      +"\"revision\":"+IntegerToString(nw.revision)+","
      +"\"old_forecast\":"+Ljs(oldv.forecast)+",\"old_actual\":"+Ljs(oldv.actual)+","
      +"\"old_prev\":"+Ljs(oldv.prevv)+",\"old_revised_prev\":"+Ljs(oldv.revised_prev)+","
      +"\"new_forecast\":"+Ljs(nw.forecast)+",\"new_actual\":"+Ljs(nw.actual)+","
      +"\"new_prev\":"+Ljs(nw.prevv)+",\"new_revised_prev\":"+Ljs(nw.revised_prev)+","
      +"\"payload_hash\":\""+I64(nw.payload_hash)+"\","
      +"\"latency_sec\":"+IntegerToString(latency)+","
      +"\"due_set\":"+IntegerToString(duesz)+","
      +"\"gap\":"+B01(isgap)+","
      +"\"importance\":"+(eix>=0?IntegerToString(g_ev[eix].importance):"0")+","
      +"\"event_name\":\""+Esc(eix>=0?g_ev[eix].name:"")+"\","
      +"\"event_code\":\""+Esc(eix>=0?g_ev[eix].code:"")+"\","
      +"\"source_currencies\":\""+Esc(eix>=0?g_ev[eix].currencies:"")+"\","
      +SafetyJson()+"}");
   return (csv_ok && json_ok);
}

bool ApplyValue(const MqlCalendarValue &v,const datetime nows,const datetime fromt,const datetime tot,
                const int duesz,bool &saw_future,bool &io_failed)
{
   if(v.event_id==0 || v.id==0) return false;
   if((datetime)v.time<fromt || (datetime)v.time>tot) return false;
   int eix=FindEvent(v.event_id);
   if(eix<0) return false;

   ulong hv=PayloadHash(v.revision,v.forecast_value,v.actual_value,v.prev_value,v.revised_prev_value);
   int oix=FindOcc(v.event_id,v.id,(long)v.time,(long)v.period);
   OccRec nw;
   ZeroMemory(nw);
   nw.event_id=v.event_id;
   nw.value_id=v.id;
   nw.scheduled=(long)v.time;
   nw.period=(long)v.period;
   nw.revision=v.revision;
   nw.forecast=v.forecast_value;
   nw.actual=v.actual_value;
   nw.prevv=v.prev_value;
   nw.revised_prev=v.revised_prev_value;
   nw.payload_hash=hv;
   nw.last_obs=TimeLocal();
   nw.last_poll=TimeLocal();
   long lat=(long)nows-(long)v.time;

   if(oix<0)
   {
      nw.first_obs=TimeLocal();
      nw.obs_count=1;
      OccRec oldz; ZeroMemory(oldz);
      oldz.forecast=CAL_UNSET; oldz.actual=CAL_UNSET; oldz.prevv=CAL_UNSET; oldz.revised_prev=CAL_UNSET;
      if(!WriteTape("OBSERVATION_HISTORY",eix,oldz,nw,lat,duesz,false))
      {
         io_failed=true;
         return false;
      }
      int n=g_noc; ArrayResize(g_oc,n+1);
      g_oc[n]=nw;
      oix=n; g_noc++;
      g_obs++;
   }
   else if(g_oc[oix].payload_hash!=hv)
   {
      OccRec oldv=g_oc[oix];
      if(!WriteTape("MUTATION_HISTORY",eix,oldv,nw,lat,duesz,false))
      {
         io_failed=true;
         return false;
      }
      nw.first_obs=g_oc[oix].first_obs;
      nw.obs_count=g_oc[oix].obs_count+1;
      nw.future_emitted=g_oc[oix].future_emitted;
      nw.idle_emitted=g_oc[oix].idle_emitted;
      g_oc[oix]=nw;
      g_mut++;
   }
   else
   {
      g_oc[oix].last_obs=TimeLocal();
      g_oc[oix].last_poll=TimeLocal();
      g_oc[oix].obs_count++;
   }

   if((long)v.time>(long)nows && (long)v.time<=(long)nows+HORIZON_SEC)
   {
      saw_future=true;
      if(!g_oc[oix].future_emitted)
      {
         bool future_json=Emit("FUTURE_DISCOVERY_HISTORY",
              ",\"event_id\":"+I64(v.event_id)+
              ",\"value_id\":"+I64(v.id)+
              ",\"scheduled_unix\":"+IntegerToString((long)v.time)+
              ",\"n\":1,\"api_error\":0"+
              ",\"payload_hash\":\""+I64(hv)+"\"");
         bool future_csv=CsvRow("FUTURE_DISCOVERY_HISTORY,"+Iso(TimeLocal())+","+Iso(TimeTradeServer())+","
            +Iso(TimeCurrent())+","+I64(GetTickCount64())+","
            +I64(v.event_id)+","+I64(v.id)+","+IntegerToString((long)v.time)+","
            +IntegerToString((long)v.period)+","+IntegerToString(v.revision)+
            ",,,,,,,,,"+I64(hv)+",,,"+"0,0,"+
            IntegerToString(g_ev[eix].importance)+","+CsvQ(g_ev[eix].name)+","
            +CsvQ(g_ev[eix].code)+","+CsvQ(g_ev[eix].currencies)+","
            +"terminal_observation_not_official_first_public");
         if(!future_json || !future_csv)
         {
            io_failed=true;
            return false;
         }
         g_oc[oix].future_emitted=true;
         g_future_ok++;
         g_force_eid=v.event_id;
         g_force_vid=v.id;
         g_force_sched=(long)v.time;
         g_force_period=(long)v.period;
         g_force_hash=hv;
      }
   }
   return true;
}

void DoHistory(const ulong eid,const ulong expect_vid,const long expect_sch,const long expect_per,const int duesz)
{
   ulong force_before=g_force_eid;
   datetime nows=TimeTradeServer();
   datetime fromt=nows-PRE_SEC;
   datetime tot=nows+HORIZON_SEC;
   MqlCalendarValue vals[];
   ResetLastError();
   int n=CalendarValueHistoryByEvent(eid,vals,fromt,tot);
   int err=GetLastError();
   if(n<0 || err!=0)
   {
      g_errors++;
      Emit("API_ERROR_HISTORY",
           ",\"event_id\":"+I64(eid)+
           ",\"n\":"+IntegerToString(n)+
           ",\"api_error\":"+IntegerToString(err)+
           ",\"cursor_advanced\":false");
      CsvRow("API_ERROR_HISTORY,"+Iso(TimeLocal())+","+Iso(TimeTradeServer())+","
         +Iso(TimeCurrent())+","+I64(GetTickCount64())+","
         +I64(eid)+",,,,,,,,,,,,,,,"+IntegerToString(err)+",1,,,,,"
         +"terminal_observation_not_official_first_public");
      return;
   }

   bool saw_future=false;
   bool saw_expect=false;
   bool io_failed=false;
   int accepted=0;
   for(int i=0;i<n;i++)
   {
      if(vals[i].event_id!=eid) continue;
      if(ApplyValue(vals[i],nows,fromt,tot,duesz,saw_future,io_failed))
      {
         accepted++;
         if(expect_vid!=0 && vals[i].id==expect_vid && (long)vals[i].time==expect_sch && (long)vals[i].period==expect_per)
            saw_expect=true;
      }
   }

   if(io_failed || !SaveOcc())
   {
      g_errors++;
      g_fatal=true;
      Emit("IO_ERROR_HISTORY",
           ",\"event_id\":"+I64(eid)+",\"state_advanced\":false,\"collector_fatal\":true");
      return;
   }
   g_last_ok=TimeLocal();

   if(expect_vid!=0 && !saw_expect)
   {
      int oix=FindOcc(eid,expect_vid,expect_sch,expect_per);
      if(oix>=0) g_oc[oix].gap=true;
      g_gaps++;
      Emit("MISSING_DUE_HISTORY",
           ",\"event_id\":"+I64(eid)+
           ",\"value_id\":"+I64(expect_vid)+
           ",\"scheduled_unix\":"+IntegerToString(expect_sch)+
           ",\"n\":"+IntegerToString(n)+
           ",\"accepted\":"+IntegerToString(accepted));
      SaveOcc();
   }

   if(force_before==eid && g_force_vid!=0)
   {
      int oix=FindOcc(g_force_eid,g_force_vid,g_force_sched,g_force_period);
      if(oix>=0 && saw_expect && n>=1 && err==0 && g_oc[oix].payload_hash==g_force_hash && !g_oc[oix].idle_emitted)
      {
         bool idle_json=Emit("IDLE_PROOF_HISTORY",
              ",\"event_id\":"+I64(g_force_eid)+
              ",\"value_id\":"+I64(g_force_vid)+
              ",\"scheduled_unix\":"+IntegerToString(g_force_sched)+
              ",\"n\":"+IntegerToString(n)+
              ",\"api_error\":0"+
              ",\"payload_unchanged\":true");
         bool idle_csv=CsvRow("IDLE_PROOF_HISTORY,"+Iso(TimeLocal())+","+Iso(TimeTradeServer())+","
            +Iso(TimeCurrent())+","+I64(GetTickCount64())+","
            +I64(g_force_eid)+","+I64(g_force_vid)+","+IntegerToString(g_force_sched)+","
            +IntegerToString(g_force_period)+",,,,,,,,,"+I64(g_force_hash)+",,,0,0,,,,,"
            +"terminal_observation_not_official_first_public");
         if(!idle_json || !idle_csv)
         {
            g_errors++;
            g_fatal=true;
            Emit("IO_ERROR_HISTORY",
                 ",\"event_id\":"+I64(eid)+",\"idle_receipt_written\":false,\"collector_fatal\":true");
            return;
         }
         g_oc[oix].idle_emitted=true;
         g_idle_ok++;
         if(!SaveOcc())
         {
            g_errors++;
            g_fatal=true;
            Emit("IO_ERROR_HISTORY",
                 ",\"event_id\":"+I64(eid)+",\"idle_state_written\":false,\"collector_fatal\":true");
            return;
         }
      }
      g_force_eid=0; g_force_vid=0;
   }
}

void DoPoll()
{
   if(g_nev<=0) return;
   datetime nows=TimeTradeServer();
   int due[]; int ndue=0; int nover=0;
   BuildDue(due,ndue,nover,nows);
   g_last_due_n=ndue+nover;
   g_last_future_n=CountFutureOcc(nows);

   if(nover>0)
   {
      g_gaps+=nover;
      Emit("GAP_OVERFLOW",
           ",\"due_set\":"+IntegerToString(g_last_due_n)+
           ",\"cap\":"+IntegerToString(DUE_CAP)+
           ",\"overflow\":"+IntegerToString(nover)+
           ",\"fail_closed\":true");
   }

   if(g_force_eid!=0)
   {
      DoHistory(g_force_eid,g_force_vid,g_force_sched,g_force_period,ndue);
      return;
   }

   if(ndue>0)
   {
      int pick=due[g_due_rr%ndue];
      g_due_rr++;
      long lat=(long)nows-g_oc[pick].scheduled;
      Emit("DUE_POLL",
           ",\"event_id\":"+I64(g_oc[pick].event_id)+
           ",\"due_set\":"+IntegerToString(g_last_due_n)+
           ",\"latency_sec\":"+IntegerToString(lat));
      DoHistory(g_oc[pick].event_id,g_oc[pick].value_id,g_oc[pick].scheduled,g_oc[pick].period,ndue);
      return;
   }

   int eix=g_rr%g_nev;
   g_rr=(g_rr+1)%g_nev;
   DoHistory(g_ev[eix].event_id,0,0,0,0);
}

void Step()
{
   g_polls++;
   if(g_fatal){ Heartbeat(); return; }
   if(!g_countries_ok) DoCountries();
   else if(!g_frozen) DoEnumOne();
   else DoPoll();
   Heartbeat();
}

int OnInit()
{
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
   {
      Print("EA_ProspectiveCalendarPITMQDemo v1.5.1 tester fail-closed");
      return(INIT_FAILED);
   }
   if(AccountInfoString(ACCOUNT_SERVER)!="MetaQuotes-Demo")
   {
      Print("HYP-CALENDAR-PIT-MQDEMO-001 server fail-closed: ",AccountInfoString(ACCOUNT_SERVER));
      return(INIT_FAILED);
   }
   if(MQLInfoInteger(MQL_TRADE_ALLOWED))
   {
      Print("HYP-CALENDAR-PIT-MQDEMO-001 requires EA Algo Trading permission OFF");
      return(INIT_FAILED);
   }
   FolderCreate("calendar_pit_mqdemo_001",FILE_COMMON);
   ResetMemory();
   if(!LoadCountries()){ Print("v1.5.1 corrupt countries"); return(INIT_FAILED); }
   if(!LoadCatalog()){ Print("v1.5.1 corrupt catalog"); return(INIT_FAILED); }
   if(!LoadOcc()){ Print("v1.5.1 corrupt occurrences"); return(INIT_FAILED); }
   if(HasDupEventIds()){ Print("v1.5.1 duplicate/zero event_id"); return(INIT_FAILED); }

   if(InpTimerMs>=100 && EventSetMillisecondTimer(InpTimerMs)) g_timer_ms=true;
   else EventSetTimer(1);

   Emit("INIT",
        ",\"events_loaded\":"+IntegerToString(g_nev)+
        ",\"occurrences_loaded\":"+IntegerToString(g_noc)+
        ",\"n_all_defs\":"+IntegerToString(g_nall)+
        ",\"catalog_frozen\":"+B01(g_frozen)+
        ",\"catalog_hash\":\""+I64(g_catalog_hash)+"\""+
        ",\"countries_loaded\":"+B01(g_countries_ok)+
        ",\"enum_ok_loaded\":"+IntegerToString(CountEnumOk())+
        ",\"timer_ms\":"+B01(g_timer_ms)+
        ",\"horizon_h\":48,\"pre_h\":6,\"post_h\":6");
   return(INIT_SUCCEEDED);
}

void OnTimer(){ Step(); }

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_frozen) SaveCatalog();
   SaveOcc();
   Emit("SHUTDOWN",
        ",\"reason\":"+IntegerToString(reason)+
        ",\"selected_events\":"+IntegerToString(g_nev)+
        ",\"occurrences\":"+IntegerToString(g_noc)+
        ",\"future_history_successes\":"+I64(g_future_ok)+
        ",\"idle_proofs\":"+I64(g_idle_ok)+
        ",\"observations\":"+I64(g_obs)+
        ",\"mutations\":"+I64(g_mut)+
        ",\"gaps\":"+I64(g_gaps)+
        ",\"api_errors\":"+I64(g_errors));
}

void OnTick(){}
//+------------------------------------------------------------------+

