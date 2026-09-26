//+------------------------------------------------------------------+
//|                                                     VPA_Core.mqh |
//|  T-VPA-VIS-1 - DR3 detector engine, ported line by line from the  |
//|  frozen Python code path:                                         |
//|    research/lab/vpa_core.py   (Detector engine)                   |
//|    research/lab/vpa_dr1.py    (Dr1Detector, DR3_CFG, gates)       |
//|    research/lab/vpa_data.py   (server->UTC conversion, modulo fix)|
//|  VISUAL / FORENSIC ONLY. No order, position or trade call exists  |
//|  anywhere in this header.                                         |
//|  Python line references in comments point at those files.         |
//+------------------------------------------------------------------+
#define VPA_NGATES        11
#define VPA_MAX_TOUCHES   32
#define VPA_MAX_PIVOTS    400

//--- DR1_DEFAULTS (vpa_dr1.py:29-93) merged with DR3_CFG (vpa_dr1.py:95-107)
#define VPA_PIVOT_LAG              2
#define VPA_PIVOT_SIG_LAG          5
#define VPA_BARRIER_SCAN          17
#define VPA_BARRIER_T_MIN          2
#define VPA_BARRIER_EXPIRY        20
#define VPA_BARRIER_EPS_ATR        0.10
#define VPA_BARRIER_BREAK_ATR      0.05
#define VPA_DEDUPE_ATR             0.10
#define VPA_PRESSURE_WINDOW        6
#define VPA_DISP_MIN               0.60
#define VPA_ER_MIN                 0.55
#define VPA_CLV_MIN                0.20
#define VPA_PRESSURE_SLOPE_MIN     0.10
#define VPA_PRESSURE_DUR_MIN       2
#define VPA_BIAS_SLOPE_LOOKBACK    6
#define VPA_BIAS_SLOPE_MIN         0.10
#define VPA_BIAS_SIDE_MIN         -0.20
#define VPA_WARMUP_BARS           50
#define VPA_SIGNAL_ATR             0.50
#define VPA_SIGNAL_MAX_ATR         0.25
#define VPA_DOJI_BODY_FRAC         0.10
#define VPA_THETA_SLOPE            0.10
#define VPA_FRAC_SIDE_MIN          0.60
#define VPA_FRAC_LOOKBACK         10
#define VPA_SLOPE_LOOKBACK         6
#define VPA_BUILDUP_MAX           10
#define VPA_BUILDUP_MIN            3
#define VPA_BAND_LO_ATR           -0.10
#define VPA_BAND_HI_ATR            0.50
#define VPA_MIN_BAND_CLOSES        2
#define VPA_BUILDUP_TOUCH_ATR      0.10
#define VPA_MIN_TOUCHES            1
#define VPA_OVERLAP_MIN            0.45
#define VPA_CONTRACTION_MAX        0.85
#define VPA_BUILDUP_MIN_CONDITIONS 4
#define VPA_CHOP_LOOKBACK          4
#define VPA_CHOP_OVERLAP_MIN       0.65
#define VPA_CHOP_PROG_MAX         (1.0/3.0)
#define VPA_CHOP_BODY_MAX          0.35
#define VPA_CHOP_LONG_ATR          1.5
#define VPA_ROOM_R_MIN             2.0
#define VPA_ADVERSE_PIVOT_R        0.5
#define VPA_ADVERSE_SKIP_FRAC      0.10
#define VPA_INTEGRITY_EPS_ATR      0.10
#define VPA_ROOM_ZONE_R            0.5
#define VPA_ANTI_ENTRY_B_ATR       0.35
#define VPA_ANTI_SIGNAL_RANGE_ATR  1.5
#define VPA_ANTI_EMA_ATR           1.5
#define VPA_SQUEEZE_EMA_ATR        0.6
#define VPA_SQUEEZE_MIN_BARS       2
#define VPA_COMBI_BODY_ATR         0.35
#define VPA_COMBI_CLV              0.50
#define VPA_COMBI_INSIDE_RATIO     0.75
#define VPA_STOP_PIPS              8.0
#define VPA_TARGET_R               2.0
#define VPA_ENTRY_BUFFER_PIPS      1.0
#define VPA_ORDER_VALID_BARS       3
#define VPA_COST_PIPS              1.0
#define VPA_RHO_MAX                0.20
#define VPA_ROUND_GRID_PIPS       50.0
#define VPA_EU_LO                 300
#define VPA_EU_HI                 660
#define VPA_US_LO                 690
#define VPA_US_HI                1050
#define VPA_LUNCH_1_LO            660
#define VPA_LUNCH_1_HI            780
#define VPA_LUNCH_2_LO           1020
#define VPA_LUNCH_2_HI           1140
#define VPA_NO_PRESSURE      (-1000000000)
#define VPA_INF             1.7e308

//--- barrier end kinds
#define VPA_END_ACTIVE     0
#define VPA_END_EXPIRED    1
#define VPA_END_MISSED     2
#define VPA_END_EXEC       3

//--- bar dict = vpa_data.load_m5_bars return value
struct VpaBar
  {
   long              t;        // bar OPEN time, server clock, unix seconds
   double            o;
   double            h;
   double            l;
   double            c;
   int               utc_min;  // UTC minute of the bar CLOSE, modulo fix applied
   int               srv_min;  // server minute of the bar CLOSE
  };

struct VpaPivot
  {
   int               idx;
   double            px;
   int               kind;     // +1 pivot high, -1 pivot low
  };

struct VpaBarrier
  {
   int               id;
   int               side;
   double            level;    // B = median of the touch prices
   int               lock_idx;
   int               exp_idx;
   int               touches[VPA_MAX_TOUCHES];
   int               n_touches;
   double            atr_lock;
   int               end_idx;  // -1 while active
   int               end_kind; // VPA_END_*
   bool              integrity_fail;
  };

struct Buildup
  {
   bool              has;
   int               n;
   int               start;
   double            contraction;
   double            overlap;
   int               band_closes;
   int               touches;
   int               conditions_passed;
   bool              squeeze;
   bool              v2ok;
   int               v2of4_n;
   bool              vtok;
   int               vtight_n;
  };

struct VpaEvent
  {
   int               id;
   int               bar_idx;   // signal bar  (vpa_dr1.py:418)
   int               trig_idx;  // trigger bar (vpa_dr1.py:418)
   int               side;
   double            level;
   int               lock_idx;
   int               n_touches;
   bool              executable;
   int               first_fail;      // gate index, -1 = accepted
   bool              gate_pass[VPA_NGATES];
   bool              gate_eval[VPA_NGATES];
   string            session;
   string            setup;
   bool              has_entry;
   double            entry;
   double            invalidation;
   double            atr;
   bool              atr_ok;
   double            ema;
   bool              ema_ok;
   bool              has_room;
   double            room_r;
   bool              room_inf;
   bool              has_obstacle;
   double            obstacle_price;
   string            obstacle_type;
   bool              ema_dist_ok;
   double            ema_dist_atr;
   double            entry_b_atr;
   double            range_atr;
   bool              squeeze;
   bool              lunch;
   bool              chop;
   bool              chop_exempt;
   int               chop_window;     // -1 n/a, 0 no, 1 yes
   int               buildup_n;
   int               buildup_start;
   int               band_closes;
   int               bu_touches;
   double            overlap;
   double            contraction;
   bool              has_buildup;
   double            trend_slope;
   double            frac_side;
   double            signal_body_frac;
   bool              trend_ok;
   bool              doji;
   int               bias;
   bool              pressure;
   long              bars_since_pressure;
   double            rho;
   bool              has_rho;
  };

//+------------------------------------------------------------------+
//| gate tables - vpa_dr1.py:111-149                                 |
//+------------------------------------------------------------------+
string VpaGateKey(const int i)
  {
   string k[VPA_NGATES]={"warmup","session","direction","trend","integrity","chop",
                         "buildup","room","adverse","anti_chase","cost"};
   return(k[i]);
  }

