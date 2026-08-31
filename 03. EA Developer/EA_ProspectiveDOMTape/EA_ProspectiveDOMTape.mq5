//+------------------------------------------------------------------+
//| EA_ProspectiveDOMTape.mq5  collector v1.1.1                      |
//| MarketBookAdd + OnBookEvent + MarketBookGet. Source only.        |
//| Exclusive JSON/CSV handles. High-water IDs. Session tick64.      |
//+------------------------------------------------------------------+
#property copyright "Prospective DOM tape v1.1.1 - not a trading system"
#property version   "1.101"
#property description "DOM full-book snapshot collector v1.1; trading disabled"

#define COLLECTOR_VER  "1.1.1"
#define SCHEMA_VER     "1.1"
#define FOLDER         "dom_tape/"
#define N_SYM          4
#define SNAP_BLOCK     10000
#define EV_BLOCK       10000

string g_sym[N_SYM] = {"XAUUSD","EURUSD","GBPUSD","USDJPY"};

struct SymSt
{
   bool     subscribed;
   ulong    ev_reserved;
   ulong    ev_used;
   ulong    last_hash;
   ulong    last_tick64;
   int      last_depth;
   datetime last_snap_local;
   ulong    snapshots;
   ulong    duplicates;
   ulong    empty;
   ulong    api_errors;
};

SymSt    g_s[N_SYM];
ulong    g_snap_reserved = 0;
ulong    g_snap_used = 0;
ulong    g_events = 0;
ulong    g_snapshots = 0;
ulong    g_duplicates = 0;
ulong    g_empty = 0;
ulong    g_api_errors = 0;
ulong    g_io_errors = 0;
ulong    g_session_tick64 = 0;
datetime g_hb_last = 0;
string   g_session = "";
int      g_hLock = INVALID_HANDLE;
int      g_hJson = INVALID_HANDLE;
int      g_hCsv  = INVALID_HANDLE;
bool     g_fatal = false;
bool     g_deinit = false;
bool     g_state_ok = false;
bool     g_stop_requested = false;

string Esc(string s)
{
   StringReplace(s,"\\","\\\\");
   StringReplace(s,"\"","\\\"");
   StringReplace(s,"\n"," ");
   StringReplace(s,"\r","");
   return s;
}
string Iso(const datetime t){ return TimeToString(t,TIME_DATE|TIME_SECONDS); }
string I64(const ulong v){ return IntegerToString((long)v); }
string B01(const bool v){ return (v?"true":"false"); }
string Px(const double p){ return DoubleToString(p,8); }
string Vr(const double v){ return DoubleToString(v,8); }

ulong Fnv(const string s)
{
   ulong h=1469598103934665603;
   ushort ch[];
   int n=StringToShortArray(s,ch);
   if(n>0) n--;
   for(int i=0;i<n;i++){ h^=(ulong)ch[i]; h*=1099511628211; }
   return h;
}

int FindSym(const string sym)
{
   for(int i=0;i<N_SYM;i++) if(g_sym[i]==sym) return i;
   return -1;
}

string SafetyJson()
{
   return "\"schema_version\":\""+SCHEMA_VER+"\","+
        "\"collector_version\":\""+COLLECTOR_VER+"\","+
        "\"session_id\":\""+Esc(g_session)+"\","+
        "\"terminal_build\":"+IntegerToString(TerminalInfoInteger(TERMINAL_BUILD))+","+
        "\"account_server\":\""+Esc(AccountInfoString(ACCOUNT_SERVER))+"\","+
        "\"recv_clock\":\"terminal_observation_not_official_first_public\","+
        "\"crash_partial_possible\":true,"+
        "\"transactional\":false,"+
        "\"outcome_accessed\":false,\"prices_read\":false,\"orders\":false,\"trading_disabled\":true";
}

