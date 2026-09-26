//+------------------------------------------------------------------+
//|                                               PA_Perception.mqh  |
//|  PA-PRO EA lane - Perception v1 object model + snapshot importer.|
//|                                                                  |
//|  Mirrors research/perception/schema/perception_v1.json (emitted  |
//|  by the PERCEPTION lane) projected onto a flat CSV wire format    |
//|  (perception_csv_v1).  MQL5 never parses JSON: a Python projector|
//|  (tools/jsonl_to_csv.py, planned) converts the engine's JSONL     |
//|  snapshots to this CSV.                                          |
//|                                                                  |
//|  CSV columns (13 with parity column, 12 flat):                   |
//|                                                                  |
//|    [bar_t,]id,type,state,role,t_birth,t1,t2,p1,p2,letter,side,why|
//|                                                                  |
//|    bar_t   optional leading column -> per-bar snapshot stream    |
//|            (parity mode): the row is "the object as seen at bar  |
//|            bar_t".  Flat files omit it; the viewer then uses     |
//|            every row, or the newest bar_t group <= the window    |
//|            right edge when the column exists.                    |
//|    id      string (schema: "box_7", "lvl_2", ...)                |
//|    type    BOX|RANGE_OPEN|CONTEXT_RANGE|PATTERN_LINE|            |
//|            CONTEXT_LINE|LEVEL_CARRIED|MINI_LEVEL|SQUEEZE|        |
//|            LABEL_TF|BRACKET|FALSE_EXT  (+ provisional STAND_ASIDE|
//|            pseudo-type for the top-level stand_aside[] codes)    |
//|    state   PROVISIONAL|CONFIRMED|BROKEN|PIERCED|CONSUMED|DEAD|   |
//|            ACTIVE  (schema enum; aliases accepted for tolerance) |
//|    role    PRIMARY|NESTED|CONTEXT|CARRIED|TRIGGER|SPAWNED|GRID   |
//|    t_birth epoch seconds, bar at which the object became drawable|
//|    t1,t2   geometry times (epoch seconds); t2 empty/0 = open end |
//|            (schema t_right = null)                               |
//|    p1,p2   geometry prices (empty when unused)                   |
//|    letter  T|F for LABEL_TF;  M|W|Mm|Ww|SHS for BRACKET          |
//|    side    above|below for LABEL_TF / BRACKET / FALSE_EXT        |
//|    why     machine-readable reason code (schema `why`)           |
//|                                                                  |
//|  Per-type geometry (schema $defs -> flat columns):               |
//|    BOX / CONTEXT_RANGE  : range_geom top,bottom -> p2=top,p1=bot;|
//|                           t1=t_left, t2=t_right                  |
//|    RANGE_OPEN           : same; t2 open -> 0                     |
//|    PATTERN_LINE /       : line_geom anchor1,anchor2 ->           |
//|      CONTEXT_LINE         (t1,p1),(t2,p2); extends_to folded into|
//|                           draw ray (t2=0 means project right)    |
//|    LEVEL_CARRIED        : level_geom price -> p1; t1=t_left,     |
//|                           t2=0 (projects right)                  |
//|    MINI_LEVEL           : level_geom price -> p1; t1,t2 span     |
//|    SQUEEZE              : squeeze_geom t0,t1 -> t1,t2;           |
//|                           price_lo,price_hi -> p1,p2             |
//|    LABEL_TF             : label_geom letter,t_bar,side,price ->  |
//|                           letter,t1,side,p1                      |
//|    BRACKET              : bracket_geom letter,t0,t1,side,        |
//|                           mid_price -> letter,t1,t2,side,p1      |
//|    FALSE_EXT            : false_ext_geom t_bar,price,side ->     |
//|                           t1,p1,side                             |
//|    STAND_ASIDE          : t1,t2 span; why = reason code          |
//|                           (provisional: not a schema object)     |
//|                                                                  |
//|  Times are SERVER epochs (identical to MqlRates.time and to the  |
//|  Python pa_data bar `t`).  The schema uses bar INDICES on the    |
//|  Python side; the projector maps idx -> epoch so the epoch is    |
//|  the join key and bar indices never cross the wire.              |
//|                                                                  |
//|  NO order, position or trade call exists in this header.         |
//+------------------------------------------------------------------+
#ifndef PA_PERCEPTION_MQH
#define PA_PERCEPTION_MQH

