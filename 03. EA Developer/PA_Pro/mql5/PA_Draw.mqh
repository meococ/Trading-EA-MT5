//+------------------------------------------------------------------+
//|                                                     PA_Draw.mqh  |
//|  PA-PRO EA lane - the Volman drawing grammar (spec section 2).   |
//|                                                                  |
//|  One draw function per object type, in the casebook style:       |
//|    BOX            solid rectangle; edges render as thin bands    |
//|                   (+/- tol) around the stored price              |
//|    RANGE_OPEN     two horizontal lines, no vertical ends         |
//|    CONTEXT_RANGE  dotted rectangle                               |
//|    PATTERN_LINE   solid diagonal                                 |
//|    CONTEXT_LINE   fine-dotted diagonal                           |
//|    LEVEL_CARRIED  long-dashed horizontal, projected right        |
//|    MINI_LEVEL     short horizontal                               |
//|    SQUEEZE        dashed ellipse                                 |
//|    LABEL_TF       T/F letter at the poking bar                   |
//|    BRACKET        span line + centred M/W/Mm/Ww/SHS letter       |
//|    FALSE_EXT      short tick at the failed extreme               |
//|    STAND_ASIDE    small tag (nothing drawable in chop)           |
//|    EMA25          one line buffer (the only indicator)           |
//|                                                                  |
//|  00/50 gridlines are context - never drawn here.                 |
//|  Object names carry the PAV_ prefix + object id and are wiped    |
//|  wholesale on redraw/deinit.  The spec-5 budget (<=5 structural  |
//|  objects, hard cap 8) is enforced at draw time as well.          |
//|                                                                  |
//|  No order, position or trade call exists in this header.         |
//+------------------------------------------------------------------+
#ifndef PA_DRAW_MQH
#define PA_DRAW_MQH

#include "PA_Perception.mqh"

#define PA_DRAW_PREFIX "PAV_"

enum PA_DRAW_THEME
  {
   PA_THEME_DARK=0,
   PA_THEME_LIGHT=1
  };

//--- palette per theme.  Dark theme = the Owner's chart default;
//--- light theme keeps the same grammar readable on a white chart.
struct PaDrawPal
  {
   color             box;        // box outline
   color             box_band;   // edge band fill
   color             range_open;
   color             ctx_range;
   color             pat_line;
   color             ctx_line;
   color             carried;
   color             mini;
   color             squeeze;
   color             label_t;
   color             label_f;
   color             bracket;
   color             false_ext;
   color             aside;
   color             ema;
   color             hud_fg;
   color             hud_dim;
  };

PaDrawPal PaDrawPalette(const PA_DRAW_THEME th)
  {
   PaDrawPal p;
   if(th==PA_THEME_LIGHT)
     {
      p.box=clrNavy;        p.box_band=clrLavender;
      p.range_open=clrDimGray;
      p.ctx_range=clrGray;  p.pat_line=clrBlack;
      p.ctx_line=clrSilver; p.carried=clrDarkOrange;
      p.mini=clrSaddleBrown; p.squeeze=clrIndigo;
      p.label_t=clrDarkGoldenrod; p.label_f=clrCrimson;
      p.bracket=clrSteelBlue; p.false_ext=clrCrimson;
      p.aside=clrGray;      p.ema=clrRoyalBlue;
      p.hud_fg=clrBlack;    p.hud_dim=clrDimGray;
     }
   else
     {
      p.box=clrGainsboro;   p.box_band=clrDarkSlateGray;
      p.range_open=clrSilver;
      p.ctx_range=clrDimGray; p.pat_line=clrWhite;
      p.ctx_line=clrGray;   p.carried=clrOrange;
      p.mini=clrGold;       p.squeeze=clrMediumPurple;
      p.label_t=clrGold;    p.label_f=clrTomato;
      p.bracket=clrLightSteelBlue; p.false_ext=clrSalmon;
      p.aside=clrDimGray;   p.ema=clrDeepSkyBlue;
      p.hud_fg=clrWhite;    p.hud_dim=clrLightGray;
     }
   return(p);
  }

//+------------------------------------------------------------------+
//| primitives (same discipline as PA_Visual / VPA_Vision)           |
//+------------------------------------------------------------------+
void PaDRct(const string name,const long t1,const double p1,
            const long t2,const double p2,const color col,
            const int style,const bool fill)
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
   ObjectSetInteger(0,name,OBJPROP_ZORDER,0);
  }

