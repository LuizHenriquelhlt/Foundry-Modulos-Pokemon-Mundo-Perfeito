#!/usr/bin/env python3
"""
Fase 1 (parte 3) — "Classes de Treinador" (Livro de Regras, páginas 29-32).
Cada classe tem 4 recursos em níveis fixos (2, 5, 9, 15), cada um com seu próprio
nome como linha-título. Mesma técnica de âncoras por nome conhecido, agrupando
cada 4 âncoras consecutivas em uma classe.

Uso: python scripts/parse-trainer-classes.py "<pasta com os PDFs>"
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

# Cada classe: (nome da classe, [nomes dos 4 recursos em ordem: nível 2, 5, 9, 15])
CLASSES = [
    ("Treinador Ás", ["Treinador Ás", "Mestre de Batalha", "Ritmo de Combate", "Troca Rápida"]),
    ("Versátil", ["Versátil", "Apoiador", "Muitas Faces", "Troca de Habilidade"]),
    ("Mentor Pokémon", ["Mentor Pokémon", "Pokéchef", "Tutor capacitado", "Tutor Mestre"]),
    ("Enfermeiro", ["Enfermeiro", "Coração Puro", "Espírito de Cura", "Alegria"]),
    ("Pesquisador", ["Pesquisador", "Analista", "Especialista em Aprendizado", "Preparação Estratégica"]),
    ("Colecionador Pokémon",
     ["Colecionador Pokémon", "Tenho que Pegar Todos", "Especialista em Captura", "Ataques Disciplinados"]),
    ("Comandante", ["Comandante", "Líder Inspirador", "Mostre-Me o Que Você Tem", "Somos Uma Equipe"]),
    ("Patrulheiro", ["Patrulheiro", "Conexão Profunda", "Ligação Forte", "Melhores Amigos"]),
    ("Capanga", ["Capanga", "Encrenca em Dobro", "Renda-se Agora", "Prepare-se para Lutar"]),
    ("Tático", ["Tático", "Golpe Direcionado", "Aumente Suas Defesas", "Não Dessa Vez"]),
    ("Guru", ["Guru", "Mente", "Corpo", "Espírito"]),
    ("Criador de Pokémon", ["Criador de Pokémon", "Cuidado e Carinho", "Boa Genética", "Mestre dos Traços"])
]

LEVELS = [2, 5, 9, 15]


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


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-trainer-classes.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")

    raw = extract_range(pdf_path, 29, 32, n_columns=2)
    lines = [l for l in strip_noise(raw).split("\n") if l.strip()]

    flat_names = [name for _, features in CLASSES for name in features]
    anchors = []
    search_from = 0
    for expected in flat_names:
        found_idx = None
        for i in range(search_from, len(lines)):
            if lines[i].strip() == expected:
                found_idx = i
                break
        if found_idx is None:
            print(f"AVISO: recurso '{expected}' não encontrado a partir da linha {search_from}")
            anchors.append(None)
            continue
        anchors.append(found_idx)
        search_from = found_idx + 1

    os.makedirs(OUT_DIR, exist_ok=True)
    used_ids = set()
    written = 0
    anchor_i = 0

    for class_name, feature_names in CLASSES:
        parts = []
        for level, feature_name in zip(LEVELS, feature_names):
            start_idx = anchors[anchor_i]
            end_idx = None
            for j in range(anchor_i + 1, len(anchors)):
                if anchors[j] is not None:
                    end_idx = anchors[j]
                    break
            end_idx = end_idx if end_idx is not None else len(lines)
            anchor_i += 1
            if start_idx is None:
                continue
            text = " ".join(lines[start_idx + 1:end_idx]).strip()
            parts.append(f"<h3>Nível {level} — {feature_name}</h3><p>{text}</p>")

        system = {
            "description": {"value": "".join(parts)},
            "type": {"value": "class", "subtype": ""},
            "requirements": "Escolhida no nível 2 (Caminho de Treinador)"
        }
        doc = base_item(make_id(f"classe-{class_name}", used_ids), class_name, "feat", system)
        doc["flags"] = {
            "pokemon-mundo-perfeito": {"category": "classe-de-treinador",
                                        "features": dict(zip([str(l) for l in LEVELS], feature_names))}
        }
        with open(os.path.join(OUT_DIR, f"classe-{slugify(class_name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1

    print(f"{written} Classes de Treinador escritas em {OUT_DIR}")


if __name__ == "__main__":
    main()