string VpaGateReason(const int i)
  {
   string r[VPA_NGATES]={"skip_warmup","skip_session","skip_direction","skip_trend",
                         "skip_integrity","skip_chop","skip_no_buildup","skip_room",
                         "skip_adverse_magnet","skip_anti_chase","skip_cost"};
   return(r[i]);
  }

//--- DR3_HARD_GATES (vpa_dr1.py:27): warmup, session, direction, trend, integrity, cost
bool VpaGateHard(const int i)
  {
   return(i==0 || i==1 || i==2 || i==3 || i==4 || i==10);
  }

//+------------------------------------------------------------------+
//| helpers                                                          |
//+------------------------------------------------------------------+
double VpaMedian(const double &src[],const int n)
  {
   if(n<=0)
      return(0.0);
   double tmp[];
   ArrayResize(tmp,n);
   for(int i=0;i<n;i++)
      tmp[i]=src[i];
   ArraySort(tmp);
   if((n%2)==1)
      return(tmp[n/2]);
   return((tmp[n/2-1]+tmp[n/2])/2.0);
  }

double VpaMedianSlice(const double &src[],const int from,const int to)
  {
   int n=to-from;
   if(n<=0)
      return(0.0);
   double tmp[];
   ArrayResize(tmp,n);
   for(int i=0;i<n;i++)
      tmp[i]=src[from+i];
   ArraySort(tmp);
   if((n%2)==1)
      return(tmp[n/2]);
   return((tmp[n/2-1]+tmp[n/2])/2.0);
  }

int VpaLastSundayOfMonth(const int year,const int month)
  {
   MqlDateTime dt;
   TimeToStruct(StringToTime(StringFormat("%04d.%02d.31",year,month)),dt);
   return(31-dt.day_of_week);
  }

//--- vpa_data.py:55-60 with the TIME_SANITY modulo fix, offset rule from
//--- vpa_random_baseline.eu_server_offset_hours (server = UTC+2 winter, +3 summer)
void VpaUtcMinute(const datetime close_time,int &utc_min,int &srv_min)
  {
   MqlDateTime dt;
   TimeToStruct(close_time,dt);
   srv_min=dt.hour*60+dt.min;
   datetime mar=(datetime)StringToTime(StringFormat("%04d.03.%02d 01:00",dt.year,
                                                    VpaLastSundayOfMonth(dt.year,3)));
   datetime oct=(datetime)StringToTime(StringFormat("%04d.10.%02d 01:00",dt.year,
                                                    VpaLastSundayOfMonth(dt.year,10)));
   int off=(close_time>=mar && close_time<oct) ? 3 : 2;
   int m=srv_min-off*60;
   m=((m%1440)+1440)%1440;
   utc_min=m;
  }

