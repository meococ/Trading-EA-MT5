from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
import numpy as np
PATH=Path(__file__).resolve().parents[1]/"analyze_uo_h1_source.py"; SPEC=spec_from_file_location("uo",PATH); MODULE=module_from_spec(SPEC)
assert SPEC and SPEC.loader; SPEC.loader.exec_module(MODULE)

def series(n=80):
    x=np.arange(n,dtype=float); close=1.1+.001*np.sin(x/3)+.0001*x; return close+.001,close-.001,close

def test_first_uo_and_formula():
    h,l,c=series(); bp,tr,a7,a14,a28,uo=MODULE.ultimate(h,l,c)
    assert np.isnan(uo[27]) and np.isfinite(uo[28]); assert np.isfinite(a7[7]) and np.isfinite(a14[14]) and np.isfinite(a28[28])
    assert uo[28]==100*(4*a7[28]+2*a14[28]+a28[28])/7

def test_bp_tr_exact():
    h,l,c=series(); bp,tr,*_=MODULE.ultimate(h,l,c)
    assert bp[1]==c[1]-min(l[1],c[0]); assert tr[1]==max(h[1],c[0])-min(l[1],c[0])

def test_nonpositive_tr_sum_is_local_invalid():
    h=np.ones(80); l=np.ones(80); c=np.ones(80); *_,uo=MODULE.ultimate(h,l,c); assert np.isnan(uo).all()

def test_event_allowlist_no_outcomes():
    assert not (MODULE.EVENT_KEYS&{"entry","exit","pnl","return","profit_factor","cost"})

def test_contract_strings():
    s=PATH.read_text(encoding="utf-8"); assert "np.roll(uo,1)<=30" in s and "uo>30" in s
    assert "np.roll(uo,1)>=70" in s and "uo<70" in s; assert "pd.Timedelta(hours=1)" in s and "+3600.0" in s
    assert 'pd.Timestamp(e["decision_time_utc"]).year' in s and '"next_row_ohlc_read":False' in s

def test_claim_and_rehash():
    s=PATH.read_text(encoding="utf-8"); assert 'initial["analyzer"]!=claimed' in s
    assert '{k:sha256_file(v) for k,v in bound.items()}!=initial' in s and '"test":test' in s
