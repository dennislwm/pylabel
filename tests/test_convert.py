import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from convert import convert, find_blank_derived_fields, set_to_slug

MAPPING = {
    "doc_id": "test",
    "table_id": "test",
    "columns": {
        "RefId": "refid",
        "Owner": "owner",
        "Set": "set",
        "Date": "date",
        "Vendor": "vendor",
        "Platform": "platform",
    },
    "filter": "Printed != 'True'",
    "derived": {
        "expense": "{{ (Qty|float * Price|float)|money if Qty and Price else Expense }}",
        "qty": "{{ Qty if Qty and Price else 1 }}",
        "price": "{{ Price if Qty and Price else Expense }}",
        "type": "{% if Type == 'Raw' %}{% set name, number = Character|split_card_number %}{{ name }} | {{ number }}{% elif Type.upper().startswith(graded_prefixes) %}{% set name, number = Character|split_card_number %}{{ Type }} | {{ name }} | {{ number }}{% else %}{{ Type }}{% endif %}",
        "url": "{% set blocked = Type == 'Raw' or Type.upper().startswith(graded_prefixes) or Set.startswith(non_english_prefixes) %}{% set slug = Type|type_slug %}{% if not blocked and slug %}https://www.pricecharting.com/game/pokemon-{{ Set|slugify }}/{{ slug }}{% endif %}",
    },
}

LOOKUPS = {
    "graded_prefixes": ["PSA", "BGS", "CGC", "SGC"],
    "non_english_prefixes": ["JP ", "KR ", "ME "],
    "type_slugs": {"Booster Box": "booster-box"},
}

FIELDNAMES = ["RefId", "Owner", "Set", "Date", "Vendor", "Platform", "Type",
              "Character", "Qty", "Price", "Expense", "Printed"]

ROW_DEFAULTS = {name: "" for name in FIELDNAMES}


