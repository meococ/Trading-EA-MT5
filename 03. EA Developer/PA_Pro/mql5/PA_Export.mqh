//+------------------------------------------------------------------+
//|                                                    PA_Export.mqh |
//|  PA-PRO EA lane - parity export.  For every bar in the DESIGN    |
//|  window the EA dumps the ARMED zone views (sx replay state, the  |
//|  same state views_at exposes to Python readers) to CSV.          |
//|                                                                  |
//|  The Python twin lives at mql5/parity/export_zones.py and must   |
//|  emit byte-compatible columns; compare_parity.py diffs the two.  |
//|                                                                  |
//|  Columns: t_idx,t_epoch,gen,zid,kind,scale,lo,hi,strength,       |
//|           touches,fresh,broken_idx,role_flip,approach_side,      |
//|           born_idx,end_idx                                       |
//|                                                                  |
//|  No order, position or trade call exists in this header.         |
//+------------------------------------------------------------------+
#ifndef PA_EXPORT_MQH
#define PA_EXPORT_MQH

#include "PA_Types.mqh"
#include "PA_Zones.mqh"

#define PA_EXP_COLS "t_idx,t_epoch,gen,zid,kind,scale,lo,hi,strength,touches,fresh,broken_idx,role_flip,approach_side,born_idx,end_idx"

class CPaExport
  {
public:
   int               fh;
   string            path;
   int               rows;

                     CPaExport(void)
     {
      fh=INVALID_HANDLE; path=""; rows=0;
     }

   bool              Open(const string folder,const string fname)
     {
      if(fh!=INVALID_HANDLE)
         FileClose(fh);
      path=folder+"\\"+fname;
      fh=FileOpen(path,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
      if(fh==INVALID_HANDLE)
         fh=FileOpen(path,FILE_WRITE|FILE_TXT|FILE_ANSI);
      if(fh==INVALID_HANDLE)
        {
         PrintFormat("PA-PRO export: cannot open %s (err %d)",path,GetLastError());
         return(false);
        }
      FileWriteString(fh,PA_EXP_COLS+"\n");
      FileFlush(fh);
      rows=0;
      return(true);
     }

   void              Close(void)
     {
      if(fh!=INVALID_HANDLE)
        {
         FileClose(fh);
         fh=INVALID_HANDLE;
        }
     }

   //--- dump every ARMED view at bar t (call right after StepBar(t))
   void              BarZones(CPaPerception &pa,const int t)
     {
      if(fh==INVALID_HANDLE)
         return;
      int dg=(int)SymbolInfoInteger(pa.ctx.symbol,SYMBOL_DIGITS);
      for(int g=0;g<PA_GEN_COUNT;g++)
        {
         if(pa.gen[g]==NULL)
            continue;
         PaZoneView views[];
         int nv=pa.ViewsAt(g,t,true,views);
         for(int v=0;v<nv;v++)
           {
            PaZoneView z=views[v];
            string line=StringFormat("%d,%I64d,%s,%d,%s,%d,%s,%s,%.6f,%d,%d,%d,%d,%d,%d,%d",
                                     t,pa.ctx.b[t].t,PaGenName(g),z.zid,
                                     PaZoneKindName(z.kind),z.scale,
                                     DoubleToString(z.lo,dg),
                                     DoubleToString(z.hi,dg),
                                     z.strength,z.touches,
                                     (z.fresh?1:0),z.broken_idx,
                                     z.role_flip,z.approach_side,
                                     z.born_idx,z.end_idx);
            FileWriteString(fh,line+"\n");
            rows++;
           }
        }
      if((rows&255)==0)
         FileFlush(fh);
     }
  };

#endif // PA_EXPORT_MQH
