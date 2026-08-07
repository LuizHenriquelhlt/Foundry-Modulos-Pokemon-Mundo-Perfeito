#!/usr/bin/env python3
"""
Fase 3 — parser da Pokédex completa (Livro dos Pokémon, 596 páginas, ~2 espécies por
página em 2 colunas). Usa a mesma extração column-aware (pdfplumber) da Fase 2.

Uso:
    python scripts/parse-pokedex.py "<caminho para a pasta com os PDFs>"

Gera um .json por espécie em packs/_source/pokedex/, no schema do PokemonData
(module/data/pokemon-actor.mjs). Não tenta ler a linha "Defesas de Tipo:" do livro —
esses multiplicadores são derivados em runtime a partir de Tipo 1/Tipo 2 pelo
module/combat/type-chart.mjs, então a coluna de ícones de tipo (sem texto, portanto
não extraível de forma confiável) é dispensável.
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from pdf_text import extract_range, strip_noise  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "pokedex")

FIRST_PAGE = 1
LAST_PAGE = 596

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
    "grande": "large", "enorme": "huge", "gigantesco": "gigantic", "colossal": "gigantic"
}

HEADER_RE = re.compile(r"^(.*)#(\d{3,4})$")
FIELD_RE = {
    "type": re.compile(r"^Tipo:\s*(.+)$"),
    "sr": re.compile(r"^SR:\s*(.+)$"),
    "size": re.compile(r"^Tamanho:\s*(.+)$"),
    "minlevel": re.compile(r"^Nível Mínimo Encontrado:\s*(.+)$"),
    # algumas formas alternativas (ex.: Tatsugiri Forma Caída/Esticada) têm o campo em branco
    "egggroup": re.compile(r"^Grupo de Ovos:\s*(.*)$"),
    "gender": re.compile(r"^Gênero:\s*(.+)$"),
    "evostage": re.compile(r"^Estágio Evolutivo:\s*(.+)$"),
    "ca": re.compile(r"^CA:\s*(.+)$"),
    # "Dado de Vida" normalmente é "dN", mas Shedinja usa "—" (PV sempre fixo em 1, sem
    # progressão de dado de vida — referência à mecânica clássica do Shedinja nos jogos).
    "hp": re.compile(r"^Pontos de Vida:\s*(\d+)\s*\|\s*Dado de Vida:\s*(d\d+|—|-)"),
    "movement": re.compile(r"^Deslocamento:\s*(.+)$"),
    "abilities_header": re.compile(r"^FOR\s+DES\s+CON\s+INT\s+SAB\s+CHA$"),
    "skills": re.compile(r"^Perícias:\s*(.+)$"),
    "passive": re.compile(r"^Habilidade Passiva:\s*(.+)$"),
    "hidden": re.compile(r"^Habilidade Oculta:\s*(.+)$"),
    "senses": re.compile(r"^Sentidos:\s*(.+)$"),
    "evolution": re.compile(r"^Evolução:\s*(.+)$"),
    "movetable_header": re.compile(r"^Nível\s+Moves adquiridos em cada nível$"),
    "tms": re.compile(r"^TMs:\s*(.*)$"),
    "eggmoves": re.compile(r"^Egg Moves:\s*(.*)$"),
    "typedefense": re.compile(r"^Defesas de Tipo:")
}
# Correções pontuais verificadas manualmente contra a extração por posição de palavra
# (pdfplumber word-level), para blocos com quirks de layout do PDF que a extração
# column-aware por si só não resolve de forma genérica:
#  - Arceus: os 2 atributos com valor 30 (o único Pokémon com atributo 30 no livro) quebram
#    em 3 linhas ("30 30" / "25 (+7) x4" / "(+10) (+10)"), fora do padrão de 1 linha único.
#  - Munna: a 1ª linha do parágrafo de TMs usa espaçamento de caractere esticado no PDF
#    (efeito de justificação), tornando "TMs: After You, Ally Switch, ..." em
#    "T M s : A ft e r Y o u , A l ly S w i tc h , ..." — persiste em qualquer x_tolerance
#    do pdfplumber porque é a geometria real do PDF, não um artefato de agrupamento.
SPECIES_CORRECTIONS = {
    ("Arceus", 493): {
        "abilities": {"str": 30, "dex": 30, "con": 25, "int": 25, "wis": 25, "cha": 25}
    },
    ("Munna", 517): {
        "tms": [
            "After You", "Ally Switch", "Attract", "Calm Mind", "Charge Beam", "Confide",
            "Dazzling Gleam", "Double Team", "Dream Eater", "Energy Ball", "Expanding Force",
            "Facade", "Frustration", "Gravity", "Guard Swap", "Gyro Ball", "Heal Bell",
            "Helping Hand", "Hidden Power", "Imprison", "Light Screen", "Magic Coat",
            "Pain Split", "Power Swap", "Protect", "Psych Up", "Psychic", "Psyshock",
            "Rain Dance", "Reflect", "Rest", "Return", "Rock Slide", "Rock Tomb", "Round",
            "Safeguard", "Shadow Ball", "Shock Wave", "Signal Beam", "Skill Swap",
            "Sleep Talk", "Snore", "Substitute", "Swagger", "Swift", "Telekinesis",
            "Thunder Wave", "Torment", "Toxic", "Trick", "Trick Room", "Wonder Room",
            "Worry Seed", "Zen Headbutt"
        ],
        "eggMoves": [
            "Barrier", "Baton Pass", "Curse", "Healing Wish", "Helping Hand", "Magic Coat",
            "Secret Power", "Sleep Talk", "Sonic Boom", "Swift"
        ]
    }
}

ABILITY_LINE_RE = re.compile(r"(\d+)\s*\(([+-]\d+)\)")
LEVEL_LINE_RE = re.compile(r"^(\d{1,2})\s+(.+)$")
BARE_LEVEL_RE = re.compile(r"^(\d{1,2})$")


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def find_species_headers(lines):
    """Âncoras em linhas terminadas em '#DDDD' (número da Pokédex). A fusão de nomes
    quebrados em duas linhas (ex.: formas alternativas) acontece em merge_two_line_names."""
    headers = []
    for i, line in enumerate(lines):
        m = HEADER_RE.match(line)
        if not m:
            continue
        headers.append({"idx": i, "name_raw": m.group(1).strip(), "dex": m.group(2)})
    return headers


NAME_CONTINUATION_RE = re.compile(r"^[A-Za-zÀ-ÿ' -]+$")


def merge_two_line_names(lines, headers):
    """Alguns nomes de forma alternativa quebram em duas linhas antes do '#dex'
    (ex.: 'Ogerpon Máscara' \\n 'Turquesa #1017'). Detecta e funde — mas só quando a
    linha anterior parece mesmo um fragmento de nome (só letras/espaço/hífen, poucas
    palavras), para não engolir a linha de multiplicadores de 'Defesas de Tipo:' da
    espécie anterior (ex.: 'x2 ½ ½ ¼ x2 ½ x2 x2 ½'), que não bate em nenhum FIELD_RE."""
    merged = []
    for h in headers:
        i = h["idx"]
        name = h["name_raw"]
        if i >= 1:
            prev = lines[i - 1].strip()
            looks_like_name = bool(NAME_CONTINUATION_RE.match(prev)) and 0 < len(prev.split()) <= 4
            if looks_like_name:
                name = f"{prev} {name}".strip()
                h = {**h, "start": i - 1}
        h.setdefault("start", i)
        h["name"] = re.sub(r"\s+", " ", name).strip()
        merged.append(h)
    return merged


def parse_ability_scores(line):
    pairs = ABILITY_LINE_RE.findall(line)
    keys = ["str", "dex", "con", "int", "wis", "cha"]
    return {keys[i]: int(pairs[i][0]) for i in range(min(6, len(pairs)))}


def parse_move_table(table_lines):
    """Constrói {nível: [moves]} lidando com o caso em que uma célula de nível quebra em
    2 linhas e o pdfplumber intercala o número do nível entre elas (ver docstring do
    módulo) — cada fragmento de texto é associado ao nível mais próximo (o 'nível ativo'
    mais recente; fragmentos antes do primeiro nível pertencem ao nível 1)."""
    table = {}
    order = []
    active_level = None
    pending_pretext = []

    def ensure(level):
        if level not in table:
            table[level] = []
            order.append(level)

    for raw in table_lines:
        line = raw.strip()
        if not line:
            continue
        m = LEVEL_LINE_RE.match(line)
        if m:
            level = int(m.group(1))
            content = m.group(2).strip()
            ensure(level)
            if pending_pretext:
                table[level].extend(pending_pretext)
                pending_pretext = []
            if content not in ("—", "-"):
                table[level].append(content)
            active_level = level
            continue
        m2 = BARE_LEVEL_RE.match(line)
        if m2:
            level = int(m2.group(1))
            ensure(level)
            if pending_pretext:
                table[level].extend(pending_pretext)
                pending_pretext = []
            active_level = level
            continue
        if line in ("—", "-"):
            continue
        # linha de texto puro (continuação de lista de moves)
        if active_level is not None:
            table[active_level].append(line)
        else:
            pending_pretext.append(line)

    result = []
    for level in order:
        moves_text = " ".join(table[level]).strip()
        if not moves_text:
            continue
        moves = [m.strip() for m in moves_text.split(",") if m.strip() and m.strip() != "—"]
        if moves:
            result.append({"level": level, "moves": moves})
    return result


def parse_species(lines, header, block_end, warnings_out):
    name = header["name"]
    dex = int(header["dex"])
    idx = header["idx"] + 1

    def find(key, end):
        nonlocal idx
        for j in range(idx, end):
            m = FIELD_RE[key].match(lines[j])
            if m:
                return j, (m.group(1).strip() if m.groups() else None)
        return None, None

    # bloco fixo inicial: type..evostage, todos numa janela curta antes do texto de sabor
    fixed = {}
    search_from = idx
    for key in ["type", "sr", "size", "minlevel", "egggroup", "gender", "evostage"]:
        j, val = find(key, min(block_end, search_from + 10))
        if j is None:
            warnings_out.append(f"{name} #{dex}: campo '{key}' não encontrado")
            fixed[key] = ""
            continue
        fixed[key] = val
        search_from = j + 1
    idx = search_from

    # texto de sabor: tudo até a linha "CA:"
    ca_idx, ca_val = find("ca", block_end)
    if ca_idx is None:
        warnings_out.append(f"{name} #{dex}: 'CA:' não encontrado")
        biography = " ".join(lines[idx:block_end]).strip()
        ca_val = ""
        idx = block_end
    else:
        biography = " ".join(lines[idx:ca_idx]).strip()
        idx = ca_idx + 1

    hp_idx, hp_m = None, None
    for j in range(idx, min(block_end, idx + 3)):
        m = FIELD_RE["hp"].match(lines[j])
        if m:
            hp_idx, hp_m = j, m
            break
    if hp_m:
        hp_value, hit_die = int(hp_m.group(1)), hp_m.group(2)
        idx = hp_idx + 1
    else:
        warnings_out.append(f"{name} #{dex}: 'Pontos de Vida' não encontrado")
        hp_value, hit_die = 1, "d6"

    move_idx, move_val = find("movement", min(block_end, idx + 3))
    if move_idx is not None:
        idx = move_idx + 1
    else:
        move_val = ""

    # linha de cabeçalho FOR DES CON INT SAB CHA + linha de valores
    abilities = {}
    for j in range(idx, min(block_end, idx + 4)):
        if FIELD_RE["abilities_header"].match(lines[j]):
            if j + 1 < block_end:
                abilities = parse_ability_scores(lines[j + 1])
                idx = j + 2
            break
    if not abilities:
        warnings_out.append(f"{name} #{dex}: linha de atributos não encontrada")
        abilities = {k: 10 for k in ["str", "dex", "con", "int", "wis", "cha"]}

    # bloco de campos opcionais em ordem flexível, até achar o cabeçalho da tabela de moves
    header_table_idx = None
    for j in range(idx, block_end):
        if FIELD_RE["movetable_header"].match(lines[j]):
            header_table_idx = j
            break
    scan_end = header_table_idx if header_table_idx is not None else block_end

    skills, passive, hidden, senses, evolution_lines = "", "", "", "", []
    j = idx
    while j < scan_end:
        line = lines[j]
        if m := FIELD_RE["skills"].match(line):
            skills = m.group(1).strip()
        elif m := FIELD_RE["passive"].match(line):
            passive = m.group(1).strip()
        elif m := FIELD_RE["hidden"].match(line):
            hidden = m.group(1).strip()
        elif m := FIELD_RE["senses"].match(line):
            senses = m.group(1).strip()
        elif m := FIELD_RE["evolution"].match(line):
            evolution_lines.append(m.group(1).strip())
        elif evolution_lines and not FIELD_RE["abilities_header"].match(line):
            # continuação multi-linha do texto de Evolução
            evolution_lines.append(line.strip())
        j += 1
    evolution = " ".join(evolution_lines).strip()

    move_table = []
    tms, egg_moves = [], []
    if header_table_idx is not None:
        tms_idx, _ = find("tms", block_end)
        table_end = tms_idx if tms_idx is not None else block_end
        move_table = parse_move_table(lines[header_table_idx + 1: table_end])

        if tms_idx is not None:
            eggmoves_idx, _ = find("eggmoves", block_end)
            typedef_idx = None
            for j in range(tms_idx, block_end):
                if FIELD_RE["typedefense"].match(lines[j]):
                    typedef_idx = j
                    break
            tms_end = eggmoves_idx if eggmoves_idx is not None else (typedef_idx or block_end)
            tms_text = " ".join(
                [FIELD_RE["tms"].match(lines[tms_idx]).group(1)] + lines[tms_idx + 1: tms_end]
            ).strip()
            tms = [m.strip() for m in tms_text.split(",") if m.strip()]

            if eggmoves_idx is not None:
                egg_end = typedef_idx if typedef_idx is not None else block_end
                egg_text = " ".join(
                    [FIELD_RE["eggmoves"].match(lines[eggmoves_idx]).group(1)] + lines[eggmoves_idx + 1: egg_end]
                ).strip()
                egg_moves = [m.strip() for m in egg_text.split(",") if m.strip()]
        else:
            warnings_out.append(f"{name} #{dex}: 'TMs:' não encontrado")
    else:
        warnings_out.append(f"{name} #{dex}: tabela de Moves não encontrada")

    # --- normalizações ---
    type_parts = [t.strip() for t in fixed["type"].split("/")]
    type1 = TYPE_PT_TO_EN.get(strip_accents_lower(type_parts[0]), None) if type_parts else None
    type2 = TYPE_PT_TO_EN.get(strip_accents_lower(type_parts[1]), None) if len(type_parts) > 1 else None
    if fixed["type"] and not type1:
        warnings_out.append(f"{name} #{dex}: tipo '{fixed['type']}' não reconhecido")

    sr_raw = fixed["sr"]
    if "/" in sr_raw:
        num, den = sr_raw.split("/")
        sr_value = float(num) / float(den)
    else:
        try:
            sr_value = float(sr_raw)
        except ValueError:
            sr_value = 0.0
            warnings_out.append(f"{name} #{dex}: SR '{sr_raw}' não numérico")

    size_m = re.match(r"^(.+?)\s*\(([\d,.]+)\s*m\)$", fixed["size"])
    size_word, height_m = "", 0.0
    if size_m:
        size_word = SIZE_PT_TO_EN.get(strip_accents_lower(size_m.group(1)), "medium")
        try:
            height_m = float(size_m.group(2).replace(",", "."))
        except ValueError:
            height_m = 0.0
    else:
        warnings_out.append(f"{name} #{dex}: Tamanho '{fixed['size']}' não reconhecido")

    try:
        min_level = int(re.search(r"\d+", fixed["minlevel"]).group())
    except (AttributeError, ValueError):
        min_level = 1
        warnings_out.append(f"{name} #{dex}: Nível Mínimo '{fixed['minlevel']}' inválido")

    egg_groups = [] if strip_accents_lower(fixed["egggroup"]) in ("nao descoberto", "não descoberto") \
        else [g.strip() for g in fixed["egggroup"].split(",") if g.strip()]

    gender_raw = fixed["gender"]
    genderless = "sem gênero" in strip_accents_lower(gender_raw) or "genderless" in strip_accents_lower(gender_raw)
    male_pct, female_pct = 50, 50
    gm = re.search(r"(\d+)%\s*M", gender_raw)
    gf = re.search(r"(\d+)%\s*F", gender_raw)
    if gm:
        male_pct = int(gm.group(1))
    if gf:
        female_pct = int(gf.group(1))

    stage_m = re.match(r"(\d+)/(\d+)", fixed["evostage"])
    evo_current, evo_max = (int(stage_m.group(1)), int(stage_m.group(2))) if stage_m else (1, 1)

    correction = SPECIES_CORRECTIONS.get((name, dex))
    if correction:
        if "abilities" in correction:
            abilities = correction["abilities"]
        if "tms" in correction:
            tms = correction["tms"]
        if "eggMoves" in correction:
            egg_moves = correction["eggMoves"]
        warnings_out.append(f"{name} #{dex}: dados corrigidos manualmente ({', '.join(correction)})")

    system = {
        "species": re.sub(r"[^a-z0-9]+", "-", strip_accents_lower(name)).strip("-"),
        "dexNumber": dex,
        "types": {"type1": type1 or "normal", "type2": type2},
        "speciesRank": {"value": sr_value, "display": sr_raw},
        "size": size_word or "medium",
        "heightMeters": height_m,
        "minLevelFound": min_level,
        "eggGroups": egg_groups,
        "gender": {"malePercent": male_pct, "femalePercent": female_pct, "genderless": genderless},
        "evolutionStage": {"current": evo_current, "max": evo_max},
        "evolution": evolution,
        "biography": f"<p>{biography}</p>" if biography else "",
        "abilities": {k: {"value": v} for k, v in abilities.items()},
        "skills": [s.strip() for s in skills.split(",") if s.strip()],
        "armorClass": {"value": int(re.search(r"\d+", ca_val).group()) if re.search(r"\d+", ca_val or "") else 10},
        "hitPoints": {"value": hp_value, "max": hp_value, "hitDie": hit_die},
        "movement": {"walk": (lambda m: int(m.group(1)) if m else 9)(re.search(r"(\d+)m", move_val or "")),
                     "other": move_val},
        "senses": senses,
        "passiveAbility": {"options": [passive] if passive else [], "active": passive},
        "hiddenAbility": hidden,
        "level": min_level,
        "moveTable": move_table,
        "knownMoves": [m["moves"][0] for m in move_table[:1]] and (move_table[0]["moves"][:4] if move_table else []),
        "tms": tms,
        "eggMoves": egg_moves,
        "typeDefenseOverrides": {},
        "nature": {"name": "", "increased": "", "decreased": ""},
        "loyalty": 0,
        "shiny": False,
        "evs": {k: 0 for k in ["str", "dex", "con", "int", "wis", "cha"]}
    }
    return name, dex, system


def slugify(name, dex):
    slug = strip_accents_lower(name)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return f"{slug}-{dex:04d}"


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


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/parse-pokedex.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro dos Pokémon - Pokémon Mundo Perfeito (1).pdf")

    print(f"Extraindo páginas {FIRST_PAGE}-{LAST_PAGE} de {pdf_path} (column-aware)...")
    raw = extract_range(pdf_path, FIRST_PAGE, LAST_PAGE, n_columns=2)
    cleaned = strip_noise(raw)
    lines = [l for l in cleaned.split("\n") if l.strip()]
    print(f"{len(lines)} linhas extraídas.")

    headers = find_species_headers(lines)
    headers = merge_two_line_names(lines, headers)
    print(f"{len(headers)} cabeçalhos de espécie identificados.")

    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))

    used_ids = set()
    all_warnings = []
    written = 0
    seen_dex = {}

    for i, header in enumerate(headers):
        block_start = header.get("start", header["idx"])
        block_end = headers[i + 1].get("start", headers[i + 1]["idx"]) if i + 1 < len(headers) else len(lines)
        try:
            name, dex, system = parse_species(lines, header, block_end, all_warnings)
        except Exception as e:
            all_warnings.append(f"ERRO em bloco #{i} (linha {block_start}): {e}")
            continue

        key = (name, dex)
        seen_dex[key] = seen_dex.get(key, 0) + 1
        if seen_dex[key] > 1:
            all_warnings.append(f"{name} #{dex}: nome+dex duplicado (ocorrência #{seen_dex[key]})")

        doc_id = make_id(f"{name}{dex}{seen_dex[key]}", used_ids)
        doc = {
            "_key": f"!actors!{doc_id}",
            "_id": doc_id,
            "name": name,
            "type": "pokemon-mundo-perfeito.pokemon",
            "img": "icons/svg/mystery-man.svg",
            "system": system,
            "effects": [],
            "folder": None,
            "flags": {},
            "_stats": {
                "coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                "compendiumSource": None, "duplicateSource": None
            },
            "sort": i * 10,
            "ownership": {"default": 0},
            "prototypeToken": {"name": name, "actorLink": False}
        }
        suffix = "" if seen_dex[key] == 1 else f"-{seen_dex[key]}"
        filename = f"{slugify(name, dex)}{suffix}.json"
        with open(os.path.join(OUT_DIR, filename), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1

    print(f"\n{written} espécies escritas em {OUT_DIR}")
    print(f"{len(all_warnings)} avisos para revisão manual.")
    report_path = os.path.join(ROOT, "scripts", "parse-pokedex-report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(f"{written} espécies escritas.\n{len(all_warnings)} avisos:\n")
        for w in all_warnings:
            fh.write(f"- {w}\n")
    print(f"Relatório completo em {report_path}")
    for w in all_warnings[:60]:
        print(f"  - {w}")
    if len(all_warnings) > 60:
        print(f"  ... e mais {len(all_warnings) - 60} (veja o relatório)")


if __name__ == "__main__":
    main()
