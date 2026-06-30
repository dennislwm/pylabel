import argparse
import csv
import json
import os
import sys

DEFAULT_OWNER = "dennislwm"
OUTPUT_FIELDS = ["owner", "set", "date", "type", "platform", "vendor", "expense", "price_menu", "url"]


def set_to_slug(s):
    return s.lower().replace(".", "pt").replace(" ", "-")


def convert(mapping_path, input_path, output_path, tail=None):
    with open(mapping_path) as f:
        mapping = json.load(f)

    lookups_path = os.path.join(os.path.dirname(mapping_path), "lookups.json")
    with open(lookups_path) as f:
        lookups = json.load(f)

    owner_codes = lookups["owner_codes"]
    type_slugs = lookups["type_slugs"]
    graded_prefixes = tuple(lookups["graded_prefixes"])
    non_english_prefixes = tuple(lookups["non_english_prefixes"])
    col_map = mapping["columns"]
    derived = mapping["derived"]

    rows_out = []
    with open(input_path, newline="", encoding="utf-8") as f:
        rows_in = list(csv.DictReader(f))

    rows_in.sort(key=lambda r: r.get("Date", ""), reverse=True)
    if tail is not None:
        rows_in = rows_in[:tail]

    for row in rows_in:
            out = {dst: row.get(src, "") for src, dst in col_map.items()}

            # owner: first token of Player against owner_codes; default dennislwm
            player = row.get(derived["owner"], "")
            prefix = player.split()[0] if player else ""
            out["owner"] = owner_codes.get(prefix, DEFAULT_OWNER)

            # type + url: sealed / single (Raw) / graded (PSA*)
            type_val = row.get(derived["type"], "")
            set_val = out.get("set", "")

            if type_val == "Raw" or type_val.upper().startswith(graded_prefixes):
                out["type"] = ""
                out["url"] = ""
            else:
                out["type"] = type_val
                type_slug = type_slugs.get(type_val)
                if not type_slug:
                    print(f"[WARN] unknown type {type_val!r} -- url left blank", file=sys.stderr)
                    out["url"] = ""
                elif any(set_val.startswith(p) for p in non_english_prefixes):
                    print(f"[WARN] non-English set {set_val!r} -- url left blank", file=sys.stderr)
                    out["url"] = ""
                else:
                    out["url"] = (
                        f"https://www.pricecharting.com/game/"
                        f"pokemon-{set_to_slug(set_val)}/{type_slug}"
                    )

            rows_out.append(out)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"[OK] {len(rows_out)} rows written to {output_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mapping", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--tail", type=int, default=None)
    args = p.parse_args()
    convert(args.mapping, args.input, args.output, tail=args.tail)


if __name__ == "__main__":
    main()
