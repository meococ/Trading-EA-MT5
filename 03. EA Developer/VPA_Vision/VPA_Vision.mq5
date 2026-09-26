//+------------------------------------------------------------------+
//|                                                   VPA_Vision.mq5 |
//|  T-VPA-VIS-1 - forensic view of the frozen DR3 detector.         |
//|                                                                  |
//|  Draws on a EURUSD M5 chart exactly what the Python DR3 detector  |
//|  (research/lab/vpa_dr1.py, DR3_CFG) sees: touch-cluster barriers,  |
//|  EMA25, ATR(14) Wilder, and one annotation per candidate           |
//|  evaluation (ACCEPT / SKIP + failed hard gates + features).        |
//|                                                                  |
//|  VISUAL ONLY. There is no order, position, trade or DLL call in    |
//|  this file or in VPA_Core.mqh. Only the Owner's trading plane      |
//|  places orders.                                                    |
//|                                                                  |
//|  Closed bars only: the forming bar is never fed to the detector,   |
//|  so nothing repaints. One redraw happens when a bar closes.        |
//+------------------------------------------------------------------+
#property copyright "Trading-EA-MT5 / T-VPA-VIS-1"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 1
#property indicator_plots   1
#property indicator_label1  "EMA25"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrGoldenrod
#property indicator_style1  STYLE_SOLID
#property indicator_width1  1

#include "VPA_Core.mqh"

#define VPA_OBJ_PREFIX "VPA_VIS_"

input group "--- Layers ---"
input bool   InpShowBarriers      = true;      // barrier lines + touch markers
input bool   InpShowTouchMarkers  = true;      // dots on every barrier touch
input bool   InpShowEma           = true;      // EMA25 line (detector recursion)
input bool   InpShowAtrPanel      = true;      // ATR(14) panel bottom-left
input bool   InpShowEvents        = true;      // signal bar + entry/stop/target
input bool   InpShowObstacle      = true;      // blocking obstacle (orange)
input bool   InpShowAccepted      = true;      // draw ACCEPT events
input bool   InpShowRejected      = true;      // draw SKIP events

input group "--- Depth / scale ---"
input int    InpHistoryBars       = 20000;     // detector depth (closed M5 bars)
input int    InpDrawBars          = 2000;      // newest N bars drawn (0 = whole depth)
input int    InpMaxEvents         = 300;       // newest N evaluations drawn (0 = all)
input int    InpLabelFontSize     = 8;         // label font size
input int    InpLabelOffsetPoints = 40;        // label distance from the bar extreme
input int    InpAtrPanelBars      = 60;        // ATR spark length

input group "--- Colors ---"
input color  InpColorBarrierUp    = clrDeepSkyBlue;   // pivot-high barrier (ceiling)
input color  InpColorBarrierDn    = clrOrangeRed;     // pivot-low barrier (floor)
input color  InpColorBarrierBad   = clrDimGray;       // integrity failed (dashed)
input color  InpColorTouch        = clrSilver;        // touch markers
input color  InpColorEma          = clrGoldenrod;     // EMA25
input color  InpColorAccept       = clrLimeGreen;     // ACCEPT label
input color  InpColorSkip         = clrTomato;        // SKIP label
input color  InpColorEntry        = clrRoyalBlue;     // entry line
input color  InpColorStop         = clrCrimson;       // stop line (S = 8 pips)
input color  InpColorTarget       = clrMediumSeaGreen;// target line (2R = 16)
input color  InpColorObstacle     = clrDarkOrange;    // blocking obstacle
input color  InpColorLabel        = clrWhiteSmoke;    // label text
input color  InpColorAtrPanel     = clrSlateGray;     // ATR panel

input group "--- Parity export (optional) ---"
input bool   InpExportCsv         = false;            // export CSVs once on attach
input string InpExportFrom        = "2019.02.01 00:00"; // window start (server)
input string InpExportTo          = "2019.04.01 00:00"; // window end (server)
input string InpExportFolder      = "vis1";           // MQL5\Files\<folder>

input bool   InpAllowNonM5        = false;      // detector params are M5-frozen