//+------------------------------------------------------------------+
//| CVpaDr3 - the ported detector                                    |
//+------------------------------------------------------------------+
class CVpaDr3
  {
public:
   VpaBar            m_b[];
   int               m_n;
   double            m_pip;
   double            m_tick;
   double            m_round_grid;
   //--- indicator state (vpa_core.py:98-112)
   double            m_tr[];
   double            m_atr[];
   double            m_ema[];
   double            m_clv[];
   bool              m_atr_ok[];
   bool              m_ema_ok[];
   bool              m_pressure[];
   int               m_pdir[];
   int               m_pdur[];
   int               m_bias[];
   long              m_last_pressure_end;
   //--- pivots / barriers
   VpaPivot          m_pivots[];
   VpaPivot          m_pivots_sig[];
   VpaBarrier        m_barriers[];
   int               m_n_barriers;
   int               m_active[];
   int               m_n_active;
   //--- day high/low (vpa_dr1.py:210-225)
   long              m_cur_day;
   bool              m_has_day;
   double            m_cur_day_high;
   double            m_cur_day_low;
   double            m_pdh;
   double            m_pdl;
   bool              m_pd_ok;
   //--- output
   VpaEvent          m_events[];
   int               m_n_events;
   string            m_cnt_key[];
   int               m_cnt_val[];
   string            m_error;

                     CVpaDr3(void)
     {
      m_n=0;
      m_n_barriers=0;
      m_n_active=0;
      m_n_events=0;
      m_last_pressure_end=VPA_NO_PRESSURE;
      m_has_day=false;
      m_cur_day=0;
      m_cur_day_high=0.0;
      m_cur_day_low=0.0;
      m_pdh=0.0;
      m_pdl=0.0;
      m_pd_ok=false;
      m_pip=0.0001;
      m_tick=0.00001;
      m_round_grid=VPA_ROUND_GRID_PIPS*m_pip;
      m_error="";
     }

   bool Init(const VpaBar &bars[],const int n,const double pip,const double tick)
     {
      if(n<2)
        {
         m_error="need at least 2 bars";
         return(false);
        }
      m_pip=pip;
      m_tick=tick;
      m_round_grid=VPA_ROUND_GRID_PIPS*m_pip;
      m_n=n;
      ArrayResize(m_b,n);
      for(int i=0;i<n;i++)
         m_b[i]=bars[i];
      ArrayResize(m_tr,n);       ArrayInitialize(m_tr,0.0);
      ArrayResize(m_atr,n);      ArrayInitialize(m_atr,0.0);
      ArrayResize(m_ema,n);      ArrayInitialize(m_ema,0.0);
      ArrayResize(m_clv,n);      ArrayInitialize(m_clv,0.0);
      ArrayResize(m_atr_ok,n);
      for(int i=0;i<n;i++) m_atr_ok[i]=false;
      ArrayResize(m_ema_ok,n);
      for(int i=0;i<n;i++) m_ema_ok[i]=false;
      ArrayResize(m_pressure,n);
      for(int i=0;i<n;i++) m_pressure[i]=false;
      ArrayResize(m_pdir,n);     ArrayInitialize(m_pdir,0);
      ArrayResize(m_pdur,n);     ArrayInitialize(m_pdur,0);
      ArrayResize(m_bias,n);     ArrayInitialize(m_bias,0);
      ArrayResize(m_pivots,0);
      ArrayResize(m_pivots_sig,0);
      ArrayResize(m_barriers,0);
      ArrayResize(m_active,0);
      ArrayResize(m_events,0);
      ArrayResize(m_cnt_key,0);
      ArrayResize(m_cnt_val,0);
      return(true);
     }

   //--- counters (_cnt / _cnt)
   void Cnt(const string key)
     {
      for(int i=0;i<ArraySize(m_cnt_key);i++)
         if(m_cnt_key[i]==key)
           {
            m_cnt_val[i]++;
            return;
           }
      int k=ArraySize(m_cnt_key);
      ArrayResize(m_cnt_key,k+1);
      ArrayResize(m_cnt_val,k+1);
      m_cnt_key[k]=key;
      m_cnt_val[k]=1;
     }

   int CntGet(const string key)
     {
      for(int i=0;i<ArraySize(m_cnt_key);i++)
         if(m_cnt_key[i]==key)
            return(m_cnt_val[i]);
      return(0);
     }

   //--- main loop (vpa_dr1.py:242-250)
   void Run(void)
     {
      for(int t=0;t<m_n;t++)
        {
         UpdateBar(t);
         if(t>14)
           {
            ConfirmPivots(t);
            BarrierUpdate(t);
           }
         Dr1Eval(t);
        }
     }

   //--- vpa_core.py:118-162
   void UpdateBar(const int t)
     {
      double h=m_b[t].h;
      double l=m_b[t].l;
      double c=m_b[t].c;
      double tr=h-l;
      if(t>0)
         tr=MathMax(tr,MathMax(MathAbs(h-m_b[t-1].c),MathAbs(l-m_b[t-1].c)));
      m_tr[t]=tr;
      if(t==13)
        {
         double s=0.0;
         for(int i=0;i<14;i++)
            s+=m_tr[i];
         m_atr[t]=s/14.0;
         m_atr_ok[t]=true;
        }
      else
         if(t>13)
           {
            m_atr[t]=(13.0*m_atr[t-1]+tr)/14.0;
            m_atr_ok[t]=true;
           }
      if(t==24)
        {
         double s=0.0;
         for(int i=0;i<25;i++)
            s+=m_b[i].c;
         m_ema[t]=s/25.0;
         m_ema_ok[t]=true;
        }
      else
         if(t>24)
           {
            m_ema[t]=(2.0/26.0)*c+(24.0/26.0)*m_ema[t-1];
            m_ema_ok[t]=true;
           }
      double rng=h-l;
      m_clv[t]=(rng>0.0) ? (2.0*c-h-l)/rng : 0.0;
      //--- day high/low (vpa_dr1.py:210-225)
      long day=m_b[t].t/86400;
      if(!m_has_day || day!=m_cur_day)
        {
         if(m_has_day)
           {
            m_pdh=m_cur_day_high;
            m_pdl=m_cur_day_low;
            m_pd_ok=true;
           }
         m_cur_day=day;
         m_cur_day_high=h;
         m_cur_day_low=l;
         m_has_day=true;
        }
      else
        {
         if(h>m_cur_day_high)
            m_cur_day_high=h;
         if(l<m_cur_day_low)
            m_cur_day_low=l;
        }
      //--- pressure (vpa_core.py:136-151)
      if(t>=5 && m_atr_ok[t] && m_atr[t]>0.0)
        {
         if(PressureComponents(t,+1))
            m_pdir[t]=1;
         else
            if(PressureComponents(t,-1))
               m_pdir[t]=-1;
         if(m_pdir[t]!=0)
           {
            m_pressure[t]=true;
            if(m_pdir[t-1]==m_pdir[t])
               m_pdur[t]=m_pdur[t-1]+1;
            else
               m_pdur[t]=1;
            m_last_pressure_end=t;
           }
        }
      //--- bias (vpa_core.py:152-162)
      m_bias[t]=0;
      if(t>=VPA_BIAS_SLOPE_LOOKBACK && m_atr_ok[t] && m_atr[t]>0.0
         && m_ema_ok[t] && m_ema_ok[t-VPA_BIAS_SLOPE_LOOKBACK])
        {
         double slope=(m_ema[t]-m_ema[t-VPA_BIAS_SLOPE_LOOKBACK])/m_atr[t];
         double side=(c-m_ema[t])/m_atr[t];
         if(slope>=VPA_BIAS_SLOPE_MIN && side>=VPA_BIAS_SIDE_MIN)
            m_bias[t]=1;
         else
            if(slope<=-VPA_BIAS_SLOPE_MIN && side<=-VPA_BIAS_SIDE_MIN)
               m_bias[t]=-1;
        }
     }

   //--- vpa_core.py:164-179
   bool PressureComponents(const int u,const int d)
     {
      if(u<VPA_PRESSURE_WINDOW || !m_atr_ok[u] || m_atr[u]<=0.0)
         return(false);
      double c_u=m_b[u].c;
      double c_ref=m_b[u-VPA_PRESSURE_WINDOW+1].c;
      double disp=d*(c_u-c_ref)/m_atr[u];
      double den=0.0;
      for(int k=u-VPA_PRESSURE_WINDOW+2;k<=u;k++)
         den+=MathAbs(m_b[k].c-m_b[k-1].c);
      if(den<=0.0)
         return(false);
      double er=d*(c_u-c_ref)/den;
      double mean_clv=0.0;
      for(int k=u-VPA_PRESSURE_WINDOW+1;k<=u;k++)
         mean_clv+=m_clv[k];
      mean_clv=d*mean_clv/VPA_PRESSURE_WINDOW;
      bool slope_ok=(m_ema_ok[u] && m_ema_ok[u-VPA_PRESSURE_WINDOW+1]);
      double slope=0.0;
      if(slope_ok)
         slope=d*(m_ema[u]-m_ema[u-VPA_PRESSURE_WINDOW+1])/m_atr[u];
      return(disp>=VPA_DISP_MIN && er>=VPA_ER_MIN && mean_clv>=VPA_CLV_MIN
             && slope_ok && slope>=VPA_PRESSURE_SLOPE_MIN);
     }

   //--- vpa_dr1.py:184-208 + vpa_core.py:182-196
   void ConfirmPivots(const int t)
     {
      int L=VPA_PIVOT_LAG;
      int i=t-L;
      if(i<L)
         return;
      double left_h=MathMax(m_b[i-1].h,m_b[i-2].h);
      double left_l=MathMin(m_b[i-1].l,m_b[i-2].l);
      double right_h=MathMax(m_b[i+1].h,m_b[i+2].h);
      double right_l=MathMin(m_b[i+1].l,m_b[i+2].l);
      bool hi=(m_b[i].h>left_h && m_b[i].h>=right_h);
      bool lo=(m_b[i].l<left_l && m_b[i].l<=right_l);
      if(hi)
         AddPivot(i,m_b[i].h,+1);
      if(lo)
         AddPivot(i,m_b[i].l,-1);
      //--- significant pivots: extremum over +-5 bars, tested at t = j + 5
      int S=VPA_PIVOT_SIG_LAG;
      int j=t-S;
      if(j>=S && j+S<=t)
        {
         double lhs=0.0;
         double lls=0.0;
         double rhs=0.0;
         double rls=0.0;
         for(int k=j-S;k<j;k++)
           {
            if(k==j-S)
              {
               lhs=m_b[k].h;
               lls=m_b[k].l;
               continue;
              }
            if(m_b[k].h>lhs)
               lhs=m_b[k].h;
            if(m_b[k].l<lls)
               lls=m_b[k].l;
           }
         for(int k=j+1;k<=j+S;k++)
           {
            if(k==j+1)
              {
               rhs=m_b[k].h;
               rls=m_b[k].l;
               continue;
              }
            if(m_b[k].h>rhs)
               rhs=m_b[k].h;
            if(m_b[k].l<rls)
               rls=m_b[k].l;
           }
         if(m_b[j].h>lhs && m_b[j].h>=rhs)
            AddPivotSig(j,m_b[j].h,+1);
         if(m_b[j].l<lls && m_b[j].l<=rls)
            AddPivotSig(j,m_b[j].l,-1);
        }
      //--- lock attempts: base class order, high then low (vpa_core.py:191-196)
      if(hi)
         TryLock(i,+1);
      if(lo)
         TryLock(i,-1);
     }

   void AddPivot(const int idx,const double px,const int kind)
     {
      int n=ArraySize(m_pivots);
      ArrayResize(m_pivots,n+1);
      m_pivots[n].idx=idx;
      m_pivots[n].px=px;
      m_pivots[n].kind=kind;
      if(ArraySize(m_pivots)>VPA_MAX_PIVOTS)
        {
         for(int i=0;i<VPA_MAX_PIVOTS;i++)
            m_pivots[i]=m_pivots[ArraySize(m_pivots)-VPA_MAX_PIVOTS+i];
         ArrayResize(m_pivots,VPA_MAX_PIVOTS);
        }
     }

   void AddPivotSig(const int idx,const double px,const int kind)
     {
      int n=ArraySize(m_pivots_sig);
      ArrayResize(m_pivots_sig,n+1);
      m_pivots_sig[n].idx=idx;
      m_pivots_sig[n].px=px;
      m_pivots_sig[n].kind=kind;
      if(ArraySize(m_pivots_sig)>VPA_MAX_PIVOTS)
        {
         for(int i=0;i<VPA_MAX_PIVOTS;i++)
            m_pivots_sig[i]=m_pivots_sig[ArraySize(m_pivots_sig)-VPA_MAX_PIVOTS+i];
         ArrayResize(m_pivots_sig,VPA_MAX_PIVOTS);
        }
     }

   //--- vpa_core.py:198-238
   void TryLock(const int i,const int side)
     {
      if(!m_atr_ok[i] || m_atr[i]<=0.0)
         return;
      double A=m_atr[i];
      double eps=VPA_BARRIER_EPS_ATR*A;
      double px=(side>0) ? m_b[i].h : m_b[i].l;
      int touches[VPA_MAX_TOUCHES];
      double prices[VPA_MAX_TOUCHES];
      int n=0;
      touches[n]=i;
      prices[n]=px;
      n++;
      int limit=MathMax(0,i-VPA_BARRIER_SCAN);
      for(int j=i-2;j>=limit;j--)
        {
         double p=(side>0) ? m_b[j].h : m_b[j].l;
         bool far=true;
         for(int k=0;k<n;k++)
            if(MathAbs(j-touches[k])<2)
              {
               far=false;
               break;
              }
         if(far && MathAbs(p-px)<=eps)
           {
            if(n>=VPA_MAX_TOUCHES)
               break;
            touches[n]=j;
            prices[n]=p;
            n++;
           }
        }
      double B=VpaMedian(prices,n);
      if(n<VPA_BARRIER_T_MIN)
        {
         Cnt("skip_barrier_insufficient_touches");
         return;
        }
      if(side>0 && m_b[i].c>B+VPA_BARRIER_BREAK_ATR*A)
        {
         Cnt("skip_barrier_already_broken");
         return;
        }
      if(side<0 && m_b[i].c<B-VPA_BARRIER_BREAK_ATR*A)
        {
         Cnt("skip_barrier_already_broken");
         return;
        }
      for(int a=0;a<m_n_active;a++)
        {
         int bi=m_active[a];
         if(m_barriers[bi].side!=side)
            continue;
         if(MathAbs(m_barriers[bi].level-B)<=VPA_DEDUPE_ATR*A)
           {
            Cnt("skip_duplicate_barrier");
            return;
           }
         int shared=0;
         for(int p=0;p<n;p++)
            for(int q=0;q<m_barriers[bi].n_touches;q++)
               if(touches[p]==m_barriers[bi].touches[q])
                  shared++;
         if(shared>=2)
           {
            Cnt("skip_duplicate_barrier");
            return;
           }
        }
      int nb=ArraySize(m_barriers);
      ArrayResize(m_barriers,nb+1);
      m_barriers[nb].id=nb;
      m_barriers[nb].side=side;
      m_barriers[nb].level=B;
      m_barriers[nb].lock_idx=i;
      m_barriers[nb].exp_idx=i+VPA_BARRIER_EXPIRY;
      m_barriers[nb].n_touches=n;
      for(int k=0;k<n;k++)
         m_barriers[nb].touches[k]=touches[k];
      m_barriers[nb].atr_lock=A;
      m_barriers[nb].end_idx=-1;
      m_barriers[nb].end_kind=VPA_END_ACTIVE;
      m_barriers[nb].integrity_fail=false;
      m_n_barriers=nb+1;
      ArrayResize(m_active,m_n_active+1);
      m_active[m_n_active]=nb;
      m_n_active++;
      Cnt("barrier_locked");
     }

   //--- vpa_dr1.py:227-240: expiry only, consumption lives in Dr1Eval
   void BarrierUpdate(const int t)
     {
      if(!m_atr_ok[t] || m_atr[t]<=0.0)
         return;
      int keep[];
      int nkeep=0;
      for(int a=0;a<m_n_active;a++)
        {
         int bi=m_active[a];
         if(t>m_barriers[bi].exp_idx)
           {
            m_barriers[bi].end_kind=VPA_END_EXPIRED;
            m_barriers[bi].end_idx=m_barriers[bi].exp_idx;
            Cnt("barrier_expired");
            continue;
           }
         ArrayResize(keep,nkeep+1);
         keep[nkeep]=bi;
         nkeep++;
        }
      ArrayResize(m_active,nkeep);
      for(int i=0;i<nkeep;i++)
         m_active[i]=keep[i];
      m_n_active=nkeep;
     }

   //--- vpa_dr1.py:270-319
   void Dr1Eval(const int t)
     {
      if(t<1)
         return;
      if(!m_atr_ok[t] || m_atr[t]<=0.0)
         return;
      double A=m_atr[t];
      double ct=m_b[t].c;
      int consumed_id[];
      int consumed_kind[];
      int nconsumed=0;
      for(int a=0;a<m_n_active;a++)
        {
         int bi=m_active[a];
         int side=m_barriers[bi].side;
         double B=m_barriers[bi].level;
         double dist=side*(ct-B);
         if(dist < -VPA_SIGNAL_ATR*A)
            continue;
         bool exec_here=false;
         if(dist > VPA_SIGNAL_MAX_ATR*A)
           {
            int sig=-1;
            for(int q=0;q<m_barriers[bi].n_touches;q++)
              {
               int ii=m_barriers[bi].touches[q];
               if(ii>=m_barriers[bi].lock_idx && ii<t)
                  sig=ii;
              }
            if(sig>=0)
              {
               Cnt("signal_eval");
               if(Dr1Candidate(t,bi,sig))
                  exec_here=true;
              }
            if(!exec_here)
               Cnt("skip_missed_break");
            ArrayResize(consumed_id,nconsumed+1);
            ArrayResize(consumed_kind,nconsumed+1);
            consumed_id[nconsumed]=bi;
            consumed_kind[nconsumed]=(exec_here ? VPA_END_EXEC : VPA_END_MISSED);
            nconsumed++;
            continue;
           }
         Cnt("signal_eval");
         if(Dr1Candidate(t,bi,t))
           {
            ArrayResize(consumed_id,nconsumed+1);
            ArrayResize(consumed_kind,nconsumed+1);
            consumed_id[nconsumed]=bi;
            consumed_kind[nconsumed]=VPA_END_EXEC;
            nconsumed++;
           }
        }
      if(nconsumed>0)
        {
         for(int i=0;i<nconsumed;i++)
           {
            m_barriers[consumed_id[i]].end_kind=consumed_kind[i];
            m_barriers[consumed_id[i]].end_idx=t;
           }
         int keep[];
         int nkeep=0;
         for(int a=0;a<m_n_active;a++)
           {
            bool drop=false;
            for(int i=0;i<nconsumed;i++)
               if(m_active[a]==consumed_id[i])
                 {
                  drop=true;
                  break;
                 }
            if(drop)
               continue;
            ArrayResize(keep,nkeep+1);
            keep[nkeep]=m_active[a];
            nkeep++;
           }
         ArrayResize(m_active,nkeep);
         for(int i=0;i<nkeep;i++)
            m_active[i]=keep[i];
         m_n_active=nkeep;
        }
     }

   //--- vpa_dr1.py:404-463
   bool Dr1Candidate(const int t,const int bi,const int sig)
     {
      int side=m_barriers[bi].side;
      double B=m_barriers[bi].level;
      VpaEvent e;
      ResetEvent(e);
      e.id=m_n_events;
      e.bar_idx=sig;
      e.trig_idx=t;
      e.side=side;
      e.level=B;
      e.lock_idx=m_barriers[bi].lock_idx;
      e.n_touches=m_barriers[bi].n_touches;
      e.session=SessionDr1(t);
      e.atr=m_atr[sig];
      e.atr_ok=m_atr_ok[sig];
      e.ema=m_ema[sig];
      e.ema_ok=m_ema_ok[sig];
      e.bias=m_bias[sig];
      e.pressure=m_pressure[sig];
      e.bars_since_pressure=(long)sig-m_last_pressure_end;
      e.lunch=LunchFeature(t);
      Gates(sig,bi,t,e);
      int first_fail=-1;
      for(int g=0;g<VPA_NGATES;g++)
        {
         if(!VpaGateHard(g))
            continue;
         if(!e.gate_eval[g])
            continue;
         if(!e.gate_pass[g])
           {
            first_fail=g;
            break;
           }
        }
      e.first_fail=first_fail;
      e.executable=(first_fail<0);
      if(!e.executable)
        {
         if(e.gate_eval[4] && !e.gate_pass[4])
            m_barriers[bi].integrity_fail=true;
         if(e.chop_exempt)
           {
            bool pre_fail=(first_fail==0 || first_fail==1 || first_fail==2 || first_fail==3);
            if(!pre_fail)
               Cnt("chop_exempt_buildup");
           }
         Cnt(VpaGateReason(first_fail));
         AppendEvent(e);
         return(false);
        }
      if(CombiDr1(sig,side,B))
         e.setup="combi";
      Cnt("executable_"+e.setup);
      AppendEvent(e);
      return(true);
     }

   void ResetEvent(VpaEvent &e)
     {
      e.id=0;
      e.bar_idx=0;
      e.trig_idx=0;
      e.side=0;
      e.level=0.0;
      e.lock_idx=0;
      e.n_touches=0;
      e.executable=false;
      e.first_fail=-1;
      for(int g=0;g<VPA_NGATES;g++)
        {
         e.gate_pass[g]=false;
         e.gate_eval[g]=false;
        }
      e.session="";
      e.setup="pattern_break";
      e.has_entry=false;
      e.entry=0.0;
      e.invalidation=0.0;
      e.atr=0.0;
      e.atr_ok=false;
      e.ema=0.0;
      e.ema_ok=false;
      e.has_room=false;
      e.room_r=0.0;
      e.room_inf=false;
      e.has_obstacle=false;
      e.obstacle_price=0.0;
      e.obstacle_type="";
      e.ema_dist_atr=0.0;
      e.entry_b_atr=0.0;
      e.range_atr=0.0;
      e.squeeze=false;
      e.lunch=false;
      e.chop=false;
      e.chop_exempt=false;
      e.chop_window=-1;
      e.buildup_n=0;
      e.buildup_start=-1;
      e.band_closes=-1;
      e.bu_touches=-1;
      e.overlap=0.0;
      e.contraction=0.0;
      e.has_buildup=false;
      e.trend_slope=0.0;
      e.frac_side=0.0;
      e.signal_body_frac=0.0;
      e.trend_ok=false;
      e.doji=false;
      e.bias=0;
      e.pressure=false;
      e.bars_since_pressure=0;
      e.rho=0.0;
      e.has_rho=false;
     }

   void AppendEvent(const VpaEvent &e)
     {
      ArrayResize(m_events,m_n_events+1);
      m_events[m_n_events]=e;
      m_n_events++;
     }

   //--- vpa_dr1.py:253-261
   string SessionDr1(const int t)
     {
      int m=m_b[t].utc_min;
      if(m>=VPA_EU_LO && m<VPA_EU_HI)
         return("eu");
      if(m>=VPA_US_LO && m<VPA_US_HI)
         return("us");
      return("");
     }

   //--- vpa_dr1.py:263-268
   bool LunchFeature(const int t)
     {
      int m=m_b[t].utc_min;
      return((m>=VPA_LUNCH_1_LO && m<VPA_LUNCH_1_HI) || (m>=VPA_LUNCH_2_LO && m<VPA_LUNCH_2_HI));
     }

   //--- vpa_dr1.py:322-402: every gate, no short circuit
   void Gates(const int sig,const int bi,const int trig,VpaEvent &e)
     {
      int side=m_barriers[bi].side;
      double B=m_barriers[bi].level;
      double A=m_atr[sig];
      double rng=m_b[sig].h-m_b[sig].l;
      double body=m_b[sig].c-m_b[sig].o;
      //--- 1 warmup
      e.gate_eval[0]=true;
      e.gate_pass[0]=(sig>=VPA_WARMUP_BARS);
      //--- 2 session, measured at the trigger bar (prereg F2 / DR3 s2)
      e.gate_eval[1]=true;
      e.gate_pass[1]=(SessionDr1(trig)!="");
      //--- 3 direction (D1a)
      bool doji=(rng>0.0 && MathAbs(body)<=VPA_DOJI_BODY_FRAC*rng);
      bool dir_ok=((side>0 && (body>0.0 || doji)) || (side<0 && (body<0.0 || doji)));
      e.gate_eval[2]=true;
      e.gate_pass[2]=dir_ok;
      e.signal_body_frac=(rng>0.0) ? body/rng : 0.0;
      e.doji=doji;
      //--- 4 trend
      bool trend_ok=(m_atr_ok[sig] && m_ema_ok[sig] && sig>=VPA_SLOPE_LOOKBACK
                     && m_ema_ok[sig-VPA_SLOPE_LOOKBACK]);
      double slope=0.0;
      if(trend_ok)
         slope=side*(m_ema[sig]-m_ema[sig-VPA_SLOPE_LOOKBACK])/A;
      int cnt_side=0;
      for(int i=sig-VPA_FRAC_LOOKBACK+1;i<=sig;i++)
        {
         if(i<0 || !m_ema_ok[i])
            continue;
         if(side*(m_b[i].c-m_ema[i])>=0.0)
            cnt_side++;
        }
      double frac=(double)cnt_side/(double)VPA_FRAC_LOOKBACK;
      e.gate_eval[3]=true;
      e.gate_pass[3]=(trend_ok && slope>=VPA_THETA_SLOPE && frac>=VPA_FRAC_SIDE_MIN);
      e.trend_ok=trend_ok;
      e.trend_slope=NormalizeDouble(slope,4);
      e.frac_side=NormalizeDouble(frac,3);
      //--- 5 integrity (F2c): no close beyond B by more than eps after first touch
      double eps=VPA_INTEGRITY_EPS_ATR*A;
      int first_touch=-1;
      for(int q=0;q<m_barriers[bi].n_touches;q++)
        {
         int ii=m_barriers[bi].touches[q];
         if(ii<=sig && (first_touch<0 || ii<first_touch))
            first_touch=ii;
        }
      bool int_ok=true;
      if(first_touch>=0)
         for(int i=first_touch;i<=sig;i++)
           {
            double beyond=side*(m_b[i].c-B);
            if(beyond>eps)
              {
               int_ok=false;
               break;
              }
           }
      e.gate_eval[4]=true;
      e.gate_pass[4]=int_ok;
      //--- 6 buildup (vpa_dr1.py:466-515)
      Buildup bu;
      bool has_bu=BuildupDr1(sig,side,B,A,bu);
      e.gate_eval[6]=true;
      e.gate_pass[6]=has_bu;
      e.has_buildup=has_bu;
      if(has_bu)
        {
         e.buildup_n=bu.n;
         e.buildup_start=bu.start;
         e.band_closes=bu.band_closes;
         e.bu_touches=bu.touches;
         e.overlap=bu.overlap;
         e.contraction=bu.contraction;
         e.squeeze=bu.squeeze;
        }
      //--- 7 chop (vpa_dr1.py:368-376), exempt inside a valid buildup
      bool chop=ChopDr1(sig);
      e.gate_eval[5]=true;
      e.gate_pass[5]=((!chop) || has_bu);
      e.chop=chop;
      e.chop_exempt=(chop && has_bu);
      e.chop_window=-1;
      if(has_bu)
         e.chop_window=(ChopMetrics(bu.start,sig) ? 1 : 0);
      //--- 8..11 room / adverse / anti-chase / cost
      if(has_bu)
        {
         double entry=(side>0) ? (m_b[sig].h+VPA_ENTRY_BUFFER_PIPS*m_pip)
                      : (m_b[sig].l-VPA_ENTRY_BUFFER_PIPS*m_pip);
         double inv=0.0;
         if(side>0)
           {
            double lo=0.0;
            for(int i=bu.start;i<sig;i++)
               if(i==bu.start || m_b[i].l<lo)
                  lo=m_b[i].l;
            inv=lo-0.10*A;
           }
         else
           {
            double hi=0.0;
            for(int i=bu.start;i<sig;i++)
               if(i==bu.start || m_b[i].h>hi)
                  hi=m_b[i].h;
            inv=hi+0.10*A;
           }
         double S=VPA_STOP_PIPS*m_pip;
         double room=0.0;
         double obs_price=0.0;
         string obs_type="";
         bool has_obs=false;
         bool room_inf=false;
         RoomDetail(sig,side,entry,A,bi,room,room_inf,has_obs,obs_price,obs_type);
         e.gate_eval[7]=true;
         e.gate_pass[7]=(room>=VPA_ROOM_R_MIN*S);
         e.has_room=true;
         e.room_r=room/S;
         e.room_inf=room_inf;
         e.has_obstacle=has_obs;
         e.obstacle_price=obs_price;
         e.obstacle_type=obs_type;
         bool adv=false;
         double adv_price=0.0;
         string adv_type="";
         AdverseDetail(sig,side,entry,S,bu.start,adv,adv_price,adv_type);
         e.gate_eval[8]=true;
         e.gate_pass[8]=(!adv);
         double entry_b=side*(entry-B);
         bool ema_dist_ok=(m_ema_ok[sig]);
         double ema_dist=(ema_dist_ok) ? MathAbs(entry-m_ema[sig]) : 0.0;
         e.gate_eval[9]=true;
         e.gate_pass[9]=(entry_b<=VPA_ENTRY_BUFFER_PIPS*m_pip+VPA_ANTI_ENTRY_B_ATR*A
                         && rng<=VPA_ANTI_SIGNAL_RANGE_ATR*A
                         && ema_dist_ok && ema_dist<=VPA_ANTI_EMA_ATR*A);
         //--- logged exactly like vpa_dr1.py:392-394 (round(...,4) of the ATR ratio)
         e.ema_dist_atr=NormalizeDouble((ema_dist_ok ? ema_dist/A : 0.0),4);
         e.ema_dist_ok=ema_dist_ok;
         e.entry_b_atr=NormalizeDouble(entry_b/A,4);
         e.range_atr=NormalizeDouble(rng/A,4);
         e.rho=VPA_COST_PIPS/VPA_STOP_PIPS;
         e.gate_eval[10]=true;
         e.gate_pass[10]=(e.rho<=VPA_RHO_MAX);
         e.has_rho=true;
         e.has_entry=true;
         e.entry=entry;
         e.invalidation=inv;
        }
     }

   //--- vpa_dr1.py:466-515
   bool BuildupDr1(const int t,const int d,const double B,const double A,Buildup &out)
     {
      out.has=false;
      out.n=0;
      out.start=-1;
      out.contraction=0.0;
      out.overlap=0.0;
      out.band_closes=-1;
      out.touches=-1;
      out.conditions_passed=0;
      out.squeeze=false;
      out.v2ok=false;
      out.v2of4_n=0;
      out.vtok=false;
      out.vtight_n=0;
      Buildup prim,sec,tgt;
      ZeroMemory(prim);
      ZeroMemory(sec);
      ZeroMemory(tgt);
      bool have_prim=false;
      bool have_sec=false;
      bool have_tgt=false;
      for(int n=VPA_BUILDUP_MAX;n>=VPA_BUILDUP_MIN;n--)
        {
         int s=t-n;
         if(s<1)
            continue;
         int band_closes=0;
         int touches=0;
         for(int i=s;i<t;i++)
           {
            double v=d*(B-m_b[i].c);
            if(v>=VPA_BAND_LO_ATR*A && v<=VPA_BAND_HI_ATR*A)
               band_closes++;
            double p=(d>0) ? m_b[i].h : m_b[i].l;
            if(MathAbs(p-B)<=VPA_BUILDUP_TOUCH_ATR*A)
               touches++;
           }
         int pfrom=MathMax(0,s-12);
         int wlen=t-s;
         int plen=s-pfrom;
         if(wlen<=0 || plen<=0)
            continue;
         double med_w=VpaMedianSlice(m_tr,s,t);
         double med_p=VpaMedianSlice(m_tr,pfrom,s);
         double contraction=(med_p>0.0) ? med_w/med_p : 9.9;
         double ov_sum=0.0;
         int n_ov=0;
         for(int i=s+1;i<t;i++)
           {
            double den=MathMax(MathMin(m_b[i].h-m_b[i].l,m_b[i-1].h-m_b[i-1].l),1e-12);
            ov_sum+=MathMax(0.0,MathMin(m_b[i].h,m_b[i-1].h)-MathMax(m_b[i].l,m_b[i-1].l))/den;
            n_ov++;
           }
         double overlap=(n_ov>0) ? ov_sum/n_ov : 0.0;
         int npass=0;
         if(band_closes>=VPA_MIN_BAND_CLOSES)
            npass++;
         if(touches>=VPA_MIN_TOUCHES)
            npass++;
         if(overlap>=VPA_OVERLAP_MIN)
            npass++;
         if(contraction<=VPA_CONTRACTION_MAX)
            npass++;
         Buildup m;
         m.has=true;
         m.n=n;
         m.start=s;
         m.contraction=contraction;
         m.overlap=overlap;
         m.band_closes=band_closes;
         m.touches=touches;
         m.conditions_passed=npass;
         m.squeeze=false;
         m.v2ok=false;
         m.v2of4_n=0;
         m.vtok=false;
         m.vtight_n=0;
         if(!have_prim && npass>=VPA_BUILDUP_MIN_CONDITIONS)
           {
            prim=m;
            have_prim=true;
           }
         if(!have_sec && npass>=2)
           {
            sec=m;
            have_sec=true;
           }
         if(!have_tgt && band_closes>=3 && touches>=2 && contraction<=VPA_CONTRACTION_MAX)
           {
            tgt=m;
            have_tgt=true;
           }
         if(have_prim && have_sec && have_tgt)
            break;
        }
      if(!have_prim)
         return(false);
      bool squeeze=false;
      if(m_ema_ok[t] && MathAbs(m_ema[t]-B)<=VPA_SQUEEZE_EMA_ATR*A)
        {
         int nbars=0;
         for(int i=prim.start;i<t;i++)
            if(m_ema_ok[i] && m_b[i].l<=m_ema[i] && m_ema[i]<=m_b[i].h)
               nbars++;
         squeeze=(nbars>=VPA_SQUEEZE_MIN_BARS);
        }
      out.has=true;
      out.n=prim.n;
      out.start=prim.start;
      out.contraction=prim.contraction;
      out.overlap=prim.overlap;
      out.band_closes=prim.band_closes;
      out.touches=prim.touches;
      out.conditions_passed=prim.conditions_passed;
      out.squeeze=squeeze;
      out.v2ok=have_sec;
      out.v2of4_n=(have_sec) ? sec.n : 0;
      out.vtok=have_tgt;
      out.vtight_n=(have_tgt) ? tgt.n : 0;
      return(true);
     }

   //--- vpa_dr1.py:517-538
   bool ChopMetrics(const int lo,const int hi)
     {
      if(hi-lo<2)
         return(false);
      if(lo<1)
         return(false);
      double ov_sum=0.0;
      int n=0;
      bool doji=false;
      bool long_bar=false;
      for(int i=lo;i<hi;i++)
        {
         double den=MathMax(MathMin(m_b[i].h-m_b[i].l,m_b[i-1].h-m_b[i-1].l),1e-12);
         ov_sum+=MathMax(0.0,MathMin(m_b[i].h,m_b[i-1].h)-MathMax(m_b[i].l,m_b[i-1].l))/den;
         n++;
         double rng=m_b[i].h-m_b[i].l;
         if(rng>0.0 && MathAbs(m_b[i].c-m_b[i].o)/rng<=VPA_CHOP_BODY_MAX)
            doji=true;
         if(m_atr_ok[i] && rng>VPA_CHOP_LONG_ATR*m_atr[i])
            long_bar=true;
        }
      if(n<=0)
         return(false);
      double overlap=ov_sum/(double)n;
      int np=0;
      for(int i=lo+1;i<hi;i++)
         if((m_b[i].l-m_b[i-1].l)>=0.0)
            np++;
      int nd=hi-lo-1;
      double prog=(nd>0) ? (double)np/(double)nd : 0.0;
      return(overlap>=VPA_CHOP_OVERLAP_MIN && prog<=VPA_CHOP_PROG_MAX && (doji || long_bar));
     }

   bool ChopDr1(const int t)
     {
      if(t<VPA_CHOP_LOOKBACK+1)
         return(false);
      return(ChopMetrics(t-VPA_CHOP_LOOKBACK,t));
     }

   //--- vpa_dr1.py:550-565
   double RoomZone(const int t,const int d,const double entry,const double A,const int bi)
     {
      double B=m_barriers[bi].level;
      double eps=VPA_INTEGRITY_EPS_ATR*A;
      double S=VPA_STOP_PIPS*m_pip;
      double extreme=B;
      bool have=false;
      for(int q=0;q<m_barriers[bi].n_touches;q++)
        {
         int ii=m_barriers[bi].touches[q];
         if(ii>t)
            continue;
         double p=(d>0) ? m_b[ii].h : m_b[ii].l;
         if(!have || (d>0 && p>extreme) || (d<0 && p<extreme))
           {
            extreme=p;
            have=true;
           }
        }
      if(d>0)
         return(MathMax(extreme+eps,entry+MathMax(eps,VPA_ROOM_ZONE_R*S)));
      return(MathMin(extreme-eps,entry-MathMax(eps,VPA_ROOM_ZONE_R*S)));
     }

   //--- vpa_dr1.py:567-616
   void RoomDetail(const int t,const int d,const double entry,const double A,const int bi,
                   double &room,bool &room_inf,bool &has_obs,double &obs_price,string &obs_type)
     {
      room=VPA_INF;
      room_inf=true;
      has_obs=false;
      obs_price=0.0;
      obs_type="";
      bool has_zone=(VPA_ROOM_ZONE_R>0.0);
      double zone=0.0;
      if(has_zone)
         zone=RoomZone(t,d,entry,A,bi);
      for(int p=0;p<ArraySize(m_pivots_sig);p++)
        {
         int i=m_pivots_sig[p].idx;
         int kind=m_pivots_sig[p].kind;
         double px=m_pivots_sig[p].px;
         if(i>=t || kind!=d)
            continue;
         if(!((d>0 && px>entry+0.05*A) || (d<0 && px<entry-0.05*A)))
            continue;
         if(has_zone && ((d>0 && px<=zone) || (d<0 && px>=zone)))
            continue;
         double dist=MathAbs(px-entry);
         if(dist<room)
           {
            room=dist;
            room_inf=false;
            has_obs=true;
            obs_price=px;
            obs_type="pivot_sig";
           }
        }
      for(int a=0;a<m_n_active;a++)
        {
         int bb=m_active[a];
         if(m_barriers[bb].side!=d)
            continue;
         double lvl=m_barriers[bb].level;
         if(!((d>0 && lvl>entry) || (d<0 && lvl<entry)))
            continue;
         if(has_zone && ((d>0 && lvl<=zone) || (d<0 && lvl>=zone)))
            continue;
         double dist=MathAbs(lvl-entry);
         if(dist<room)
           {
            room=dist;
            room_inf=false;
            has_obs=true;
            obs_price=lvl;
            obs_type="barrier";
           }
        }
      if(m_pd_ok)
        {
         double lvl=(d>0) ? m_pdh : m_pdl;
         if((d>0 && lvl>entry+0.05*A) || (d<0 && lvl<entry-0.05*A))
           {
            if(!has_zone || (d>0 && lvl>zone) || (d<0 && lvl<zone))
              {
               double dist=MathAbs(lvl-entry);
               if(dist<room)
                 {
                  room=dist;
                  room_inf=false;
                  has_obs=true;
                  obs_price=lvl;
                  obs_type=(d>0) ? "pdh" : "pdl";
                 }
              }
           }
        }
      if(m_round_grid>0.0)
        {
         double nxt=(d>0) ? MathFloor(entry/m_round_grid+1.0)*m_round_grid
                    : MathCeil(entry/m_round_grid-1.0)*m_round_grid;
         if((d>0 && nxt>entry) || (d<0 && nxt<entry))
           {
            if(!has_zone || (d>0 && nxt>zone) || (d<0 && nxt<zone))
              {
               double dist=MathAbs(nxt-entry);
               if(dist<room)
                 {
                  room=dist;
                  room_inf=false;
                  has_obs=true;
                  obs_price=nxt;
                  obs_type="round_grid";
                 }
              }
           }
        }
     }

   //--- vpa_dr1.py:620-641
   void AdverseDetail(const int t,const int d,const double entry,const double S,const int bu_start,
                      bool &adv,double &adv_price,string &adv_type)
     {
      adv=false;
      adv_price=0.0;
      adv_type="";
      double skip=VPA_ADVERSE_SKIP_FRAC*S;
      for(int p=0;p<ArraySize(m_pivots);p++)
        {
         int i=m_pivots[p].idx;
         int kind=m_pivots[p].kind;
         double px=m_pivots[p].px;
         if(i>=t || i>=bu_start)
            continue;
         if(d>0 && kind==-1 && (entry-VPA_ADVERSE_PIVOT_R*S)<px && px<(entry-skip))
           {
            adv=true;
            adv_price=px;
            adv_type="pivot_low";
            return;
           }
         if(d<0 && kind==+1 && (entry+skip)<px && px<(entry+VPA_ADVERSE_PIVOT_R*S))
           {
            adv=true;
            adv_price=px;
            adv_type="pivot_high";
            return;
           }
        }
      if(m_round_grid>0.0)
        {
         if(d>0)
           {
            double lvl=MathFloor(entry/m_round_grid)*m_round_grid;
            if((entry-S)<lvl && lvl<(entry-skip))
              {
               adv=true;
               adv_price=lvl;
               adv_type="round_grid";
               return;
              }
           }
         else
           {
            double lvl=MathCeil(entry/m_round_grid)*m_round_grid;
            if((entry+skip)<lvl && lvl<(entry+S))
              {
               adv=true;
               adv_price=lvl;
               adv_type="round_grid";
               return;
              }
           }
        }
     }

   //--- vpa_dr1.py:646-663
   bool CombiDr1(const int t,const int d,const double B)
     {
      if(t<2)
         return(false);
      int p=t-1;
      double A=m_atr[p];
      if(!m_atr_ok[p] || A<=0.0 || (m_b[p].h-m_b[p].l)<=0.0)
         return(false);
      if(d*(m_b[p].c-m_b[p].o)<VPA_COMBI_BODY_ATR*A)
         return(false);
      if(d*m_clv[p]<VPA_COMBI_CLV)
         return(false);
      if(m_b[t].h>m_b[p].h+0.5*m_tick || m_b[t].l<m_b[p].l-0.5*m_tick)
         return(false);
      if((m_b[t].h-m_b[t].l)/(m_b[p].h-m_b[p].l)>VPA_COMBI_INSIDE_RATIO)
         return(false);
      return(true);
     }

   //--- CSV export (parity harness + indicator export mode) --------------
   string Num(const double v,const int digits,const bool ok)
     {
      if(!ok)
         return("");
      return(DoubleToString(v,digits));
     }

   bool ExportCsv(const string folder,const string prefix,const int from_idx,const int to_idx,
                  string &out_dir,string &out_err)
     {
      out_err="";
      int f0=(from_idx<0) ? 0 : from_idx;
      int f1=(to_idx>=m_n) ? m_n-1 : to_idx;
      if(f0>f1)
        {
         out_err="empty index range";
         return(false);
        }
      string dir=(StringLen(folder)>0) ? folder+"\\" : "";
      if(StringLen(folder)>0)
         FolderCreate(folder,0);
      string bars="idx,t,o,h,l,c,utc_min,srv_min\n";
      for(int i=f0;i<=f1;i++)
         bars+=IntegerToString(i)+","+IntegerToString(m_b[i].t)+","
               +DoubleToString(m_b[i].o,8)+","+DoubleToString(m_b[i].h,8)+","
               +DoubleToString(m_b[i].l,8)+","+DoubleToString(m_b[i].c,8)+","
               +IntegerToString(m_b[i].utc_min)+","+IntegerToString(m_b[i].srv_min)+"\n";
      if(!WriteText(dir+prefix+"_bars.csv",bars,out_err))
         return(false);
      string barriers="barrier_id,side,level,lock_idx,exp_idx,n_touches,end_idx,end_kind,integrity_fail\n";
      for(int i=0;i<m_n_barriers;i++)
        {
         if(m_barriers[i].lock_idx>f1 || m_barriers[i].exp_idx<f0)
            continue;
         string kind="active";
         if(m_barriers[i].end_kind==VPA_END_EXPIRED)
            kind="expired";
         if(m_barriers[i].end_kind==VPA_END_MISSED)
            kind="missed";
         if(m_barriers[i].end_kind==VPA_END_EXEC)
            kind="exec";
         int eidx=(m_barriers[i].end_kind==VPA_END_ACTIVE) ? -1 : m_barriers[i].end_idx;
         barriers+=IntegerToString(i)+","+IntegerToString(m_barriers[i].side)+","
                   +DoubleToString(m_barriers[i].level,8)+","
                   +IntegerToString(m_barriers[i].lock_idx)+","
                   +IntegerToString(m_barriers[i].exp_idx)+","
                   +IntegerToString(m_barriers[i].n_touches)+","
                   +IntegerToString(eidx)+","+kind+","
                   +IntegerToString(m_barriers[i].integrity_fail ? 1 : 0)+"\n";
        }
      if(!WriteText(dir+prefix+"_barriers.csv",barriers,out_err))
         return(false);
      string events="event_id,bar_idx,trig_idx,side,level,lock_idx,n_touches,entry,invalidation,verdict,"
                    "first_fail,fail_set,session,setup,room_r,room_inf,obstacle_price,obstacle_type,"
                    "ema_dist_atr,entry_b_atr,range_atr,squeeze,lunch,chop,chop_exempt,buildup_n,"
                    "buildup_start,band_closes,buildup_touches,overlap,contraction,trend_slope,"
                    "frac_side,signal_body_frac,doji,atr,ema,pressure,bars_since_pressure,rho,chop_window\n";
      for(int i=0;i<m_n_events;i++)
        {
         if(m_events[i].trig_idx<f0 || m_events[i].trig_idx>f1)
            continue;
         VpaEvent e=m_events[i];
         string fails="";
         if(e.executable)
            fails="";
         else
            for(int g=0;g<VPA_NGATES;g++)
               if(e.gate_eval[g] && !e.gate_pass[g])
                  fails+=(StringLen(fails)>0 ? ";" : "")+VpaGateKey(g);
         string first_fail=(e.first_fail>=0) ? VpaGateReason(e.first_fail) : "";
         string room_r="";
         if(e.has_room)
            room_r=(e.room_inf) ? "inf" : DoubleToString(e.room_r,3);
         string chop_window="";
         if(e.chop_window>=0)
            chop_window=IntegerToString(e.chop_window);
         string line=IntegerToString(e.id)+","+IntegerToString(e.bar_idx)+","
                     +IntegerToString(e.trig_idx)+","+IntegerToString(e.side)+","
                     +DoubleToString(e.level,8)+","+IntegerToString(e.lock_idx)+","
                     +IntegerToString(e.n_touches)+","
                     +Num(e.entry,8,e.has_entry)+","+Num(e.invalidation,8,e.has_entry)+","
                     +(e.executable ? "ACCEPT" : "SKIP")+","
                     +first_fail+","+fails+","+e.session+","+e.setup+","
                     +room_r+","+IntegerToString(e.room_inf ? 1 : 0)+","
                     +Num(e.obstacle_price,8,e.has_obstacle)+","+e.obstacle_type+","
                     +Num(e.ema_dist_atr,8,e.ema_dist_ok)+","+Num(e.entry_b_atr,8,e.has_room)+","
                     +Num(e.range_atr,8,e.has_room)+","
                     +IntegerToString(e.squeeze ? 1 : 0)+","
                     +IntegerToString(e.lunch ? 1 : 0)+","
                     +IntegerToString(e.chop ? 1 : 0)+","
                     +IntegerToString(e.chop_exempt ? 1 : 0)+","
                     +IntegerToString(e.buildup_n)+","+IntegerToString(e.buildup_start)+","
                     +IntegerToString(e.band_closes)+","+IntegerToString(e.bu_touches)+","
                     +Num(e.overlap,8,e.has_buildup)+","+Num(e.contraction,8,e.has_buildup)+","
                     +Num(e.trend_slope,4,e.trend_ok)+","+DoubleToString(e.frac_side,3)+","
                     +DoubleToString(e.signal_body_frac,8)+","+IntegerToString(e.doji ? 1 : 0)+","
                     +Num(e.atr,8,e.atr_ok)+","+Num(e.ema,8,e.ema_ok)+","
                     +IntegerToString(e.pressure ? 1 : 0)+","+IntegerToString(e.bars_since_pressure)+","
                     +Num(e.rho,8,e.has_rho)+","+chop_window+"\n";
         events+=line;
        }
      if(!WriteText(dir+prefix+"_events.csv",events,out_err))
         return(false);
      out_dir=dir;
      return(true);
     }

   bool WriteText(const string path,const string text,string &out_err)
     {
      int h=FileOpen(path,FILE_WRITE|FILE_TXT|FILE_ANSI);
      if(h==INVALID_HANDLE)
        {
         out_err=StringFormat("cannot open %s (err %d)",path,GetLastError());
         return(false);
        }
      FileWriteString(h,text);
      FileClose(h);
      return(true);
     }

  };

