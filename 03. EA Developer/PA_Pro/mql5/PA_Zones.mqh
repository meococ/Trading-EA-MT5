//+------------------------------------------------------------------+
//|                                                     PA_Zones.mqh |
//|  PA-PRO EA lane - causal zone engine, port of                    |
//|    PA_Pro/struct/zones/common.py + the six frozen generators.    |
//|                                                                  |
//|  SEMANTIC CONTRACT (binding, Lead ruling + SF01 DECISIONS D4):   |
//|  the read side is views_at/state_at = replay of _step_zone over  |
//|  EVERY bar in [born_idx, t].  The live pass (_step_all) is an    |
//|  approximation that decides the zone UNIVERSE and lifecycle      |
//|  (creation, set_band, end_idx, retirement) only.  families/      |
//|  sf_ctx.py run_pass (:127-208) is the unit-tested reference:     |
//|    - per bar: _on_bar(t) then _step_all(t) drive the universe;   |
//|    - a shadow state per zone is stepped over every bar in        |
//|      [born, t] with replaying semantics (no side effects);       |
//|    - zones created at t with born<t are BACKFILLED [born, t-1];  |
//|    - reads filter created_idx <= t <= end_idx, then strength +   |
//|      sort (-S, zid) + arm_zones.                                 |
//|  This file mirrors that: each zone carries st_* (pass) and sx_*  |
//|  (shadow).  No outcomes, no orders anywhere in this header.      |
//+------------------------------------------------------------------+
#ifndef PA_ZONES_MQH
#define PA_ZONES_MQH

#include "PA_Types.mqh"
#include "PA_Clock.mqh"

//+------------------------------------------------------------------+
//| small helpers                                                    |
//+------------------------------------------------------------------+
struct PaPivot      // common.confirmed_pivots row
  {
   int               idx;
   double            price;
   int               side;      // +1 high, -1 low
   int               confirm;   // idx + k
  };

struct PaH1Pivot    // ZoneContext.h1_pivots row mapped into M5 space
  {
   int               h1_idx;
   double            price;
   int               side;
   int               m5_confirm;
   int               m5_anchor;
  };

//--- common.wilder_atr (:109-130): NaN until bar period-1 -> *_ok flags here
void PaWilderAtr(const double &h[],const double &l[],const double &c[],
                 const int n,const int period,double &out[],bool &ok[])
  {
   ArrayResize(out,n);
   ArrayResize(ok,n);
   ArrayInitialize(out,0.0);
   if(n<period || n<=0)
     {
      for(int i=0;i<n;i++)
         ok[i]=false;
      return;
     }
   double tr[];
   ArrayResize(tr,n);
   tr[0]=h[0]-l[0];
   for(int i=1;i<n;i++)
      tr[i]=MathMax(h[i]-l[i],MathMax(MathAbs(h[i]-c[i-1]),MathAbs(l[i]-c[i-1])));
   for(int i=0;i<n;i++)
      ok[i]=false;
   double s=0.0;
   for(int i=0;i<period;i++)
      s+=tr[i];
   out[period-1]=s/period;
   ok[period-1]=true;
   double a=(period-1.0)/period;
   for(int i=period;i<n;i++)
     {
      out[i]=a*out[i-1]+(1.0-a)*tr[i];
      ok[i]=true;
     }
  }

//--- common.confirmed_pivots (:133-153): +-k fractals, sorted (confirm, idx)
int PaConfirmedPivots(const double &h[],const double &l[],const int n,
                      const int k,PaPivot &out[])
  {
   int m=0;
   ArrayResize(out,0);
   if(n<2*k+1)
      return(0);
   for(int j=k;j<n-k;j++)
     {
      bool isH=true,isL=true;
      for(int q=j-k;q<j;q++)
        {
         if(!(h[j]>h[q])) isH=false;
         if(!(l[j]<l[q])) isL=false;
        }
      for(int q=j+1;q<=j+k;q++)
        {
         if(!(h[j]>=h[q])) isH=false;
         if(!(l[j]<=l[q])) isL=false;
        }
      if(isH)
        {
         ArrayResize(out,m+1);
         out[m].idx=j; out[m].price=h[j]; out[m].side=+1; out[m].confirm=j+k;
         m++;
        }
      if(isL)
        {
         ArrayResize(out,m+1);
         out[m].idx=j; out[m].price=l[j]; out[m].side=-1; out[m].confirm=j+k;
         m++;
        }
     }
   //--- sort by (confirm, idx) - simple insertion (few thousand rows)
   for(int i=1;i<m;i++)
     {
      PaPivot v=out[i];
      int j=i-1;
      while(j>=0 && (out[j].confirm>v.confirm ||
            (out[j].confirm==v.confirm && out[j].idx>v.idx)))
        {
         out[j+1]=out[j];
         j--;
        }
      out[j+1]=v;
     }
   return(m);
  }

//+------------------------------------------------------------------+
//| CPaRefs - refs.py RefBook, computed incrementally (same values). |
//| pdh/pdl/pdc = previous completed server day; wk_hi/lo = previous |
//| completed week (Monday rollover); asia = UTC 00:00-05:00 window; |
//| round = 50-pip grid.                                             |
//+------------------------------------------------------------------+
class CPaRefs
  {
public:
   double            pip;
   double            grid;
   double            width_atr;   // confluence band half-width factor 0.25*A
   //--- current published values (arrays in refs.py; here the value at t)
   double            pdh,pdl,pdc;
   double            asia_hi,asia_lo;
   double            wk_hi,wk_lo;
   bool              pd_ok,asia_ok,wk_ok;
   //--- running trackers
   long              cur_day;
   double            d_hi,d_lo,d_c;
   bool              d_ok;
   double            p_hi,p_lo,p_c;
   bool              p_ok;
   double            w_hi,w_lo;
   bool              w_run;
   double            a_hi,a_lo;
   bool              a_run;
   double            a_done_hi,a_done_lo;
   bool              a_done;
   bool              in_asia_prev;
   long              last_t;

                     CPaRefs(void)
     {
      pip=0.0001; grid=PA_ROUND_GRID_PIPS*pip; width_atr=0.25;
      pd_ok=false; asia_ok=false; wk_ok=false;
      cur_day=-1; d_ok=false; p_ok=false;
      w_run=false; a_run=false; a_done=false; in_asia_prev=false;
      last_t=-1;
     }

   void Init(const double pip_)
     {
      pip=pip_; grid=PA_ROUND_GRID_PIPS*pip;
     }

   //--- one bar of the forward pass; b = closed M5 bar t (refs.py:59-121)
   void OnBar(const PaBar &b)
     {
      long day=b.t/PA_DAY_SEC;
      //--- day rollover
      if(day!=cur_day)
        {
         if(d_ok)
           {
            p_hi=d_hi; p_lo=d_lo; p_c=d_c; p_ok=true;
           }
         d_hi=b.h; d_lo=b.l; d_c=b.c; d_ok=true;
         cur_day=day;
        }
      else
        {
         if(!d_ok)
           {
            d_hi=b.h; d_lo=b.l; d_c=b.c; d_ok=true;
           }
         else
           {
            if(b.h>d_hi) d_hi=b.h;
            if(b.l<d_lo) d_lo=b.l;
            d_c=b.c;
           }
        }
      if(p_ok)
        {
         pdh=p_hi; pdl=p_lo; pdc=p_c; pd_ok=true;
        }
      //--- week: publish the completed week's extremes at a Monday rollover
      if(last_t>=0 && day!=(last_t/PA_DAY_SEC) && b.dow==0)
        {
         if(w_run)
           {
            wk_hi=w_hi; wk_lo=w_lo; wk_ok=true;
           }
         w_hi=b.h; w_lo=b.l; w_run=true;
        }
      else
        {
         if(!w_run)
           {
            w_hi=b.h; w_lo=b.l; w_run=true;
           }
         else
           {
            if(b.h>w_hi) w_hi=b.h;
            if(b.l<w_lo) w_lo=b.l;
           }
        }
      //--- Asia window on bar-close utc_min (refs.py:102-121)
      bool in_asia=(b.utc_min>=PA_ASIA_UTC_LO && b.utc_min<PA_ASIA_UTC_HI);
      if(in_asia)
        {
         if(!in_asia_prev)
           {
            a_hi=b.h; a_lo=b.l; a_run=true;
           }
         else
           {
            if(b.h>a_hi) a_hi=b.h;
            if(b.l<a_lo) a_lo=b.l;
           }
         asia_hi=a_hi; asia_lo=a_lo; asia_ok=a_run;
        }
      else
        {
         if(in_asia_prev && a_run)
           {
            a_done_hi=a_hi; a_done_lo=a_lo; a_done=true;
           }
         if(a_done)
           {
            asia_hi=a_done_hi; asia_lo=a_done_lo; asia_ok=true;
           }
        }
      in_asia_prev=in_asia;
      last_t=b.t;
     }

   //--- levels_at(t) equivalent: fills px[] with active level prices
   int LevelsAt(double &px[]) const
     {
      int n=0;
      ArrayResize(px,7);
      if(pd_ok)  { px[n]=pdh;     n++; px[n]=pdl;     n++; px[n]=pdc; n++; }
      if(asia_ok){ px[n]=asia_hi; n++; px[n]=asia_lo; n++; }
      if(wk_ok)  { px[n]=wk_hi;   n++; px[n]=wk_lo;   n++; }
      ArrayResize(px,n);
      return(n);
     }

   //--- round_near(price): the two nearest 00/50 grid prices; false =
   //--- refs.py's `g<=0 -> []` (no levels -> nothing published)
   bool RoundNear(const double price,double &g0,double &g1) const
     {
      g0=0.0; g1=0.0;
      if(!(grid>0.0))
         return(false);
      double k=MathFloor(price/grid);
      g0=k*grid; g1=(k+1.0)*grid;
      return(true);
     }

   //--- confluence(lo,hi,t) = min(1,(n_ref+n_round)/2); refs.py:145-166
   double Confluence(const double lo,const double hi,const double A) const
     {
      if(!(A>0.0))
         return(0.0);
      double half=0.5*width_atr*A;
      double px[];
      int n=LevelsAt(px);
      int n_ref=0;
      for(int i=0;i<n;i++)
         if((px[i]-half)<=hi && (px[i]+half)>=lo)
            n_ref++;
      double cen=0.5*(lo+hi);
      double g0,g1;
      int n_round=0;
      if(RoundNear(cen,g0,g1))
        {
         if((g0-half)<=hi && (g0+half)>=lo) n_round=1;
         if(n_round==0 && (g1-half)<=hi && (g1+half)>=lo) n_round=1;
        }
      return(MathMin(1.0,(n_ref+n_round)/2.0));
     }
  };

//+------------------------------------------------------------------+
//| PaZoneState - common._fresh_state() (:339-352).  None -> -1,     |
//| side None -> 0 (Python `x or +1` -> `x!=0?x:+1`).                |
//+------------------------------------------------------------------+
struct PaZoneState
  {
   int               touches;
   int               last_touch;     // -1 = None
   int               n_respected;
   int               n_reclaims;
   int               broken;         // broken bar idx, -1 = None
   int               role_flip;
   int               broken_side;    // 0 = None
   int               pending_from;   // -1 = None
   int               pending_until;
   int               approach_side;  // 0 = None
   int               flip_deadline;

   void              Reset()
     {
      touches=0; last_touch=-1; n_respected=0; n_reclaims=0;
      broken=-1; role_flip=0; broken_side=0;
      pending_from=-1; pending_until=-1; approach_side=0;
      flip_deadline=-1;
     }
  };