#define PA_PERC_CSV_VER "perception_csv_v1"

//--- object types (schema perception_v1 $defs/object.type, plus the
//--- provisional STAND_ASIDE pseudo-type for facts.stand_aside codes)
enum PA_PO_TYPE
  {
   PA_PO_BOX=0,
   PA_PO_RANGE_OPEN,
   PA_PO_CONTEXT_RANGE,
   PA_PO_PATTERN_LINE,
   PA_PO_CONTEXT_LINE,
   PA_PO_LEVEL_CARRIED,
   PA_PO_MINI_LEVEL,
   PA_PO_SQUEEZE,
   PA_PO_LABEL_TF,
   PA_PO_BRACKET,
   PA_PO_FALSE_EXT,
   PA_PO_STAND_ASIDE,     // provisional - not a schema type
   PA_PO_UNKNOWN=99
  };

//--- lifecycle state (schema object.state)
enum PA_PO_STATE
  {
   PA_POS_PROVISIONAL=0,
   PA_POS_CONFIRMED,
   PA_POS_BROKEN,
   PA_POS_PIERCED,
   PA_POS_CONSUMED,
   PA_POS_DEAD,
   PA_POS_ACTIVE
  };

//--- role (schema object.role)
enum PA_PO_ROLE
  {
   PA_POR_NONE=0,         // absent / not applicable
   PA_POR_PRIMARY,
   PA_POR_NESTED,
   PA_POR_CONTEXT,
   PA_POR_CARRIED,
   PA_POR_TRIGGER,
   PA_POR_SPAWNED,
   PA_POR_GRID
  };

//--- draw side for letter/tick annotations (schema *.side)
enum PA_PO_SIDE
  {
   PA_SIDE_NONE=0,
   PA_SIDE_ABOVE,
   PA_SIDE_BELOW
  };

//+------------------------------------------------------------------+
//| PaPercObj - one perception object row                            |
//+------------------------------------------------------------------+
struct PaPercObj
  {
   string            id;        // schema id is a string
   PA_PO_TYPE        type;
   PA_PO_STATE       state;
   PA_PO_ROLE        role;
   PA_PO_SIDE        side;
   long              t_birth;
   long              bar_t;     // 0 = flat object list; else the bar
                                // this row is the view of (parity mode)
   long              t1;        // left / start / event bar
   long              t2;        // right / end; 0 = open (project right)
   double            p1;        // lo / start price / event price
   double            p2;        // hi / end price
   string            letter;    // T|F | M|W|Mm|Ww|SHS
   string            why;
  };

//--- type name <-> enum (CSV wire values = schema enum values)
string PaPercTypeName(const PA_PO_TYPE t)
  {
   switch(t)
     {
      case PA_PO_BOX:           return("BOX");
      case PA_PO_RANGE_OPEN:    return("RANGE_OPEN");
      case PA_PO_CONTEXT_RANGE: return("CONTEXT_RANGE");
      case PA_PO_PATTERN_LINE:  return("PATTERN_LINE");
      case PA_PO_CONTEXT_LINE:  return("CONTEXT_LINE");
      case PA_PO_LEVEL_CARRIED: return("LEVEL_CARRIED");
      case PA_PO_MINI_LEVEL:    return("MINI_LEVEL");
      case PA_PO_SQUEEZE:       return("SQUEEZE");
      case PA_PO_LABEL_TF:      return("LABEL_TF");
      case PA_PO_BRACKET:       return("BRACKET");
      case PA_PO_FALSE_EXT:     return("FALSE_EXT");
      case PA_PO_STAND_ASIDE:   return("STAND_ASIDE");
      default:                  return("UNKNOWN");
     }
  }

PA_PO_TYPE PaPercTypeOf(const string s)
  {
   for(int i=0;i<(int)PA_PO_UNKNOWN;i++)
      if(s==PaPercTypeName((PA_PO_TYPE)i))
         return((PA_PO_TYPE)i);
   return(PA_PO_UNKNOWN);
  }

