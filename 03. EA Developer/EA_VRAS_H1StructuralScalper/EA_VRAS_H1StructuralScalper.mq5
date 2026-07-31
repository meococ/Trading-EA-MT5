#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "VRAS H1 Structural Scalper hypothesis HYP-VRAS-EURUSD-M5-005"
#property description "Closed-bar H1 Structure Bias, M5 Session VWAP, Path Confirmation, Structural SL & Break-Even"

#include "NewsCalendar2019_2022.mqh"

enum ENUM_VRAS_SIGNAL
  {
   SIGNAL_NONE=0,
   SIGNAL_BUY=1,
   SIGNAL_SELL=2
  };

input bool                  InpResearchAutoMode=false;
input bool                  InpEnableTelemetry=true;
input string                InpHypothesisId="HYP-VRAS-EURUSD-M5-005";
input string                InpVariantTag="CHALLENGER_H1_STRUCTURAL";
input long                  InpMagic=5600755;

input int                   InpH1EmaPeriod=200;
input int                   InpSwingLookbackBars=10;
input double                InpSlBufferPips=1.5;
input double                InpMinSlPips=4.0;
input double                InpMaxSlPips=15.0;
input double                InpRiskRewardRatio=1.5;
input double                InpBreakEvenTriggerR=1.0;
input double                InpBreakEvenOffsetPips=0.5;

input double                InpRiskPercent=0.25;
input double                InpMaxSpreadPips=1.20;
input int                   InpMaxTradesPerDay=5;
input double                InpDailyLossPct=1.50;
input double                InpMaxAccountDrawdownPct=6.00;
input int                   InpMaxHoldBars=24;
input bool                  InpRequireNewsGuard=false;
input int                   InpNewsBlackoutMinutes=45;
input int                   InpBrokerGMTOffsetWinter=2;
input bool                  InpBrokerFollowsUS_DST=true;

const string EA_NAME="EA_VRAS_H1StructuralScalper";
const string TELEMETRY_PROFILE="lifecycle-v3";

datetime g_last_bar_time=0;
int      g_h1_ema_handle=INVALID_HANDLE;

string   g_run_id="";
string   g_lifecycle_name="";
string   g_run_meta_name="";
string   g_decision_name="";
int      g_lifecycle_handle=INVALID_HANDLE;
int      g_decision_handle=INVALID_HANDLE;

struct PositionState
  {
   ulong    ticket;
   double   entry_price;
   double   initial_sl;
   double   initial_tp;
   double   sl_distance;
   bool     be_applied;
   datetime open_time;
   int      open_bar_index;
  };

PositionState g_active_pos;

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   string payload=StringFormat("{\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\",\"variant_tag\":\"%s\"}",
                               g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,InpHypothesisId,InpVariantTag);
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenTelemetry()
  {
   if(!InpEnableTelemetry)
      return true;
   g_run_id=StringFormat("%s_%I64u",InpHypothesisId,GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_decision_name=StringFormat("%s_DecisionTelemetry_%s.csv",_Symbol,g_run_id);
   
   g_lifecycle_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_lifecycle_handle,"event_time","action","order_type","volume","price",
             "symbol","position_id","risk_pts","initial_risk_account","deal",
             "deal_profit","deal_commission","deal_swap","deal_fee","deal_net",
             "is_final_close");
   FileFlush(g_lifecycle_handle);
   
   g_decision_handle=FileOpen(g_decision_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_decision_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_decision_handle,"server_time","utc_time","variant","regime","event",
             "status","h1_close","h1_ema","vwap","m5_close","m5_low","m5_high",
             "entry","stop","target","spread_pips");
   FileFlush(g_decision_handle);
   
   return WriteRunMeta();
  }

void WriteDecisionTelemetry(datetime server_time, string status, double h1_close, double h1_ema, double vwap, double m5_close, double entry, double stop, double target, double spread)
  {
   if(!InpEnableTelemetry || g_decision_handle==INVALID_HANDLE)
      return;
   FileWrite(g_decision_handle,TimeToString(server_time,TIME_DATE|TIME_SECONDS),TimeToString(server_time,TIME_DATE|TIME_SECONDS),
             InpVariantTag,"TREND","SIGNAL_EVAL",status,h1_close,h1_ema,vwap,m5_close,0.0,0.0,
             entry,stop,target,spread);
   FileFlush(g_decision_handle);
  }

void WriteLifecycleTrade(datetime time, string action, string type, double vol, double price, ulong pos_id, double profit, bool is_final)
  {
   if(!InpEnableTelemetry || g_lifecycle_handle==INVALID_HANDLE)
      return;
   FileWrite(g_lifecycle_handle,TimeToString(time,TIME_DATE|TIME_SECONDS),action,type,vol,price,
             _Symbol,pos_id,0.0,0.0,pos_id,profit,0.0,0.0,0.0,profit,is_final ? "true" : "false");
   FileFlush(g_lifecycle_handle);
  }

