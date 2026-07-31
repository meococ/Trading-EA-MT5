//+------------------------------------------------------------------+
//| EA_PTR_T2_DataEpochD0V3.mq5                                        |
//| T2/P4 D0 data-epoch synchronization probe.                       |
//| No trading, no file writes, no telemetry sidecars.                |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "T2 D0 data-quality synchronization probe; no trading"

input string          InpHypothesisId="";
input string          InpGenerationId="T2";
input string          InpEpochManifestSha256="F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648";
input ENUM_TIMEFRAMES InpExpectedTimeframe=PERIOD_M5;
input bool            InpCollectionOnly=true;

class CDataEpochProbe
  {
private:
   string   m_hypothesis_id;
   string   m_generation_id;
   string   m_epoch_manifest_sha256;
   ENUM_TIMEFRAMES m_expected_timeframe;
   datetime m_last_closed_bar_time;
   datetime m_first_closed_bar_time;
   long     m_closed_bar_count;

   bool IsHex64(const string value) const
     {
      if(StringLen(value)!=64)
         return false;
      for(int i=0; i<64; ++i)
        {
         ushort ch=StringGetCharacter(value,i);
         bool digit=(ch>='0' && ch<='9');
         bool upper=(ch>='A' && ch<='F');
         if(!digit && !upper)
            return false;
        }
      return true;
     }

   string FormatTimestamp(const datetime value) const
     {
      if(value<=0)
         return "NA";
      return TimeToString(value,TIME_DATE|TIME_MINUTES|TIME_SECONDS);
     }

   bool ReadSeriesInteger(
      const ENUM_TIMEFRAMES timeframe,
      const ENUM_SERIES_INFO_INTEGER property_id,
      const string field_name,
      long &value
   ) const
     {
      ResetLastError();
      if(!SeriesInfoInteger(_Symbol,timeframe,property_id,value))
        {
         PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=series_info_invalid symbol=%s field=%s timeframe=%d error=%d",
                     _Symbol,field_name,(int)timeframe,GetLastError());
         return false;
        }
      return true;
     }

