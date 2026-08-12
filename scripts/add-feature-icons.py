#!/usr/bin/env python3
"""
Ícones temáticos para os recursos de treinador que ficavam com o ícone genérico
(Classes, Especializações, Habilidades Gerais, Regiões, Origens, Progressão,
Mecânicas) e para as 45 Mega Pedras fan-made sem sprite no PokeAPI.

- Especializações: ícone do TIPO Pokémon associado (flag pokemonType já existente).
- Mega Pedras fan-made: ícone do tipo primário da Mega forma (se a mega não muda o
  tipo, busca o tipo base da espécie na Pokédex); informativo e consistente.
- Demais: ícones core do Foundry (caminhos colhidos do SRD do dnd5e — válidos em
  qualquer instalação).

Idempotente. Uso: python scripts/add-feature-icons.py
"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAINER = os.path.join(ROOT, "packs", "_source", "trainer-features")
MEGAS = os.path.join(ROOT, "packs", "_source", "mega-evolutions")
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")

TYPE_ICON = "https://raw.githubusercontent.com/MissingGlitch/pokemon-images/refs/heads/main/types/{t}.svg"

CLASS_ICONS = {
    "Treinador Ás": "icons/skills/melee/weapons-crossed-swords-yellow.webp",
    "Versátil": "icons/skills/melee/hand-grip-staff-yellow-brown.webp",
    "Mentor Pokémon": "icons/sundries/books/book-embossed-clasp-gold-brown.webp",
    "Enfermeiro": "icons/magic/life/heart-cross-strong-flame-purple-orange.webp",
    "Pesquisador": "icons/skills/trades/academics-investigation-puzzles.webp",
    "Colecionador Pokémon": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png",
    "Comandante": "icons/magic/sonic/scream-wail-shout-teal.webp",
    "Patrulheiro": "icons/creatures/abilities/paw-print-yellow.webp",
    "Capanga": "icons/sundries/flags/banner-skull-red.webp",
    "Tático": "icons/sundries/gaming/chess-knight-white.webp",
    "Guru": "icons/magic/holy/meditation-chi-focus-blue.webp",
    "Criador de Pokémon": "icons/commodities/gems/pearl-storm.webp"
}

HABILIDADE_ICONS = {
    "Rastreador Pokémon": "icons/creatures/mammals/wolf-howl-moon-forest-blue.webp",
    "Aura de Treinador": "icons/magic/light/orbs-firefly-hand-yellow.webp",
    "Determinação do Treinador": "icons/magic/control/buff-strength-muscle-damage-orange.webp",
    "Foco de Treinador": "icons/skills/ranged/target-bullseye-arrow-glowing.webp",
    "Atenção Aguçada": "icons/creatures/eyes/human-single-brown.webp",
    "Treinador Mestre": "icons/magic/control/control-influence-crown-gold.webp"
}

CATEGORY_DEFAULT_ICONS = {
    "regiao-de-origem": "icons/tools/navigation/map-chart-tan.webp",
    "origem-de-jornada": "icons/skills/movement/figure-running-gray.webp",
    "progressao-de-nivel": "icons/skills/movement/arrow-upward-yellow.webp",
    "mecanica-dynamax": "icons/magic/control/buff-strength-muscle-damage-orange.webp",
    "mecanica-terastal": "icons/commodities/gems/gem-faceted-large-green.webp"
}

FALLBACK_GEM = "icons/commodities/gems/pearl-purple-dark.webp"


def save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def base_type_by_species():
    """species (nome em inglês) -> type1, para Mega Pedras que não mudam o tipo."""
    types = {}
    for f in glob.glob(os.path.join(POKEDEX, "*.json")):
        if os.path.basename(f).startswith("folder-"):
            continue
        d = json.load(open(f, encoding="utf-8"))
        sp = d.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("species", {})
        name = d["name"]
        t1 = sp.get("types", {}).get("type1")
        if t1 and name not in types:
            types[name] = t1
    return types


def patch_trainer():
    n = 0
    for f in glob.glob(os.path.join(TRAINER, "*.json")):
        if os.path.basename(f).startswith(("item-", "folder-")):
            continue
        doc = json.load(open(f, encoding="utf-8"))
        if not doc.get("img", "").startswith("icons/svg/"):
            continue
        flags = doc.get("flags", {}).get("pokemon-mundo-perfeito", {})
        category = flags.get("category", "")
        name = doc["name"]

        img = None
        if category == "especializacao" and flags.get("pokemonType"):
            img = TYPE_ICON.format(t=flags["pokemonType"])
        elif category == "classe-de-treinador":
            img = CLASS_ICONS.get(name)
        elif category == "habilidade-geral-treinador":
            img = HABILIDADE_ICONS.get(name)
        else:
            img = CATEGORY_DEFAULT_ICONS.get(category)

        if img:
            doc["img"] = img
            save(f, doc)
            n += 1
    print(f"trainer-features: {n} recursos com ícone temático")


def patch_fanmade_megas():
    species_types = base_type_by_species()
    n = 0
    for f in glob.glob(os.path.join(MEGAS, "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if not doc.get("img", "").startswith("icons/svg/"):
            continue
        sys_ = doc.get("system", {})
        t1 = (sys_.get("types") or {}).get("type1")
        if not t1:
            t1 = species_types.get(sys_.get("species", ""))
        doc["img"] = TYPE_ICON.format(t=t1) if t1 else FALLBACK_GEM
        save(f, doc)
        n += 1
    print(f"mega-evolutions: {n} pedras fan-made com ícone de tipo")


TALENTO_ICONS = {
    # caminhos conferidos contra o compêndio-fonte oficial do dnd5e (github.com/foundryvtt/dnd5e,
    # packs/_source) para não repetir a aposta às cegas que gerou ícones quebrados na v1.1.2
    "Acrobata": "icons/commodities/materials/feather-blue.webp",
    "Adepto de Terreno": "icons/environment/wilderness/cave-entrance-mountain.webp",
    "Alerta": "icons/creatures/eyes/human-single-blue.webp",
    "Atacante Bestial": "icons/magic/earth/strike-fist-stone-gray.webp",
    "Atleta": "icons/magic/control/buff-strength-muscle-damage-orange.webp",
    "Ator": "icons/commodities/treasure/mask-wood-tan.webp",
    "Controlador de área": "icons/magic/earth/explosion-lava-orange.webp",
    "Corpo Apto": "icons/magic/life/heart-cross-green.webp",
    "Curandeiro": "icons/magic/life/heart-cross-blue.webp",
    "Dedos Rápidos": "icons/equipment/finger/ring-band-copper.webp",
    "Disputador": "icons/magic/control/debuff-chains-ropes-net-red-orange.webp",
    "Escultor de Poder": "icons/magic/lightning/barrier-shield-crackling-orb-pink.webp",
    "Esquivo": "icons/equipment/back/cloak-hooded-blue.webp",
    "Aumento de CA": "icons/equipment/shield/heater-crystal-blue.webp",
    "Explorador dos Céus": "icons/commodities/treasure/trinket-wing-white.webp",
    "Explorador dos Mares": "icons/tools/nautical/anchor-blue.webp",
    "Explorador das Profundezas": "icons/commodities/stone/rock-chunk-brown.webp",
    "Explorador de Cavernas": "icons/environment/wilderness/cave-entrance-dwarven-hill.webp",
    "Incansável": "icons/magic/time/day-night-sunset-sunrise.webp",
    "Investida Poderosa": "icons/magic/earth/explosion-lava-stone-red.webp",
    "Mente Afiada": "icons/commodities/biological/organ-brain-pink-purple.webp",
    "Mestre de Combate à Distância": "icons/skills/ranged/arrow-flying-broadhead-metal.webp",
    "Mestre de Combate Corpo a Corpo": "icons/creatures/abilities/fang-tooth-blood-red.webp",
    "Mestre do Tipo": "icons/magic/control/silhouette-aura-energy.webp",
    "Mobilidade": "icons/equipment/feet/boots-layered-blue.webp",
    "Move Extra": "icons/magic/time/clock-spinning-gold-pink.webp",
    "Musculoso": "icons/magic/control/buff-strength-muscle-damage-red.webp",
    "Observador": "icons/tools/navigation/compass-brass-blue-red.webp",
    "Pequeno Grande": "icons/magic/nature/plant-sprout-snow-green.webp",
    "Perceptivo": "icons/creatures/birds/raptor-owl-flying-moon.webp",
    "Perito": "icons/sundries/books/book-embossed-jewel-gold-purple.webp",
    "Resiliente": "icons/magic/defensive/barrier-shield-dome-blue-purple.webp",
    "Resistente": "icons/commodities/treasure/statue-bust-stone-grey.webp",
    "Robusto": "icons/commodities/treasure/statue-runed-blue-grey.webp",
    "Sentinela": "icons/environment/traps/trap-jaw-green.webp",
    "Sorrateiro": "icons/equipment/head/hood-purple-mask.webp",
    "Sortudo": "icons/commodities/currency/coins-plain-stack-gold.webp",
}

NATUREZA_ICON_BY_ATTR = {
    "Força": "icons/magic/control/buff-strength-muscle-damage-orange.webp",
    "Destreza": "icons/commodities/materials/feather-blue.webp",
    "Constituição": "icons/magic/life/heart-cross-green.webp",
    "Sabedoria": "icons/svg/light.svg",
    "Carisma": "icons/magic/control/silhouette-aura-energy.webp",
    "CA": "icons/equipment/shield/heater-crystal-blue.webp",
}


def patch_talentos_naturezas():
    n = 0
    for f in glob.glob(os.path.join(TRAINER, "talento-*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        img = TALENTO_ICONS.get(doc["name"])
        if img:
            doc["img"] = img
            save(f, doc)
            n += 1
    for f in glob.glob(os.path.join(TRAINER, "natureza-*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        bonus = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("bonus", "")
        m = re.search(r"[+-]\d+\s+(Força|Destreza|Constituição|Sabedoria|Carisma|CA)", bonus)
        img = NATUREZA_ICON_BY_ATTR.get(m.group(1)) if m else None
        if img:
            doc["img"] = img
            save(f, doc)
            n += 1
    print(f"trainer-features: {n} talentos/naturezas com ícone próprio")


def main():
    patch_trainer()
    patch_fanmade_megas()
    patch_talentos_naturezas()


if __name__ == "__main__":
    main()