int OnInit()
  {
   if(!OpenTelemetry())
     {
      Print("Error opening telemetry files");
      return INIT_FAILED;
     }

   g_h1_ema_handle = iMA(_Symbol, PERIOD_H1, InpH1EmaPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_h1_ema_handle == INVALID_HANDLE)
     {
      Print("Error creating H1 EMA handle");
      return INIT_FAILED;
     }
   
   g_active_pos.ticket = 0;
   Print("EA_VRAS_H1StructuralScalper initialized. Hypothesis: ", InpHypothesisId);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_h1_ema_handle != INVALID_HANDLE)
      IndicatorRelease(g_h1_ema_handle);
   if(g_lifecycle_handle != INVALID_HANDLE)
      FileClose(g_lifecycle_handle);
   if(g_decision_handle != INVALID_HANDLE)
      FileClose(g_decision_handle);
  }

double CalculateSessionVWAP(int lookback_bars)
  {
   double sum_pv = 0.0;
   double sum_v = 0.0;
   for(int i=1; i<=lookback_bars; i++)
     {
      double typical_price = (iHigh(_Symbol, PERIOD_M5, i) + iLow(_Symbol, PERIOD_M5, i) + iClose(_Symbol, PERIOD_M5, i)) / 3.0;
      long vol = iVolume(_Symbol, PERIOD_M5, i);
      if(vol <= 0) vol = 1;
      sum_pv += typical_price * vol;
      sum_v += vol;
     }
   return (sum_v > 0) ? (sum_pv / sum_v) : iClose(_Symbol, PERIOD_M5, 1);
  }

ENUM_VRAS_SIGNAL CheckClosedBarSignal(double &h1_close_out, double &h1_ema_out, double &vwap_out)
  {
   double h1_ema[1];
   if(CopyBuffer(g_h1_ema_handle, 0, 1, 1, h1_ema) <= 0)
      return SIGNAL_NONE;
   
   double h1_close = iClose(_Symbol, PERIOD_H1, 1);
   h1_close_out = h1_close;
   h1_ema_out   = h1_ema[0];
   
   bool h1_bullish = (h1_close > h1_ema[0]);
   bool h1_bearish = (h1_close < h1_ema[0]);
   
   double m5_close1 = iClose(_Symbol, PERIOD_M5, 1);
   double m5_low1   = iLow(_Symbol, PERIOD_M5, 1);
   double m5_high1  = iHigh(_Symbol, PERIOD_M5, 1);
   double m5_high2  = iHigh(_Symbol, PERIOD_M5, 2);
   double m5_low2   = iLow(_Symbol, PERIOD_M5, 2);
   
   double vwap = CalculateSessionVWAP(48);
   vwap_out = vwap;
   
   // BUY Signal: H1 Bullish + M5 Pullback to VWAP + M5 Confirmation
   if(h1_bullish && m5_low1 <= vwap && m5_close1 > vwap && m5_close1 > m5_high2)
      return SIGNAL_BUY;
      
   // SELL Signal: H1 Bearish + M5 Pullback to VWAP + M5 Confirmation
   if(h1_bearish && m5_high1 >= vwap && m5_close1 < vwap && m5_close1 < m5_low2)
      return SIGNAL_SELL;
      
   return SIGNAL_NONE;
  }

void ManageBreakEven()
  {
   if(g_active_pos.ticket == 0 || g_active_pos.be_applied)
      return;
      
   if(!PositionSelectByTicket(g_active_pos.ticket))
     {
      g_active_pos.ticket = 0;
      return;
     }
     
   ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   double current_price = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double profit_dist = (type == POSITION_TYPE_BUY) ? (current_price - g_active_pos.entry_price) : (g_active_pos.entry_price - current_price);
   
   if(profit_dist >= g_active_pos.sl_distance * InpBreakEvenTriggerR)
     {
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      double new_sl = (type == POSITION_TYPE_BUY) ? (g_active_pos.entry_price + InpBreakEvenOffsetPips * 10 * point)
                                                  : (g_active_pos.entry_price - InpBreakEvenOffsetPips * 10 * point);
      
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action   = TRADE_ACTION_SLTP;
      req.position = g_active_pos.ticket;
      req.symbol   = _Symbol;
      req.sl       = NormalizeDouble(new_sl, _Digits);
      req.tp       = PositionGetDouble(POSITION_TP);
      
      if(OrderSend(req, res))
        {
         g_active_pos.be_applied = true;
         Print("Break-Even applied for ticket ", g_active_pos.ticket, " New SL: ", new_sl);
        }
     }
  }

void CheckTimeExits()
  {
   if(g_active_pos.ticket == 0)
      return;
   if(!PositionSelectByTicket(g_active_pos.ticket))
     {
      g_active_pos.ticket = 0;
      return;
     }
     
   int current_bar = iBarShift(_Symbol, PERIOD_M5, PositionGetInteger(POSITION_TIME));
   if(current_bar >= InpMaxHoldBars)
     {
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action   = TRADE_ACTION_DEAL;
      req.position = g_active_pos.ticket;
      req.symbol   = _Symbol;
      req.volume   = PositionGetDouble(POSITION_VOLUME);
      req.type     = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price    = (req.type == ORDER_TYPE_SELL) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      
      if(OrderSend(req, res))
        {
         Print("Time exit applied after ", current_bar, " bars for ticket ", g_active_pos.ticket);
         WriteLifecycleTrade(TimeCurrent(), "CLOSE", EnumToString(req.type), req.volume, req.price, g_active_pos.ticket, PositionGetDouble(POSITION_PROFIT), true);
         g_active_pos.ticket = 0;
        }
     }
  }

