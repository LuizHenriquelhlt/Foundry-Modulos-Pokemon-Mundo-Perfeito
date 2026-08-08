#!/usr/bin/env python3
"""
Ajustes de tamanho de token na Pokédex (pedido do usuário):

1. Lendários e Míticos de tamanho Médio sobem uma categoria (Médio -> Grande, token 2x2).
2. Formas finais de tamanho Médio com mais de 1,60 m de altura ganham token 2x2
   (a categoria de regra continua Médio — só a presença em cena cresce).
3. Proporção nas linhas evolutivas: reconstrói as famílias pelo texto de Evolução
   ("X pode evoluir para Y") e garante que nenhuma evolução tenha token MENOR que uma
   pré-evolução — o token nunca encolhe ao evoluir.

Roda DEPOIS de add-images.py / add-form-images.py / convert-to-dnd5e-native.py
(qualquer um deles reseta os campos que este script ajusta). Idempotente.

Uso: python scripts/adjust-token-sizes.py
"""
import glob
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")

# Lendários e Míticos por número da Dex (Gen 1-9; Ultra Beasts e Paradoxos não contam)
LEGENDARY_MYTHICAL = {
    144, 145, 146, 150, 151,                                  # Kanto
    243, 244, 245, 249, 250, 251,                             # Johto
    377, 378, 379, 380, 381, 382, 383, 384, 385, 386,          # Hoenn
    480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490,     # Sinnoh
    491, 492, 493,
    494, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647,     # Unova
    648, 649,
    716, 717, 718, 719, 720, 721,                              # Kalos
    772, 773, 785, 786, 787, 788, 789, 790, 791, 792, 800,     # Alola
    801, 802, 807, 808, 809,
    888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898,     # Galar/Hisui
    905,
    1001, 1002, 1003, 1004, 1007, 1008, 1014, 1015, 1016,      # Paldea
    1017, 1024, 1025
}

EVOLVE_RE = re.compile(r"evoluir para (?:o |a )?([A-ZÀ-Ý][\w'’.-]*(?:[ -][A-ZÀ-Ý][\w'’.-]*)*)")


def normalize(name):
    s = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def main():
    docs = {}
    for f in glob.glob(os.path.join(POKEDEX, "*.json")):
        if os.path.basename(f).startswith("folder-"):
            continue
        docs[f] = json.load(open(f, encoding="utf-8"))

    by_norm = {normalize(d["name"]): f for f, d in docs.items()}

    n_leg = n_final = n_prop = 0
    changed = set()

    # Regra 1: lendários/míticos médios sobem uma categoria
    for f, d in docs.items():
        sp = d["flags"]["pokemon-mundo-perfeito"]["species"]
        if sp["dexNumber"] in LEGENDARY_MYTHICAL and d["system"]["traits"]["size"] == "med":
            d["system"]["traits"]["size"] = "lg"
            d["prototypeToken"]["width"] = 2
            d["prototypeToken"]["height"] = 2
            n_leg += 1
            changed.add(f)

    # Regra 2: forma final média com mais de 1,60 m -> token 2x2
    for f, d in docs.items():
        sp = d["flags"]["pokemon-mundo-perfeito"]["species"]
        stage = sp.get("evolutionStage", {})
        is_final = stage.get("current", 1) == stage.get("max", 1)
        if is_final and d["system"]["traits"]["size"] == "med" \
                and sp.get("heightMeters", 0) > 1.60 \
                and d["prototypeToken"].get("width", 1) < 2:
            d["prototypeToken"]["width"] = 2
            d["prototypeToken"]["height"] = 2
            n_final += 1
            changed.add(f)

    # Regra 3: famílias evolutivas — o token nunca encolhe ao evoluir
    uf = UnionFind()
    for f, d in docs.items():
        sp = d["flags"]["pokemon-mundo-perfeito"]["species"]
        me = normalize(d["name"])
        for m in EVOLVE_RE.finditer(sp.get("evolution", "")):
            target = by_norm.get(normalize(m.group(1)))
            if target:
                uf.union(f, target)

    families = {}
    for f in docs:
        families.setdefault(uf.find(f), []).append(f)

    examples = []
    for members in families.values():
        if len(members) < 2:
            continue
        # dims mínimos por estágio: cada estágio herda o maior token dos estágios anteriores
        members_sorted = sorted(
            members,
            key=lambda f: docs[f]["flags"]["pokemon-mundo-perfeito"]["species"]
                          .get("evolutionStage", {}).get("current", 1)
        )
        running_max = 0
        for f in members_sorted:
            d = docs[f]
            w = d["prototypeToken"].get("width", 1)
            if w < running_max:
                d["prototypeToken"]["width"] = running_max
                d["prototypeToken"]["height"] = running_max
                n_prop += 1
                changed.add(f)
                if len(examples) < 8:
                    examples.append(f"{d['name']}: {w} -> {running_max}")
            running_max = max(running_max, d["prototypeToken"].get("width", 1))

    for f in changed:
        save(f, docs[f])

    print(f"Regra 1 (lendário/mítico médio -> Grande 2x2): {n_leg}")
    print(f"Regra 2 (forma final média > 1,60 m -> token 2x2): {n_final}")
    print(f"Regra 3 (proporção na linha evolutiva): {n_prop}")
    for e in examples:
        print(f"  - {e}")
    print(f"{len(changed)} documentos alterados")


if __name__ == "__main__":
    main()
