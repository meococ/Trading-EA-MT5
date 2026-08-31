//+------------------------------------------------------------------+
//| AlphaFactoryCustomRateImport.mq5                                 |
//| MTS005 H1 source-only importer. No orders, positions or PnL.     |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

const string PLAN_PATH    = "AlphaFactoryCustomRateImport\\active_plan.csv";
const string RECEIPT_PATH = "AlphaFactoryCustomRateImport\\active_receipt.csv";
const long   AFRATE_MAGIC = 0x4146524154453100;
const int    HEADER_BYTES = 16;
const int    RECORD_BYTES = 60;
const int    CONTROL_BARS_PER_H1 = 4;
const int    MAX_H1_PER_MONTH = 1000;

void Fail(const int receipt,const string code,const string detail)
  {
   if(receipt!=INVALID_HANDLE)
     {
      FileWrite(receipt,"FATAL",code,detail);
      FileFlush(receipt);
      FileClose(receipt);
     }
   Print("AlphaFactoryCustomRateImport FATAL ",code," ",detail);
   TerminalClose(1);
  }

bool ParseLongCell(const string text,long &value)
  {
   const int length=StringLen(text);
   if(length<1)
      return false;
   for(int index=0;index<length;index++)
     {
      const ushort ch=StringGetCharacter(text,index);
      if(ch<'0' || ch>'9')
         return false;
     }
   value=StringToInteger(text);
   return IntegerToString(value)==text;
  }

bool ParseDoubleCell(const string text,double &value)
  {
   value=StringToDouble(text);
   return StringLen(text)>0 && MathIsValidNumber(value);
  }

bool NearlyEqual(const double left,const double right,const double tolerance)
  {
   return MathAbs(left-right)<=tolerance;
  }

void SetFlatRate(MqlRates &rate,
                 const datetime epoch,
                 const double price,
                 const long tick_volume,
                 const int spread)
  {
   rate.time=epoch;
   rate.open=price;
   rate.high=price;
   rate.low=price;
   rate.close=price;
   rate.tick_volume=(tick_volume>0 ? tick_volume : 1);
   rate.spread=spread;
   rate.real_volume=0;
  }

bool AppendControlBars(MqlRates &target[],
                       const int offset,
                       const datetime hour,
                       const double open_price,
                       const double high_price,
                       const double low_price,
                       const double close_price,
                       const long tick_volume,
                       const int spread)
  {
   if(offset<0 || offset+3>=ArraySize(target) || hour<=0 || hour%3600!=0 ||
      open_price<=0.0 || high_price<MathMax(open_price,close_price) ||
      low_price>MathMin(open_price,close_price) || tick_volume<1 || spread<1)
      return false;
   const long quarter_volume=MathMax(1,tick_volume/4);
   SetFlatRate(target[offset],hour,open_price,quarter_volume,spread);
   if(close_price>=open_price)
     {
      SetFlatRate(target[offset+1],hour+1200,low_price,quarter_volume,spread);
      SetFlatRate(target[offset+2],hour+2400,high_price,quarter_volume,spread);
     }
   else
     {
      SetFlatRate(target[offset+1],hour+1200,high_price,quarter_volume,spread);
      SetFlatRate(target[offset+2],hour+2400,low_price,quarter_volume,spread);
     }
   SetFlatRate(target[offset+3],hour+3540,close_price,
               MathMax(1,tick_volume-3*quarter_volume),spread);
   return true;
  }

