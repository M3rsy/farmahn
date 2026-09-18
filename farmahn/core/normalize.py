from __future__ import annotations

import re
import unicodedata


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.upper().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"(?<=\d)\s*MG\b", " MG", value)
    return value


def parse_money(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.upper().replace("LPS", "").replace("L.", "").replace("L", "")
    cleaned = cleaned.replace(",", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def extract_quantity(name: str) -> int | None:
    patterns = [
        r"\bX\s*(\d+)\b",
        r"\b(\d+)\s*(?:TAB(?:LETAS?)?|CAP(?:SULAS?)?|COMP(?:RIMIDOS?)?|UNID(?:ADES?)?)\b",
    ]
    upper = name.upper()
    for pattern in patterns:
        m = re.search(pattern, upper)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


def extract_concentration(name: str) -> str | None:
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(MG|G|MCG|ML|UI)\b", name.upper())
    return f"{m.group(1)} {m.group(2).lower()}" if m else None