string ClockHead()
{
   return "\"ts_local\":\""+Iso(TimeLocal())+"\","+
        "\"ts_server\":\""+Iso(TimeTradeServer())+"\","+
        "\"ts_current\":\""+Iso(TimeCurrent())+"\","+
        "\"tick64\":"+I64(GetTickCount64());
}

void ReleaseAll()
{
   for(int i=0;i<N_SYM;i++)
   {
      if(g_s[i].subscribed)
      {
         MarketBookRelease(g_sym[i]);
         g_s[i].subscribed=false;
      }
   }
}

void CloseHandles()
{
   if(g_hCsv!=INVALID_HANDLE){ FileFlush(g_hCsv); FileClose(g_hCsv); g_hCsv=INVALID_HANDLE; }
   if(g_hJson!=INVALID_HANDLE){ FileFlush(g_hJson); FileClose(g_hJson); g_hJson=INVALID_HANDLE; }
   if(g_hLock!=INVALID_HANDLE){ FileClose(g_hLock); g_hLock=INVALID_HANDLE; }
}

void FatalIo(const string where)
{
   if(g_fatal) return;
   g_fatal=true;
   int err=GetLastError();
   g_io_errors++;
   Print("EA_ProspectiveDOMTape FATAL_IO where=",where," err=",err);
   if(g_hJson!=INVALID_HANDLE)
   {
      FileSeek(g_hJson,0,SEEK_END);
      FileWriteString(g_hJson,
         "{\"kind\":\"IO_ERROR\","+ClockHead()+","+SafetyJson()+
         ",\"where\":\""+Esc(where)+"\",\"api_error\":"+IntegerToString(err)+
         ",\"fatal\":true}\n");
      FileFlush(g_hJson);
   }
   ReleaseAll();
   CloseHandles();
   if(!g_deinit) ExpertRemove();
}

bool Jline(const string obj)
{
   if(g_fatal || g_hJson==INVALID_HANDLE) return false;
   if(FileSeek(g_hJson,0,SEEK_END)==false) return false;
   if(FileWriteString(g_hJson,obj+"\n")==0) return false;
   FileFlush(g_hJson);
   return true;
}

void Emit(const string kind,const string extra)
{
   if(g_fatal) return;
   if(!Jline("{\"kind\":\""+kind+"\","+ClockHead()+","+SafetyJson()+extra+"}"))
      FatalIo("jsonl_"+kind);
}

void StopSource(const string kind,const string extra)
{
   if(g_stop_requested || g_fatal) return;
   Emit(kind,extra);
   if(g_fatal) return;
   g_stop_requested=true;
   ReleaseAll();
   ExpertRemove();
}

const string CSV_HDR=
   "kind,ts_local,ts_server,ts_current,tick64,symbol,"
   "event_seq,snapshot_seq,payload_hash,depth,level_index,"
   "type,price,volume,volume_real,session_id,recv_clock";

bool CsvLevels(const string symbol,const ulong evseq,const ulong snapseq,
               const ulong hv,const MqlBookInfo &book[],const int n)
{
   if(g_fatal || g_hCsv==INVALID_HANDLE) return false;
   if(FileSeek(g_hCsv,0,SEEK_END)==false) return false;
   string ts=Iso(TimeLocal())+","+Iso(TimeTradeServer())+","+Iso(TimeCurrent())+","+I64(GetTickCount64());
   for(int i=0;i<n;i++)
   {
      string line="SNAPSHOT,"+ts+","+symbol+","
         +I64(evseq)+","+I64(snapseq)+","+I64(hv)+","+IntegerToString(n)+","+IntegerToString(i)+","
         +IntegerToString((int)book[i].type)+","+Px(book[i].price)+","
         +IntegerToString(book[i].volume)+","+Vr(book[i].volume_real)+","
         +g_session+",terminal_observation_not_official_first_public\n";
      if(FileWriteString(g_hCsv,line)==0) return false;
   }
   FileFlush(g_hCsv);
   return true;
}

