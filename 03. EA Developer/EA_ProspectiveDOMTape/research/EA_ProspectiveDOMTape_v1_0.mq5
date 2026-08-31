//+------------------------------------------------------------------+
//| EA_ProspectiveDOMTape.mq5  collector v1.0.0                      |
//| MarketBookAdd + OnBookEvent + MarketBookGet. Source only.        |
//| Tester fail-closed. No ticks, bars, calendar, orders, signals.   |
//+------------------------------------------------------------------+
#property copyright "Prospective DOM tape v1.0.0 - not a trading system"
#property version   "1.000"
#property description "DOM full-book snapshot collector; trading disabled"

#define COLLECTOR_VER  "1.0.0"
#define SCHEMA_VER     "1"
#define FOLDER         "dom_tape/"
#define N_SYM          4

string g_sym[N_SYM] = {"XAUUSD","EURUSD","GBPUSD","USDJPY"};

struct SymSt
{
   bool     subscribed;
   ulong    event_seq;
   ulong    last_hash;
   ulong    last_tick64;
   int      last_depth;
   datetime last_snap_local;
   ulong    snapshots;
   ulong    duplicates;
   ulong    empty;
   ulong    api_errors;
   ulong    tick_regress;
};

SymSt    g_s[N_SYM];
ulong    g_snapshot_seq = 0;
ulong    g_events = 0;
ulong    g_snapshots = 0;
ulong    g_duplicates = 0;
ulong    g_empty = 0;
ulong    g_api_errors = 0;
ulong    g_io_errors = 0;
datetime g_hb_last = 0;
bool     g_state_ok = false;

string Esc(string s)
{
   StringReplace(s,"\\","\\\\"); StringReplace(s,"\"","\\\"");
   StringReplace(s,"\n"," "); StringReplace(s,"\r","");
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
   return "\"schema_version\":\""+SCHEMA_VER+"\","
        +"\"collector_version\":\""+COLLECTOR_VER+"\","
        +"\"terminal_build\":"+IntegerToString(TerminalInfoInteger(TERMINAL_BUILD))+","
        +"\"account_server\":\""+Esc(AccountInfoString(ACCOUNT_SERVER))+"\","
        +"\"recv_clock\":\"terminal_observation_not_official_first_public\","
        +"\"outcome_accessed\":false,\"prices_read\":false,\"orders\":false,\"trading_disabled\":true";
}

string ClockHead()
{
   return "\"ts_local\":\""+Iso(TimeLocal())+"\","
        +"\"ts_server\":\""+Iso(TimeTradeServer())+"\","
        +"\"ts_current\":\""+Iso(TimeCurrent())+"\","
        +"\"tick64\":"+I64(GetTickCount64());
}

