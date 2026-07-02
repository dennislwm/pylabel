import argparse
import csv
import json
import os
import sys

from jinja2 import Environment


def set_to_slug(s):
    return s.lower().replace(".", "pt").replace(" ", "-")


def split_card_number(s):
    parts = s.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0], parts[1]
    return s, ""


def build_environment(lookups):
    env = Environment()
    env.globals.update(
        graded_prefixes=tuple(lookups["graded_prefixes"]),
        non_english_prefixes=tuple(lookups["non_english_prefixes"]),
    )
    env.filters["type_slug"] = lambda t: lookups["type_slugs"].get(t)
    env.filters["slugify"] = set_to_slug
    env.filters["split_card_number"] = split_card_number
    env.filters["money"] = lambda v: f"{round(float(v), 2):g}"
    return env


def convert(mapping_path, input_path, output_path, tail=None):
    with open(mapping_path) as f:
        mapping = json.load(f)

    lookups_path = os.path.join(os.path.dirname(mapping_path), "lookups.json")
    with open(lookups_path) as f:
        lookups = json.load(f)

    col_map = mapping["columns"]
    derived = mapping.get("derived", {})
    env = build_environment(lookups)
    templates = {field: env.from_string(expr) for field, expr in derived.items()}
    output_fields = list(col_map.values()) + list(derived.keys())
    row_filter = env.compile_expression(mapping.get("filter", "true"))

    with open(input_path, newline="", encoding="utf-8") as f:
        rows_in = list(csv.DictReader(f))

    rows_in = [r for r in rows_in if row_filter(**r)]
    rows_in.sort(key=lambda r: r.get("Date", ""), reverse=True)
    if tail is not None:
        rows_in = rows_in[:tail]

    rows_out = []
    for row in rows_in:
        out = {dst: row.get(src, "") for src, dst in col_map.items()}
        for field, template in templates.items():
            try:
                out[field] = template.render(**row)
            except Exception as e:
                print(f"[WARN] derive {field!r} failed for row {row!r}: {e}", file=sys.stderr)
                out[field] = ""
        rows_out.append(out)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
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
