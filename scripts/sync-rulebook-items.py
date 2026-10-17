#!/usr/bin/env python3
"""
Sincroniza os itens do capítulo "Itens" do Livro de Regras com o compêndio (Recursos de
Treinador e Pokébolas), relendo as tabelas com o leitor de scripts/parse-gen89-items.py.

O catálogo tinha sido extraído com pdfplumber, que em tabelas de célula centralizada juntava
linhas de itens vizinhos: o Balm Mushroom levou o texto de Nugget/Big Nugget/Pearl/Big
Pearl/Pearl String (que sumiram do catálogo), o Soul Dew levou o de Arceus Plate e Genesect
Drives, a Water Gem o das outras 16 Gems, o Everstone e o Lucky Punch os de Genesect Drives
e Memory Disc; preços entraram no meio de frases ("...durante a Não batalha... vendido") e
textos ficaram cortados ("Fornece +1 em", Berries sem a lista de Naturezas).

O que faz:
- texto/preço do compêndio diferente do livro → passa a ser o do livro (KEEP_MODULE_TEXT
  guarda as exceções em que o módulo está certo e o livro tem erro de digitação);
- item que aparece em duas tabelas (King's Rock: Itens Evolutivos e Itens Seguráveis) fica
  com os dois efeitos;
- Gems: as 18 dividem um efeito e um preço numa linha só do livro — cada uma recebe os dois;
- nome cortado no compêndio ("Camisa de Cores", "Extender") é corrigido mantendo o _id;
- item do livro que não existe no compêndio é criado no mesmo formato do catálogo;
- "(veja abaixo)" (Pokédex, Rotom Dex, Pedra-Chave) recebe o texto da seção do livro, e
  "(veja a página seguinte)" das varas de pesca aponta o Guia de Pesca do compêndio de Regras.
Idempotente. Uso: python scripts/sync-rulebook-items.py "<pasta com os PDFs>"
"""
import glob
import importlib.util
import json
import os
import re
import sys
import urllib.request

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRAINER = os.path.join(ROOT, "packs", "_source", "trainer-features")
POKEBALLS = os.path.join(ROOT, "packs", "_source", "pokeballs")
MODULE_ID = "pokemon-mundo-perfeito"
BOOK = "Livro de Regras - Pokémon Mundo Perfeito.pdf"
SPRITE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{slug}.png"


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader = load("parse-gen89-items")
fiu = load("fix-item-usability")
folders = load("add-trainer-folders")
abilities = load("sync-gen89-abilities")  # page_lines/EntryBuilder pras seções de texto corrido

# nome no compêndio -> nome no livro (o parser antigo cortou o nome)
MODULE_RENAMES = {"Camisa de Cores": "Camisa de Cores Vibrantes", "Extender": "Terrain Extender"}
# nome que o livro quebra em duas linhas de tabela, cada uma lida como item
BOOK_NAME_JOIN = {"Kit de Primeiros": "Socorros"}
# o módulo está certo e o livro tem erro de digitação ("profciiência")
KEEP_MODULE_TEXT = {"Iron Ball"}
# "(veja abaixo)": seção do livro com o texto que o item cita
SECTION_FOR = {"Pokédex": "Pokédex", "Rotom Dex": "Rotom Dex", "Pedra-Chave": "Pedra-Chave"}
FISHING_REF = ("(veja a página seguinte)", "(veja o \"Guia de Pesca\" no compêndio de Regras)")


def norm(text):
    return reader.norm(text)


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def strip_price_tail(lines):
    """Célula de preço ("Não" / "Vendida", "N/A") vazada pro fim do texto do efeito."""
    lines = list(lines)
    while lines:
        last = lines[-1].strip()
        if not last or re.fullmatch(r"(?:N/A|Não|[Vv]endid[oa]s?|Não\s+[Vv]endid[oa]s?)", last):
            lines.pop()
            continue
        cleaned = re.sub(r"\s+(?:N/A|Não(?:\s+[Vv]endid[oa]s?)?|[Vv]endid[oa]s?)$", "", last)
        if cleaned == last:
            break
        lines[-1] = cleaned
    return lines


def book_items(doc):
    first, last = reader.chapter_pages(doc, "Itens")
    out, cols_prev, section = [], None, ""
    for pno in range(first, last + 1):
        page = doc[pno - 1]
        heads = reader.headings(page)
        for table in page.find_tables().tables:
            parsed = reader.read_table(table, cols_prev)
            if parsed is None:
                continue
            items, cols_prev = parsed
            above = [text for y, text in heads if y < table.bbox[1]]
            # tabela que continua da página anterior não tem título acima: herda o da anterior
            section = above[-1] if above else section
            for item in items:
                out.append({"name": item["name"].strip(), "lines": strip_price_tail(item["lines"]),
                            "price": item["price"], "section": section, "page": pno})
    # nome partido em duas linhas de tabela
    merged = []
    for item in out:
        if merged and BOOK_NAME_JOIN.get(merged[-1]["name"]) == item["name"]:
            merged[-1]["name"] += " " + item["name"]
            merged[-1]["lines"] += item["lines"]
            continue
        merged.append(item)
    # Gems: uma linha com o efeito e o preço, seguida só dos nomes das outras
    for i, item in enumerate(merged):
        if not any(l.strip() for l in item["lines"]) and item["price"] is None and i > 0:
            head = next((m for m in reversed(merged[:i]) if any(l.strip() for l in m["lines"])), None)
            if head and head["section"] == item["section"]:
                item["lines"], item["price"] = list(head["lines"]), head["price"]
    return merged


