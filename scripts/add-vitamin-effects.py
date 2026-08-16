#!/usr/bin/env python3
"""
Active Effects nos 5 "vitamina" (Protein, Carbos, Iron, Calcium, Zinc): até agora eram só
consumíveis com botão "Usar" genérico e texto "Recebe imediatamente 2 Pontos de EV em X" —
o Mestre tinha que ajustar o atributo na mão. Diferente das Naturezas (item permanente na
ficha, transfer=true), esses itens são CONSUMIDOS (autoDestroy) — um effect transfer=true
sumiria junto com o item destruído. Por isso o effect aqui fica com transfer=false direto no
item (um "molde"), referenciado pela Activity; usar o item mostra o botão "Aplicar Efeitos"
no chat, que cria uma cópia independente do effect no Ator, sobrevivendo à destruição do item
(mesmo padrão usado pelas poções de item mágico oficiais do dnd5e, ex. Potion of Giant
Strength).

Idempotente. Uso: python scripts/add-vitamin-effects.py
"""
import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAINER = os.path.join(ROOT, "packs", "_source", "trainer-features")

# nome do item -> (atributo dnd5e, sigla PT usada na descrição)
VITAMINS = {
    "Protein": "str", "Carbos": "dex", "Iron": "con", "Calcium": "cha", "Zinc": "wis"
}
EV_RE = re.compile(r"(\d+)\s*Pontos? de EV")


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


def build_effect(item_id, name, img, ability_key, amount):
    effect_id = make_id(f"vitamina-effect-{name}")
    return effect_id, {
        "_key": f"!items.effects!{item_id}.{effect_id}",
        "_id": effect_id,
        "name": name,
        "img": img,
        "origin": None,
        "type": "base",
        "system": {},
        "changes": [
            {"key": f"system.abilities.{ability_key}.value", "mode": 2,
             "value": str(amount), "priority": None}
        ],
        "disabled": False,
        "duration": {"startTime": None, "seconds": None, "combat": None, "rounds": None,
                      "turns": None, "startRound": None, "startTurn": None},
        "description": "",
        "tint": "#ffffff",
        "transfer": False,
        "statuses": [],
        "sort": 0,
        "flags": {},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None}
    }


def main():
    n = 0
    for f in glob.glob(os.path.join(TRAINER, "item-*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        ability_key = VITAMINS.get(doc["name"])
        if not ability_key:
            continue
        desc = doc.get("system", {}).get("description", {}).get("value", "")
        m = EV_RE.search(desc)
        amount = int(m.group(1)) if m else 2

        effect_id, effect = build_effect(doc["_id"], doc["name"], doc["img"], ability_key, amount)
        doc["effects"] = [effect]

        for act in doc.get("system", {}).get("activities", {}).values():
            if act.get("type") == "utility":
                act["effects"] = [{"_id": effect_id, "uuid": None, "level": {}}]

        with open(f, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        n += 1
    print(f"{n} vitaminas com Active Effect (botão 'Aplicar Efeitos' aumenta o atributo)")


if __name__ == "__main__":
    main()
