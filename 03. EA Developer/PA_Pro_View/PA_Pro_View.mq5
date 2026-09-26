//+------------------------------------------------------------------+
//|                                                 PA_Pro_View.mq5  |
//|  PA-PRO perception SNAPSHOT VIEWER - indicator, view-only.       |
//|                                                                  |
//|  Loads a perception snapshot (perception_csv_v1 - the flat CSV   |
//|  projection of schema/perception_v1.json, see PA_Perception.mqh) |
//|  from MQL5\Files and draws                                       |
//|  every object overlapping the VISIBLE window in the Volman       |
//|  grammar (PA_Draw.mqh), plus the EMA25 line.                     |
//|                                                                  |
//|  Generate a mock snapshot with mql5/tools/mock_snapshot.py;      |
//|  steps for the Owner are in mql5/VIEWER_RUNBOOK.md.              |
//|                                                                  |
//|  VIEW-ONLY: this file contains no order, position or trade call  |
//|  and never will.                                                 |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 1
#property indicator_plots   1
#property indicator_label1  "EMA25"
#property indicator_type1   DRAW_LINE
#property indicator_style1  STYLE_SOLID
#property indicator_width1  1

#include "..\PA_Pro\mql5\PA_Perception.mqh"
#include "..\PA_Pro\mql5\PA_Draw.mqh"

input string InpFile       = "PA_Pro/perception_EURUSD.csv"; // snapshot CSV
input int    InpTheme      = 0;        // 0 = dark chart, 1 = light chart
input double InpTolPips    = 1.0;      // edge band half-width, pips
input int    InpMaxObj     = 5;        // spec-5 soft budget
input int    InpHardCap    = 8;        // spec-5 hard cap
input bool   InpDrawEma25  = true;     // draw the EMA25 line
input int    InpPollMs     = 1000;     // file re-check interval, ms
input int    InpHudY       = 16;       // HUD top-left offset

double  g_ema[];
CPaSnapshot g_snap;
datetime    g_mtime=0;
PaDrawPal   g_pal;

//+------------------------------------------------------------------+
int OnInit()
  {
   SetIndexBuffer(0,g_ema,INDICATOR_DATA);
   IndicatorSetString(INDICATOR_SHORTNAME,"PA-PRO view");
   g_pal=PaDrawPalette((InpTheme==1)?PA_THEME_LIGHT:PA_THEME_DARK);
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,g_pal.ema);
   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,24);
   if(!InpDrawEma25)
      PlotIndexSetInteger(0,PLOT_DRAW_TYPE,DRAW_NONE);
   g_mtime=0;
   EventSetMillisecondTimer(MathMax(200,InpPollMs));
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| visible window in epochs: first/last visible bar on this chart   |
//+------------------------------------------------------------------+
void PaViewWindow(long &t0,long &t1)
  {
   t0=0; t1=0;
   long first=(long)ChartGetInteger(0,CHART_FIRST_VISIBLE_BAR);
   long cnt=(long)ChartGetInteger(0,CHART_VISIBLE_BARS);
   if(cnt<=0)
      return;
   datetime a=iTime(_Symbol,Period(),(int)first);
   datetime b=iTime(_Symbol,Period(),(int)MathMax(0,first-cnt+1));
   t0=(long)MathMin(a,b);
   t1=(long)MathMax(a,b)+PeriodSeconds(Period());
  }

//+------------------------------------------------------------------+
//| (re)load the snapshot if the file changed                        |
//+------------------------------------------------------------------+
int PaViewEnsure()
  {
   datetime mt=g_snap.FileMtime(InpFile);
   if(mt!=g_mtime)
     {
      int r=g_snap.Load(InpFile);
      if(r<0)
         return(-1);
      g_mtime=mt;
     }
   return(g_snap.n);
  }

//+------------------------------------------------------------------+
//| redraw: wipe, reload if needed, draw window objects + HUD        |
//+------------------------------------------------------------------+
void PaViewRedraw(const double point)
  {
   PaDrawWipe();
   long t0,t1;
   PaViewWindow(t0,t1);
   int rows=PaViewEnsure();
   if(rows<0)
     {
      //--- HUD as a label, not a chart-time text
      if(!ObjectCreate(0,PA_DRAW_PREFIX "HUD",OBJ_LABEL,0,0,0))
         return;
      ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_XDISTANCE,8);
      ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_YDISTANCE,InpHudY);
      ObjectSetString(0,PA_DRAW_PREFIX "HUD",OBJPROP_FONT,"Consolas");
      ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_FONTSIZE,9);
      ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_COLOR,clrTomato);
      ObjectSetString(0,PA_DRAW_PREFIX "HUD",OBJPROP_TEXT,
                      "PA-PRO view: snapshot not found - "+InpFile);
      ChartRedraw(0);
      return;
     }
   PaPercObj win[];
   int m=g_snap.InWindow(t0,t1,win,0);
   double pip=(point<1e-3)?point*10.0:point;   // 5-digit broker -> pip
   double tol=InpTolPips*pip;
   int drawn=PaDrawSnapshot(PA_DRAW_PREFIX,win,m,t1,tol,g_pal,
                            InpMaxObj,InpHardCap);
   //--- HUD
   if(!ObjectCreate(0,PA_DRAW_PREFIX "HUD",OBJ_LABEL,0,0,0))
      return;
   ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_XDISTANCE,8);
   ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_YDISTANCE,InpHudY);
   ObjectSetString(0,PA_DRAW_PREFIX "HUD",OBJPROP_FONT,"Consolas");
   ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_FONTSIZE,9);
   ObjectSetInteger(0,PA_DRAW_PREFIX "HUD",OBJPROP_COLOR,g_pal.hud_dim);
   ObjectSetString(0,PA_DRAW_PREFIX "HUD",OBJPROP_TEXT,
                   StringFormat("PA-PRO view  objs=%d/%d  win=%d  %s",
                                drawn,m,rows,InpFile));
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
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
   if(rates_total<=0)
      return(0);
   //--- EMA25 buffer (incremental over prev_calculated)
   int start=prev_calculated-1;
   if(start<0)
      start=0;
   double a=2.0/26.0;
   for(int i=start;i<rates_total;i++)
     {
      if(i<24)
         g_ema[i]=EMPTY_VALUE;
      else if(i==24)
        {
         double s=0.0;
         for(int k=0;k<25;k++)
            s+=close[k];
         g_ema[i]=s/25.0;
        }
      else
         g_ema[i]=a*close[i]+(1.0-a)*g_ema[i-1];
     }
   PaViewRedraw(_Point);
   return(rates_total);
  }

//+------------------------------------------------------------------+
void OnChartEvent(const int id,const long &lp,const double &dp,
                  const string &sp)
  {
   if(id==CHARTEVENT_CHART_CHANGE)       // scroll / zoom -> redraw window
      PaViewRedraw(_Point);
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   //--- file mtime check - a weekend chart gets no ticks, so the
   //--- poll is what makes "edit CSV -> redraw" work there
   datetime mt=g_snap.FileMtime(InpFile);
   if(mt!=g_mtime)
      PaViewRedraw(_Point);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   PaDrawWipe();
   ChartRedraw(0);
  }
//+------------------------------------------------------------------+