void PaDLine(const string name,const long t1,const double p1,
             const long t2,const double p2,const color col,
             const int style,const int width,const bool ray)
  {
   ObjectDelete(0,name);
   if(!ObjectCreate(0,name,OBJ_TREND,0,(datetime)t1,p1,(datetime)t2,p2))
      return;
   ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,ray);
   ObjectSetInteger(0,name,OBJPROP_RAY_LEFT,false);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,width);
   ObjectSetInteger(0,name,OBJPROP_BACK,false);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
  }

void PaDText(const string name,const long t,const double p,
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

void PaDTick(const string name,const long t,const double p,
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

void PaDEllipse(const string name,const long t1,const double p1,
                const long t2,const double p2,const color col)
  {
   ObjectDelete(0,name);
   if(!ObjectCreate(0,name,OBJ_ELLIPSE,0,(datetime)t1,p1,(datetime)t2,p2))
      return;
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_STYLE,STYLE_DASH);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,name,OBJPROP_FILL,false);
   ObjectSetInteger(0,name,OBJPROP_BACK,false);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
  }

//+------------------------------------------------------------------+
//| grammar: one function per spec-2 type                            |
//|  All take (base object name, obj, drawing params, palette).      |
//|  tol = edge tolerance in price -> edges render as thin bands.    |
//|  t_edge = current right edge of the visible window (open-ended   |
//|  objects draw to it; carried levels ray past it).                |
//+------------------------------------------------------------------+

//--- BOX: solid outline + each edge as a filled band +/- tol
void PaDrawBox(const string nm,const PaPercObj &o,const double tol,
               const long t_edge,const PaDrawPal &pal)
  {
   long rt=(o.t2>0)?o.t2:t_edge;
   PaDRct(nm+"_o",o.t1,o.p1,rt,o.p2,pal.box,STYLE_SOLID,false);
   PaDRct(nm+"_tb",o.t1,o.p2-tol,rt,o.p2+tol,pal.box_band,STYLE_SOLID,true);
   PaDRct(nm+"_bb",o.t1,o.p1-tol,rt,o.p1+tol,pal.box_band,STYLE_SOLID,true);
   if(o.role==PA_POR_NESTED)
      PaDText(nm+"_n",o.t1,o.p2,"n",pal.box,7,ANCHOR_LEFT_LOWER);
  }

//--- RANGE_OPEN: two horizontal lines, no vertical ends
void PaDrawRangeOpen(const string nm,const PaPercObj &o,const double tol,
                     const long t_edge,const PaDrawPal &pal)
  {
   bool open=(o.t2<=0);
   long rt=open?t_edge:o.t2;
   PaDLine(nm+"_hi",o.t1,o.p2,rt,o.p2,pal.range_open,STYLE_SOLID,1,open);
   PaDLine(nm+"_lo",o.t1,o.p1,rt,o.p1,pal.range_open,STYLE_SOLID,1,open);
   //--- edge bands (thin) on the open lines as well
   PaDRct(nm+"_hb",o.t1,o.p2-tol,rt,o.p2+tol,pal.ctx_range,STYLE_SOLID,true);
   PaDRct(nm+"_lb",o.t1,o.p1-tol,rt,o.p1+tol,pal.ctx_range,STYLE_SOLID,true);
  }

//--- CONTEXT_RANGE: dotted rectangle
void PaDrawContextRange(const string nm,const PaPercObj &o,const double tol,
                        const long t_edge,const PaDrawPal &pal)
  {
   long rt=(o.t2>0)?o.t2:t_edge;
   PaDRct(nm+"_o",o.t1,o.p1,rt,o.p2,pal.ctx_range,STYLE_DOT,false);
  }

//--- PATTERN_LINE: solid diagonal through (t1,p1)-(t2,p2)
void PaDrawPatternLine(const string nm,const PaPercObj &o,const double tol,
                       const long t_edge,const PaDrawPal &pal)
  {
   PaDLine(nm+"_l",o.t1,o.p1,o.t2,o.p2,pal.pat_line,STYLE_SOLID,1,false);
   if(o.state==PA_POS_PIERCED)      // kept, but marked
      PaDText(nm+"_p",o.t2,o.p2,"x",pal.pat_line,7,ANCHOR_LEFT_LOWER);
  }

