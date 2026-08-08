#!/usr/bin/env python3
"""
Imagens específicas das FORMAS alternativas (regionais, Therian, máscaras de Ogerpon...).
add-images.py usa o número da Pokédex, então todas as formas de uma espécie ficavam com a
arte da forma base. Este script traduz o nome PT da forma para o slug de variedade do
PokeAPI (ex.: "Raichu de Alola" -> raichu-alola), consulta a API REST uma vez por forma
para descobrir o ID interno (10000+) e aplica a arte oficial + sprite de token da forma.

Também corrige o nome corrompido "fazê-lo retornar à forma Hoopa Liberto" -> "Hoopa
Liberto" (artefato de extração do Livro dos Pokémon).

Roda DEPOIS de add-images.py e ANTES de convert-to-dnd5e-native.py (mas é idempotente e
funciona sobre docs já convertidos, lendo o nome do próprio actor).

Uso: python scripts/add-form-images.py
"""
import json
import glob
import os
import re
import unicodedata
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")

ARTWORK = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{id}.png"
SPRITE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/{id}.png"

NAME_FIXES = {
    "fazê-lo retornar à forma Hoopa Liberto": "Hoopa Liberto"
}

# Formas com slug irregular no PokeAPI, chaveadas pelo nome PT completo do actor.
EXPLICIT_SLUGS = {
    "Tauros Raça de Combate": "tauros-paldea-combat-breed",
    "Tauros Raça Incandescente": "tauros-paldea-blaze-breed",
    "Tauros Raça Aquática": "tauros-paldea-aqua-breed",
    "Castform Forma Sol": "castform-sunny",
    "Castform Forma Chuva": "castform-rainy",
    "Castform Forma Neve": "castform-snowy",
    "Wormadam Manto de Planta": "wormadam-plant",
    "Wormadam Manto de Areia": "wormadam-sandy",
    "Wormadam Manto de Lixo": "wormadam-trash",
    "Rotom Calor": "rotom-heat",
    "Rotom Lavagem": "rotom-wash",
    "Rotom Frio": "rotom-frost",
    "Rotom Ventilador": "rotom-fan",
    "Rotom Corte": "rotom-mow",
    "Dialga Forma Origem": "dialga-origin",
    "Palkia Forma Origem": "palkia-origin",
    "Giratina Forma Alterada": "giratina-altered",
    "Giratina Forma Origem": "giratina-origin",
    "Shaymin Forma Terrestre": "shaymin-land",
    "Shaymin Forma Celeste": "shaymin-sky",
    "Basculin de Linha Vermelha": "basculin-red-striped",
    "Basculin de Linha Azul": "basculin-blue-striped",
    "Basculin de Linha Branca": "basculin-white-striped",
    "Darmanitan Modo Zen": "darmanitan-zen",
    "Darmanitan de Galar": "darmanitan-galar-standard",
    "Darmanitan de Galar Modo Zen": "darmanitan-galar-zen",
    "Tornadus Forma Encarnada": "tornadus-incarnate",
    "Tornadus Forma Therian": "tornadus-therian",
    "Thundurus Forma Encarnada": "thundurus-incarnate",
    "Thundurus Forma Therian": "thundurus-therian",
    "Landorus Forma Encarnada": "landorus-incarnate",
    "Landorus Forma Therian": "landorus-therian",
    "Enamorus Forma Encarnada": "enamorus-incarnate",
    "Enamorus Forma Therian": "enamorus-therian",
    "Kyurem Preto": "kyurem-black",
    "Kyurem Branco": "kyurem-white",
    "Meloetta Forma Aria": "meloetta-aria",
    "Meloetta Forma Pirueta": "meloetta-pirouette",
    "Greninja do Ash": "greninja-ash",
    "Meowstic Macho": "meowstic-male",
    "Meowstic Fêmea": "meowstic-female",
    "Aegislash Forma Escudo": "aegislash-shield",
    "Aegislash Forma Espada": "aegislash-blade",
    "Zygarde forma 10%": "zygarde-10",
    "Zygarde forma 50%": "zygarde-50",
    "Zygarde Forma Completa": "zygarde-complete",
    "Hoopa Confinado": "hoopa",
    "Hoopa Liberto": "hoopa-unbound",
    "Oricorio Estilo Baile": "oricorio-baile",
    "Oricorio Estilo Pom-Pom": "oricorio-pom-pom",
    "Oricorio Estilo Pa'u": "oricorio-pau",
    "Oricorio Estilo Sensu": "oricorio-sensu",
    "Lycanroc Forma Diurna": "lycanroc-midday",
    "Lycanroc Forma Noturna": "lycanroc-midnight",
    "Lycanroc Forma Crepúsculo": "lycanroc-dusk",
    "Wishiwashi Forma Solo": "wishiwashi-solo",
    "Wishiwashi Forma Cardume": "wishiwashi-school",
    "Minior Forma Meteoro": "minior-red-meteor",
    "Minior Forma Núcleo": "minior-red",
    "Necrozma Juba Crepúsculo": "necrozma-dusk",
    "Necrozma Asas da Alvorada": "necrozma-dawn",
    "Ultra Necrozma": "necrozma-ultra",
    "Toxtricity Forma Estridente": "toxtricity-amped",
    "Toxtricity Forma Suave": "toxtricity-low-key",
    "Eiscue Cara de Gelo": "eiscue-ice",
    "Eiscue Cara Derretida": "eiscue-noice",
    "Indeedee Macho": "indeedee-male",
    "Indeedee Fêmea": "indeedee-female",
    "Zacian Herói de Muitas Batalhas": "zacian",
    "Zacian Espada Coroada": "zacian-crowned",
    "Zamazenta Herói de Muitas Batalhas": "zamazenta",
    "Zamazenta Escudo Coroado": "zamazenta-crowned",
    "Eternatus Eternamax": "eternatus-eternamax",
    "Urshifu Estilo Golpe Único": "urshifu-single-strike",
    "Urshifu Estilo Golpe Rápido": "urshifu-rapid-strike",
    "Calyrex Cavaleiro Glacial": "calyrex-ice",
    "Calyrex Cavaleiro Espectral": "calyrex-shadow",
    "Ursaluna Lua Sangrenta": "ursaluna-bloodmoon",
    "Basculegion Macho": "basculegion-male",
    "Basculegion Fêmea": "basculegion-female",
    "Oinkologne Macho": "oinkologne",
    "Oinkologne Fêmea": "oinkologne-female",
    "Maushold Família com Quatro": "maushold-family-of-four",
    "Maushold Família com Três": "maushold-family-of-three",
    "Squawkabilly Plumagem Verde": "squawkabilly-green-plumage",
    "Squawkabilly Plumagem Azul": "squawkabilly-blue-plumage",
    "Squawkabilly Plumagem Amarela": "squawkabilly-yellow-plumage",
    "Squawkabilly Plumagem Branca": "squawkabilly-white-plumage",
    "Palafin Forma Zero": "palafin-zero",
    "Palafin Forma Herói": "palafin-hero",
    "Tatsugiri Forma Curva": "tatsugiri-curly",
    "Tatsugiri Forma Caída": "tatsugiri-droopy",
    "Tatsugiri Forma Esticada": "tatsugiri-stretchy",
    "Dudunsparce de Dois Segmentos": "dudunsparce-two-segment",
    "Dudunsparce de Três Segmentos": "dudunsparce-three-segment",
    "Gimmighoul Forma Baú": "gimmighoul",
    "Gimmighoul Forma Andarilha": "gimmighoul-roaming",
    "Ogerpon Máscara Turquesa": "ogerpon",
    "Ogerpon Máscara Nascente": "ogerpon-wellspring-mask",
    "Ogerpon Máscara Fornalha": "ogerpon-hearthflame-mask",
    "Ogerpon Máscara Alicerce": "ogerpon-cornerstone-mask",
    "Terapagos Forma Terastal": "terapagos-terastal",
    "Terapagos Forma Estelar": "terapagos-stellar",
    "Wooper de Paldea": "wooper-paldea"
}

