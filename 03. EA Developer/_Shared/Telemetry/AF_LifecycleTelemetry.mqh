//+------------------------------------------------------------------+
//| AF_LifecycleTelemetry.mqh                                        |
//| lifecycle-v3 minimal telemetry for AlphaFactory fleet EAs.       |
//| Emits exactly one <SYM>_LifecycleTrades_<runid>.csv and one      |
//| <SYM>_RunMeta_<runid>.json per run (tester agent Files dir).     |
//|                                                                  |
//| Usage:                                                           |
//|   input bool InpEnableTelemetry = true;                          |
//|   AfTele_OnInit("EA_X", "HYP-...");   // in OnInit               |
//|   AfTele_OnTransaction(trans);        // in OnTradeTransaction    |
//|   AfTele_OnDeinit();                  // in OnDeinit              |
//+------------------------------------------------------------------+
#ifndef AF_LIFECYCLE_TELEMETRY_MQH
#define AF_LIFECYCLE_TELEMETRY_MQH

string   g_af_tele_run_id = "";
string   g_af_tele_hyp = "";
string   g_af_tele_ea = "";
int      g_af_tele_csv = INVALID_HANDLE;
bool     g_af_tele_enabled = false;

// run counters carried into RunMeta diagnostic block
long     g_af_tele_deals = 0;
long     g_af_tele_opens = 0;
long     g_af_tele_closes = 0;
double   g_af_tele_net = 0.0;

// Planned-risk registry: the EA declares entry-side risk (stop distance in
// points, planned account-currency risk) right after a successful order send;
// the next OPEN deal for this magic binds it to its position id so OPEN rows
// carry real risk evidence and CLOSE rows can repeat it.
long     g_af_risk_pos[];
double   g_af_risk_pts[];
double   g_af_risk_acct[];
double   g_af_pending_risk_pts = 0.0;
double   g_af_pending_risk_acct = 0.0;

void AfTele_SetPlannedRisk(const double risk_pts, const double risk_account)
  {
   g_af_pending_risk_pts = risk_pts;
   g_af_pending_risk_acct = risk_account;
  }

int AfTeleRiskIndex(const long position_id)
  {
   for(int i = 0; i < ArraySize(g_af_risk_pos); i++)
      if(g_af_risk_pos[i] == position_id)
         return i;
   return -1;
  }

void AfTeleBindRisk(const long position_id)
  {
   const int n = ArraySize(g_af_risk_pos);
   ArrayResize(g_af_risk_pos, n + 1);
   ArrayResize(g_af_risk_pts, n + 1);
   ArrayResize(g_af_risk_acct, n + 1);
   g_af_risk_pos[n] = position_id;
   g_af_risk_pts[n] = g_af_pending_risk_pts;
   g_af_risk_acct[n] = g_af_pending_risk_acct;
   g_af_pending_risk_pts = 0.0;
   g_af_pending_risk_acct = 0.0;
  }

string AfTeleJsonEscape(const string s)
  {
   string r = s;
   StringReplace(r, "\\", "\\\\");
   StringReplace(r, "\"", "\\\"");
   return r;
  }

bool AfTeleWriteRunMeta()
  {
   if(!g_af_tele_enabled || g_af_tele_run_id == "")
      return true;
   const string name = StringFormat("%s_RunMeta_%s.json", _Symbol, g_af_tele_run_id);
   const int h = FileOpen(name, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
      return false;
   const string payload = StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\","
      "\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\","
      "\"telemetry_profile\":\"lifecycle-v3\",\"hypothesis_id\":\"%s\","
      "\"promotion_eligible\":false,"
      "\"diagnostic\":{\"deals_logged\":%I64d,\"opens_logged\":%I64d,"
      "\"closes_logged\":%I64d,\"deal_net_sum\":%.2f}}",
      g_af_tele_run_id, AfTeleJsonEscape(g_af_tele_ea), _Symbol,
      AfTeleJsonEscape(g_af_tele_hyp),
      g_af_tele_deals, g_af_tele_opens, g_af_tele_closes, g_af_tele_net);
   FileWriteString(h, payload);
   FileClose(h);
   return true;
  }

