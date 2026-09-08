"""Estandarización de los materiales dosificados (descripciones de silo).

Los operadores escriben a mano el nombre del material en cada silo, así que el
mismo polvo aparece como 'PM ENCHAPE', 'pm enchape', 'PM  ENCHAPE' o
'PM ENCAHPE'. Además el HMI trunca el campo a 20 caracteres, de modo que
'PM CERAM 100 CERAMICO' llega como 'PM CERAM 100 CERAMIC'.

La estandarización va en tres pasos, de más seguro a más agresivo:

1. `normalize_description`  - sólo cosmético (mayúsculas, tildes, ñ, espacios,
   puntuación, códigos incrustados). Nunca fusiona materiales distintos.
2. `family_and_spec`        - reglas por familia. Los números son significativos
   (ARENA #8 != ARENA 8/30), así que aquí no hay fuzzy: sólo sinónimos.
3. `cluster_variants`       - fuzzy sobre el resto (typos y truncados), con la
   guarda de que dos variantes con números distintos jamás se fusionan.

El resultado se materializa en `config/materials_map.csv`, que es el diccionario
revisable a mano y la única fuente de verdad en producción.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable
import difflib
import re
import unicodedata


_EMBEDDED_CODE = re.compile(r"\b\d{6,}\b")
_MESH_MARKS = re.compile(r"[·•∙*]")
_NUMERIC_TOKEN = re.compile(r"\d+")
_ALPHA = re.compile(r"[^A-Z]")

# Marcadores de "sin dato" que el operador escribe en el campo de material.
_NULLISH = {"nan", "none", "na", "n/a", "-", "--", "?", "."}

# Errores de tipeo observados en los datos. Se aplican como palabra completa.
_TYPO_SYNONYMS = {
    "GRUSA": "", "F.G": "FG", "FG": "FG",
    "OMMYA": "OMYA", "OMYACARB": "OMYA", "OMYA-CARB": "OMYA",
    "CEMENTOS": "CEMENTO", "CTO": "CEMENTO",
    "BCO": "BLANCO", "BLNACO": "BLANCO", "BLACO": "BLANCO",
    "TIII": "3", "TIPO3": "3", "T3": "3", "TIPO": "", "T": "",
}

# Textos que el operador usa para marcar que el silo NO lleva material.
# No son materiales y deben excluirse del análisis de desviación.
_STATUS_MARKER = re.compile(
    r"\bVAC[IS]O\b|\bVASIO\b|FUERA DE SERV\w*|MANTENIMIENT\w*|\bNO USAR\b|"
    r"\bLIMPIEZA\b|\bSIN USO\b|\bDISPONIB\w*"
)

# Familias en orden de prioridad: la primera que casa, gana.
_FAMILY_RULES: list[tuple[str, re.Pattern]] = [
    ("ARENA", re.compile(r"\bAR[FNR]?ENA[A-Z]*|\bFINA\s*GRUESA\b|\bFG\b|\bGRUSA\b")),
    ("CEMENTO", re.compile(r"\bCEMENTO?S?\b|\bCTO\b")),
    ("OMYA", re.compile(r"\bOM+YA\w*\b|\bCARBONATO\b")),
    ("CENIZA", re.compile(r"\bCENIZA\b")),
    ("PM", re.compile(r"^PM\b|^PM(?=[A-Z])")),
]


def strip_accents(text: str) -> str:
    """Quita tildes y convierte ñ->N.

    La ñ importa: en los datos conviven 'ESTUKA PAÑETE' y 'ESTUKA PANETE'
    para el mismo producto.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_description(value: object) -> str:
    """Normalización cosmética: no toma ninguna decisión semántica."""
    if value is None:
        return ""
    text = str(value)
    if not text.strip() or text.strip().lower() in _NULLISH:
        return ""

    text = strip_accents(text).upper()
    text = _EMBEDDED_CODE.sub(" ", text)
    text = _MESH_MARKS.sub("#", text)
    text = re.sub(r"\bF\s*\.?\s*G\b", "FG", text)
    text = re.sub(r"[.,;:]", " ", text)
    text = re.sub(r"\s*#\s*", " #", text)
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def numeric_signature(text: str) -> tuple[str, ...]:
    """Números presentes en la descripción, en orden.

    Es la guarda contra fusiones falsas: 'PM CERAM 100' y 'PM CERAM 230' se
    parecen mucho como texto pero son productos distintos.
    """
    return tuple(_NUMERIC_TOKEN.findall(text))


def _apply_synonyms(tokens: list[str]) -> list[str]:
    result = []
    for token in tokens:
        replacement = _TYPO_SYNONYMS.get(token, token)
        if replacement:
            result.append(replacement)
    return result


def family_and_spec(normalized: str) -> tuple[str, str]:
    """Separa la familia del material de su especificación.

    'ARENA FG #8' -> ('ARENA', '8');  'PM ENCHAPE GRIS' -> ('PM', 'ENCHAPE GRIS')
    """
    if _STATUS_MARKER.search(normalized):
        # El marcador puede acompañar a un material real ('ESCORIA 325 NO USAR').
        # Sólo es un estado si al quitarlo no queda nada que identifique al polvo.
        residual = _STATUS_MARKER.sub(" ", normalized)
        residual = re.sub(r"\bSILO\b", " ", residual)
        residual = re.sub(r"[^A-Z0-9]+", " ", residual).strip()
        if len(_ALPHA.sub("", residual)) < 3:
            return "ESTADO", normalized
        normalized = residual

    for family, pattern in _FAMILY_RULES:
        if pattern.search(normalized):
            rest = pattern.sub(" ", normalized) if family != "PM" else normalized[2:]
            tokens = _apply_synonyms(rest.replace("#", "").split())
            # El nombre de la familia puede repetirse en el resto
            # ('CEMENTO GRIS CEMENTO' -> spec 'GRIS'). En ARENA, además, FG es
            # marca de familia y no de especificación.
            drop = {family, "FG"} if family == "ARENA" else {family}
            tokens = [t for t in tokens if t not in drop]
            return family, " ".join(tokens).strip()
    return "OTROS", normalized


