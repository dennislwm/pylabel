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
        "Set": "set",
        "Expense": "expense",
        "Sale": "price_menu",
        "Platform": "platform",
        "Vendor": "vendor",
        "Date": "date",
    },
    "derived": {
        "owner": "Player",
        "type": "Type",
        "url": ["Set", "Type"],
    },
}

LOOKUPS = {
    "graded_prefixes": ["PSA", "BGS", "CGC", "SGC"],
    "non_english_prefixes": ["JP ", "KR ", "ME "],
    "owner_codes": {"BG": "brigette"},
    "type_slugs": {"Booster Box": "booster-box"},
}


def run_convert(rows):
    with tempfile.TemporaryDirectory() as d:
        mapping_path = os.path.join(d, "mapping.json")
        lookups_path = os.path.join(d, "lookups.json")
        input_path = os.path.join(d, "input.csv")
        output_path = os.path.join(d, "output.csv")

        with open(mapping_path, "w") as f:
            json.dump(MAPPING, f)
        with open(lookups_path, "w") as f:
            json.dump(LOOKUPS, f)

        fieldnames = ["Set", "Date", "Expense", "Sale", "Platform", "Vendor", "Player", "Type"]
        with open(input_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        convert(mapping_path, input_path, output_path)

        with open(output_path, newline="") as f:
            return list(csv.DictReader(f))


# REQ-003: TST-007
def test_sealed_english_url_derived():
    rows = run_convert([{
        "Set": "SV08 Surging Sparks", "Date": "2026-06-30", "Expense": "10.00",
        "Sale": "", "Platform": "", "Vendor": "", "Player": "", "Type": "Booster Box",
    }])
    assert rows[0]["url"] == "https://www.pricecharting.com/game/pokemon-sv08-surging-sparks/booster-box"
    assert rows[0]["type"] == "Booster Box"


# REQ-003: TST-008
def test_graded_row_blanks_type_and_url():
    for prefix in ["PSA 10", "BGS 9.5", "psa 9"]:
        rows = run_convert([{
            "Set": "SV08 Surging Sparks", "Date": "2026-06-30", "Expense": "10.00",
            "Sale": "", "Platform": "", "Vendor": "", "Player": "", "Type": prefix,
        }])
        assert rows[0]["type"] == "", f"type should be blank for {prefix!r}"
        assert rows[0]["url"] == "", f"url should be blank for {prefix!r}"


# REQ-003: TST-009
def test_non_english_set_blanks_url_keeps_type():
    rows = run_convert([{
        "Set": "JP S10b Pokemon Go", "Date": "2026-06-30", "Expense": "10.00",
        "Sale": "", "Platform": "", "Vendor": "", "Player": "", "Type": "Booster Box",
    }])
    assert rows[0]["url"] == ""
    assert rows[0]["type"] == "Booster Box"