ulong HashBook(const string symbol,const MqlBookInfo &book[],const int n)
{
   string s=symbol+"|";
   for(int i=0;i<n;i++)
      s+=IntegerToString((int)book[i].type)+","+Px(book[i].price)+","
        +IntegerToString(book[i].volume)+","+Vr(book[i].volume_real)+";";
   return Fnv(s);
}

string StateBody()
{
   string b="schema="+SCHEMA_VER+"\n";
   b+="version="+COLLECTOR_VER+"\n";
   b+="symbols="+g_sym[0]+","+g_sym[1]+","+g_sym[2]+","+g_sym[3]+"\n";
   b+="snapshot_reserved="+I64(g_snap_reserved)+"\n";
   b+="snapshot_used="+I64(g_snap_used)+"\n";
   b+="events="+I64(g_events)+"\n";
   b+="snapshots="+I64(g_snapshots)+"\n";
   b+="duplicates="+I64(g_duplicates)+"\n";
   b+="empty="+I64(g_empty)+"\n";
   b+="api_errors="+I64(g_api_errors)+"\n";
   b+="io_errors="+I64(g_io_errors)+"\n";
   for(int i=0;i<N_SYM;i++)
      b+="S\t"+g_sym[i]+"\t"+I64(g_s[i].ev_reserved)+"\t"+I64(g_s[i].ev_used)+"\t"
        +I64(g_s[i].last_hash)+"\t"+IntegerToString(g_s[i].last_depth)+"\t"
        +I64(g_s[i].snapshots)+"\t"+I64(g_s[i].duplicates)+"\t"+I64(g_s[i].empty)+"\n";
   return b;
}