REGIONAL_SUFFIXES = {" de Alola": "-alola", " de Galar": "-galar", " de Hisui": "-hisui"}


def slugify_species(name):
    s = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    s = s.replace("'", "").replace("’", "").replace(".", "").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def form_slug_for(name):
    if name in EXPLICIT_SLUGS:
        return EXPLICIT_SLUGS[name]
    for suffix, api_suffix in REGIONAL_SUFFIXES.items():
        if name.endswith(suffix):
            return slugify_species(name[: -len(suffix)]) + api_suffix
    return None


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


def pokeapi_id(slug, cache={}):
    if slug in cache:
        return cache[slug]
    url = f"https://pokeapi.co/api/v2/pokemon/{slug}"
    # pokeapi.co responde 403 a requisições sem User-Agent
    req = urllib.request.Request(url, headers={"User-Agent": "pokemon-mundo-perfeito-foundry/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            cache[slug] = json.load(resp)["id"]
    except Exception:
        cache[slug] = None
    return cache[slug]


def main():
    n_ok = 0
    failures = []
    for f in glob.glob(os.path.join(POKEDEX, "*.json")):
        if os.path.basename(f).startswith("folder-"):
            continue
        doc = json.load(open(f, encoding="utf-8"))
        changed = False

        if doc["name"] in NAME_FIXES:
            doc["name"] = NAME_FIXES[doc["name"]]
            doc.setdefault("prototypeToken", {})["name"] = doc["name"]
            changed = True

        slug = form_slug_for(doc["name"])
        if slug:
            pid = pokeapi_id(slug)
            artwork = ARTWORK.format(id=pid) if pid else None
            if pid and url_exists(artwork):
                doc["img"] = artwork
                sprite = SPRITE.format(id=pid)
                if url_exists(sprite):
                    doc.setdefault("prototypeToken", {}).setdefault("texture", {})["src"] = sprite
                n_ok += 1
                changed = True
            else:
                failures.append((doc["name"], slug))

        if changed:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
                fh.write("\n")

    print(f"{n_ok} formas com arte específica aplicada")
    if failures:
        print(f"{len(failures)} formas sem correspondência no PokeAPI (mantêm a arte da forma base):")
        for name, slug in failures:
            print(f"  - {name} (tentou '{slug}')")


if __name__ == "__main__":
    main()
