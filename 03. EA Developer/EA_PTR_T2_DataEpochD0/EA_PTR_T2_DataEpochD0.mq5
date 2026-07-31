//+------------------------------------------------------------------+
//| EA_PTR_T2_DataEpochD0.mq5                                        |
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
