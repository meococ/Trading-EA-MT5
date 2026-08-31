//+------------------------------------------------------------------+
//|                                      SMC Order Block Detector.mq5|
//+------------------------------------------------------------------+
#property copyright "Ahmad Arju"
#property link      "https://www.mql5.com/en/users/arju0612_/"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//====================================================================
// [1] ENUM & INPUT PARAMETERS
//====================================================================
enum ENUM_MITIGATION {
    MITIGATION_BODY,
    MITIGATION_WICK
};

input group "--- Order Block Settings ---"
input ENUM_MITIGATION InpMitigation = MITIGATION_BODY;
input int InpMaxOB                  = 3;
input bool InpFillOB                = true;
input color InpColorOB_Bull         = C'10,40,15';
input color InpColorOB_Bear         = C'40,10,10';
input color InpColorOB_TextBull     = clrLime;
input color InpColorOB_TextBear     = clrRed;

input group "--- Alert Settings ---"
input bool   InpEnableAlert         = true;
input bool   InpAlertPopup          = true;
input bool   InpAlertPush           = false;
input int    InpAlertCooldownBars   = 5;

//====================================================================
// [2] GLOBAL VARIABLES & STRUCTS
//====================================================================
long obj_counter = 0; 
double prev_valid_high = 0;
double prev_valid_low = 0;
double last_tick_price = 0;
datetime prev_live_bar_time = 0;

struct ValidBar {
    double h;
    double l;
    datetime t;
};
ValidBar vb1, vb2, vb3;

struct OrderBlock {
    bool     active;
    datetime ob_time;
    double   top;
    double   bottom;
    long     ticket;
    double   fvg_size;
    bool     visual_deleted;
    bool     touch_alerted;
    bool     has_exited;
    int      bars_since_exit;
};

OrderBlock BullOBs[];
OrderBlock BearOBs[];
long ob_ticket_counter = 0;

//====================================================================
// [3] INITIALIZATION & DEINITIALIZATION
//====================================================================
int OnInit()
  {
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);
   last_tick_price = 0;
   prev_live_bar_time = 0;
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, "SMC_OB_");
  }

//====================================================================
// [4] ORDER BLOCK GRAPHICS RENDERER
//====================================================================
void UpdateOBGraphics(const datetime &time[], int current_bar)
  {
   int active_bull = 0;
   int active_bear = 0;
   
   int total_bull = ArraySize(BullOBs);
   for(int i = total_bull - 1; i >= 0; i--)
     {
      string obj_name = "SMC_OB_BULL_" + IntegerToString(BullOBs[i].ticket);
      string lbl_name = obj_name + "_lbl";
      
      if(!BullOBs[i].active || active_bull >= InpMaxOB)
        {
         if(!BullOBs[i].visual_deleted)
           {
            ObjectDelete(0, obj_name);
            ObjectDelete(0, lbl_name);
            BullOBs[i].visual_deleted = true;
           }
         continue;
        }
      
      if(ObjectFind(0, obj_name) < 0)
        {
         ObjectCreate(0, obj_name, OBJ_RECTANGLE, 0, BullOBs[i].ob_time, BullOBs[i].top, time[current_bar], BullOBs[i].bottom);
         ObjectSetInteger(0, obj_name, OBJPROP_COLOR, InpColorOB_Bull);
         ObjectSetInteger(0, obj_name, OBJPROP_BACK, true);
         ObjectSetInteger(0, obj_name, OBJPROP_FILL, InpFillOB);
        }
      else
        {
         ObjectSetInteger(0, obj_name, OBJPROP_TIME, 1, time[current_bar]);
        }
         
      if(ObjectFind(0, lbl_name) < 0)
        {
         ObjectCreate(0, lbl_name, OBJ_TEXT, 0, time[current_bar], BullOBs[i].top);
         ObjectSetString(0, lbl_name, OBJPROP_TEXT, " " + DoubleToString(BullOBs[i].top, _Digits)); 
         ObjectSetInteger(0, lbl_name, OBJPROP_COLOR, InpColorOB_TextBull);
         ObjectSetInteger(0, lbl_name, OBJPROP_ANCHOR, ANCHOR_LEFT); 
         ObjectSetInteger(0, lbl_name, OBJPROP_FONTSIZE, 9);
         ObjectSetString(0, lbl_name, OBJPROP_FONT, "Trebuchet MS");
        }
      else
        {
         ObjectSetInteger(0, lbl_name, OBJPROP_TIME, 0, time[current_bar]);
         ObjectSetDouble(0, lbl_name, OBJPROP_PRICE, 0, BullOBs[i].top);
        }
         
      active_bull++;
     }
   
   int total_bear = ArraySize(BearOBs);
   for(int i = total_bear - 1; i >= 0; i--)
     {
      string obj_name = "SMC_OB_BEAR_" + IntegerToString(BearOBs[i].ticket);
      string lbl_name = obj_name + "_lbl";
      
      if(!BearOBs[i].active || active_bear >= InpMaxOB)
        {
         if(!BearOBs[i].visual_deleted)
           {
            ObjectDelete(0, obj_name);
            ObjectDelete(0, lbl_name);
            BearOBs[i].visual_deleted = true;
           }
         continue;
        }
      
      if(ObjectFind(0, obj_name) < 0)
        {
         ObjectCreate(0, obj_name, OBJ_RECTANGLE, 0, BearOBs[i].ob_time, BearOBs[i].top, time[current_bar], BearOBs[i].bottom);
         ObjectSetInteger(0, obj_name, OBJPROP_COLOR, InpColorOB_Bear);
         ObjectSetInteger(0, obj_name, OBJPROP_BACK, true);
         ObjectSetInteger(0, obj_name, OBJPROP_FILL, InpFillOB);
        }
      else
        {
         ObjectSetInteger(0, obj_name, OBJPROP_TIME, 1, time[current_bar]);
        }
         
      if(ObjectFind(0, lbl_name) < 0)
        {
         ObjectCreate(0, lbl_name, OBJ_TEXT, 0, time[current_bar], BearOBs[i].bottom);
         ObjectSetString(0, lbl_name, OBJPROP_TEXT, " " + DoubleToString(BearOBs[i].bottom, _Digits));
         ObjectSetInteger(0, lbl_name, OBJPROP_COLOR, InpColorOB_TextBear);
         ObjectSetInteger(0, lbl_name, OBJPROP_ANCHOR, ANCHOR_LEFT); 
         ObjectSetInteger(0, lbl_name, OBJPROP_FONTSIZE, 9);
         ObjectSetString(0, lbl_name, OBJPROP_FONT, "Trebuchet MS");
        }
      else
        {
         ObjectSetInteger(0, lbl_name, OBJPROP_TIME, 0, time[current_bar]);
         ObjectSetDouble(0, lbl_name, OBJPROP_PRICE, 0, BearOBs[i].bottom);
        }
         
      active_bear++;
     }
  }