def section_html(doc, page_no, title):
    """Texto corrido de uma seção do livro (título em "Digitalt"), em parágrafos."""
    lines = sorted(abilities.page_lines(doc[page_no - 1]), key=lambda l: (l[1], l[0]))
    start = next((i for i, l in enumerate(lines) if l[2] == title and any(f.startswith("Digitalt") for f in l[3])), None)
    if start is None:
        return ""
    body = []
    for x, y, text, fonts, size in lines[start + 1:]:
        if any(f.startswith("Digitalt") for f in fonts) or re.fullmatch(r"\d{1,3}", text):
            break
        body.append((x, y, text))
    if not body:
        return ""
    # margem = alinhamento das linhas da própria seção (a 1ª linha do parágrafo vem recuada)
    builder = abilities.EntryBuilder(min(x for x, y, t in body))
    for x, y, text in body:
        builder.line(x, y, text)
    return builder.finish()


def module_items():
    out = {}
    for f in glob.glob(os.path.join(TRAINER, "item-*.json")) + glob.glob(os.path.join(POKEBALLS, "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if doc["_key"].startswith("!folders"):
            continue
        if doc.get("flags", {}).get(MODULE_ID, {}).get("source") in ("Gen8", "Gen9"):
            continue
        out[norm(MODULE_RENAMES.get(doc["name"], doc["name"]))] = (f, doc)
    return out


def url_ok(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "pokemon-mundo-perfeito-foundry/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/sync-rulebook-items.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    doc = pymupdf.open(os.path.join(sys.argv[1], BOOK))
    items = book_items(doc)
    print(f"{len(items)} linhas de item no capítulo Itens do Livro de Regras")

    # o mesmo item em duas tabelas (evolutivo e segurável): junta os dois efeitos
    by_name = {}
    for item in items:
        key = norm(item["name"])
        text = " ".join(l for l in item["lines"] if l.strip())
        if key in by_name and text and norm(text) not in norm(by_name[key]["text_all"]):
            first = by_name[key]
            first["html"] = (f"<p><strong>{first['section']}:</strong></p>{first['html']}"
                             f"<p><strong>{item['section']}:</strong></p>{reader.paragraphs_html(item['lines'])}")
            first["text_all"] += " " + text
            continue
        by_name.setdefault(key, {**item, "html": reader.paragraphs_html(item["lines"]), "text_all": text})

    # seções citadas por "(veja abaixo)"
    for name, title in SECTION_FOR.items():
        entry = by_name.get(norm(name))
        if not entry:
            continue
        page = next(p for lv, t, p in doc.get_toc() if t.strip() == title and p >= entry["page"])
        extra = section_html(doc, page, title)
        if extra:
            entry["html"] = entry["html"].replace(" (veja abaixo)", "") + extra
    for entry in by_name.values():
        entry["html"] = entry["html"].replace(*FISHING_REF)

    module = module_items()
    ids = {slug: fiu.make_id(f"folder-trainer-{slug}") for slug, _, _, _ in folders.FOLDERS}
    updated, renamed, priced, created = [], [], [], []
    for key, entry in by_name.items():
        name = entry["name"]
        if not name or not entry["html"]:
            continue
        price = reader.price_value(entry["price"])
        hit = module.get(key)
        if hit:
            path, mdoc = hit
            changed = False
            if mdoc["name"] != name and MODULE_RENAMES.get(mdoc["name"]) == name:
                renamed.append(f"{mdoc['name']} -> {name}")
                mdoc["name"] = name
                changed = True
            current = mdoc["system"]["description"]["value"]
            if name not in KEEP_MODULE_TEXT and current != entry["html"]:
                mdoc["system"]["description"]["value"] = entry["html"]
                updated.append(name)
                changed = True
            if entry["price"] and price != mdoc["system"].get("price", {}).get("value"):
                priced.append(f"{name}: {mdoc['system'].get('price', {}).get('value')} -> {price}")
                mdoc["system"].setdefault("price", {})["value"] = price
                mdoc.setdefault("flags", {}).setdefault(MODULE_ID, {})["priceRaw"] = entry["price"]
                changed = True
            if changed:
                fiu.save(path, mdoc)
            continue
        # item do livro que não existe no compêndio
        slug = reader.slugify(name)
        item_type, system = fiu.catalog_item(name, entry["html"], price, fiu.is_consumable(name))
        sprite = SPRITE.format(slug=slug)
        doc_id = fiu.make_id(f"item-{name}")
        new = {
            "_key": f"!items!{doc_id}", "_id": doc_id, "name": name, "type": item_type,
            "img": sprite if url_ok(sprite) else "icons/svg/item-bag.svg", "system": system,
            "effects": [], "folder": ids[folders.item_subfolder(name)],
            "flags": {MODULE_ID: {"category": "item-treinador", "priceRaw": entry["price"] or "",
                                  "section": entry["section"]}},
            "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                       "compendiumSource": None, "duplicateSource": None},
            "sort": 0, "ownership": {"default": 0}
        }
        fiu.save(os.path.join(TRAINER, f"item-{slug}.json"), new)
        created.append(name)

    print(f"Texto atualizado: {len(updated)} {updated}")
    print(f"Renomeados: {renamed}")
    print(f"Preço corrigido: {priced}")
    print(f"Criados: {len(created)} {created}")
    missing = [m["name"] for k, (f, m) in module.items() if k not in by_name]
    if missing:
        print(f"No compêndio e não no capítulo de Itens do livro (mantidos): {missing}")


if __name__ == "__main__":
    main()
