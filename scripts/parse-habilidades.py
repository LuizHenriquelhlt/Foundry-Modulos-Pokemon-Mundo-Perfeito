#!/usr/bin/env python3
"""
Lista de Habilidades Passivas (pág. 213-230 do Livro de Regras): glossário com
o texto de regras de cada Habilidade Passiva/Oculta de Pokémon, extraído via
detecção de fonte de título x corpo (pdf_glossary.extract_glossary).

Gera o compêndio "abilities" (packs/_source/abilities/), um Item (feat) por
Habilidade, para servir de referência navegável e ser arrastável (ex.: sobre
o Ability Capsule/Patch ou diretamente na ficha de um Pokémon possuído).

Uso: python scripts/parse-habilidades.py "<pasta com os PDFs>"
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
OUT_DIR = os.path.join(ROOT, "packs", "_source", "abilities")
FIRST_PAGE, LAST_PAGE = 213, 230


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


def base_item(doc_id, name, item_type, system, img):
    return {
        "_key": f"!items!{doc_id}",
        "_id": doc_id, "name": name, "type": item_type, "img": img, "system": system,
        "effects": [], "folder": None, "flags": {},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": 0, "ownership": {"default": 0}
    }


def clean_body(body):
    # remove número de página solto que o pdfplumber intercala no fim do fluxo
    # de texto de página única (ex.: "...habilidade. 213")
    return re.sub(r"\s+\d{1,4}$", "", body).strip()


def parse_habilidades(pdf_path):
    entries = extract_glossary(pdf_path, FIRST_PAGE, LAST_PAGE, n_columns=1)
    written = 0
    for i, (name, body) in enumerate(entries):
        if i == 0:
            continue  # "Lista de Habilidades Passivas" (título do capítulo)
        name = name.strip()
        desc = clean_body(body)
        if not desc:
            continue
        system = {
            "description": {"value": f"<p>{desc}</p>", "chat": ""},
            "type": {"value": "feat", "subtype": ""},
            "requirements": ""
        }
        doc = base_item(make_id(f"habilidade-{name}"), name, "feat", system,
                         "icons/magic/control/buff-flight-wings-blue.webp")
        doc["flags"] = {"pokemon-mundo-perfeito": {"category": "habilidade-passiva"}}
        with open(os.path.join(OUT_DIR, f"habilidade-{slugify(name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1
    return written


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-habilidades.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")
    os.makedirs(OUT_DIR, exist_ok=True)
    n = parse_habilidades(pdf_path)
    print(f"{n} Habilidades Passivas escritas em {OUT_DIR}")


if __name__ == "__main__":
    main()
