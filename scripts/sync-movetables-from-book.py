#!/usr/bin/env python3
"""
Sincroniza o campo "moveTable" (Moves adquiridos em cada nível) de cada espécie na Pokédex
com o "Livro dos Pokémon - Pokémon Mundo Perfeito.pdf" (fonte oficial dos blocos de
estatística) — o Luiz avisou que essa tabela estava desatualizada/errada em relação ao livro.

Só mexe em "moveTable". NÃO toca em knownMoves (moves iniciais de um Actor recém-criado no
Nível Mínimo Encontrado — essa lista já foi curada à mão pra caber no limite de 4 Moves
conhecidos, e reconstruir isso a partir do moveTable puro exigiria decidir sozinho QUAIS 4
Moves escolher, o que não é o que foi pedido) nem em nenhum outro campo (tipo, atributos, TMs,
Egg Moves etc.) — só a tabela de progressão por nível.

Layout do PDF: 2 espécies por página, lado a lado (colunas esquerda/direita). Duas
dificuldades de extração, resolvidas aqui com coordenadas de palavra (não texto corrido):

1. Cada bloco de espécie tem uma altura de texto ligeiramente diferente, então uma extração
   ingênua linha-a-linha intercala as duas colunas de forma inconsistente — por isso as
   palavras são primeiro agrupadas por região X (esquerda/direita da metade da página) antes
   de reconstruir qualquer linha.
2. Dentro da própria tabela "Nível | Moves adquiridos em cada nível", quando a lista de Moves
   de um nível quebra em 2+ linhas, o número do Nível aparece CENTRALIZADO verticalmente em
   relação a essa célula multi-linha — ou seja, o texto do nível pode aparecer ENTRE as linhas
   de Moves, não necessariamente antes delas (ex.: Kingambit nível 1 tem 6 Moves quebrando em
   2 linhas, com o "1" aparecendo entre as duas). Por isso a tabela é reconstruída por
   PALAVRA: qualquer palavra que seja só um número de 1-2 dígitos é um marcador de nível;
   todas as outras palavras dentro da região da tabela são atribuídas ao marcador de nível
   mais próximo verticalmente (vizinho mais próximo), não por ordem de linha.

Casamento com os arquivos já existentes em packs/_source/pokedex/*.json é feito por
`dexNumber` (extraído do "#DDDD" no cabeçalho do bloco) + nome normalizado (sem acento,
minúsculo) — várias formas regionais/alternativas compartilham o mesmo dexNumber, então o
nome desambigua. Formas de batalha sem bloco próprio no livro (Aegislash Forma Escudo/Espada,
Necrozma Asas da Alvorada, etc.) ficam de fora do relatório de "sem correspondência" — não há
nada pra sincronizar contra, o livro só documenta a forma base.

Idempotente: se o moveTable já bate com o livro, o arquivo não é reescrito.

Uso:
  python scripts/sync-movetables-from-book.py                 # aplica as mudanças
  python scripts/sync-movetables-from-book.py --dry-run        # só relata as diferenças
"""
import glob
import json
import os
import re
import sys
import unicodedata

import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKEDEX_DIR = os.path.join(ROOT, "packs", "_source", "pokedex")
BOOK_PDF = r"C:\Users\Luiz\Documents\Base de Dados - PMP\Livro dos Pokémon - Pokémon Mundo Perfeito.pdf"

HEADER_RE = re.compile(r"^(.*?)\s+#(\d{3,4})$")
MOVE_TABLE_HEADER_RE = re.compile(r"^N[íi]vel\s+Moves adquiridos em cada n[íi]vel$")
BARE_LEVEL_RE = re.compile(r"^\d{1,2}$")
EMPTY_MARKERS = {"—", "-", "–"}


def normalize_name(name):
    """Chave tolerante a acento/caixa pra casar nomes do livro com os do compêndio."""
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", stripped.lower())


def grouped_lines(words):
    """words já filtradas pra uma coluna/região — agrupa por 'top' arredondado, retorna
    lista de (top, texto_da_linha) em ordem crescente de top."""
    rows = {}
    for w in words:
        key = round(w["top"])
        rows.setdefault(key, []).append(w)
    out = []
    for top in sorted(rows.keys()):
        row = sorted(rows[top], key=lambda w: w["x0"])
        out.append((top, " ".join(w["text"] for w in row)))
    return out


