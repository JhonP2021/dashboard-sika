"""Regenera config/materials_map.csv a partir de los CSV de producción.

Uso:  python scripts/build_materials_map.py
El CSV resultante es editable a mano: la columna `canonico` manda.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from config.settings import get_settings  # noqa: E402
from src.models.material_normalizer import (  # noqa: E402
    cluster_variants,
    family_and_spec,
    normalize_description,
)

SLOTS = [f"Silo{i}" for i in range(1, 13)] + ["SiloP1", "SiloP2", "Oil"]
OUTPUT = REPO_ROOT / "config" / "materials_map.csv"
COLUMNS = ["familia", "variante", "canonico", "usos", "usos_grupo",
           "code_dominante", "n_codes", "revisar"]


def load_slot_usage() -> pd.DataFrame:
    """Apila los 15 pares (code, des) en una sola tabla larga y la normaliza."""
    settings = get_settings()
    columns = [f"{slot}{suffix}" for slot in SLOTS for suffix in ("Code", "Des")]
    source = pd.read_csv(
        settings.csv_paths["table_report_m1"], usecols=columns, dtype=str, low_memory=False
    )
    stacked = pd.concat(
        [
            source[[f"{slot}Code", f"{slot}Des"]]
            .rename(columns={f"{slot}Code": "code", f"{slot}Des": "des"})
            .assign(slot=slot)
            for slot in SLOTS
        ],
        ignore_index=True,
    )
    stacked["des"] = stacked["des"].str.strip()
    stacked = stacked[stacked["des"].notna() & (stacked["des"] != "")]
    stacked["norm"] = stacked["des"].map(normalize_description)
    return stacked[stacked["norm"] != ""]


def _reclaim_orphans(distinct: pd.DataFrame) -> pd.DataFrame:
    """Devuelve a su familia las variantes que perdieron la palabra que la nombra.

    El clustering corre dentro de cada familia, así que una descripción a la que
    el operario no le escribió el nombre del polvo ('30/100' a secas) cae en
    OTROS y ya no puede alcanzar a 'ARENA 30/100'. Se reasigna sólo con
    coincidencia exacta contra un spec ya existente -- nada difuso -- para no
    inventar parentescos.
    """
    result = distinct.copy()
    real = result[result["family"] != "OTROS"]
    owner = {}
    for spec, group in real.groupby("spec"):
        families = set(group["family"])
        if spec and len(families) == 1:  # un spec ambiguo entre familias no se toca
            owner[spec] = families.pop()
    orphans = result["family"].eq("OTROS") & result["norm"].isin(owner)
    result.loc[orphans, "spec"] = result.loc[orphans, "norm"]
    result.loc[orphans, "family"] = result.loc[orphans, "norm"].map(owner)
    return result


def build_map(usage: pd.DataFrame) -> pd.DataFrame:
    if usage.empty:
        return pd.DataFrame(columns=COLUMNS)

    distinct = usage["norm"].drop_duplicates().to_frame()
    resolved = distinct["norm"].map(family_and_spec)
    distinct["family"] = [family for family, _ in resolved]
    distinct["spec"] = [spec for _, spec in resolved]
    usage = usage.merge(_reclaim_orphans(distinct), on="norm", how="left")

    distinct = _reclaim_orphans(distinct)
    spec_of = dict(zip(distinct["norm"], distinct["spec"]))
    rows = []
    for family, group in usage.groupby("family"):
        counts = group["norm"].value_counts().to_dict()
        # Los códigos por variante se calculan una sola vez para toda la familia:
        # recorrerlos por cluster reescanea el grupo entero en cada iteración.
        codes_by_norm = group.groupby(["norm", "code"], dropna=False).size()
        # La similitud se mide siempre sobre el spec: en las familias estructuradas
        # ya tiene los sinónimos resueltos y sin el nombre de familia repetido, y
        # en OTROS es el propio texto salvo cuando llevaba una nota del operador
        # ('ESCORIA 325 NO USAR' -> 'ESCORIA 325'), que es justo lo que queremos
        # comparar.
        for cluster in cluster_variants(counts, key=lambda v: spec_of.get(v, v)):
            dominant = (
                codes_by_norm.loc[list(cluster.members)]
                .groupby("code")
                .sum()
                .sort_values(ascending=False)
            )
            for member in cluster.members:
                rows.append({
                    "familia": family, "variante": member, "canonico": cluster.canonical,
                    "usos": counts[member], "usos_grupo": cluster.usage,
                    "code_dominante": dominant.index[0] if len(dominant) else "",
                    "n_codes": len(dominant), "revisar": int(cluster.needs_review),
                })

    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows).sort_values(
        ["usos_grupo", "canonico", "usos"], ascending=[False, True, False]
    )


def main() -> None:
    usage = load_slot_usage()
    if usage.empty:
        raise SystemExit(
            f"No hay descripciones utilizables en {get_settings().csv_paths['table_report_m1']}."
        )

    materials_map = build_map(usage)
    materials_map.to_csv(OUTPUT, index=False)

    print("variantes originales :", usage["des"].nunique())
    print("tras normalizar      :", usage["norm"].nunique())
    print("canonicos finales    :", materials_map["canonico"].nunique())
    print("reduccion total      : %.1f%%" % (
        (1 - materials_map["canonico"].nunique() / usage["des"].nunique()) * 100))
    print()
    print("=== por familia ===")
    print(
        materials_map.groupby("familia")
        .agg(variantes=("variante", "nunique"), canonicos=("canonico", "nunique"),
             usos=("usos", "sum"))
        .sort_values("usos", ascending=False)
        .to_string()
    )


if __name__ == "__main__":
    main()
