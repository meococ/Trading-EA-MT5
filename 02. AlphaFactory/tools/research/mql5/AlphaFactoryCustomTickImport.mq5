//+------------------------------------------------------------------+
//| AlphaFactoryCustomTickImport.mq5                                 |
//| Data-only custom-symbol importer. No orders, positions or PnL.   |
//| Binary schema: AFDTICK1, <QQ header, then <qdd tick records.      |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

const string PLAN_PATH    = "AlphaFactoryCustomImport\\active_plan.csv";
const string RECEIPT_PATH = "AlphaFactoryCustomImport\\active_receipt.csv";
const long   AFD_MAGIC    = 0x4146445449434B31;
const int    HEADER_BYTES = 16;
const int    RECORD_BYTES = 24;
const int    MAX_TICKS_PER_DAY = 2000000;
const long   READBACK_WINDOW_MSC = 3600000;

void CloseWithFailure(const int receipt,
                      const string code,
                      const string detail)
  {
   if(receipt != INVALID_HANDLE)
     {
      FileWrite(receipt, "FATAL", code, detail);
      FileFlush(receipt);
      FileClose(receipt);
     }
   Print("AlphaFactoryCustomTickImport FATAL ", code, " ", detail);
   TerminalClose(1);
  }

bool NearlyEqual(const double left, const double right, const double tolerance)
  {
   return MathAbs(left - right) <= tolerance;
  }

bool ParseLongCell(const string text, long &value)
  {
   int length = StringLen(text);
   if(length < 1)
      return false;
   int offset = 0;
   if(StringGetCharacter(text, 0) == '-')
     {
      if(length == 1)
         return false;
      offset = 1;
     }
   for(int index = offset; index < length; index++)
     {
      ushort character = StringGetCharacter(text, index);
      if(character < '0' || character > '9')
         return false;
     }
   value = StringToInteger(text);
   return IntegerToString(value) == text;
  }

bool ParseDoubleCell(const string text, double &value)
  {
   int length = StringLen(text);
   if(length < 1)
      return false;
   bool mantissa_digit = false;
   bool exponent_seen = false;
   bool exponent_digit = false;
   bool decimal_seen = false;
   for(int index = 0; index < length; index++)
     {
      ushort character = StringGetCharacter(text, index);
      if(character >= '0' && character <= '9')
        {
         if(exponent_seen)
            exponent_digit = true;
         else
            mantissa_digit = true;
         continue;
        }
      if((character == '+' || character == '-') &&
         (index == 0 || (index > 0 &&
          (StringGetCharacter(text, index - 1) == 'e' ||
           StringGetCharacter(text, index - 1) == 'E'))))
         continue;
      if(character == '.' && !decimal_seen && !exponent_seen)
        {
         decimal_seen = true;
         continue;
        }
      if((character == 'e' || character == 'E') &&
         !exponent_seen && mantissa_digit)
        {
         exponent_seen = true;
         continue;
        }
      return false;
     }
   if(!mantissa_digit || (exponent_seen && !exponent_digit))
      return false;
   value = StringToDouble(text);
   return MathIsValidNumber(value);
  }