//+------------------------------------------------------------------+
//| free helpers shared by the indicator and the parity script        |
//+------------------------------------------------------------------+
string VpaCounterSummary(CVpaDr3 &d)
  {
   string out="";
   string keys[]={"signal_eval","barrier_locked","barrier_expired","skip_missed_break",
                  "skip_barrier_insufficient_touches","skip_barrier_already_broken",
                  "skip_duplicate_barrier","executable_pattern_break","executable_combi",
                  "skip_warmup","skip_session","skip_direction","skip_trend","skip_integrity",
                  "skip_chop","skip_no_buildup","skip_room","skip_adverse_magnet","skip_anti_chase"};
   for(int i=0;i<ArraySize(keys);i++)
     {
      int v=d.CntGet(keys[i]);
      if(v>0)
         out+=(StringLen(out)>0 ? "," : "")+keys[i]+"="+IntegerToString(v);
     }
   return(out);
  }

double VpaPipSize(const string sym)
  {
   int d=(int)SymbolInfoInteger(sym,SYMBOL_DIGITS);
   double pt=SymbolInfoDouble(sym,SYMBOL_POINT);
   return((d==3 || d==5) ? 10.0*pt : pt);
  }

double VpaTickSize(const string sym)
  {
   return(SymbolInfoDouble(sym,SYMBOL_POINT));
  }

