#!/usr/bin/env python3
"""
Organiza o compêndio "Recursos de Treinador" em PASTAS (Folders do Foundry), usando o
flag de categoria que cada documento já carrega. Os itens do catálogo ganham subpastas
por heurística de nome (Berries, Hortelãs, Doces, Poções); o resto fica em "Itens".

Cria os documentos de Folder como JSONs próprios (com _key "!folders!<id>", formato que
o compilePack espera) e preenche o campo "folder" de cada item.

Roda a qualquer momento depois dos parsers (idempotente).
Uso: python scripts/add-trainer-folders.py
"""
import glob
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


# (slug, nome exibido, cor, pasta-pai ou None)
FOLDERS = [
    ("classes", "Classes de Treinador", "#8a2be2", None),
    ("especializacoes", "Especializações", "#2e8b57", None),
    ("habilidades-gerais", "Habilidades Gerais de Treinador", "#4682b4", None),
    ("regioes", "Regiões de Origem", "#b8860b", None),
    ("origens", "Origens de Jornada", "#cd5c5c", None),
    ("progressao", "Progressão de Níveis do Pokémon", "#20b2aa", None),
    ("mecanicas", "Mecânicas Especiais (Dynamax/Terastal)", "#dc143c", None),
    ("itens", "Itens", "#708090", None),
    ("berries", "Berries", "#c71585", "itens"),
    ("hortelas", "Hortelãs (Natureza)", "#6b8e23", "itens"),
    ("doces", "Doces (Candy)", "#ff8c00", "itens"),
    ("pocoes", "Poções", "#9370db", "itens"),
]

CATEGORY_TO_FOLDER = {
    "classe-de-treinador": "classes",
    "especializacao": "especializacoes",
    "habilidade-geral-treinador": "habilidades-gerais",
    "regiao-de-origem": "regioes",
    "origem-de-jornada": "origens",
    "progressao-de-nivel": "progressao",
    "mecanica-dynamax": "mecanicas",
    "mecanica-terastal": "mecanicas",
}


def item_subfolder(name):
    if name.endswith(" Berry") or name == "Berry Juice":
        return "berries"
    if name.startswith("Hortelã"):
        return "hortelas"
    if "Candy" in name:
        return "doces"
    if name.startswith("Poção"):
        return "pocoes"
    return "itens"


def main():
    folder_ids = {slug: make_id(f"folder-trainer-{slug}") for slug, _, _, _ in FOLDERS}

    for i, (slug, label, color, parent) in enumerate(FOLDERS):
        doc = {
            "_key": f"!folders!{folder_ids[slug]}",
            "_id": folder_ids[slug],
            "name": label,
            "type": "Item",
            "folder": folder_ids[parent] if parent else None,
            "sorting": "a",
            "color": color,
            "description": "",
            "flags": {},
            "sort": i * 10000,
            "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                        "compendiumSource": None, "duplicateSource": None}
        }
        with open(os.path.join(DIR, f"folder-{slug}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    counts = {}
    for f in glob.glob(os.path.join(DIR, "*.json")):
        if os.path.basename(f).startswith("folder-"):
            continue
        doc = json.load(open(f, encoding="utf-8"))
        category = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("category", "")
        slug = CATEGORY_TO_FOLDER.get(category)
        if not slug and category == "item-treinador":
            slug = item_subfolder(doc["name"])
        if not slug:
            slug = "itens"
        doc["folder"] = folder_ids[slug]
        counts[slug] = counts.get(slug, 0) + 1
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    print(f"{len(FOLDERS)} pastas criadas; documentos distribuídos:")
    for slug, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {slug}: {n}")


if __name__ == "__main__":
    main()