PA_PO_STATE PaPercStateOf(const string s)
  {
   if(s=="PROVISIONAL") return(PA_POS_PROVISIONAL);
   if(s=="CONFIRMED")   return(PA_POS_CONFIRMED);
   if(s=="BROKEN")      return(PA_POS_BROKEN);
   if(s=="PIERCED")     return(PA_POS_PIERCED);
   if(s=="CONSUMED")    return(PA_POS_CONSUMED);
   if(s=="DEAD")        return(PA_POS_DEAD);
   if(s=="ACTIVE")      return(PA_POS_ACTIVE);
   //--- aliases tolerated while the lane converges
   if(s=="FROZEN")      return(PA_POS_CONFIRMED);
   if(s=="CLOSED")      return(PA_POS_DEAD);
   if(s=="DELETED")     return(PA_POS_DEAD);
   return(PA_POS_ACTIVE);
  }

PA_PO_ROLE PaPercRoleOf(const string s)
  {
   if(s=="PRIMARY")  return(PA_POR_PRIMARY);
   if(s=="NESTED")   return(PA_POR_NESTED);
   if(s=="CONTEXT")  return(PA_POR_CONTEXT);
   if(s=="CARRIED")  return(PA_POR_CARRIED);
   if(s=="TRIGGER")  return(PA_POR_TRIGGER);
   if(s=="SPAWNED")  return(PA_POR_SPAWNED);
   if(s=="GRID")     return(PA_POR_GRID);
   //--- aliases tolerated
   if(s=="MAIN")     return(PA_POR_PRIMARY);
   if(s=="OBSTACLE") return(PA_POR_CONTEXT);
   if(s=="EXIT")     return(PA_POR_CARRIED);
   return(PA_POR_NONE);
  }

PA_PO_SIDE PaPercSideOf(const string s)
  {
   if(s=="above") return(PA_SIDE_ABOVE);
   if(s=="below") return(PA_SIDE_BELOW);
   return(PA_SIDE_NONE);
  }

//--- structural types (counted in the spec section-5 budget);
//--- LABEL_TF / BRACKET / FALSE_EXT / STAND_ASIDE are annotations and
//--- ride along with the object they belong to.
bool PaPercIsStructural(const PA_PO_TYPE t)
  {
   return(t==PA_PO_BOX || t==PA_PO_RANGE_OPEN || t==PA_PO_CONTEXT_RANGE ||
          t==PA_PO_PATTERN_LINE || t==PA_PO_CONTEXT_LINE ||
          t==PA_PO_LEVEL_CARRIED || t==PA_PO_MINI_LEVEL || t==PA_PO_SQUEEZE);
  }

//--- spec section-5 drawing priority (lower = drawn first):
//--- 1) the BOX containing/just left by price, 2) breakout-side edge /
//--- PATTERN_LINE / MINI_LEVEL trigger, 3) LEVEL_CARRIED, 4) CONTEXT.
int PaPercRank(const PaPercObj &o)
  {
   switch(o.type)
     {
      case PA_PO_BOX:           return(0);
      case PA_PO_PATTERN_LINE:  return(1);
      case PA_PO_MINI_LEVEL:    return(1);
      case PA_PO_LEVEL_CARRIED: return(2);
      case PA_PO_RANGE_OPEN:    return(3);
      case PA_PO_SQUEEZE:       return(3);
      case PA_PO_CONTEXT_RANGE: return(4);
      case PA_PO_CONTEXT_LINE:  return(4);
      default:                  return(9);   // annotations last
     }
  }

