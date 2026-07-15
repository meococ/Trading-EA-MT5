//+------------------------------------------------------------------+
//| SonicR_CaseSnapshot.mq5                                          |
//| MT5-native visual audit helper for sampled Sonic R casebook rows. |
//| Visual evidence only; not a strategy validation or promotion gate.|
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input string InpCasesFile = "SonicR_CaseSnapshot\\cases.csv";
input string InpOutputPrefix = "SonicR_CaseSnapshot";
input int    InpMaxCases = 20;
input int    InpWidth = 1280;
input int    InpHeight = 720;
input int    InpRightPaddingBars = 12;
input bool   InpAddDragonTrend = true;
input bool   InpCloseChartsAfterShot = true;

#define SNR_CASE_FIELDS 24

struct SnrSnapshotCase
{
   string case_id;
   string symbol;
   ENUM_TIMEFRAMES timeframe;
   string timeframe_text;
   datetime event_time;
   string direction;
   double entry_price;
   double stop_loss;
   double target_price;
   string entry_reason;
   string realized_r;
   string pnl_net;
   string session_bucket;
   string h1_bias;
   string h4_bias;
   string dragon_slope_atr;
   string trend_slope_atr;
   string pvsra_bias;
   string pvsra_event;
   string pvsra_grade;
   string level_zone;
   string level_distance_pips;
   string sample_reason;
   string source_case_id;
   string note;
};

