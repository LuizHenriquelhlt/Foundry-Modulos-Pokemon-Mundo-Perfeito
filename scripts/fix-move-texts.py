#!/usr/bin/env python3
"""
Aplica aos dados já guardados dos Moves (flags.move) as mesmas limpezas que parse-moves.py
passou a fazer na extração:

- tira o crédito de arte colado no fim de um trecho ("Arte feita twarda8" no Mist Ball,
  "Arte Sweet Kiss Arte feita por (Beijo Doce) megubunnii" no Swallow...);
- grava a prioridade declarada no texto ("prioridade 3" do Fake Out ficava 0, porque o
  parser só reconhecia "prioridade 1").

Depois rode scripts/rebuild-moves.py, que refaz o "system" (descrição da ficha) e leva tudo
para as cópias dos Moves embutidas na Pokédex. Idempotente.
Uso: python scripts/fix-move-texts.py
"""
import glob
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOVES = os.path.join(ROOT, "packs", "_source", "moves")
MODULE_ID = "pokemon-mundo-perfeito"

spec = importlib.util.spec_from_file_location("parse_moves", os.path.join(HERE, "parse-moves.py"))
parse_moves = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parse_moves)


def clean_html(html):
    """Os campos de texto são "<p>...</p>": limpa o conteúdo e devolve no mesmo formato."""
    m = re.match(r"^<p>(.*)</p>$", html or "", re.DOTALL)
    if not m:
        return html
    inner = parse_moves.strip_art_credit(m.group(1))
    return f"<p>{inner}</p>" if inner else ""


def main():
    changed = []
    for f in sorted(glob.glob(os.path.join(MOVES, "*.json"))):
        doc = json.load(open(f, encoding="utf-8"))
        move = doc.get("flags", {}).get(MODULE_ID, {}).get("move")
        if not move:
            continue
        before = json.dumps(move, ensure_ascii=False)
        for field in ("description", "higherLevels", "observations"):
            move[field] = clean_html(move.get(field, ""))
        move["priority"] = parse_moves.move_priority(re.sub(r"<[^>]+>", " ", move.get("description", "")))
        if json.dumps(move, ensure_ascii=False) != before:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            changed.append(doc["name"])
    print(f"{len(changed)} Moves limpos: {changed}")


if __name__ == "__main__":
    main()
