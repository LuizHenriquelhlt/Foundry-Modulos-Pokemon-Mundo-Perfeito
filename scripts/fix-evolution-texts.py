#!/usr/bin/env python3
"""
Corrige textos de evolução da Pokédex que não declaram a forma de destino.

Formas regionais copiavam a frase da forma comum ("Growlithe pode evoluir para Arcanine" no
Growlithe de Hisui), o Goomy cita "Sligoo de Hisui", o Darmanitan de Galar Modo Zen aponta
pro Darumaka comum, o Snorunt diz "para a Froslass" e o Burmy chama de "Manto de Grama" a
forma que a Pokédex chama de "Manto de Planta". Troca só o trecho, em todo o documento
(flags e biografia).

Também acerta o estágio evolutivo da família Zigzagoon de Galar: o livro dá 1/2 e 2/2 pra
Zigzagoon e Linoone de Galar, mas o Linoone de Galar evolui pro Obstagoon (3/3) — o
estágio máximo da família é 3. Idempotente. Uso: python scripts/fix-evolution-texts.py
"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")

FIXES = {
    "Growlithe de Hisui": [("Growlithe pode evoluir para Arcanine ", "Growlithe de Hisui pode evoluir para Arcanine de Hisui ")],
    "Ponyta de Galar": [("Ponyta pode evoluir para Rapidash ", "Ponyta de Galar pode evoluir para Rapidash de Galar ")],
    "Zorua de Hisui": [("Zorua pode evoluir para Zoroark ", "Zorua de Hisui pode evoluir para Zoroark de Hisui ")],
    "Sliggoo de Hisui": [("Sliggoo pode evoluir para Goodra ", "Sliggoo de Hisui pode evoluir para Goodra de Hisui ")],
    "Voltorb de Hisui": [("para Electrode no", "para Electrode de Hisui no")],
    "Goomy": [("Sligoo de Hisui", "Sliggoo de Hisui")],
    "Darmanitan de Galar Modo Zen": [("evolução final de Darumaka.", "evolução final de Darumaka de Galar.")],
    "Snorunt": [("para a Froslass", "para Froslass")],
    "Burmy": [("Manto de Grama", "Manto de Planta")],
}
STAGE_FIXES = {"Zigzagoon de Galar": (1, 3), "Linoone de Galar": (2, 3)}
STAGE_FIELD = re.compile(r'"evolutionStage": \{\s*"current": \d+,\s*"max": \d+\s*\}')


def main():
    changed = []
    for path in glob.glob(os.path.join(POKEDEX, "*.json")):
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        name = json.loads(raw).get("name")
        if name not in FIXES and name not in STAGE_FIXES:
            continue
        new = raw
        for old, fixed in FIXES.get(name, []):
            new = new.replace(old, fixed)
        if name in STAGE_FIXES:
            current, top = STAGE_FIXES[name]
            new, count = STAGE_FIELD.subn(lambda m: f'"evolutionStage": {{"current": {current}, "max": {top}}}', new, count=1)
            if not count:
                raise SystemExit(f"{name}: evolutionStage não encontrado")
        doc = json.loads(new)  # continua JSON válido
        if doc != json.loads(raw):
            if name in STAGE_FIXES:
                # reescreve com a formatação do resto do pack
                new = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            changed.append(name)
    print(f"Textos de evolução corrigidos: {len(changed)} {sorted(changed)}")


if __name__ == "__main__":
    main()
