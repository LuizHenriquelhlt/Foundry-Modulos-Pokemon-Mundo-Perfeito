#!/usr/bin/env python3
"""
Itens consumíveis de cura (Poções, Berries restauradoras, Éteres de PV etc.) ficavam com
uma activity "utility" genérica (só o botão "Usar", sem rolagem) — o texto "Restaura Xd Y+Z
PV" já extraído na descrição não virava uma rolagem de cura de verdade. Troca a activity
desses itens por "heal" (dnd5e), preservando o consumo de 1 uso/autoDestroy já existente.

Roda depois de fix-item-usability.py. Idempotente.
Uso: python scripts/add-healing-activities.py
"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAINER = os.path.join(ROOT, "packs", "_source", "trainer-features")

DICE_RE = re.compile(r"[Rr]estaura (\d+)d(\d+)(?:\s*\+\s*(\d+))?\s*PV")
FLAT_RE = re.compile(r"[Rr]estaura (\d+)\s*PV")


def save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def healing_field(desc):
    m = DICE_RE.search(desc)
    if m:
        number, denom, bonus = m.group(1), m.group(2), m.group(3)
        return {
            "number": int(number), "denomination": int(denom), "bonus": bonus or "",
            "types": [], "custom": {"enabled": False, "formula": ""}, "modifiers": [],
            "scaling": {"mode": "", "number": 1, "formula": ""}
        }
    m = FLAT_RE.search(desc)
    if m:
        return {
            "number": 0, "denomination": 0, "bonus": m.group(1),
            "types": [], "custom": {"enabled": False, "formula": ""}, "modifiers": [],
            "scaling": {"mode": "", "number": 1, "formula": ""}
        }
    return None


def main():
    n = 0
    for f in glob.glob(os.path.join(TRAINER, "item-*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if doc.get("type") != "consumable":
            continue
        desc = doc.get("system", {}).get("description", {}).get("value", "")
        healing = healing_field(desc)
        if not healing:
            continue
        activities = doc.get("system", {}).get("activities", {})
        for act in activities.values():
            if act.get("type") != "utility":
                continue
            act["type"] = "heal"
            act["healing"] = healing
            act.pop("roll", None)
        save(f, doc)
        n += 1
    print(f"{n} itens de cura convertidos para activity 'heal' com rolagem")


if __name__ == "__main__":
    main()
