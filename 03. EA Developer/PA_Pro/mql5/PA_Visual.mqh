//+------------------------------------------------------------------+
//|                                                    PA_Visual.mqh |
//|  PA-PRO EA lane - chart overlay in the VPA_Vision style:          |
//|   - armed zones -> rectangles over [born_idx, now+pad] x [lo,hi] |
//|   - setup plans -> entry / SL / TP lines + direction arrow       |
//|   - SKIP reason -> text label at the signal bar                  |
//|   - HUD -> rectangle_label + label, top-left (VPA doctrine: HUD  |
//|     LTF lives top-left, never the right corner over the price    |
//|     column).                                                     |
//|                                                                  |
//|  Prefix PAP_ on every object; Wipe() + ChartRedraw on rebuild.   |
//|  No order, position or trade call exists in this header.         |
//+------------------------------------------------------------------+
#ifndef PA_VISUAL_MQH
#define PA_VISUAL_MQH

#include "PA_Types.mqh"
#include "PA_Zones.mqh"
#include "PA_Trade.mqh"

#define PA_OBJ_PREFIX "PAP_"

//--- zone colours by scale (micro teal / meso indigo / macro rose)
#define PA_COL_MICRO   clrTeal
#define PA_COL_MESO    clrRoyalBlue
#define PA_COL_MACRO   clrDarkOrange
#define PA_COL_BROKEN  clrDimGray
#define PA_COL_ENTRY   clrDeepSkyBlue
#define PA_COL_SL      clrCrimson
#define PA_COL_TP      clrLimeGreen
#define PA_COL_SKIP    clrGoldenrod

//+------------------------------------------------------------------+
//| helpers (VPA_Vision.mq5:214-300 shape)                            |
//+------------------------------------------------------------------+
void PaVisLine(const string name,const long t1,const double p1,
               const long t2,const double p2,
               const color col,const int style,const int width)
  {
   ObjectDelete(0,name);
   if(!ObjectCreate(0,name,OBJ_TREND,0,(datetime)t1,p1,(datetime)t2,p2))
      return;
   ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,false);
   ObjectSetInteger(0,name,OBJPROP_RAY_LEFT,false);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,width);
   ObjectSetInteger(0,name,OBJPROP_BACK,false);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
  }

void PaVisRect(const string name,const long t1,const double p1,
               const long t2,const double p2,
               const color col,const int style,const bool fill)
  {
   ObjectDelete(0,name);
   if(!ObjectCreate(0,name,OBJ_RECTANGLE,0,(datetime)t1,p1,(datetime)t2,p2))
      return;
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_FILL,fill);
   ObjectSetInteger(0,name,OBJPROP_BACK,true);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
  }

void PaVisText(const string name,const long t,const double p,
               const string text,const color col,const int size,
               const int anchor)
  {
   ObjectDelete(0,name);
   if(!ObjectCreate(0,name,OBJ_TEXT,0,(datetime)t,p))
      return;
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetString(0,name,OBJPROP_FONT,"Consolas");
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,size);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,anchor);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
  }

void PaVisArrow(const string name,const long t,const double p,
                const int code,const color col)
  {
   ObjectDelete(0,name);
   if(!ObjectCreate(0,name,OBJ_ARROW,0,(datetime)t,p))
      return;
   ObjectSetInteger(0,name,OBJPROP_ARROWCODE,code);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
  }

void PaVisHudLabel(const string name,const int x,const int y,
                   const string text,const color col,const int size)
  {
   ObjectDelete(0,name);
   if(!ObjectCreate(0,name,OBJ_LABEL,0,0,0))
      return;
   ObjectSetInteger(0,name,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetString(0,name,OBJPROP_FONT,"Consolas");
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,size);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
  }

