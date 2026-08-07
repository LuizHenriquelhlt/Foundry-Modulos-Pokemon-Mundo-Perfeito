#!/usr/bin/env python3
"""
Fase 1 (parte 1) — "Habilidades gerais de Treinador" e "Especializações"
(Livro de Regras, páginas 20-22). Ambas as listas têm nomes conhecidos e fixos
(usados aqui como âncoras) em vez de um rótulo de campo repetido como nos Moves,
então o parser usa uma lista de nomes esperados em vez de regex de rótulo.

Uso: python scripts/parse-trainer-especializacoes.py "<pasta com os PDFs>"
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from pdf_text import extract_range, strip_noise  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")

# (nome esperado no texto — tolera espaço extra por quirk de extração —, nome correto, nível)
HABILIDADES_GERAIS = [
    (r"Rastreador\s*Pok[eé]mon", "Rastreador Pokémon", 10),
    (r"Aura\s*de\s*Treinador", "Aura de Treinador", 11),
    (r"Determina[çc][ãa]o\s*do\s*Treinador", "Determinação do Treinador", 13),
    (r"Foco\s*de\s*Treinador", "Foco de Treinador", 14),
    (r"Aten[çc][ãa]o\s*Agu[çc]ada", "Atenção Aguçada", 17),
    (r"Treinador\s*Mestre", "Treinador Mestre", 20)
]

# (nome esperado, nome correto, tipo Pokémon associado)
ESPECIALIZACOES = [
    (r"Guardi[ãa]o\s*dos\s*P[áa]ssaros", "Guardião dos Pássaros", "flying"),
    (r"Man[íi]aco\s*por\s*Insetos", "Maníaco por Insetos", "bug"),
    (r"Campista", "Campista", "ground"),
    (r"Domador\s*de\s*Drag[õo]es", "Domador de Dragões", "dragon"),
    (r"Engenheiro", "Engenheiro", "electric"),
    (r"Piroman[íi]aco", "Piromaníaco", "fire"),
    (r"Jardineiro", "Jardineiro", "grass"),
    (r"Artista\s*Marcial", "Artista Marcial", "fighting"),
    (r"Alpinista", "Alpinista", "rock"),
    (r"M[íi]stico", "Místico", "ghost"),
    (r"Metal[úu]rgico", "Metalúrgico", "steel"),
    (r"Psíquico", "Psíquico", "psychic"),
    (r"N\s*adador", "Nadador", "water"),
    (r"Encantador", "Encantador", "fairy"),
    (r"Sombrio", "Sombrio", "dark"),
    (r"Alquimista", "Alquimista", "poison"),
    (r"Jo\s*gador\s*de\s*Equipe", "Jogador de Equipe", "normal"),
    (r"Es\s*quiador", "Esquiador", "ice")
]


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def find_anchors(lines, entries):
    anchors = []
    for i, line in enumerate(lines):
        for pattern, correct_name, meta in entries:
            if re.fullmatch(pattern, line.strip()):
                anchors.append({"idx": i, "name": correct_name, "meta": meta})
                break
    return anchors


def slice_blocks(lines, anchors, end_idx):
    blocks = []
    for i, a in enumerate(anchors):
        start = a["idx"] + 1
        stop = anchors[i + 1]["idx"] if i + 1 < len(anchors) else end_idx
        text = " ".join(lines[start:stop]).strip()
        blocks.append((a["name"], a["meta"], text))
    return blocks


def base_item(doc_id, name, item_type, system, img="icons/svg/upgrade.svg"):
    return {
        "_id": doc_id, "name": name, "type": item_type, "img": img, "system": system,
        "effects": [], "folder": None, "flags": {},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": 0, "ownership": {"default": 0}
    }


def make_id(seed, used_ids):
    import hashlib
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    doc_id = "".join(out)
    while doc_id in used_ids:
        doc_id = doc_id[1:] + doc_id[0]
    used_ids.add(doc_id)
    return doc_id


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", strip_accents_lower(name)).strip("-")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-trainer-especializacoes.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")

    raw = extract_range(pdf_path, 20, 22, n_columns=2)
    cleaned = strip_noise(raw)
    lines = [l for l in cleaned.split("\n") if l.strip()]

    habilidades_anchors = find_anchors(lines, HABILIDADES_GERAIS)
    especializacoes_anchors = find_anchors(lines, ESPECIALIZACOES)

    if len(habilidades_anchors) != len(HABILIDADES_GERAIS):
        print(f"AVISO: esperava {len(HABILIDADES_GERAIS)} Habilidades Gerais, achou {len(habilidades_anchors)}")
    if len(especializacoes_anchors) != len(ESPECIALIZACOES):
        print(f"AVISO: esperava {len(ESPECIALIZACOES)} Especializações, achou {len(especializacoes_anchors)}")
        found_names = {a["name"] for a in especializacoes_anchors}
        for _, correct_name, _ in ESPECIALIZACOES:
            if correct_name not in found_names:
                print(f"  faltando: {correct_name}")

    habilidades_blocks = slice_blocks(lines, habilidades_anchors, especializacoes_anchors[0]["idx"]
                                       if especializacoes_anchors else len(lines))
    especializacoes_blocks = slice_blocks(lines, especializacoes_anchors, len(lines))

    os.makedirs(OUT_DIR, exist_ok=True)
    used_ids = set()
    written = 0

    for name, level, text in habilidades_blocks:
        system = {
            "description": {"value": f"<p>{text}</p>"},
            "type": {"value": "feat", "subtype": ""},
            "requirements": f"Nível {level}"
        }
        doc = base_item(make_id(f"habilidade-geral-{name}", used_ids), name, "feat", system)
        doc["flags"] = {"pokemon-mundo-perfeito": {"category": "habilidade-geral-treinador", "level": level}}
        with open(os.path.join(OUT_DIR, f"habilidade-geral-{slugify(name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1

    for name, pmp_type, text in especializacoes_blocks:
        system = {
            "description": {"value": f"<p>{text}</p>"},
            "type": {"value": "feat", "subtype": ""},
            "requirements": "Nível 1 (repetível nos níveis 7 e 18)"
        }
        doc = base_item(make_id(f"especializacao-{name}", used_ids), name, "feat", system)
        doc["flags"] = {"pokemon-mundo-perfeito": {"category": "especializacao", "pokemonType": pmp_type}}
        with open(os.path.join(OUT_DIR, f"especializacao-{slugify(name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1

    print(f"{written} Items escritos em {OUT_DIR} "
          f"({len(habilidades_blocks)} Habilidades Gerais + {len(especializacoes_blocks)} Especializações)")


if __name__ == "__main__":
    main()