string SanitizeFilePart(string value)
{
   string out = "";
   for(int i = 0; i < StringLen(value); i++)
   {
      ushort ch = StringGetCharacter(value, i);
      bool ok = ((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_');
      out += (ok ? ShortToString(ch) : "_");
   }
   if(StringLen(out) == 0)
      out = "case";
   if(StringLen(out) > 34)
      out = StringSubstr(out, 0, 34);
   return out;
}

ENUM_TIMEFRAMES ParseTimeframe(string value)
{
   StringToUpper(value);
   if(value == "PERIOD_M1" || value == "M1") return PERIOD_M1;
   if(value == "PERIOD_M5" || value == "M5") return PERIOD_M5;
   if(value == "PERIOD_M15" || value == "M15") return PERIOD_M15;
   if(value == "PERIOD_M30" || value == "M30") return PERIOD_M30;
   if(value == "PERIOD_H1" || value == "H1") return PERIOD_H1;
   if(value == "PERIOD_H4" || value == "H4") return PERIOD_H4;
   if(value == "PERIOD_D1" || value == "D1") return PERIOD_D1;
   return PERIOD_M5;
}

string TfLabel(ENUM_TIMEFRAMES tf)
{
   string text = EnumToString(tf);
   StringReplace(text, "PERIOD_", "");
   return text;
}

bool ReadCaseRow(const int handle, SnrSnapshotCase &row)
{
   if(FileIsEnding(handle))
      return false;

   string values[SNR_CASE_FIELDS];
   for(int i = 0; i < SNR_CASE_FIELDS; i++)
   {
      if(FileIsEnding(handle))
         return false;
      values[i] = FileReadString(handle);
   }

   row.case_id = values[0];
   row.symbol = values[1];
   row.timeframe_text = values[2];
   row.timeframe = ParseTimeframe(values[2]);
   row.event_time = StringToTime(values[3]);
   row.direction = values[4];
   row.entry_price = StringToDouble(values[5]);
   row.stop_loss = StringToDouble(values[6]);
   row.target_price = StringToDouble(values[7]);
   row.entry_reason = values[8];
   row.realized_r = values[9];
   row.pnl_net = values[10];
   row.session_bucket = values[11];
   row.h1_bias = values[12];
   row.h4_bias = values[13];
   row.dragon_slope_atr = values[14];
   row.trend_slope_atr = values[15];
   row.pvsra_bias = values[16];
   row.pvsra_event = values[17];
   row.pvsra_grade = values[18];
   row.level_zone = values[19];
   row.level_distance_pips = values[20];
   row.sample_reason = values[21];
   row.source_case_id = values[22];
   row.note = values[23];
   return row.event_time > 0 && row.symbol != "";
}

void SkipHeader(const int handle)
{
   for(int i = 0; i < SNR_CASE_FIELDS && !FileIsEnding(handle); i++)
      FileReadString(handle);
}

void AddHLine(const long chart_id, const string name, const double price, const color clr, const int style, const string text)
{
   if(price <= 0.0)
      return;
   ObjectDelete(chart_id, name);
   if(ObjectCreate(chart_id, name, OBJ_HLINE, 0, 0, price))
   {
      ObjectSetInteger(chart_id, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(chart_id, name, OBJPROP_STYLE, style);
      ObjectSetInteger(chart_id, name, OBJPROP_WIDTH, 2);
      ObjectSetString(chart_id, name, OBJPROP_TEXT, text);
   }
}

void AddVLine(const long chart_id, const string name, const datetime when, const color clr, const string text)
{
   ObjectDelete(chart_id, name);
   if(ObjectCreate(chart_id, name, OBJ_VLINE, 0, when, 0.0))
   {
      ObjectSetInteger(chart_id, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(chart_id, name, OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(chart_id, name, OBJPROP_WIDTH, 2);
      ObjectSetString(chart_id, name, OBJPROP_TEXT, text);
   }
}

void AddLabel(const long chart_id, const string name, const string text, const int y)
{
   ObjectDelete(chart_id, name);
   if(ObjectCreate(chart_id, name, OBJ_LABEL, 0, 0, 0))
   {
      ObjectSetInteger(chart_id, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(chart_id, name, OBJPROP_XDISTANCE, 12);
      ObjectSetInteger(chart_id, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(chart_id, name, OBJPROP_FONTSIZE, 9);
      ObjectSetInteger(chart_id, name, OBJPROP_COLOR, clrWhite);
      ObjectSetString(chart_id, name, OBJPROP_FONT, "Consolas");
      ObjectSetString(chart_id, name, OBJPROP_TEXT, text);
   }
}

void ConfigureChart(const long chart_id)
{
   ChartSetInteger(chart_id, CHART_AUTOSCROLL, false);
   ChartSetInteger(chart_id, CHART_SHIFT, true);
   ChartSetInteger(chart_id, CHART_MODE, CHART_CANDLES);
   ChartSetInteger(chart_id, CHART_SHOW_GRID, false);
   ChartSetInteger(chart_id, CHART_SHOW_VOLUMES, CHART_VOLUME_TICK);
   ChartSetInteger(chart_id, CHART_COLOR_BACKGROUND, clrBlack);
   ChartSetInteger(chart_id, CHART_COLOR_FOREGROUND, clrSilver);
   ChartSetInteger(chart_id, CHART_COLOR_CANDLE_BULL, clrSeaGreen);
   ChartSetInteger(chart_id, CHART_COLOR_CANDLE_BEAR, clrIndianRed);
   ChartSetInteger(chart_id, CHART_COLOR_CHART_UP, clrSeaGreen);
   ChartSetInteger(chart_id, CHART_COLOR_CHART_DOWN, clrIndianRed);
}

void AddDragonTrend(const long chart_id, const string symbol, const ENUM_TIMEFRAMES tf)
{
   if(!InpAddDragonTrend)
      return;
   int dragon_high = iMA(symbol, tf, 34, 0, MODE_EMA, PRICE_HIGH);
   int dragon_close = iMA(symbol, tf, 34, 0, MODE_EMA, PRICE_CLOSE);
   int dragon_low = iMA(symbol, tf, 34, 0, MODE_EMA, PRICE_LOW);
   int trend = iMA(symbol, tf, 89, 0, MODE_EMA, PRICE_CLOSE);
   if(dragon_high != INVALID_HANDLE) ChartIndicatorAdd(chart_id, 0, dragon_high);
   if(dragon_close != INVALID_HANDLE) ChartIndicatorAdd(chart_id, 0, dragon_close);
   if(dragon_low != INVALID_HANDLE) ChartIndicatorAdd(chart_id, 0, dragon_low);
   if(trend != INVALID_HANDLE) ChartIndicatorAdd(chart_id, 0, trend);
}

bool EnsureEventBar(const string symbol, const ENUM_TIMEFRAMES tf, const datetime event_time)
{
   int period_seconds = PeriodSeconds(tf);
   if(period_seconds <= 0)
      period_seconds = 300;

   datetime from_time = event_time - period_seconds * 220;
   datetime to_time = event_time + period_seconds * 40;
   MqlRates rates[];

   for(int attempt = 0; attempt < 12; attempt++)
   {
      ResetLastError();
      int copied = CopyRates(symbol, tf, from_time, to_time, rates);
      int shift = iBarShift(symbol, tf, event_time, true);
      datetime bar_time = (shift >= 0 ? iTime(symbol, tf, shift) : 0);
      if(copied > 0 && shift >= 0 && bar_time == event_time)
         return true;
      Sleep(500);
   }
   return false;
}

string ContextLine(const SnrSnapshotCase &row)
{
   return StringFormat("%s %s %s | R=%s PnL=%s | H1=%s H4=%s | Dragon=%s Trend=%s | PVSRA=%s/%s/%s | Level=%s %sp",
                       row.symbol,
                       TfLabel(row.timeframe),
                       TimeToString(row.event_time, TIME_DATE | TIME_MINUTES),
                       row.realized_r,
                       row.pnl_net,
                       row.h1_bias,
                       row.h4_bias,
                       row.dragon_slope_atr,
                       row.trend_slope_atr,
                       row.pvsra_bias,
                       row.pvsra_event,
                       row.pvsra_grade,
                       row.level_zone,
                       row.level_distance_pips);
}

bool IsShiftVisible(const long chart_id, const int shift, long &first_visible, long &visible_bars, long &last_visible)
{
   first_visible = ChartGetInteger(chart_id, CHART_FIRST_VISIBLE_BAR, 0);
   visible_bars = ChartGetInteger(chart_id, CHART_VISIBLE_BARS, 0);
   last_visible = first_visible - visible_bars + 1;
   return (first_visible >= 0 && visible_bars > 0 && shift <= first_visible && shift >= last_visible);
}

bool NavigateEventIntoView(const long chart_id, const int shift, const string case_id)
{
   int offsets[4];
   offsets[0] = shift + InpRightPaddingBars;
   offsets[1] = shift;
   offsets[2] = shift - InpRightPaddingBars;
   offsets[3] = shift + 1;

   for(int attempt = 0; attempt < 4; attempt++)
   {
      int offset = offsets[attempt];
      if(offset < 0)
         offset = 0;
      ChartNavigate(chart_id, CHART_END, -offset);
      ChartRedraw(chart_id);
      Sleep(1200);

      long first_visible = 0;
      long visible_bars = 0;
      long last_visible = 0;
      if(IsShiftVisible(chart_id, shift, first_visible, visible_bars, last_visible))
         return true;
   }

   long first_visible = 0;
   long visible_bars = 0;
   long last_visible = 0;
   IsShiftVisible(chart_id, shift, first_visible, visible_bars, last_visible);
   PrintFormat("Event bar not visible for %s. shift=%d first=%I64d visible=%I64d last=%I64d. Refusing screenshot.",
               case_id,
               shift,
               first_visible,
               visible_bars,
               last_visible);
   return false;
}

bool CaptureCase(const SnrSnapshotCase &row, const int index, string &file_name)
{
   SymbolSelect(row.symbol, true);
   long chart_id = ChartOpen(row.symbol, row.timeframe);
   if(chart_id == 0)
   {
      PrintFormat("ChartOpen failed for %s %s. Error=%d", row.symbol, TfLabel(row.timeframe), GetLastError());
      return false;
   }

   Sleep(1200);
   if(!EnsureEventBar(row.symbol, row.timeframe, row.event_time))
   {
      PrintFormat("Event bar unavailable for %s %s %s. Refusing current-chart screenshot. Error=%d",
                  row.symbol,
                  TfLabel(row.timeframe),
                  TimeToString(row.event_time, TIME_DATE | TIME_MINUTES),
                  GetLastError());
      if(InpCloseChartsAfterShot)
         ChartClose(chart_id);
      return false;
   }

   ConfigureChart(chart_id);
   AddDragonTrend(chart_id, row.symbol, row.timeframe);

   int shift = iBarShift(row.symbol, row.timeframe, row.event_time, true);
   if(shift < 0)
   {
      PrintFormat("Event shift unavailable after history load for %s. Refusing screenshot.", row.case_id);
      if(InpCloseChartsAfterShot)
         ChartClose(chart_id);
      return false;
   }
   datetime chart_bar_time = iTime(row.symbol, row.timeframe, shift);
   if(chart_bar_time != row.event_time)
   {
      PrintFormat("Event bar mismatch for %s. Expected=%s actual=%s. Refusing screenshot.",
                  row.case_id,
                  TimeToString(row.event_time, TIME_DATE | TIME_MINUTES),
                  TimeToString(chart_bar_time, TIME_DATE | TIME_MINUTES));
      if(InpCloseChartsAfterShot)
         ChartClose(chart_id);
      return false;
   }
   if(!NavigateEventIntoView(chart_id, shift, row.case_id))
   {
      if(InpCloseChartsAfterShot)
         ChartClose(chart_id);
      return false;
   }

   string prefix = "snr_" + IntegerToString(index) + "_";
   AddVLine(chart_id, prefix + "event", row.event_time, clrDodgerBlue, "event");
   AddHLine(chart_id, prefix + "entry", row.entry_price, clrDodgerBlue, STYLE_SOLID, "entry");
   AddHLine(chart_id, prefix + "sl", row.stop_loss, clrTomato, STYLE_DASH, "sl");
   AddHLine(chart_id, prefix + "tp", row.target_price, clrLimeGreen, STYLE_DASH, "tp");
   AddLabel(chart_id, prefix + "label1", ContextLine(row), 18);
   AddLabel(chart_id, prefix + "label2", row.sample_reason + " | " + row.entry_reason + " | " + row.note, 36);

   ChartRedraw(chart_id);
   Sleep(1000);

   int event_x = 0;
   int entry_y = 0;
   bool entry_visible = ChartTimePriceToXY(chart_id, 0, row.event_time, row.entry_price, event_x, entry_y);
   if(!entry_visible || event_x < 0 || event_x > InpWidth || entry_y < 0 || entry_y > InpHeight)
   {
      PrintFormat("Event entry point not visible for %s. visible=%d x=%d y=%d entry=%.5f. Refusing screenshot.",
                  row.case_id,
                  entry_visible,
                  event_x,
                  entry_y,
                  row.entry_price);
      if(InpCloseChartsAfterShot)
         ChartClose(chart_id);
      return false;
   }

   string safe_case = SanitizeFilePart(row.case_id);
   file_name = StringFormat("%s_%03d_%s.png", InpOutputPrefix, index, safe_case);
   if(StringLen(file_name) > 63)
      file_name = StringSubstr(file_name, 0, 59) + ".png";

   ResetLastError();
   bool ok = ChartScreenShot(chart_id, file_name, InpWidth, InpHeight, ALIGN_LEFT);
   if(!ok)
      PrintFormat("ChartScreenShot failed for %s. Error=%d", row.case_id, GetLastError());
   else
      PrintFormat("Sonic snapshot saved: %s", file_name);

   if(InpCloseChartsAfterShot)
   {
      Sleep(200);
      ChartClose(chart_id);
   }
   return ok;
}

void WriteShotRow(const int handle, const SnrSnapshotCase &row, const string file_name, const bool ok)
{
   FileWrite(handle,
             row.case_id,
             row.symbol,
             TfLabel(row.timeframe),
             TimeToString(row.event_time, TIME_DATE | TIME_MINUTES),
             row.direction,
             row.entry_reason,
             row.sample_reason,
             row.realized_r,
             row.pnl_net,
             file_name,
             (ok ? "OK" : "FAILED"));
}

void OnStart()
{
   int input_handle = FileOpen(InpCasesFile, FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(input_handle == INVALID_HANDLE)
   {
      PrintFormat("Cannot open %s. Error=%d", InpCasesFile, GetLastError());
      return;
   }

   int output_handle = FileOpen("SonicR_CaseSnapshot\\shots.csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(output_handle == INVALID_HANDLE)
   {
      PrintFormat("Cannot open shots.csv. Error=%d", GetLastError());
      FileClose(input_handle);
      return;
   }
   FileWrite(output_handle, "case_id", "symbol", "timeframe", "event_time", "direction", "entry_reason", "sample_reason", "realized_r", "pnl_net", "png_file", "status");

   SkipHeader(input_handle);

   int count = 0;
   while(!FileIsEnding(input_handle) && count < InpMaxCases)
   {
      SnrSnapshotCase row;
      if(!ReadCaseRow(input_handle, row))
         break;
      count++;
      string file_name = "";
      bool ok = CaptureCase(row, count, file_name);
      WriteShotRow(output_handle, row, file_name, ok);
   }

   FileClose(output_handle);
   FileClose(input_handle);
   PrintFormat("SonicR_CaseSnapshot finished. Cases attempted=%d", count);
}
