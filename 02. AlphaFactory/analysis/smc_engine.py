"""
SMC (Smart Money Concepts) Engine for Python
============================================
This module implements SMC/ICT concepts for backtesting with VectorBT.
Logic is designed to match MT5 EA implementation exactly.

Core Components:
1. Market Structure (Swing Points, BOS, CHoCH)
2. Order Blocks (Bullish/Bearish)
3. Fair Value Gaps
4. Premium/Discount Zones
5. Multi-Timeframe Analysis

Author: AlphaFactory
Version: 1.0
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum

# =============================================================================
# ENUMS - Same as MT5
# =============================================================================
class MarketBias(Enum):
    NONE = 0
    BULLISH = 1
    BEARISH = -1

class StructureType(Enum):
    NONE = 0
    BOS = 1      # Break of Structure (continuation)
    CHOCH = 2    # Change of Character (reversal)

class Zone(Enum):
    NEUTRAL = 0
    PREMIUM = 1   # Sell zone (top 30%)
    DISCOUNT = -1 # Buy zone (bottom 30%)

# =============================================================================
# DATA CLASSES
# =============================================================================
@dataclass
class SwingPoint:
    """Represents a swing high or low"""
    price: float
    index: int
    is_high: bool
    is_broken: bool = False

@dataclass
class OrderBlock:
    """Order Block - entry zone"""
    high: float
    low: float
    index: int
    bias: MarketBias
    is_valid: bool = True
    is_mitigated: bool = False

@dataclass 
class FairValueGap:
    """Fair Value Gap - imbalance zone"""
    top: float
    bottom: float
    index: int
    bias: MarketBias
    is_valid: bool = True
    is_filled: bool = False

# =============================================================================
# SMC ENGINE CLASS
# =============================================================================
class SMCEngine:
    """
    Smart Money Concepts Engine
    
    Usage:
        engine = SMCEngine(swing_len=5, ob_min_atr=0.3, fvg_min_atr=0.5)
        signals = engine.generate_signals(df)
    """
    
    def __init__(
        self,
        # Structure detection
        htf_swing_len: int = 10,
        ltf_swing_len: int = 5,
        # Order Blocks
        use_ob: bool = True,
        ob_lookback: int = 20,
        ob_min_atr: float = 0.3,
        # Fair Value Gaps
        use_fvg: bool = True,
        fvg_min_atr: float = 0.5,
        # Premium/Discount
        use_pd_zone: bool = True,
        premium_level: float = 0.70,
        discount_level: float = 0.30,
        # Risk
        rr_ratio: float = 2.0,
        atr_period: int = 14,
    ):
        self.htf_swing_len = htf_swing_len
        self.ltf_swing_len = ltf_swing_len
        self.use_ob = use_ob
        self.ob_lookback = ob_lookback
        self.ob_min_atr = ob_min_atr
        self.use_fvg = use_fvg
        self.fvg_min_atr = fvg_min_atr
        self.use_pd_zone = use_pd_zone
        self.premium_level = premium_level
        self.discount_level = discount_level
        self.rr_ratio = rr_ratio
        self.atr_period = atr_period
        
    def calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate ATR - matches MT5 iATR"""
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr[0] = tr1[0]  # First bar
        
        # EMA-based ATR (MT5 default)
        atr = np.zeros_like(tr)
        atr[period-1] = np.mean(tr[:period])
        multiplier = 2 / (period + 1)
        for i in range(period, len(tr)):
            atr[i] = (tr[i] - atr[i-1]) * multiplier + atr[i-1]
        
        return atr
    
    def detect_swing_points(
        self, 
        high: np.ndarray, 
        low: np.ndarray, 
        length: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Detect swing highs and lows
        
        Returns:
            swing_high_idx: indices where swing highs occur
            swing_high_prices: prices at swing highs
            swing_low_idx: indices where swing lows occur  
            swing_low_prices: prices at swing lows
        """
        n = len(high)
        swing_highs = np.full(n, np.nan)
        swing_lows = np.full(n, np.nan)
        
        for i in range(length, n - length):
            # Check swing high
            is_swing_high = True
            pivot_high = high[i]
            for j in range(1, length + 1):
                if high[i - j] > pivot_high or high[i + j] > pivot_high:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs[i] = pivot_high
                
            # Check swing low
            is_swing_low = True
            pivot_low = low[i]
            for j in range(1, length + 1):
                if low[i - j] < pivot_low or low[i + j] < pivot_low:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows[i] = pivot_low
        
        # Extract non-nan values
        sh_idx = np.where(~np.isnan(swing_highs))[0]
        sh_prices = swing_highs[sh_idx]
        sl_idx = np.where(~np.isnan(swing_lows))[0]
        sl_prices = swing_lows[sl_idx]
        
        return sh_idx, sh_prices, sl_idx, sl_prices
    
    def determine_structure(
        self,
        close: np.ndarray,
        swing_high_idx: np.ndarray,
        swing_high_prices: np.ndarray,
        swing_low_idx: np.ndarray,
        swing_low_prices: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Determine market structure (bias, BOS, CHoCH)
        
        Logic:
        - BOS Bullish: Close breaks above swing high in uptrend
        - CHoCH Bullish: Close breaks above swing high in downtrend (reversal)
        - BOS Bearish: Close breaks below swing low in downtrend
        - CHoCH Bearish: Close breaks below swing low in uptrend (reversal)
        
        Returns:
            bias: array of MarketBias values
            bos_signals: array (1=bullish BOS, -1=bearish BOS, 0=none)
            choch_signals: array (1=bullish CHoCH, -1=bearish CHoCH, 0=none)
        """
        n = len(close)
        bias = np.zeros(n, dtype=int)  # 0=none, 1=bullish, -1=bearish
        bos = np.zeros(n, dtype=int)
        choch = np.zeros(n, dtype=int)
        
        current_bias = 0
        last_sh_price = 0.0
        last_sl_price = float('inf')
        last_sh_broken = True
        last_sl_broken = True
        
        sh_ptr = 0  # Pointer to current swing high
        sl_ptr = 0  # Pointer to current swing low
        
        for i in range(n):
            # Update swing points as we pass them
            while sh_ptr < len(swing_high_idx) and swing_high_idx[sh_ptr] <= i:
                last_sh_price = swing_high_prices[sh_ptr]
                last_sh_broken = False
                sh_ptr += 1
                
            while sl_ptr < len(swing_low_idx) and swing_low_idx[sl_ptr] <= i:
                last_sl_price = swing_low_prices[sl_ptr]
                last_sl_broken = False
                sl_ptr += 1
            
            # Check for bullish break (close > swing high)
            if not last_sh_broken and last_sh_price > 0 and close[i] > last_sh_price:
                last_sh_broken = True
                if current_bias == -1:  # Was bearish, now bullish = CHoCH
                    choch[i] = 1
                else:  # BOS
                    bos[i] = 1
                current_bias = 1
            
            # Check for bearish break (close < swing low)
            if not last_sl_broken and last_sl_price < float('inf') and close[i] < last_sl_price:
                last_sl_broken = True
                if current_bias == 1:  # Was bullish, now bearish = CHoCH
                    choch[i] = -1
                else:  # BOS
                    bos[i] = -1
                current_bias = -1
            
            bias[i] = current_bias
        
        return bias, bos, choch
    
    def detect_order_blocks(
        self,
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        bias: np.ndarray,
        bos: np.ndarray,
        choch: np.ndarray,
        atr: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Detect Order Blocks
        
        Bullish OB: Last bearish candle before bullish impulse
        Bearish OB: Last bullish candle before bearish impulse
        
        Returns:
            ob_bull_high, ob_bull_low: Arrays of bullish OB levels (nan if no OB)
            ob_bear_high, ob_bear_low: Arrays of bearish OB levels
        """
        n = len(close)
        ob_bull_high = np.full(n, np.nan)
        ob_bull_low = np.full(n, np.nan)
        ob_bear_high = np.full(n, np.nan)
        ob_bear_low = np.full(n, np.nan)
        
        for i in range(self.ob_lookback, n):
            # On bullish structure break, find bullish OB
            if bos[i] == 1 or choch[i] == 1:
                for j in range(1, min(self.ob_lookback, i)):
                    idx = i - j
                    # Bearish candle (close < open)
                    if close[idx] < open_[idx]:
                        body_size = open_[idx] - close[idx]
                        if body_size >= atr[idx] * self.ob_min_atr:
                            # Verify impulse after
                            if idx + 1 < n and close[idx + 1] > high[idx]:
                                ob_bull_high[i] = high[idx]
                                ob_bull_low[i] = low[idx]
                                break
            
            # On bearish structure break, find bearish OB
            if bos[i] == -1 or choch[i] == -1:
                for j in range(1, min(self.ob_lookback, i)):
                    idx = i - j
                    # Bullish candle (close > open)
                    if close[idx] > open_[idx]:
                        body_size = close[idx] - open_[idx]
                        if body_size >= atr[idx] * self.ob_min_atr:
                            if idx + 1 < n and close[idx + 1] < low[idx]:
                                ob_bear_high[i] = high[idx]
                                ob_bear_low[i] = low[idx]
                                break
        
        # Forward fill OB levels until mitigated
        last_bull_high, last_bull_low = np.nan, np.nan
        last_bear_high, last_bear_low = np.nan, np.nan
        
        for i in range(n):
            # Update if new OB detected
            if not np.isnan(ob_bull_high[i]):
                last_bull_high, last_bull_low = ob_bull_high[i], ob_bull_low[i]
            if not np.isnan(ob_bear_high[i]):
                last_bear_high, last_bear_low = ob_bear_high[i], ob_bear_low[i]
            
            # Check mitigation
            if not np.isnan(last_bull_low) and close[i] < last_bull_low:
                last_bull_high, last_bull_low = np.nan, np.nan
            if not np.isnan(last_bear_high) and close[i] > last_bear_high:
                last_bear_high, last_bear_low = np.nan, np.nan
            
            # Assign
            ob_bull_high[i] = last_bull_high
            ob_bull_low[i] = last_bull_low
            ob_bear_high[i] = last_bear_high
            ob_bear_low[i] = last_bear_low
        
        return ob_bull_high, ob_bull_low, ob_bear_high, ob_bear_low
    
    def detect_fvg(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        atr: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Detect Fair Value Gaps
        
        Bullish FVG: Current low > 2 bars ago high (gap up)
        Bearish FVG: Current high < 2 bars ago low (gap down)
        """
        n = len(close)
        fvg_bull_top = np.full(n, np.nan)
        fvg_bull_bottom = np.full(n, np.nan)
        fvg_bear_top = np.full(n, np.nan)
        fvg_bear_bottom = np.full(n, np.nan)
        
        for i in range(2, n):
            # Bullish FVG
            if low[i] > high[i-2]:
                gap_size = low[i] - high[i-2]
                if gap_size >= atr[i] * self.fvg_min_atr:
                    fvg_bull_top[i] = low[i]
                    fvg_bull_bottom[i] = high[i-2]
            
            # Bearish FVG
            if high[i] < low[i-2]:
                gap_size = low[i-2] - high[i]
                if gap_size >= atr[i] * self.fvg_min_atr:
                    fvg_bear_top[i] = low[i-2]
                    fvg_bear_bottom[i] = high[i]
        
        # Forward fill until filled
        last_bull_top, last_bull_bottom = np.nan, np.nan
        last_bear_top, last_bear_bottom = np.nan, np.nan
        
        for i in range(n):
            if not np.isnan(fvg_bull_top[i]):
                last_bull_top, last_bull_bottom = fvg_bull_top[i], fvg_bull_bottom[i]
            if not np.isnan(fvg_bear_top[i]):
                last_bear_top, last_bear_bottom = fvg_bear_top[i], fvg_bear_bottom[i]
            
            # Check if filled
            if not np.isnan(last_bull_bottom) and low[i] < last_bull_bottom:
                last_bull_top, last_bull_bottom = np.nan, np.nan
            if not np.isnan(last_bear_top) and high[i] > last_bear_top:
                last_bear_top, last_bear_bottom = np.nan, np.nan
            
            fvg_bull_top[i] = last_bull_top
            fvg_bull_bottom[i] = last_bull_bottom
            fvg_bear_top[i] = last_bear_top
            fvg_bear_bottom[i] = last_bear_bottom
        
        return fvg_bull_top, fvg_bull_bottom, fvg_bear_top, fvg_bear_bottom
    
    def calculate_pd_zone(
        self,
        close: np.ndarray,
        swing_high_prices: np.ndarray,
        swing_high_idx: np.ndarray,
        swing_low_prices: np.ndarray,
        swing_low_idx: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate Premium/Discount Zone
        
        Returns:
            pd_zone: 1=premium, -1=discount, 0=neutral
            pd_level: 0-1 position within range
        """
        n = len(close)
        pd_zone = np.zeros(n, dtype=int)
        pd_level = np.full(n, 0.5)
        
        # Use rolling swing high/low
        last_sh = 0.0
        last_sl = float('inf')
        sh_ptr = 0
        sl_ptr = 0
        
        for i in range(n):
            # Update swings
            while sh_ptr < len(swing_high_idx) and swing_high_idx[sh_ptr] <= i:
                last_sh = swing_high_prices[sh_ptr]
                sh_ptr += 1
            while sl_ptr < len(swing_low_idx) and swing_low_idx[sl_ptr] <= i:
                last_sl = swing_low_prices[sl_ptr]
                sl_ptr += 1
            
            if last_sh > 0 and last_sl < float('inf') and last_sh > last_sl:
                range_ = last_sh - last_sl
                position = (close[i] - last_sl) / range_
                pd_level[i] = position
                
                if position >= self.premium_level:
                    pd_zone[i] = 1  # Premium
                elif position <= self.discount_level:
                    pd_zone[i] = -1  # Discount
        
        return pd_zone, pd_level
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from OHLC data
        
        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close']
            
        Returns:
            DataFrame with signals and all SMC components
        """
        # Extract arrays
        open_ = df['open'].values
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        n = len(close)
        
        # Calculate ATR
        atr = self.calculate_atr(high, low, close, self.atr_period)
        
        # Detect swing points
        sh_idx, sh_prices, sl_idx, sl_prices = self.detect_swing_points(
            high, low, self.ltf_swing_len
        )
        
        # Determine structure
        bias, bos, choch = self.determine_structure(
            close, sh_idx, sh_prices, sl_idx, sl_prices
        )
        
        # Detect Order Blocks
        ob_bull_high, ob_bull_low, ob_bear_high, ob_bear_low = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
        if self.use_ob:
            ob_bull_high, ob_bull_low, ob_bear_high, ob_bear_low = self.detect_order_blocks(
                open_, high, low, close, bias, bos, choch, atr
            )
        
        # Detect FVG
        fvg_bull_top, fvg_bull_bottom, fvg_bear_top, fvg_bear_bottom = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
        if self.use_fvg:
            fvg_bull_top, fvg_bull_bottom, fvg_bear_top, fvg_bear_bottom = self.detect_fvg(
                high, low, close, atr
            )
        
        # Calculate P/D Zone
        pd_zone, pd_level = np.zeros(n, dtype=int), np.full(n, 0.5)
        if self.use_pd_zone:
            pd_zone, pd_level = self.calculate_pd_zone(
                close, sh_prices, sh_idx, sl_prices, sl_idx
            )
        
        # Generate entry signals
        entries_long = np.zeros(n, dtype=bool)
        entries_short = np.zeros(n, dtype=bool)
        sl_long = np.full(n, np.nan)
        sl_short = np.full(n, np.nan)
        tp_long = np.full(n, np.nan)
        tp_short = np.full(n, np.nan)
        
        for i in range(1, n):
            # ═══════════════════════════════════════════════════════
            # LONG ENTRY CONDITIONS:
            # 1. Bias = Bullish
            # 2. P/D Zone = Discount (or disabled)
            # 3. Price at OB or FVG zone (or structure entry)
            # ═══════════════════════════════════════════════════════
            if bias[i] == 1:  # Bullish bias
                pd_ok = (not self.use_pd_zone) or (pd_zone[i] == -1)  # Discount
                
                if pd_ok:
                    # Check OB entry
                    ob_entry = False
                    if self.use_ob and not np.isnan(ob_bull_high[i]):
                        if low[i] <= ob_bull_high[i] and close[i] >= ob_bull_low[i]:
                            ob_entry = True
                            sl_long[i] = ob_bull_low[i] - atr[i] * 0.2
                    
                    # Check FVG entry
                    fvg_entry = False
                    if self.use_fvg and not np.isnan(fvg_bull_top[i]):
                        if close[i] <= fvg_bull_top[i] and close[i] >= fvg_bull_bottom[i]:
                            fvg_entry = True
                            if np.isnan(sl_long[i]):
                                sl_long[i] = fvg_bull_bottom[i] - atr[i] * 0.2
                    
                    # Structure entry (if no OB/FVG required)
                    struct_entry = False
                    if not self.use_ob and not self.use_fvg:
                        if bos[i] == 1 or choch[i] == 1:
                            struct_entry = True
                            sl_long[i] = low[i] - atr[i] * 1.5
                    
                    if ob_entry or fvg_entry or struct_entry:
                        entries_long[i] = True
                        risk = close[i] - sl_long[i]
                        tp_long[i] = close[i] + risk * self.rr_ratio
            
            # ═══════════════════════════════════════════════════════
            # SHORT ENTRY CONDITIONS
            # ═══════════════════════════════════════════════════════
            if bias[i] == -1:  # Bearish bias
                pd_ok = (not self.use_pd_zone) or (pd_zone[i] == 1)  # Premium
                
                if pd_ok:
                    ob_entry = False
                    if self.use_ob and not np.isnan(ob_bear_low[i]):
                        if high[i] >= ob_bear_low[i] and close[i] <= ob_bear_high[i]:
                            ob_entry = True
                            sl_short[i] = ob_bear_high[i] + atr[i] * 0.2
                    
                    fvg_entry = False
                    if self.use_fvg and not np.isnan(fvg_bear_bottom[i]):
                        if close[i] >= fvg_bear_bottom[i] and close[i] <= fvg_bear_top[i]:
                            fvg_entry = True
                            if np.isnan(sl_short[i]):
                                sl_short[i] = fvg_bear_top[i] + atr[i] * 0.2
                    
                    struct_entry = False
                    if not self.use_ob and not self.use_fvg:
                        if bos[i] == -1 or choch[i] == -1:
                            struct_entry = True
                            sl_short[i] = high[i] + atr[i] * 1.5
                    
                    if ob_entry or fvg_entry or struct_entry:
                        entries_short[i] = True
                        risk = sl_short[i] - close[i]
                        tp_short[i] = close[i] - risk * self.rr_ratio
        
        # Build result DataFrame
        result = df.copy()
        result['atr'] = atr
        result['bias'] = bias
        result['bos'] = bos
        result['choch'] = choch
        result['ob_bull_high'] = ob_bull_high
        result['ob_bull_low'] = ob_bull_low
        result['ob_bear_high'] = ob_bear_high
        result['ob_bear_low'] = ob_bear_low
        result['fvg_bull_top'] = fvg_bull_top
        result['fvg_bull_bottom'] = fvg_bull_bottom
        result['fvg_bear_top'] = fvg_bear_top
        result['fvg_bear_bottom'] = fvg_bear_bottom
        result['pd_zone'] = pd_zone
        result['pd_level'] = pd_level
        result['entry_long'] = entries_long
        result['entry_short'] = entries_short
        result['sl_long'] = sl_long
        result['sl_short'] = sl_short
        result['tp_long'] = tp_long
        result['tp_short'] = tp_short
        
        return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def resample_to_htf(df: pd.DataFrame, htf: str) -> pd.DataFrame:
    """Resample LTF data to HTF for multi-timeframe analysis"""
    return df.resample(htf).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum' if 'volume' in df.columns else 'first'
    }).dropna()


def get_htf_bias(htf_df: pd.DataFrame, ltf_df: pd.DataFrame, engine: SMCEngine) -> np.ndarray:
    """
    Get HTF bias for each LTF bar
    
    This allows multi-timeframe analysis where HTF determines bias
    and LTF determines entry
    """
    # Generate HTF signals
    htf_signals = engine.generate_signals(htf_df)
    
    # Map HTF bias to LTF timeframe
    htf_bias = htf_signals['bias']
    
    # Forward fill to LTF
    ltf_bias = np.zeros(len(ltf_df))
    
    htf_times = htf_df.index
    ltf_times = ltf_df.index
    
    htf_ptr = 0
    for i, t in enumerate(ltf_times):
        while htf_ptr < len(htf_times) - 1 and htf_times[htf_ptr + 1] <= t:
            htf_ptr += 1
        if htf_ptr < len(htf_bias):
            ltf_bias[i] = htf_bias.iloc[htf_ptr]
    
    return ltf_bias


# =============================================================================
# TEST
# =============================================================================
if __name__ == "__main__":
    print("SMC Engine loaded successfully")
    print("Use: engine = SMCEngine(); signals = engine.generate_signals(df)")