//+------------------------------------------------------------------+
//| CPaZone - one zone: geometry/quality step histories + the two    |
//| state tracks (st = pass state; sx = shadow/replay read state).   |
//+------------------------------------------------------------------+
class CPaZone
  {
public:
   int               zid;
   int               kind;        // ENUM_PA_ZK
   int               scale;       // ENUM_PA_SCALE
   int               born_idx;
   int               created_idx;
   int               end_idx;
   bool              live;
   //--- geometry step history (geom_idx/geom_hist)
   int               geom_t[];
   double            geom_lo[];
   double            geom_hi[];
   //--- quality step history (qual_idx/qual_hist)
   int               qual_t[];
   double            qual_v[];
   //--- the two state tracks
   PaZoneState       st;             // pass state (lifecycle)
   PaZoneState       sx;             // shadow replay state (reads)
   bool              sx_init;
   //--- meta
   int               m_n_members;
   int               m_anchor;
   double            m_level;
   double            m_poc;
   int               m_base_end;
   int               m_nb;
   int               m_k;
   string            m_slot;           // ref_zones retirement slot

                     CPaZone(void)
     {
      zid=0; kind=0; scale=0; born_idx=0; created_idx=0; end_idx=0;
      live=true;
      st.Reset();
      sx.Reset();
      sx_init=false;
      m_n_members=0; m_anchor=-1; m_level=0.0; m_poc=0.0;
      m_base_end=-1; m_nb=0; m_k=0; m_slot="";
     }

   //--- set_band / add_quality: append only when the value moved by more
   //--- than 1e-12 (Zone.set_band / add_quality, common.py:209-218)
   void SetGeom(const int t,const double lo,const double hi)
     {
      int n=ArraySize(geom_t);
      if(n>0 && MathAbs(lo-geom_lo[n-1])<=1e-12 &&
         MathAbs(hi-geom_hi[n-1])<=1e-12)
         return;
      ArrayResize(geom_t,n+1);
      ArrayResize(geom_lo,n+1);
      ArrayResize(geom_hi,n+1);
      geom_t[n]=t; geom_lo[n]=lo; geom_hi[n]=hi;
     }

   void AddQuality(const int t,const double q)
     {
      int n=ArraySize(qual_t);
      if(n>0 && MathAbs(q-qual_v[n-1])<=1e-12)
         return;
      ArrayResize(qual_t,n+1);
      ArrayResize(qual_v,n+1);
      qual_t[n]=t; qual_v[n]=q;
     }

   //--- band_at(t): last entry with geom_t <= t, clamped to index 0
   void BandAt(const int t,double &lo,double &hi) const
     {
      int n=ArraySize(geom_t);
      int k=0;
      for(int i=0;i<n;i++)
        {
         if(geom_t[i]<=t)
            k=i;
         else
            break;
        }
      lo=geom_lo[k]; hi=geom_hi[k];
     }

   double QualityAt(const int t) const
     {
      int n=ArraySize(qual_t);
      int k=0;
      for(int i=0;i<n;i++)
        {
         if(qual_t[i]<=t)
            k=i;
         else
            break;
        }
      return(qual_v[k]);
     }
  };

//+------------------------------------------------------------------+
//| view = common.ZoneView equivalent                                |
//+------------------------------------------------------------------+
struct PaZoneView
  {
   int               zid;
   int               kind;
   int               scale;
   double            lo;
   double            hi;
   double            strength;
   int               born_idx;
   int               touches;
   bool              fresh;
   int               n_respected;
   int               broken_idx;
   int               role_flip;
   int               age;
   int               last_touch;
   double            quality;
   int               approach_side;
   int               end_idx;
   double            meta_level;
   double            salience;    // SF02 hook (LEAD R1): real score TBD;
                                  // until then SalienceOf returns strength
  };

