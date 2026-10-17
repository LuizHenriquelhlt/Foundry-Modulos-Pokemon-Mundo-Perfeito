#!/usr/bin/env python3
"""
Sincroniza os Moves de Gen 8/9 do compêndio "moves" com a versão ATUAL dos suplementos
(capítulos "Moves da Oitava Geração" e "Moves da Nona Geração"). Substitui o antigo
parse-gen89-moves.py, que só criava Moves ainda inexistentes e no formato pré-dnd5e — este
lê o livro com o mesmo parser (parse-moves.parse_block) e:

- Move já existente vindo do suplemento (flag source Gen8/Gen9): atualiza os campos lidos
  do livro em flags.move, mantendo os que vieram de outras fontes (ex.: zPowerEffect, do
  livro de Z-Moves), e refaz o "system" com convert-to-dnd5e-native.move_system();
- Move cujo nome a extração antiga quebrou ("S urging Strikes"): renomeia mantendo o _id,
  porque a Pokédex referencia os Moves por UUID nos avanços de nível;
- Move novo: cria o Item feat nativo, na pasta e com o ícone do tipo;
- Moves que também estão na Lista de Moves do Livro de Regras (source base) não são
  tocados — o livro principal tem precedência, como no parse-gen89-moves.py original;
  diferenças só aparecem no relatório.

Depois propaga as mudanças para as cópias embutidas nos Actors da Pokédex. Só reescreve
um documento (do compêndio ou embutido) se o "system" atual ainda for o gerado
automaticamente; se alguém o ajustou à mão, mantém e avisa.

As páginas de cada capítulo vêm do sumário do PDF, então funciona em versões novas dos
suplementos com outra paginação. Idempotente.
Uso: python scripts/sync-gen89-moves.py "<pasta com os PDFs>"
"""
import glob
import importlib.util
import json
import os
import re
import sys
import unicodedata

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOVES = os.path.join(ROOT, "packs", "_source", "moves")
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")
TYPE_ICON = "modules/pokemon-mundo-perfeito/assets/types/{type}.svg"

BOOKS = [
    ("Geração 8 - Pokémon Mundo Perfeito.pdf", "Moves da Oitava", "Gen8"),
    ("Geração 9 - Pokémon Mundo Perfeito.pdf", "Moves da Nona", "Gen9"),
]

# campos de flags.move que vêm do texto do livro; o resto (ex.: zPowerEffect) é preservado
BOOK_FIELDS = ["moveType", "category", "power", "powerAbilities", "activation", "pp", "duration",
               "range", "priority", "description", "higherLevels", "observations", "damage"]


def load_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parse_moves = load_script("parse-moves.py", "parse_moves")
parse_moves.ALLOW_BARE_NAMES = True  # nos suplementos o nome vem sem tradução
convert = load_script("convert-to-dnd5e-native.py", "convert_native")
sys.path.insert(0, os.path.join(HERE, "lib"))
from pdf_text import extract_range, strip_noise  # noqa: E402