//--- CONTEXT_LINE: fine-dotted diagonal, 3-8 h guide
void PaDrawContextLine(const string nm,const PaPercObj &o,const double tol,
                       const long t_edge,const PaDrawPal &pal)
  {
   PaDLine(nm+"_l",o.t1,o.p1,o.t2,o.p2,pal.ctx_line,STYLE_DOT,1,false);
  }

//--- LEVEL_CARRIED: long-dashed horizontal projected right.
//--- CONSUMED state: dimmed (the level no longer counts as obstacle).
void PaDrawLevelCarried(const string nm,const PaPercObj &o,const double tol,
                        const long t_edge,const PaDrawPal &pal)
  {
   color c=(o.state==PA_POS_CONSUMED)?pal.ctx_range:pal.carried;
   long t2=(o.t1>0)?o.t1+8*300:t_edge;      // 2nd anchor for the ray
   PaDLine(nm+"_l",o.t1,o.p1,t2,o.p1,c,STYLE_DASH,1,true);
   PaDRct(nm+"_b",o.t1,o.p1-tol,t2,o.p1+tol,pal.ctx_range,STYLE_SOLID,true);
  }

//--- MINI_LEVEL: short horizontal, 2-8 bars
void PaDrawMiniLevel(const string nm,const PaPercObj &o,const double tol,
                     const long t_edge,const PaDrawPal &pal)
  {
   long rt=(o.t2>0)?o.t2:o.t1+3*300;
   PaDLine(nm+"_l",o.t1,o.p1,rt,o.p1,pal.mini,STYLE_SOLID,2,false);
   PaDRct(nm+"_b",o.t1,o.p1-tol,rt,o.p1+tol,pal.ctx_range,STYLE_SOLID,true);
  }

//--- SQUEEZE: dashed ellipse around the trapped bars
void PaDrawSqueeze(const string nm,const PaPercObj &o,const double tol,
                   const long t_edge,const PaDrawPal &pal)
  {
   long rt=(o.t2>0)?o.t2:o.t1+3*300;
   PaDEllipse(nm+"_e",o.t1,o.p2,rt,o.p1,pal.squeeze);
  }

//--- LABEL_TF: T/F letter beside the poking bar.  p1 = label price
//--- (the engine already places it beyond the poke extreme); side
//--- picks whether the letter floats above or hangs below the point.
void PaDrawLabelTF(const string nm,const PaPercObj &o,const double tol,
                   const long t_edge,const PaDrawPal &pal)
  {
   color c=(o.letter=="F")?pal.label_f:pal.label_t;
   int anc=(o.side==PA_SIDE_BELOW)?ANCHOR_UPPER:ANCHOR_LOWER;
   PaDText(nm+"_t",o.t1,o.p1,(o.letter=="")?"T":o.letter,c,8,anc);
  }

//--- BRACKET: span line t1..t2 at p1 with the letter centred
void PaDrawBracket(const string nm,const PaPercObj &o,const double tol,
                   const long t_edge,const PaDrawPal &pal)
  {
   long rt=(o.t2>0)?o.t2:o.t1+6*300;
   PaDLine(nm+"_s",o.t1,o.p1,rt,o.p1,pal.bracket,STYLE_SOLID,1,false);
   long tm=o.t1+(rt-o.t1)/2;
   int anc=(o.side==PA_SIDE_BELOW)?ANCHOR_UPPER:ANCHOR_LOWER;
   PaDText(nm+"_c",tm,o.p1,(o.letter=="")?"M":o.letter,pal.bracket,8,anc);
  }

//--- FALSE_EXT: short tick at the failed extreme (arrowcode 159 = dot;
//--- 231/232 small arrows mark the failed side when `side` is given)
void PaDrawFalseExt(const string nm,const PaPercObj &o,const double tol,
                    const long t_edge,const PaDrawPal &pal)
  {
   int code=159;
   if(o.side==PA_SIDE_ABOVE) code=231;
   else if(o.side==PA_SIDE_BELOW) code=232;
   PaDTick(nm+"_x",o.t1,o.p1,code,pal.false_ext);
  }

