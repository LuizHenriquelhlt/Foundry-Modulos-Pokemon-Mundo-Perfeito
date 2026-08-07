#!/usr/bin/env python3
"""
Pós-processamento: aplica imagens do repositório de sprites do PokeAPI
(https://github.com/PokeAPI/sprites, URLs raw do GitHub — estáveis e aceitas pelo
Foundry como img remota) aos JSONs de packs/_source/:

- pokedex: retrato = arte oficial da espécie (por número da Pokédex);
  token = sprite pixelado clássico. Formas alternativas compartilham o número da
  espécie base, então usam a mesma arte (o PokeAPI indexa formas por IDs internos
  10000+ sem relação com o número da Dex — mapeá-los um a um não compensa).
- pokeballs: sprite do item correspondente (poke-ball, great-ball, ...).
- tms e moves: sprite de TM colorido pelo tipo do Move (tm-fire, tm-water, ...).
- mega-evolutions: sprite da Mega Stone quando existir no PokeAPI (megas oficiais);
  as fan-made (Raichunite X, Drampanite, ...) mantêm o ícone genérico.

Requer rede só para as checagens de existência (Pokébolas/Mega Stones); roda depois
de qualquer parser e antes de `npm run build:packs`.

Uso: python scripts/add-images.py
"""
import json
import glob
import os
import re
import unicodedata
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "packs", "_source")

BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"
ARTWORK = BASE + "/pokemon/other/official-artwork/{dex}.png"
SPRITE = BASE + "/pokemon/{dex}.png"
ITEM = BASE + "/items/{slug}.png"

TM_TYPES = {"normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison",
            "ground", "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark",
            "steel", "fairy"}


def slugify(name):
    s = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def url_exists(url, cache={}):
    if url in cache:
        return cache[url]
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            cache[url] = resp.status == 200
    except Exception:
        cache[url] = False
    return cache[url]


def save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def patch_pokedex():
    n = 0
    for f in glob.glob(os.path.join(SRC, "pokedex", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        # após convert-to-dnd5e-native.py o schema PMP vive em flags, não em system
        dex = doc["system"].get("dexNumber") \
            or doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("species", {}).get("dexNumber")
        if not dex:
            continue
        doc["img"] = ARTWORK.format(dex=dex)
        token = doc.setdefault("prototypeToken", {})
        token["texture"] = {"src": SPRITE.format(dex=dex)}
        save(f, doc)
        n += 1
    print(f"pokedex: {n} espécies com arte oficial + sprite de token")


def patch_pokeballs():
    special = {"pokebola": "poke-ball"}
    n_ok = n_missing = 0
    for f in glob.glob(os.path.join(SRC, "pokeballs", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        slug = special.get(slugify(doc["name"]), slugify(doc["name"]))
        url = ITEM.format(slug=slug)
        if url_exists(url):
            doc["img"] = url
            n_ok += 1
        else:
            n_missing += 1
        save(f, doc)
    print(f"pokeballs: {n_ok} com sprite, {n_missing} sem correspondência no PokeAPI")


def move_type_of(doc):
    # após convert-to-dnd5e-native.py o schema PMP vive em flags, não em system
    return doc["system"].get("moveType") \
        or doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("move", {}).get("moveType", "normal")


def move_types_by_name():
    types = {}
    for f in glob.glob(os.path.join(SRC, "moves", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        types[doc["name"]] = move_type_of(doc)
    return types


def patch_moves_and_tms(types_by_name):
    n = 0
    for f in glob.glob(os.path.join(SRC, "moves", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        mtype = move_type_of(doc)
        if mtype in TM_TYPES:
            doc["img"] = ITEM.format(slug=f"tm-{mtype}")
            save(f, doc)
            n += 1
    print(f"moves: {n} com sprite de tipo")

    n_ok = n_fallback = 0
    for f in glob.glob(os.path.join(SRC, "tms", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        move_name = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("teachesMove", "")
        mtype = types_by_name.get(move_name)
        if mtype in TM_TYPES:
            doc["img"] = ITEM.format(slug=f"tm-{mtype}")
            n_ok += 1
        else:
            doc["img"] = ITEM.format(slug="tm-normal")
            n_fallback += 1
        save(f, doc)
    print(f"tms: {n_ok} com sprite do tipo do Move, {n_fallback} com sprite genérico (Move não encontrado)")


def patch_megas():
    n_ok = n_missing = 0
    for f in glob.glob(os.path.join(SRC, "mega-evolutions", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        slug = slugify(doc["name"])
        url = ITEM.format(slug=slug)
        if url_exists(url):
            doc["img"] = url
            n_ok += 1
        else:
            n_missing += 1
        save(f, doc)
    print(f"mega-evolutions: {n_ok} com sprite da Mega Stone, {n_missing} fan-made sem sprite (ícone genérico)")


def main():
    patch_pokedex()
    patch_pokeballs()
    patch_moves_and_tms(move_types_by_name())
    patch_megas()


if __name__ == "__main__":
    main()
