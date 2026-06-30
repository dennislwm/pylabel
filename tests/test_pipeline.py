import os
import sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from pipeline import build_payload, parse_template_meta


# REQ-000: TST-001
def test_build_payload_encodes_cents_and_offset():
    card = {"owner": "a", "set": "SV08", "type": "X | 1",
            "expense": "10.00", "price_menu": "15.00", "url": "https://x.com"}
    assert "In: 1500" in build_payload(card, offset=500)
    assert "Out: 2000" in build_payload(card, offset=500)


# REQ-000: TST-002
def test_build_payload_omits_out_when_blank():
    card = {"owner": "a", "set": "SV08", "type": "X | 1",
            "expense": "10.00", "price_menu": "", "url": "https://x.com"}
    assert "Out:" not in build_payload(card, offset=0)


# REQ-001: TST-003
def test_parse_template_meta_valid():
    assert parse_template_meta("templates/avery_6572_letter_15.html") == ("letter", 15)
    assert parse_template_meta("templates/avery_l7161_a4_18.html") == ("a4", 18)


# REQ-001: TST-004
def test_parse_template_meta_invalid():
    with pytest.raises(ValueError):
        parse_template_meta("bad_template.html")


# REQ-003: TST-005
def test_build_payload_omits_type_when_blank():
    card = {"owner": "a", "set": "SV08", "type": "",
            "expense": "10.00", "price_menu": "", "url": ""}
    assert "Type:" not in build_payload(card, offset=0)


# REQ-003: TST-006
def test_build_payload_omits_url_when_blank():
    card = {"owner": "a", "set": "SV08", "type": "",
            "expense": "10.00", "price_menu": "", "url": ""}
    payload = build_payload(card, offset=0)
    lines = payload.splitlines()
    assert all(line.startswith(("Owner:", "Set:", "In:")) or line == "" for line in lines if line)
