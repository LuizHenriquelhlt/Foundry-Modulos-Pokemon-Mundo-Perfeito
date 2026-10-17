#!/usr/bin/env python3
"""
Completa o "Deslocamento" das espécies em que o parser da Pokédex só leu a primeira linha.

No Livro dos Pokémon, quando o deslocamento não cabe numa linha, o resto ("voo", "9m de
natação") vai para a linha de baixo, e parse-pokedex.py guardava só a primeira — 66
espécies ficaram com flags.species.movement.other cortado ("9m de caminhada, 9m de
escalada, 6m de") e, pior, sem o último modo na ficha (o Heracross não tinha voo).

Lê o livro com PyMuPDF: cada coluna começa com o nome da espécie em fonte "PokemonGB"
("Heracross #0214"; formas vêm sem o número e às vezes em duas linhas); a linha
"Deslocamento:" daquela coluna é emendada com as linhas logo abaixo, no mesmo recuo, até a
linha em branco. Só mexe numa espécie quando o texto guardado
é um começo do texto do livro (ou seja, foi cortado) — e só refaz system.attributes.movement
quando ele ainda era o calculado pelo conversor a partir do texto antigo.
Idempotente. Uso: python scripts/fix-pokedex-movement.py "<pasta com os PDFs>"
"""
import glob
import importlib.util
import json
import os
import re
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")
MODULE_ID = "pokemon-mundo-perfeito"
BOOK = "Livro dos Pokémon - Pokémon Mundo Perfeito.pdf"
HEADING_FONT = "PokemonGB"
LABEL = "Deslocamento:"

# Texto do livro com erro de digitação que impede a leitura do deslocamento: "7,5 de caminhada"
# (sem o "m") fazia a ficha do Palafin Forma Herói sair com 50 pés de caminhada — o primeiro
# número com "m" era o da natação.
OVERRIDES = {
    "Palafin Forma Herói": "7,5m de caminhada, 15m de natação",
}

spec = importlib.util.spec_from_file_location("convert_native", os.path.join(HERE, "convert-to-dnd5e-native.py"))
convert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(convert)


def norm_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def book_movements(pdf_path):
    """{nome da espécie como no título: texto completo do Deslocamento}"""
    doc = pymupdf.open(pdf_path)
    found = {}
    for page in doc:
        mid = page.rect.width / 2
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"])
                fonts = {s["font"] for s in line["spans"] if s["text"].strip()}
                lines.append((line["bbox"][0], line["bbox"][1], text, fonts))
        for column in (0, 1):
            col = sorted((l for l in lines if (l[0] >= mid) == bool(column)), key=lambda l: l[1])
            species = None
            i = 0
            while i < len(col):
                x, y, text, fonts = col[i]
                if any(f.startswith(HEADING_FONT) for f in fonts):
                    # título da espécie; formas vêm sem "#número" e às vezes em 2 linhas
                    # ("Dudunsparce de Dois" / "Segmentos")
                    parts = [text.split("#")[0]]
                    j = i + 1
                    while j < len(col) and any(f.startswith(HEADING_FONT) for f in col[j][3]) \
                            and col[j][1] - col[j - 1][1] < 16:
                        parts.append(col[j][2].split("#")[0])
                        j += 1
                    species = norm_space(" ".join(parts))
                    i = j
                    continue
                elif text.strip().startswith(LABEL) and species:
                    parts, last_y = [text.strip()[len(LABEL):]], y
                    j = i + 1
                    while j < len(col):
                        nx, ny, ntext, _ = col[j]
                        if not ntext.strip() or abs(nx - x) > 3 or ny - last_y > 16:
                            break
                        parts.append(ntext)
                        last_y = ny
                        j += 1
                    found.setdefault(species, norm_space(" ".join(parts)))
                    i = j
                    continue
                i += 1
    return found


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/fix-pokedex-movement.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    book = book_movements(os.path.join(sys.argv[1], BOOK))
    print(f"{len(book)} deslocamentos lidos do livro")

    fixed, sheet_kept, not_found, hover = [], [], [], []
    for f in sorted(glob.glob(os.path.join(POKEDEX, "*.json"))):
        doc = json.load(open(f, encoding="utf-8"))
        if doc["_key"].startswith("!folders"):
            continue
        species = doc["flags"][MODULE_ID]["species"]
        stored = norm_space(species.get("movement", {}).get("other", ""))
        override = OVERRIDES.get(doc["name"])
        full = override or book.get(species.get("species")) or book.get(doc["name"])
        if full is None:
            not_found.append(doc["name"])
            continue
        sheet = doc["system"]["attributes"]["movement"]
        truncated = full != stored and full.startswith(stored) and len(full) > len(stored)
        if truncated or (override and full != stored):
            old_sheet = convert.parse_movement(species)
            species["movement"]["other"] = full
            new_sheet = convert.parse_movement(species)
            # ficha ainda igual à calculada do texto antigo (com ou sem "hover", que o conversor
            # antigo não lia) — ou é a exceção explícita: troca pela do texto completo
            if override or {**sheet, "hover": old_sheet["hover"]} == old_sheet:
                doc["system"]["attributes"]["movement"] = new_sheet
            else:
                sheet_kept.append(doc["name"])
            convert.save(f, doc)
            added = {k: v for k, v in new_sheet.items() if sheet.get(k) != v}
            fixed.append(f"{doc['name']}: \"{stored}\" → \"{full}\" {added}")
            continue
        # texto já completo: só acerta o "hover" de "voo (flutuação)", que o conversor não lia
        expected = convert.parse_movement(species)
        if expected["hover"] and not sheet.get("hover") and {**sheet, "hover": True} == expected:
            sheet["hover"] = True
            convert.save(f, doc)
            hover.append(doc["name"])

    print(f"\n{len(fixed)} espécies com o deslocamento completado:")
    for line in fixed:
        print(f"  {line}")
    if hover:
        print(f"{len(hover)} espécies com \"voo (flutuação)\" marcadas como flutuantes na ficha: {hover}")
    if sheet_kept:
        print(f"Ficha mexida à mão, deslocamento nativo mantido: {sheet_kept}")
    if not_found:
        print(f"{len(not_found)} espécies sem título correspondente no livro: {not_found[:15]}")


if __name__ == "__main__":
    main()