//--- STAND_ASIDE: small tag at the span's start (nothing drawable)
void PaDrawStandAside(const string nm,const PaPercObj &o,const double tol,
                      const long t_edge,const PaDrawPal &pal)
  {
   string txt=(o.why=="")?"stand-aside":o.why;
   PaDText(nm+"_a",o.t1,o.p1,txt,pal.aside,7,ANCHOR_LOWER);
  }

//+------------------------------------------------------------------+
//| PaDrawSnapshot - draw the objects overlapping [t0,t1].           |
//|                                                                  |
//|  Budget (spec section 5): at most `max_obj` structural objects   |
//|  (hard cap `hard_cap`).  Annotations (LABEL_TF / BRACKET /       |
//|  FALSE_EXT / STAND_ASIDE) ride along and are not counted.        |
//|  Objects arrive sorted by PaPercRank.                            |
//|  Returns the number of structural objects drawn.                 |
//+------------------------------------------------------------------+
int PaDrawSnapshot(const string prefix,PaPercObj &objs[],const int m,
                   const long t_edge,const double tol,
                   const PaDrawPal &pal,const int max_obj,
                   const int hard_cap)
  {
   int structural=0;
   for(int i=0;i<m;i++)
     {
      PaPercObj o=objs[i];
      bool strc=PaPercIsStructural(o.type);
      if(strc && structural>=hard_cap)
         break;                          // hard cap - stop entirely
      if(strc && structural>=max_obj)
         continue;                       // soft cap - annotations still
                                         // pass, structures dropped
      string nm=prefix+o.id;
      if(o.id=="")
         nm=prefix+IntegerToString(i);
      switch(o.type)
        {
         case PA_PO_BOX:           PaDrawBox(nm,o,tol,t_edge,pal); break;
         case PA_PO_RANGE_OPEN:    PaDrawRangeOpen(nm,o,tol,t_edge,pal); break;
         case PA_PO_CONTEXT_RANGE: PaDrawContextRange(nm,o,tol,t_edge,pal); break;
         case PA_PO_PATTERN_LINE:  PaDrawPatternLine(nm,o,tol,t_edge,pal); break;
         case PA_PO_CONTEXT_LINE:  PaDrawContextLine(nm,o,tol,t_edge,pal); break;
         case PA_PO_LEVEL_CARRIED: PaDrawLevelCarried(nm,o,tol,t_edge,pal); break;
         case PA_PO_MINI_LEVEL:    PaDrawMiniLevel(nm,o,tol,t_edge,pal); break;
         case PA_PO_SQUEEZE:       PaDrawSqueeze(nm,o,tol,t_edge,pal); break;
         case PA_PO_LABEL_TF:      PaDrawLabelTF(nm,o,tol,t_edge,pal); break;
         case PA_PO_BRACKET:       PaDrawBracket(nm,o,tol,t_edge,pal); break;
         case PA_PO_FALSE_EXT:     PaDrawFalseExt(nm,o,tol,t_edge,pal); break;
         case PA_PO_STAND_ASIDE:   PaDrawStandAside(nm,o,tol,t_edge,pal); break;
         default: break;
        }
      if(strc)
         structural++;
     }
   return(structural);
  }

void PaDrawWipe()
  {
   ObjectsDeleteAll(0,PA_DRAW_PREFIX);
  }

//+------------------------------------------------------------------+
//| EMA25 - the only indicator (spec section 1).  Wilder-free: seed  |
//|  = SMA of the first 25 closes, then a=2/26 recursion - the same  |
//|  convention as sf_ctx.ema.  `ema[]` must be pre-sized to n.      |
//+------------------------------------------------------------------+
void PaEma25(const double &close[],const int n,double &ema[])
  {
   if(n<=0)
      return;
   double a=2.0/26.0;
   double seed=0.0;
   int m=MathMin(25,n);
   for(int i=0;i<m;i++)
      seed+=close[i];
   seed/=m;
   for(int i=0;i<n;i++)
     {
      if(i<24)
         ema[i]=EMPTY_VALUE;
      else if(i==24)
         ema[i]=seed;
      else
         ema[i]=a*close[i]+(1.0-a)*ema[i-1];
     }
  }

#endif // PA_DRAW_MQH