//+------------------------------------------------------------------+
//| CPaSnapshot - CSV snapshot importer                              |
//|                                                                  |
//|  Load(path) reads one file of object rows.  Flat files carry one |
//|  row per object; per-bar files (parity mode) carry a leading     |
//|  bar_t epoch column.  FILE_COMMON is tried first, then the       |
//|  terminal-local Files dir.                                       |
//+------------------------------------------------------------------+
class CPaSnapshot
  {
public:
   PaPercObj         objs[];
   int               n;
   string            path;
   datetime          loaded_mtime;

                     CPaSnapshot(void) { n=0; path=""; loaded_mtime=0; }

   //--- does the object overlap the [t0,t1] window?  t2==0 = open end
   bool              Overlaps(const PaPercObj &o,const long t0,
                              const long t1) const
     {
      long rt=(o.t2>0)?o.t2:t1;
      return(o.t1<=t1 && rt>=t0);
     }

   //--- open a snapshot file: FILE_COMMON first, then terminal-local
   int               OpenHandle(const string rel_path,const bool write)
     {
      int flags=(write?FILE_WRITE:FILE_READ)|FILE_TXT|FILE_ANSI;
      int fh=FileOpen(rel_path,flags|FILE_COMMON);
      if(fh==INVALID_HANDLE)
         fh=FileOpen(rel_path,flags);
      return(fh);
     }

   datetime          FileMtime(const string rel_path)
     {
      long mt=FileGetInteger(rel_path,FILE_MODIFY_DATE,true);
      if(mt<=0)
         mt=FileGetInteger(rel_path,FILE_MODIFY_DATE,false);
      return((datetime)mt);
     }

   //--- (re)load the CSV; returns rows parsed or -1 on open failure
   int               Load(const string rel_path)
     {
      path=rel_path;
      n=0;
      ArrayResize(objs,0);
      int fh=OpenHandle(rel_path,false);
      if(fh==INVALID_HANDLE)
         return(-1);
      loaded_mtime=FileMtime(rel_path);
      while(!FileIsEnding(fh))
        {
         string line=FileReadString(fh);
         StringTrimLeft(line);
         StringTrimRight(line);
         if(line=="" || line=="\n")
            continue;
         string f[];
         int nf=StringSplit(line,',',f);
         for(int k=0;k<nf;k++)
           { StringTrimLeft(f[k]); StringTrimRight(f[k]); }
         if(nf<1 || f[0]=="id" || f[0]=="bar_t" || f[0]=="#")
            continue;                     // header / comment row
         int off=(nf>=13)?1:0;            // leading bar_t column?
         if(nf<12)
            continue;
         PaPercObj o;
         o.bar_t=(off)?StringToInteger(f[0]):0;
         o.id=f[off+0];
         o.type=PaPercTypeOf(f[off+1]);
         o.state=PaPercStateOf(f[off+2]);
         o.role=PaPercRoleOf(f[off+3]);
         o.t_birth=StringToInteger(f[off+4]);
         o.t1=StringToInteger(f[off+5]);
         o.t2=StringToInteger(f[off+6]);
         o.p1=(f[off+7]=="")?0.0:StringToDouble(f[off+7]);
         o.p2=(f[off+8]=="")?0.0:StringToDouble(f[off+8]);
         o.letter=f[off+9];
         o.side=PaPercSideOf(f[off+10]);
         o.why=f[off+11];
         ArrayResize(objs,n+1);
         objs[n]=o;
         n++;
        }
      FileClose(fh);
      return(n);
     }

   //--- newest bar_t <= `t` (per-bar mode; never looks ahead); falls
   //--- back to the smallest bar_t when the window precedes the file.
   //--- 0 on a flat file.
   long              NearestBar(const long t) const
     {
      long best=0,first=0;
      for(int i=0;i<n;i++)
         if(objs[i].bar_t>0)
           {
            if(first==0 || objs[i].bar_t<first)
               first=objs[i].bar_t;
            if(objs[i].bar_t<=t && objs[i].bar_t>best)
               best=objs[i].bar_t;
           }
      return((best>0)?best:first);
     }

   //--- objects overlapping [t0,t1], sorted by spec-5 priority then id.
   //--- On a per-bar file only the rows of `bar` are considered (pass 0
   //--- to use the bar_t nearest the window's right edge); flat files
   //--- ignore `bar`.
   int               InWindow(const long t0,const long t1,PaPercObj &out[],
                              const long bar)
     {
      ArrayResize(out,0);
      long use=bar;
      if(use<=0)
         use=NearestBar(t1);
      int m=0;
      for(int i=0;i<n;i++)
        {
         if(use>0 && objs[i].bar_t>0 && objs[i].bar_t!=use)
            continue;
         if(Overlaps(objs[i],t0,t1))
           {
            ArrayResize(out,m+1);
            out[m]=objs[i];
            m++;
           }
        }
      //--- insertion sort by (rank, id) - tiny sets (<= ~30 rows)
      for(int i=1;i<m;i++)
        {
         PaPercObj v=out[i];
         int j=i-1;
         int rv=PaPercRank(v);
         while(j>=0 && (PaPercRank(out[j])>rv ||
               (PaPercRank(out[j])==rv && out[j].id>v.id)))
           {
            out[j+1]=out[j];
            j--;
           }
         out[j+1]=v;
        }
      return(m);
     }
  };

#endif // PA_PERCEPTION_MQH