def key_of(name):
    text = "".join(c for c in unicodedata.normalize("NFKD", name.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text)


def chapter_pages(pdf_path, prefix):
    doc = pymupdf.open(pdf_path)
    tops = [(t.strip(), p) for lv, t, p in doc.get_toc() if lv == 1]
    for i, (t, p) in enumerate(tops):
        if t.startswith(prefix):
            return p, (tops[i + 1][1] - 1 if i + 1 < len(tops) else doc.page_count)
    raise SystemExit(f"Capítulo '{prefix}...' não encontrado no sumário de {pdf_path}")


def parse_book(pdf_path, prefix):
    first, last = chapter_pages(pdf_path, prefix)
    lines = [l for l in strip_noise(extract_range(pdf_path, first, last, n_columns=2)).split("\n") if l.strip()]
    headers = parse_moves.find_move_headers(lines)
    moves, warnings = [], []
    for i, header in enumerate(headers):
        end = headers[i + 1]["start"] if i + 1 < len(headers) else len(lines)
        name, system, warns = parse_moves.parse_block(lines, header, end)
        moves.append((name, system))
        warnings.extend(warns)
    return (first, last), moves, warnings


def is_generated(doc_system, pmp, name):
    return doc_system == convert.move_system(pmp, name)


def merged_pmp(old, parsed):
    pmp = dict(old)
    pmp.update({k: parsed[k] for k in BOOK_FIELDS if k in parsed})
    return pmp


def save(path, doc):
    convert.save(path, doc)


def new_move_doc(name, pmp, tag, sort, used_ids):
    doc_id = parse_moves.make_id(name + tag, used_ids)
    mtype = pmp.get("moveType", "")
    icon = TYPE_ICON.format(type=mtype)
    has_icon = os.path.exists(os.path.join(ROOT, "assets", "types", f"{mtype}.svg"))
    return {
        "_key": f"!items!{doc_id}",
        "_id": doc_id, "name": name, "type": "feat",
        "img": icon if has_icon else "icons/svg/item-bag.svg",
        "system": convert.move_system(pmp, name),
        "effects": [], "folder": convert.make_id(f"folder-moves-{mtype}"),
        "flags": {"pokemon-mundo-perfeito": {"source": tag, "move": pmp}},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": sort, "ownership": {"default": 0}
    }


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/sync-gen89-moves.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]

    pack = {}  # key_of(nome) -> (arquivo, doc)
    used_ids = set()
    for f in glob.glob(os.path.join(MOVES, "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        used_ids.add(doc["_id"])
        if not doc["_key"].startswith("!folders"):
            pack[key_of(doc["name"])] = (f, doc)

    changes = {}  # nome antigo -> (nome novo, pmp antigo, pmp novo)
    created, unchanged, base_diffs, report = [], 0, [], []
    for filename, prefix, tag in BOOKS:
        pdf_path = os.path.join(pdf_dir, filename)
        pages, moves, warnings = parse_book(pdf_path, prefix)
        print(f"{filename}: {len(moves)} Moves nas páginas {pages[0]}-{pages[1]}")
        report.extend(f"[{tag}] {w}" for w in warnings)

        for i, (name, parsed) in enumerate(moves):
            hit = pack.get(key_of(name))
            if hit is None:
                pmp = merged_pmp({}, parsed)
                doc = new_move_doc(name, pmp, tag, 10000 + i * 10, used_ids)
                path = os.path.join(MOVES, f"{parse_moves.slugify(name)}.json")
                if os.path.exists(path):
                    path = os.path.join(MOVES, f"{parse_moves.slugify(name)}-{tag.lower()}.json")
                save(path, doc)
                pack[key_of(name)] = (path, doc)
                created.append(f"{name} ({tag})")
                continue

            path, doc = hit
            flags = doc["flags"]["pokemon-mundo-perfeito"]
            old_pmp = flags["move"]
            new_pmp = merged_pmp(old_pmp, parsed)
            if flags.get("source") not in ("Gen8", "Gen9"):
                if new_pmp != old_pmp:
                    base_diffs.append(name)
                continue
            if new_pmp == old_pmp and doc["name"] == name:
                unchanged += 1
                continue
            if not is_generated(doc["system"], old_pmp, doc["name"]):
                report.append(f"{doc['name']}: system ajustado à mão no compêndio — não atualizado")
                continue
            old_name = doc["name"]
            doc["name"] = name
            doc["system"] = convert.move_system(new_pmp, name)
            flags["move"] = new_pmp
            new_path = os.path.join(MOVES, f"{parse_moves.slugify(name)}.json")
            if new_path != path and not os.path.exists(new_path):
                os.remove(path)
                path = new_path
            save(path, doc)
            pack[key_of(name)] = (path, doc)
            changes[old_name] = (name, old_pmp, new_pmp)

    # cópias embutidas nos Actors da Pokédex
    embedded = 0
    for f in glob.glob(os.path.join(POKEDEX, "*.json")):
        actor = json.load(open(f, encoding="utf-8"))
        touched = False
        for item in actor.get("items", []):
            if item.get("type") != "feat" or item["name"] not in changes:
                continue
            new_name, old_pmp, new_pmp = changes[item["name"]]
            item_flags = item.get("flags", {}).get("pokemon-mundo-perfeito", {})
            if item_flags.get("move") != old_pmp or not is_generated(item["system"], old_pmp, item["name"]):
                report.append(f"{actor['name']}: cópia de {item['name']} ajustada à mão — não atualizada")
                continue
            item["name"] = new_name
            item["system"] = convert.move_system(new_pmp, new_name)
            item_flags["move"] = new_pmp
            touched = True
            embedded += 1
        if touched:
            save(f, actor)

    print(f"\n{len(changes)} Moves atualizados, {len(created)} criados, {unchanged} já estavam iguais ao livro")
    for old, (new, old_pmp, new_pmp) in changes.items():
        fields = [k for k in BOOK_FIELDS if old_pmp.get(k) != new_pmp.get(k)]
        rename = f" (renomeado de '{old}')" if old != new else ""
        print(f"  ~ {new}{rename}: {', '.join(fields) or 'nome'}")
    for name in created:
        print(f"  + {name}")
    print(f"{embedded} cópias embutidas na Pokédex atualizadas")
    if base_diffs:
        print(f"Diferem do Livro de Regras (mantida a versão do livro principal): {', '.join(base_diffs)}")
    if report:
        print(f"{len(report)} avisos:")
        for line in report:
            print(f"  - {line}")


if __name__ == "__main__":
    main()