double   g_emaBuf[];
CVpaDr3  g_det;
datetime g_last_closed = 0;
int      g_last_rates  = 0;
bool     g_initialized = false;
bool     g_exported    = false;

int OnInit()
  {
   if(_Period!=PERIOD_M5 && !InpAllowNonM5)
     {
      Alert("VPA_Vision: attach to a M5 chart (detector parameters are M5-frozen). ",
            "Set InpAllowNonM5=true to override.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   SetIndexBuffer(0,g_emaBuf,INDICATOR_DATA);
   ArraySetAsSeries(g_emaBuf,false);
   PlotIndexSetDouble(0,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,InpColorEma);
   PlotIndexSetString(0,PLOT_LABEL,"VPA_VIS_EMA25");
   IndicatorSetString(INDICATOR_SHORTNAME,"VPA_Vision (DR3)");
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0,VPA_OBJ_PREFIX);
   ChartRedraw(0);
  }

int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   if(rates_total<120)
      return(0);
   datetime last_closed=iTime(_Symbol,_Period,1);
   if(last_closed==0)
      return(0);
   if(g_initialized && last_closed==g_last_closed && rates_total==g_last_rates)
      return(rates_total);
   g_last_closed=last_closed;
   g_last_rates=rates_total;
   Rebuild(rates_total);
   g_initialized=true;
   return(rates_total);
  }

//+------------------------------------------------------------------+
//| build the closed-bar slice, run the detector, redraw             |
//+------------------------------------------------------------------+
void Rebuild(const int rates_total)
  {
   if(InpExportCsv && !g_exported)
     {
      g_exported=true;
      string msg="";
      datetime t0=StringToTime(InpExportFrom);
      datetime t1=StringToTime(InpExportTo);
      if(t0>0 && t1>t0 && VpaExportWindow(_Symbol,_Period,t0,t1,InpExportFolder,"VPA_Vision",msg))
         Print("VPA_Vision export OK: ",msg);
      else
         Print("VPA_Vision export FAILED: ",msg);
     }
   int want=InpHistoryBars;
   if(want<200)
      want=200;
   int avail=MathMin(Bars(_Symbol,_Period)-1,rates_total-1);
   int copy=MathMin(want,avail);
   if(copy<120)
      return;
   MqlRates r[];
   ArraySetAsSeries(r,true);
   int got=CopyRates(_Symbol,_Period,0,copy+1,r);
   if(got<120)
      return;
   int closed=got-1;
   VpaBar raw[];
   ArrayResize(raw,closed);
   for(int k=0;k<closed;k++)
     {
      int src=closed-k;
      raw[k].t=(long)r[src].time;
      raw[k].o=r[src].open;
      raw[k].h=r[src].high;
      raw[k].l=r[src].low;
      raw[k].c=r[src].close;
      datetime ct=(datetime)((long)r[src].time+(long)PeriodSeconds(_Period));
      VpaUtcMinute(ct,raw[k].utc_min,raw[k].srv_min);
     }
   //--- slice start on a UTC-day boundary so the day H/L tracker sees full days
   int start=0;
   long d0=raw[0].t/86400;
   while(start<closed && raw[start].t/86400==d0)
      start++;
   if(start>=closed-120)
      start=0;
   int nslice=closed-start;
   VpaBar bars[];
   ArrayResize(bars,nslice);
   for(int k=0;k<nslice;k++)
      bars[k]=raw[start+k];
   if(!g_det.Init(bars,nslice,VpaPipSize(_Symbol),VpaTickSize(_Symbol)))
     {
      Print("VPA_Vision: detector init failed: ",g_det.m_error);
      return;
     }
   g_det.Run();
   PlotIndexSetDouble(0,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   for(int i=0;i<rates_total;i++)
      g_emaBuf[i]=EMPTY_VALUE;
   for(int k=0;k<nslice;k++)
     {
      int bi=rates_total-1-nslice+k;
      if(bi<0 || bi>=rates_total)
         continue;
      if(g_det.m_ema_ok[k] && InpShowEma)
         g_emaBuf[bi]=g_det.m_ema[k];
     }
   DrawAll(nslice);
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
//| object helpers                                                   |
//+------------------------------------------------------------------+
string ObjName(const string tag,const int id)
  {
   return(VPA_OBJ_PREFIX+tag+"_"+IntegerToString(id));
  }

bool MkTrend(const string name,const datetime t1,const double p1,const datetime t2,const double p2,
             const color col,const int style,const int width)
  {
   if(!ObjectCreate(0,name,OBJ_TREND,0,t1,p1,t2,p2))
      return(false);
   ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,false);
   ObjectSetInteger(0,name,OBJPROP_RAY_LEFT,false);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,width);
   ObjectSetInteger(0,name,OBJPROP_BACK,false);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   return(true);
  }