void OnStart()
  {
   int receipt=FileOpen(RECEIPT_PATH,FILE_WRITE|FILE_CSV|FILE_ANSI,';');
   if(receipt==INVALID_HANDLE)
     {
      Print("AlphaFactoryCustomRateImport cannot open receipt: ",GetLastError());
      TerminalClose(1);
      return;
     }
   FileWrite(receipt,"RECEIPT","alphafactory_custom_rate_import_receipt.v1",
             "SOURCE_DATA_ONLY_NO_PERFORMANCE");

   int plan=FileOpen(PLAN_PATH,FILE_READ|FILE_CSV|FILE_ANSI,';');
   if(plan==INVALID_HANDLE)
     {
      Fail(receipt,"PLAN_OPEN_FAILED",IntegerToString(GetLastError()));
      return;
     }
   string tag=FileReadString(plan);
   string schema=FileReadString(plan);
   string custom_symbol=FileReadString(plan);
   string origin_symbol=FileReadString(plan);
   string digits_text=FileReadString(plan);
   string point_text=FileReadString(plan);
   string source_contract_sha256=FileReadString(plan);
   string range_manifest_sha256=FileReadString(plan);
   string import_plan_sha256=FileReadString(plan);
   string expected_months_text=FileReadString(plan);
   string range_from_text=FileReadString(plan);
   string range_to_text=FileReadString(plan);
   string expected_h1_text=FileReadString(plan);
   string expected_m1_text=FileReadString(plan);
   string expected_first_text=FileReadString(plan);
    string expected_last_text=FileReadString(plan);
    string rate_mode=FileReadString(plan);
    const bool reuse_verify=(rate_mode=="REUSE_VERIFY");
    const bool replace_rates=(rate_mode=="REPLACE");

   long digits_value=0,expected_months_value=0,range_from=0,range_to=0;
   long expected_h1=0,expected_m1=0,expected_first=0,expected_last=0;
   double point=0.0;
   const bool numeric_ok=
      ParseLongCell(digits_text,digits_value) && ParseDoubleCell(point_text,point) &&
      ParseLongCell(expected_months_text,expected_months_value) &&
      ParseLongCell(range_from_text,range_from) && ParseLongCell(range_to_text,range_to) &&
      ParseLongCell(expected_h1_text,expected_h1) && ParseLongCell(expected_m1_text,expected_m1) &&
      ParseLongCell(expected_first_text,expected_first) && ParseLongCell(expected_last_text,expected_last);
   const int digits=(int)digits_value;
   const int expected_months=(int)expected_months_value;
   if(tag!="META" || schema!="alphafactory_custom_rate_import_plan.v1" || !numeric_ok ||
      custom_symbol=="" || origin_symbol=="" || digits<0 || digits>12 || point<=0.0 ||
      expected_months<1 || range_from<=0 || range_to<range_from || expected_h1<1 ||
      expected_m1!=expected_h1*CONTROL_BARS_PER_H1 || expected_first<=0 ||
       expected_last<expected_first || (!reuse_verify && !replace_rates) ||
       StringLen(source_contract_sha256)!=64 ||
      StringLen(range_manifest_sha256)!=64 || StringLen(import_plan_sha256)!=64)
     {
      FileClose(plan);
      Fail(receipt,"META_CONTRACT_INVALID","plan header failed validation");
      return;
     }

   const string expected_description=
      "AlphaFactory Jetta "+StringSubstr(source_contract_sha256,0,16)+
      " plan "+StringSubstr(import_plan_sha256,0,16);
   bool is_custom=false;
   const bool symbol_exists=SymbolExist(custom_symbol,is_custom);
    if(!symbol_exists && reuse_verify)
      {
       FileClose(plan);
       Fail(receipt,"REUSE_SYMBOL_MISSING",custom_symbol);
       return;
      }
    if(!symbol_exists)
     {
      if(!CustomSymbolCreate(custom_symbol,"AlphaFactory\\DukascopyJetta",origin_symbol))
        {
         FileClose(plan);
         Fail(receipt,"CUSTOM_SYMBOL_CREATE_FAILED",IntegerToString(GetLastError()));
         return;
        }
     }
   else if(!is_custom)
     {
      FileClose(plan);
      Fail(receipt,"SYMBOL_EXISTS_NOT_CUSTOM",custom_symbol);
      return;
     }
    else if(!reuse_verify && SymbolInfoString(custom_symbol,SYMBOL_DESCRIPTION)!=expected_description)
     {
      FileClose(plan);
      Fail(receipt,"SYMBOL_PLAN_IDENTITY_MISMATCH",custom_symbol);
      return;
     }

    SymbolSelect(custom_symbol,false);
    if(!reuse_verify &&
       (!CustomSymbolSetInteger(custom_symbol,SYMBOL_DIGITS,digits) ||
        !CustomSymbolSetInteger(custom_symbol,SYMBOL_CHART_MODE,SYMBOL_CHART_MODE_BID) ||
        !CustomSymbolSetDouble(custom_symbol,SYMBOL_POINT,point) ||
        !CustomSymbolSetDouble(custom_symbol,SYMBOL_TRADE_TICK_SIZE,point) ||
        !CustomSymbolSetString(custom_symbol,SYMBOL_DESCRIPTION,expected_description)))
     {
      FileClose(plan);
      Fail(receipt,"CUSTOM_SYMBOL_PROPERTY_SET_FAILED",IntegerToString(GetLastError()));
      return;
     }
    const string origin_currency_base=SymbolInfoString(origin_symbol,SYMBOL_CURRENCY_BASE);
    const string origin_currency_profit=SymbolInfoString(origin_symbol,SYMBOL_CURRENCY_PROFIT);
    const string origin_currency_margin=SymbolInfoString(origin_symbol,SYMBOL_CURRENCY_MARGIN);
    const long origin_calc_mode=SymbolInfoInteger(origin_symbol,SYMBOL_TRADE_CALC_MODE);
    const double origin_contract_size=SymbolInfoDouble(origin_symbol,SYMBOL_TRADE_CONTRACT_SIZE);
    if(origin_currency_base=="" || origin_currency_profit=="" ||
       origin_currency_margin=="" || origin_contract_size<=0.0 ||
       !CustomSymbolSetString(custom_symbol,SYMBOL_CURRENCY_BASE,origin_currency_base) ||
       !CustomSymbolSetString(custom_symbol,SYMBOL_CURRENCY_PROFIT,origin_currency_profit) ||
       !CustomSymbolSetString(custom_symbol,SYMBOL_CURRENCY_MARGIN,origin_currency_margin))
      {
       FileClose(plan);
       Fail(receipt,"CUSTOM_SYMBOL_CURRENCY_BIND_FAILED",IntegerToString(GetLastError()));
       return;
      }
    const int deleted=(reuse_verify ? 0 :
                       CustomRatesDelete(custom_symbol,(datetime)range_from,(datetime)range_to));
    if(deleted<0 || !SymbolSelect(custom_symbol,true))
     {
      FileClose(plan);
      Fail(receipt,"CUSTOM_SYMBOL_PREP_FAILED",IntegerToString(GetLastError()));
      return;
     }
    const string custom_currency_base=SymbolInfoString(custom_symbol,SYMBOL_CURRENCY_BASE);
    const string custom_currency_profit=SymbolInfoString(custom_symbol,SYMBOL_CURRENCY_PROFIT);
    const string custom_currency_margin=SymbolInfoString(custom_symbol,SYMBOL_CURRENCY_MARGIN);
    const long custom_calc_mode=SymbolInfoInteger(custom_symbol,SYMBOL_TRADE_CALC_MODE);
    const double custom_contract_size=SymbolInfoDouble(custom_symbol,SYMBOL_TRADE_CONTRACT_SIZE);
    if(custom_currency_base!=origin_currency_base ||
       custom_currency_profit!=origin_currency_profit ||
       custom_currency_margin!=origin_currency_margin ||
       custom_calc_mode!=origin_calc_mode ||
       MathAbs(custom_contract_size-origin_contract_size)>1e-9)
      {
       FileClose(plan);
       Fail(receipt,"CUSTOM_SYMBOL_TRADE_SPEC_MISMATCH",custom_symbol);
       return;
      }
    FileWrite(receipt,"META","PASS",custom_symbol,origin_symbol,digits,
             DoubleToString(point,digits),source_contract_sha256,range_manifest_sha256,
              import_plan_sha256,expected_months,range_from,range_to,expected_h1,
              expected_m1,expected_first,expected_last,rate_mode);
    FileWrite(receipt,"SPEC","PASS",custom_symbol,origin_symbol,
              custom_currency_base,custom_currency_profit,custom_currency_margin,
              custom_calc_mode,DoubleToString(custom_contract_size,8));

   int imported_months=0;
   long imported_h1=0;
   long imported_m1=0;
   while(!FileIsEnding(plan))
     {
      tag=FileReadString(plan);
      if(tag=="END")
         break;
      if(tag!="MONTH")
        {
         FileClose(plan);
         Fail(receipt,"MONTH_TAG_INVALID",tag);
         return;
        }
      string year_month=FileReadString(plan);
      string relative_path=FileReadString(plan);
      string expected_sha256=FileReadString(plan);
      string count_text=FileReadString(plan);
      string first_text=FileReadString(plan);
      string last_text=FileReadString(plan);
      long h1_count=0,first_epoch=0,last_epoch=0;
      if(year_month=="" || StringFind(relative_path,"AlphaFactoryCustomRateImport\\")!=0 ||
         StringFind(relative_path,"..")>=0 || StringFind(relative_path,":")>=0 ||
         StringLen(expected_sha256)!=64 || !ParseLongCell(count_text,h1_count) ||
         !ParseLongCell(first_text,first_epoch) || !ParseLongCell(last_text,last_epoch) ||
         h1_count<1 || h1_count>MAX_H1_PER_MONTH || first_epoch<=0 || last_epoch<first_epoch)
        {
         FileClose(plan);
         Fail(receipt,"MONTH_CONTRACT_INVALID",year_month);
         return;
        }
      int source=FileOpen(relative_path,FILE_READ|FILE_BIN);
      if(source==INVALID_HANDLE)
        {
         FileClose(plan);
         Fail(receipt,"BINARY_OPEN_FAILED",relative_path);
         return;
        }
      const long expected_size=HEADER_BYTES+h1_count*RECORD_BYTES;
      const long actual_size=FileGetInteger(source,FILE_SIZE);
      const long magic=FileReadLong(source);
      const long header_count=FileReadLong(source);
      if(actual_size!=expected_size || magic!=AFRATE_MAGIC || header_count!=h1_count)
        {
         FileClose(source);
         FileClose(plan);
         Fail(receipt,"BINARY_HEADER_OR_SIZE_MISMATCH",year_month);
         return;
        }

      MqlRates h1[];
      MqlRates m1[];
      if(ArrayResize(h1,(int)h1_count)!=(int)h1_count ||
         ArrayResize(m1,(int)(h1_count*CONTROL_BARS_PER_H1))!=(int)(h1_count*CONTROL_BARS_PER_H1))
        {
         FileClose(source);
         FileClose(plan);
         Fail(receipt,"RATE_ARRAY_ALLOCATION_FAILED",year_month);
         return;
        }
      long previous=0;
      for(int index=0;index<(int)h1_count;index++)
        {
         const long epoch=FileReadLong(source);
         const double open_price=FileReadDouble(source);
         const double high_price=FileReadDouble(source);
         const double low_price=FileReadDouble(source);
         const double close_price=FileReadDouble(source);
         const long tick_volume=FileReadLong(source);
         const int spread=FileReadInteger(source);
         const long real_volume=FileReadLong(source);
         if(epoch<=previous || epoch%3600!=0 || open_price<=0.0 ||
            high_price<MathMax(open_price,close_price) ||
            low_price>MathMin(open_price,close_price) || tick_volume<1 || spread<1 ||
            real_volume<0 ||
            !AppendControlBars(m1,index*CONTROL_BARS_PER_H1,(datetime)epoch,
                               open_price,high_price,low_price,close_price,tick_volume,spread))
           {
            FileClose(source);
            FileClose(plan);
            Fail(receipt,"RATE_RECORD_INVALID",year_month);
            return;
           }
         h1[index].time=(datetime)epoch;
         h1[index].open=open_price;
         h1[index].high=high_price;
         h1[index].low=low_price;
         h1[index].close=close_price;
         h1[index].tick_volume=tick_volume;
         h1[index].spread=spread;
         h1[index].real_volume=real_volume;
         previous=epoch;
        }
      FileClose(source);
      if(h1[0].time!=(datetime)first_epoch || h1[(int)h1_count-1].time!=(datetime)last_epoch)
        {
         FileClose(plan);
         Fail(receipt,"RATE_BOUNDARY_MISMATCH",year_month);
         return;
        }
       const int replaced=(reuse_verify ? ArraySize(m1) :
                          CustomRatesReplace(custom_symbol,m1[0].time,
                                             m1[ArraySize(m1)-1].time,m1));
       if(replaced!=ArraySize(m1))
        {
         FileClose(plan);
         Fail(receipt,"CUSTOM_RATES_REPLACE_MISMATCH",year_month);
         return;
        }

      MqlRates verify[];
      int copied=-1;
      for(int wait=0;wait<600;wait++)
        {
         copied=CopyRates(custom_symbol,PERIOD_H1,h1[0].time,
                          h1[(int)h1_count-1].time,verify);
         if(copied==(int)h1_count)
            break;
         Sleep(100);
        }
       bool mismatch=(copied!=(int)h1_count);
      if(!mismatch)
        {
         for(int index=0;index<copied;index++)
           {
            if(verify[index].time!=h1[index].time ||
               !NearlyEqual(verify[index].open,h1[index].open,point/1000.0) ||
               !NearlyEqual(verify[index].high,h1[index].high,point/1000.0) ||
               !NearlyEqual(verify[index].low,h1[index].low,point/1000.0) ||
               !NearlyEqual(verify[index].close,h1[index].close,point/1000.0) ||
               verify[index].spread!=h1[index].spread)
              {
               mismatch=true;
               break;
              }
           }
        }
      if(!mismatch && reuse_verify)
        {
         MqlRates verify_m1[];
         const int copied_m1=CopyRates(custom_symbol,PERIOD_M1,m1[0].time,
                                       m1[ArraySize(m1)-1].time,verify_m1);
         mismatch=(copied_m1!=ArraySize(m1));
         if(!mismatch)
           {
            for(int index=0;index<copied_m1;index++)
              {
               if(verify_m1[index].time!=m1[index].time ||
                  !NearlyEqual(verify_m1[index].open,m1[index].open,point/1000.0) ||
                  !NearlyEqual(verify_m1[index].high,m1[index].high,point/1000.0) ||
                  !NearlyEqual(verify_m1[index].low,m1[index].low,point/1000.0) ||
                  !NearlyEqual(verify_m1[index].close,m1[index].close,point/1000.0) ||
                  verify_m1[index].spread!=m1[index].spread)
                 {
                  mismatch=true;
                  break;
                 }
              }
           }
         ArrayFree(verify_m1);
        }
      if(mismatch)
        {
         FileClose(plan);
         Fail(receipt,"H1_READBACK_MISMATCH",year_month);
         return;
        }
      FileWrite(receipt,"MONTH",year_month,"PASS",h1_count,ArraySize(m1),
                first_epoch,last_epoch,expected_sha256,rate_mode);
      FileFlush(receipt);
      imported_months++;
      imported_h1+=h1_count;
      imported_m1+=ArraySize(m1);
      ArrayFree(h1);
      ArrayFree(m1);
      ArrayFree(verify);
     }
   FileClose(plan);

   if(imported_months!=expected_months || imported_h1!=expected_h1 ||
      imported_m1!=expected_m1)
     {
      Fail(receipt,"IMPORT_TOTAL_MISMATCH",
           StringFormat("months=%d/%d h1=%I64d/%I64d m1=%I64d/%I64d",
                        imported_months,expected_months,imported_h1,expected_h1,
                        imported_m1,expected_m1));
      return;
     }
   long h1_bars=0,m1_bars=0,d1_bars=0,h1_first=0;
   bool h1_sync=false,m1_sync=false,d1_sync=false;
   for(int wait=0;wait<600;wait++)
     {
      h1_bars=Bars(custom_symbol,PERIOD_H1,(datetime)range_from,(datetime)range_to);
      m1_bars=Bars(custom_symbol,PERIOD_M1,(datetime)range_from,(datetime)range_to);
      d1_bars=Bars(custom_symbol,PERIOD_D1,(datetime)range_from,(datetime)range_to);
      h1_sync=(bool)SeriesInfoInteger(custom_symbol,PERIOD_H1,SERIES_SYNCHRONIZED);
      m1_sync=(bool)SeriesInfoInteger(custom_symbol,PERIOD_M1,SERIES_SYNCHRONIZED);
      d1_sync=(bool)SeriesInfoInteger(custom_symbol,PERIOD_D1,SERIES_SYNCHRONIZED);
      h1_first=SeriesInfoInteger(custom_symbol,PERIOD_H1,SERIES_FIRSTDATE);
      if(h1_sync && m1_sync && d1_sync && h1_bars==expected_h1 &&
         m1_bars==expected_m1 && d1_bars>0 && h1_first==expected_first)
         break;
      Sleep(100);
     }
    if(!h1_sync || !m1_sync || !d1_sync || h1_bars!=expected_h1 ||
      m1_bars!=expected_m1 || d1_bars<=0 || h1_first!=expected_first)
     {
      Fail(receipt,"FINAL_SERIES_READBACK_MISMATCH",
           StringFormat("h1=%I64d/%I64d m1=%I64d/%I64d d1=%I64d first=%I64d/%I64d",
                        h1_bars,expected_h1,m1_bars,expected_m1,d1_bars,h1_first,expected_first));
      return;
     }
   if(reuse_verify &&
      !CustomSymbolSetString(custom_symbol,SYMBOL_DESCRIPTION,expected_description))
     {
      Fail(receipt,"REUSE_DESCRIPTION_REBIND_FAILED",IntegerToString(GetLastError()));
      return;
     }
   FileWrite(receipt,"SUMMARY","PASS",custom_symbol,imported_months,imported_h1,
             imported_m1,d1_bars,h1_first,source_contract_sha256,
             range_manifest_sha256,import_plan_sha256);
   FileFlush(receipt);
   FileClose(receipt);
   Print("AlphaFactoryCustomRateImport PASS symbol=",custom_symbol,
         " months=",imported_months," h1=",imported_h1," m1=",imported_m1,
         " d1=",d1_bars);
   TerminalClose(0);
  }
//+------------------------------------------------------------------+
