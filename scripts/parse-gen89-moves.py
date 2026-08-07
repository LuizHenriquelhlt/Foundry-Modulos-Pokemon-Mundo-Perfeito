#!/usr/bin/env python3
"""
Fase 5 — "Moves da Oitava Geração" (Livro da Geração 8, pág. 16-28) e "Moves da Nona
Geração" (Livro da Geração 9, pág. 23-34). Mesmo template e mesmo parser da Fase 2
(scripts/parse-moves.py), reaproveitado aqui via import. Só grava Moves cujo nome
ainda não existe no compêndio principal (algumas Moves de Gen 8/9, como Trailblaze,
já apareciam na Lista de Moves principal e nas listas de TM/Egg Moves da Pokédex).

Uso: python scripts/parse-gen89-moves.py "<pasta com os PDFs>"
"""
import glob
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "packs", "_source", "moves")

spec = importlib.util.spec_from_file_location("parse_moves", os.path.join(HERE, "parse-moves.py"))
parse_moves = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parse_moves)

sys.path.insert(0, os.path.join(HERE, "lib"))
from pdf_text import extract_range, strip_noise  # noqa: E402

BOOKS = [
    ("Geração 8 - Pokémon Mundo Perfeito.pdf", 16, 28, "Gen8"),
    ("Geração 9 - Pokémon Mundo Perfeito.pdf", 23, 34, "Gen9")
]


def existing_move_names():
    names = set()
    for f in glob.glob(os.path.join(OUT_DIR, "*.json")):
        names.add(json.load(open(f, encoding="utf-8"))["name"])
    return names


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-gen89-moves.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]

    known_names = existing_move_names()
    print(f"{len(known_names)} Moves já existentes no compêndio principal.")

    used_ids = set()
    total_new = 0
    total_dupe = 0
    all_warnings = []

    for filename, first, last, tag in BOOKS:
        pdf_path = os.path.join(pdf_dir, filename)
        print(f"\nExtraindo {filename} páginas {first}-{last}...")
        raw = extract_range(pdf_path, first, last, n_columns=2)
        lines = [l for l in strip_noise(raw).split("\n") if l.strip()]

        headers = parse_moves.find_move_headers(lines)
        print(f"{len(headers)} blocos de Move identificados em {tag}.")

        names_seen = {}
        for i, header in enumerate(headers):
            block_end = headers[i + 1]["start"] if i + 1 < len(headers) else len(lines)
            name, system, warnings = parse_moves.parse_block(lines, header, block_end)
            all_warnings.extend(f"[{tag}] {w}" for w in warnings)

            if name in known_names:
                total_dupe += 1
                continue
            if name in names_seen:
                continue
            names_seen[name] = True
            known_names.add(name)

            doc_id = parse_moves.make_id(name + tag, used_ids)
            doc = {
                "_id": doc_id, "name": name, "type": "pokemon-mundo-perfeito.move",
                "img": "icons/svg/item-bag.svg", "system": system,
                "effects": [], "folder": None, "flags": {"pokemon-mundo-perfeito": {"source": tag}},
                "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                           "compendiumSource": None, "duplicateSource": None},
                "sort": 10000 + i * 10, "ownership": {"default": 0}
            }
            filename_out = f"{parse_moves.slugify(name)}.json"
            with open(os.path.join(OUT_DIR, filename_out), "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            total_new += 1

    print(f"\n{total_new} Moves novos escritos em {OUT_DIR}")
    print(f"{total_dupe} Moves já existiam no compêndio principal (não duplicados)")
    print(f"{len(all_warnings)} avisos:")
    for w in all_warnings[:40]:
        print(f"  - {w}")


if __name__ == "__main__":
    main()
