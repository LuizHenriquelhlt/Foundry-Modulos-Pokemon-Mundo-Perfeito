#!/usr/bin/env python3
"""
Fase 5 (parte 3) — Itens dos suplementos de Geração 8 (Galar) e Geração 9 (Paldea): os
capítulos "Itens" dos dois livros (Consumíveis, Itens Evolutivos, Fósseis, Itens
Seguráveis, Itens-Chave, Tesouros, Máscaras da Ogerpon, Tera Shards e Diversos).

Grava os itens no compêndio "Recursos de Treinador" (packs/_source/trainer-features),
no mesmo formato final dos itens do Livro de Regras — o "system" vem de
fix-item-usability.catalog_item(), então consumíveis ganham o botão Usar e o resto vira
acessório equipável, exatamente como no catálogo principal. Pastas: Exp. Candy e afins em
"Doces (Candy)", Tera Shards numa subpasta própria, o resto em "Itens".

Como lê o PDF (PyMuPDF, não pdfplumber):
- as páginas do capítulo vêm do sumário do PDF (do marcador "Itens" até o capítulo
  seguinte), então uma nova versão do suplemento com outra paginação continua funcionando;
- cada tabela é lida com find_tables(); a seção do item é o título em fonte "Digitalt"
  mais próximo acima da tabela;
- dentro da tabela, preço e número se reconhecem pelo conteúdo, e nome × efeito pela
  posição horizontal da célula em relação à coluna "Efeito" do cabeçalho — as linhas que
  quebram (nome em duas linhas, efeito em várias) chegam como linhas de tabela separadas;
- o ícone de cada item é a imagem desenhada na coluna "Item" daquela linha. O PokeAPI não
  tem sprite de quase nenhum item de Gen 8/9, então os ícones são extraídos do próprio
  livro para assets/items/ (PNG com transparência, no máximo 128 px).

Idempotente: apaga antes os itens que ele mesmo gerou (flag "source" Gen8/Gen9) e a pasta
assets/items/. Uso: python scripts/parse-gen89-items.py "<pasta com os PDFs>"
"""
import glob
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import unicodedata

import numpy
import pymupdf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")
ICON_DIR = os.path.join(ROOT, "assets", "items")
ICON_URL = "modules/pokemon-mundo-perfeito/assets/items/{slug}.png"
ICON_MAX = 128

BOOKS = [
    ("Geração 8 - Pokémon Mundo Perfeito.pdf", "Gen8", "Expansão da Oitava Geração (Galar)"),
    ("Geração 9 - Pokémon Mundo Perfeito.pdf", "Gen9", "Expansão da Nona Geração (Paldea)"),
]
HEADING_FONT = "Digitalt"


def load_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fiu = load_script("fix-item-usability.py", "fix_item_usability")
folders = load_script("add-trainer-folders.py", "add_trainer_folders")

# palavra quebrada no meio pela própria diagramação do livro
TEXT_FIXES = {"Terasta lize": "Terastalize"}

# itens que o livro lista sem ícone próprio: usam o ícone de outro item da mesma tabela
ICON_FROM = {
    "Carga de energia extra para Rotom Bike": "Bicicleta Rotom",
    "Modo Aquático para Rotom Bike": "Bicicleta Rotom",
}

# como o item conversa com a automação do módulo
MODULE_NOTES = {
    "Orbe Tera": "<p><em>No módulo:</em> o botão \"✨ Terastalizar\" da ficha do Pokémon é "
                 "liberado pelo item <strong>Fator Terastal</strong> (compêndio Itens) equipado "
                 "no Pokémon — ele representa a Orbe Tera sintonizada àquele Pokémon.</p>",
}


def norm(text):
    text = "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text)


