//+------------------------------------------------------------------+
//|                                                    PA_Setups.mqh |
//|  PA-PRO EA lane - setup module interface for Setup Factory        |
//|  survivors.                                                      |
//|                                                                  |
//|  Contract (clean detect/build-order split):                      |
//|   - Detect(perception, sess, t, sig)  fills PaSetupSignal at the  |
//|     CLOSED M5 bar t using only causal state (zone sx track).     |
//|   - The EA then calls CPaTrade.BuildStop/BuildMarket on it.      |
//|  A Setup Factory survivor drops in by subclassing CPaSetupBase   |
//|  and registering in PaSetupInit().  Stub modules below mirror    |
//|  the SF01 family SHAPES (f1_zone_rejection / f2_break_retest)    |
//|  marked STUB - they log signals for plumbing tests, and are      |
//|  replaced by survivor modules when the Factory lane delivers.    |
//|                                                                  |
//|  No order, position or trade call exists in this header.         |
//+------------------------------------------------------------------+
#ifndef PA_SETUPS_MQH
#define PA_SETUPS_MQH

#include "PA_Types.mqh"
#include "PA_Zones.mqh"
#include "PA_Session.mqh"

struct PaSetupSignal
  {
   bool              ok;
   int               side;         // +1 / -1
   int               gen;          // which generator produced the zone
   int               zid;
   double            zone_lo;
   double            zone_hi;
   double            zone_center;
   double            strength;
   string            tag;          // module tag (journal column)
   int               veto;
   string            note;
  };

void PaSetupClear(PaSetupSignal &s)
  {
   s.ok=false; s.side=0; s.gen=-1; s.zid=0;
   s.zone_lo=0; s.zone_hi=0; s.zone_center=0; s.strength=0;
   s.tag=""; s.veto=PA_VETO_NONE; s.note="";
  }

//+------------------------------------------------------------------+
//| module interface                                                  |
//+------------------------------------------------------------------+
class CPaSetupBase
  {
public:
   string            name;
   bool              enabled;
                     CPaSetupBase(void) { name=""; enabled=true; }
   //--- t = index of the just-closed M5 bar in the perception book
   virtual bool      Detect(const int t,PaSetupSignal &sig)=0;
   //--- context bindings (set by the host before stepping)
   virtual void      Bind(CPaPerception *per,CPaSession *sess)=0;
  };

//+------------------------------------------------------------------+
//| STUB F1 - zone rejection shape (families/f1_zone_rejection.py):  |
//| price wicks INTO an intact armed zone and closes back on the     |
//| approach side -> fade the zone (stop order on the far side).     |
//+------------------------------------------------------------------+
class CPaSetupF1 : public CPaSetupBase
  {
public:
   CPaPerception    *pa;
   CPaSession       *sess;
   int               min_touches;
   double            min_strength;

                     CPaSetupF1(void)
     {
      name="f1_zone_rejection_stub";
      min_touches=1;
      min_strength=0.15;
     }

   virtual void      Bind(CPaPerception *per,CPaSession *se)
     {
      pa=per;
      sess=se;
     }

   virtual bool      Detect(const int t,PaSetupSignal &sig)
     {
      PaSetupClear(sig);
      sig.tag=name;
      if(pa==NULL || t<1)
         return(false);
      const PaBar b=pa.ctx.b[t];
      //--- scan armed views of every generator for a rejection shape
      for(int g=0;g<PA_GEN_COUNT;g++)
        {
         PaZoneView views[];
         int nv=pa.ViewsAt(g,t,true,views);
         for(int v=0;v<nv;v++)
           {
            PaZoneView z=views[v];
            if(z.touches<min_touches || z.strength<min_strength)
               continue;
            //--- rejection: bar range pierced the band, close back outside.
            //--- approach_side: -1 = price below (zone = resistance -> sell);
            //---                  +1 = price above (zone = support -> buy).
            bool pierce_dn=(b.l<z.hi && b.l>=z.lo && b.c>z.hi); // up through
            bool pierce_up=(b.h>z.lo && b.h<=z.hi && b.c<z.lo); // down
            bool test_lo=(b.l<=z.hi && b.l>=z.lo && b.c>b.l && b.c>z.lo);
            bool test_hi=(b.h>=z.lo && b.h<=z.hi && b.c<b.h && b.c<z.hi);
            int side=0;
            if((pierce_up || test_hi) && b.c<b.o && z.approach_side<=0)
               side=-1;                     // rejected a ceiling -> sell
            else if((pierce_dn || test_lo) && b.c>b.o && z.approach_side>=0)
               side=+1;                     // rejected a floor -> buy
            if(side==0)
               continue;
            sig.ok=true; sig.side=side;
            sig.gen=g; sig.zid=z.zid;
            sig.zone_lo=z.lo; sig.zone_hi=z.hi;
            sig.zone_center=0.5*(z.lo+z.hi);
            sig.strength=z.strength;
            sig.note="STUB_F1";
            return(true);
           }
        }
      return(false);
     }
  };

