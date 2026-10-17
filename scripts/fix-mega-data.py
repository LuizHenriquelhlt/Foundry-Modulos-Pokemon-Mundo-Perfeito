#!/usr/bin/env python3
"""
Relê o capítulo "Lista de Mega Evoluções" do livro de Mega Evoluções com PyMuPDF e corrige
o compêndio "mega-evolutions" onde ele diverge do livro.

O parser original (parse-mega-evolutions.py, pdfplumber) só reconhecia a frase "...enquanto
estiver segurando ESTA pedra" — a Aerodactylite ("segurando A pedra") e a Zygardite ("ao
atingir a Forma Completa") não viraram pedras e o conteúdo delas foi somado à pedra anterior:
a Pinsirite ficou com a habilidade e os bônus da Aerodactylite somados aos dela, a
Hawluchanite com os da Zygardite (CA -1, SAB +9, "tamanho Imenso"). As descrições também
carregavam o começo da frase de abertura ("Charizard X recebe os seguintes benefícios: ...")
e, em 4 pedras, blocos inteiros de outras páginas.

Aqui cada pedra vai do seu título (fonte "Digitalt" ~14pt) até o próximo; os benefícios são
as linhas com "•" (interpretadas pelo mesmo parse_bullet do parser original), e a descrição
é o texto em itálico. Além disso:
- habilidade "[ainda a ser lançada]" não troca a Habilidade Passiva (vira nota em
  otherEffects) — antes, Mega Evoluir substituía a habilidade real por esse texto;
- "Ganha/Mantém a habilidade X" vira a Habilidade da forma Mega (Floettite, Abomasite);
- pokedexSpecies: espécies da Pokédex que podem usar a pedra quando o nome do livro não é o
  da Pokédex (Meowstic -> Meowstic Fêmea/Macho; Eternal Flower Floette -> Floette...);
- cria as pedras que faltam (Aerodactylite, Zygardite) e o Move exclusivo Nihil Light;
- refaz a descrição de todas as pedras (fix-item-usability.mega_description).
Pedras que não estão nesse capítulo (Red/Blue Orb, Rayquaza) só ganham a descrição refeita.
Idempotente. Uso: python scripts/fix-mega-data.py "<pasta com os PDFs>"
"""
import glob
import importlib.util
import json
import os
import re
import sys
import unicodedata
import urllib.request

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MEGAS = os.path.join(ROOT, "packs", "_source", "mega-evolutions")
POKEDEX = os.path.join(ROOT, "packs", "_source", "pokedex")
MOVES = os.path.join(ROOT, "packs", "_source", "moves")
MODULE_ID = "pokemon-mundo-perfeito"
BOOK = "Mega Evoluções - Pokémon Mundo Perfeito.pdf"
ITEM_SPRITE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{slug}.png"

ANCHOR_RE = re.compile(r"Permite que (.+?) Mega Evolua para (.+?)"
                       r"(?: enquanto estiver segurando (?:esta|a) pedra| ao atingir (?:a )?([^.]+))\.\s*(.*)$", re.S)
PENDING_RE = re.compile(r"ainda a ser lan", re.IGNORECASE)
# marca do livro pra habilidade pendente; a frase legível sai na descrição (mega_description)
PENDING_MARK = "[ainda a ser lançada]"
GAINS_ABILITY_RE = re.compile(r"^(Ganha|Mantém) a habilidade (.+?)(?:\s*\(.*)?$")