//====================================================================
// [5] MAIN CALCULATION ENGINE
//====================================================================
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
   if(rates_total < 10) return(0);

   int limit;
   if(prev_calculated == 0)
     {
      limit = 1;
      ObjectsDeleteAll(0, "SMC_OB_");
      obj_counter = 0;
      last_tick_price = 0;
      prev_live_bar_time = 0;
      
      prev_valid_high = high[1];
      prev_valid_low = low[1];
      
      ArrayResize(BullOBs, 0);
      ArrayResize(BearOBs, 0);
      
      ob_ticket_counter = 0;
      vb1.t = 0; vb2.t = 0; vb3.t = 0;
     }
   else
     {
      limit = prev_calculated - 1;
     }

   for(int i = limit; i < rates_total - 1; i++)
     {
      // --- OB MITIGATION CHECK (HISTORY) ---
      int total_bull_obs = ArraySize(BullOBs);
      for(int b = 0; b < total_bull_obs; b++)
        {
         if(!BullOBs[b].active) continue;
         
         if(InpMitigation == MITIGATION_BODY)
           {
            if(close[i] < BullOBs[b].bottom) BullOBs[b].active = false;
           }
         else 
           {
            if(low[i] <= BullOBs[b].top) BullOBs[b].active = false;
           }
        }
        
      int total_bear_obs = ArraySize(BearOBs);
      for(int b = 0; b < total_bear_obs; b++)
        {
         if(!BearOBs[b].active) continue;
         
         if(InpMitigation == MITIGATION_BODY)
           {
            if(close[i] > BearOBs[b].top) BearOBs[b].active = false;
           }
         else 
           {
            if(high[i] >= BearOBs[b].bottom) BearOBs[b].active = false;
           }
        }

      if(high[i] <= prev_valid_high && low[i] >= prev_valid_low) continue;
      
      ValidBar vb0;
      vb0.h = high[i];
      vb0.l = low[i];
      vb0.t = time[i];

      // --- ORDER BLOCK CREATION & OVERLAP LOGIC ---
      if(vb3.t != 0)
        {
         if(vb2.l < vb3.l && vb0.l > vb2.h)
           {
            int size = ArraySize(BullOBs);
            ArrayResize(BullOBs, size + 1, 1000);
            BullOBs[size].active = true;
            BullOBs[size].ob_time = vb2.t;
            BullOBs[size].top = vb2.h;
            BullOBs[size].bottom = vb2.l;
            BullOBs[size].ticket = ++ob_ticket_counter;
            BullOBs[size].fvg_size = vb0.l - vb2.h;
            BullOBs[size].visual_deleted = false;
            BullOBs[size].touch_alerted = false;
            BullOBs[size].has_exited = true;
            BullOBs[size].bars_since_exit = 999;
            
            if(InpMitigation == MITIGATION_BODY)
              {
               for(int b = 0; b < size; b++)
                 {
                  if(!BullOBs[b].active) continue;
                  
                  if(BullOBs[size].bottom <= BullOBs[b].top && BullOBs[size].top >= BullOBs[b].bottom)
                    {
                     if(BullOBs[size].fvg_size > BullOBs[b].fvg_size)
                       {
                        BullOBs[b].active = false;
                       }
                     else
                       {
                        BullOBs[size].active = false;
                        break;
                       }
                    }
                 }
              }
           }
            
         if(vb2.h > vb3.h && vb0.h < vb2.l)
           {
            int size = ArraySize(BearOBs);
            ArrayResize(BearOBs, size + 1, 1000);
            BearOBs[size].active = true;
            BearOBs[size].ob_time = vb2.t;
            BearOBs[size].top = vb2.h;
            BearOBs[size].bottom = vb2.l;
            BearOBs[size].ticket = ++ob_ticket_counter;
            BearOBs[size].fvg_size = vb2.l - vb0.h;
            BearOBs[size].visual_deleted = false;
            BearOBs[size].touch_alerted = false;
            BearOBs[size].has_exited = true;
            BearOBs[size].bars_since_exit = 999;
            
            if(InpMitigation == MITIGATION_BODY)
              {
               for(int b = 0; b < size; b++)
                 {
                  if(!BearOBs[b].active) continue;
                  
                  if(BearOBs[size].bottom <= BearOBs[b].top && BearOBs[size].top >= BearOBs[b].bottom)
                    {
                     if(BearOBs[size].fvg_size > BearOBs[b].fvg_size)
                       {
                        BearOBs[b].active = false;
                       }
                     else
                       {
                        BearOBs[size].active = false;
                        break;
                       }
                    }
                 }
              }
           }
        }

      vb3 = vb2;
      vb2 = vb1;
      vb1 = vb0;

      prev_valid_high = high[i];
      prev_valid_low = low[i];
     }

   // --- REAL-TIME LIVE BAR TOUCH ALERTS ---
   if(InpEnableAlert && rates_total > 1)
     {
      int live_bar = rates_total - 1;
      double check_price = (SymbolInfoDouble(_Symbol, SYMBOL_BID) > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : close[live_bar];
      if(last_tick_price == 0) last_tick_price = check_price;

      bool is_new_bar = (time[live_bar] != prev_live_bar_time);
      if(is_new_bar) prev_live_bar_time = time[live_bar];

      // 1. Bullish OB Touch Alert Logic
      int total_bull = ArraySize(BullOBs);
      int displayed_bull = 0;
      for(int b = total_bull - 1; b >= 0; b--)
        {
         if(!BullOBs[b].active) continue;
         displayed_bull++;
         if(displayed_bull > InpMaxOB) break;
         
         if(check_price > BullOBs[b].top)
           {
            if(!BullOBs[b].has_exited)
              {
               BullOBs[b].has_exited = true;
               BullOBs[b].bars_since_exit = 0;
              }
            else if(is_new_bar && BullOBs[b].touch_alerted)
              {
               BullOBs[b].bars_since_exit++;
              }
               
            if(BullOBs[b].bars_since_exit >= InpAlertCooldownBars)
              {
               BullOBs[b].touch_alerted = false;
              }
           }
         else if(check_price <= BullOBs[b].top)
           {
            BullOBs[b].has_exited = false;
           }
         
         if(last_tick_price > BullOBs[b].top && check_price <= BullOBs[b].top && !BullOBs[b].touch_alerted)
           {
            string msg = StringFormat("Bullish OB Touch at %s [%s, %s]", DoubleToString(BullOBs[b].top, _Digits), _Symbol, EnumToString(_Period));
            if(InpAlertPopup) Alert(msg);
            if(InpAlertPush) SendNotification(msg);
            BullOBs[b].touch_alerted = true;
           }
        }

      // 2. Bearish OB Touch Alert Logic
      int total_bear = ArraySize(BearOBs);
      int displayed_bear = 0;
      for(int b = total_bear - 1; b >= 0; b--)
        {
         if(!BearOBs[b].active) continue;
         displayed_bear++;
         if(displayed_bear > InpMaxOB) break;
         
         if(check_price < BearOBs[b].bottom)
           {
            if(!BearOBs[b].has_exited)
              {
               BearOBs[b].has_exited = true;
               BearOBs[b].bars_since_exit = 0;
              }
            else if(is_new_bar && BearOBs[b].touch_alerted)
              {
               BearOBs[b].bars_since_exit++;
              }
               
            if(BearOBs[b].bars_since_exit >= InpAlertCooldownBars)
              {
               BearOBs[b].touch_alerted = false;
              }
           }
         else if(check_price >= BearOBs[b].bottom)
           {
            BearOBs[b].has_exited = false;
           }
         
         if(last_tick_price < BearOBs[b].bottom && check_price >= BearOBs[b].bottom && !BearOBs[b].touch_alerted)
           {
            string msg = StringFormat("Bearish OB Touch at %s [%s, %s]", DoubleToString(BearOBs[b].bottom, _Digits), _Symbol, EnumToString(_Period));
            if(InpAlertPopup) Alert(msg);
            if(InpAlertPush) SendNotification(msg);
            BearOBs[b].touch_alerted = true;
           }
        }

      last_tick_price = check_price;
     }

   UpdateOBGraphics(time, rates_total - 1);

   return(rates_total);
  }
//+------------------------------------------------------------------+