void OnTick()
  {
   ManageBreakEven();
   CheckTimeExits();
   
   datetime current_bar_time = iTime(_Symbol, PERIOD_M5, 0);
   if(current_bar_time == g_last_bar_time)
      return;
   g_last_bar_time = current_bar_time;
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double spread_pips = (ask - bid) / (10 * point);
   if(spread_pips > InpMaxSpreadPips)
      return;
      
   if(PositionsTotal() > 0 || g_active_pos.ticket > 0)
      return;
      
   double h1_close=0.0, h1_ema=0.0, vwap=0.0;
   ENUM_VRAS_SIGNAL sig = CheckClosedBarSignal(h1_close, h1_ema, vwap);
   if(sig == SIGNAL_NONE)
      return;
      
   double sl_price = 0.0;
   double tp_price = 0.0;
   double entry_price = (sig == SIGNAL_BUY) ? ask : bid;
   
   if(sig == SIGNAL_BUY)
     {
      int lowest_idx = iLowest(_Symbol, PERIOD_M5, MODE_LOW, InpSwingLookbackBars, 1);
      double swing_low = iLow(_Symbol, PERIOD_M5, lowest_idx);
      sl_price = swing_low - InpSlBufferPips * 10 * point;
      double sl_dist_pips = (entry_price - sl_price) / (10 * point);
      if(sl_dist_pips < InpMinSlPips) sl_price = entry_price - InpMinSlPips * 10 * point;
      if(sl_dist_pips > InpMaxSlPips) sl_price = entry_price - InpMaxSlPips * 10 * point;
      
      double final_sl_dist = entry_price - sl_price;
      tp_price = entry_price + final_sl_dist * InpRiskRewardRatio;
     }
   else if(sig == SIGNAL_SELL)
     {
      int highest_idx = iHighest(_Symbol, PERIOD_M5, MODE_HIGH, InpSwingLookbackBars, 1);
      double swing_high = iHigh(_Symbol, PERIOD_M5, highest_idx);
      sl_price = swing_high + InpSlBufferPips * 10 * point;
      double sl_dist_pips = (sl_price - entry_price) / (10 * point);
      if(sl_dist_pips < InpMinSlPips) sl_price = entry_price + InpMinSlPips * 10 * point;
      if(sl_dist_pips > InpMaxSlPips) sl_price = entry_price + InpMaxSlPips * 10 * point;
      
      double final_sl_dist = sl_price - entry_price;
      tp_price = entry_price - final_sl_dist * InpRiskRewardRatio;
     }
     
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amount = balance * (InpRiskPercent / 100.0);
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double sl_points = MathAbs(entry_price - sl_price) / point;
   double lot_size = (sl_points > 0 && tick_value > 0) ? (risk_amount / (sl_points * tick_value)) : 0.01;
   lot_size = MathFloor(lot_size / 0.01) * 0.01;
   if(lot_size < 0.01) lot_size = 0.01;
   if(lot_size > 10.0) lot_size = 10.0;
   
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action   = TRADE_ACTION_DEAL;
   req.symbol   = _Symbol;
   req.volume   = lot_size;
   req.type     = (sig == SIGNAL_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.price    = entry_price;
   req.sl       = NormalizeDouble(sl_price, _Digits);
   req.tp       = NormalizeDouble(tp_price, _Digits);
   req.magic    = InpMagic;
   req.comment  = InpHypothesisId;
   
   WriteDecisionTelemetry(TimeCurrent(), "ORDER_ACCEPTED", h1_close, h1_ema, vwap, iClose(_Symbol, PERIOD_M5, 1), entry_price, sl_price, tp_price, spread_pips);
   
   if(OrderSend(req, res))
     {
      if(res.retcode == TRADE_RETCODE_DONE || res.deal > 0)
        {
         g_active_pos.ticket         = res.order;
         g_active_pos.entry_price    = entry_price;
         g_active_pos.initial_sl     = sl_price;
         g_active_pos.initial_tp     = tp_price;
         g_active_pos.sl_distance    = MathAbs(entry_price - sl_price);
         g_active_pos.be_applied     = false;
         g_active_pos.open_time      = TimeCurrent();
         g_active_pos.open_bar_index = 0;
         WriteLifecycleTrade(TimeCurrent(), "OPEN", EnumToString(req.type), lot_size, entry_price, res.order, 0.0, false);
         Print("Order executed. Ticket: ", res.order, " Signal: ", EnumToString(sig), " Lot: ", lot_size);
        }
     }
  }