//+------------------------------------------------------------------+
//| CPaGenBase - common.ZoneGen machinery: _on_bar (virtual),        |
//| _step_all (pass track), shadow stepping (replay track), views.   |
//+------------------------------------------------------------------+
class CPaGenBase
  {
public:
   string            m_name;
   int               m_scale_default;
   double            m_qual_ref;
   //--- cfg (common.DEFAULTS + per-gen)
   double            cfg_break_atr;
   int               cfg_min_touch_sep;
   double            cfg_resp_move_atr;
   int               cfg_resp_window;
   int               cfg_reclaim_bars;
   int               cfg_fresh_bars;
   int               cfg_max_age_bars;
   int               cfg_break_keep_bars;
   double            cfg_arm_near_atr;
   double            cfg_arm_dedupe_atr;
   int               cfg_arm_max;
   int               cfg_arm_topk;     // SF02 hook: top-k armed per side by
                                       // salience; 0 = off (parity default)
   int               cfg_salience_mode;// 0 = salience := strength (parity
                                       // default); 1 = SF02 a-priori score
                                       // (AUTOPSY_PLAN A3 formula)
   double            cfg_max_width_atr;
   //--- universe
   CPaZone          *m_zones[];
   CPaZone          *m_live[];
   //--- pass bookkeeping: _sorted snapshot, _pending, _warm
   double            s_lo[];
   int               s_zid[];
   int               m_pending[];      // indices into m_zones
   int               warm_zid[];
   int               warm_exp[];
   int               m_t_now;
   int               m_reindex_every;

                     CPaGenBase(void)
                     {
                      m_scale_default=PA_SC_MICRO;
                      m_qual_ref=1.0;
                      cfg_break_atr=PA_BREAK_ATR;
                      cfg_min_touch_sep=PA_MIN_TOUCH_SEP;
                      cfg_resp_move_atr=PA_RESP_MOVE_ATR;
                      cfg_resp_window=PA_RESP_WINDOW;
                      cfg_reclaim_bars=PA_RECLAIM_BARS;
                      cfg_fresh_bars=PA_FRESH_BARS;
                      cfg_max_age_bars=PA_MAX_AGE_BARS;
                      cfg_break_keep_bars=PA_BREAK_KEEP_BARS;
                      cfg_arm_near_atr=PA_ARM_NEAR_ATR;
                      cfg_arm_dedupe_atr=PA_ARM_DEDUPE_ATR;
                      cfg_arm_max=PA_ARM_MAX;
                      cfg_arm_topk=0;        // off until SF02 defines salience
                      cfg_salience_mode=0;   // 0 = strength (parity default)
                      cfg_max_width_atr=PA_MAX_WIDTH_ATR;
                      m_t_now=-1;
                      m_reindex_every=256;
                     }

   virtual          ~CPaGenBase(void)
     {
      for(int i=0;i<ArraySize(m_zones);i++)
         if(CheckPointer(m_zones[i])==POINTER_DYNAMIC)
            delete m_zones[i];
     }

   //--- context hooks supplied by the facade (implemented by CPaGenCtx
   //--- once CPaCtx is declared - it sits below in this file)
   virtual void      OnBar(const int t)=0;   // _on_bar hook

   //--- _new_zone
   CPaZone          *NewZone(const int kind,const int scale,const int born,
                            const int created,const double lo,const double hi,
                            const double quality)
     {
      return(NewZoneEnd(kind,scale,born,created,lo,hi,quality,
                        born+cfg_max_age_bars));
     }

   CPaZone          *NewZoneEnd(const int kind,const int scale,const int born,
                               const int created,const double lo,const double hi,
                               const double quality,const int end_idx)
     {
      CPaZone *z=new CPaZone();
      int n=ArraySize(m_zones);
      z.zid=n+1;
      z.kind=kind; z.scale=scale;
      z.born_idx=born; z.created_idx=created; z.end_idx=end_idx;
      z.SetGeom(created,lo,hi);
      z.AddQuality(created,quality);
      ArrayResize(m_zones,n+1);
      m_zones[n]=z;
      int nl=ArraySize(m_live);
      ArrayResize(m_live,nl+1);
      m_live[nl]=z;
      int np=ArraySize(m_pending);
      ArrayResize(m_pending,np+1);
      m_pending[np]=n;          // store index into m_zones
      return(z);
     }

   //--- _step_zone (common.py:459-532) shared by pass (replay=false) and
   //--- shadow (replay=true).  The state struct is copied in/out so no
   //--- member-by-reference binding is needed.
   void StepZone(CPaZone *z,const int j,const PaBar &bar,const double A,
                 const bool ok,const bool replay)
     {
      //--- common.py:455 — skip when ATR missing/non-positive or before born
      if(!ok || !(A>0.0) || j<z.born_idx)
         return;
      PaZoneState s;
      if(replay)
         s=z.sx;
      else
         s=z.st;
      double zlo,zhi;
      z.BandAt(j,zlo,zhi);
      double h=bar.h,l=bar.l,c=bar.c;
      double brk=cfg_break_atr*A;
      //--- response to a previous touch (common.py:462-473)
      if(s.pending_from>=0 && j>=s.pending_from)
        {
         if(s.broken>=0)
           {
            s.pending_from=-1; s.pending_until=-1;
           }
         else if(j<=s.pending_until)
           {
            if(s.approach_side==-1 && c<=zlo-cfg_resp_move_atr*A)
              {
               s.n_respected++;
               s.pending_from=-1; s.pending_until=-1;
              }
            else if(s.approach_side==+1 && c>=zhi+cfg_resp_move_atr*A)
              {
               s.n_respected++;
               s.pending_from=-1; s.pending_until=-1;
              }
           }
         else
           {
            s.pending_from=-1; s.pending_until=-1;
           }
        }
      //--- break / reclaim / flip (common.py:481-510)
      if(s.broken<0)
        {
         int side=s.approach_side;
         bool broke=false;
         if(side==-1)
            broke=(c>zhi+brk);
         else if(side==+1)
            broke=(c<zlo-brk);
         if(j>z.born_idx && broke)
           {
            s.broken=j;
            s.broken_side=side;
            s.pending_from=-1; s.pending_until=-1;
            s.flip_deadline=j+cfg_reclaim_bars;
            if(!replay)
              {
               if(j+cfg_break_keep_bars<z.end_idx)
                  z.end_idx=j+cfg_break_keep_bars;
              }
           }
        }
      else
        {
         if((zlo-brk)<=c && c<=(zhi+brk) && j<=s.flip_deadline)
           {
            s.broken=-1;
            s.n_reclaims++;
           }
         else if(j>s.flip_deadline && s.role_flip==0)
           {
            int side=(s.broken_side!=0) ? s.broken_side : +1;
            if((side<0 && c>zhi+brk) || (side>0 && c<zlo-brk))
              {
               s.role_flip=1;
               s.broken=-1;
               s.approach_side=-side;
              }
           }
        }
      //--- touch episodes (common.py:512-528)
      bool touched=(l<=zhi && h>=zlo);
      if(touched)
        {
         if(s.last_touch<0 || (j-s.last_touch)>=cfg_min_touch_sep)
           {
            s.touches++;
            s.last_touch=j;
            double prev_c=(j==0) ? c : PrevClose(j);
            if(prev_c<zlo)
               s.approach_side=-1;
            else if(prev_c>zhi)
               s.approach_side=+1;
            else if(s.approach_side==0)
               s.approach_side=1;
            s.pending_from=j+1;
            s.pending_until=j+cfg_resp_window;
            if(!replay)
               WarmSet(z.zid,j+cfg_resp_window+1);
           }
        }
      if(replay)
         z.sx=s;
      else
         z.st=s;
     }

   void WarmSet(const int zid,const int exp)
     {
      int n=ArraySize(warm_zid);
      for(int i=0;i<n;i++)
         if(warm_zid[i]==zid)
           {
            warm_exp[i]=exp;
            return;
           }
      ArrayResize(warm_zid,n+1);
      ArrayResize(warm_exp,n+1);
      warm_zid[n]=zid; warm_exp[n]=exp;
     }

   void WarmDel(const int zid)
     {
      int n=ArraySize(warm_zid);
      for(int i=0;i<n;i++)
         if(warm_zid[i]==zid)
           {
            for(int k=i;k<n-1;k++)
              {
               warm_zid[k]=warm_zid[k+1];
               warm_exp[k]=warm_exp[k+1];
              }
            ArrayResize(warm_zid,n-1);
            ArrayResize(warm_exp,n-1);
            return;
           }
     }

   bool IsLive(const int zid)
     {
      for(int i=0;i<ArraySize(m_live);i++)
         if(m_live[i].zid==zid)
            return(true);
      return(false);
     }

   //--- _retire
   void Retire(CPaZone *z,const int idx)
     {
      if(idx<z.end_idx)
         z.end_idx=idx;
      z.live=false;
      for(int i=0;i<ArraySize(m_live);i++)
         if(m_live[i].zid==z.zid)
           {
            for(int k=i;k<ArraySize(m_live)-1;k++)
               m_live[k]=m_live[k+1];
            ArrayResize(m_live,ArraySize(m_live)-1);
            break;
           }
      WarmDel(z.zid);
     }

   //--- _reindex: _sorted = live zones sorted by (band_at(t).lo, zid);
   //--- _pending cleared
   void Reindex(const int t)
     {
      int nl=ArraySize(m_live);
      ArrayResize(s_lo,nl);
      ArrayResize(s_zid,nl);
      for(int i=0;i<nl;i++)
        {
         double lo,hi;
         m_live[i].BandAt(t,lo,hi);
         s_lo[i]=lo;
         s_zid[i]=m_live[i].zid;
        }
      //--- sort by (lo, zid) ascending - insertion sort
      for(int i=1;i<nl;i++)
        {
         double vl=s_lo[i];
         int vz=s_zid[i];
         int j=i-1;
         while(j>=0 && (s_lo[j]>vl || (s_lo[j]==vl && s_zid[j]>vz)))
           {
            s_lo[j+1]=s_lo[j];
            s_zid[j+1]=s_zid[j];
            j--;
           }
         s_lo[j+1]=vl;
         s_zid[j+1]=vz;
        }
      ArrayResize(m_pending,0);
     }

   //--- facade entry: one bar of the pass + shadow track.
   //--- Mirrors sf_ctx.run_pass loop body (:143-167).
   void StepBar(const int t,const PaBar &bar,const double A,const bool a_ok,
                const PaBar &bars[])
     {
      m_t_now=t;
      OnBar(t);
      //---------------- _step_all (pass track) ----------------
      if(a_ok && A>0.0)
        {
         double pad=A*cfg_break_atr+1e-9;
         double lo_b=bar.l,hi_b=bar.h;
         double Lo=lo_b-pad,Hi=hi_b+pad;
         //--- ids via the _sorted snapshot (same scan window as Python)
         int ids[];
         int nid=0;
         int ns=ArraySize(s_lo);
         //--- k0 = bisect_left(arr, (Lo - max_width*A, -1))
         int k0=0;
         while(k0<ns && s_lo[k0]<Lo-cfg_max_width_atr*A)
            k0++;
         for(int k=k0;k<ns;k++)
           {
            if(s_lo[k]>Hi)
               break;
            int zid=s_zid[k];
            CPaZone *z=FindLive(zid);
            if(z==NULL)
               continue;
            double zlo,zhi;
            z.BandAt(t,zlo,zhi);
            if(zhi+pad>=Lo && zlo-pad<=Hi)
              {
               ArrayResize(ids,nid+1);
               ids[nid]=zid; nid++;
              }
           }
         //--- _pending (created since last reindex): band +- pad vs raw range
         for(int k=0;k<ArraySize(m_pending);k++)
           {
            CPaZone *z=m_zones[m_pending[k]];
            double zlo,zhi;
            z.BandAt(t,zlo,zhi);
            if(zhi+pad>=lo_b && zlo-pad<=hi_b)
              {
               bool dup=false;
               for(int q=0;q<nid;q++)
                  if(ids[q]==z.zid) { dup=true; break; }
               if(!dup)
                 {
                  ArrayResize(ids,nid+1);
                  ids[nid]=z.zid; nid++;
                 }
              }
           }
         //--- _warm (pending-response zones): step until expiry
         for(int k=ArraySize(warm_zid)-1;k>=0;k--)
           {
            if(t<=warm_exp[k])
              {
               bool dup=false;
               for(int q=0;q<nid;q++)
                  if(ids[q]==warm_zid[k]) { dup=true; break; }
               if(!dup)
                 {
                  ArrayResize(ids,nid+1);
                  ids[nid]=warm_zid[k]; nid++;
                 }
              }
            else
              {
               WarmDel(warm_zid[k]);
              }
           }
         //--- step each id: t >= born && t >= created (common.py:433)
         for(int q=0;q<nid;q++)
           {
            CPaZone *z=FindLive(ids[q]);
            if(z==NULL || t<z.born_idx || t<z.created_idx)
               continue;
            StepZone(z,t,bar,A,a_ok,false);
           }
         //--- retire heap: pop while end < t -> retire if end_idx <= t
         //--- (equivalent form: retire every live zone with end_idx < t)
         for(int i=ArraySize(m_live)-1;i>=0;i--)
           {
            CPaZone *z=m_live[i];
            if(z.end_idx<t)
               Retire(z,z.end_idx);
           }
         if(t%m_reindex_every==0)
            Reindex(t);
        }
      //---------------- shadow track (replay semantics) ----------------
      //--- sf_ctx:151-166 - new zones backfill [born, t-1], then every live
      //--- zone steps bar t.  Lazy sx_init covers both cases.
      for(int i=ArraySize(m_live)-1;i>=0;i--)
        {
         CPaZone *z=m_live[i];
         if(!z.sx_init)
           {
            z.sx_init=true;
            for(int j=z.born_idx;j<t;j++)
               StepZone(z,j,bars[j],AtrAt(j),AtrOk(j),true);
           }
         if(t>=z.born_idx)
            StepZone(z,t,bar,A,a_ok,true);
        }
     }

   //--- strength v0 on a state track (common._strength :544-567)
   double Strength(CPaZone *z,const int t,const double A,const PaZoneState &s)
     {
      double s_touch=MathMin(1.0,s.touches/PA_TOUCH_FULL);
      double s_resp=MathMin(1.0,s.n_respected/PA_RESP_FULL);
      double s_rec=(s.last_touch<0) ? 0.0 : MathExp(-(t-s.last_touch)/PA_REC_HALF_LIFE);
      double s_age=MathMin(1.0,MathMax(0,t-z.born_idx)/PA_AGE_FULL);
      double s_scale=PaScaleScore(z.scale,PA_SCALE_MICRO,PA_SCALE_MESO,PA_SCALE_MACRO);
      double s_role=(s.role_flip!=0) ? 1.0 : 0.0;
      double zlo,zhi;
      z.BandAt(t,zlo,zhi);
      double s_ref=RefConfluence(zlo,zhi,A);
      double s_qual=(m_qual_ref>0.0) ? MathMin(1.0,z.QualityAt(t)/m_qual_ref) : 0.0;
      return(PA_W_TOUCH*s_touch+PA_W_RESP*s_resp+PA_W_REC*s_rec
             +PA_W_AGE*s_age+PA_W_SCALE*s_scale+PA_W_ROLE*s_role
             +PA_W_REF*s_ref+PA_W_QUAL*s_qual);
     }

   //--- SF02 salience (LEAD_RULINGS R1 item 3).  Default: salience :=
   //--- strength so arming order and parity output are unchanged.
   //--- cfg_salience_mode==1 enables the SF02 a-priori score - the real
   //--- implementation sits in CPaGenCtx (needs the bound CPaCtx).
   virtual double    SalienceOf(CPaZone *z,const int t,const double strength)
     {
      return(strength);
     }

   //--- views_at(t, arm) equivalent - fills views[] sorted (-S, zid);
   //--- arm applies arm_zones (broken zones never armed).
   int ViewsAt(const int t,const double A,const bool a_ok,const double close,
               const bool arm,PaZoneView &views[])
     {
      ArrayResize(views,0);
      if(!a_ok || !(A>0.0))
         return(0);
      int nv=0;
      for(int i=0;i<ArraySize(m_live);i++)
        {
         CPaZone *z=m_live[i];
         if(t<z.created_idx || t<z.born_idx || t>z.end_idx)
            continue;
         if(!z.sx_init)
            continue;
         double S=Strength(z,t,A,z.sx);
         double zlo,zhi;
         z.BandAt(t,zlo,zhi);
         bool fresh=(z.sx.broken<0 &&
                     (z.sx.last_touch<0 || (t-z.sx.last_touch)>cfg_fresh_bars));
         ArrayResize(views,nv+1);
         views[nv].zid=z.zid;
         views[nv].kind=z.kind;
         views[nv].scale=z.scale;
         views[nv].lo=zlo; views[nv].hi=zhi;
         views[nv].strength=S;
         views[nv].born_idx=z.born_idx;
         views[nv].touches=z.sx.touches;
         views[nv].fresh=fresh;
         views[nv].n_respected=z.sx.n_respected;
         views[nv].broken_idx=z.sx.broken;
         views[nv].role_flip=z.sx.role_flip;
         views[nv].age=t-z.born_idx;
         views[nv].last_touch=z.sx.last_touch;
         views[nv].quality=z.QualityAt(t);
         views[nv].approach_side=z.sx.approach_side;
         views[nv].end_idx=z.end_idx;
         views[nv].meta_level=z.m_level;
         views[nv].salience=SalienceOf(z,t,S);
         nv++;
        }
      //--- sort by (-strength, zid)
      for(int i=1;i<nv;i++)
        {
         PaZoneView v=views[i];
         int j=i-1;
         while(j>=0 && (views[j].strength<v.strength ||
               (views[j].strength==v.strength && views[j].zid>v.zid)))
           {
            views[j+1]=views[j];
            j--;
           }
         views[j+1]=v;
        }
      if(!arm)
         return(nv);
      //--- SF02 hook: top-k per side ranks by SALIENCE, not strength
      if(cfg_arm_topk>0)
        {
         for(int i=1;i<nv;i++)
           {
            PaZoneView v=views[i];
            int j=i-1;
            while(j>=0 && (views[j].salience<v.salience ||
                  (views[j].salience==v.salience && views[j].zid>v.zid)))
              {
               views[j+1]=views[j];
               j--;
              }
            views[j+1]=v;
           }
        }
      //--- arm_zones (common.py:627-651): near, dedupe by center, cap 6,
      //--- broken never armed
      double near=cfg_arm_near_atr*A;
      double dedupe=cfg_arm_dedupe_atr*A;
      PaZoneView tmp[];
      ArrayResize(tmp,nv);
      for(int i=0;i<nv;i++)
         tmp[i]=views[i];
      int m=0;
      int n_up=0,n_dn=0;      // SF02 top-k per side counters
      ArrayResize(views,0);
      for(int i=0;i<nv && m<cfg_arm_max;i++)
        {
         if(tmp[i].broken_idx>=0)
            continue;
         double cen=0.5*(tmp[i].lo+tmp[i].hi);
         if(MathAbs(cen-close)>near)
            continue;
         bool dup=false;
         for(int q=0;q<m;q++)
            if(MathAbs(cen-0.5*(views[q].lo+views[q].hi))<dedupe)
              { dup=true; break; }
         if(dup)
            continue;
         if(cfg_arm_topk>0)
           {
            int sd=(cen>close)?1:(cen<close)?-1:0;
            if(sd>0 && n_up>=cfg_arm_topk) continue;
            if(sd<0 && n_dn>=cfg_arm_topk) continue;
            if(sd>0) n_up++; else if(sd<0) n_dn++;
           }
         ArrayResize(views,m+1);
         views[m]=tmp[i];
         m++;
        }
      return(m);
     }

protected:
   CPaZone          *FindLive(const int zid)
     {
      for(int i=0;i<ArraySize(m_live);i++)
         if(m_live[i].zid==zid)
            return(m_live[i]);
      return(NULL);
     }

   //--- context access implemented by the derived generator (it holds the
   //--- facade pointer): ATR at bar j, ATR valid, close of bar j-1, refs
   virtual double    AtrAt(const int j)=0;
   virtual bool      AtrOk(const int j)=0;
   virtual double    PrevClose(const int j)=0;
   virtual double    RefConfluence(const double lo,const double hi,const double A)=0;
  };