def parse_species_block(words):
    """words: todas as palavras de UMA coluna (um bloco de espécie inteiro).
    Retorna (name, dex, move_table)."""
    lines = grouped_lines(words)
    if not lines:
        return None, None, []
    header = HEADER_RE.match(lines[0][1].strip())
    if not header:
        return None, None, []
    name, dex = header.group(1).strip(), int(header.group(2))

    header_top = next((top for top, text in lines if MOVE_TABLE_HEADER_RE.match(text.strip())), None)
    if header_top is None:
        return name, dex, []
    tms_top = next((top for top, text in lines
                     if top > header_top and (text.strip().startswith("TMs:") or text.strip() == "TMs")), None)
    if tms_top is None:
        tms_top = max(w["top"] for w in words) + 1

    # Compara top ARREDONDADO nos dois lados (grouped_lines já usou round() pra achar
    # header_top/tms_top) — misturar bruto com arredondado deixa passar palavras da própria
    # linha de cabeçalho/TMs quando o arredondamento "puxa" o valor pra cima ou pra baixo.
    table_words = [w for w in words if header_top < round(w["top"]) < tms_top]
    level_markers = sorted(
        ({"top": w["top"], "level": int(w["text"])} for w in table_words if BARE_LEVEL_RE.match(w["text"])),
        key=lambda m: m["top"]
    )
    if not level_markers:
        return name, dex, []

    move_words = [w for w in table_words if not BARE_LEVEL_RE.match(w["text"])]
    # Cada palavra de Move vai pro marcador de nível verticalmente mais próximo — resolve o
    # caso em que o número do nível fica centralizado entre as linhas de uma lista que quebrou.
    buckets = {m["level"]: [] for m in level_markers}
    for w in move_words:
        nearest = min(level_markers, key=lambda m: abs(m["top"] - w["top"]))
        buckets[nearest["level"]].append(w)

    table = []
    for level in sorted(buckets.keys()):
        ws = sorted(buckets[level], key=lambda w: (w["top"], w["x0"]))
        text = " ".join(w["text"] for w in ws)
        moves = [m.strip() for m in text.split(",") if m.strip() and m.strip() not in EMPTY_MARKERS]
        table.append({"level": level, "moves": moves})
    return name, dex, table


def extract_book():
    """Retorna dict {(dexNumber, nome_normalizado): moveTable} pra cada bloco do livro."""
    entries = {}
    dupes = []
    with pdfplumber.open(BOOK_PDF) as pdf:
        for page in pdf.pages:
            mid = page.width / 2
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            for x_min, x_max in ((0, mid), (mid, page.width)):
                col_words = [w for w in words if x_min <= w["x0"] < x_max]
                name, dex, table = parse_species_block(col_words)
                if name is None:
                    continue
                key = (dex, normalize_name(name))
                if key in entries:
                    dupes.append((name, dex))
                entries[key] = {"name": name, "dex": dex, "moveTable": table}
    return entries, dupes


def load_pokedex_files():
    files = []
    for path in sorted(glob.glob(os.path.join(POKEDEX_DIR, "*.json"))):
        base = os.path.basename(path)
        if base.startswith("folder-"):
            continue
        doc = json.load(open(path, encoding="utf-8"))
        files.append((path, doc))
    return files


def main():
    dry_run = "--dry-run" in sys.argv

    print("Extraindo tabelas de Move do livro (596 páginas)...")
    book_entries, dupes = extract_book()
    print(f"  {len(book_entries)} blocos de espécie extraídos do livro.")
    if dupes:
        print(f"  AVISO: {len(dupes)} cabeçalhos duplicados/ambíguos no livro: {dupes[:10]}")

    pokedex_files = load_pokedex_files()
    print(f"Comparando com {len(pokedex_files)} arquivos em {POKEDEX_DIR}...")

    changed = []
    unmatched = []
    for path, doc in pokedex_files:
        pmp = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("species")
        if not pmp:
            continue
        dex = pmp.get("dexNumber")
        name = doc.get("name", "")
        key = (dex, normalize_name(name))
        book = book_entries.get(key)
        if book is None:
            unmatched.append((os.path.basename(path), name, dex))
            continue

        old_table = pmp.get("moveTable", [])
        new_table = book["moveTable"]
        if old_table == new_table:
            continue

        changed.append((os.path.basename(path), name, old_table, new_table))
        if not dry_run:
            pmp["moveTable"] = new_table
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
                fh.write("\n")

    report_path = os.path.join(ROOT, "movetable-sync-report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(f"Espécies com moveTable diferente do livro: {len(changed)}\n")
        fh.write(f"Espécies do compêndio sem correspondência no livro: {len(unmatched)}\n\n")
        fh.write("===== MUDANÇAS =====\n")
        for base, name, old, new in changed:
            fh.write(f"\n-- {name} ({base}) --\n")
            fh.write(f"  ANTES: {old}\n")
            fh.write(f"  DEPOIS: {new}\n")
        fh.write("\n===== SEM CORRESPONDÊNCIA NO LIVRO =====\n")
        for base, name, dex in unmatched:
            fh.write(f"  {name} (dex {dex}, arquivo {base})\n")

    print(f"{len(changed)} espécies com moveTable diferente do livro.")
    print(f"{len(unmatched)} espécies do compêndio sem correspondência no livro.")
    print(f"Relatório completo em {report_path}")
    if dry_run:
        print("(--dry-run: nenhum arquivo foi alterado)")


if __name__ == "__main__":
    main()
