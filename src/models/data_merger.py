from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.settings import get_settings
from src.models.data_cleaner import clean_m1, clean_table_date
from src.models.material_normalizer import load_canonical_map, load_status_canonicals


@dataclass(frozen=True)
class DashboardData:
    table_date: pd.DataFrame
    m1: pd.DataFrame


def status_canonicals() -> set[str]:
    """Nombres que marcan silo sin material, para excluirlos de los gráficos."""
    path = get_settings().materials_map_path
    return load_status_canonicals(path) if path.exists() else set()


def _load_materials() -> dict[str, str] | None:
    """El mapa de materiales es opcional: sin él la app funciona igual, sólo
    pierde el desglose por material."""
    path = get_settings().materials_map_path
    return load_canonical_map(path) if path.exists() else None


def material_long(df: pd.DataFrame, *, exclude: set[str] | None = None) -> pd.DataFrame:
    """Una fila por (batch, silo) con su material y su desviación.

    El ancho es cómodo para la tabla de detalle, pero para agrupar por material
    hace falta el formato largo: cada silo lleva un polvo distinto en cada batch.
    """
    frames = []
    for silo in range(1, 9):
        material, kg, pct = f"Silo {silo}_material", f"Silo {silo}_kg", f"Silo {silo}_pct"
        if material not in df:
            continue
        piece = pd.DataFrame({
            "material": df[material],
            "silo": f"Silo {silo}",
            "kg": pd.to_numeric(df.get(kg), errors="coerce"),
            "pct": pd.to_numeric(df.get(pct), errors="coerce"),
        })
        frames.append(piece)
    if not frames:
        return pd.DataFrame(columns=["material", "silo", "kg", "pct"])
    long = pd.concat(frames, ignore_index=True)
    # Un silo sin material declarado no aporta nada al análisis por polvo.
    long = long[(long["material"] != "") & long["pct"].notna()]
    if exclude:
        long = long[~long["material"].isin(exclude)]
    return long


def _isolate_materials(m1: pd.DataFrame, materials: list[str]) -> pd.DataFrame:
    """Deja sólo la desviación de los materiales pedidos.

    No basta con quedarse con los batches que llevan el polvo: casi todas las
    recetas llevan cemento y carbonato, así que filtrar por fila no descarta
    nada. Lo que se quiere ver es la desviación *de ese polvo*, así que además
    se anulan los silos que en ese batch cargaban otra cosa, y se descartan los
    batches que quedan sin ningún silo del material.
    """
    columns = [silo for silo in range(1, 9) if f"Silo {silo}_material" in m1]
    if not columns:
        return m1
    result = m1.copy()
    selected = pd.DataFrame(
        {silo: result[f"Silo {silo}_material"].isin(materials) for silo in columns}
    )
    for silo in columns:
        keep = selected[silo]
        result.loc[~keep, [f"Silo {silo}_kg", f"Silo {silo}_pct"]] = pd.NA
    return result[selected.any(axis=1)]


def operator_long(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por (batch, silo) con el operario que lo dosificó.

    Mismo formato que `material_long`, pero la dimensión es quién estaba en el
    tablero: separa el error humano del que trae el polvo o el equipo.
    """
    if "OperatorName" not in df:
        return pd.DataFrame(columns=["operario", "silo", "kg", "pct"])
    frames = []
    for silo in range(1, 9):
        pct = f"Silo {silo}_pct"
        if pct not in df:
            continue
        frames.append(pd.DataFrame({
            "operario": df["OperatorName"],
            "silo": f"Silo {silo}",
            "kg": pd.to_numeric(df.get(f"Silo {silo}_kg"), errors="coerce"),
            "pct": pd.to_numeric(df[pct], errors="coerce"),
        }))
    if not frames:
        return pd.DataFrame(columns=["operario", "silo", "kg", "pct"])
    long = pd.concat(frames, ignore_index=True)
    return long[(long["operario"] != "") & long["pct"].notna()]


def prepare_dashboard_data(raw_tables: dict[str, pd.DataFrame]) -> DashboardData:
    """Unifica las lecturas de M1 y conserva únicamente producción desde 2026."""
    sources = [raw_tables.get("table_report_m1", pd.DataFrame()), raw_tables.get("table_report_m1_out", pd.DataFrame())]
    frames = [frame for frame in sources if not frame.empty]
    raw_m1 = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    raw_dedupe_columns = [column for column in ["ReportDate", "ReportTime", "RecipeBB1name", "NumberBatchDone1", "OperatorName"] if column in raw_m1]
    if raw_dedupe_columns:
        raw_m1 = raw_m1.drop_duplicates(subset=raw_dedupe_columns, keep="last")
    m1 = clean_m1(raw_m1, materials=_load_materials())
    return DashboardData(table_date=clean_table_date(raw_tables.get("table_date", pd.DataFrame())), m1=m1)


def apply_dashboard_filters(
    dataset: DashboardData,
    *,
    date_range: tuple | None = None,
    formula_keys: list[str] | None = None,
    operators: list[str] | None = None,
    lots: list[str] | None = None,
    batch_range: tuple[int, int] | None = None,
    materials: list[str] | None = None,
) -> DashboardData:
    m1 = dataset.m1.copy()
    if date_range and "report_day" in m1:
        start, end = date_range
        m1 = m1[(m1["report_day"] >= start) & (m1["report_day"] <= end)]
    if formula_keys:
        m1 = m1[m1["formula_key"].isin(formula_keys)]
    if operators and "OperatorName" in m1:
        m1 = m1[m1["OperatorName"].astype(str).isin(operators)]
    if lots and "LOTE" in m1:
        m1 = m1[m1["LOTE"].astype(str).isin(lots)]
    if batch_range and "NumberBatchDone1" in m1:
        m1 = m1[m1["NumberBatchDone1"].between(*batch_range)]
    if materials:
        m1 = _isolate_materials(m1, materials)
    return DashboardData(table_date=dataset.table_date, m1=m1)