bool SaveState()
{
   if(g_fatal) return false;
   ResetLastError();
   string tmp=FOLDER+"dom_state_v1_1.tmp";
   string dst=FOLDER+"dom_state_v1_1.txt";
   int h=FileOpen(tmp,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return false;
   if(FileWriteString(h,StateBody())==0){ FileClose(h); return false; }
   FileFlush(h);
   FileClose(h);
   if(!FileMove(tmp,FILE_COMMON,dst,FILE_COMMON|FILE_REWRITE))
   {
      if(!FileCopy(tmp,FILE_COMMON,dst,FILE_COMMON|FILE_REWRITE)) return false;
      FileDelete(tmp,FILE_COMMON);
   }
   return true;
}

bool ParseU(const string line,const string key,ulong &out)
{
   if(StringFind(line,key)!=0) return false;
   string raw=StringSubstr(line,StringLen(key));
   int n=StringLen(raw);
   if(n<=0) return false;
   for(int i=0;i<n;i++)
   {
      ushort c=StringGetCharacter(raw,i);
      if(c<48 || c>57) return false;
   }
   long value=StringToInteger(raw);
   if(value<0) return false;
   out=(ulong)value;
   return true;
}

bool LoadState()
{
   string p=FOLDER+"dom_state_v1_1.txt";
   if(!FileIsExist(p,FILE_COMMON)) return true;
   int h=FileOpen(p,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,0,CP_UTF8);
   if(h==INVALID_HANDLE) return false;
   bool saw_schema=false,saw_ver=false,saw_syms=false;
   bool saw_sr=false,saw_su=false,saw_ev=false,saw_sn=false;
   bool saw_du=false,saw_em=false,saw_api=false,saw_io=false;
   int ns=0;
   bool seen[N_SYM];
   for(int i=0;i<N_SYM;i++) seen[i]=false;
   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringFind(line,"schema=")==0)
      {
         if(saw_schema || StringSubstr(line,7)!=SCHEMA_VER){ FileClose(h); return false; }
         saw_schema=true;
      }
      else if(StringFind(line,"version=")==0)
      {
         if(saw_ver || StringSubstr(line,8)!=COLLECTOR_VER){ FileClose(h); return false; }
         saw_ver=true;
      }
      else if(StringFind(line,"symbols=")==0)
      {
         if(saw_syms || StringSubstr(line,8)!=g_sym[0]+","+g_sym[1]+","+g_sym[2]+","+g_sym[3])
         { FileClose(h); return false; }
         saw_syms=true;
      }
      else if(StringFind(line,"snapshot_reserved=")==0)
      { if(saw_sr || !ParseU(line,"snapshot_reserved=",g_snap_reserved)){ FileClose(h); return false; } saw_sr=true; }
      else if(StringFind(line,"snapshot_used=")==0)
      { if(saw_su || !ParseU(line,"snapshot_used=",g_snap_used)){ FileClose(h); return false; } saw_su=true; }
      else if(StringFind(line,"events=")==0)
      { if(saw_ev || !ParseU(line,"events=",g_events)){ FileClose(h); return false; } saw_ev=true; }
      else if(StringFind(line,"snapshots=")==0)
      { if(saw_sn || !ParseU(line,"snapshots=",g_snapshots)){ FileClose(h); return false; } saw_sn=true; }
      else if(StringFind(line,"duplicates=")==0)
      { if(saw_du || !ParseU(line,"duplicates=",g_duplicates)){ FileClose(h); return false; } saw_du=true; }
      else if(StringFind(line,"empty=")==0)
      { if(saw_em || !ParseU(line,"empty=",g_empty)){ FileClose(h); return false; } saw_em=true; }
      else if(StringFind(line,"api_errors=")==0)
      { if(saw_api || !ParseU(line,"api_errors=",g_api_errors)){ FileClose(h); return false; } saw_api=true; }
      else if(StringFind(line,"io_errors=")==0)
      { if(saw_io || !ParseU(line,"io_errors=",g_io_errors)){ FileClose(h); return false; } saw_io=true; }
      else if(StringFind(line,"S\t")==0)
      {
         string f[];
         if(StringSplit(line,'\t',f)!=9){ FileClose(h); return false; }
         int ix=FindSym(f[1]);
         if(ix<0 || seen[ix]){ FileClose(h); return false; }
         ulong parsed=0;
         if(!ParseU("v="+f[2],"v=",parsed)){ FileClose(h); return false; }
         g_s[ix].ev_reserved=parsed;
         if(!ParseU("v="+f[3],"v=",parsed)){ FileClose(h); return false; }
         g_s[ix].ev_used=parsed;
         g_s[ix].last_hash=(ulong)StringToInteger(f[4]);
         g_s[ix].last_depth=(int)StringToInteger(f[5]);
         if(!ParseU("v="+f[6],"v=",parsed)){ FileClose(h); return false; }
         g_s[ix].snapshots=parsed;
         if(!ParseU("v="+f[7],"v=",parsed)){ FileClose(h); return false; }
         g_s[ix].duplicates=parsed;
         if(!ParseU("v="+f[8],"v=",parsed)){ FileClose(h); return false; }
         g_s[ix].empty=parsed;
         if(g_s[ix].last_depth<0){ FileClose(h); return false; }
         g_s[ix].last_tick64=0;
         seen[ix]=true;
         ns++;
      }
      else if(StringLen(line)>0)
      { FileClose(h); return false; }
   }
   FileClose(h);
   if(!saw_schema || !saw_ver || !saw_syms || !saw_sr || !saw_su ||
      !saw_ev || !saw_sn || !saw_du || !saw_em || !saw_api || !saw_io || ns!=N_SYM)
      return false;
   if(g_snap_used>g_snap_reserved) return false;
   for(int i=0;i<N_SYM;i++) if(g_s[i].ev_used>g_s[i].ev_reserved) return false;
   g_snap_used=g_snap_reserved;
   for(int i=0;i<N_SYM;i++) g_s[i].ev_used=g_s[i].ev_reserved;
   return true;
}

bool ReserveSnap()
{
   if(g_snap_used<g_snap_reserved) return true;
   ulong floor=g_snap_reserved;
   g_snap_reserved=floor+(ulong)SNAP_BLOCK;
   if(g_snap_reserved<=floor) return false;
   if(!SaveState()) return false;
   return true;
}