bool MkText(const string name,const datetime t,const double p,const string text,const color col,
            const int size,const ENUM_ANCHOR_POINT anchor)
  {
   if(!ObjectCreate(0,name,OBJ_TEXT,0,t,p))
      return(false);
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetString(0,name,OBJPROP_FONT,"Consolas");
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,size);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,anchor);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   return(true);
  }

bool MkArrow(const string name,const datetime t,const double p,const int code,const color col)
  {
   if(!ObjectCreate(0,name,OBJ_ARROW,0,t,p))
      return(false);
   ObjectSetInteger(0,name,OBJPROP_ARROWCODE,code);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   return(true);
  }

bool MkRect(const string name,const datetime t1,const double p1,const datetime t2,const double p2,
            const color col)
  {
   if(!ObjectCreate(0,name,OBJ_RECTANGLE,0,t1,p1,t2,p2))
      return(false);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_FILL,false);
   ObjectSetInteger(0,name,OBJPROP_BACK,true);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   return(true);
  }

bool MkPanelRect(const string name,const int corner,const int x,const int y,const int w,const int h,
                 const color col,const bool back)
  {
   if(!ObjectCreate(0,name,OBJ_RECTANGLE_LABEL,0,0,0))
      return(false);
   ObjectSetInteger(0,name,OBJPROP_CORNER,corner);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,name,OBJPROP_XSIZE,w);
   ObjectSetInteger(0,name,OBJPROP_YSIZE,h);
   ObjectSetInteger(0,name,OBJPROP_BGCOLOR,col);
   ObjectSetInteger(0,name,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_BACK,back);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   return(true);
  }

bool MkPanelText(const string name,const int corner,const int x,const int y,const string text,
                 const color col,const int size)
  {
   if(!ObjectCreate(0,name,OBJ_LABEL,0,0,0))
      return(false);
   ObjectSetInteger(0,name,OBJPROP_CORNER,corner);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetString(0,name,OBJPROP_FONT,"Consolas");
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,size);
   ObjectSetInteger(0,name,OBJPROP_COLOR,col);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   return(true);
  }

//+------------------------------------------------------------------+
//| layer 1 - barriers + touch markers + integrity flag              |
//+------------------------------------------------------------------+
void DrawBarriers(const int nslice,const int from)
  {
   if(!InpShowBarriers)
      return;
   for(int i=0;i<g_det.m_n_barriers;i++)
     {
      if(g_det.m_barriers[i].exp_idx<from)
         continue;
      int end_idx=(g_det.m_barriers[i].end_kind==VPA_END_ACTIVE) ? g_det.m_barriers[i].exp_idx
                  : g_det.m_barriers[i].end_idx;
      if(end_idx>nslice-1)
         end_idx=nslice-1;
      if(end_idx<0 || g_det.m_barriers[i].lock_idx<0)
         continue;
      bool bad=g_det.m_barriers[i].integrity_fail;
      color col=(bad) ? InpColorBarrierBad
                 : ((g_det.m_barriers[i].side>0) ? InpColorBarrierUp : InpColorBarrierDn);
      int style=(bad) ? STYLE_DASH : STYLE_SOLID;
      double lvl=g_det.m_barriers[i].level;
      MkTrend(ObjName("BAR",i),
              (datetime)g_det.m_b[g_det.m_barriers[i].lock_idx].t,lvl,
              (datetime)g_det.m_b[end_idx].t,lvl,col,style,1);
      if(InpShowTouchMarkers)
         for(int q=0;q<g_det.m_barriers[i].n_touches;q++)
           {
            int ti=g_det.m_barriers[i].touches[q];
            if(ti<from || ti>nslice-1)
               continue;
            MkArrow(ObjName("TOUCH",i*100+q),(datetime)g_det.m_b[ti].t,lvl,159,InpColorTouch);
           }
      if(bad)
         MkText(ObjName("INTEG",i),(datetime)g_det.m_b[end_idx].t,lvl,"integrity",
                InpColorBarrierBad,7,
                (g_det.m_barriers[i].side>0) ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER);
     }
  }

