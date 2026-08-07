#!/usr/bin/env python3
"""
Fase 1 (parte 5) — Lista de Preços de TM (Livro de Regras, página 90).
Tabela de 4 blocos repetidos [Nº, TM, Preço] lado a lado, extraída com
pdfplumber extract_tables() (grade real, não texto corrido).

Uso: python scripts/parse-tm-prices.py "<pasta com os PDFs>"
"""
import json
import os
import re
import sys
import unicodedata

import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "tms")
PAGE = 90


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def base_item(doc_id, name, item_type, system, img="icons/svg/item-bag.svg"):
    return {
        "_key": f"!items!{doc_id}",
        "_id": doc_id, "name": name, "type": item_type, "img": img, "system": system,
        "effects": [], "folder": None, "flags": {},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": 0, "ownership": {"default": 0}
    }


def make_id(seed, used_ids):
    import hashlib
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    doc_id = "".join(out)
    while doc_id in used_ids:
        doc_id = doc_id[1:] + doc_id[0]
    used_ids.add(doc_id)
    return doc_id


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", strip_accents_lower(name)).strip("-")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-tm-prices.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")

    with pdfplumber.open(pdf_path) as pdf:
        tables = pdf.pages[PAGE - 1].extract_tables()

    entries = []
    for table in tables:
        for row in table:
            cells = [c.strip() if isinstance(c, str) else c for c in row]
            non_empty = [c for c in cells if c]
            # cada linha tem até 4 grupos [Nº, TM, Preço]
            i = 0
            while i < len(non_empty):
                num, move, price = non_empty[i:i + 3]
                i += 3
                if not re.fullmatch(r"\d+", num):
                    continue
                if "₽" not in price:
                    continue
                entries.append((int(num), move, price))

    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.startswith("tm-") and f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))

    used_ids = set()
    written = 0
    seen_numbers = set()
    for num, move, price in entries:
        if num in seen_numbers:
            continue
        seen_numbers.add(num)
        system = {
            "description": {"value": f"<p>TM que ensina o Move <strong>{move}</strong> a um Pokémon compatível.</p>"},
            "price": {"value": price, "denomination": "P"}
        }
        doc = base_item(make_id(f"tm-{num}", used_ids), f"TM{num:03d}: {move}", "consumable", system)
        doc["flags"] = {"pokemon-mundo-perfeito": {"tmNumber": num, "teachesMove": move, "priceRaw": price}}
        with open(os.path.join(OUT_DIR, f"tm-{num:03d}-{slugify(move)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1

    print(f"{written} TMs escritas em {OUT_DIR} (de {len(entries)} entradas na tabela)")
    missing = sorted(set(range(1, max(seen_numbers) + 1)) - seen_numbers) if seen_numbers else []
    if missing:
        print(f"Números de TM ausentes na sequência 1..{max(seen_numbers)}: {missing}")


if __name__ == "__main__":
    main()
