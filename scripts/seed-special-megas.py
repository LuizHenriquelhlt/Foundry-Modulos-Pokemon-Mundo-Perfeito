#!/usr/bin/env python3
"""
Fase 4 (parte 2) — "O Trio do Clima" (Livro de Mega Evoluções, página 40):
Mega Rayquaza, Kyogre Primal e Groudon Primal têm um formato de texto mais
condensado (sem a mesma frase-âncora e bullets do resto da lista), então são
adicionados aqui a partir da leitura direta da página, em vez do parser genérico.
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "mega-evolutions")


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


def base_item(doc_id, name, system, img="icons/svg/upgrade.svg"):
    return {
        "_id": doc_id, "name": name, "type": "equipment", "img": img, "system": system,
        "effects": [], "folder": None, "flags": {"pokemon-mundo-perfeito": {"category": "mega-stone-especial"}},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": 900, "ownership": {"default": 0}
    }


ENTRIES = [
    {
        "stoneName": "Rayquazanite (não requer Mega Pedra)",
        "species": "Rayquaza", "megaForm": "Mega Rayquaza",
        "types": {"type1": None, "type2": None},
        "size": "gigantic",
        "armorClassDelta": 1,
        "abilityDeltas": {"str": 5, "dex": 5, "wis": 2},
        "abilityChoices": [], "movementBonusFeet": 0, "movementGrants": [], "otherEffects": [
            "Rayquaza pode Mega Evoluir assim que aprende o Move Dragon Ascent, sem precisar de Mega Pedra "
            "(o Mestre pode exigir um Meteorite ou inventar uma Rayquazanite)."
        ],
        "passiveAbility": "Delta Stream",
        "description": "<p>Rayquaza pode Mega Evoluir assim que aprende o Move Dragon Ascent, desde que todos "
                        "os requisitos não relacionados à Mega Pedra sejam atendidos e Rayquaza não esteja "
                        "segurando um Cristal-Z. Mega Rayquaza é um dos Pokémon mais poderosos do jogo.</p>"
    },
    {
        "stoneName": "Blue Orb",
        "species": "Kyogre", "megaForm": "Kyogre Primal",
        "types": {"type1": None, "type2": None},
        "size": "gigantic",
        "armorClassDelta": 1,
        "abilityDeltas": {"str": 3, "dex": 5, "wis": 2},
        "abilityChoices": [], "movementBonusFeet": 0, "movementGrants": [], "otherEffects": [
            "Reversão Primal, não Mega Evolução: nível mínimo 10, 1 uso por descanso (2 usos a partir do "
            "nível 15), exige segurar a Blue Orb. Não depende de Treinador ou lealdade — Pokémon Primal sem "
            "lealdade máxima não obedece comandos e ataca ameaças percebidas por conta própria."
        ],
        "passiveAbility": "Primordial Sea",
        "description": "<p>Kyogre não Mega Evolui — passa pela Reversão Primal, retornando a um poder que "
                        "já teve ao absorver a força da natureza ao redor. Pokémon Primal são extremamente "
                        "perigosos, capazes de causar desastres naturais massivos.</p>"
    },
    {
        "stoneName": "Red Orb",
        "species": "Groudon", "megaForm": "Groudon Primal",
        "types": {"type1": "ground", "type2": "fire"},
        "size": "gigantic",
        "armorClassDelta": 2,
        "abilityDeltas": {"str": 5, "dex": 3},
        "abilityChoices": [], "movementBonusFeet": 0, "movementGrants": [], "otherEffects": [
            "Reversão Primal, não Mega Evolução: nível mínimo 10, 1 uso por descanso (2 usos a partir do "
            "nível 15), exige segurar a Red Orb. Mesmas regras de obediência/lealdade do Kyogre Primal."
        ],
        "passiveAbility": "Desolate Land",
        "description": "<p>Groudon não Mega Evolui — passa pela Reversão Primal, retornando a um poder que "
                        "já teve ao absorver a força da natureza ao redor. Pokémon Primal são extremamente "
                        "perigosos, capazes de causar desastres naturais massivos.</p>"
    }
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for e in ENTRIES:
        doc = base_item(make_id(f"mega-especial-{e['stoneName']}"), e["stoneName"], e)
        slug = e["megaForm"].lower().replace(" ", "-")
        with open(os.path.join(OUT_DIR, f"{slug}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    print(f"{len(ENTRIES)} entradas especiais (Trio do Clima) escritas em {OUT_DIR}")


if __name__ == "__main__":
    main()