//+------------------------------------------------------------------+
//| CPaCtx - common.ZoneContext: bars + H1 + ATR alignment + pivots  |
//| + RefBook.  H1 bars are aggregated from the SAME M5 series (12   |
//| complete M5 bars per server-hour bucket) - never a second feed.  |
//+------------------------------------------------------------------+
class CPaCtx
  {
public:
   PaBar             b[];
   int               n;
   double            pip;
   string            symbol;
   //--- H1 aggregated from M5 (complete 12-bar buckets only)
   long              h1_t[];
   double            h1_o[];
   double            h1_h[];
   double            h1_l[];
   double            h1_c[];
   int               n_h1;
   //--- ATR14(H1) aligned (common.AtrH1): newest H1 bucket whose close
   //--- (h1_t+3600) <= the M5 bar close (t+300)
   double            atr_h1[];
   bool              atr_h1_ok[];
   long              h1_close[];
   int               h1_idx[];     // per M5 bar
   double            atr_m5[];
   bool              atr_m5_ok[];
   CPaRefs           refs;
   //--- lazy pivot caches
   PaPivot           piv3[];
   bool              piv3_done;
   PaH1Pivot         h1p2[];
   bool              h1p2_done;
   //--- raw H1 pivot table (lag 2) kept for KDE weight calc
   PaPivot           h1raw2[];
   //--- H4 aggregated from M5 (complete 48-bar buckets only) - feeds the
   //--- SF02 salience pivot_conf term (confirmed +-2 H4 fractals).  Raw
   //--- pivot rows carry .confirm as an H4 index; confirmation at M5 bar
   //--- t iff h4_close[conf] <= b[t].t+300 (same rule as the h1p2 map).
   long              h4_t[];
   double            h4_o[];
   double            h4_h[];
   double            h4_l[];
   double            h4_c[];
   int               n_h4;
   long              h4_close[];
   PaPivot           h4raw2[];
   bool              h4p_done;
   //--- incremental-extension watermarks for PushBar (live bars):
   //--- piv3_scan   = next M5 source index j to pivot-test (j+k<=n-1)
   //--- h1raw_scan  = next H1 index to test (j+2<=n_h1-1)
   //--- h4raw_scan  = next H4 index to test (j+2<=n_h4-1)
   //--- h1p2_pend   = h1raw2 rows already emitted to h1p2 (FIFO; a row
   //---   whose m5_confirm is beyond the book blocks the tail - correct:
   //---   confirm times are non-decreasing so later rows map even later)
   int               piv3_scan;
   int               h1raw_scan;
   int               h4raw_scan;
   int               h1p2_pend;
   double            atr_m5_seed;
   double            atr_h1_seed;

                     CPaCtx(void)
     {
      n=0; n_h1=0; n_h4=0; pip=0.0001; symbol="";
      piv3_done=false; h1p2_done=false; h4p_done=false;
      piv3_scan=PA_L1_PIVOT_LAG; h1raw_scan=PA_KD_PIV_H1;
      h4raw_scan=PA_KD_PIV_H1; h1p2_pend=0;
      atr_m5_seed=0.0; atr_h1_seed=0.0;
     }

   //--- aggregate complete H1 buckets from the M5 array (12 M5 bars at the
   //--- exact :00,:05,... slots = the loader's 60-complete-M1 rule)
   int BuildH1()
     {
      n_h1=0;
      ArrayResize(h1_t,0);
      ArrayResize(h1_o,0);
      ArrayResize(h1_h,0);
      ArrayResize(h1_l,0);
      ArrayResize(h1_c,0);
      int i=0;
      while(i<n)
        {
         long key=b[i].t/3600;
         int j=i;
         int cnt=0;
         bool aligned=true;
         while(j<n && b[j].t/3600==key)
           {
            if(b[j].t!=key*3600+(long)cnt*300)
               aligned=false;
            cnt++;
            j++;
           }
         if(cnt==12 && aligned)
           {
            double hh=b[i].h,ll=b[i].l;
            for(int k=i+1;k<j;k++)
              {
               if(b[k].h>hh) hh=b[k].h;
               if(b[k].l<ll) ll=b[k].l;
              }
            int m=n_h1;
            ArrayResize(h1_t,m+1);
            ArrayResize(h1_o,m+1);
            ArrayResize(h1_h,m+1);
            ArrayResize(h1_l,m+1);
            ArrayResize(h1_c,m+1);
            h1_t[m]=key*3600;
            h1_o[m]=b[i].o;
            h1_h[m]=hh;
            h1_l[m]=ll;
            h1_c[m]=b[j-1].c;
            n_h1=m+1;
           }
         i=j;
        }
      return(n_h1);
     }

   //--- aggregate complete H4 buckets from the M5 array (48 M5 bars at
   //--- the exact :00,:05,... slots - same rule as pa_data.resample H4
   //--- which demands 240 contiguous M1 bars per bucket)
   int BuildH4()
     {
      n_h4=0;
      ArrayResize(h4_t,0);
      ArrayResize(h4_o,0);
      ArrayResize(h4_h,0);
      ArrayResize(h4_l,0);
      ArrayResize(h4_c,0);
      int i=0;
      while(i<n)
        {
         long key=b[i].t/14400;
         int j=i;
         int cnt=0;
         bool aligned=true;
         while(j<n && b[j].t/14400==key)
           {
            if(b[j].t!=key*14400+(long)cnt*300)
               aligned=false;
            cnt++;
            j++;
           }
         if(cnt==48 && aligned)
           {
            double hh=b[i].h,ll=b[i].l;
            for(int k=i+1;k<j;k++)
              {
               if(b[k].h>hh) hh=b[k].h;
               if(b[k].l<ll) ll=b[k].l;
              }
            int m=n_h4;
            ArrayResize(h4_t,m+1);
            ArrayResize(h4_o,m+1);
            ArrayResize(h4_h,m+1);
            ArrayResize(h4_l,m+1);
            ArrayResize(h4_c,m+1);
            h4_t[m]=key*14400;
            h4_o[m]=b[i].o;
            h4_h[m]=hh;
            h4_l[m]=ll;
            h4_c[m]=b[j-1].c;
            n_h4=m+1;
           }
         i=j;
        }
      return(n_h4);
     }

   bool Init(const PaBar &bars[],const int n_,const double pip_,const string sym)
     {
      n=n_;
      pip=pip_;
      symbol=sym;
      piv3_scan=PA_L1_PIVOT_LAG; h1raw_scan=PA_KD_PIV_H1;
      h4raw_scan=PA_KD_PIV_H1; h1p2_pend=0;
      piv3_done=false; h1p2_done=false; h4p_done=false;
      atr_m5_seed=0.0; atr_h1_seed=0.0;
      ArrayResize(b,n);
      for(int i=0;i<n;i++)
         b[i]=bars[i];
      refs.Init(pip);
      BuildH1();
      BuildH4();
      ArrayResize(h4_close,n_h4);
      for(int i=0;i<n_h4;i++)
         h4_close[i]=h4_t[i]+14400;
      //--- ATR14(H1) + alignment
      PaWilderAtr(h1_h,h1_l,h1_c,n_h1,14,atr_h1,atr_h1_ok);
      ArrayResize(h1_close,n_h1);
      for(int i=0;i<n_h1;i++)
         h1_close[i]=h1_t[i]+3600;
      ArrayResize(h1_idx,n);
      for(int t=0;t<n;t++)
        {
         long mc=b[t].t+300;
         //--- bisect right: newest h1_close <= mc
         int lo=0,hi=n_h1;
         while(lo<hi)
           {
            int mid=(lo+hi)/2;
            if(h1_close[mid]<=mc)
               lo=mid+1;
            else
               hi=mid;
           }
         h1_idx[t]=lo-1;
        }
      //--- ATR14(M5)
      double hh[],ll[],cc[];
      ArrayResize(hh,n); ArrayResize(ll,n); ArrayResize(cc,n);
      for(int i=0;i<n;i++)
        {
         hh[i]=b[i].h; ll[i]=b[i].l; cc[i]=b[i].c;
        }
      PaWilderAtr(hh,ll,cc,n,14,atr_m5,atr_m5_ok);
      return(true);
     }

   //--- live extension: append one CLOSED M5 bar and extend every
   //--- derived array causally (H1 buckets, ATRs, h1_idx, pivot caches).
   //--- Equivalent to re-running Init on the longer book, O(1) per bar.
   int PushBar(const PaBar &nb)
     {
      int i=n;
      ArrayResize(b,n+1);
      b[i]=nb;
      n++;
      //--- ATR14(M5) incremental (wilder_atr: seed = mean(tr[:14]) at i=13,
      //--- then atr = (13*prev + tr)/14)
      ArrayResize(atr_m5,n);
      ArrayResize(atr_m5_ok,n);
      double tr;
      if(i==0)
         tr=nb.h-nb.l;
      else
         tr=MathMax(MathMax(nb.h-nb.l,MathAbs(nb.h-b[i-1].c)),
                    MathAbs(nb.l-b[i-1].c));
      if(i<13)
        {
         atr_m5[i]=0.0; atr_m5_ok[i]=false; atr_m5_seed+=tr;
        }
      else if(i==13)
        {
         atr_m5_seed+=tr;
         atr_m5[i]=atr_m5_seed/14.0; atr_m5_ok[i]=true;
        }
      else
        {
         //--- same arithmetic as wilder_atr: a*prev + (1-a)*tr (bit-exact)
         double a=13.0/14.0;
         atr_m5[i]=a*atr_m5[i-1]+(1.0-a)*tr; atr_m5_ok[i]=true;
        }
      //--- H1 bucket finalizes when the bar's hour differs from the
      //--- previous bar's (same completeness rule as BuildH1)
      if(i>0 && b[i].t/3600!=b[i-1].t/3600)
         H1Finalize(i-1);
      //--- H4 bucket finalizes at a 4h boundary (48-bar rule, BuildH4)
      if(i>0 && b[i].t/14400!=b[i-1].t/14400)
         H4Finalize(i-1);
      //--- h1_idx for the new bar: newest h1_close <= close time
      ArrayResize(h1_idx,n);
      {
       long mc=nb.t+300;
       int lo=0,hi=n_h1;
       while(lo<hi)
         {
          int mid=(lo+hi)/2;
          if(h1_close[mid]<=mc) lo=mid+1; else hi=mid;
         }
       h1_idx[i]=lo-1;
      }
      //--- M5 pivots: emit newly confirmable rows (j+k <= n-1).  When the
      //--- lazy full build has not run yet just advance the watermark -
      //--- Pivots3() will compute the whole table on first use.
      if(piv3_done)
        {
         while(piv3_scan<=n-1-PA_L1_PIVOT_LAG)
           {
            TestPivotBar(piv3_scan,PA_L1_PIVOT_LAG,piv3);
            piv3_scan++;
           }
        }
      else
         piv3_scan=n-PA_L1_PIVOT_LAG;
      return(i);
     }

   //--- test bar j as a +-k fractal on h/l arrays (PaConfirmedPivots row
   //--- rule: strict vs the LEFT k, non-strict vs the RIGHT k); append.
   void TestPivot(const double &hh[],const double &ll[],
                  const int j,const int k,PaPivot &out[])
     {
      int m=ArraySize(out);
      bool isH=true,isL=true;
      for(int q=j-k;q<j;q++)
        {
         if(!(hh[j]>hh[q])) isH=false;
         if(!(ll[j]<ll[q])) isL=false;
        }
      for(int q=j+1;q<=j+k;q++)
        {
         if(!(hh[j]>=hh[q])) isH=false;
         if(!(ll[j]<=ll[q])) isL=false;
        }
      if(isH)
        {
         ArrayResize(out,m+1);
         out[m].idx=j; out[m].price=hh[j]; out[m].side=+1; out[m].confirm=j+k;
         m++;
        }
      if(isL)
        {
         ArrayResize(out,m+1);
         out[m].idx=j; out[m].price=ll[j]; out[m].side=-1; out[m].confirm=j+k;
         m++;
        }
     }

   //--- same rule on the PaBar book (b[].h / b[].l)
   void TestPivotBar(const int j,const int k,PaPivot &out[])
     {
      int m=ArraySize(out);
      bool isH=true,isL=true;
      for(int q=j-k;q<j;q++)
        {
         if(!(b[j].h>b[q].h)) isH=false;
         if(!(b[j].l<b[q].l)) isL=false;
        }
      for(int q=j+1;q<=j+k;q++)
        {
         if(!(b[j].h>=b[q].h)) isH=false;
         if(!(b[j].l<=b[q].l)) isL=false;
        }
      if(isH)
        {
         ArrayResize(out,m+1);
         out[m].idx=j; out[m].price=b[j].h; out[m].side=+1; out[m].confirm=j+k;
         m++;
        }
      if(isL)
        {
         ArrayResize(out,m+1);
         out[m].idx=j; out[m].price=b[j].l; out[m].side=-1; out[m].confirm=j+k;
         m++;
        }
     }

   //--- an M5 hour bucket closed at bar `last`: keep it iff 12 bars at the
   //--- exact :00,:05,... slots (BuildH1 parity), then extend the H1 ATR,
   //--- h1_close, the raw H1 pivot table and the m5-mapped h1p2 rows.
   void H1Finalize(const int last)
     {
      long key=b[last].t/3600;
      int s=last;
      while(s>=0 && b[s].t/3600==key)
         s--;
      s++;
      int cnt=last-s+1;
      if(cnt!=12)
         return;                          // incomplete bucket -> dropped
      for(int q=0;q<12;q++)
         if(b[s+q].t!=key*3600+(long)q*300)
            return;                        // misaligned slot -> dropped
      int m=n_h1;
      ArrayResize(h1_t,m+1);
      ArrayResize(h1_o,m+1);
      ArrayResize(h1_h,m+1);
      ArrayResize(h1_l,m+1);
      ArrayResize(h1_c,m+1);
      double hh=b[s].h,ll=b[s].l;
      for(int q=s+1;q<=last;q++)
        {
         if(b[q].h>hh) hh=b[q].h;
         if(b[q].l<ll) ll=b[q].l;
        }
      h1_t[m]=key*3600;
      h1_o[m]=b[s].o;
      h1_h[m]=hh;
      h1_l[m]=ll;
      h1_c[m]=b[last].c;
      n_h1=m+1;
      //--- H1 ATR incremental
      ArrayResize(atr_h1,n_h1);
      ArrayResize(atr_h1_ok,n_h1);
      double tr=(m==0)?(h1_h[m]-h1_l[m])
                :MathMax(MathMax(h1_h[m]-h1_l[m],MathAbs(h1_h[m]-h1_c[m-1])),
                         MathAbs(h1_l[m]-h1_c[m-1]));
      if(m<13)
        {
         atr_h1[m]=0.0; atr_h1_ok[m]=false; atr_h1_seed+=tr;
        }
      else if(m==13)
        {
         atr_h1_seed+=tr;
         atr_h1[m]=atr_h1_seed/14.0; atr_h1_ok[m]=true;
        }
      else
        {
         double a=13.0/14.0;                 // wilder_atr arithmetic
         atr_h1[m]=a*atr_h1[m-1]+(1.0-a)*tr; atr_h1_ok[m]=true;
        }
      ArrayResize(h1_close,n_h1);
      h1_close[m]=h1_t[m]+3600;
      //--- H1 pivot watermark (lag PA_KD_PIV_H1=2 on the H1 series)
      if(h1p2_done)
        {
         while(h1raw_scan<=n_h1-1-PA_KD_PIV_H1)
           {
            TestPivot(h1_h,h1_l,h1raw_scan,PA_KD_PIV_H1,h1raw2);
            h1raw_scan++;
           }
         //--- map consumed raw pivots into M5 space (FIFO)
         while(h1p2_pend<ArraySize(h1raw2))
           {
            int conf=h1raw2[h1p2_pend].confirm;
            if(conf>=n_h1)
               break;
            long hc=h1_close[conf];
            int lo=0,hi=n;
            while(lo<hi)
              {
               int mid=(lo+hi)/2;
               if(b[mid].t+300>=hc) hi=mid; else lo=mid+1;
              }
            if(lo>=n)
               break;                       // m5_confirm still future
            int m5c=lo;
            lo=0; hi=n;
            while(lo<hi)
              {
               int mid=(lo+hi)/2;
               if(b[mid].t>=h1_t[h1raw2[h1p2_pend].idx]) hi=mid; else lo=mid+1;
              }
            int m=ArraySize(h1p2);
            ArrayResize(h1p2,m+1);
            h1p2[m].h1_idx=h1raw2[h1p2_pend].idx;
            h1p2[m].price =h1raw2[h1p2_pend].price;
            h1p2[m].side  =h1raw2[h1p2_pend].side;
            h1p2[m].m5_confirm=m5c;
            h1p2[m].m5_anchor =lo;
            h1p2_pend++;
           }
        }
      else
         h1raw_scan=n_h1-PA_KD_PIV_H1;
     }

   //--- an M5 4h bucket closed at bar `last`: keep it iff 48 bars at the
   //--- exact slots (BuildH4 parity), then extend h4_close and the raw
   //--- H4 pivot table (lag PA_KD_PIV_H1=2, same as sf_ctx h4piv).
   void H4Finalize(const int last)
     {
      long key=b[last].t/14400;
      int s=last;
      while(s>=0 && b[s].t/14400==key)
         s--;
      s++;
      int cnt=last-s+1;
      if(cnt!=48)
         return;                          // incomplete bucket -> dropped
      for(int q=0;q<48;q++)
         if(b[s+q].t!=key*14400+(long)q*300)
            return;                        // misaligned slot -> dropped
      int m=n_h4;
      ArrayResize(h4_t,m+1);
      ArrayResize(h4_o,m+1);
      ArrayResize(h4_h,m+1);
      ArrayResize(h4_l,m+1);
      ArrayResize(h4_c,m+1);
      double hh=b[s].h,ll=b[s].l;
      for(int q=s+1;q<=last;q++)
        {
         if(b[q].h>hh) hh=b[q].h;
         if(b[q].l<ll) ll=b[q].l;
        }
      h4_t[m]=key*14400;
      h4_o[m]=b[s].o;
      h4_h[m]=hh;
      h4_l[m]=ll;
      h4_c[m]=b[last].c;
      n_h4=m+1;
      ArrayResize(h4_close,n_h4);
      h4_close[m]=h4_t[m]+14400;
      //--- H4 pivot watermark (lag 2 on the H4 series)
      if(h4p_done)
        {
         while(h4raw_scan<=n_h4-1-PA_KD_PIV_H1)
           {
            TestPivot(h4_h,h4_l,h4raw_scan,PA_KD_PIV_H1,h4raw2);
            h4raw_scan++;
           }
        }
      else
         h4raw_scan=n_h4-PA_KD_PIV_H1;
     }

   //--- lazy build of the raw +-2 H4 pivot table (PushBar extends it
   //--- incrementally afterwards via the h4raw_scan watermark)
   int H4Pivots2()
     {
      if(h4p_done)
         return(ArraySize(h4raw2));
      PaConfirmedPivots(h4_h,h4_l,n_h4,PA_KD_PIV_H1,h4raw2);
      h4p_done=true;
      h4raw_scan=n_h4-PA_KD_PIV_H1;
      return(ArraySize(h4raw2));
     }

   //--- SF02 salience helper: is a CONFIRMED +-2 pivot (H1 or H4) known at
   //--- M5 bar t within `tol` of price `px`?  H1 rows use the precomputed
   //--- m5_confirm; H4 rows confirm iff h4_close[conf] <= b[t].t+300 -
   //--- identical to the h1p2 mapping rule (first M5 close >= bucket
   //--- close).  Both tables are emitted in non-decreasing confirm order,
   //--- so a backward scan can stop at the first confirmed row.
   bool PivotNear(const double px,const double tol,const int t)
     {
      int np=H1Pivots2();
      int i=np-1;
      while(i>=0 && h1p2[i].m5_confirm>t)
         i--;
      for(;i>=0;i--)
         if(MathAbs(h1p2[i].price-px)<=tol)
            return(true);
      int nq=H4Pivots2();
      long mc=(t>=0 && t<n) ? b[t].t+300 : -1;
      int j=nq-1;
      while(j>=0 && h4raw2[j].confirm<n_h4 && h4_close[h4raw2[j].confirm]>mc)
         j--;
      for(;j>=0;j--)
        {
         if(h4raw2[j].confirm>=n_h4)
            continue;                     // still unconfirmable tail
         if(MathAbs(h4raw2[j].price-px)<=tol)
            return(true);
        }
      return(false);
     }

   //--- ctx.a(t): ATR14(H1) known at close of M5 bar t
   double Atr(const int t)
     {
      if(t<0 || t>=n)
         return(0.0);
      int k=h1_idx[t];
      if(k<0 || k>=n_h1 || !atr_h1_ok[k])
         return(0.0);
      return(atr_h1[k]);
     }

   bool AtrOk(const int t)
     {
      if(t<0 || t>=n)
         return(false);
      int k=h1_idx[t];
      return(k>=0 && k<n_h1 && atr_h1_ok[k]);
     }

   double Close(const int j) { return(b[j].c); }
   double High(const int j)  { return(b[j].h); }
   double Low(const int j)   { return(b[j].l); }

   //--- ctx.pivots(3): confirmed +-3 M5 fractals (lazy; PushBar extends)
   int Pivots3()
     {
      if(!piv3_done)
        {
         double hh[],ll[];
         ArrayResize(hh,n); ArrayResize(ll,n);
         for(int i=0;i<n;i++)
           {
            hh[i]=b[i].h; ll[i]=b[i].l;
           }
         PaConfirmedPivots(hh,ll,n,PA_L1_PIVOT_LAG,piv3);
         piv3_done=true;
         piv3_scan=n-PA_L1_PIVOT_LAG;      // next confirmable source j
        }
      return(ArraySize(piv3));
     }

   //--- ctx.h1_pivots(2): +-2 H1 fractals mapped into M5 index space
   //--- (common.py:310-335): (h1_idx, price, side, m5_confirm, m5_anchor)
   int H1Pivots2()
     {
      if(h1p2_done)
         return(ArraySize(h1p2));
      PaConfirmedPivots(h1_h,h1_l,n_h1,PA_KD_PIV_H1,h1raw2);
      ArrayResize(h1p2,0);
      int m=0;
      int i;
      for(i=0;i<ArraySize(h1raw2);i++)
        {
         int conf=h1raw2[i].confirm;
         if(conf>=n_h1)
            break;
         long hc=h1_close[conf];
         //--- m5c = first M5 bar whose close >= hc (searchsorted left)
         int lo=0,hi=n;
         while(lo<hi)
           {
            int mid=(lo+hi)/2;
            if(b[mid].t+300>=hc)
               hi=mid;
            else
               lo=mid+1;
           }
         int m5c=lo;
         if(m5c>=n)
            break;                        // rest are even later - FIFO stop
         //--- m5a = first M5 bar with t >= h1_t[j]
         lo=0; hi=n;
         while(lo<hi)
           {
            int mid=(lo+hi)/2;
            if(b[mid].t>=h1_t[h1raw2[i].idx])
               hi=mid;
            else
               lo=mid+1;
           }
         int m5a=lo;
         ArrayResize(h1p2,m+1);
         h1p2[m].h1_idx=h1raw2[i].idx;
         h1p2[m].price=h1raw2[i].price;
         h1p2[m].side=h1raw2[i].side;
         h1p2[m].m5_confirm=m5c;
         h1p2[m].m5_anchor=m5a;
         m++;
        }
      h1p2_done=true;
      h1p2_pend=i;                        // h1raw2[0..i) already mapped
      h1raw_scan=n_h1-PA_KD_PIV_H1;       // next confirmable H1 source
      return(m);
     }
  };

