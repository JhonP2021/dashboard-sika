"""Frecuencia de incidencias, independiente del sigma reportado de main."""
from __future__ import annotations

import numpy as np
import pandas as pd


def valid_weighings(df: pd.DataFrame, silo: int) -> pd.Series:
    """Filas en las que ese silo dosificó de verdad.

    Criterio único para toda la app. Un silo que no participa en la fórmula se
    reporta con objetivo 0 y real 0, y su 0% entra en cualquier promedio que no
    lo excluya: el Silo 1 sólo dosifica en el 9,5% de los batches, así que su
    sigma sobre todas las filas mide más con qué frecuencia se usa que con qué
    precisión pesa. También se descarta el objetivo 0 con real distinto de 0,
    donde el porcentaje reportado no es evaluable.
    """
    def numeric(column):
        return pd.to_numeric(df.get(column, pd.Series(index=df.index, dtype=float)), errors="coerce")

    target, actual, pct = numeric(f"Silo{silo}Target"), numeric(f"Silo{silo}Real"), numeric(f"Silo {silo}_pct")
    if f"Silo{silo}Target" not in df or f"Silo{silo}Real" not in df:
        return pct.notna()
    return target.gt(0) & actual.ge(0) & np.isfinite(target) & np.isfinite(actual) & pct.notna()


def silo_incidents(df: pd.DataFrame, silo: int, tolerance: float = 5.0,
                   materials: list[str] | None = None) -> dict:
    def numeric(column):
        return pd.to_numeric(df.get(column, pd.Series(index=df.index, dtype=float)), errors="coerce")

    pct = numeric(f"Silo {silo}_pct")
    target, actual = numeric(f"Silo{silo}Target"), numeric(f"Silo{silo}Real")
    scope = pd.Series(True, index=df.index)
    if materials and f"Silo {silo}_material" in df:
        scope = df[f"Silo {silo}_material"].isin(materials)
    finite_weights = np.isfinite(target) & np.isfinite(actual)
    unused = target.eq(0) & actual.eq(0)
    no_target = scope & finite_weights & target.eq(0) & actual.gt(0)
    valid = scope & finite_weights & target.gt(0) & actual.ge(0) & np.isfinite(pct)
    outside = valid & pct.abs().gt(tolerance)
    extreme = valid & pct.abs().gt(2 * tolerance)
    zero_real = scope & finite_weights & target.gt(0) & actual.eq(0)
    invalid = scope & ~unused & ~no_target & ~valid
    count = int(valid.sum())
    return {
        "evaluated": count,
        "outside": int(outside.sum()),
        "extreme": int(extreme.sum()),
        "zero_real": int(zero_real.sum()),
        "extreme_zero_real": int((extreme & zero_real).sum()),
        "no_target": int(no_target.sum()),
        "invalid": int(invalid.sum()),
        "compliance_pct": 100 * (count - int(outside.sum())) / count if count else None,
    }