bool ReserveEv(const int ix)
{
   if(g_s[ix].ev_used<g_s[ix].ev_reserved) return true;
   ulong floor=g_s[ix].ev_reserved;
   g_s[ix].ev_reserved=floor+(ulong)EV_BLOCK;
   if(g_s[ix].ev_reserved<=floor) return false;
   if(!SaveState()) return false;
   return true;
}

bool OpenAppendExclusive(const string name,const bool csv,int &out_h)
{
   string p=FOLDER+name;
   int h=FileOpen(p,FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ,0,CP_UTF8);
   if(h==INVALID_HANDLE) return false;
   ulong sz=FileSize(h);
   if(sz==0)
   {
      if(csv && FileWriteString(h,CSV_HDR+"\n")==0){ FileClose(h); return false; }
      FileFlush(h);
   }
   if(FileSeek(h,0,SEEK_END)==false){ FileClose(h); return false; }
   out_h=h;
   return true;
}

void Heartbeat()
{
   if(g_fatal || g_deinit || g_stop_requested) return;
   datetime now=TimeLocal();
   if(g_hb_last!=0 && now-g_hb_last<30) return;
   g_hb_last=now;
   string per="";
   for(int i=0;i<N_SYM;i++)
   {
      long age=(g_s[i].last_snap_local==0?-1:(long)(now-g_s[i].last_snap_local));
      if(i>0) per+=",";
      per+="{\"symbol\":\""+g_sym[i]+"\",\"subscribed\":"+B01(g_s[i].subscribed)
         +",\"event_seq\":"+I64(g_s[i].ev_used)
         +",\"event_reserved\":"+I64(g_s[i].ev_reserved)
         +",\"last_depth\":"+IntegerToString(g_s[i].last_depth)
         +",\"age_sec\":"+IntegerToString(age)
         +",\"snapshots\":"+I64(g_s[i].snapshots)
         +",\"duplicates\":"+I64(g_s[i].duplicates)
         +",\"empty\":"+I64(g_s[i].empty)
         +",\"api_errors\":"+I64(g_s[i].api_errors)+"}";
   }
   Emit("HEARTBEAT",
        ",\"events\":"+I64(g_events)+
        ",\"snapshots\":"+I64(g_snapshots)+
        ",\"duplicates\":"+I64(g_duplicates)+
        ",\"empty\":"+I64(g_empty)+
        ",\"api_errors\":"+I64(g_api_errors)+
        ",\"io_errors\":"+I64(g_io_errors)+
        ",\"snapshot_used\":"+I64(g_snap_used)+
        ",\"snapshot_reserved\":"+I64(g_snap_reserved)+
        ",\"symbols\":["+per+"]");
   if(g_fatal) return;
   if(!SaveState()) FatalIo("state_heartbeat");
}

