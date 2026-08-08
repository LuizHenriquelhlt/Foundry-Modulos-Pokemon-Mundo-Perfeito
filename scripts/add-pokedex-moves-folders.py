#!/usr/bin/env python3
"""
Organiza os compêndios Pokédex (pastas por GERAÇÃO, com o nome da região) e Moves
(pastas por TIPO, com a cor clássica de cada tipo) — mesmo mecanismo de Folders do
add-trainer-folders.py. Idempotente; roda depois dos parsers/conversor.

Uso: python scripts/add-pokedex-moves-folders.py
"""
import glob
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")
MOVES = os.path.join(ROOT, "packs", "_source", "moves")


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


# (última dex da geração, rótulo)
GENERATIONS = [
    (151, "Geração 1 — Kanto"),
    (251, "Geração 2 — Johto"),
    (386, "Geração 3 — Hoenn"),
    (493, "Geração 4 — Sinnoh"),
    (649, "Geração 5 — Unova"),
    (721, "Geração 6 — Kalos"),
    (809, "Geração 7 — Alola"),
    (905, "Geração 8 — Galar/Hisui"),
    (1025, "Geração 9 — Paldea"),
]

# cores clássicas dos tipos
TYPE_FOLDERS = [
    ("normal", "Normal", "#A8A878"), ("fire", "Fogo", "#F08030"),
    ("water", "Água", "#6890F0"), ("electric", "Elétrico", "#F8D030"),
    ("grass", "Grama", "#78C850"), ("ice", "Gelo", "#98D8D8"),
    ("fighting", "Lutador", "#C03028"), ("poison", "Venenoso", "#A040A0"),
    ("ground", "Terrestre", "#E0C068"), ("flying", "Voador", "#A890F0"),
    ("psychic", "Psíquico", "#F85888"), ("bug", "Inseto", "#A8B820"),
    ("rock", "Pedra", "#B8A038"), ("ghost", "Fantasma", "#705898"),
    ("dragon", "Dragão", "#7038F8"), ("dark", "Sombrio", "#705848"),
    ("steel", "Aço", "#B8B8A0"), ("fairy", "Fada", "#EE99AC"),
    ("variable", "Tipo Variável", "#68A090"),
]


def folder_doc(folder_id, name, doc_type, color, sort):
    return {
        "_key": f"!folders!{folder_id}",
        "_id": folder_id,
        "name": name,
        "type": doc_type,
        "folder": None,
        "sorting": "a",
        "color": color,
        "description": "",
        "flags": {},
        "sort": sort,
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                    "compendiumSource": None, "duplicateSource": None}
    }


def save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def gen_of(dex):
    for last, label in GENERATIONS:
        if dex <= last:
            return label
    return GENERATIONS[-1][1]


def organize_pokedex():
    gen_ids = {}
    for i, (_, label) in enumerate(GENERATIONS):
        fid = make_id(f"folder-pokedex-{label}")
        gen_ids[label] = fid
        save(os.path.join(POKEDEX, f"folder-gen{i + 1}.json"),
             folder_doc(fid, label, "Actor", None, i * 10000))

    counts = {}
    for f in glob.glob(os.path.join(POKEDEX, "*.json")):
        if os.path.basename(f).startswith("folder-"):
            continue
        doc = json.load(open(f, encoding="utf-8"))
        dex = doc["system"].get("dexNumber") \
            or doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("species", {}).get("dexNumber", 0)
        label = gen_of(dex)
        doc["folder"] = gen_ids[label]
        counts[label] = counts.get(label, 0) + 1
        save(f, doc)
    print("Pokédex por geração:")
    for _, label in GENERATIONS:
        print(f"  {label}: {counts.get(label, 0)}")


def organize_moves():
    type_ids = {}
    for i, (key, label, color) in enumerate(TYPE_FOLDERS):
        fid = make_id(f"folder-moves-{key}")
        type_ids[key] = fid
        save(os.path.join(MOVES, f"folder-{key}.json"),
             folder_doc(fid, label, "Item", color, i * 10000))

    counts = {}
    for f in glob.glob(os.path.join(MOVES, "*.json")):
        if os.path.basename(f).startswith("folder-"):
            continue
        doc = json.load(open(f, encoding="utf-8"))
        mtype = doc["system"].get("moveType") \
            or doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("move", {}).get("moveType", "normal")
        if mtype not in type_ids:
            mtype = "variable"
        doc["folder"] = type_ids[mtype]
        counts[mtype] = counts.get(mtype, 0) + 1
        save(f, doc)
    print("Moves por tipo:")
    for key, label, _ in TYPE_FOLDERS:
        if counts.get(key):
            print(f"  {label}: {counts[key]}")


def main():
    organize_pokedex()
    organize_moves()


if __name__ == "__main__":
    main()
