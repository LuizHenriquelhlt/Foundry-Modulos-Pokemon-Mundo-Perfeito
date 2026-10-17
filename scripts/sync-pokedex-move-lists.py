#!/usr/bin/env python3
"""
Relê do Livro dos Pokémon as listas de Moves de cada espécie — tabela "Nível | Moves
adquiridos em cada nível", "TMs:" e "Egg Moves:" — e corrige a Pokédex onde ela diverge.

Por que existe: as listas tinham sido extraídas com pdfplumber, que nesse PDF parte palavras
com espaçamento de letra ("St o m p i n g T a n tr u m", "Ca n n o n") e números de nível
("16" vira "1" e "6" — os Moves dos níveis 16-20 caíam no nível 1, como "Metal Claw Flash
Cannon" no Duraludon). As listas de TMs/Egg Moves também emendavam o texto seguinte do livro
("Zen Headbutt Def esa s d e T ipo : x2 ½...", "Mudança de Forma: ..."). O PyMuPDF lê essas
mesmas linhas sem esses defeitos.

Para cada espécie (casada pelo título "Nome #0000" da coluna, ou só pelo nome nas formas):
- tabela por nível: palavras de Move vão para o número de nível mais próximo na vertical (o
  número fica centralizado quando a lista quebra em várias linhas);
- TMs e Egg Moves: do rótulo até a linha em branco, emendando "Will-O-" + "Wisp";
- cada nome é resolvido contra o compêndio de Moves (sem acento/espaço/pontuação), e o nome
  canônico do compêndio é o que fica gravado.

Quando a lista muda, atualiza também o que o conversor derivou dela: os ItemGrant de Moves
por nível da classe embutida (mantendo os itens de progressão do mesmo nível), as cópias dos
Moves iniciais embutidas no Actor (até o Nível Mínimo Encontrado) e a biografia, que mostra
as tabelas. knownMoves (lista curada à mão) só tem os nomes quebrados resolvidos.
Idempotente. Uso: python scripts/sync-pokedex-move-lists.py "<pasta com os PDFs>" [--dry-run]
"""
import glob
import importlib.util
import json
import os
import re
import sys
import unicodedata
from collections import Counter

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")
MOVES = os.path.join(ROOT, "packs", "_source", "moves")
MODULE_ID = "pokemon-mundo-perfeito"
BOOK = "Livro dos Pokémon - Pokémon Mundo Perfeito.pdf"
HEADING_FONT = "PokemonGB"
NO_TMS = "não possui TMs"
EMPTY_MARKERS = {"—", "-", "–", ""}
MOVE_UUID = "Compendium.pokemon-mundo-perfeito.moves.Item."

spec = importlib.util.spec_from_file_location("convert_native", os.path.join(HERE, "convert-to-dnd5e-native.py"))
convert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(convert)


def key_of(text):
    text = "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text)