def run_convert(rows, tail=None, mapping=None):
    with tempfile.TemporaryDirectory() as d:
        mapping_path = os.path.join(d, "mapping.json")
        lookups_path = os.path.join(d, "lookups.json")
        input_path = os.path.join(d, "input.csv")
        output_path = os.path.join(d, "output.csv")

        with open(mapping_path, "w") as f:
            json.dump(mapping if mapping is not None else MAPPING, f)
        with open(lookups_path, "w") as f:
            json.dump(LOOKUPS, f)

        with open(input_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows({**ROW_DEFAULTS, **row} for row in rows)

        convert(mapping_path, input_path, output_path, tail=tail)

        with open(output_path, newline="") as f:
            return list(csv.DictReader(f))


# REQ-003: TST-007
def test_sealed_english_url_derived():
    rows = run_convert([{
        "Set": "SV08 Surging Sparks", "Date": "2026-06-30", "Expense": "10.00", "Type": "Booster Box",
    }])
    assert rows[0]["url"] == "https://www.pricecharting.com/game/pokemon-surging-sparks/booster-box"
    assert rows[0]["type"] == "Booster Box"


# REQ-003: TST-008
def test_graded_row_composes_grade_character_number():
    rows = run_convert([{
        "Set": "SV08 Surging Sparks", "Date": "2026-06-30", "Expense": "10.00",
        "Type": "PSA10", "Character": "Pikachu 218",
    }])
    assert rows[0]["type"] == "PSA10 | Pikachu | 218"
    assert rows[0]["url"] == ""


# REQ-003: TST-009
def test_non_english_set_blanks_url_keeps_type():
    rows = run_convert([{
        "Set": "JP S10b Pokemon Go", "Date": "2026-06-30", "Expense": "10.00", "Type": "Booster Box",
    }])
    assert rows[0]["url"] == ""
    assert rows[0]["type"] == "Booster Box"


# REQ-003: TST-010
def test_singles_row_composes_character_number():
    rows = run_convert([{
        "Set": "SV08 Surging Sparks", "Date": "2026-06-30", "Expense": "10.00",
        "Type": "Raw", "Character": "Charizard ex 125",
    }])
    assert rows[0]["type"] == "Charizard ex | 125"
    assert rows[0]["url"] == ""


# REQ-003: TST-011
def test_expense_computed_from_qty_and_price():
    rows = run_convert([{
        "Set": "SV08 Surging Sparks", "Date": "2026-06-30", "Expense": "10.00",
        "Type": "Booster Box", "Qty": "3", "Price": "1380",
    }])
    assert rows[0]["expense"] == "4140"
    assert rows[0]["qty"] == "3"
    assert rows[0]["price"] == "1380"


# REQ-003: TST-012
def test_expense_falls_back_when_qty_or_price_blank():
    rows = run_convert([{
        "Set": "SV08 Surging Sparks", "Date": "2026-06-30", "Expense": "268.95", "Type": "Booster Box",
    }])
    assert rows[0]["expense"] == "268.95"
    assert rows[0]["qty"] == "1"
    assert rows[0]["price"] == "268.95"


# REQ-003: TST-013
def test_printed_rows_are_filtered_out():
    rows = run_convert([
        {"Set": "A", "Date": "2026-06-30", "Expense": "10.00", "Type": "Booster Box", "Printed": "True"},
        {"Set": "B", "Date": "2026-06-29", "Expense": "10.00", "Type": "Booster Box", "Printed": "False"},
    ])
    assert len(rows) == 1
    assert rows[0]["set"] == "B"


# REQ-003: TST-014
def test_no_filter_key_keeps_all_rows():
    mapping_no_filter = {k: v for k, v in MAPPING.items() if k != "filter"}
    rows = run_convert([
        {"Set": "A", "Date": "2026-06-30", "Expense": "10.00", "Type": "Booster Box", "Printed": "True"},
    ], mapping=mapping_no_filter)
    assert len(rows) == 1


# REQ-003: TST-015
def test_refid_passthrough():
    rows = run_convert([{
        "RefId": "1251", "Set": "SV08 Surging Sparks", "Date": "2026-06-30",
        "Expense": "10.00", "Type": "Booster Box",
    }])
    assert rows[0]["refid"] == "1251"


PYLABEL_GRADED_MAPPING = os.path.join(os.path.dirname(__file__), '..', 'mappings', 'pylabel-graded.json')
LEDGER_MAPPING = os.path.join(os.path.dirname(__file__), '..', 'mappings', 'trackmycollection_pylabel_ledger.json')

GRADED_FIELDNAMES = ["RefId", "Owner", "Set", "Date", "Vendor", "Serial No", "Qty", "Price",
                     "Expense", "Card No", "Type", "Character", "Printed"]

LEDGER_FIELDNAMES = ["Owner", "Expense", "Set", "Date", "Vendor", "Player", "Type", "Printed",
                     "RefId", "Platform", "Qty", "Price", "Character", "Serial No"]


def run_convert_with_file(mapping_path, rows, fieldnames):
    with tempfile.TemporaryDirectory() as d:
        input_path = os.path.join(d, "input.csv")
        output_path = os.path.join(d, "output.csv")
        with open(input_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        convert(mapping_path, input_path, output_path)
        with open(output_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


# REQ-003: TST-022 (real pylabel-graded.json, Japanese graded row -> SnkrDunk keyed by Card No)
def test_snkrdunk_url_keyed_by_card_number_for_graded():
    rows = run_convert_with_file(PYLABEL_GRADED_MAPPING, [{
        "RefId": "1", "Owner": "DL", "Set": "JP M2a Mega Dream", "Date": "2026-03-15",
        "Vendor": "Test", "Serial No": "157768060", "Qty": "", "Price": "",
        "Expense": "427", "Card No": "240", "Type": "PSA10", "Character": "Mega Gengar", "Printed": "False",
    }], GRADED_FIELDNAMES)
    assert rows[0]["url"] == "https://snkrdunk.com/apparels/724996"


# REQ-003: TST-023 (real Ledger mapping, Japanese sealed row -> SnkrDunk keyed by Type, no Card No exists)
def test_snkrdunk_url_keyed_by_type_for_sealed():
    rows = run_convert_with_file(LEDGER_MAPPING, [{
        "Owner": "DL", "Expense": "156.21", "Set": "JP M5 Abyss Eye", "Date": "2026-06-22",
        "Vendor": "Test", "Player": "", "Type": "Booster Box", "Printed": "False",
        "RefId": "1272", "Platform": "Buyandship", "Qty": "2", "Price": "78.11",
        "Character": "", "Serial No": "",
    }], LEDGER_FIELDNAMES)
    assert rows[0]["url"] == "https://snkrdunk.com/apparels/806644"


# REQ-003: TST-024 (real pylabel-graded.json, non-Japanese graded row -> PriceCharting search URL, not a guessed slug)
def test_pricecharting_search_url_for_non_japanese_graded():
    rows = run_convert_with_file(PYLABEL_GRADED_MAPPING, [{
        "RefId": "2", "Owner": "Top", "Set": "ME02 Phantasmal Flames", "Date": "2026-03-15",
        "Vendor": "Test", "Serial No": "157768050", "Qty": "", "Price": "",
        "Expense": "47", "Card No": "109/094", "Type": "PSA9", "Character": "Mega Charizard", "Printed": "False",
    }], GRADED_FIELDNAMES)
    assert rows[0]["url"].startswith("https://www.pricecharting.com/search-products?type=prices&q=")


# REQ-003: TST-031
def test_find_blank_derived_fields_lists_rows_and_omits_clean_fields():
    rows_out = [
        {"refid": "1", "url": "", "price_menu": "15.00", "expense": "10.00"},
        {"refid": "2", "url": "https://x.com", "price_menu": "", "expense": "20.00"},
        {"refid": "", "owner": "alice", "url": "", "price_menu": "", "expense": "5.00"},
    ]
    blanks = find_blank_derived_fields(rows_out, ["url", "price_menu", "expense"])
    assert blanks == {"url": ["1", "alice"], "price_menu": ["2", "alice"]}
    assert "expense" not in blanks


# REQ-003: TST-030 (real Ledger mapping, English Raw row -> PriceCharting search URL, not blank)
def test_pricecharting_search_url_for_ledger_english_raw():
    rows = run_convert_with_file(LEDGER_MAPPING, [{
        "Owner": "DL", "Expense": "10.00", "Set": "SV08 Surging Sparks", "Date": "2026-06-30",
        "Vendor": "Test", "Player": "", "Type": "Raw", "Printed": "False",
        "RefId": "1300", "Platform": "Shopee", "Qty": "", "Price": "",
        "Character": "Charizard ex 125", "Serial No": "",
    }], LEDGER_FIELDNAMES)
    assert rows[0]["url"].startswith("https://www.pricecharting.com/search-products?type=prices&q=")


# REQ-003: TST-032
def test_set_to_slug_strips_dotted_set_code_prefix():
    assert set_to_slug("SV08.5 Prismatic Evolutions") == "prismatic-evolutions"
    assert set_to_slug("SV08 Surging Sparks") == "surging-sparks"