//+------------------------------------------------------------------+
//| mid-level: binds a generator to the shared CPaCtx                |
//+------------------------------------------------------------------+
class CPaGenCtx : public CPaGenBase
  {
public:
   CPaCtx           *ctx;
   void              SetCtx(CPaCtx *c) { ctx=c; }
   virtual double    AtrAt(const int j)  { return(ctx.Atr(j)); }
   virtual bool      AtrOk(const int j)  { return(ctx.AtrOk(j)); }
   virtual double    PrevClose(const int j) { return(ctx.Close(j-1)); }
   //--- SF02 salience mode 1 - the a-priori score declared in
   //--- rounds/SF02/AUTOPSY_PLAN.md A3 (fixed weights, all causal at t):
   //---   1.0*n_respected + 1.0*pivot_conf + 0.5*round_conf
   //---   - 0.5*(width/ATR_H1) + 0.25*log(1+age_bars/96)
   //--- pivot_conf: a confirmed +-2 H1/H4 pivot within 0.5*ATR_H1 of a
   //--- zone edge; round_conf: zone mid within 0.25*ATR_H1 of a 25-pip
   //--- gridline.  n_respected/age read the sx replay state.
   virtual double    SalienceOf(CPaZone *z,const int t,const double strength)
     {
      if(cfg_salience_mode!=1 || ctx==NULL)
         return(strength);
      double A=ctx.Atr(t);
      if(!(A>0.0))
         return(strength);
      double zlo,zhi;
      z.BandAt(t,zlo,zhi);
      double mid=0.5*(zlo+zhi);
      double sc=(double)z.sx.n_respected;
      double ptol=0.5*A;
      if(ctx.PivotNear(zlo,ptol,t) || ctx.PivotNear(zhi,ptol,t))
         sc+=1.0;
      double grid=25.0*ctx.pip;
      if(grid>0.0)
        {
         double rem=MathMod(mid,grid);
         if(rem<0.0) rem+=grid;
         if(MathMin(rem,grid-rem)<=0.25*A)
            sc+=0.5;
        }
      sc-=0.5*((zhi-zlo)/A);
      sc+=0.25*MathLog(1.0+(double)(t-z.born_idx)/96.0);
      return(sc);
     }
   virtual double    RefConfluence(const double lo,const double hi,const double A)
     {
      return(ctx.refs.Confluence(lo,hi,A));
     }
  };

