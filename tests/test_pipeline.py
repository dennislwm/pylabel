import csv
import json
import os
import sys
import tempfile
import pytest
from jinja2 import Template as JinjaTemplate
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from convert import convert as run_conversion
from pipeline import QR_ENV, build_payload, load_qr_template, parse_template_meta

QR_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '..', 'templates', 'qr_payload.txt')


@pytest.fixture
def qr_template():
    return load_qr_template(QR_TEMPLATE_PATH)


@pytest.fixture
def base_card():
    return {"owner": "a", "set": "SV08", "type": "", "date": "2026-01-01T00:00:00.000+08:00",
            "expense": "10.00", "price_menu": "", "url": ""}


# REQ-000: TST-001
def test_build_payload_encodes_cents_and_offset(qr_template, base_card):
    card = {**base_card, "type": "X | 1", "price_menu": "15.00", "url": "https://x.com"}
    assert "In: 1500" in build_payload(card, offset=500, qr_template=qr_template)
    assert "Out: 2000" in build_payload(card, offset=500, qr_template=qr_template)


# REQ-000: TST-002
def test_build_payload_omits_out_when_blank(qr_template, base_card):
    card = {**base_card, "type": "X | 1", "url": "https://x.com"}
    assert "Out:" not in build_payload(card, offset=0, qr_template=qr_template)


# REQ-001: TST-003
def test_parse_template_meta_valid():
    assert parse_template_meta("templates/avery_6572_letter_15.html") == ("letter", 15)
    assert parse_template_meta("templates/avery_l7161_a4_18.html") == ("a4", 18)


# REQ-001: TST-004
def test_parse_template_meta_invalid():
    with pytest.raises(ValueError):
        parse_template_meta("bad_template.html")


# REQ-003: TST-005
def test_build_payload_omits_type_when_blank(qr_template, base_card):
    assert "Type:" not in build_payload(base_card, offset=0, qr_template=qr_template)


# REQ-003: TST-006
def test_build_payload_omits_url_when_blank(qr_template, base_card):
    payload = build_payload(base_card, offset=0, qr_template=qr_template)
    lines = payload.splitlines()
    assert all(line.startswith(("Date:", "Owner:", "Set:", "In:")) or line == "" for line in lines if line)


# REQ-001: TST-016
def test_build_payload_ref_line_precedes_owner_when_present(qr_template, base_card):
    card = {**base_card, "refid": "1251"}
    lines = build_payload(card, offset=0, qr_template=qr_template).splitlines()
    assert lines[0] == "Ref: 1251"
    assert lines[1] == "Date: 01-Jan-26"
    assert lines[2] == "Owner: a"


# REQ-001: TST-017
def test_build_payload_omits_ref_line_when_absent(qr_template, base_card):
    assert "Ref:" not in build_payload(base_card, offset=0, qr_template=qr_template)


# REQ-001: TST-018
def test_build_payload_omits_qty_price_when_single(qr_template, base_card):
    card = {**base_card, "qty": "1", "price": "10.00"}
    payload = build_payload(card, offset=0, qr_template=qr_template)
    assert "Qty:" not in payload
    assert "Price:" not in payload


# REQ-001: TST-019
def test_build_payload_shows_qty_price_when_bulk(qr_template, base_card):
    card = {**base_card, "qty": "3", "price": "1380", "expense": "4140"}
    payload = build_payload(card, offset=0, qr_template=qr_template)
    assert "Qty: 3" in payload
    assert "Price: 138000" in payload
    assert "In: 414000" in payload


# REQ-001: start-label pads blank grid cells before the real cards
def test_start_label_pads_blank_cells():
    tmpl_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'avery_l7161_a4_18.html')
    html = JinjaTemplate(open(tmpl_path).read()).render(
        cards=[{"qr": "x", "owner": "a", "set": "b", "type": "c"}], start=3
    )
    assert html.count('<div class="label"></div>') == 2


# REQ-001: TST-026
def test_type_over_threshold_gets_small_type_class():
    tmpl_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'avery_l7161_a4_18.html')
    long_type = "PSA10 | Detective Pikachu | 098/SV-P"  # 37 chars, over threshold
    short_type = "PSA10 | Mega Gengar | 240"  # 25 chars, under threshold
    html = JinjaTemplate(open(tmpl_path).read()).render(
        cards=[{"qr": "x", "owner": "a", "set": "b", "type": long_type},
               {"qr": "x", "owner": "a", "set": "b", "type": short_type}],
        start=1
    )
    assert 'small-type' in html.split(long_type)[0].splitlines()[-1]
    assert 'small-type' not in html.split(short_type)[0].splitlines()[-1]


# REQ-003: TST-025
def test_dateformat_filter_formats_iso_date():
    assert QR_ENV.filters["dateformat"]("2026-06-23T00:00:00.000+08:00") == "23-Jun-26"


# REQ-003: TST-020 (convert.py -> pipeline.py seam, real conversion output, not hand-typed fixtures)
def test_convert_output_feeds_build_payload_for_bulk_purchase(qr_template):
    mapping = {
        "doc_id": "test", "table_id": "test",
        "columns": {"Owner": "owner", "Set": "set", "Date": "date"},
        "derived": {
            "expense": "{{ (Qty|float * Price|float)|money if Qty and Price else Expense }}",
            "qty": "{{ Qty if Qty and Price else 1 }}",
            "price": "{{ Price if Qty and Price else Expense }}",
        },
    }
    lookups = {"graded_prefixes": [], "non_english_prefixes": [], "type_slugs": {}}
    fieldnames = ["Owner", "Set", "Date", "Qty", "Price", "Expense"]

    with tempfile.TemporaryDirectory() as d:
        mapping_path = os.path.join(d, "mapping.json")
        lookups_path = os.path.join(d, "lookups.json")
        input_path = os.path.join(d, "input.csv")
        output_path = os.path.join(d, "output.csv")

        with open(mapping_path, "w") as f:
            json.dump(mapping, f)
        with open(lookups_path, "w") as f:
            json.dump(lookups, f)
        with open(input_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({"Owner": "DL", "Set": "SV08", "Date": "2026-01-01T00:00:00.000+08:00",
                              "Qty": "3", "Price": "1380", "Expense": ""})

        run_conversion(mapping_path, input_path, output_path)

        with open(output_path, newline="") as f:
            card = next(csv.DictReader(f))

    payload = build_payload(card, offset=0, qr_template=qr_template)
    assert "Qty: 3" in payload
    assert "Price: 138000" in payload
    assert "In: 414000" in payload
