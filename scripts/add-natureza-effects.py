#!/usr/bin/env python3
"""
Active Effects nas 20 Naturezas (packs/_source/trainer-features/natureza-*.json): até agora
o bônus/penalidade ("+2 Força, -2 Destreza") era só texto na descrição — o Mestre tinha que
ler e ajustar os atributos manualmente. Agora cada Natureza carrega um Active Effect com
transfer=true, então ao arrastar a Natureza para cima de um Pokémon possuído em mundo, o
Foundry aplica (e remove, se o item for apagado) os ajustes de atributo/CA sozinho.

Idempotente. Uso: python scripts/add-natureza-effects.py
"""
import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAINER = os.path.join(ROOT, "packs", "_source", "trainer-features")

ABILITY_KEY = {
    "Força": "str", "Destreza": "dex", "Constituição": "con",
    "Inteligência": "int", "Sabedoria": "wis", "Carisma": "cha"
}


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


def changes_for_bonus(bonus_text):
    """'+2 Força, -2 Destreza' -> duas mudanças em system.abilities.*.value (modo ADD).
    '+1 CA, -2 Força' -> system.attributes.ac.bonus + system.abilities.str.value."""
    changes = []
    for sign_num, attr in re.findall(r"([+-]\d+)\s+(Força|Destreza|Constituição|Sabedoria|Carisma|CA)",
                                      bonus_text):
        if attr == "CA":
            key = "system.attributes.ac.bonus"
        else:
            key = f"system.abilities.{ABILITY_KEY[attr]}.value"
        # o exemplo real do dnd5e usa "2" sem sinal para bônus positivo (só negativo leva "-")
        changes.append({"key": key, "mode": 2, "value": sign_num.lstrip("+"), "priority": None})
    return changes


def build_effect(item_id, name, img, bonus_text):
    effect_id = make_id(f"natureza-effect-{name}")
    return {
        "_key": f"!items.effects!{item_id}.{effect_id}",
        "_id": effect_id,
        "name": name,
        "img": img,
        "type": "base",
        "system": {},
        "changes": changes_for_bonus(bonus_text),
        "disabled": False,
        "duration": {"startTime": None, "seconds": None, "combat": None, "rounds": None,
                      "turns": None, "startRound": None, "startTurn": None},
        "description": "",
        "tint": "#ffffff",
        "transfer": True,
        "statuses": [],
        "sort": 0,
        "flags": {},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None}
    }


def main():
    n = 0
    for f in glob.glob(os.path.join(TRAINER, "natureza-*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        bonus = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("bonus", "")
        if not bonus:
            continue
        effect = build_effect(doc["_id"], doc["name"], doc["img"], bonus)
        doc["effects"] = [effect]
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        n += 1
    print(f"{n} Naturezas com Active Effect (aplica atributos automaticamente ao arrastar)")


if __name__ == "__main__":
    main()
