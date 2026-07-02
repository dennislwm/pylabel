import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from convert import convert

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
    assert rows[0]["url"] == "https://www.pricecharting.com/game/pokemon-sv08-surging-sparks/booster-box"
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