public:
   CDataEpochProbe()
     {
      m_hypothesis_id="";
      m_generation_id="";
      m_epoch_manifest_sha256="";
      m_expected_timeframe=PERIOD_M5;
      m_last_closed_bar_time=0;
      m_first_closed_bar_time=0;
      m_closed_bar_count=0;
     }

   bool Configure(
      const string hypothesis_id,
      const string generation_id,
      const string epoch_manifest_sha256,
      const ENUM_TIMEFRAMES expected_timeframe
   )
     {
      m_hypothesis_id=hypothesis_id;
      m_generation_id=generation_id;
      m_epoch_manifest_sha256=epoch_manifest_sha256;
      m_expected_timeframe=expected_timeframe;

      if(!InpCollectionOnly)
        {
         Print("DATA_EPOCH_D0_INIT_FAIL reason=collection_only_disabled");
         return false;
        }
      if(StringLen(m_hypothesis_id)<=0)
        {
         Print("DATA_EPOCH_D0_INIT_FAIL reason=empty_hypothesis_id");
         return false;
        }
      if(m_generation_id!="T2")
        {
         PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=wrong_generation_id generation_id=%s",m_generation_id);
         return false;
        }
      if(m_epoch_manifest_sha256!="F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648" ||
         !IsHex64(m_epoch_manifest_sha256))
        {
         Print("DATA_EPOCH_D0_INIT_FAIL reason=epoch_manifest_sha_mismatch");
         return false;
        }
      if(_Period!=m_expected_timeframe || m_expected_timeframe!=PERIOD_M5)
        {
         PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=wrong_timeframe actual=%d expected=%d",
                     (int)_Period,(int)m_expected_timeframe);
         return false;
        }
      return true;
     }

   void MarkReady() const
     {
      PrintFormat("DATA_EPOCH_D0_READY hypothesis_id=%s generation_id=%s epoch_manifest_sha256=%s symbol=%s timeframe=M5 collection_only=true closed_bar_shift=1 no_outcome_metrics=true",
                  m_hypothesis_id,m_generation_id,m_epoch_manifest_sha256,_Symbol);
     }

   bool EmitSeriesProof() const
     {
      long m5_synchronized=0;
      long m5_first_epoch=0;
      long m5_terminal_first_epoch=0;
      long m1_server_first_epoch=0;
      long m1_terminal_first_epoch=0;
      long m5_bars=0;
      long terminal_maxbars=0;

      if(!ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED,"m5_synchronized",m5_synchronized) ||
         !ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,"m5_first_epoch",m5_first_epoch) ||
         !ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,"m5_terminal_first_epoch",m5_terminal_first_epoch) ||
         !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,"m1_server_first_epoch",m1_server_first_epoch) ||
         !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,"m1_terminal_first_epoch",m1_terminal_first_epoch) ||
         !ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT,"m5_bars",m5_bars))
         return false;

      ResetLastError();
      terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
      int terminal_error=GetLastError();
      if(terminal_maxbars<=0 || terminal_error!=0)
        {
         PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=terminal_maxbars_invalid symbol=%s terminal_maxbars=%I64d error=%d",
                     _Symbol,terminal_maxbars,terminal_error);
         return false;
        }

      datetime copytime_values[];
      ArraySetAsSeries(copytime_values,false);
      const datetime copytime_from=(datetime)m5_first_epoch;
      ResetLastError();
      int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);
      int copytime_error=GetLastError();
      long copytime_first_epoch=0;
      if(copytime_result==1)
         copytime_first_epoch=(long)copytime_values[0];

      PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
                  _Symbol,m5_synchronized,m5_first_epoch,m5_terminal_first_epoch,
                  m1_server_first_epoch,m1_terminal_first_epoch,m5_bars,terminal_maxbars,
                  (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);

      if(m5_synchronized!=1 || m5_first_epoch<=0 || m5_terminal_first_epoch<=0 ||
         m1_server_first_epoch<=0 || m1_terminal_first_epoch<=0 || m5_bars<=0 ||
         copytime_result!=1 || copytime_first_epoch!=m5_first_epoch || copytime_error!=0)
        {
         PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=series_proof_invalid symbol=%s m5_synchronized=%I64d copytime_result=%d copytime_last_error=%d",
                     _Symbol,m5_synchronized,copytime_result,copytime_error);
         return false;
        }
      return true;
     }

   void ObserveClosedBar()
     {
      datetime closed_bar_time=iTime(_Symbol,PERIOD_M5,1);
      if(closed_bar_time<=0 || closed_bar_time==m_last_closed_bar_time)
         return;

      m_last_closed_bar_time=closed_bar_time;
      if(m_first_closed_bar_time<=0)
        {
         m_first_closed_bar_time=closed_bar_time;
         PrintFormat("DATA_EPOCH_D0_FIRST_CLOSED_BAR symbol=%s closed_bar_shift=1 first_closed_bar_time=%s",
                     _Symbol,FormatTimestamp(m_first_closed_bar_time));
        }
      ++m_closed_bar_count;
     }

   void PrintSummary() const
     {
      PrintFormat("DATA_EPOCH_D0_SUMMARY hypothesis_id=%s generation_id=%s symbol=%s timeframe=M5 closed_bar_shift=1 closed_bar_count=%I64d first_closed_bar_time=%s last_closed_bar_time=%s no_trades=true no_outcome_metrics=true",
                  m_hypothesis_id,m_generation_id,_Symbol,m_closed_bar_count,
                  FormatTimestamp(m_first_closed_bar_time),FormatTimestamp(m_last_closed_bar_time));
     }
  };

CDataEpochProbe g_probe;

int OnInit()
  {
   if(!g_probe.Configure(InpHypothesisId,InpGenerationId,InpEpochManifestSha256,InpExpectedTimeframe))
      return INIT_FAILED;
   if(!g_probe.EmitSeriesProof())
      return INIT_FAILED;
   g_probe.MarkReady();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   g_probe.PrintSummary();
  }

void OnTick()
  {
   g_probe.ObserveClosedBar();
  }
