#!/usr/bin/env python3
"""
Talentos (pág. 72-75 do Livro de Regras): capítulo de Talentos de Treinador e
de Pokémon, extraído via detecção de fonte de título ("...Digitalt", corpo
maior) x fonte de corpo (pdf_glossary.extract_glossary), já que os nomes de
Talentos não formam uma lista fechada conhecida de antemão.

Gera um Item (feat) por Talento em packs/_source/trainer-features/, numa
pasta própria "Talentos".

Uso: python scripts/parse-talentos.py "<pasta com os PDFs>"
"""
import hashlib
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from pdf_glossary import extract_glossary  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")
FOLDER_ID = "tAlEnToSfOlDeR001"
FIRST_PAGE, LAST_PAGE = 72, 75


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", strip_accents_lower(name)).strip("-")


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


def base_item(doc_id, name, item_type, system, img, folder=None):
    return {
        "_key": f"!items!{doc_id}",
        "_id": doc_id, "name": name, "type": item_type, "img": img, "system": system,
        "effects": [], "folder": folder, "flags": {},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": 0, "ownership": {"default": 0}
    }


def write_folder():
    doc = {
        "_key": f"!folders!{FOLDER_ID}",
        "_id": FOLDER_ID, "name": "Talentos", "type": "Item", "folder": None,
        "sorting": "a", "color": "#a3be8c", "flags": {}, "_stats": {}, "sort": 0
    }
    with open(os.path.join(OUT_DIR, "folder-talentos.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def normalize_name(name):
    name = name.strip()
    if name.isupper():
        name = name.title()
    return name


def parse_talentos(pdf_path):
    entries = extract_glossary(pdf_path, FIRST_PAGE, LAST_PAGE, n_columns=2)
    written = 0
    for i, (raw_name, body) in enumerate(entries):
        if i == 0:
            continue  # entrada 0 é o cabeçalho "Talentos" do capítulo, sem corpo útil
        name = normalize_name(raw_name)
        requirements = ""
        desc = body
        m = re.search(r"Pré-requisitos?:\s*([^.]+\.)", body)
        if m:
            requirements = m.group(1).strip()
        system = {
            "description": {"value": f"<p>{desc}</p>", "chat": ""},
            "type": {"value": "feat", "subtype": ""},
            "requirements": requirements
        }
        doc = base_item(make_id(f"talento-{name}"), name, "feat", system,
                         "icons/skills/trades/mining-pick-pickaxe.webp", folder=FOLDER_ID)
        doc["flags"] = {"pokemon-mundo-perfeito": {"category": "talento"}}
        with open(os.path.join(OUT_DIR, f"talento-{slugify(name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1
    return written


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-talentos.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")
    os.makedirs(OUT_DIR, exist_ok=True)
    write_folder()
    n = parse_talentos(pdf_path)
    print(f"{n} Talentos escritos em {OUT_DIR}")


if __name__ == "__main__":
    main()
