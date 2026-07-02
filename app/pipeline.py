import argparse
import base64
import csv
import io
import os
import re
import subprocess
import sys

import segno
from jinja2 import Environment, Template
from weasyprint import HTML

QR_ENV = Environment(trim_blocks=True, lstrip_blocks=True)


def parse_args():
    p = argparse.ArgumentParser(description="Generate QR label sheet PDF")
    p.add_argument("--csv", required=True)
    p.add_argument("--template", default="templates/avery_6572_letter_15.html")
    p.add_argument("--qr-template", default="templates/qr_payload.txt")
    p.add_argument("--out", default="output")
    p.add_argument("--printer")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--force", action="store_true")
    return p.parse_args()


def load_qr_template(path):
    with open(path) as f:
        return QR_ENV.from_string(f.read())


def build_payload(card, offset, qr_template):
    ctx = dict(card)
    ctx.setdefault("qty", "1")
    ctx["in_cents"] = round(float(card["expense"]) * 100) + offset
    if card.get("price_menu", "").strip():
        ctx["out_cents"] = round(float(card["price_menu"]) * 100) + offset
    if int(card.get("qty") or 1) > 1 and card.get("price", "").strip():
        ctx["price_cents"] = round(float(card["price"]) * 100) + offset
    return qr_template.render(**ctx).strip("\n")


def card_to_qr_b64(card, offset, qr_template):
    payload = build_payload(card, offset, qr_template)
    qr = segno.make(payload, error="M")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=10)
    return base64.b64encode(buf.getvalue()).decode()


def parse_template_meta(path):
    m = re.search(r'_([a-z0-9]+)_(\d+)\.html$', path)
    if not m:
        raise ValueError("Template filename must end with _<media>_<count>.html")
    return m.group(1), int(m.group(2))


def main():
    args = parse_args()
    try:
        media, batch_min = parse_template_meta(args.template)
    except ValueError as e:
        sys.exit(f"[ERROR] {e}")
    with open(args.csv, newline="", encoding="utf-8") as f:
        cards = list(csv.DictReader(f))
    if len(cards) < batch_min and not args.force:
        sys.exit(f"[ERROR] Only {len(cards)} rows found; need {batch_min} for a full sheet. Use --force to print anyway.")
    print(f"[OK] Loaded {len(cards)} rows from {args.csv}")
    qr_template = load_qr_template(args.qr_template)
    for card in cards:
        card["qr"] = card_to_qr_b64(card, args.offset, qr_template)
    print(f"[OK] QR generated for {len(cards)} cards")
    html = Template(open(args.template).read()).render(cards=cards)
    print(f"[OK] Template rendered ({len(html)} chars)")
    out_name = (os.path.splitext(os.path.basename(args.csv))[0] + "_" +
                os.path.splitext(os.path.basename(args.template))[0] + ".pdf")
    out_path = os.path.join(args.out, out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    HTML(string=html).write_pdf(out_path)
    print(f"[OK] {out_path} written")
    if args.printer:
        result = subprocess.run(["lp", "-d", args.printer, "-o", f"media={media}", out_path])
        if result.returncode != 0:
            sys.exit(f"[ERROR] lp failed (exit {result.returncode})")
        print(f"[OK] Sent to printer {args.printer} (media={media})")
    else:
        print("[INFO] No printer set -- PDF written, skipping print")


if __name__ == "__main__":
    main()