//+------------------------------------------------------------------+
//| label text for one evaluation                                    |
//+------------------------------------------------------------------+
string EventLabel(const VpaEvent &e)
  {
   string head=(e.executable) ? "ACCEPT" : "SKIP";
   string hard="";
   for(int g=0;g<VPA_NGATES;g++)
      if(VpaGateHard(g) && e.gate_eval[g] && !e.gate_pass[g])
         hard+=(StringLen(hard)>0 ? "," : "")+VpaGateKey(g);
   string l1=head+" "+(e.side>0 ? "long" : "short");
   if(StringLen(hard)>0)
      l1+=" ["+hard+"]";
   double pip=VpaPipSize(_Symbol);
   double S=VPA_STOP_PIPS*pip;
   string l2="B="+DoubleToString(e.level,_Digits);
   if(e.has_entry)
      l2+=" entry="+DoubleToString(e.entry,_Digits)
          +" stop="+DoubleToString((e.side>0) ? e.entry-S : e.entry+S,_Digits)
          +" tgt="+DoubleToString((e.side>0) ? e.entry+VPA_TARGET_R*S : e.entry-VPA_TARGET_R*S,_Digits);
   else
      l2+=" no buildup";
   string l3="";
   if(e.has_room)
      l3=(e.room_inf) ? "room inf" : StringFormat("room %.2fR",e.room_r);
   else
      l3="room n/a";
   if(e.has_obstacle)
      l3+=StringFormat(" ob=%s@%s",e.obstacle_type,DoubleToString(e.obstacle_price,_Digits));
   l3+=StringFormat(" | ema %sA | sq %s | lunch %s",DoubleToString(e.ema_dist_atr,2),
                    (e.squeeze ? "Y" : "N"),(e.lunch ? "Y" : "N"));
   l3+=StringFormat(" | chop %s(win %s) | S=%s",(e.chop ? "Y" : "N"),
                    (e.chop_window==1 ? "Y" : (e.chop_window==0 ? "N" : "-")),
                    (StringLen(e.session)>0 ? e.session : "off"));
   l3+=StringFormat(" | A=%s",DoubleToString(e.atr,_Digits));
   return(l1+"\n"+l2+"\n"+l3);
  }