def load_moves():
    by_key = {}
    for f in glob.glob(os.path.join(MOVES, "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if not doc["_key"].startswith("!folders"):
            by_key[key_of(doc["name"])] = doc
    return by_key


class Resolver:
    """Nome do livro -> nome do compêndio. Tenta o nome inteiro e, se não achar, segmenta
    (vírgula faltando no livro: "Withdraw Razor Shell" = Withdraw + Razor Shell)."""

    def __init__(self, moves_by_key):
        self.moves = moves_by_key
        self.unresolved = Counter()

    def segment(self, key):
        best = {0: []}
        for i in range(len(key)):
            if i not in best:
                continue
            for j in range(i + 1, len(key) + 1):
                if key[i:j] in self.moves and (j not in best or len(best[j]) > len(best[i]) + 1):
                    best[j] = best[i] + [key[i:j]]
        return best.get(len(key))

    def names(self, raw):
        raw = raw.strip().rstrip(".")
        if raw in EMPTY_MARKERS:
            return []
        key = key_of(raw)
        if not key:
            return []
        if key in self.moves:
            return [self.moves[key]["name"]]
        parts = self.segment(key)
        if parts:
            return [self.moves[p]["name"] for p in parts]
        self.unresolved[raw] += 1
        return [raw]

    def resolve_list(self, raws):
        out = []
        for raw in raws:
            for name in self.names(raw):
                if name not in out:
                    out.append(name)
        return out


def join_lines(lines):
    text = ""
    for line in lines:
        line = line.strip()
        if text.endswith("-"):
            text += line
        else:
            text += (" " if text else "") + line
    return text


def column_blocks(page):
    """Divide a página nas duas colunas e devolve, por coluna, (linhas, palavras)."""
    mid = page.rect.width / 2
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"])
            fonts = {s["font"] for s in line["spans"] if s["text"].strip()}
            lines.append((line["bbox"][0], line["bbox"][1], text, fonts))
    words = page.get_text("words")
    for column in (0, 1):
        col_lines = sorted((l for l in lines if (l[0] >= mid) == bool(column)), key=lambda l: l[1])
        col_words = [w for w in words if (w[0] >= mid) == bool(column)]
        yield col_lines, col_words


def repair_wrapped_cells(buckets, is_move):
    """Uma célula de Moves que quebra em várias linhas tem o número do nível centralizado; a
    última linha ("Down", de "Take Down") pode ficar mais perto do nível seguinte. Se o último
    Move de um nível não existe e passa a existir puxando a 1ª palavra do nível seguinte, a
    palavra volta pro nível de cima."""
    levels = sorted(buckets)
    for a, b in zip(levels, levels[1:]):
        for _ in range(3):
            text_a = " ".join(w[4] for w in buckets[a])
            last = text_a.split(",")[-1].strip()
            # nível vazio ("—") não tem Move a completar — sem isso "— Acid" virava "Acid"
            if not buckets[b] or last in EMPTY_MARKERS or not key_of(last) or is_move(last):
                break
            candidate = f"{last} {buckets[b][0][4].rstrip(',')}"
            if not is_move(candidate):
                break
            buckets[a].append(buckets[b].pop(0))


def parse_column(col_lines, col_words, is_move=lambda name: True):
    """{"name", "dex", "table": [{level, moves}], "tms": [...], "eggMoves": [...]} ou None."""
    heading, dex, idx = [], None, 0
    for idx, (x, y, text, fonts) in enumerate(col_lines):
        if any(f.startswith(HEADING_FONT) for f in fonts):
            heading.append(text)
            if m := re.search(r"#(\d{3,4})", text):
                dex = int(m.group(1))
            nxt = col_lines[idx + 1] if idx + 1 < len(col_lines) else None
            if not (nxt and any(f.startswith(HEADING_FONT) for f in nxt[3]) and nxt[1] - y < 16):
                break
    if not heading:
        return None
    name = re.sub(r"\s+", " ", " ".join(h.split("#")[0] for h in heading)).strip()

    def find(prefix):
        return next((i for i, l in enumerate(col_lines) if l[2].strip().startswith(prefix)), None)

    table_i = next((i for i, l in enumerate(col_lines) if "Moves adquiridos" in l[2]), None)
    tms_i, egg_i = find("TMs"), find("Egg Moves")

    def labeled_list(start, label):
        if start is None:
            return None
        parts = [col_lines[start][2].strip()[len(label):].lstrip(": ")]
        for x, y, text, fonts in col_lines[start + 1:]:
            if not text.strip() or text.strip().startswith(("Egg Moves", "TMs", "Defesas", "Mudança")):
                break
            parts.append(text)
        text = join_lines(parts)
        if NO_TMS in text or not text.strip():
            return []
        return [p for p in (s.strip() for s in text.split(",")) if p]

    table = []
    if table_i is not None:
        top = col_lines[table_i][1] + 4
        bottom = col_lines[tms_i][1] - 2 if tms_i is not None and tms_i > table_i else 10 ** 6
        level_x = min((l[0] for l in col_lines[table_i:table_i + 3] if "Nível" in l[2]), default=None)
        region = [w for w in col_words if top < w[1] < bottom]
        markers = [w for w in region if re.fullmatch(r"\d{1,2}", w[4])
                   and (level_x is None or abs(w[0] - level_x) < 20)]
        move_words = [w for w in region if w not in markers]
        buckets = {int(m[4]): [] for m in markers}
        for w in move_words:
            nearest = min(markers, key=lambda m: abs(m[1] - w[1]), default=None)
            if nearest is not None:
                buckets[int(nearest[4])].append(w)
        for level in buckets:
            buckets[level].sort(key=lambda w: (round(w[1]), w[0]))
        repair_wrapped_cells(buckets, is_move)
        for level in sorted(buckets):
            text = " ".join(w[4] for w in buckets[level])
            moves = [m.strip() for m in text.split(",") if m.strip() not in EMPTY_MARKERS]
            table.append({"level": level, "moves": moves})
    return {"name": name, "dex": dex, "table": table,
            "tms": labeled_list(tms_i, "TMs"), "eggMoves": labeled_list(egg_i, "Egg Moves")}


def read_book(pdf_path, is_move):
    entries = []
    for page in pymupdf.open(pdf_path):
        for col_lines, col_words in column_blocks(page):
            entry = parse_column(col_lines, col_words, is_move)
            if entry:
                entries.append(entry)
    return entries


def update_grants(doc, species_name, min_level, table, moves_by_key):
    """Troca os Moves dos ItemGrant por nível da classe embutida pelos da tabela nova."""
    cls = next(i for i in doc["items"] if i["type"] == "class")
    advs = cls["system"]["advancement"]
    # os ItemGrant da classe da espécie são os "Moves e Recursos" de cada nível (Moves +
    # itens de progressão do mesmo nível), um por nível — ver build_class_item
    by_level = {a.get("level"): a for a in advs if a["type"] == "ItemGrant"}
    wanted = {}
    for row in table:
        if min_level < row["level"] <= 20:
            ids = [moves_by_key[key_of(n)]["_id"] for n in row["moves"] if key_of(n) in moves_by_key]
            if ids:
                wanted[row["level"]] = [f"{MOVE_UUID}{i}" for i in ids]
    changed = False
    for level in range(min_level + 1, 21):
        adv = by_level.get(level)
        others = [it for it in (adv["configuration"]["items"] if adv else []) if MOVE_UUID not in it["uuid"]]
        new_items = [{"uuid": u, "optional": False} for u in wanted.get(level, [])] + others
        if adv is None:
            if not new_items:
                continue
            advs.append({
                "_id": convert.make_id(f"{species_name}-adv-grant-{level}"),
                "type": "ItemGrant", "level": level, "title": "Moves e Recursos",
                "configuration": {"items": new_items, "optional": False, "spell": None},
                "value": {}, "flags": {}
            })
            changed = True
        elif adv["configuration"]["items"] != new_items:
            if new_items:
                adv["configuration"]["items"] = new_items
            else:
                advs.remove(adv)
            changed = True
    advs.sort(key=lambda a: (a.get("level") or 0))
    return changed


def update_known(doc, min_level, old_table, new_table, moves_by_key):
    """Cópias embutidas dos Moves iniciais (níveis até o Nível Mínimo Encontrado)."""
    def known(table):
        names = [n for r in table if r["level"] <= min_level for n in r["moves"]]
        if not names and table:
            names = list(table[0]["moves"])
        return {key_of(n) for n in names + ["Struggle"]}
    old_keys, new_keys = known(old_table), known(new_table)
    items = doc["items"]
    present = {key_of(i["name"]) for i in items if i.get("flags", {}).get(MODULE_ID, {}).get("move")}
    added = removed = 0
    for k in sorted(new_keys - present):
        if k in moves_by_key:
            src = moves_by_key[k]
            embed = json.loads(json.dumps({x: src[x] for x in ("_id", "name", "type", "img", "system", "effects", "flags")}))
            embed["sort"] = 100
            items.append(embed)
            added += 1
    for item in list(items):
        k = key_of(item["name"])
        if item.get("flags", {}).get(MODULE_ID, {}).get("move") and k in old_keys and k not in new_keys:
            items.remove(item)
            removed += 1
    return added, removed


def embedded_keys(doc):
    """_key dos Items embutidos e dos efeitos deles: o CLI do Foundry não compila o pack sem
    eles, e a cópia que vem do compêndio de Moves não tem (ou tem o "!items.effects!..." de lá)."""
    fixed = 0
    for item in doc.get("items", []):
        key = f"!actors.items!{doc['_id']}.{item['_id']}"
        if item.get("_key") != key:
            item["_key"] = key
            fixed += 1
        for effect in item.get("effects", []):
            effect_key = f"!actors.items.effects!{doc['_id']}.{item['_id']}.{effect['_id']}"
            if effect.get("_key") != effect_key:
                effect["_key"] = effect_key
                fixed += 1
    return fixed


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/sync-pokedex-move-lists.py \"<pasta com os PDFs>\" [--dry-run]")
        sys.exit(1)
    dry_run = "--dry-run" in sys.argv
    moves_by_key = load_moves()
    resolver = Resolver(moves_by_key)
    book = read_book(os.path.join(sys.argv[1], BOOK), lambda name: key_of(name) in moves_by_key)
    by_dex_name = {(e["dex"], key_of(e["name"])): e for e in book if e["dex"]}
    by_name = {}
    for e in book:
        by_name.setdefault(key_of(e["name"]), []).append(e)
    print(f"{len(book)} blocos de espécie lidos do livro")

    stats = Counter()
    report, unmatched = [], []
    for f in sorted(glob.glob(os.path.join(POKEDEX, "*.json"))):
        doc = json.load(open(f, encoding="utf-8"))
        if doc["_key"].startswith("!folders"):
            continue
        pmp = doc["flags"][MODULE_ID]["species"]
        k = key_of(doc["name"])
        entry = by_dex_name.get((pmp.get("dexNumber"), k)) or (by_name.get(k) or [None])[0]
        if entry is None:
            unmatched.append(doc["name"])
            continue
        min_level = pmp.get("level") or pmp.get("minLevelFound", 1)
        changes = []

        new_table = [{"level": r["level"], "moves": resolver.resolve_list(r["moves"])} for r in entry["table"]]
        old_table = pmp.get("moveTable") or []
        if new_table and new_table != old_table:
            pmp["moveTable"] = new_table
            changes.append("tabela por nível")
            if update_grants(doc, doc["name"], min_level, new_table, moves_by_key):
                stats["grants"] += 1
            added, removed = update_known(doc, min_level, old_table, new_table, moves_by_key)
            stats["embedded_added"] += added
            stats["embedded_removed"] += removed
        for field in ("tms", "eggMoves"):
            # sem a lista no bloco do livro (ex.: Mew), só resolve os nomes já guardados
            source = entry[field] if entry[field] is not None else (pmp.get(field) or [])
            new = resolver.resolve_list(source)
            if new != (pmp.get(field) or []):
                pmp[field] = new
                changes.append(field)
        known = pmp.get("knownMoves") or []
        fixed_known = resolver.resolve_list([re.split(r"\s\d+\s", n)[0] for n in known])
        if fixed_known != known:
            pmp["knownMoves"] = fixed_known
            changes.append("knownMoves")
        if changes:
            doc["system"]["details"]["biography"]["value"] = convert.biography_html(pmp, doc["name"])
            stats["species"] += 1
            for c in changes:
                stats[c] += 1
            report.append(f"{doc['name']}: {', '.join(changes)}")
        keys_fixed = embedded_keys(doc)
        stats["keys"] += keys_fixed
        if (changes or keys_fixed) and not dry_run:
            convert.save(f, doc)

    print(f"\n{stats['species']} espécies corrigidas{' (simulação)' if dry_run else ''}: "
          f"tabela {stats['tabela por nível']}, TMs {stats['tms']}, Egg Moves {stats['eggMoves']}, "
          f"knownMoves {stats['knownMoves']}")
    print(f"Avanços de nível atualizados: {stats['grants']} | Moves iniciais embutidos +{stats['embedded_added']} "
          f"-{stats['embedded_removed']} | _key de embutidos corrigidos: {stats['keys']}")
    for line in report[:25]:
        print(f"  {line}")
    if len(report) > 25:
        print(f"  ... e mais {len(report) - 25}")
    if resolver.unresolved:
        print(f"{sum(resolver.unresolved.values())} nomes do livro sem Move no compêndio: "
              f"{resolver.unresolved.most_common(30)}")
    if unmatched:
        print(f"{len(unmatched)} espécies sem bloco no livro: {unmatched[:20]}")


if __name__ == "__main__":
    main()
