#!/usr/bin/env python3
"""
Cria no compêndio "abilities" as Habilidades Passivas que só existem no livro de Mega
Evoluções (capítulo "Habilidades Passivas") — Piercing Drill, Mega Sol, Dragonize, Spicy
Spray, Desolate Land, Primordial Sea... A Mega Pedra prometia a Habilidade, mas ao Mega
Evoluir o módulo não achava a ficha dela e mostrava só "Veja a Lista de Habilidades
Passivas no Livro de Regras".

Lê o capítulo com o mesmo leitor de scripts/sync-gen89-abilities.py. Só CRIA as que faltam:
uma Habilidade que já existe no compêndio (vinda do Livro de Regras ou dos suplementos)
não é tocada. Idempotente.
Uso: python scripts/add-mega-abilities.py "<pasta com os PDFs>"
"""
import glob
import hashlib
import importlib.util
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ABILITIES = os.path.join(ROOT, "packs", "_source", "abilities")
BOOK = "Mega Evoluções - Pokémon Mundo Perfeito.pdf"
IMG = "icons/magic/control/buff-flight-wings-blue.webp"  # mesmo ícone das demais Habilidades

spec = importlib.util.spec_from_file_location("sync_abilities", os.path.join(HERE, "sync-gen89-abilities.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


def slugify(name):
    text = "".join(c for c in unicodedata.normalize("NFKD", name.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/add-mega-abilities.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pages, entries = sync.parse_chapter(os.path.join(sys.argv[1], BOOK))
    print(f"{BOOK}: {len(entries)} Habilidades nas páginas {pages[0]}-{pages[1]}")

    existing = {json.load(open(f, encoding="utf-8"))["name"].lower()
                for f in glob.glob(os.path.join(ABILITIES, "*.json"))}
    created = []
    for name, html in entries.items():
        if name.lower() in existing or not html:
            continue
        doc_id = make_id(f"habilidade-{name}")
        doc = {
            "_key": f"!items!{doc_id}", "_id": doc_id, "name": name, "type": "feat", "img": IMG,
            "system": {"description": {"value": html, "chat": ""},
                       "type": {"value": "feat", "subtype": ""}, "requirements": ""},
            "effects": [], "folder": None,
            "flags": {"pokemon-mundo-perfeito": {"category": "habilidade-passiva", "source": "Mega"}},
            "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                       "compendiumSource": None, "duplicateSource": None},
            "sort": 0, "ownership": {"default": 0}
        }
        sync.save(os.path.join(ABILITIES, f"habilidade-{slugify(name)}.json"), doc)
        created.append(name)
    print(f"{len(created)} Habilidades criadas: {created}")


if __name__ == "__main__":
    main()
