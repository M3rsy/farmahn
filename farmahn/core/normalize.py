from __future__ import annotations

import re
import unicodedata
from rapidfuzz.fuzz import token_set_ratio


DOSAGE_FORMS = {
    "TABLETA": ("TAB", "TABS", "TABLETA", "TABLETAS", "COMPRIMIDO", "COMPRIMIDOS"),
    "CAPSULA": ("CAP", "CAPS", "CAPSULA", "CAPSULAS"),
    "JARABE": ("JARABE", "JBE"),
    "SUSPENSION": ("SUSP", "SUSPENSION"),
    "SOLUCION": ("SOL", "SOLUCION"),
    "CREMA": ("CREMA",),
    "GEL": ("GEL",),
    "GOTAS": ("GOTA", "GOTAS"),
    "AMPOLLA": ("AMP", "AMPOLLA", "AMPOLLAS"),
    "INYECTABLE": ("INY", "INYECTABLE"),
    "SOBRE": ("SOBRE", "SOBRES"),
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.upper().strip()
    value = re.sub(r"[®™]", "", value)
    value = re.sub(r"[^A-Z0-9.%/+ -]", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"(?<=\d)\s*(MG|MCG|G|ML|UI)\b", r" \1", value)
    return value.strip()


def parse_money(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.upper().replace("HNL", "").replace("LPS", "").replace("L.", "").replace("L", "")
    cleaned = cleaned.replace(",", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def extract_quantity(name: str) -> int | None:
    patterns = [
        r"\bX\s*(\d+)\b",
        r"\b(\d+)\s*(?:TAB(?:LETAS?)?|CAP(?:SULAS?)?|COMP(?:RIMIDOS?)?|UNID(?:ADES?)?|SOBRES?|AMP(?:OLLAS?)?)\b",
    ]
    upper = normalize_text(name)
    for pattern in patterns:
        match = re.search(pattern, upper)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
    return None


def extract_concentration(name: str) -> str | None:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(MG|G|MCG|ML|UI)(?:\s*/\s*(\d+(?:\.\d+)?)\s*(ML|G))?\b", normalize_text(name))
    if not match:
        return None
    value = f"{match.group(1)} {match.group(2).lower()}"
    if match.group(3):
        value += f"/{match.group(3)} {match.group(4).lower()}"
    return value


def extract_dosage_form(name: str) -> str | None:
    upper = normalize_text(name)
    for canonical, aliases in DOSAGE_FORMS.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                return canonical.lower()
    return None


def canonical_product_key(name: str) -> str:
    text = normalize_text(name)
    concentration = extract_concentration(text) or ""
    quantity = extract_quantity(text)
    form = extract_dosage_form(text) or ""

    # Retira ruido de empaque, pero conserva marca/principio activo.
    text = re.sub(r"\b(UNIDAD|CAJA|BLISTER|FRASCO|BOTELLA)\b", " ", text)
    text = re.sub(r"\bX\s*\d+\b", " ", text)
    for aliases in DOSAGE_FORMS.values():
        for alias in aliases:
            text = re.sub(rf"\b{re.escape(alias)}\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    suffix = "|".join((concentration, form, str(quantity or "")))
    return f"{text}|{suffix}".strip("|")


def relevance_score(query: str, product_name: str) -> float:
    return float(token_set_ratio(normalize_text(query), normalize_text(product_name)))
