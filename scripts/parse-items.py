#!/usr/bin/env python3
"""
Fase 1 (parte 4) — catálogo de Itens (Livro de Regras, páginas 76-90): Pacotes,
Itens para Treinador, Itens-X, Itens Evolutivos, Itens Seguráveis, Itens-Chave.

Diferente das outras seções (texto corrido em 2 colunas), esta é uma grade de
tabela real (Nº | Item | Efeito/Descrição | Preço), então usa pdfplumber
extract_tables() em vez da técnica column-aware de texto — é o método correto
para tabelas com células que quebram em várias linhas.

Uso: python scripts/parse-items.py "<pasta com os PDFs>"
"""
import json
import os
import re
import sys
import unicodedata

import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "pokeballs")
ITEMS_OUT_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")

# Página 90 é a Lista de Preços de TM (tabela de 4 colunas repetidas Nº/TM/Preço), não
# itens genéricos — tratada à parte por scripts/parse-tm-prices.py.
FIRST_PAGE, LAST_PAGE = 76, 89

# (índice de página 1-based, categoria) — usado para separar Pokébolas de Itens-X etc.
# determinado lendo os cabeçalhos de seção reais do livro.
CATEGORY_BY_PAGE = {
    76: "pacote", 77: "pacote-ou-treinador",
    78: "treinador", 79: "pokebola-ou-itemx", 80: "itemx-ou-evolutivo",
    81: "evolutivo", 82: "evolutivo", 83: "seguravel", 84: "seguravel",
    85: "seguravel", 86: "seguravel-ou-chave", 87: "chave", 88: "chave",
    89: "chave", 90: "chave"
}

POKEBALL_NAMES = {
    "Pokébola", "Great Ball", "Ultra Ball", "Level Ball", "Net Ball", "Nest Ball",
    "Repeat Ball", "Luxury Ball", "Dive Ball", "Dusk Ball", "Moon Ball", "Heal Ball",
    "Timer Ball", "Premier Ball", "Quick Ball", "Lure Ball", "Love Ball", "Heavy Ball",
    "Beast Ball", "Master Ball"
}


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def is_price(cell):
    return bool(cell) and ("₽" in cell or "endida" in cell)


def normalize_price(cell):
    return re.sub(r"\s+", " ", cell).strip()


def extract_page_items(page):
    """Retorna lista de (nome, descrição, preço) para todas as tabelas da página."""
    items = []
    for table in page.extract_tables():
        current = None  # [nome, [linhas_desc], preco]
        for row in table:
            cells = [c.strip() if isinstance(c, str) else c for c in row]
            non_empty = [c for c in cells if c]
            if not non_empty:
                continue
            if len(non_empty) >= 2 and strip_accents_lower(non_empty[0]) in ("item", "no", "nº"):
                continue  # linha de cabeçalho

            price = None
            rest = []
            for c in non_empty:
                if is_price(c):
                    price = normalize_price(c)
                else:
                    rest.append(c)

            # remove número de índice solto (célula curta só com dígitos)
            rest = [c for c in rest if not re.fullmatch(r"\d{1,3}", c)]

            if not rest and price is None:
                continue

            if current is not None and not rest and price:
                # linha só com o preço, fecha o item atual
                current[2] = price
                items.append(tuple(current))
                current = None
                continue

            if len(rest) >= 2 or (current is None and rest):
                # nova entrada de item: primeira célula = nome, resto = início da descrição
                if current is not None:
                    items.append(tuple(current))
                name = rest[0]
                desc = " ".join(rest[1:])
                current = [name, [desc] if desc else [], price]
                if price:
                    items.append(tuple(current))
                    current = None
            elif len(rest) == 1 and current is not None:
                current[1].append(rest[0])
                if price:
                    current[2] = price
                    items.append(tuple(current))
                    current = None

        if current is not None:
            items.append(tuple(current))

    return [(name, " ".join(desc), price) for name, desc, price in items]


def base_item(doc_id, name, item_type, system, img="icons/svg/item-bag.svg"):
    return {
        "_key": f"!items!{doc_id}",
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
    slug = re.sub(r"[^a-z0-9]+", "-", strip_accents_lower(name)).strip("-")
    return slug[:60].rstrip("-")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-items.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(ITEMS_OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.startswith("pokebola-") and f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))
    for f in os.listdir(ITEMS_OUT_DIR):
        if f.startswith("item-") and f.endswith(".json"):
            os.remove(os.path.join(ITEMS_OUT_DIR, f))

    used_ids = set()
    all_items = []
    seen_names = set()

    skipped_bad_name = 0
    with pdfplumber.open(pdf_path) as pdf:
        for pi in range(FIRST_PAGE - 1, LAST_PAGE):
            page_items = extract_page_items(pdf.pages[pi])
            for name, desc, price in page_items:
                if not name or name in seen_names:
                    continue
                # heurística de sanidade: nomes reais de item nesta tabela começam com
                # maiúscula e são curtos. Um "nome" longo e/ou iniciado em minúscula é sinal
                # de que o parser de grade de tabela associou um fragmento de descrição
                # (linha de continuação de célula) como se fosse o início de um novo item —
                # mais seguro descartar essa entrada do que gerar dado errado.
                if len(name) > 45 or not name[0].isupper():
                    skipped_bad_name += 1
                    continue
                seen_names.add(name)
                all_items.append((name, desc, price))
    if skipped_bad_name:
        print(f"{skipped_bad_name} linhas descartadas por falharem a checagem de nome "
              f"(provável fragmento de descrição mal associado pelo parser de tabela)")

    n_pokeballs = 0
    n_items = 0
    n_skipped_empty = 0
    used_slugs = set()
    for name, desc, price in all_items:
        if not desc.strip():
            # mesmo sintoma do filtro de nome acima: um fragmento de descrição foi
            # separado como se fosse um item próprio, deixando este "item" sem descrição.
            n_skipped_empty += 1
            continue
        is_pokeball = name in POKEBALL_NAMES
        system = {
            "description": {"value": f"<p>{desc}</p>"},
            "price": {"value": price or "", "denomination": "P"},
        }
        item_type = "consumable" if is_pokeball else "loot"
        doc = base_item(make_id(f"item-{name}", used_ids), name, item_type, system)
        doc["flags"] = {
            "pokemon-mundo-perfeito": {
                "category": "pokebola" if is_pokeball else "item-treinador",
                "priceRaw": price or ""
            }
        }
        target_dir = OUT_DIR if is_pokeball else ITEMS_OUT_DIR
        prefix = "pokebola" if is_pokeball else "item"
        slug = slugify(name)
        while slug in used_slugs:
            slug = f"{slug}-x"
        used_slugs.add(slug)
        with open(os.path.join(target_dir, f"{prefix}-{slug}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        if is_pokeball:
            n_pokeballs += 1
        else:
            n_items += 1

    print(f"{n_pokeballs} Pokébolas em {OUT_DIR}")
    print(f"{n_items} outros Itens em {ITEMS_OUT_DIR}")
    print(f"{n_skipped_empty} itens descartados por descrição vazia (mesmo motivo do filtro de nome)")
    print(f"Total: {len(all_items)} itens únicos processados.")


if __name__ == "__main__":
    main()
