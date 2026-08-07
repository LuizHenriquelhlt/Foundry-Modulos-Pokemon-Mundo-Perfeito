#!/usr/bin/env python3
"""
Fase 1 (parte 2) — "Região de Origem" (pág. 23-26) e "Origem de Jornada" (pág. 27-28)
do Livro de Regras. Mesma técnica de âncoras por nome conhecido da Fase 1 parte 1.

Uso: python scripts/parse-trainer-regioes-origens.py "<pasta com os PDFs>"
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

REGIOES = ["Alola", "Hoenn", "Johto", "Kalos", "Kanto", "Sinnoh", "Unova", "Galar"]

# (nome esperado no texto, nome correto, subtítulo)
ORIGENS = [
    (r"Atleta\s*\(O\s*Forte\)", "Atleta", "O Forte"),
    (r"[Cc]onhecedor\s*\(O\s*Tranquilo\)", "Conhecedor", "O Tranquilo"),
    (r"Nobre\s*\(O\s*Esnobe\)", "Nobre", "O Esnobe"),
    (r"Encrenqueiro\s*\(O\s*Afiado\)", "Encrenqueiro", "O Afiado"),
    (r"Amigo\s*dos\s*Pok[eé]mon\s*\(O\s*Selvagem\)", "Amigo dos Pokémon", "O Selvagem"),
    (r"Rival\s*\(O\s*[Dd]esafiador\)", "Rival", "O Desafiador"),
    (r"Estudioso\s*\(O\s*C[eé]rebro\)", "Estudioso", "O Cérebro")
]


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


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


def parse_regioes(lines, used_ids):
    anchors = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in REGIOES or strip_accents_lower(stripped) in [strip_accents_lower(r) for r in REGIOES]:
            # evita casar a palavra dentro de uma frase (linha deve ser só o nome da região)
            anchors.append({"idx": i, "name": stripped})

    if len(anchors) != len(REGIOES):
        print(f"AVISO Região de Origem: esperava {len(REGIOES)}, achou {len(anchors)}: "
              f"{[a['name'] for a in anchors]}")

    written = 0
    for i, a in enumerate(anchors):
        start = a["idx"] + 1
        stop = anchors[i + 1]["idx"] if i + 1 < len(anchors) else len(lines)
        text = " ".join(lines[start:stop]).strip()
        name = a["name"][0].upper() + a["name"][1:].lower() if a["name"].isupper() else a["name"]
        if strip_accents_lower(name) == "sinnoh":
            name = "Sinnoh"
        system = {
            "description": {"value": f"<p>{text}</p>"},
            "type": {"value": "feat", "subtype": ""},
            "requirements": "Escolhida na criação do Treinador"
        }
        doc = base_item(make_id(f"regiao-{name}", used_ids), name, "feat", system)
        doc["flags"] = {"pokemon-mundo-perfeito": {"category": "regiao-de-origem"}}
        with open(os.path.join(OUT_DIR, f"regiao-{slugify(name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1
    return written


def parse_origens(lines, used_ids):
    anchors = []
    for i, line in enumerate(lines):
        for pattern, name, subtitle in ORIGENS:
            if re.fullmatch(pattern, line.strip()):
                anchors.append({"idx": i, "name": name, "subtitle": subtitle})
                break

    if len(anchors) != len(ORIGENS):
        found = {a["name"] for a in anchors}
        print(f"AVISO Origem de Jornada: esperava {len(ORIGENS)}, achou {len(anchors)}")
        for _, name, _ in ORIGENS:
            if name not in found:
                print(f"  faltando: {name}")

    written = 0
    for i, a in enumerate(anchors):
        start = a["idx"] + 1
        stop = anchors[i + 1]["idx"] if i + 1 < len(anchors) else len(lines)
        text = " ".join(lines[start:stop]).strip()

        skills_m = re.search(r"Per[íi]cias:\s*([^•]+?)(?:•|$)", text)
        skills = [s.strip() for s in skills_m.group(1).split(",")] if skills_m else []

        system = {
            "description": {"value": f"<p>{text}</p>"},
        }
        doc = base_item(
            make_id(f"origem-{a['name']}", used_ids), f"{a['name']} ({a['subtitle']})", "background", system
        )
        doc["flags"] = {"pokemon-mundo-perfeito": {"category": "origem-de-jornada", "skills": skills}}
        with open(os.path.join(OUT_DIR, f"origem-{slugify(a['name'])}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1
    return written


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-trainer-regioes-origens.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")
    os.makedirs(OUT_DIR, exist_ok=True)
    used_ids = set()

    raw_regioes = extract_range(pdf_path, 23, 26, n_columns=2)
    lines_regioes = [l for l in strip_noise(raw_regioes).split("\n") if l.strip()]
    n_regioes = parse_regioes(lines_regioes, used_ids)

    raw_origens = extract_range(pdf_path, 27, 28, n_columns=2)
    lines_origens = [l for l in strip_noise(raw_origens).split("\n") if l.strip()]
    n_origens = parse_origens(lines_origens, used_ids)

    print(f"{n_regioes} Regiões de Origem + {n_origens} Origens de Jornada escritas em {OUT_DIR}")


if __name__ == "__main__":
    main()
