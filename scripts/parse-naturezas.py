#!/usr/bin/env python3
"""
Naturezas do Pokémon (pág. 36 do Livro de Regras): tabela de 20 Naturezas com
descrição e bônus/penalidade em atributos, usada pelo Mestre para atribuir
(rolagem de 1d20) ou pelo jogador escolher a Natureza do seu Pokémon inicial.

Gera um Item (feat) por Natureza em packs/_source/trainer-features/, numa
pasta própria "Naturezas", para ser arrastado sobre um Pokémon possuído em
mundo (o compêndio da Pokédex guarda apenas as espécies "molde").

Uso: python scripts/parse-naturezas.py "<pasta com os PDFs>"
"""
import hashlib
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")
FOLDER_ID = "nAtUrEzAsFoLdEr01"

ATTR_PATTERN = r"(?:Força|Destreza|Constituição|Inteligência|Sabedoria|Carisma|CA)"
ROW_RE = re.compile(
    r"^\d+\s+(\S+)\s+(.+?)\s+((?:[+-]\d+\s+" + ATTR_PATTERN + r",\s*)?[+-]\d+\s+" + ATTR_PATTERN + r")$"
)


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
        "_id": FOLDER_ID, "name": "Naturezas", "type": "Item", "folder": None,
        "sorting": "a", "color": "#88c0d0", "flags": {}, "_stats": {}, "sort": 0
    }
    with open(os.path.join(OUT_DIR, "folder-naturezas.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def parse_naturezas(pdf_path):
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[35].extract_text() or ""  # página 36 (0-indexado)

    rows = []
    for line in text.split("\n"):
        m = ROW_RE.match(line.strip())
        if m:
            name, desc, bonus = m.group(1), m.group(2).strip(), m.group(3).strip()
            rows.append((name, desc, bonus))

    if len(rows) != 20:
        print(f"AVISO Naturezas: esperava 20 linhas, achou {len(rows)}: {[r[0] for r in rows]}")

    written = 0
    for name, desc, bonus in rows:
        system = {
            "description": {
                "value": f"<p>{desc}</p><p><strong>Bônus e Penalidade:</strong> {bonus}</p>",
                "chat": ""
            },
            "type": {"value": "feat", "subtype": ""},
            "requirements": "Definida ao nascer/eclodir (role 1d20) ou escolhida para o inicial"
        }
        doc = base_item(make_id(f"natureza-{name}"), name, "feat", system,
                         "icons/magic/light/orb-lightbulb-gray.webp", folder=FOLDER_ID)
        doc["flags"] = {"pokemon-mundo-perfeito": {"category": "natureza", "bonus": bonus}}
        with open(os.path.join(OUT_DIR, f"natureza-{slugify(name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1
    return written


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-naturezas.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")
    os.makedirs(OUT_DIR, exist_ok=True)
    write_folder()
    n = parse_naturezas(pdf_path)
    print(f"{n} Naturezas escritas em {OUT_DIR}")


if __name__ == "__main__":
    main()
