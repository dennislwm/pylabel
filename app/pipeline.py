import argparse
import base64
import csv
import io
import os
import subprocess
import sys

import segno
from jinja2 import Template
from weasyprint import HTML


def parse_args():
    p = argparse.ArgumentParser(description="Generate Avery 6572 QR label sheet PDF")
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="output")
    p.add_argument("--printer")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--force", action="store_true")
    return p.parse_args()


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_payload(card, offset):
    in_val = round(float(card["expense"]) * 100) + offset
    lines = [
        f"Owner: {card['owner']}",
        f"Set: {card['set']}",
        f"Type: {card['type']}",
        f"In: {in_val}",
    ]
    if card["price_menu"].strip():
        out_val = round(float(card["price_menu"]) * 100) + offset
        lines.append(f"Out: {out_val}")
    lines.append(card["url"])
    return "\n".join(lines)


def card_to_qr_b64(card, offset):
    payload = build_payload(card, offset)
    qr = segno.make(payload, error="M")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=10)
    return base64.b64encode(buf.getvalue()).decode()


TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<style>
@page { size: 8.5in 11in; margin: 0.5in 0.21875in; }
body { margin: 0; padding: 0; }
.sheet {
  display: grid;
  grid-template-columns: repeat(3, 2.625in);
  grid-template-rows: repeat(5, 2in);
  column-gap: 0.09375in;
  row-gap: 0;
}
.label {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2mm;
  box-sizing: border-box;
  overflow: hidden;
}
.label img { width: 1.5in; height: 1.5in; }
.info {
  font-size: 7pt;
  text-align: center;
  margin-top: 1mm;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}
</style>
</head>
<body>
<div class="sheet">
  {% for card in cards %}
  <div class="label">
    <img src="data:image/png;base64,{{ card.qr }}">
    <div class="info">{{ card.owner }} · {{ card.set }}<br>{{ card.type }}</div>
  </div>
  {% endfor %}
</div>
</body>
</html>"""


def render_template(cards):
    return Template(TEMPLATE).render(cards=cards)


def render_pdf(html, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    HTML(string=html).write_pdf(out_path)


def main():
    args = parse_args()
    cards = load_csv(args.csv)
    if len(cards) < 15 and not args.force:
        sys.exit(f"[ERROR] Only {len(cards)} rows found; need 15 for a full sheet. Use --force to print anyway.")
    print(f"[OK] Loaded {len(cards)} rows from {args.csv}")
    for card in cards:
        card["qr"] = card_to_qr_b64(card, args.offset)
    print(f"[OK] QR generated for {len(cards)} cards")
    html = render_template(cards)
    print(f"[OK] Template rendered ({len(html)} chars)")
    out_name = os.path.splitext(os.path.basename(args.csv))[0] + ".pdf"
    out_path = os.path.join(args.out, out_name)
    render_pdf(html, out_path)
    print(f"[OK] {out_path} written")
    if args.printer:
        result = subprocess.run(["lp", "-d", args.printer, out_path])
        if result.returncode != 0:
            sys.exit(f"[ERROR] lp failed (exit {result.returncode})")
        print(f"[OK] Sent to printer {args.printer}")
    else:
        print("[INFO] No printer set -- PDF written, skipping print")


if __name__ == "__main__":
    main()
