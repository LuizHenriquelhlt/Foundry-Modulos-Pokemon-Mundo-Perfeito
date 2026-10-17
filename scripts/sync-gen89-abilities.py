#!/usr/bin/env python3
"""
Preenche o texto das Habilidades Passivas de Gen 8/9 a partir dos suplementos (capítulos
"Habilidades Passivas da Oitava Geração" e "... da Nona Geração").

Até aqui essas 73 Habilidades existiam no compêndio "abilities" só como marcador
(flag placeholder=true, texto "Regra completa não encontrada no glossário..."), porque o
glossário do Livro de Regras para na Geração 7 — e as cópias embutidas nos Pokémon da
Pokédex ("Habilidade Passiva: X" / "Habilidade Oculta: X") herdaram esse marcador. Este
script:

- lê o capítulo de cada livro (páginas pelo sumário do PDF) com PyMuPDF: título de cada
  Habilidade em fonte "Digitalt" 18pt, parágrafo começando com recuo, "Observações:" em
  negrito (ou como subtítulo, caso de Hadron Engine) e listas marcadas com "•";
- grava o texto no documento do compêndio (mesmo _id, nome e ícone), troca a flag
  placeholder pela flag source Gen8/Gen9;
- monta também as Habilidades combinadas que a Pokédex lista juntas ("Pressure +
  Transformer", do Deoxys) a partir das entradas individuais;
- atualiza as cópias embutidas na Pokédex que ainda tinham o marcador.

Só substitui texto que ainda é marcador (no compêndio e nos Pokémon) — uma Habilidade que
alguém já tenha escrito à mão não é tocada. Idempotente.
Uso: python scripts/sync-gen89-abilities.py "<pasta com os PDFs>"
"""
import glob
import json
import os
import re
import sys
from collections import Counter

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ABILITIES = os.path.join(ROOT, "packs", "_source", "abilities")
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")

BOOKS = [
    ("Geração 8 - Pokémon Mundo Perfeito.pdf", "Gen8"),
    ("Geração 9 - Pokémon Mundo Perfeito.pdf", "Gen9"),
]
STUB_MARK = "Regra completa não encontrada"
HEADING_FONT = "Digitalt"
BULLET = "•"
PARAGRAPH_GAP = 15  # distância vertical (pt) que separa uma lista do parágrafo seguinte


def save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def chapter_pages(doc, prefix):
    tops = [(t.strip(), p) for lv, t, p in doc.get_toc() if lv == 1]
    for i, (t, p) in enumerate(tops):
        if t.startswith(prefix):
            return p, (tops[i + 1][1] - 1 if i + 1 < len(tops) else doc.page_count)
    raise SystemExit(f"Capítulo '{prefix}...' não encontrado no sumário de {doc.name}")


