#!/usr/bin/env python3
"""
Fase 4 (parte 1) — Lista de Mega Evoluções (Livro de Mega Evoluções, páginas 7-39).
Cada entrada: nome da Mega Pedra, frase fixa "Permite que <Espécie> Mega Evolua para
<Mega Forma> enquanto estiver segurando esta pedra.", lista de bullets com os
benefícios (habilidade, CA, atributos, tipo, tamanho, deslocamento), texto de sabor.

As Mega Evoluções alteram estatísticas por DELTA (+N), não valor absoluto — diferente
do que module/combat/mega-evolution.mjs assumia na Fase 0 (a função foi corrigida
nesta fase para aplicar deltas de CA/atributos e manter tipo/habilidade/tamanho como
overrides absolutos, exatamente como o livro descreve cada um).

Uso: python scripts/parse-mega-evolutions.py "<pasta com os PDFs>"
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from pdf_text import extract_range, strip_noise  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "mega-evolutions")

FIRST_PAGE, LAST_PAGE = 7, 39

TYPE_PT_TO_EN = {
    "normal": "normal", "fogo": "fire", "água": "water", "agua": "water",
    "elétrico": "electric", "eletrico": "electric", "grama": "grass", "gelo": "ice",
    "lutador": "fighting", "venenoso": "poison", "terrestre": "ground", "terra": "ground",
    "voador": "flying", "psíquico": "psychic", "psiquico": "psychic", "inseto": "bug",
    "pedra": "rock", "fantasma": "ghost", "dragão": "dragon", "dragao": "dragon",
    "sombrio": "dark", "aço": "steel", "aco": "steel", "fada": "fairy"
}
SIZE_PT_TO_EN = {
    "miúdo": "tiny", "miudo": "tiny", "minúsculo": "tiny", "minusculo": "tiny",
    "pequeno": "small", "médio": "medium", "medio": "medium",
    "grande": "large", "enorme": "huge", "gigantesco": "gigantic", "imenso": "gigantic"
}
ABILITY_PT_TO_KEY = {
    "forca": "str", "destreza": "dex", "constituicao": "con",
    "inteligencia": "int", "sabedoria": "wis", "carisma": "cha"
}

ANCHOR_RE = re.compile(r"^Permite que (.+?) Mega Evolua para (.+?) enquanto estiver segurando esta pedra\.")
BULLET_ABILITY_RE = re.compile(r"^Sua habilidade passiva muda para (.+)$")
BULLET_TYPE_RE = re.compile(r"^Seu tipo muda para (.+)$")
BULLET_SIZE_RE = re.compile(r"^Seu tamanho muda para (.+)$")
BULLET_CA_RE = re.compile(r"^([+-]\d+) na CA$")
BULLET_MOVE_BONUS_RE = re.compile(r"^([+-]\d+) pés? \([\d,.-]+ metros?\) em todos os seus deslocamentos$")
BULLET_MOVE_GRANT_RE = re.compile(r"^Ganha deslocamento de (.+?) igual ao? de (.+)$")
BULLET_ABILITY_SCORE_RE = re.compile(
    r"^([+-]\d+) n[ao]s? (\w+)(?:\s+ou\s+n[ao]s?\s+(\w+))?(\s*\(à escolha do jogador\))?$"
)


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def parse_bullet(line, result, warnings, stone_name):
    line = line.strip().lstrip("•").strip()
    line = line.replace("m uda", "muda")  # quirk pontual de extração ("Pinsirite")
    if m := BULLET_ABILITY_RE.match(line):
        result["passiveAbility"] = m.group(1).strip()
        return
    if m := BULLET_TYPE_RE.match(line):
        type_text = re.sub(r"\s*\([^)]*\)\s*$", "", m.group(1)).strip()  # ex.: "(perde o tipo Pedra)"
        parts = [p.strip() for p in re.split(r"/", type_text)]
        type1 = TYPE_PT_TO_EN.get(strip_accents_lower(parts[0]))
        type2 = TYPE_PT_TO_EN.get(strip_accents_lower(parts[1])) if len(parts) > 1 else None
        if not type1:
            warnings.append(f"{stone_name}: tipo '{parts[0]}' não reconhecido")
        result["types"] = {"type1": type1, "type2": type2}
        return
    if m := BULLET_SIZE_RE.match(line):
        size = SIZE_PT_TO_EN.get(strip_accents_lower(m.group(1).strip()))
        if not size:
            warnings.append(f"{stone_name}: tamanho '{m.group(1)}' não reconhecido")
        result["size"] = size
        return
    if m := BULLET_CA_RE.match(line):
        result["armorClassDelta"] = int(m.group(1))
        return
    if m := BULLET_MOVE_BONUS_RE.match(line):
        result["movementBonusFeet"] = int(m.group(1))
        return
    if m := BULLET_MOVE_GRANT_RE.match(line):
        result["movementGrants"].append({"type": m.group(1).strip(), "equalTo": m.group(2).strip()})
        return
    if m := BULLET_ABILITY_SCORE_RE.match(line):
        delta = int(m.group(1))
        key1 = ABILITY_PT_TO_KEY.get(strip_accents_lower(m.group(2)))
        key2 = ABILITY_PT_TO_KEY.get(strip_accents_lower(m.group(3))) if m.group(3) else None
        if not key1:
            warnings.append(f"{stone_name}: atributo '{m.group(2)}' não reconhecido em '{line}'")
            return
        if key2:
            result["abilityChoices"].append({"options": [key1, key2], "delta": delta})
        else:
            result["abilityDeltas"][key1] = result["abilityDeltas"].get(key1, 0) + delta
        return
    # bullet fora dos padrões comuns (ex.: retenção condicional de habilidade, deslocamento
    # reduzido pela metade) — preserva o texto bruto em vez de descartar a informação.
    result["otherEffects"].append(line)
    warnings.append(f"{stone_name}: bullet incomum preservado em otherEffects: '{line}'")


def base_item(doc_id, name, item_type, system, img="icons/svg/upgrade.svg"):
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
    return re.sub(r"[^a-z0-9]+", "-", strip_accents_lower(name)).strip("-")


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-mega-evolutions.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Mega Evoluções - Pokémon Mundo Perfeito.pdf")

    raw = extract_range(pdf_path, FIRST_PAGE, LAST_PAGE, n_columns=2)
    lines = [l for l in strip_noise(raw).split("\n") if l.strip()]

    # A frase-âncora "Permite que X Mega Evolua para Y enquanto estiver segurando esta
    # pedra." quebra em 2 linhas no layout do livro — testa a linha atual unida à próxima.
    anchors = []
    consumed_next = set()
    for i, line in enumerate(lines):
        if i in consumed_next:
            continue
        joined = line.strip() + " " + (lines[i + 1].strip() if i + 1 < len(lines) else "")
        m = ANCHOR_RE.match(line.strip()) or ANCHOR_RE.match(joined)
        if m:
            stone_idx = i - 1 if i >= 1 else i
            anchor_idx = i
            if not ANCHOR_RE.match(line.strip()):
                consumed_next.add(i + 1)
                anchor_idx = i + 1  # corpo do bloco começa depois da 2ª linha da frase-âncora
            anchors.append({"anchor_idx": anchor_idx, "stone_idx": stone_idx, "match": m})

    print(f"{len(anchors)} Mega Evoluções identificadas.")

    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))

    used_ids = set()
    all_warnings = []
    written = 0

    for i, a in enumerate(anchors):
        stone_name = lines[a["stone_idx"]].strip()
        species, mega_form = a["match"].group(1).strip(), a["match"].group(2).strip()

        block_end = anchors[i + 1]["stone_idx"] if i + 1 < len(anchors) else len(lines)
        body_lines = lines[a["anchor_idx"] + 1:block_end]

        result = {"abilityDeltas": {}, "abilityChoices": [], "movementGrants": [], "otherEffects": []}
        flavor_lines = []
        in_bullets = True
        for line in body_lines:
            stripped = line.strip()
            if not stripped or re.match(r"^Ao Mega Evoluir,.*benef[ií]cios:?$", stripped):
                continue  # frase de transição fixa antes dos bullets
            if stripped.startswith("•"):
                parse_bullet(stripped, result, all_warnings, stone_name)
                in_bullets = True
            elif in_bullets and not flavor_lines and re.match(r"^(Sua|Seu|\+\d|-\d|Ganha)", stripped):
                # bullet cuja marcador "•" ficou em linha própria por causa da coluna
                parse_bullet(stripped, result, all_warnings, stone_name)
            else:
                in_bullets = False
                flavor_lines.append(stripped)

        flavor = " ".join(flavor_lines).strip()

        system = {
            "stoneName": stone_name,
            "species": species,
            "megaForm": mega_form,
            "types": result.get("types", {"type1": None, "type2": None}),
            "size": result.get("size"),
            "armorClassDelta": result.get("armorClassDelta", 0),
            "abilityDeltas": result["abilityDeltas"],
            "abilityChoices": result["abilityChoices"],
            "passiveAbility": result.get("passiveAbility", ""),
            "movementBonusFeet": result.get("movementBonusFeet", 0),
            "movementGrants": result["movementGrants"],
            "otherEffects": result["otherEffects"],
            "description": f"<p>{flavor}</p>" if flavor else ""
        }
        doc = base_item(make_id(f"mega-{stone_name}", used_ids), stone_name, "equipment", system)
        doc["flags"] = {"pokemon-mundo-perfeito": {"category": "mega-stone", "species": species,
                                                     "megaForm": mega_form}}
        with open(os.path.join(OUT_DIR, f"{slugify(stone_name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1

    print(f"{written} Mega Evoluções escritas em {OUT_DIR}")
    print(f"{len(all_warnings)} avisos:")
    for w in all_warnings[:60]:
        print(f"  - {w}")
    if len(all_warnings) > 60:
        print(f"  ... e mais {len(all_warnings) - 60}")


if __name__ == "__main__":
    main()