# nome da espécie no livro -> nomes na Pokédex, quando não batem
SPECIES_ALIASES = {
    "Eternal Flower Floette": ["Floette"],  # o livro de Megas tem bloco próprio dessa forma; a Pokédex só tem Floette
    "Tatsugiri": ["Tatsugiri Forma Curva"],  # "Mega Tatsugiri (Curly Form)"
    "Zygarde": ["Zygarde Forma Completa"],  # "ao atingir a Forma Completa"
}


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(HERE, f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pm = load("parse-mega-evolutions")
fiu = load("fix-item-usability")
sprites = load("fetch-mega-sprites")
parse_moves = load("parse-moves")
sync_moves = load("sync-gen89-moves")


def key_of(text):
    text = "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text)


def chapter_pages(doc):
    tops = [(t.strip(), p) for lv, t, p in doc.get_toc() if lv == 1]
    first = next(p for t, p in tops if t.startswith("Lista de Mega"))
    last = next(p for t, p in tops if t.startswith("Habilidades Passivas")) - 1
    return first, last


def page_lines(page):
    """Linhas da página por coluna, com as linhas justificadas (uma palavra por "linha" no
    PDF) emendadas pela altura: [(coluna, y, x, texto, fonte, tamanho)]."""
    mid = page.rect.width / 2
    raw = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            x, y = line["bbox"][0], line["bbox"][1]
            raw.append((int(x >= mid), round(y), x, "".join(s["text"] for s in line["spans"]).strip(),
                        spans[0]["font"], round(spans[0]["size"], 1)))
    raw.sort()
    merged = []
    for item in raw:
        if merged and merged[-1][0] == item[0] and merged[-1][1] == item[1]:
            col, y, x, text, font, size = merged[-1]
            merged[-1] = (col, y, x, f"{text} {item[3]}", font, size)
        else:
            merged.append(item)
    return merged


def read_book(pdf_path):
    doc = pymupdf.open(pdf_path)
    first, last = chapter_pages(doc)
    stones, specials, current, special = [], [], None, None
    flat = []  # todas as linhas em ordem de leitura, títulos inclusive (pra achar Moves)
    for pno in range(first, last + 1):
        for col, y, x, text, font, size in page_lines(doc[pno - 1]):
            if re.fullmatch(r"\d{1,3}", text):
                continue  # número da página
            flat.append(text)
            if font.startswith("Digitalt") and size >= 20:
                current, special = None, {"title": text, "lines": []}  # página especial (Mega Zygarde)
                specials.append(special)
            elif font.startswith("Digitalt") and size >= 11:
                current, special = {"stone": text, "lines": []}, None
                stones.append(current)
            elif current is not None:
                current["lines"].append((text, font))
            elif special is not None:
                special["lines"].append((text, font))
    return (first, last), stones, flat


def parse_stone(entry, warnings):
    body, bullets, flavor = [], [], []
    for text, font in entry["lines"]:
        if "Italic" in font:
            flavor.append(text)
        elif text.startswith("•"):
            bullets.append(text)
        elif bullets and not flavor:
            bullets[-1] += " " + text  # benefício que quebrou de linha
        else:
            body.append(text)
    m = ANCHOR_RE.search(" ".join(body))
    if not m:
        warnings.append(f"{entry['stone']}: frase \"Permite que...\" não encontrada")
        return None
    species, mega_form, condition, rest = (g.strip() if g else "" for g in m.groups())
    result = {"abilityDeltas": {}, "abilityChoices": [], "movementGrants": [], "otherEffects": []}
    if condition:
        result["otherEffects"].append(f"Só Mega Evolui ao atingir a {condition}.")
    # o que vem entre a frase de abertura e "...recebe os seguintes benefícios:" é condição extra
    # (Zygardite: "Se souber o Move Core Enforcer, este se torna Nihil Light...")
    extra = re.sub(r"\s*(?:Ao Mega Evoluir,.*|[^.]*recebe os seguintes benef[ií]cios:?)$", "", rest).strip()
    if extra:
        result["otherEffects"].append(extra)
    for bullet in bullets:
        text = bullet.lstrip("•").strip()
        # "Aumenta de tamanho para Imenso" (Zygardite) — mesmo efeito de "Seu tamanho muda para"
        if size := re.match(r"^Aumenta de tamanho para (.+)$", text):
            bullet = f"• Seu tamanho muda para {size.group(1)}"
        pm.parse_bullet(bullet, result, [], entry["stone"])
    passive = result.get("passiveAbility", "")
    other = []
    for effect in result["otherEffects"]:
        gains = GAINS_ABILITY_RE.match(effect)
        if PENDING_RE.search(effect):
            continue
        if gains and not PENDING_RE.search(gains.group(2)):
            # "Ganha a habilidade Fairy Aura" / "Mantém a habilidade Snow Warning (torna-se Snow
            # Warning caso tenha Habilidade Oculta)": é a habilidade da forma Mega, em qualquer caso
            passive = passive or gains.group(2).strip()
            continue
        other.append(effect)
    if PENDING_RE.search(passive) or any(PENDING_RE.search(e) for e in result["otherEffects"]):
        passive = PENDING_MARK
    flavor_text = " ".join(flavor).strip()
    return {
        "stoneName": entry["stone"],
        "species": species,
        "megaForm": mega_form,
        "types": result.get("types", {"type1": None, "type2": None}),
        "size": result.get("size"),
        "armorClassDelta": result.get("armorClassDelta", 0),
        "abilityDeltas": result["abilityDeltas"],
        "abilityChoices": result["abilityChoices"],
        "passiveAbility": passive,
        "movementBonusFeet": result.get("movementBonusFeet", 0),
        "movementGrants": result["movementGrants"],
        "otherEffects": other,
        "description": f"<p>{flavor_text}</p>" if flavor_text else ""
    }


def pokedex_names():
    names = set()
    for f in glob.glob(os.path.join(POKEDEX, "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if not doc["_key"].startswith("!folders"):
            names.add(doc["name"])
    return names


def species_list(species, names):
    if species in names:
        return None
    if species in SPECIES_ALIASES:
        return SPECIES_ALIASES[species]
    forms = sorted(n for n in names if n.startswith(species + " "))
    return forms or None


def url_ok(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "pokemon-mundo-perfeito-foundry/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception:
        return False


def new_stone_doc(mega):
    name = mega["stoneName"]
    slug = pm.slugify(name)
    img = ITEM_SPRITE.format(slug=slug)
    try:
        token = sprites.fetch_sprite(sprites.derive_pokeapi_slug(mega["species"], mega["megaForm"]) or "")
    except Exception:
        token = None
    if token:
        mega["tokenImage"] = token
    doc_id = pm.make_id(f"mega-{name}", set())
    return {
        "_key": f"!items!{doc_id}", "_id": doc_id, "name": name, "type": "equipment",
        "img": img if url_ok(img) else "icons/svg/upgrade.svg",
        "system": {
            "description": {"value": "", "chat": ""}, "type": {"value": "trinket", "subtype": ""},
            "price": {"value": 0, "denomination": "gp"}, "weight": {"value": 0, "units": "lb"},
            "quantity": 1, "rarity": "veryRare", "identified": True, "attunement": "", "attuned": False,
            "equipped": False, "armor": {"value": None, "dex": None, "magicalBonus": None}, "properties": []
        },
        "effects": [], "folder": None,
        "flags": {MODULE_ID: {"category": "mega-stone", "species": mega["species"],
                              "megaForm": mega["megaForm"], "mega": mega}},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": 0, "ownership": {"default": 0}
    }


def add_signature_moves(lines, report):
    """Moves exclusivos que o livro de Megas descreve no meio do capítulo (Nihil Light, na
    página da Mega Zygarde). O nome do Move vem em fonte de título, então a busca é feita na
    sequência inteira de linhas; só cria o que ainda não existe no compêndio de Moves."""
    existing = {key_of(json.load(open(f, encoding="utf-8"))["name"]) for f in glob.glob(os.path.join(MOVES, "*.json"))}
    used_ids = {json.load(open(f, encoding="utf-8"))["_id"] for f in glob.glob(os.path.join(MOVES, "*.json"))}
    headers = parse_moves.find_move_headers(lines)
    for i, header in enumerate(headers):
        if header["name"] is None:
            continue  # "Tipo:" de bloco de estatísticas de espécie, não de Move
        end = headers[i + 1]["start"] if i + 1 < len(headers) else len(lines)
        name, system, _ = parse_moves.parse_block(lines, header, end)
        if key_of(name) in existing or "Descrição" not in " ".join(lines[header["tipo_idx"]:end]):
            continue
        pmp = sync_moves.merged_pmp({}, system)
        doc = sync_moves.new_move_doc(name, pmp, "Mega", 20000, used_ids)
        sync_moves.save(os.path.join(MOVES, f"{parse_moves.slugify(name)}.json"), doc)
        existing.add(key_of(name))
        report.append(f"Move criado: {name} — {sync_moves.convert.TYPE_LABELS.get(pmp['moveType'])}, "
                      f"PP {pmp['pp']['max']}, alcance {pmp['range']['raw']}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/fix-mega-data.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pages, entries, flat = read_book(os.path.join(sys.argv[1], BOOK))
    warnings, report = [], []
    book = {}
    for entry in entries:
        mega = parse_stone(entry, warnings)
        if mega:
            book[mega["stoneName"]] = mega
    print(f"{BOOK}: {len(book)} Mega Pedras nas páginas {pages[0]}-{pages[1]}")

    names = pokedex_names()
    files = {}
    for f in glob.glob(os.path.join(MEGAS, "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        files[doc["name"]] = (f, doc)

    mechanics = ["species", "megaForm", "types", "size", "armorClassDelta", "abilityDeltas", "abilityChoices",
                 "passiveAbility", "movementBonusFeet", "movementGrants", "otherEffects"]
    for name, mega in book.items():
        pokedex_species = species_list(mega["species"], names)
        if pokedex_species:
            mega["pokedexSpecies"] = pokedex_species
        if name not in files:
            doc = new_stone_doc(mega)
            path = os.path.join(MEGAS, f"{pm.slugify(name)}.json")
            files[name] = (path, doc)
            report.append(f"Pedra criada: {name} ({mega['species']} -> {mega['megaForm']})")
            continue
        path, doc = files[name]
        flags = doc["flags"][MODULE_ID]
        old = flags["mega"]
        diffs = [k for k in mechanics + ["pokedexSpecies"] if old.get(k) != mega.get(k)]
        if [d for d in diffs if d not in ("otherEffects",)] or diffs:
            mech = [d for d in diffs if d != "otherEffects"]
            if mech or diffs:
                report.append(f"{name}: " + ", ".join(f"{d} {old.get(d)!r} -> {mega.get(d)!r}" for d in diffs))
        flags["mega"] = {**{k: v for k, v in old.items() if k != "pokedexSpecies"}, **mega}
        flags["species"], flags["megaForm"] = mega["species"], mega["megaForm"]

    add_signature_moves(flat, report)

    rewritten = 0
    for name, (path, doc) in files.items():
        mega = doc["flags"][MODULE_ID]["mega"]
        description = fiu.mega_description(mega)
        before = json.dumps(doc, ensure_ascii=False, sort_keys=True)
        doc["system"]["description"]["value"] = description
        if json.dumps(doc, ensure_ascii=False, sort_keys=True) != before or not os.path.exists(path):
            fiu.save(path, doc)
            rewritten += 1

    print(f"{rewritten} pedras gravadas")
    for line in report:
        print(f"  {line}")
    if warnings:
        print(f"{len(warnings)} avisos: {warnings}")


if __name__ == "__main__":
    main()