//+------------------------------------------------------------------+
//| line1_cluster (baseline) - line1_cluster_zones.py                |
//| confirmed +-3 M5 pivots absorbed into the nearest live "swing"   |
//| zone within link_atr, else a new 0.25A band.                     |
//+------------------------------------------------------------------+
class CPaGenLine1 : public CPaGenCtx
  {
public:
   int               m_next;
   int               m_npiv;

                     CPaGenLine1(void)
     {
      m_name="line1_cluster";
      m_scale_default=PA_SC_MICRO;
      m_qual_ref=2.0;
      cfg_max_age_bars=PA_MAX_AGE_BARS;
      m_next=0; m_npiv=0;
     }

   void              Prepare() { m_npiv=ctx.Pivots3(); }

   virtual void      OnBar(const int t)
     {
      double A=AtrAt(t);
      if(!(A>0.0))
         return;
      m_npiv=ctx.Pivots3();   // live: piv3 grows via CPaCtx::PushBar
      while(m_next<m_npiv && ctx.piv3[m_next].confirm<=t)
        {
         int j=ctx.piv3[m_next].idx;
         double price=ctx.piv3[m_next].price;
         m_next++;
         if(t-j>PA_L1_SCAN_BARS)
            continue;
         double w=PA_L1_WIDTH_ATR*A;
         double link=PA_L1_LINK_ATR*A;
         double max_w=PA_L1_MAX_W_ATR*A;
         double best_d=0.0;
         CPaZone *best=NULL;
         double bnlo=0.0,bnhi=0.0;
         for(int i=0;i<ArraySize(m_live);i++)
           {
            CPaZone *z=m_live[i];
            if(z.kind!=PA_ZK_SWING)
               continue;
            double zlo,zhi;
            z.BandAt(t,zlo,zhi);
            double nlo=MathMin(zlo,price-w/2.0);
            double nhi=MathMax(zhi,price+w/2.0);
            if(nhi-nlo>max_w+1e-12)
               continue;
            double d;
            if(price<zlo)      d=zlo-price;
            else if(price>zhi) d=price-zhi;
            else               d=0.0;
            if(d<=link+1e-12 && (best==NULL || d<best_d))
              {
               best_d=d; best=z; bnlo=nlo; bnhi=nhi;
              }
           }
         if(best!=NULL)
           {
            best.SetGeom(t,bnlo,bnhi);
            best.AddQuality(t,best.QualityAt(t)+1.0);
           }
         else
           {
            CPaZone *z=NewZone(PA_ZK_SWING,PA_SC_MICRO,j,t,
                               price-w/2.0,price+w/2.0,1.0);
            z.m_n_members=1; z.m_anchor=j;
           }
        }
     }
  };

//+------------------------------------------------------------------+
//| fractal_h1 - fractal_zones.py: +-2 H1 fractals qualified by      |
//| past-leg prominence, absorbed into "swing_h1" zones.             |
//+------------------------------------------------------------------+
class CPaGenFractal : public CPaGenCtx
  {
public:
   PaH1Pivot         piv[];
   int               m_npiv;
   int               m_next;
   int               m_src;   // ctx.h1p2 rows already qualified (live extension)

                     CPaGenFractal(void)
     {
      m_name="fractal_h1";
      m_scale_default=PA_SC_MESO;
      m_qual_ref=2.0;
      cfg_max_age_bars=PA_FR_MAX_AGE;
      m_next=0; m_npiv=0; m_src=0;
     }

   //--- _qualify (:67-92): past-leg prominence >= 0.40 x A(confirm);
   //--- stale guard m5c - m5a <= scan_bars
   void              Qualify(const int i)
     {
      PaH1Pivot p=ctx.h1p2[i];
      if(p.m5_confirm-p.m5_anchor>PA_FR_SCAN_BARS)
         return;
      double A=ctx.Atr(p.m5_confirm);
      if(!(A>0.0))
         return;
      int j=p.h1_idx;
      int j0=MathMax(0,j-PA_FR_PROM_LOOK);
      double leg;
      if(p.side>0)
        {
         double mn=ctx.h1_l[j0];
         for(int k=j0+1;k<=j;k++)
            if(ctx.h1_l[k]<mn) mn=ctx.h1_l[k];
         leg=p.price-mn;
        }
      else
        {
         double mx=ctx.h1_h[j0];
         for(int k=j0+1;k<=j;k++)
            if(ctx.h1_h[k]>mx) mx=ctx.h1_h[k];
         leg=mx-p.price;
        }
      if(leg>=PA_FR_PROM_ATR*A)
        {
         ArrayResize(piv,m_npiv+1);
         piv[m_npiv]=p;
         m_npiv++;
        }
     }
   //--- lazily qualify h1p2 rows appended by CPaCtx::PushBar (live parity
   //--- with a fresh Python run over the extended book)
   void              SyncPivots()
     {
      int nraw=ctx.H1Pivots2();
      while(m_src<nraw) { Qualify(m_src); m_src++; }
     }

   void              Prepare()
     {
      ArrayResize(piv,0);
      m_npiv=0; m_src=0;
      SyncPivots();
     }

   virtual void      OnBar(const int t)
     {
      double A=AtrAt(t);
      if(!(A>0.0))
         return;
      SyncPivots();   // live: h1p2 grows via CPaCtx::PushBar
      while(m_next<m_npiv && piv[m_next].m5_confirm<=t)
        {
         double price=piv[m_next].price;
         int anchor=piv[m_next].m5_anchor;
         m_next++;
         double w=PA_FR_WIDTH_ATR*A;
         double link=PA_FR_LINK_ATR*A;
         double max_w=PA_FR_MAX_W_ATR*A;
         double best_d=0.0;
         CPaZone *best=NULL;
         double bnlo=0.0,bnhi=0.0;
         for(int i=0;i<ArraySize(m_live);i++)
           {
            CPaZone *z=m_live[i];
            if(z.kind!=PA_ZK_SWING_H1)
               continue;
            double zlo,zhi;
            z.BandAt(t,zlo,zhi);
            double nlo=MathMin(zlo,price-w/2.0);
            double nhi=MathMax(zhi,price+w/2.0);
            if(nhi-nlo>max_w+1e-12)
               continue;
            double d;
            if(price<zlo)      d=zlo-price;
            else if(price>zhi) d=price-zhi;
            else               d=0.0;
            if(d<=link+1e-12 && (best==NULL || d<best_d))
              {
               best_d=d; best=z; bnlo=nlo; bnhi=nhi;
              }
           }
         if(best!=NULL)
           {
            best.SetGeom(t,bnlo,bnhi);
            best.AddQuality(t,best.QualityAt(t)+1.0);
           }
         else
           {
            CPaZone *z=NewZoneEnd(PA_ZK_SWING_H1,PA_SC_MESO,anchor,t,
                                  price-w/2.0,price+w/2.0,1.0,
                                  anchor+PA_FR_MAX_AGE);
            z.m_n_members=1;
           }
        }
     }
  };