int OnInit()
{
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
   {
      Print("EA_ProspectiveDOMTape v1.1.1 tester fail-closed");
      return(INIT_FAILED);
   }

   FolderCreate("dom_tape",FILE_COMMON);
   for(int i=0;i<N_SYM;i++)
   {
      ZeroMemory(g_s[i]);
      g_s[i].subscribed=false;
      g_s[i].last_tick64=0;
   }
   g_snap_reserved=0; g_snap_used=0;
   g_events=0; g_snapshots=0; g_duplicates=0; g_empty=0;
   g_api_errors=0; g_io_errors=0; g_session_tick64=0;
   g_hb_last=0; g_fatal=false; g_deinit=false; g_state_ok=false; g_stop_requested=false;
   g_hLock=INVALID_HANDLE; g_hJson=INVALID_HANDLE; g_hCsv=INVALID_HANDLE;
   g_session=IntegerToString((long)TimeLocal())+"-"+I64(GetTickCount64());

   g_hLock=FileOpen(FOLDER+"dom_writer_v1_1.lock",
                    FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(g_hLock==INVALID_HANDLE)
   {
      Print("EA_ProspectiveDOMTape WRITER_LOCK failed - second instance or lock busy");
      return(INIT_FAILED);
   }
   FileWriteString(g_hLock,"session_id="+g_session+"\nversion="+COLLECTOR_VER+"\n");
   FileFlush(g_hLock);

   if(!LoadState())
   {
      Print("EA_ProspectiveDOMTape corrupt/invalid dom_state_v1_1.txt - no silent reset");
      CloseHandles();
      return(INIT_FAILED);
   }
   g_state_ok=true;

   if(!OpenAppendExclusive("dom_tape_v1_1.jsonl",false,g_hJson))
   {
      Print("EA_ProspectiveDOMTape exclusive JSON open failed");
      CloseHandles();
      return(INIT_FAILED);
   }
   if(!OpenAppendExclusive("dom_levels_v1_1.csv",true,g_hCsv))
   {
      Print("EA_ProspectiveDOMTape exclusive CSV open failed");
      CloseHandles();
      return(INIT_FAILED);
   }

   Emit("WRITER_LOCK",",\"lock\":\"dom_writer_v1_1.lock\",\"share_write\":false");
   if(g_fatal){ CloseHandles(); return(INIT_FAILED); }

   for(int i=0;i<N_SYM;i++)
   {
      ResetLastError();
      if(!MarketBookAdd(g_sym[i]))
      {
         int err=GetLastError();
         Print("MarketBookAdd failed ",g_sym[i]," ",err);
         Emit("API_ERROR_BOOK",",\"symbol\":\""+g_sym[i]+"\",\"where\":\"MarketBookAdd\",\"api_error\":"+IntegerToString(err));
         ReleaseAll();
         CloseHandles();
         return(INIT_FAILED);
      }
      g_s[i].subscribed=true;
      Emit("SUBSCRIBE",",\"symbol\":\""+g_sym[i]+"\",\"index\":"+IntegerToString(i));
      if(g_fatal){ ReleaseAll(); CloseHandles(); return(INIT_FAILED); }
   }

   ResetLastError();
   if(!EventSetTimer(30))
   {
      int err=GetLastError();
      Emit("API_ERROR_TIMER",",\"where\":\"EventSetTimer\",\"api_error\":"+IntegerToString(err));
      ReleaseAll();
      CloseHandles();
      return(INIT_FAILED);
   }

   Emit("INIT",
        ",\"symbols\":[\"XAUUSD\",\"EURUSD\",\"GBPUSD\",\"USDJPY\"]"+
        ",\"snapshot_used\":"+I64(g_snap_used)+
        ",\"snapshot_reserved\":"+I64(g_snap_reserved)+
        ",\"events_loaded\":"+I64(g_events)+
        ",\"snapshots_loaded\":"+I64(g_snapshots)+
        ",\"high_water_jump\":true"+
        ",\"state_loaded\":"+B01(FileIsExist(FOLDER+"dom_state_v1_1.txt",FILE_COMMON)));
   if(g_fatal){ ReleaseAll(); CloseHandles(); return(INIT_FAILED); }
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   g_deinit=true;
   EventKillTimer();
   ReleaseAll();
   if(!g_fatal && g_hJson!=INVALID_HANDLE)
   {
      Emit("SHUTDOWN",
           ",\"reason\":"+IntegerToString(reason)+
           ",\"events\":"+I64(g_events)+
           ",\"snapshots\":"+I64(g_snapshots)+
           ",\"duplicates\":"+I64(g_duplicates)+
           ",\"empty\":"+I64(g_empty)+
           ",\"api_errors\":"+I64(g_api_errors)+
           ",\"io_errors\":"+I64(g_io_errors)+
           ",\"snapshot_used\":"+I64(g_snap_used)+
           ",\"snapshot_reserved\":"+I64(g_snap_reserved));
      if(g_state_ok && !SaveState()) FatalIo("state_deinit");
   }
   CloseHandles();
}

void OnTimer(){ Heartbeat(); }

void OnBookEvent(const string &symbol)
{
   if(g_fatal || g_deinit || g_stop_requested) return;
   int ix=FindSym(symbol);
   if(ix<0) return;

   ulong tick=GetTickCount64();
   if(g_session_tick64!=0 && tick<g_session_tick64)
   {
      StopSource("TICK64_REGRESS",
           ",\"symbol\":\""+symbol+"\""+
           ",\"prev\":"+I64(g_session_tick64)+
           ",\"now\":"+I64(tick));
      return;
   }
   g_session_tick64=tick;
   g_s[ix].last_tick64=tick;

   if(!ReserveEv(ix))
   {
      FatalIo("reserve_event");
      return;
   }
   g_s[ix].ev_used++;
   g_events++;

   MqlBookInfo book[];
   ResetLastError();
   if(!MarketBookGet(symbol,book))
   {
      int err=GetLastError();
      g_api_errors++;
      g_s[ix].api_errors++;
      StopSource("API_ERROR_BOOK",
           ",\"symbol\":\""+symbol+"\""+
           ",\"where\":\"MarketBookGet\""+
           ",\"api_error\":"+IntegerToString(err)+
           ",\"event_seq\":"+I64(g_s[ix].ev_used));
      return;
   }

   int n=ArraySize(book);
   if(n<=0)
   {
      g_empty++;
      g_s[ix].empty++;
      StopSource("EMPTY_BOOK",
           ",\"symbol\":\""+symbol+"\""+
           ",\"event_seq\":"+I64(g_s[ix].ev_used)+
           ",\"depth\":0");
      return;
   }

   ulong hv=HashBook(symbol,book,n);
   if(g_s[ix].last_hash!=0 && hv==g_s[ix].last_hash)
   {
      g_duplicates++;
      g_s[ix].duplicates++;
      Emit("DUPLICATE",
           ",\"symbol\":\""+symbol+"\""+
           ",\"event_seq\":"+I64(g_s[ix].ev_used)+
           ",\"payload_hash\":\""+I64(hv)+"\""+
           ",\"depth\":"+IntegerToString(n)+
           ",\"duplicate_count\":"+I64(g_s[ix].duplicates));
      return;
   }

   if(!ReserveSnap())
   {
      FatalIo("reserve_snapshot");
      return;
   }
   g_snap_used++;
   ulong snap=g_snap_used;

   string levels="[";
   for(int i=0;i<n;i++)
   {
      if(i>0) levels+=",";
      levels+="{\"i\":"+IntegerToString(i)
         +",\"type\":"+IntegerToString((int)book[i].type)
         +",\"price\":"+Px(book[i].price)
         +",\"volume\":"+IntegerToString(book[i].volume)
         +",\"volume_real\":"+Vr(book[i].volume_real)+"}";
   }
   levels+="]";

   string snapj="{\"kind\":\"SNAPSHOT\","+ClockHead()+","+SafetyJson()
      +",\"symbol\":\""+symbol+"\""
      +",\"event_seq\":"+I64(g_s[ix].ev_used)
      +",\"snapshot_seq\":"+I64(snap)
      +",\"payload_hash\":\""+I64(hv)+"\""
      +",\"depth\":"+IntegerToString(n)
      +",\"levels\":"+levels+"}";

   if(!Jline(snapj))
   {
      FatalIo("snapshot_jsonl");
      return;
   }
   if(!CsvLevels(symbol,g_s[ix].ev_used,snap,hv,book,n))
   {
      FatalIo("snapshot_csv");
      return;
   }

   g_snapshots++;
   g_s[ix].snapshots++;
   g_s[ix].last_hash=hv;
   g_s[ix].last_depth=n;
   g_s[ix].last_snap_local=TimeLocal();
}

void OnTick(){}
//+------------------------------------------------------------------+
