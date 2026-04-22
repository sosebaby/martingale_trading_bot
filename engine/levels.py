"""
engine/levels.py
════════════════════════════════════════════════════════
ROLE: Pure math — calculates lot sizes, SL/TP prices,
      and profit targets at every martingale level.

No trading happens here. No Telegram. No MT5.
Just numbers in, numbers out.
════════════════════════════════════════════════════════
"""


class MartingaleLevels:
    """
    Calculates all values for each martingale level.

    Level Logic:
    ┌───────┬──────────┬──────────┬────────────────────────────┐
    │ Level │ Lot Size │ SL Pips  │ TP Pips                    │
    ├───────┼──────────┼──────────┼────────────────────────────┤
    │  1    │  base    │ sl_pips  │ tp_pips                    │
    │  2    │  2x base │ sl_pips  │ tp_pips × 1.5              │
    │  3    │  4x base │ sl_pips  │ tp_pips × 1.5²             │
    │  4    │  8x base │ sl_pips  │ tp_pips × 1.5³             │
    └───────┴──────────┴──────────┴────────────────────────────┘
    SL pips never changes. Lots double. TP grows 50% each level.
    """

    def __init__(self, base_lot: float, sl_pips: int, tp_pips: int,
                 tp_escalation: float = 0.5, max_levels: int = 6):
        self.base_lot      = base_lot
        self.sl_pips       = sl_pips          # Fixed forever
        self.tp_pips       = tp_pips          # Level 1 TP
        self.tp_escalation = tp_escalation    # 0.5 = 50% increase
        self.max_levels    = max_levels

    def get_lot_size(self, level: int) -> float:
        """Doubles with each level: 1→2→4→8→16..."""
        return round(self.base_lot * (2 ** (level - 1)), 2)

    def get_tp_pips(self, level: int) -> float:
        """Grows by escalation factor each level: 50→75→112→168..."""
        return self.tp_pips * ((1 + self.tp_escalation) ** (level - 1))

    def get_sl_pips(self) -> int:
        """SL never changes."""
        return self.sl_pips

    def get_sl_price(self, entry: float, direction: str,
                     pip_size: float) -> float:
        """Calculate actual SL price from entry."""
        dist = self.sl_pips * pip_size
        return round(entry - dist if direction == "BUY" else entry + dist, 5)

    def get_tp_price(self, entry: float, direction: str,
                     pip_size: float, level: int) -> float:
        """Calculate actual TP price from entry at given level."""
        dist = self.get_tp_pips(level) * pip_size
        return round(entry + dist if direction == "BUY" else entry - dist, 5)

    def is_max_level(self, level: int) -> bool:
        return level > self.max_levels

    def print_table(self):
        """Print a summary table of all levels — useful for debugging."""
        print(f"\n{'─'*65}")
        print(f"  MARTINGALE LEVELS  (base={self.base_lot}, "
              f"SL={self.sl_pips}pip, TP={self.tp_pips}pip)")
        print(f"{'─'*65}")
        print(f"  {'Level':<8} {'Lots':<10} {'SL (pips)':<12} {'TP (pips)':<12}")
        print(f"{'─'*65}")
        for lvl in range(1, self.max_levels + 1):
            print(f"  {lvl:<8} {self.get_lot_size(lvl):<10.2f} "
                  f"{self.sl_pips:<12} {self.get_tp_pips(lvl):<12.1f}")
        print(f"{'─'*65}\n")