def page_lines(page):
    """[(x0, y0, texto, fontes, tamanho)] das linhas com texto, em ordem de leitura."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            text = re.sub(r"\s+", " ", "".join(s["text"] for s in line["spans"])).strip().replace("’", "'")
            fonts = {s["font"] for s in spans}
            out.append((line["bbox"][0], line["bbox"][1], text, fonts, max(s["size"] for s in spans)))
    return out


def is_page_number(text, size):
    return bool(re.fullmatch(r"\d{1,3}", text)) and size < 12


def join_lines(lines):
    text = ""
    for line in lines:
        if not text:
            text = line
        elif text.endswith("-") and line[:1].islower():
            text += line
        else:
            text += " " + line
    return text.strip()


class EntryBuilder:
    """Transforma as linhas de uma Habilidade em HTML (parágrafos, rótulo e listas)."""

    def __init__(self, margin):
        self.margin = margin
        self.html = []
        self.para = []
        self.bullets = []      # itens da lista aberta
        self.bullet = None     # linhas do item atual
        self.bullet_x = None
        self.last_y = None

    def set_margin(self, margin):
        self.margin = margin

    def _flush_para(self):
        if self.para:
            self.html.append(f"<p>{join_lines(self.para)}</p>")
            self.para = []

    def _flush_list(self):
        if self.bullet:
            self.bullets.append(join_lines(self.bullet))
            self.bullet = None
        if self.bullets:
            self.html.append("<ul>" + "".join(f"<li>{b}</li>" for b in self.bullets) + "</ul>")
            self.bullets = []

    def label(self, text):
        self._flush_para()
        self._flush_list()
        self.html.append(f"<p><strong>{text}</strong></p>")
        self.last_y = None

    def line(self, x, y, text, new_page=False):
        gap = (y - self.last_y) if (self.last_y is not None and not new_page) else 0
        self.last_y = y
        if text == BULLET:
            self._flush_para()
            if self.bullet:
                self.bullets.append(join_lines(self.bullet))
            self.bullet, self.bullet_x = [], None
            return
        if self.bullet is not None:
            if self.bullet_x is None:
                self.bullet_x = x
                self.bullet.append(text)
                return
            if gap <= PARAGRAPH_GAP and x >= self.bullet_x - 3:
                self.bullet.append(text)
                return
            self._flush_list()
        if self.para and x > self.margin + 5:
            self._flush_para()
        self.para.append(text)

    def finish(self):
        self._flush_para()
        self._flush_list()
        return "".join(self.html)


def parse_chapter(pdf_path):
    doc = pymupdf.open(pdf_path)
    first, last = chapter_pages(doc, "Habilidades Passivas")
    entries = {}
    builder = name = None
    for pno in range(first, last + 1):
        lines = [l for l in page_lines(doc[pno - 1]) if not is_page_number(l[2], l[4])]
        # margem do texto = alinhamento dos títulos da página (a 2ª linha em diante de cada
        # parágrafo volta para ela; a 1ª vem recuada). A posição "mais comum" não serve: numa
        # página de parágrafos curtos há mais linhas recuadas do que alinhadas.
        heading_x = [x for x, y, t, f, s in lines if all(fn.startswith(HEADING_FONT) for fn in f)]
        body_x = [x for x, y, t, f, s in lines if t != BULLET and not any(fn.startswith(HEADING_FONT) for fn in f)]
        margin = min(heading_x) if heading_x else (min(body_x) if body_x else 28)
        new_page = True
        for x, y, text, fonts, size in lines:
            is_heading = all(fn.startswith(HEADING_FONT) for fn in fonts)
            if is_heading and size >= 24:
                continue  # título do capítulo
            if (is_heading or any("Bold" in fn for fn in fonts)) and text.rstrip(":").lower() == "observações":
                builder.label("Observações:")
                continue
            if is_heading:
                if builder:
                    entries[name] = builder.finish()
                name, builder = text, EntryBuilder(margin)
                new_page = False
                continue
            if builder is None:
                continue
            builder.set_margin(margin)
            builder.line(x, y, text, new_page)
            new_page = False
    if builder:
        entries[name] = builder.finish()
    return (first, last), entries


def is_stub(html):
    return STUB_MARK in (html or "")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/sync-gen89-abilities.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]

    pack = {}
    for f in glob.glob(os.path.join(ABILITIES, "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        pack[doc["name"].lower()] = (f, doc)

    texts = {}      # nome em minúsculas -> HTML final de cada Habilidade preenchida aqui
    previous = {}   # nome em minúsculas -> HTML anterior (cópias idênticas a ele também mudam)
    filled, kept, unknown = [], 0, []
    for filename, tag in BOOKS:
        pages, entries = parse_chapter(os.path.join(pdf_dir, filename))
        print(f"{filename}: {len(entries)} Habilidades nas páginas {pages[0]}-{pages[1]}")
        for name, html in entries.items():
            hit = pack.get(name.lower())
            if not hit:
                unknown.append(f"{name} ({tag})")
                continue
            path, doc = hit
            flags = doc.setdefault("flags", {}).setdefault("pokemon-mundo-perfeito", {})
            current = doc["system"]["description"]["value"]
            if not is_stub(current) and flags.get("source") != tag:
                kept += 1  # escrita à mão ou vinda do Livro de Regras: não mexe
                continue
            texts[name.lower()] = html
            previous[name.lower()] = current
            if current != html or flags.get("placeholder") or flags.get("source") != tag:
                doc["system"]["description"]["value"] = html
                flags.pop("placeholder", None)
                flags["source"] = tag
                save(path, doc)
                filled.append(name)

    # Habilidades combinadas ("Pressure + Transformer"): junta os textos das partes
    combined = []
    for key, (path, doc) in pack.items():
        flags = doc["flags"]["pokemon-mundo-perfeito"]
        current = doc["system"]["description"]["value"]
        if " + " not in doc["name"] or not (is_stub(current) or flags.get("combined")):
            continue
        parts = [p.strip() for p in doc["name"].split(" + ")]
        found = [pack.get(p.lower()) for p in parts]
        if not all(found) or any(is_stub(f[1]["system"]["description"]["value"]) for f in found):
            continue
        html = "".join(f"<h3>{p}</h3>{f[1]['system']['description']['value']}" for p, f in zip(parts, found))
        texts[key] = html
        previous[key] = current
        if html != current:
            doc["system"]["description"]["value"] = html
            flags.pop("placeholder", None)
            flags["combined"] = parts
            save(path, doc)
            combined.append(doc["name"])

    # cópias embutidas na Pokédex
    embedded = Counter()
    for f in glob.glob(os.path.join(POKEDEX, "*.json")):
        actor = json.load(open(f, encoding="utf-8"))
        touched = False
        for item in actor.get("items", []):
            m = re.match(r"Habilidade (?:Passiva|Oculta|Mega): (.+)$", item["name"])
            if not m:
                continue
            key = m.group(1).strip().lower()
            value = item["system"].get("description", {}).get("value")
            html = texts.get(key)
            if html and value != html and (is_stub(value) or value == previous.get(key)):
                item["system"]["description"]["value"] = html
                embedded[item["name"].split(":")[0]] += 1
                touched = True
        if touched:
            save(f, actor)

    left = [d["name"] for _, d in pack.values() if is_stub(d["system"]["description"]["value"])]
    print(f"\n{len(filled)} Habilidades preenchidas no compêndio, {kept} já tinham texto próprio")
    if combined:
        print(f"Combinadas montadas a partir das partes: {', '.join(combined)}")
    print(f"Cópias na Pokédex atualizadas: {dict(embedded)}")
    if unknown:
        print(f"No livro mas sem entrada no compêndio: {', '.join(unknown)}")
    print(f"Ainda como marcador no compêndio: {left or 'nenhuma'}")


if __name__ == "__main__":
    main()