//+------------------------------------------------------------------+
//| layer 3/4 - one annotation per DR3 evaluation                    |
//+------------------------------------------------------------------+
void DrawEvents(const int nslice,const int from)
  {
   if(!InpShowEvents)
      return;
   int budget=(InpMaxEvents>0) ? InpMaxEvents : g_det.m_n_events;
   int drawn=0;
   double pip=VpaPipSize(_Symbol);
   double S=VPA_STOP_PIPS*pip;
   int period=PeriodSeconds(_Period);
   for(int i=g_det.m_n_events-1;i>=0 && drawn<budget;i--)
     {
      VpaEvent e=g_det.m_events[i];
      if(e.bar_idx<from || e.bar_idx>nslice-1)
         continue;
      if(e.executable && !InpShowAccepted)
         continue;
      if(!e.executable && !InpShowRejected)
         continue;
      drawn++;
      datetime t_sig=(datetime)g_det.m_b[e.bar_idx].t;
      datetime t_left=(datetime)((long)g_det.m_b[e.bar_idx].t-(long)period);
      datetime t_right=(datetime)((long)g_det.m_b[e.bar_idx].t+(long)period);
      double hi=g_det.m_b[e.bar_idx].h;
      double lo=g_det.m_b[e.bar_idx].l;
      color col=(e.executable) ? InpColorAccept : InpColorSkip;
      MkRect(ObjName("SIG",i),t_left,lo,t_right,hi,col);
      MkArrow(ObjName("ARR",i),t_sig,(e.side>0) ? lo : hi,(e.side>0) ? 233 : 234,col);
      if(e.has_entry)
        {
         datetime t_end=(datetime)((long)g_det.m_b[e.bar_idx].t+(long)(VPA_ORDER_VALID_BARS*period));
         double stp=(e.side>0) ? e.entry-S : e.entry+S;
         double tgt=(e.side>0) ? e.entry+VPA_TARGET_R*S : e.entry-VPA_TARGET_R*S;
         MkTrend(ObjName("ENT",i),t_sig,e.entry,t_end,e.entry,InpColorEntry,STYLE_SOLID,1);
         MkTrend(ObjName("STP",i),t_sig,stp,t_end,stp,InpColorStop,STYLE_SOLID,1);
         MkTrend(ObjName("TGT",i),t_sig,tgt,t_end,tgt,InpColorTarget,STYLE_SOLID,1);
        }
      if(InpShowObstacle && e.has_obstacle)
         MkTrend(ObjName("OBS",i),t_left,e.obstacle_price,t_right,e.obstacle_price,
                 InpColorObstacle,STYLE_SOLID,2);
      double off=(double)InpLabelOffsetPoints*_Point;
      MkText(ObjName("LBL",i),t_right,(e.side>0) ? hi+off : lo-off,EventLabel(e),col,
             InpLabelFontSize,(e.side>0) ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER);
     }
  }

//+------------------------------------------------------------------+
//| layer 2b - ATR(14) Wilder panel (numeric + spark), bottom-left   |
//+------------------------------------------------------------------+
void DrawAtrPanel(const int nslice)
  {
   if(!InpShowAtrPanel)
      return;
   int last=nslice-1;
   if(last<26)
      return;
   int bars=MathMax(10,InpAtrPanelBars);
   int from=MathMax(25,last-bars+1);
   double mx=0.0;
   for(int i=from;i<=last;i++)
      if(g_det.m_atr_ok[i] && g_det.m_atr[i]>mx)
         mx=g_det.m_atr[i];
   if(mx<=0.0)
      return;
   int corner=CORNER_LEFT_LOWER;
   int px=10;
   int py=30;
   int w=190;
   int h=76;
   MkPanelRect(ObjName("ATRBG",0),corner,px,py,w,h,InpColorAtrPanel,true);
   double pip=VpaPipSize(_Symbol);
   string txt=StringFormat("ATR(14) Wilder  %s  (%.1f pips)\nEMA25  %s\nbars %d..%d",
                           DoubleToString(g_det.m_atr[last],_Digits),g_det.m_atr[last]/pip,
                           (g_det.m_ema_ok[last] ? DoubleToString(g_det.m_ema[last],_Digits) : "n/a"),
                           from,last);
   MkPanelText(ObjName("ATRTXT",0),corner,px+8,py+6,txt,InpColorLabel,8);
   int n=last-from+1;
   int colw=MathMax(1,(w-20)/MathMax(1,n));
   for(int k=0;k<n;k++)
     {
      int i=from+k;
      if(!g_det.m_atr_ok[i])
         continue;
      int hh=(int)MathRound((g_det.m_atr[i]/mx)*(h-16));
      if(hh<1)
         hh=1;
      MkPanelRect(ObjName("ATRSPK",k),corner,px+10+k*colw,py+8+(h-16)-hh,colw-1,hh,
                  (i==last) ? InpColorLabel : InpColorAtrPanel,false);
     }
  }

void DrawAll(const int nslice)
  {
   ObjectsDeleteAll(0,VPA_OBJ_PREFIX);
   int from=0;
   if(InpDrawBars>0)
      from=MathMax(0,nslice-InpDrawBars);
   DrawBarriers(nslice,from);
   DrawEvents(nslice,from);
   DrawAtrPanel(nslice);
  }