int OpenAppend(const string name,const bool csv_hdr,const string header)
{
   string p=FOLDER+name;
   bool exists=FileIsExist(p,FILE_COMMON);
   int h=FileOpen(p,FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE)
      h=FileOpen(p,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return INVALID_HANDLE;
   FileSeek(h,0,SEEK_END);
   if(!exists && csv_hdr)
   {
      uchar bom[3]; bom[0]=0xEF; bom[1]=0xBB; bom[2]=0xBF;
      FileWriteArray(h,bom,0,3);
      FileWriteString(h,header+"\n");
   }
   return h;
}

bool Jline(const string obj)
{
   int h=OpenAppend("dom_tape_v1.jsonl",false,"");
   if(h==INVALID_HANDLE) return false;
   uint w=FileWriteString(h,obj+"\n");
   FileFlush(h);
   FileClose(h);
   return (w>0);
}

const string CSV_HDR=
   "kind,ts_local,ts_server,ts_current,tick64,symbol,"
   "event_seq,snapshot_seq,payload_hash,depth,level_index,"
   "type,price,volume,volume_real,recv_clock";

bool CsvLevels(const string symbol,const ulong evseq,const ulong snapseq,
               const ulong hv,const MqlBookInfo &book[],const int n)
{
   int h=OpenAppend("dom_levels_v1.csv",true,CSV_HDR);
   if(h==INVALID_HANDLE) return false;
   string ts=Iso(TimeLocal())+","+Iso(TimeTradeServer())+","+Iso(TimeCurrent())+","+I64(GetTickCount64());
   for(int i=0;i<n;i++)
   {
      string line="SNAPSHOT,"+ts+","+symbol+","
         +I64(evseq)+","+I64(snapseq)+","+I64(hv)+","+IntegerToString(n)+","+IntegerToString(i)+","
         +IntegerToString((int)book[i].type)+","+Px(book[i].price)+","
         +IntegerToString(book[i].volume)+","+Vr(book[i].volume_real)+","
         +"terminal_observation_not_official_first_public\n";
      if(FileWriteString(h,line)==0){ FileClose(h); return false; }
   }
   FileFlush(h);
   FileClose(h);
   return true;
}

void Emit(const string kind,const string extra)
{
   if(!Jline("{\"kind\":\""+kind+"\","+ClockHead()+","+SafetyJson()+extra+"}"))
   {
      g_io_errors++;
      Print("IO_ERROR jsonl ",kind," ",GetLastError());
   }
}

void IoError(const string where,const int err)
{
   g_io_errors++;
   Jline("{\"kind\":\"IO_ERROR\","+ClockHead()+","+SafetyJson()+
         ",\"where\":\""+Esc(where)+"\",\"api_error\":"+IntegerToString(err)+"}");
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
   b+="snapshot_seq="+I64(g_snapshot_seq)+"\n";
   b+="events="+I64(g_events)+"\n";
   b+="snapshots="+I64(g_snapshots)+"\n";
   b+="duplicates="+I64(g_duplicates)+"\n";
   b+="empty="+I64(g_empty)+"\n";
   b+="api_errors="+I64(g_api_errors)+"\n";
   b+="io_errors="+I64(g_io_errors)+"\n";
   for(int i=0;i<N_SYM;i++)
      b+="S\t"+g_sym[i]+"\t"+I64(g_s[i].event_seq)+"\t"+I64(g_s[i].last_hash)+"\t"
        +I64(g_s[i].last_tick64)+"\t"+IntegerToString(g_s[i].last_depth)+"\t"
        +I64(g_s[i].snapshots)+"\t"+I64(g_s[i].duplicates)+"\t"+I64(g_s[i].empty)+"\n";
   return b;
}

bool SaveStateAtomic()
{
   string tmp=FOLDER+"dom_state_v1.tmp";
   string dst=FOLDER+"dom_state_v1.txt";
   int h=FileOpen(tmp,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE){ IoError("state_tmp_open",GetLastError()); return false; }
   if(FileWriteString(h,StateBody())==0){ FileClose(h); IoError("state_tmp_write",GetLastError()); return false; }
   FileFlush(h);
   FileClose(h);
   if(!FileMove(tmp,FILE_COMMON,dst,FILE_COMMON|FILE_REWRITE))
   {
      if(!FileCopy(tmp,FILE_COMMON,dst,FILE_REWRITE|FILE_COMMON))
      { IoError("state_move",GetLastError()); return false; }
      FileDelete(tmp,FILE_COMMON);
   }
   return true;
}

bool ParseU(const string line,const string key,ulong &out)
{
   if(StringFind(line,key)!=0) return false;
   out=(ulong)StringToInteger(StringSubstr(line,StringLen(key)));
   return true;
}

bool LoadState()
{
   string p=FOLDER+"dom_state_v1.txt";
   if(!FileIsExist(p,FILE_COMMON)) return true;
   int h=FileOpen(p,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
   if(h==INVALID_HANDLE) return false;
   bool saw_schema=false,saw_ver=false,saw_syms=false;
   int ns=0;
   bool seen[N_SYM];
   for(int i=0;i<N_SYM;i++) seen[i]=false;
   while(!FileIsEnding(h))
   {
      string line=FileReadString(h);
      if(StringFind(line,"schema=")==0)
      {
         if(StringSubstr(line,7)!=SCHEMA_VER){ FileClose(h); return false; }
         saw_schema=true;
      }
      else if(StringFind(line,"version=")==0)
      {
         if(StringSubstr(line,8)!=COLLECTOR_VER){ FileClose(h); return false; }
         saw_ver=true;
      }
      else if(StringFind(line,"symbols=")==0)
      {
         if(StringSubstr(line,8)!=g_sym[0]+","+g_sym[1]+","+g_sym[2]+","+g_sym[3])
         { FileClose(h); return false; }
         saw_syms=true;
      }
      else if(ParseU(line,"snapshot_seq=",g_snapshot_seq)) {}
      else if(ParseU(line,"events=",g_events)) {}
      else if(ParseU(line,"snapshots=",g_snapshots)) {}
      else if(ParseU(line,"duplicates=",g_duplicates)) {}
      else if(ParseU(line,"empty=",g_empty)) {}
      else if(ParseU(line,"api_errors=",g_api_errors)) {}
      else if(ParseU(line,"io_errors=",g_io_errors)) {}
      else if(StringFind(line,"S\t")==0)
      {
         string f[];
         if(StringSplit(line,'\t',f)<9){ FileClose(h); return false; }
         int ix=FindSym(f[1]);
         if(ix<0 || seen[ix]){ FileClose(h); return false; }
         seen[ix]=true;
         g_s[ix].event_seq=(ulong)StringToInteger(f[2]);
         g_s[ix].last_hash=(ulong)StringToInteger(f[3]);
         g_s[ix].last_tick64=(ulong)StringToInteger(f[4]);
         g_s[ix].last_depth=(int)StringToInteger(f[5]);
         g_s[ix].snapshots=(ulong)StringToInteger(f[6]);
         g_s[ix].duplicates=(ulong)StringToInteger(f[7]);
         g_s[ix].empty=(ulong)StringToInteger(f[8]);
         ns++;
      }
   }
   FileClose(h);
   if(!saw_schema || !saw_ver || !saw_syms || ns!=N_SYM) return false;
   return true;
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

void Heartbeat()
{
   datetime now=TimeLocal();
   if(now-g_hb_last<30 && g_hb_last!=0) return;
   g_hb_last=now;
   string per="";
   for(int i=0;i<N_SYM;i++)
   {
      long age=(g_s[i].last_snap_local==0?-1:(long)(now-g_s[i].last_snap_local));
      if(i>0) per+=",";
      per+="{\"symbol\":\""+g_sym[i]+"\",\"subscribed\":"+B01(g_s[i].subscribed)
         +",\"event_seq\":"+I64(g_s[i].event_seq)
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
        ",\"snapshot_seq\":"+I64(g_snapshot_seq)+
        ",\"symbols\":["+per+"]");
}

int OnInit()
{
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
   {
      Print("EA_ProspectiveDOMTape v1.0.0 tester fail-closed");
      return(INIT_FAILED);
   }
   FolderCreate("dom_tape",FILE_COMMON);
   for(int i=0;i<N_SYM;i++)
   {
      ZeroMemory(g_s[i]);
      g_s[i].subscribed=false;
   }
   g_snapshot_seq=0; g_events=0; g_snapshots=0; g_duplicates=0;
   g_empty=0; g_api_errors=0; g_io_errors=0; g_hb_last=0; g_state_ok=false;

   if(!LoadState())
   {
      Print("EA_ProspectiveDOMTape corrupt/invalid dom_state_v1.txt - no silent reset");
      return(INIT_FAILED);
   }
   g_state_ok=true;

   for(int i=0;i<N_SYM;i++)
   {
      ResetLastError();
      if(!MarketBookAdd(g_sym[i]))
      {
         int err=GetLastError();
         Emit("API_ERROR_BOOK",",\"symbol\":\""+g_sym[i]+"\",\"where\":\"MarketBookAdd\",\"api_error\":"+IntegerToString(err));
         ReleaseAll();
         Print("MarketBookAdd failed ",g_sym[i]," ",err);
         return(INIT_FAILED);
      }
      g_s[i].subscribed=true;
      Emit("SUBSCRIBE",",\"symbol\":\""+g_sym[i]+"\",\"index\":"+IntegerToString(i));
   }

   if(!EventSetTimer(30))
   {
      int err=GetLastError();
      Emit("IO_ERROR",",\"where\":\"EventSetTimer\",\"api_error\":"+IntegerToString(err));
      ReleaseAll();
      return(INIT_FAILED);
   }
   Emit("INIT",
        ",\"symbols\":[\"XAUUSD\",\"EURUSD\",\"GBPUSD\",\"USDJPY\"]"+
        ",\"snapshot_seq\":"+I64(g_snapshot_seq)+
        ",\"events_loaded\":"+I64(g_events)+
        ",\"snapshots_loaded\":"+I64(g_snapshots)+
        ",\"state_loaded\":"+B01(FileIsExist(FOLDER+"dom_state_v1.txt",FILE_COMMON)));
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ReleaseAll();
   if(g_state_ok) SaveStateAtomic();
   Emit("SHUTDOWN",
        ",\"reason\":"+IntegerToString(reason)+
        ",\"events\":"+I64(g_events)+
        ",\"snapshots\":"+I64(g_snapshots)+
        ",\"duplicates\":"+I64(g_duplicates)+
        ",\"empty\":"+I64(g_empty)+
        ",\"api_errors\":"+I64(g_api_errors)+
        ",\"io_errors\":"+I64(g_io_errors)+
        ",\"snapshot_seq\":"+I64(g_snapshot_seq));
}

void OnTimer(){ Heartbeat(); }

void OnBookEvent(const string &symbol)
{
   int ix=FindSym(symbol);
   if(ix<0) return;

   g_events++;
   g_s[ix].event_seq++;

   ulong tick=GetTickCount64();
   if(g_s[ix].last_tick64!=0 && tick<g_s[ix].last_tick64)
   {
      g_s[ix].tick_regress++;
      Emit("TICK64_REGRESS",
           ",\"symbol\":\""+symbol+"\""+
           ",\"prev\":"+I64(g_s[ix].last_tick64)+
           ",\"now\":"+I64(tick)+
           ",\"event_seq\":"+I64(g_s[ix].event_seq));
   }
   g_s[ix].last_tick64=tick;

   MqlBookInfo book[];
   ResetLastError();
   if(!MarketBookGet(symbol,book))
   {
      int err=GetLastError();
      g_api_errors++;
      g_s[ix].api_errors++;
      Emit("API_ERROR_BOOK",
           ",\"symbol\":\""+symbol+"\""+
           ",\"where\":\"MarketBookGet\""+
           ",\"api_error\":"+IntegerToString(err)+
           ",\"event_seq\":"+I64(g_s[ix].event_seq));
      return;
   }

   int n=ArraySize(book);
   if(n<=0)
   {
      g_empty++;
      g_s[ix].empty++;
      Emit("EMPTY_BOOK",
           ",\"symbol\":\""+symbol+"\""+
           ",\"event_seq\":"+I64(g_s[ix].event_seq)+
           ",\"depth\":0");
      return;
   }

   ulong hv=HashBook(symbol,book,n);
   if(hv==g_s[ix].last_hash && g_s[ix].last_hash!=0)
   {
      g_duplicates++;
      g_s[ix].duplicates++;
      Emit("DUPLICATE",
           ",\"symbol\":\""+symbol+"\""+
           ",\"event_seq\":"+I64(g_s[ix].event_seq)+
           ",\"payload_hash\":\""+I64(hv)+"\""+
           ",\"depth\":"+IntegerToString(n)+
           ",\"duplicate_count\":"+I64(g_s[ix].duplicates));
      return;
   }

   ulong new_snap=g_snapshot_seq+1;
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

   string snap="{\"kind\":\"SNAPSHOT\","+ClockHead()+","+SafetyJson()
      +",\"symbol\":\""+symbol+"\""
      +",\"event_seq\":"+I64(g_s[ix].event_seq)
      +",\"snapshot_seq\":"+I64(new_snap)
      +",\"payload_hash\":\""+I64(hv)+"\""
      +",\"depth\":"+IntegerToString(n)
      +",\"levels\":"+levels+"}";

   if(!Jline(snap))
   {
      IoError("snapshot_jsonl",GetLastError());
      return;
   }
   if(!CsvLevels(symbol,g_s[ix].event_seq,new_snap,hv,book,n))
   {
      IoError("snapshot_csv",GetLastError());
      return;
   }

   g_snapshot_seq=new_snap;
   g_snapshots++;
   g_s[ix].snapshots++;
   g_s[ix].last_hash=hv;
   g_s[ix].last_depth=n;
   g_s[ix].last_snap_local=TimeLocal();

   if(!SaveStateAtomic())
      IoError("state_after_snapshot",GetLastError());
}

void OnTick(){}
//+------------------------------------------------------------------+