# Longitud a partir de la cual un nombre puede ser un truncado del HMI (20 car.).
_TRUNCATION_MIN = 18


def _is_distinct_grade(left: str, right: str) -> bool:
    """True si una clave extiende a la otra con tokens de grado, no con un typo.

    'PM CERAM 230' y 'PM CERAM 230 B' se parecen lo bastante como para que el
    umbral difuso los una, pero el sufijo es la referencia comercial: son SKUs
    distintos y existe además un 'PM CERAM 230 BA'. Un typo altera caracteres;
    un grado añade tokens completos al final, y eso es lo que se detecta aquí.
    Si el nombre corto llega al límite de truncado no se aplica: ahí el sufijo
    que falta lo cortó el HMI, no el operador.
    """
    short_tokens, long_tokens = sorted((left.split(), right.split()), key=len)
    if not short_tokens or len(short_tokens) == len(long_tokens):
        return False
    if long_tokens[: len(short_tokens)] != short_tokens:
        return False
    return len(" ".join(short_tokens)) < _TRUNCATION_MIN


@dataclass(frozen=True)
class VariantCluster:
    canonical: str
    members: tuple[str, ...]
    usage: int
    needs_review: bool


def cluster_variants(
    counts: dict[str, int],
    *,
    threshold: float = 0.86,
    key: "Callable[[str], str] | None" = None,
) -> list[VariantCluster]:
    """Agrupa variantes por similitud, respetando la firma numérica.

    `counts` mapea descripción normalizada -> nº de usos. El canónico de cada
    grupo es la variante más usada, que es la que el operador escribe bien la
    mayoría de las veces. `key` proyecta cada variante al texto sobre el que se
    mide la similitud: para las familias con especificación estructurada se
    compara sólo el spec, no el nombre de la familia repetido.
    """
    project = key or (lambda variant: variant)
    by_signature: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for variant in counts:
        by_signature[numeric_signature(project(variant))].append(variant)

    clusters: list[VariantCluster] = []
    for _, variants in by_signature.items():
        # Los más usados primero: se convierten en semilla de su grupo.
        pending = sorted(variants, key=lambda v: (-counts[v], v))
        while pending:
            seed = pending.pop(0)
            members = [seed]
            remaining = []
            seed_key = project(seed)
            for candidate in pending:
                candidate_key = project(candidate)
                if seed_key == candidate_key:
                    members.append(candidate)
                    continue
                ratio = difflib.SequenceMatcher(None, seed_key, candidate_key).ratio()
                # Un truncado a 20 caracteres es prefijo exacto del nombre largo.
                # El truncado ocurre sobre la descripción cruda, y puede ser tanto
                # la semilla como el candidato: el HMI corta la forma más usada
                # igual que la rara, así que hay que mirar en ambos sentidos.
                short, long_ = sorted((seed, candidate), key=len)
                truncated = len(short) >= _TRUNCATION_MIN and long_.startswith(short)
                if _is_distinct_grade(seed_key, candidate_key):
                    remaining.append(candidate)
                    continue
                if ratio >= threshold or truncated:
                    members.append(candidate)
                else:
                    remaining.append(candidate)
            pending = remaining
            usage = sum(counts[m] for m in members)
            clusters.append(
                VariantCluster(
                    canonical=seed,
                    members=tuple(members),
                    usage=usage,
                    # Un grupo de uno no necesita ojo humano; fusionar sí.
                    needs_review=len(members) > 1,
                )
            )
    return sorted(clusters, key=lambda c: -c.usage)


def load_canonical_map(path) -> dict[str, str]:
    """Lee `materials_map.csv` y devuelve variante normalizada -> canónico.

    `keep_default_na=False` es obligatorio: sin él pandas convierte en NaN las
    descripciones que se parecen a un nulo, y la clave del diccionario se
    corrompe. El CSV es editable a mano, así que la columna `canonico` manda
    sobre lo que decidió el clustering.
    """
    import pandas as pd

    frame = pd.read_csv(path, keep_default_na=False, dtype=str)
    return dict(zip(frame["variante"], frame["canonico"]))


def canonical_material(value: object, mapping: dict[str, str]) -> str:
    """Descripción cruda de silo -> nombre canónico del material.

    Si la variante no está en el mapa se devuelve la forma normalizada, que ya
    es mejor que el texto crudo y deja ver qué falta por mapear.
    """
    normalized = normalize_description(value)
    if not normalized:
        return ""
    return mapping.get(normalized, normalized)


def load_status_canonicals(path) -> set[str]:
    """Canónicos de la familia ESTADO ('VACIO', 'MANTENIMIENTO', ...).

    No son polvos, así que su desviación no significa nada y hay que sacarlos
    del análisis por material.
    """
    import pandas as pd

    frame = pd.read_csv(path, keep_default_na=False, dtype=str)
    return set(frame.loc[frame["familia"] == "ESTADO", "canonico"])