//--- full parity export: CopyRates window -> ported detector -> 3 CSVs.
//--- The forming bar is never exported, so the CSV series is closed bars only.
bool VpaExportWindow(const string sym,const ENUM_TIMEFRAMES tf,const datetime t0,const datetime t1,
                     const string folder,const string prefix,string &msg)
  {
   MqlRates r[];
   ArraySetAsSeries(r,false);
   int got=CopyRates(sym,tf,t0,t1,r);
   if(got<100)
     {
      msg=StringFormat("CopyRates returned %d bars for %s %s",got,sym,EnumToString(tf));
      return(false);
     }
   datetime cur=(datetime)SeriesInfoInteger(sym,tf,SERIES_LASTBAR_DATE);
   int n=0;
   for(int i=0;i<got;i++)
      if(!(cur>0 && r[i].time>=cur))
         n++;
   if(n<100)
     {
      msg=StringFormat("only %d closed bars in window",n);
      return(false);
     }
   VpaBar bars[];
   ArrayResize(bars,n);
   int k=0;
   for(int i=0;i<got;i++)
     {
      if(cur>0 && r[i].time>=cur)
         continue;
      bars[k].t=(long)r[i].time;
      bars[k].o=r[i].open;
      bars[k].h=r[i].high;
      bars[k].l=r[i].low;
      bars[k].c=r[i].close;
      datetime ct=(datetime)((long)r[i].time+(long)PeriodSeconds(tf));
      VpaUtcMinute(ct,bars[k].utc_min,bars[k].srv_min);
      k++;
     }
   CVpaDr3 det;
   if(!det.Init(bars,n,VpaPipSize(sym),VpaTickSize(sym)))
     {
      msg=det.m_error;
      return(false);
     }
   det.Run();
   string dir="";
   string err="";
   if(!det.ExportCsv(folder,prefix,0,n-1,dir,err))
     {
      msg=err;
      return(false);
     }
   msg=StringFormat("bars=%d events=%d barriers=%d dir=%s counters[%s]",n,det.m_n_events,
                    det.m_n_barriers,dir,VpaCounterSummary(det));
   return(true);
  }