bool AfTele_OnInit(const string ea_name, const string hyp_id, const bool enabled)
  {
   g_af_tele_ea = ea_name;
   g_af_tele_hyp = hyp_id;
   g_af_tele_enabled = enabled;
   if(!enabled)
      return true;
   g_af_tele_run_id = StringFormat("%s_%I64u", hyp_id, GetTickCount64());
   const string csv = StringFormat("%s_LifecycleTrades_%s.csv", _Symbol, g_af_tele_run_id);
   g_af_tele_csv = FileOpen(csv, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(g_af_tele_csv == INVALID_HANDLE)
     {
      g_af_tele_enabled = false;
      PrintFormat("AF_TELE: lifecycle csv open failed for %s", csv);
      return false;
     }
   FileWrite(g_af_tele_csv,
             "event_time", "action", "order_type", "volume", "price", "symbol",
             "position_id", "risk_pts", "initial_risk_account", "deal",
             "deal_profit", "deal_commission", "deal_swap", "deal_fee",
             "deal_net", "is_final_close");
   FileFlush(g_af_tele_csv);
   if(!AfTeleWriteRunMeta())
      Print("AF_TELE: RunMeta initial write failed");
   return true;
  }

void AfTele_OnTransaction(const MqlTradeTransaction &trans, const long magic)
  {
   if(!g_af_tele_enabled || g_af_tele_csv == INVALID_HANDLE)
      return;
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.deal == 0)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol)
      return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != magic)
      return;

   const ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_IN && entry != DEAL_ENTRY_INOUT &&
      entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY)
      return;
   const ENUM_DEAL_TYPE dt = (ENUM_DEAL_TYPE)HistoryDealGetInteger(trans.deal, DEAL_TYPE);
   if(dt != DEAL_TYPE_BUY && dt != DEAL_TYPE_SELL)
      return;

   const bool is_open = (entry == DEAL_ENTRY_IN || entry == DEAL_ENTRY_INOUT);
   const long position_id = (long)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
   if(is_open)
      AfTeleBindRisk(position_id);
   const int risk_idx = AfTeleRiskIndex(position_id);
   const double risk_pts = (risk_idx >= 0 ? g_af_risk_pts[risk_idx] : 0.0);
   const double risk_acct = (risk_idx >= 0 ? g_af_risk_acct[risk_idx] : 0.0);
   const string action = is_open ? "OPEN" : "CLOSE";
   // order_type is the position's entry side on every row: an OPEN deal's type
   // is the entry side itself, a closing deal's type is its opposite.
   const string order_type = (dt == DEAL_TYPE_BUY ? "BUY" : "SELL");
   const string position_side = is_open ? order_type
      : (dt == DEAL_TYPE_BUY ? "SELL" : "BUY");
   const bool final_close = !is_open && !PositionSelectByTicket((ulong)position_id);
   const double profit = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
   const double commission = HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
   const double swap = HistoryDealGetDouble(trans.deal, DEAL_SWAP);
   const double fee = HistoryDealGetDouble(trans.deal, DEAL_FEE);
   const double net = profit + commission + swap + fee;

   FileWrite(g_af_tele_csv,
             TimeToString((datetime)HistoryDealGetInteger(trans.deal, DEAL_TIME), TIME_DATE | TIME_SECONDS),
             action, position_side,
             HistoryDealGetDouble(trans.deal, DEAL_VOLUME),
             HistoryDealGetDouble(trans.deal, DEAL_PRICE),
             _Symbol,
             position_id,
             risk_pts, risk_acct,
             (long)trans.deal,
             profit, commission, swap, fee, net,
             (int)final_close);
   FileFlush(g_af_tele_csv);

   g_af_tele_deals++;
   g_af_tele_net += net;
   if(is_open) g_af_tele_opens++; else g_af_tele_closes++;
  }

void AfTele_OnDeinit()
  {
   if(!g_af_tele_enabled)
      return;
   AfTeleWriteRunMeta();
   if(g_af_tele_csv != INVALID_HANDLE)
     {
      FileClose(g_af_tele_csv);
      g_af_tele_csv = INVALID_HANDLE;
     }
   g_af_tele_enabled = false;
  }

#endif