void OnStart()
  {
   int receipt = FileOpen(RECEIPT_PATH, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(receipt == INVALID_HANDLE)
     {
      Print("AlphaFactoryCustomTickImport cannot open receipt: ", GetLastError());
      TerminalClose(1);
      return;
     }
   FileWrite(receipt, "RECEIPT", "alphafactory_custom_tick_import_receipt.v1",
             "SOURCE_DATA_ONLY_NO_PERFORMANCE");

   int plan = FileOpen(PLAN_PATH, FILE_READ | FILE_CSV | FILE_ANSI, ';');
   if(plan == INVALID_HANDLE)
     {
      CloseWithFailure(receipt, "PLAN_OPEN_FAILED", IntegerToString(GetLastError()));
      return;
     }

   string tag = FileReadString(plan);
   string schema = FileReadString(plan);
   string custom_symbol = FileReadString(plan);
   string origin_symbol = FileReadString(plan);
   string digits_text = FileReadString(plan);
   string point_text = FileReadString(plan);
   string tick_size_text = FileReadString(plan);
   string source_contract_sha256 = FileReadString(plan);
   string range_manifest_sha256 = FileReadString(plan);
   string import_plan_sha256 = FileReadString(plan);
   string expected_days_text = FileReadString(plan);
   string range_from_sec_text = FileReadString(plan);
   string range_to_sec_text = FileReadString(plan);
   string expected_m1_bars_text = FileReadString(plan);
   string expected_m1_first_sec_text = FileReadString(plan);
   long digits_value = 0;
   long expected_days_value = 0;
   long range_from_sec = 0;
   long range_to_sec = 0;
   long expected_m1_bars_value = 0;
   long expected_m1_first_sec = 0;
   double point = 0.0;
   double tick_size = 0.0;
   bool meta_numeric_ok =
      ParseLongCell(digits_text, digits_value) &&
      ParseDoubleCell(point_text, point) &&
      ParseDoubleCell(tick_size_text, tick_size) &&
      ParseLongCell(expected_days_text, expected_days_value) &&
      ParseLongCell(range_from_sec_text, range_from_sec) &&
      ParseLongCell(range_to_sec_text, range_to_sec) &&
      ParseLongCell(expected_m1_bars_text, expected_m1_bars_value) &&
      ParseLongCell(expected_m1_first_sec_text, expected_m1_first_sec);
   int digits = (int)digits_value;
   int expected_days = (int)expected_days_value;
   int expected_m1_bars = (int)expected_m1_bars_value;
   if(tag != "META" || schema != "alphafactory_custom_tick_import_plan.v1" ||
      !meta_numeric_ok ||
      custom_symbol == "" || origin_symbol == "" || digits < 0 || digits > 12 ||
      point <= 0.0 || tick_size <= 0.0 || expected_days < 1 ||
      range_from_sec <= 0 || range_to_sec < range_from_sec ||
      expected_m1_bars <= 0 || expected_m1_first_sec <= 0 ||
      StringLen(source_contract_sha256) != 64 || StringLen(range_manifest_sha256) != 64 ||
      StringLen(import_plan_sha256) != 64)
     {
      FileClose(plan);
      CloseWithFailure(receipt, "META_CONTRACT_INVALID", "plan header failed validation");
      return;
     }

   string expected_description =
      "AlphaFactory Duka " + StringSubstr(source_contract_sha256, 0, 16) +
      " plan " + StringSubstr(import_plan_sha256, 0, 16);
   bool is_custom = false;
   bool symbol_existed = SymbolExist(custom_symbol, is_custom);
   if(!symbol_existed)
     {
      if(!CustomSymbolCreate(custom_symbol, "AlphaFactory\\Dukascopy", origin_symbol))
        {
         FileClose(plan);
         CloseWithFailure(receipt, "CUSTOM_SYMBOL_CREATE_FAILED", IntegerToString(GetLastError()));
         return;
        }
     }
   else if(!is_custom)
     {
      FileClose(plan);
      CloseWithFailure(receipt, "SYMBOL_EXISTS_NOT_CUSTOM", custom_symbol);
      return;
     }
   else if(SymbolInfoString(custom_symbol, SYMBOL_DESCRIPTION) != expected_description)
     {
      FileClose(plan);
      CloseWithFailure(receipt, "SYMBOL_PLAN_IDENTITY_MISMATCH", custom_symbol);
      return;
     }

   SymbolSelect(custom_symbol, false);
   ResetLastError();
   bool properties_ok =
      CustomSymbolSetInteger(custom_symbol, SYMBOL_DIGITS, (long)digits) &&
      CustomSymbolSetInteger(custom_symbol, SYMBOL_CHART_MODE, (long)SYMBOL_CHART_MODE_BID) &&
      CustomSymbolSetDouble(custom_symbol, SYMBOL_POINT, point) &&
      CustomSymbolSetDouble(custom_symbol, SYMBOL_TRADE_TICK_SIZE, tick_size) &&
      CustomSymbolSetString(custom_symbol, SYMBOL_DESCRIPTION, expected_description);
   if(!properties_ok)
     {
      FileClose(plan);
      CloseWithFailure(receipt, "CUSTOM_SYMBOL_PROPERTY_SET_FAILED", IntegerToString(GetLastError()));
      return;
     }
   int deleted_rates = CustomRatesDelete(custom_symbol,
                                         (datetime)range_from_sec,
                                         (datetime)range_to_sec);
   if(deleted_rates < 0)
     {
      FileClose(plan);
      CloseWithFailure(receipt, "CUSTOM_RATES_DELETE_FAILED", IntegerToString(GetLastError()));
      return;
     }
   if((int)SymbolInfoInteger(custom_symbol, SYMBOL_DIGITS) != digits ||
      !NearlyEqual(SymbolInfoDouble(custom_symbol, SYMBOL_POINT), point, point / 1000.0) ||
      !NearlyEqual(SymbolInfoDouble(custom_symbol, SYMBOL_TRADE_TICK_SIZE), tick_size,
                   point / 1000.0) ||
      (ENUM_SYMBOL_CHART_MODE)SymbolInfoInteger(custom_symbol, SYMBOL_CHART_MODE) !=
         SYMBOL_CHART_MODE_BID ||
      !SymbolInfoInteger(custom_symbol, SYMBOL_CUSTOM))
     {
      FileClose(plan);
      CloseWithFailure(receipt, "CUSTOM_SYMBOL_PROPERTY_READBACK_FAILED", custom_symbol);
      return;
     }
   if(!SymbolSelect(custom_symbol, true))
     {
      FileClose(plan);
      CloseWithFailure(receipt, "CUSTOM_SYMBOL_SELECT_FAILED", IntegerToString(GetLastError()));
      return;
     }

   FileWrite(receipt, "META", "PASS", custom_symbol, origin_symbol, digits,
             DoubleToString(point, digits), DoubleToString(tick_size, digits),
             source_contract_sha256, range_manifest_sha256, import_plan_sha256, expected_days,
             range_from_sec, range_to_sec, expected_m1_bars, expected_m1_first_sec);

   int imported_days = 0;
   long imported_ticks = 0;
   while(!FileIsEnding(plan))
     {
      tag = FileReadString(plan);
      if(tag == "END")
         break;
      if(tag != "DAY")
        {
         FileClose(plan);
         CloseWithFailure(receipt, "DAY_TAG_INVALID", tag);
         return;
        }
      string date_utc = FileReadString(plan);
      string relative_path = FileReadString(plan);
      string expected_sha256 = FileReadString(plan);
      string expected_count_text = FileReadString(plan);
      string day_from_msc_text = FileReadString(plan);
      string day_to_msc_text = FileReadString(plan);
      string expected_first_msc_text = FileReadString(plan);
      string expected_last_msc_text = FileReadString(plan);
      long expected_count = 0;
      long day_from_msc = 0;
      long day_to_msc = 0;
      long expected_first_msc = 0;
      long expected_last_msc = 0;
      bool day_numeric_ok =
         ParseLongCell(expected_count_text, expected_count) &&
         ParseLongCell(day_from_msc_text, day_from_msc) &&
         ParseLongCell(day_to_msc_text, day_to_msc) &&
         ParseLongCell(expected_first_msc_text, expected_first_msc) &&
         ParseLongCell(expected_last_msc_text, expected_last_msc);
      if(date_utc == "" || relative_path == "" || StringLen(expected_sha256) != 64 ||
         !day_numeric_ok ||
         StringFind(relative_path, "AlphaFactoryCustomImport\\") != 0 ||
         StringFind(relative_path, "..") >= 0 || StringFind(relative_path, ":") >= 0 ||
         expected_count < 0 || expected_count > MAX_TICKS_PER_DAY ||
         day_from_msc <= 0 || day_to_msc < day_from_msc)
        {
         FileClose(plan);
         CloseWithFailure(receipt, "DAY_CONTRACT_INVALID", date_utc);
         return;
        }

      int source = FileOpen(relative_path, FILE_READ | FILE_BIN);
      if(source == INVALID_HANDLE)
        {
         FileClose(plan);
         CloseWithFailure(receipt, "BINARY_OPEN_FAILED", relative_path);
         return;
        }
      long expected_size = HEADER_BYTES + expected_count * RECORD_BYTES;
      long actual_size = FileGetInteger(source, FILE_SIZE);
      long magic = FileReadLong(source);
      long header_count = FileReadLong(source);
      if(actual_size != expected_size || magic != AFD_MAGIC || header_count != expected_count)
        {
         FileClose(source);
         FileClose(plan);
         CloseWithFailure(receipt, "BINARY_HEADER_OR_SIZE_MISMATCH", relative_path);
         return;
        }

      MqlTick ticks[];
      if(ArrayResize(ticks, (int)expected_count) != (int)expected_count)
        {
         FileClose(source);
         FileClose(plan);
         CloseWithFailure(receipt, "TICK_ARRAY_ALLOCATION_FAILED", date_utc);
         return;
        }
      long previous_msc = -1;
      for(int i = 0; i < (int)expected_count; i++)
        {
         long time_msc = FileReadLong(source);
         double bid = FileReadDouble(source);
         double ask = FileReadDouble(source);
         if(time_msc < day_from_msc || time_msc > day_to_msc ||
            (previous_msc >= 0 && time_msc < previous_msc) ||
            bid <= 0.0 || ask < bid)
           {
            FileClose(source);
            FileClose(plan);
            CloseWithFailure(receipt, "TICK_RECORD_INVALID", date_utc);
            return;
           }
         previous_msc = time_msc;
         ticks[i].time = (datetime)(time_msc / 1000);
         ticks[i].time_msc = time_msc;
         ticks[i].bid = bid;
         ticks[i].ask = ask;
         ticks[i].last = 0.0;
         ticks[i].volume = 0;
         ticks[i].volume_real = 0.0;
         ticks[i].flags = TICK_FLAG_BID | TICK_FLAG_ASK;
        }
      FileClose(source);
      if((expected_count == 0 && (expected_first_msc != 0 || expected_last_msc != 0)) ||
         (expected_count > 0 &&
          (ticks[0].time_msc != expected_first_msc ||
           ticks[(int)expected_count - 1].time_msc != expected_last_msc)))
        {
         FileClose(plan);
         CloseWithFailure(receipt, "TICK_BOUNDARY_MISMATCH", date_utc);
         return;
        }

      int replaced = 0;
      if(expected_count == 0)
        {
         int deleted = CustomTicksDelete(custom_symbol, day_from_msc, day_to_msc);
         if(deleted < 0)
           {
            FileClose(plan);
            CloseWithFailure(receipt, "EMPTY_DAY_DELETE_FAILED", date_utc);
            return;
           }
        }
      else
        {
         replaced = CustomTicksReplace(custom_symbol, (ulong)day_from_msc,
                                       (ulong)day_to_msc, ticks);
         if(replaced != (int)expected_count)
           {
            FileClose(plan);
            CloseWithFailure(receipt, "CUSTOM_TICKS_REPLACE_MISMATCH", date_utc);
            return;
           }
        }

      int readback = 0;
      bool readback_failed = false;
      for(long window_from = day_from_msc;
          window_from <= day_to_msc;
          window_from += READBACK_WINDOW_MSC)
        {
         long window_to = MathMin(day_to_msc, window_from + READBACK_WINDOW_MSC - 1);
         MqlTick verify[];
         int copied = CopyTicksRange(custom_symbol, verify, COPY_TICKS_ALL,
                                     (ulong)window_from, (ulong)window_to);
         if(copied < 0 || readback + copied > (int)expected_count)
           {
            readback_failed = true;
            ArrayFree(verify);
            break;
           }
         for(int j = 0; j < copied; j++)
           {
            int source_index = readback + j;
            if(verify[j].time_msc != ticks[source_index].time_msc ||
               !NearlyEqual(verify[j].bid, ticks[source_index].bid, point / 1000.0) ||
               !NearlyEqual(verify[j].ask, ticks[source_index].ask, point / 1000.0))
              {
               readback_failed = true;
               break;
              }
           }
         readback += copied;
         ArrayFree(verify);
         if(readback_failed)
            break;
        }
      if(readback_failed || readback != (int)expected_count ||
         (readback > 0 &&
          (ticks[0].time_msc != expected_first_msc ||
           ticks[readback - 1].time_msc != expected_last_msc)))
        {
         FileClose(plan);
         CloseWithFailure(receipt, "CUSTOM_TICK_READBACK_MISMATCH", date_utc);
         return;
        }
      FileWrite(receipt, "DAY", date_utc, "PASS", expected_count, replaced,
                readback, expected_first_msc, expected_last_msc, expected_sha256);
      FileFlush(receipt);
      imported_days++;
      imported_ticks += expected_count;
     }
   FileClose(plan);

   if(imported_days != expected_days)
     {
      CloseWithFailure(receipt, "DAY_COUNT_MISMATCH", IntegerToString(imported_days));
      return;
     }
   bool m1_synchronized = false;
   long m1_first = 0;
   int m1_bars = 0;
   for(int wait = 0; wait < 600; wait++)
     {
      m1_bars = Bars(custom_symbol, PERIOD_M1,
                     (datetime)range_from_sec, (datetime)range_to_sec);
      m1_synchronized =
         (bool)SeriesInfoInteger(custom_symbol, PERIOD_M1, SERIES_SYNCHRONIZED);
      m1_first = SeriesInfoInteger(custom_symbol, PERIOD_M1, SERIES_FIRSTDATE);
      if(m1_synchronized && m1_first == expected_m1_first_sec &&
         m1_bars == expected_m1_bars)
         break;
      Sleep(100);
     }
   if(!m1_synchronized || m1_first != expected_m1_first_sec ||
      m1_bars != expected_m1_bars)
     {
      CloseWithFailure(receipt, "M1_READBACK_MISMATCH",
                       StringFormat("sync=%s first=%I64d/%I64d bars=%d/%d",
                                    (string)m1_synchronized, m1_first,
                                    expected_m1_first_sec, m1_bars, expected_m1_bars));
      return;
     }
   FileWrite(receipt, "SUMMARY", "PASS", custom_symbol, imported_days,
             imported_ticks, m1_synchronized, m1_first, m1_bars,
             source_contract_sha256, range_manifest_sha256, import_plan_sha256);
   FileFlush(receipt);
   FileClose(receipt);
   Print("AlphaFactoryCustomTickImport PASS symbol=", custom_symbol,
         " days=", imported_days, " ticks=", imported_ticks,
         " m1_bars=", m1_bars);
   TerminalClose(0);
  }
//+------------------------------------------------------------------+

