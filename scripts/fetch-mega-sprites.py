#!/usr/bin/env python3
"""
Busca a arte oficial de cada forma Mega Evoluída na PokeAPI (pokeapi.co) e grava a URL em
flags.pokemon-mundo-perfeito.mega.tokenImage de cada item do compêndio "mega-evolutions" —
usada por module/combat/mega-evolution.mjs pra trocar a arte do Actor/Token ao Mega Evoluir
(e devolver ao original ao reverter).

Nem toda Mega Evolução deste projeto é oficial dos jogos (várias foram criadas pela
comunidade, ex.: Mega Falinks, Mega Scovillain, os "Z" extras de Absol/Garchomp/Lucario) —
pra essas, a PokeAPI não tem nada cadastrado (404), e o campo fica de fora: a Mega Evolução
continua funcionando normalmente, só sem trocar a arte do token.

Idempotente: pode rodar de novo (sobrescreve tokenImage com o resultado mais recente).

Uso:
  python scripts/fetch-mega-sprites.py              # aplica
  python scripts/fetch-mega-sprites.py --dry-run    # só relata o que encontraria
"""
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "packs", "_source", "mega-evolutions")


def slugify(text):
    text = text.strip().lower()
    text = text.replace("'", "").replace(".", "")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def derive_pokeapi_slug(species, mega_form):
    """'Mega Charizard X' -> 'charizard-mega-x'; 'Groudon Primal' -> 'groudon-primal'."""
    form = re.sub(r"\s*\([^)]*\)\s*$", "", mega_form).strip()  # remove "(Curly Form)" etc.
    if form.endswith(" Primal"):
        return f"{slugify(species)}-primal"
    if not form.lower().startswith("mega "):
        return None
    rest = form[5:].strip()
    m = re.match(r"^(.*)\s+([XYZ])$", rest)
    if m:
        base, suffix = m.group(1), m.group(2).lower()
        return f"{slugify(base)}-mega-{suffix}"
    return f"{slugify(rest)}-mega"


def fetch_sprite(slug):
    url = f"https://pokeapi.co/api/v2/pokemon/{slug}"
    # Sem um User-Agent explícito, a PokeAPI devolve 403 (bloqueio genérico de bot no
    # urllib padrão do Python) mesmo pra rotas que existem de verdade.
    req = urllib.request.Request(url, headers={"User-Agent": "pokemon-mundo-perfeito-foundry-module/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    sprites = data.get("sprites", {}) or {}
    other = sprites.get("other", {}) or {}
    return ((other.get("official-artwork", {}) or {}).get("front_default")
            or (other.get("home", {}) or {}).get("front_default")
            or sprites.get("front_default"))


def main():
    dry_run = "--dry-run" in sys.argv
    found, missing = [], []
    for path in sorted(glob.glob(os.path.join(SRC_DIR, "*.json"))):
        base = os.path.basename(path)
        if base.startswith("folder-"):
            continue
        doc = json.load(open(path, encoding="utf-8"))
        mega = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("mega")
        if not mega:
            continue
        slug = derive_pokeapi_slug(mega["species"], mega["megaForm"])
        if not slug:
            missing.append((doc["name"], mega["megaForm"], "sem slug derivado"))
            continue
        sprite = fetch_sprite(slug)
        time.sleep(0.15)
        if sprite:
            found.append((doc["name"], slug, sprite))
            if not dry_run:
                mega["tokenImage"] = sprite
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh, ensure_ascii=False, indent=2)
                    fh.write("\n")
        else:
            missing.append((doc["name"], slug, "404 na PokeAPI"))

    print(f"Encontradas: {len(found)}")
    print(f"Sem arte oficial (mantidas sem tokenImage): {len(missing)}")
    for name, slug, reason in missing:
        print(f"  {name} ({slug}): {reason}")
    if dry_run:
        print("(--dry-run: nenhum arquivo foi alterado)")


if __name__ == "__main__":
    main()