def slugify(name):
    slug = "".join(c for c in unicodedata.normalize("NFKD", name.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:60].rstrip("-")


def chapter_pages(doc, title):
    """(primeira, última) página 1-based do capítulo de nível 1 do sumário com esse título."""
    tops = [(t.strip(), p) for lv, t, p in doc.get_toc() if lv == 1]
    for i, (t, p) in enumerate(tops):
        if t == title:
            last = tops[i + 1][1] - 1 if i + 1 < len(tops) else doc.page_count
            return p, last
    raise SystemExit(f"Capítulo '{title}' não encontrado no sumário de {doc.name}")


def headings(page):
    """[(y0, texto)] dos títulos de seção da página, de cima para baixo."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if spans and all(s["font"].startswith(HEADING_FONT) for s in spans):
                out.append((line["bbox"][1], " ".join(s["text"].strip() for s in spans)))
    return sorted(out)


def header_columns(table):
    """x0 das colunas do cabeçalho: num, name, effect, price (só as que existirem)."""
    cols = {}
    for cell, text in zip(table.rows[0].cells, table.extract()[0]):
        if cell is None or not text:
            continue
        key = norm(text)
        if key in ("item", "erva"):
            cols["name"] = cell[0]
        elif key in ("efeito", "pokemon", "descricao"):
            cols["effect"] = cell[0]
        elif key.startswith("preco"):
            cols["price"] = cell[0]
        elif key in ("n", "no"):  # "Nº" — o NFKD transforma o "º" em "o"
            cols["num"] = cell[0]
    return cols


PRICE_RE = re.compile(r"^(₽|N/A|Não\s+vendido|Não$)", re.IGNORECASE)
NUM_RE = re.compile(r"^(\d{1,3}|—|-)$")


def read_table(table, fallback_cols=None):
    """Itens da tabela: [{name, lines, price, bbox}] na ordem do livro.

    fallback_cols: colunas de uma tabela anterior com o mesmo layout — tabelas que continuam
    na página seguinte não repetem o cabeçalho (Livro de Regras, Berries/Itens Seguráveis).

    Quando o nome do item ocupa várias linhas, o livro centraliza o nome numa linha de tabela
    própria, ABAIXO da linha com o efeito e o preço (Arceus Plate, Genesect Drives): por isso
    toda linha com preço abre um item novo, e uma linha só com nome batiza o item que ainda
    não tem nome."""
    cols = header_columns(table)
    has_header = "name" in cols and "effect" in cols
    if not has_header:
        if not fallback_cols:
            return None  # não é tabela de itens (ex.: a grade de combinação dos fósseis)
        cols = fallback_cols
    effect_x0 = cols["effect"] - 2
    items = []
    rows = table.extract()
    first = 1 if has_header else 0
    for row, row_obj in zip(rows[first:], table.rows[first:]):
        num = price = None
        names, effects = [], []
        for cell, text in zip(row_obj.cells, row):
            if cell is None or text is None:
                continue
            clean = text.strip()
            if not clean:
                continue
            if PRICE_RE.match(clean):
                price = re.sub(r"\s+", " ", clean)
            elif NUM_RE.match(clean) and (cell[0] + cell[2]) / 2 < cols["name"] + 4:
                num = clean
            elif (cell[0] + cell[2]) / 2 < effect_x0:
                names.append(re.sub(r"\s+", " ", clean))
            else:
                effects.extend(clean.split("\n"))
        numbered = "num" in cols  # tabela com coluna "Nº": só o número abre item novo
        is_start = num is not None or (price is not None and (names or not numbered))
        if is_start or not items:
            items.append({"name": " ".join(names), "lines": effects, "price": price,
                          "bbox": list(row_obj.bbox)})
            continue
        item = items[-1]
        if not numbered and names and item["name"] and item["price"] and effects:
            # nome + efeito sem preço depois de um item completo: item novo cujo preço vem numa
            # linha de baixo (a célula de preço também fica centralizada)
            items.append({"name": " ".join(names), "lines": effects, "price": None,
                          "bbox": list(row_obj.bbox)})
            continue
        if names:
            item["name"] = f"{item['name']} {' '.join(names)}".strip()
        # linha de tabela sem texto nenhum = linha em branco dentro da célula (troca de parágrafo)
        item["lines"].extend(effects if effects else [""])
        if price and not item["price"]:
            item["price"] = price
        item["bbox"][3] = max(item["bbox"][3], row_obj.bbox[3])
    return items, cols


def paragraphs_html(lines):
    """Linhas da célula → parágrafos. Rótulos ("Efeito em batalha:") e notas entre parênteses
    em linha própria abrem parágrafo; linha vazia separa parágrafos."""
    paras = [[]]

    def new_para():
        if paras[-1]:
            paras.append([])

    for line in lines:
        s = line.strip()
        if not s:
            new_para()
        elif re.fullmatch(r"[^.:()]{3,40}:", s):
            new_para()
            paras[-1].append(f"<strong>{s}</strong>")
        elif s.startswith("(") and s.endswith(")"):
            new_para()
            paras[-1].append(f"<em>{s}</em>")
            new_para()
        else:
            paras[-1].append(s)
    html = []
    for para in paras:
        if not para:
            continue
        text = para[0]
        for nxt in para[1:]:
            text += nxt if text.endswith("-") else " " + nxt
        for wrong, right in TEXT_FIXES.items():
            text = text.replace(wrong, right)
        text = re.sub(r"\s+", " ", text).strip()
        html.append(f"<p>{text}</p>")
    return "".join(html)


def price_value(raw):
    digits = re.sub(r"[^\d]", "", raw or "")
    return int(digits) if digits else 0


def find_icon(page_images, item, cols, table_x0):
    """xref da imagem desenhada na coluna Item, na faixa vertical das linhas do item."""
    y0, y1 = item["bbox"][1], item["bbox"][3]
    best = None
    for info in page_images:
        bx0, by0, bx1, by1 = info["bbox"]
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        if table_x0 <= cx < cols["effect"] and y0 <= cy <= y1:
            area = (bx1 - bx0) * (by1 - by0)
            if best is None or area > best[0]:
                best = (area, info["xref"])
    return best[1] if best else None


def save_icon(doc, xref, path):
    """Ícone com transparência. Pixmap(doc, xref) devolve um canal alfa todo opaco nestes
    PDFs (a transparência real está na /SMask), então o alfa é descartado e a SMask aplicada
    à mão. As máscaras têm /Matte [0 0 0]: a cor foi gravada pré-multiplicada pelo preto,
    e sem desfazer isso as bordas ficam escurecidas."""
    pix = pymupdf.Pixmap(doc, xref)
    if pix.alpha:
        pix = pymupdf.Pixmap(pix, 0)
    if pix.n >= 4:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    smask = doc.extract_image(xref).get("smask")
    matte = None
    if smask:
        pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, smask))
        found = re.search(r"/Matte\s*\[([^\]]*)\]", doc.xref_object(smask, compressed=True))
        if found:
            matte = numpy.array([float(v) * 255 for v in found.group(1).split()])
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
    if matte is not None and matte.size == 3:
        px = numpy.asarray(img).astype(float)
        alpha = px[..., 3:4] / 255
        rgb = numpy.where(alpha > 0, matte + (px[..., :3] - matte) / numpy.maximum(alpha, 1e-6), 0)
        px[..., :3] = numpy.clip(rgb, 0, 255)
        img = Image.fromarray(px.round().astype(numpy.uint8), "RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    if max(img.size) > ICON_MAX:
        img.thumbnail((ICON_MAX, ICON_MAX), Image.LANCZOS)
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    canvas.save(path, optimize=True)


def folder_ids():
    ids = {slug: fiu.make_id(f"folder-trainer-{slug}") for slug, _, _, _ in folders.FOLDERS}
    return ids


def write_tera_folder(ids):
    """Cria a subpasta Tera Shards no mesmo formato de add-trainer-folders.py."""
    for i, (slug, label, color, parent) in enumerate(folders.FOLDERS):
        if slug != "tera-shards":
            continue
        doc = {
            "_key": f"!folders!{ids[slug]}", "_id": ids[slug], "name": label, "type": "Item",
            "folder": ids[parent] if parent else None, "sorting": "a", "color": color,
            "description": "", "flags": {}, "sort": i * 10000,
            "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                       "compendiumSource": None, "duplicateSource": None}
        }
        fiu.save(os.path.join(OUT_DIR, f"folder-{slug}.json"), doc)


def clean_previous():
    removed = 0
    for f in glob.glob(os.path.join(OUT_DIR, "item-*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("source") in ("Gen8", "Gen9"):
            os.remove(f)
            removed += 1
    if os.path.isdir(ICON_DIR):
        shutil.rmtree(ICON_DIR)
    os.makedirs(ICON_DIR)
    return removed


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-gen89-items.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]

    removed = clean_previous()
    existing_ids = {json.load(open(f, encoding="utf-8"))["_id"]
                    for f in glob.glob(os.path.join(OUT_DIR, "*.json"))}
    ids = folder_ids()
    write_tera_folder(ids)

    total = 0
    problems = []
    seen = set()
    for filename, tag, book_label in BOOKS:
        doc = pymupdf.open(os.path.join(pdf_dir, filename))
        first, last = chapter_pages(doc, "Itens")
        print(f"\n{filename}: capítulo Itens nas páginas {first}-{last}")
        for pno in range(first, last + 1):
            page = doc[pno - 1]
            heads = headings(page)
            images = page.get_image_info(xrefs=True)
            for table in page.find_tables().tables:
                parsed = read_table(table)
                if parsed is None:
                    continue
                items, cols = parsed
                above = [text for y, text in heads if y < table.bbox[1]]
                section = above[-1] if above else "Itens"
                print(f"  p{pno} {section}: {len(items)} itens")
                for item in items:
                    name = item["name"]
                    if not name or name in seen:
                        problems.append(f"{tag} p{pno}: nome vazio ou repetido '{name}'")
                        continue
                    seen.add(name)
                    slug = slugify(name)
                    xref = find_icon(images, item, cols, table.bbox[0])
                    img = "icons/svg/item-bag.svg"
                    borrowed = slugify(ICON_FROM.get(name, ""))
                    if xref:
                        save_icon(doc, xref, os.path.join(ICON_DIR, f"{slug}.png"))
                        img = ICON_URL.format(slug=slug)
                    elif borrowed and os.path.exists(os.path.join(ICON_DIR, f"{borrowed}.png")):
                        img = ICON_URL.format(slug=borrowed)
                    else:
                        problems.append(f"{name}: ícone não encontrado")

                    desc = paragraphs_html(item["lines"])
                    if not desc:
                        problems.append(f"{name}: sem efeito")
                    desc += MODULE_NOTES.get(name, "")
                    desc += f"<p><em>{section} — {book_label}</em></p>"

                    item_type, system = fiu.catalog_item(name, desc, price_value(item["price"]),
                                                         fiu.is_consumable(name))
                    doc_id = fiu.make_id(f"item-{name}")
                    if doc_id in existing_ids:
                        raise SystemExit(f"ID {doc_id} de '{name}' colide com um documento existente")
                    existing_ids.add(doc_id)
                    fiu.save(os.path.join(OUT_DIR, f"item-{slug}.json"), {
                        "_key": f"!items!{doc_id}",
                        "_id": doc_id, "name": name, "type": item_type, "img": img, "system": system,
                        "effects": [], "folder": ids[folders.item_subfolder(name)],
                        "flags": {"pokemon-mundo-perfeito": {
                            "category": "item-treinador", "priceRaw": item["price"] or "",
                            "source": tag, "section": section}},
                        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                                   "compendiumSource": None, "duplicateSource": None},
                        "sort": 0, "ownership": {"default": 0}
                    })
                    total += 1

    print(f"\n{removed} itens antigos de Gen 8/9 removidos; {total} itens gravados em {OUT_DIR}")
    print(f"{len(os.listdir(ICON_DIR))} ícones em {ICON_DIR}")
    if problems:
        print(f"{len(problems)} avisos:")
        for p in problems:
            print(f"  - {p}")


if __name__ == "__main__":
    main()
