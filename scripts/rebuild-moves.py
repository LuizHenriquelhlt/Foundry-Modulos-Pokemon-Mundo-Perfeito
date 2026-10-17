#!/usr/bin/env python3
"""
Regera o "system" de todos os Moves do compêndio a partir dos dados do livro guardados em
flags.move (convert-to-dnd5e-native.move_system — o mesmo caminho do conversor), e leva o
resultado para as cópias embutidas nos Actors da Pokédex.

Use depois de mudar a modelagem dos Moves no conversor (ex.: CD com modificador, áreas lidas
da descrição). Só atualiza uma cópia embutida se ela ainda era idêntica ao Move do compêndio
ANTES desta execução — cópia ajustada à mão fica como está e é listada no relatório.
Idempotente. Uso: python scripts/rebuild-moves.py
"""
import glob
import importlib.util
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOVES = os.path.join(ROOT, "packs", "_source", "moves")
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")
MODULE_ID = "pokemon-mundo-perfeito"

spec = importlib.util.spec_from_file_location("convert_native", os.path.join(HERE, "convert-to-dnd5e-native.py"))
convert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(convert)


def load_moves():
    out = {}
    for f in glob.glob(os.path.join(MOVES, "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if not doc["_key"].startswith("!folders"):
            out[doc["name"]] = (f, doc)
    return out


def main():
    before = load_moves()
    changed = Counter()
    for name, (path, doc) in before.items():
        pmp = doc.get("flags", {}).get(MODULE_ID, {}).get("move")
        if not pmp:
            continue
        system = convert.move_system(pmp, name)
        if system != doc["system"]:
            new_doc = dict(doc, system=system)
            convert.save(path, new_doc)
            kinds = []
            old_acts, new_acts = doc["system"]["activities"], system["activities"]
            if any(a.get("target") != new_acts.get(i, {}).get("target") for i, a in old_acts.items()):
                kinds.append("área")
            if any(a.get("save", {}).get("dc") != new_acts.get(i, {}).get("save", {}).get("dc") for i, a in old_acts.items()):
                kinds.append("CD")
            changed[", ".join(kinds) or "outros campos"] += 1
    after = load_moves()

    copies, kept = 0, []
    for f in glob.glob(os.path.join(POKEDEX, "*.json")):
        actor = json.load(open(f, encoding="utf-8"))
        touched = False
        for item in actor.get("items", []):
            if item.get("type") != "feat" or item["name"] not in after:
                continue
            if not item.get("flags", {}).get(MODULE_ID, {}).get("move"):
                continue
            old_system = before[item["name"]][1]["system"]
            new_system = after[item["name"]][1]["system"]
            if item["system"] == new_system:
                continue
            if item["system"] != old_system:
                kept.append(f"{actor['name']}: {item['name']}")
                continue
            item["system"] = json.loads(json.dumps(new_system))
            copies += 1
            touched = True
        if touched:
            convert.save(f, actor)

    print(f"Moves regerados no compêndio: {sum(changed.values())} {dict(changed)}")
    print(f"Cópias embutidas na Pokédex atualizadas: {copies}")
    if kept:
        print(f"{len(kept)} cópias diferentes do compêndio, mantidas como estão: {kept[:10]}")


if __name__ == "__main__":
    main()