//+------------------------------------------------------------------+
//| kde_swing - kde_swing_zones.py: weighted M5+H1 pivots -> Gaussian|
//| KDE on a 160-pt grid -> peaks -> adaptive bands.                 |
//+------------------------------------------------------------------+
class CPaGenKde : public CPaGenCtx
  {
public:
   //--- qualified sample streams (confirm, price, weight)
   int               m5_conf[];
   double            m5_px[];
   double            m5_w[];
   int               h1_conf[];
   double            h1_px[];
   double            h1_w[];
   int               m5_lo,m5_hi,h1_lo,h1_hi;
   int               m5_src,h1_src;   // pivots rows already qualified (live extension)

                     CPaGenKde(void)
     {
      m_name="kde_swing";
      m_scale_default=PA_SC_MICRO;
      m_qual_ref=1.0;
      cfg_max_age_bars=PA_KD_MAX_AGE;
      m5_lo=0; m5_hi=0; h1_lo=0; h1_hi=0;
      m5_src=0; h1_src=0;
     }

   //--- _qualify_m5 (:104-111): prom over [j-6, j], weight clip [0.2,1.5]
   void              QualifyM5(const int i)
     {
      PaPivot p=ctx.piv3[i];
      double A=ctx.Atr(p.confirm);
      if(!(A>0.0))
         return;
      int j0=MathMax(0,p.idx-PA_KD_PROM_M5);
      double prom;
      if(p.side>0)
        {
         double mn=ctx.b[j0].l;
         for(int k=j0+1;k<=p.idx;k++)
            if(ctx.b[k].l<mn) mn=ctx.b[k].l;
         prom=p.price-mn;
        }
      else
        {
         double mx=ctx.b[j0].h;
         for(int k=j0+1;k<=p.idx;k++)
            if(ctx.b[k].h>mx) mx=ctx.b[k].h;
         prom=mx-p.price;
        }
      int m=ArraySize(m5_conf);
      ArrayResize(m5_conf,m+1); ArrayResize(m5_px,m+1); ArrayResize(m5_w,m+1);
      m5_conf[m]=p.confirm;
      m5_px[m]=p.price;
      m5_w[m]=MathMin(PA_KD_W_HI,MathMax(PA_KD_W_LO,prom/A));
     }
   //--- _qualify_h1 (:125-136): prom over [j-12, j] H1 bars, ATR at m5c
   void              QualifyH1(const int i)
     {
      PaH1Pivot p=ctx.h1p2[i];
      double A=ctx.Atr(p.m5_confirm);
      if(!(A>0.0))
         return;
      int j0=MathMax(0,p.h1_idx-PA_KD_PROM_H1);
      double prom;
      if(p.side>0)
        {
         double mn=ctx.h1_l[j0];
         for(int k=j0+1;k<=p.h1_idx;k++)
            if(ctx.h1_l[k]<mn) mn=ctx.h1_l[k];
         prom=p.price-mn;
        }
      else
        {
         double mx=ctx.h1_h[j0];
         for(int k=j0+1;k<=p.h1_idx;k++)
            if(ctx.h1_h[k]>mx) mx=ctx.h1_h[k];
         prom=mx-p.price;
        }
      int m=ArraySize(h1_conf);
      ArrayResize(h1_conf,m+1); ArrayResize(h1_px,m+1); ArrayResize(h1_w,m+1);
      h1_conf[m]=p.m5_confirm;
      h1_px[m]=p.price;
      h1_w[m]=MathMin(PA_KD_W_HI,MathMax(PA_KD_W_LO,prom/A));
     }
   //--- lazily qualify pivot rows appended by CPaCtx::PushBar (live parity
   //--- with a fresh Python run over the extended book)
   void              SyncSamples()
     {
      int npv=ctx.Pivots3();
      while(m5_src<npv) { QualifyM5(m5_src); m5_src++; }
      int nh=ctx.H1Pivots2();
      while(h1_src<nh) { QualifyH1(h1_src); h1_src++; }
     }

   void              Prepare()
     {
      ArrayResize(m5_conf,0); ArrayResize(m5_px,0); ArrayResize(m5_w,0);
      ArrayResize(h1_conf,0); ArrayResize(h1_px,0); ArrayResize(h1_w,0);
      m5_src=0; h1_src=0;
      SyncSamples();
     }

   //--- _window (:141-150): monotone cursors to confirm<=t, age<=window
   void Window(const int &conf[],int &lo,int &hi,const int t)
     {
      int nn=ArraySize(conf);
      while(hi<nn && conf[hi]<=t)
         hi++;
      while(lo<hi && conf[lo]<t-PA_KD_WINDOW)
         lo++;
     }

   virtual void      OnBar(const int t)
     {
      if(t%PA_KD_REFRESH!=0)
         return;
      double A=AtrAt(t);
      if(!(A>0.0))
         return;
      SyncSamples();
      Window(m5_conf,m5_lo,m5_hi,t);
      Window(h1_conf,h1_lo,h1_hi,t);
      int nm=m5_hi-m5_lo;
      int nh=h1_hi-h1_lo;
      int tot=nm+nh;
      if(tot<=0)
         return;
      //--- gather window samples
      double px[],w[];
      bool   ish1[];
      ArrayResize(px,tot); ArrayResize(w,tot); ArrayResize(ish1,tot);
      for(int i=0;i<nm;i++)
        {
         px[i]=m5_px[m5_lo+i]; w[i]=m5_w[m5_lo+i]; ish1[i]=false;
        }
      for(int i=0;i<nh;i++)
        {
         px[nm+i]=h1_px[h1_lo+i]; w[nm+i]=h1_w[h1_lo+i]; ish1[nm+i]=true;
        }
      //--- density grid [min-0.5A, max+0.5A] x 160, h=0.2A
      double mn=px[0],mx=px[0];
      for(int i=1;i<tot;i++)
        {
         if(px[i]<mn) mn=px[i];
         if(px[i]>mx) mx=px[i];
        }
      double g0=mn-0.5*A,g1=mx+0.5*A;
      double step=(g1-g0)/(PA_KD_GRID_N-1);
      double grid[],dens[];
      ArrayResize(grid,PA_KD_GRID_N);
      ArrayResize(dens,PA_KD_GRID_N);
      double bw=PA_KD_BW_ATR*A;
      for(int i=0;i<PA_KD_GRID_N;i++)
        {
         grid[i]=g0+i*step;
         double acc=0.0;
         for(int k=0;k<tot;k++)
           {
            double z=(grid[i]-px[k])/bw;
            acc+=MathExp(-0.5*z*z)*w[k];
           }
         dens[i]=acc;
        }
      //--- peaks: local maxima >= both neighbours, >= 0.5*max; ends never
      double dmax=dens[0];
      for(int i=1;i<PA_KD_GRID_N;i++)
         if(dens[i]>dmax) dmax=dens[i];
      double thr=PA_KD_PEAK_FRAC*dmax;
      int peaks[];
      int npk=0;
      ArrayResize(peaks,0);
      for(int i=1;i<PA_KD_GRID_N-1;i++)
         if(dens[i]>=dens[i-1] && dens[i]>=dens[i+1] && dens[i]>=thr)
           {
            ArrayResize(peaks,npk+1);
            peaks[npk]=i; npk++;
           }
      if(npk==0)
         return;
      //--- median of peak densities
      double pdv[];
      ArrayResize(pdv,npk);
      for(int i=0;i<npk;i++)
         pdv[i]=dens[peaks[i]];
      ArraySort(pdv);
      double med=(npk%2==1) ? pdv[npk/2] : (pdv[npk/2-1]+pdv[npk/2])/2.0;
      //--- peaks processed strongest first (stable: ties keep grid order)
      int order[];
      ArrayResize(order,npk);
      for(int i=0;i<npk;i++)
         order[i]=i;
      for(int i=1;i<npk;i++)
        {
         int v=order[i];
         int j=i-1;
         while(j>=0 && dens[peaks[order[j]]]<dens[peaks[v]])
           {
            order[j+1]=order[j];
            j--;
           }
         order[j+1]=v;
        }
      //--- live density zones list (center, zone) snapshot
      double live_cen[];
      int    live_idx[];
      int    nlv=0;
      ArrayResize(live_cen,0); ArrayResize(live_idx,0);
      for(int i=0;i<ArraySize(m_live);i++)
        {
         CPaZone *z=m_live[i];
         if(z.kind!=PA_ZK_DENSITY)
            continue;
         double zlo,zhi;
         z.BandAt(t,zlo,zhi);
         ArrayResize(live_cen,nlv+1); ArrayResize(live_idx,nlv+1);
         live_cen[nlv]=0.5*(zlo+zhi);
         live_idx[nlv]=i;
         nlv++;
        }
      double link=PA_KD_LINK_ATR*A;
      for(int oi=0;oi<npk;oi++)
        {
         int ip=peaks[order[oi]];
         double pd=dens[ip];
         //--- half-max run
         double half=0.5*pd;
         int i0=ip;
         while(i0>0 && dens[i0-1]>=half)
            i0--;
         int i1=ip;
         while(i1<PA_KD_GRID_N-1 && dens[i1+1]>=half)
            i1++;
         double peak_price=grid[ip];
         //--- band clip/widen centered on peak into [0.2,0.6]A
         double lo=grid[i0],hi=grid[i1];
         double min_w=PA_KD_MIN_W*A,max_w=PA_KD_MAX_W*A;
         double wdt=hi-lo;
         if(wdt<min_w) { lo=peak_price-0.5*min_w; hi=peak_price+0.5*min_w; }
         else if(wdt>max_w) { lo=peak_price-0.5*max_w; hi=peak_price+0.5*max_w; }
         double q=(pd+med>0.0) ? pd/(pd+med) : 0.5;
         //--- scale: H1 weight share inside the half-max region
         double w_tot=0.0,w_h1=0.0;
         for(int k=0;k<tot;k++)
            if(px[k]>=grid[i0] && px[k]<=grid[i1])
              {
               w_tot+=w[k];
               if(ish1[k]) w_h1+=w[k];
              }
         int scale=(w_tot>0.0 && w_h1/w_tot>=0.5) ? PA_SC_MESO : PA_SC_MICRO;
         //--- link to nearest live density zone within link
         double best_d=0.0;
         int    best_k=-1;
         for(int k=0;k<nlv;k++)
           {
            double d=MathAbs(live_cen[k]-peak_price);
            if(d<=link+1e-12 && (best_k<0 || d<best_d))
              {
               best_d=d; best_k=k;
              }
           }
         if(best_k>=0)
           {
            CPaZone *z=m_live[live_idx[best_k]];
            z.SetGeom(t,lo,hi);
            z.AddQuality(t,q);
            live_cen[best_k]=0.5*(lo+hi);
           }
         else
           {
            CPaZone *z=NewZoneEnd(PA_ZK_DENSITY,scale,t,t,lo,hi,q,
                                  t+PA_KD_MAX_AGE);
            z.m_poc=peak_price;
            ArrayResize(live_cen,nlv+1); ArrayResize(live_idx,nlv+1);
            live_cen[nlv]=0.5*(lo+hi);
            live_idx[nlv]=ArraySize(m_live)-1;
            nlv++;
           }
        }
     }
  };

//+------------------------------------------------------------------+
//| profile_va - profile_zones.py: per server-day rollover, time-at- |
//| price histogram over 1440 bars -> POC + 70% value area zone.     |
//+------------------------------------------------------------------+
class CPaGenProfile : public CPaGenCtx
  {
public:
                     CPaGenProfile(void)
     {
      m_name="profile_va";
      m_scale_default=PA_SC_MACRO;
      m_qual_ref=3.0;
      cfg_max_age_bars=PA_PF_MAX_AGE;
     }

   virtual void      OnBar(const int t)
     {
      if(t<=0)
         return;
      if(ctx.b[t].t/PA_DAY_SEC==ctx.b[t-1].t/PA_DAY_SEC)
         return;
      double A=AtrAt(t);
      if(!(A>0.0))
         return;
      int w=MathMin(PA_PF_WINDOW,t+1);
      int i0=t-w+1;
      double lw[],hw[];
      ArrayResize(lw,w); ArrayResize(hw,w);
      double lmin=0.0,hmax=0.0;
      for(int j=0;j<w;j++)
        {
         lw[j]=ctx.b[i0+j].l;
         hw[j]=ctx.b[i0+j].h;
         if(j==0) { lmin=lw[j]; hmax=hw[j]; }
         else
           {
            if(lw[j]<lmin) lmin=lw[j];
            if(hw[j]>hmax) hmax=hw[j];
           }
        }
      double bin0=PA_PF_BIN_ATR*A;
      double win_lo=lmin-0.5*bin0;
      double win_hi=hmax+0.5*bin0;
      double span=win_hi-win_lo;
      int nbins=(int)MathCeil(span/bin0);
      double binw=bin0;
      if(nbins>PA_PF_MAX_BINS)
        {
         nbins=PA_PF_MAX_BINS;
         binw=span/nbins;
        }
      if(nbins<1)
         return;
      double hist[];
      ArrayResize(hist,nbins);
      ArrayInitialize(hist,0.0);
      for(int j=0;j<w;j++)
        {
         int b0=(int)((lw[j]-win_lo)/binw);
         int b1=(int)((hw[j]-win_lo)/binw);
         double wgt=1.0/(b1-b0+1);
         int e=MathMin(b1,nbins-1);
         for(int q=b0;q<=e;q++)
            hist[q]+=wgt;
        }
      //--- POC = first argmax
      int poc=0;
      for(int i=1;i<nbins;i++)
         if(hist[i]>hist[poc])
            poc=i;
      int va_lo=poc,va_hi=poc;
      double acc=hist[poc];
      double total=0.0;
      for(int i=0;i<nbins;i++)
         total+=hist[i];
      double need=PA_PF_VA_FRAC*total;
      while(acc<need)
        {
         bool has_l=(va_lo>0);
         bool has_r=(va_hi<nbins-1);
         if(!has_l && !has_r)
            break;
         double lv=has_l ? hist[va_lo-1] : -1.0;
         double rv=has_r ? hist[va_hi+1] : -1.0;
         if(lv>=rv)
           {
            va_lo--; acc+=lv;
           }
         else
           {
            va_hi++; acc+=rv;
           }
        }
      double val=win_lo+va_lo*binw;
      double vah=win_lo+(va_hi+1)*binw;
      double poc_price=win_lo+(poc+0.5)*binw;
      double min_w=PA_PF_MIN_W*A,max_w=PA_PF_MAX_W*A;
      double lo=val,hi=vah;
      if(hi-lo<min_w) { lo=poc_price-0.5*min_w; hi=poc_price+0.5*min_w; }
      else if(hi-lo>max_w) { lo=poc_price-0.5*max_w; hi=poc_price+0.5*max_w; }
      double va_mean=0.0;
      for(int i=va_lo;i<=va_hi;i++)
         va_mean+=hist[i];
      va_mean/=(va_hi-va_lo+1);
      double q=hist[poc]/va_mean;
      CPaZone *z=NewZoneEnd(PA_ZK_PROFILE_POC,PA_SC_MACRO,t,t,lo,hi,q,
                            t+PA_PF_MAX_AGE);
      z.m_poc=poc_price; z.m_level=val;
      z.m_nb=nbins; z.m_k=w;
     }
  };