//+------------------------------------------------------------------+
//| CPaVisual - redraw entry points                                   |
//+------------------------------------------------------------------+
class CPaVisual
  {
public:
   bool              on;
   int               max_zones_drawn;

                     CPaVisual(void)
     {
      on=true; max_zones_drawn=24;
     }

   void              Wipe(void)
     {
      ObjectsDeleteAll(0,PA_OBJ_PREFIX);
      ChartRedraw(0);
     }

   //--- armed zones for every generator at bar t.
   //--- t_end = chart time of the rectangle's right edge (now + pad bars)
   void DrawZones(CPaPerception &pa,const int t,const int pad_bars)
     {
      if(!on)
         return;
      int drawn=0;
      for(int g=0;g<PA_GEN_COUNT;g++)
        {
         PaZoneView views[];
         int nv=pa.ViewsAt(g,t,true,views);
         for(int v=0;v<nv && drawn<max_zones_drawn;v++)
           {
            PaZoneView z=views[v];
            long t1=pa.ctx.b[z.born_idx].t;
            long t2=pa.ctx.b[t].t+pad_bars*300;
            color col=(z.scale==PA_SC_MACRO)?PA_COL_MACRO:
                      (z.scale==PA_SC_MESO)?PA_COL_MESO:PA_COL_MICRO;
            int  sty=(z.broken_idx>=0)?STYLE_DASH:STYLE_SOLID;
            string nm=StringFormat("%sZ%d_%d",PA_OBJ_PREFIX,g,z.zid);
            PaVisRect(nm,t1,z.lo,t2,z.hi,col,sty,false);
            nm=StringFormat("%sZL%d_%d",PA_OBJ_PREFIX,g,z.zid);
            PaVisText(nm,t2,z.hi,
                      StringFormat("%s s%.2f t%d",PaGenName(g),
                                   z.strength,z.touches),
                      col,7,ANCHOR_LEFT_LOWER);
            drawn++;
           }
        }
     }

   //--- plan bracket: entry (solid), SL (dashdot), TP (dot) + arrow
   void DrawPlan(const PaPlan &p,const string sym)
     {
      if(!on || !p.ok)
         return;
      long t1=p.sig_t;
      long t2=p.sig_t+(p.expire_bars+2)*300;
      string base=StringFormat("%sP%d",PA_OBJ_PREFIX,p.sig_idx);
      PaVisLine(base+"_E",t1,p.entry,t2,p.entry,PA_COL_ENTRY,STYLE_SOLID,1);
      PaVisLine(base+"_S",t1,p.sl,   t2,p.sl,   PA_COL_SL,   STYLE_DASHDOT,1);
      PaVisLine(base+"_T",t1,p.tp,   t2,p.tp,   PA_COL_TP,   STYLE_DOT,1);
      PaVisArrow(base+"_A",t1,(p.side>0)?p.entry-3*SymbolInfoDouble(sym,SYMBOL_POINT)
                                       :p.entry+3*SymbolInfoDouble(sym,SYMBOL_POINT),
                 (p.side>0)?233:234,(p.side>0)?PA_COL_TP:PA_COL_SL);
      PaVisText(base+"_N",t2,(p.side>0)?p.tp:p.sl,
                StringFormat("%s %s %s",p.setup,
                             (p.side>0)?"BUY":"SELL",
                             DoubleToString(p.entry,_Digits)),
                PA_COL_ENTRY,7,ANCHOR_LEFT_LOWER);
     }

   //--- SKIP/veto annotation at the signal bar
   void DrawSkip(const long t,const double px,const string why)
     {
      if(!on)
         return;
      string nm=StringFormat("%sK%d",PA_OBJ_PREFIX,(int)t);
      PaVisText(nm,t,px,"SKIP "+why,PA_COL_SKIP,7,ANCHOR_UPPER);
     }

   //--- HUD top-left: engine counts + last signal + lock state
   void DrawHud(const int n_bars,const int n_live,const int n_armed,
                const string last,const string lock)
     {
      if(!on)
         return;
      PaVisHudLabel(PA_OBJ_PREFIX "H0",8,16,
                    StringFormat("PA-PRO  bars=%d  zones=%d  armed=%d",
                                 n_bars,n_live,n_armed),
                    clrWhite,9);
      PaVisHudLabel(PA_OBJ_PREFIX "H1",8,30,
                    "last: "+((last=="")?"-":last),clrLightGray,9);
      PaVisHudLabel(PA_OBJ_PREFIX "H2",8,44,
                    (lock=="")?"risk: OK":("risk: "+lock),
                    (lock=="")?clrLimeGreen:clrTomato,9);
     }
  };

#endif // PA_VISUAL_MQH
