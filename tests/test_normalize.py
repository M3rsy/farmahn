from farmahn.core.normalize import (
    canonical_product_key,
    extract_concentration,
    extract_dosage_form,
    extract_quantity,
    relevance_score,
)


def test_extract_medicine_fields():
    name = "METFORMINA 850MG X 30 TABLETAS"
    assert extract_concentration(name) == "850 mg"
    assert extract_quantity(name) == 30
    assert extract_dosage_form(name) == "tableta"


def test_canonical_key_keeps_concentration_and_quantity():
    a = canonical_product_key("METFORMINA 500MG X30 TAB")
    b = canonical_product_key("METFORMINA 850MG X30 TAB")
    c = canonical_product_key("METFORMINA 850MG X60 TAB")
    assert a != b
    assert b != c


def test_relevance_prefers_matching_name():
    exact = relevance_score("losartan 100", "LOSARTAN 100 MG X30 TABLETAS")
    other = relevance_score("losartan 100", "PARACETAMOL 500 MG X20 TABLETAS")
    assert exact > other