//+------------------------------------------------------------------+
//| sd_base - sd_base_zones.py: tight base + impulse displacement    |
//| leaves a supply/demand zone at the base band.                    |
//+------------------------------------------------------------------+
class CPaGenSdBase : public CPaGenCtx
  {
public:
   //--- used (kind, base_end) pairs
   int               bases_kind[];
   int               bases_be[];
   int               nbases;

                     CPaGenSdBase(void)
     {
      m_name="sd_base";
      m_scale_default=PA_SC_MICRO;
      m_qual_ref=2.0;
      cfg_max_age_bars=PA_SD_MAX_AGE;
      nbases=0;
     }

   bool BaseUsed(const int kind,const int be)
     {
      for(int i=0;i<nbases;i++)
         if(bases_kind[i]==kind && MathAbs(bases_be[i]-be)<=1)
            return(true);
      return(false);
     }

   void BaseMark(const int kind,const int be)
     {
      ArrayResize(bases_kind,nbases+1);
      ArrayResize(bases_be,nbases+1);
      bases_kind[nbases]=kind; bases_be[nbases]=be;
      nbases++;
     }

   bool CenterBlocked(const int kind,const double cen,const int t,const double dedupe)
     {
      for(int i=0;i<ArraySize(m_live);i++)
        {
         CPaZone *z=m_live[i];
         if(z.kind!=kind || t>z.end_idx)
            continue;
         double zlo,zhi;
         z.BandAt(t,zlo,zhi);
         if(MathAbs(0.5*(zlo+zhi)-cen)<=dedupe+1e-12)
            return(true);
        }
      return(false);
     }

   virtual void      OnBar(const int t)
     {
      double A=AtrAt(t);
      if(!(A>0.0))
         return;
      double c_t=ctx.b[t].c;
      double base_range=PA_SD_BASE_RANGE*A;
      double need=PA_SD_IMP_MIN*A;
      //--- candidates: (delta desc, k asc, nb asc)
      double cd[]; int ck[],cnb[],cbe[],ckind[];
      double clb[],chb[];
      int nc=0;
      ArrayResize(cd,0); ArrayResize(ck,0); ArrayResize(cnb,0);
      ArrayResize(cbe,0); ArrayResize(ckind,0); ArrayResize(clb,0); ArrayResize(chb,0);
      for(int k=1;k<=PA_SD_IMP_MAX;k++)
        {
         int be=t-k;
         if(be<0)
            break;
         for(int nb=1;nb<=PA_SD_BASE_MAX;nb++)
           {
            if(be-nb+1<0)
               continue;
            double hb=ctx.b[be-nb+1].h,lb=ctx.b[be-nb+1].l;
            for(int j=be-nb+2;j<=be;j++)
              {
               if(ctx.b[j].h>hb) hb=ctx.b[j].h;
               if(ctx.b[j].l<lb) lb=ctx.b[j].l;
              }
            if(hb-lb>base_range)
               continue;
            double d=c_t-hb;
            int kind=-1;
            if(d>=need)
               kind=PA_ZK_DEMAND;
            else
              {
               d=lb-c_t;
               if(d>=need)
                  kind=PA_ZK_SUPPLY;
              }
            if(kind<0)
               continue;
            ArrayResize(cd,nc+1); ArrayResize(ck,nc+1); ArrayResize(cnb,nc+1);
            ArrayResize(cbe,nc+1); ArrayResize(ckind,nc+1);
            ArrayResize(clb,nc+1); ArrayResize(chb,nc+1);
            cd[nc]=d; ck[nc]=k; cnb[nc]=nb; cbe[nc]=be; ckind[nc]=kind;
            clb[nc]=lb; chb[nc]=hb;
            nc++;
           }
        }
      if(nc==0)
         return;
      //--- sort by (-delta, k, nb) - insertion on small n
      int ord[];
      ArrayResize(ord,nc);
      for(int i=0;i<nc;i++)
         ord[i]=i;
      for(int i=1;i<nc;i++)
        {
         int v=ord[i];
         int j=i-1;
         while(j>=0 && (cd[ord[j]]<cd[v] ||
               (cd[ord[j]]==cd[v] && ck[ord[j]]>ck[v]) ||
               (cd[ord[j]]==cd[v] && ck[ord[j]]==ck[v] && cnb[ord[j]]>cnb[v])))
           {
            ord[j+1]=ord[j];
            j--;
           }
         ord[j+1]=v;
        }
      double pad=PA_SD_PAD_ATR*A;
      double min_w=PA_SD_MIN_W*A;
      double max_w=PA_SD_MAX_W*A;
      double dedupe=PA_SD_DEDUPE*A;
      for(int i=0;i<nc;i++)
        {
         int x=ord[i];
         if(BaseUsed(ckind[x],cbe[x]))
            continue;
         double lo=clb[x]-pad,hi=chb[x]+pad;
         double cen=0.5*(lo+hi);
         if(hi-lo<min_w) { lo=cen-0.5*min_w; hi=cen+0.5*min_w; }
         else if(hi-lo>max_w) { lo=cen-0.5*max_w; hi=cen+0.5*max_w; }
         if(CenterBlocked(ckind[x],cen,t,dedupe))
            continue;
         CPaZone *z=NewZoneEnd(ckind[x],PA_SC_MICRO,cbe[x],t,lo,hi,cd[x]/A,
                               cbe[x]+PA_SD_MAX_AGE);
         z.m_base_end=cbe[x]; z.m_nb=cnb[x]; z.m_k=ck[x];
         BaseMark(ckind[x],cbe[x]);
         return;
        }
     }
  };

//+------------------------------------------------------------------+
//| ref_levels - ref_zones.py: PDH/PDL/PDC + Asia + week + 00/50     |
//| round zones published at rollovers, one zone per slot.           |
//+------------------------------------------------------------------+
class CPaGenRefs : public CPaGenCtx
  {
public:
   //--- slot map: slot name -> zone (m_slot carries it on the zone)
   CPaZone          *prev[9];
   string            slot_name[9];

                     CPaGenRefs(void)
     {
      m_name="ref_levels";
      m_scale_default=PA_SC_MESO;
      m_qual_ref=1.0;
      cfg_max_age_bars=PA_RF_MAX_AGE;
      slot_name[0]="pdh"; slot_name[1]="pdl"; slot_name[2]="pdc";
      slot_name[3]="asia_hi"; slot_name[4]="asia_lo";
      slot_name[5]="wk_hi"; slot_name[6]="wk_lo";
      slot_name[7]="round_lo"; slot_name[8]="round_hi";
      for(int i=0;i<9;i++)
         prev[i]=NULL;
     }

   int KindOfSlot(const string slot)
     {
      if(slot=="pdh")     return(PA_ZK_PDH);
      if(slot=="pdl")     return(PA_ZK_PDL);
      if(slot=="pdc")     return(PA_ZK_PDC);
      if(slot=="asia_hi") return(PA_ZK_ASIA_HI);
      if(slot=="asia_lo") return(PA_ZK_ASIA_LO);
      if(slot=="wk_hi")   return(PA_ZK_WK_HI);
      if(slot=="wk_lo")   return(PA_ZK_WK_LO);
      return(PA_ZK_ROUND);
     }

   //--- _publish (:75-113): retire slot's previous zone; dedupe same-kind
   //--- live center within dedupe_atr -> carry matched zone into the slot;
   //--- else new band [level +- w/2], born=created=t
   void Publish(const int slot_i,const double level,const bool ok,
                const int t,const double A,const int scale)
     {
      CPaZone *pz=prev[slot_i];
      if(pz!=NULL)
        {
         Retire(pz,t);
         prev[slot_i]=NULL;
        }
      if(!ok)
         return;   // Python: not math.isfinite(level)
      double w=PA_RF_WIDTH_ATR*A;
      double dedupe=PA_RF_DEDUPE*A;
      int kind=KindOfSlot(slot_name[slot_i]);
      CPaZone *matched=NULL;
      for(int i=0;i<ArraySize(m_live);i++)
        {
         CPaZone *z=m_live[i];
         if(z.kind!=kind)
            continue;
         double zlo,zhi;
         z.BandAt(t,zlo,zhi);
         if(MathAbs(0.5*(zlo+zhi)-level)<=dedupe)
           {
            matched=z;
            break;
           }
        }
      if(matched!=NULL)
        {
         //--- carry the matched zone into this slot; remove it elsewhere
         for(int s=0;s<9;s++)
            if(prev[s]==matched)
               prev[s]=NULL;
         prev[slot_i]=matched;
         return;
        }
      CPaZone *z=NewZoneEnd(kind,scale,t,t,level-0.5*w,level+0.5*w,1.0,
                            t+PA_RF_MAX_AGE);
      z.m_level=level;
      z.m_slot=slot_name[slot_i];
      prev[slot_i]=z;
     }

   virtual void      OnBar(const int t)
     {
      double A=AtrAt(t);
      if(!(A>0.0))
         return;
      if(t>0 && ctx.b[t].t/PA_DAY_SEC!=ctx.b[t-1].t/PA_DAY_SEC)
        {
         double close=ctx.b[t].c;
         Publish(0,ctx.refs.pdh,ctx.refs.pd_ok,t,A,PA_SC_MESO);
         Publish(1,ctx.refs.pdl,ctx.refs.pd_ok,t,A,PA_SC_MESO);
         Publish(2,ctx.refs.pdc,ctx.refs.pd_ok,t,A,PA_SC_MESO);
         double g0,g1;
         bool rok=ctx.refs.RoundNear(close,g0,g1);
         if(rok)
           {
            Publish(7,g0,true,t,A,PA_SC_MESO);
            Publish(8,g1,true,t,A,PA_SC_MESO);
           }
         if(ctx.b[t].dow==0)
           {
            Publish(5,ctx.refs.wk_hi,ctx.refs.wk_ok,t,A,PA_SC_MACRO);
            Publish(6,ctx.refs.wk_lo,ctx.refs.wk_ok,t,A,PA_SC_MACRO);
           }
        }
      if(t>0 && ctx.b[t-1].utc_min<PA_ASIA_UTC_HI &&
         ctx.b[t].utc_min>=PA_ASIA_UTC_HI)
        {
         Publish(3,ctx.refs.asia_hi,ctx.refs.asia_ok,t,A,PA_SC_MESO);
         Publish(4,ctx.refs.asia_lo,ctx.refs.asia_ok,t,A,PA_SC_MESO);
        }
     }
  };

//+------------------------------------------------------------------+
//| CPaPerception - facade: shared ctx + the six generators.         |
//| StepBar(t) mirrors sf_ctx.run_pass per-bar order: refs update    |
//| first (Python refs arrays are precomputed; values at t identical)|
//| then each enabled generator's OnBar + _step_all + shadow track.  |
//+------------------------------------------------------------------+
class CPaPerception
  {
public:
   CPaCtx            ctx;
   CPaGenBase       *gen[PA_GEN_COUNT];

                     CPaPerception(void)
     {
      for(int i=0;i<PA_GEN_COUNT;i++)
         gen[i]=NULL;
     }

                    ~CPaPerception(void)
     {
      for(int i=0;i<PA_GEN_COUNT;i++)
         if(CheckPointer(gen[i])==POINTER_DYNAMIC)
            delete gen[i];
     }

   bool              Init(const PaBar &bars[],const int n,const double pip,
                          const string sym,const bool &gen_on[])
     {
      if(!ctx.Init(bars,n,pip,sym))
         return(false);
      for(int i=0;i<PA_GEN_COUNT;i++)
        {
         if(!gen_on[i])
            continue;
         switch(i)
           {
            case PA_GEN_LINE1:
              {
               CPaGenLine1 *g=new CPaGenLine1();
               g.SetCtx(GetPointer(ctx));
               g.Prepare();
               gen[i]=g;
               break;
              }
            case PA_GEN_FRACTAL:
              {
               CPaGenFractal *g=new CPaGenFractal();
               g.SetCtx(GetPointer(ctx));
               g.Prepare();
               gen[i]=g;
               break;
              }
            case PA_GEN_KDE:
              {
               CPaGenKde *g=new CPaGenKde();
               g.SetCtx(GetPointer(ctx));
               g.Prepare();
               gen[i]=g;
               break;
              }
            case PA_GEN_PROFILE:
              {
               CPaGenProfile *g=new CPaGenProfile();
               g.SetCtx(GetPointer(ctx));
               gen[i]=g;
               break;
              }
            case PA_GEN_SD_BASE:
              {
               CPaGenSdBase *g=new CPaGenSdBase();
               g.SetCtx(GetPointer(ctx));
               gen[i]=g;
               break;
              }
            case PA_GEN_REFS:
              {
               CPaGenRefs *g=new CPaGenRefs();
               g.SetCtx(GetPointer(ctx));
               gen[i]=g;
               break;
              }
           }
        }
      return(true);
     }

   //--- one closed M5 bar
   void              StepBar(const int t)
     {
      ctx.refs.OnBar(ctx.b[t]);
      double A=ctx.Atr(t);
      bool ok=ctx.AtrOk(t);
      for(int i=0;i<PA_GEN_COUNT;i++)
         if(gen[i]!=NULL)
            gen[i].StepBar(t,ctx.b[t],A,ok,ctx.b);
     }

   void              RunTo(const int last)
     {
      for(int t=0;t<=last && t<ctx.n;t++)
         StepBar(t);
     }

   //--- armed views for generator g at bar t (ctx.refs is current at the
   //--- facade's stepped bar - only call right after StepBar(t))
   int               ViewsAt(const int g,const int t,const bool arm,
                             PaZoneView &views[])
     {
      ArrayResize(views,0);
      if(g<0 || g>=PA_GEN_COUNT || gen[g]==NULL)
         return(0);
      return(gen[g].ViewsAt(t,ctx.Atr(t),ctx.AtrOk(t),ctx.b[t].c,arm,views));
     }
  };

#endif // PA_ZONES_MQH