//+------------------------------------------------------------------+
//| STUB F2 - break/retest shape (families/f2_break_retest.py):      |
//| a zone broke (sx.broken set) within the last few bars and price  |
//| returns INTO the band -> trade with the break direction.         |
//+------------------------------------------------------------------+
class CPaSetupF2 : public CPaSetupBase
  {
public:
   CPaPerception    *pa;
   CPaSession       *sess;
   int               max_bars_since_break;

                     CPaSetupF2(void)
     {
      name="f2_break_retest_stub";
      max_bars_since_break=12;
     }

   virtual void      Bind(CPaPerception *per,CPaSession *se)
     {
      pa=per;
      sess=se;
     }

   virtual bool      Detect(const int t,PaSetupSignal &sig)
     {
      PaSetupClear(sig);
      sig.tag=name;
      if(pa==NULL || t<1)
         return(false);
      const PaBar b=pa.ctx.b[t];
      for(int g=0;g<PA_GEN_COUNT;g++)
        {
         //--- broken zones are excluded from armed views -> scan the live
         //--- book directly (unarmed view set)
         PaZoneView views[];
         int nv=pa.ViewsAt(g,t,false,views);
         for(int v=0;v<nv;v++)
           {
            PaZoneView z=views[v];
            if(z.broken_idx<0 || (t-z.broken_idx)>max_bars_since_break)
               continue;
            if(z.role_flip!=0)
               continue;
            //--- retest: bar range re-enters the band after the break
            bool back_in=(b.l<=z.hi && b.h>=z.lo);
            if(!back_in)
               continue;
            //--- trade with the break direction (broken_side from sx)
            CPaZone *zone=FindZoneById(g,z.zid);
            if(zone==NULL)
               continue;
            int side=zone.sx.broken_side;      // -1 broke up, +1 broke down
            if(side==0)
               continue;
            //--- approach_side after break: -1 means price was below, broke
            //--- up through hi -> buy continuation; +1 -> sell
            int dir=(side==-1) ? +1 : -1;
            sig.ok=true; sig.side=dir;
            sig.gen=g; sig.zid=z.zid;
            sig.zone_lo=z.lo; sig.zone_hi=z.hi;
            sig.zone_center=0.5*(z.lo+z.hi);
            sig.strength=z.strength;
            sig.note="STUB_F2";
            return(true);
           }
        }
      return(false);
     }

   CPaZone          *FindZoneById(const int g,const int zid)
     {
      if(g<0 || g>=PA_GEN_COUNT || pa.gen[g]==NULL)
         return(NULL);
      CPaGenBase *gen=pa.gen[g];
      for(int i=0;i<ArraySize(gen.m_live);i++)
         if(gen.m_live[i].zid==zid)
            return(gen.m_live[i]);
      return(NULL);
     }
  };

//+------------------------------------------------------------------+
//| registry: enabled modules, bound once, stepped per bar           |
//+------------------------------------------------------------------+
class CPaSetups
  {
public:
   CPaSetupBase     *mods[];
   int               n;

                     CPaSetups(void) { n=0; }
                    ~CPaSetups(void)
     {
      for(int i=0;i<n;i++)
         if(CheckPointer(mods[i])==POINTER_DYNAMIC)
            delete mods[i];
     }

   void              Add(CPaSetupBase *m)
     {
      ArrayResize(mods,n+1);
      mods[n]=m;
      n++;
     }

   //--- first module to fire wins (deterministic order = registration)
   bool              Detect(const int t,PaSetupSignal &sig)
     {
      PaSetupClear(sig);
      for(int i=0;i<n;i++)
        {
         if(!mods[i].enabled)
            continue;
         if(mods[i].Detect(t,sig))
            return(true);
        }
      return(false);
     }
  };

#endif // PA_SETUPS_MQH
