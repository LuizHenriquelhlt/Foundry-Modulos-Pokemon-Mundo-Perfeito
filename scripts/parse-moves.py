#!/usr/bin/env python3
"""
Fase 2 — parser da "Lista de Moves" completa (Livro de Regras, páginas 91-212).

Uso:
    python scripts/parse-moves.py "<caminho para a pasta com os PDFs>"

Gera um arquivo .json por Move em packs/_source/moves/, substituindo os 17
gerados à mão na Fase 0 (mesma fonte, mesmo formato — a Fase 0 serviu para
validar o pipeline; agora o parser cobre o livro inteiro).

Imprime um relatório final com contagem de Moves e uma lista de entradas
sinalizadas para revisão manual (campo ausente ou heurística de tipo/atributo
não reconhecida), em vez de arriscar dado errado silenciosamente.
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from pdf_text import extract_range, strip_noise  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "moves")

FIRST_PAGE = 91
LAST_PAGE = 212

TYPE_PT_TO_EN = {
    "normal": "normal", "fogo": "fire", "água": "water", "agua": "water",
    "elétrico": "electric", "eletrico": "electric", "grama": "grass", "gelo": "ice",
    "lutador": "fighting", "venenoso": "poison", "terrestre": "ground", "terra": "ground",
    "voador": "flying", "psíquico": "psychic", "psiquico": "psychic", "inseto": "bug",
    "pedra": "rock", "fantasma": "ghost", "dragão": "dragon", "dragao": "dragon",
    "sombrio": "dark", "aço": "steel", "aco": "steel", "fada": "fairy",
    "variável": "variable", "variavel": "variable"
}

# Correções pontuais verificadas manualmente contra pmp_regras_full.txt (extração pdftotext
# -layout, usada como fonte cruzada), para blocos onde o crédito de arte do pdfplumber
# sobrepôs um campo real ou onde o nome do Move não foi identificado corretamente.
FIELD_CORRECTIONS = {
    "Ember": {"duration": "Instantânea"},
    "Fairy Wind": {"duration": "Instantânea"},
    "Fire Pledge": {"activation": "1 ação"},
    "Fire Punch": {"pp": "10"},
    "Gust": {"duration": "Instantânea"},
    "Leaf Blade": {"power": "DES"},
    "Leer": {"power": "SAB/CAR"},
    "Pain Split": {"duration": "Instantânea"},
    "Psychic": {"duration": "Instantânea"},
    "Rapid Spin": {"duration": "Instantânea, Enquanto ativo"}
}

# Chave = tipo_idx (índice da linha "Tipo:" no array de linhas extraídas — estável entre
# execuções, já que não depende de qual heurística de nome disparou). Aplicado sempre por
# tipo_idx, não por nome adivinhado, para não ser contornado se uma heurística de fallback
# nova (ex.: nomes sem tradução dos suplementos de Gen 8/9) "acertar" um nome errado nesses
# blocos específicos antes da checagem de correção rodar.
NAME_CORRECTIONS_BY_TIPO_IDX = {
    4588: "Healing Wish",
    6942: "Overheat",
    8136: "Rest",
    10388: "Sweet Kiss"
}

ABILITY_ABBR_TO_KEY = {
    "for": "str", "des": "dex", "con": "con", "int": "int", "sab": "wis",
    "car": "cha", "cha": "cha", "nenhum": None
}

LABELS = ["Descrição", "Observações", "Níveis Superiores"]
LABEL_SPLIT_RE = re.compile(r"(Descrição|Observações|Níveis Superiores): ")

FIELD_LINE_RE = {
    "type": re.compile(r"^Tipo:\s*(.+)$"),
    "power": re.compile(r"^Poder do Move:\s*(.+)$"),
    "activation": re.compile(r"^Tempo de Execução:\s*(.+)$"),
    "pp": re.compile(r"^PP:\s*(.+)$"),
    "duration": re.compile(r"^Duração:\s*(.+)$"),
    "range": re.compile(r"^Alcance:\s*(.+)$")
}


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def map_type(raw):
    key = strip_accents_lower(raw.strip())
    return TYPE_PT_TO_EN.get(key)


def map_power_abilities(raw):
    raw = raw.strip()
    if strip_accents_lower(raw) == "nenhum":
        return []
    keys = []
    for part in re.split(r"\s*/\s*", raw):
        key = ABILITY_ABBR_TO_KEY.get(strip_accents_lower(part))
        if key:
            keys.append(key)
    return keys


def parse_range_meta(raw):
    melee = "corpo a corpo" in strip_accents_lower(raw)
    m = re.search(r"([\d,.]+)\s*metros", raw)
    meters = 0.0
    if m:
        try:
            meters = float(m.group(1).replace(",", "."))
        except ValueError:
            meters = 0.0
    return meters, melee


def find_move_headers(lines):
    """Retorna lista de (start_idx, name, warnings) para cada início de bloco de Move,
    ancorado em linhas 'Tipo:' (ver docstring do módulo pdf_text sobre por que este é
    o sinal mais confiável nesta formatação)."""
    headers = []
    for i, line in enumerate(lines):
        if not FIELD_LINE_RE["type"].match(line):
            continue
        name = None
        start = None
        warn = None
        if i >= 1 and re.match(r"^\(.+\)$", lines[i - 1]) and i >= 2:
            # formato de duas linhas: "Nome" / "(Tradução)"
            start = i - 2
            name = f"{lines[i - 2]} {lines[i - 1]}"
        elif i >= 1 and re.match(r"^.+ \(.+\)$", lines[i - 1]):
            # formato de uma linha: "Nome (Tradução)"
            start = i - 1
            name = lines[i - 1]
        elif i >= 1 and lines[i - 1].strip() and not lines[i - 1].rstrip().endswith((".", ",", ":", ";")) \
                and len(lines[i - 1]) <= 40 and not re.search(r"\d", lines[i - 1]):
            # formato sem tradução (comum nos suplementos de Gen 8/9): "Nome" puro antes de "Tipo:".
            # Exclui candidatos com dígitos — nomes de Move nunca têm números, mas handles de
            # artista órfãos às vezes têm (ex.: "3Paula3", "13alrog"), que é exatamente o tipo de
            # ruído que essa heurística poderia capturar por engano.
            start = i - 1
            name = lines[i - 1]
        else:
            start = i
            name = None
            warn = f"Nome do Move não identificado antes da linha 'Tipo:' #{i}: {lines[max(0, i - 2):i]}"
        headers.append({"start": start, "tipo_idx": i, "name": name, "warning": warn})
    return headers


def clean_move_name(raw_name):
    m = re.match(r"^(.+?)\s*\((.+)\)$", raw_name)
    if m:
        return m.group(1).strip()
    return raw_name.strip()


def parse_block(lines, header, block_end):
    warnings = []
    if header["warning"]:
        warnings.append(header["warning"])

    raw_name = header["name"] or f"MOVE_DESCONHECIDO_{header['tipo_idx']}"
    name = clean_move_name(raw_name)
    if header["tipo_idx"] in NAME_CORRECTIONS_BY_TIPO_IDX:
        corrected = NAME_CORRECTIONS_BY_TIPO_IDX[header["tipo_idx"]]
        warnings.append(f"nome na linha 'Tipo:' #{header['tipo_idx']} corrigido de '{name}' para '{corrected}'")
        name = corrected

    # Delimita a região onde os 6 campos fixos (Tipo..Alcance) devem estar: do "Tipo:" até a
    # primeira linha "Descrição:" do bloco. Dentro dessa janela, procura cada campo pelo rótulo
    # em vez de exigir adjacência estrita de linha — em alguns blocos um nome de artista órfão
    # (crédito de arte mal posicionado pelo pdfplumber) se intercala entre os campos fixos.
    desc_idx = None
    for j in range(header["tipo_idx"], block_end):
        if lines[j].startswith("Descrição:"):
            desc_idx = j
            break
    header_end = desc_idx if desc_idx is not None else block_end

    fields = {}
    search_from = header["tipo_idx"]
    for key in ["type", "power", "activation", "pp", "duration", "range"]:
        found = None
        for j in range(search_from, header_end):
            if m := FIELD_LINE_RE[key].match(lines[j]):
                found = (j, m.group(1).strip())
                break
        if found is None:
            warnings.append(f"{name}: campo '{key}' ausente (janela {search_from}-{header_end})")
            fields[key] = ""
            continue
        # créditos de arte às vezes colam no fim da linha do campo (ex.: "Instantânea Arte feita")
        fields[key] = re.sub(r"\s*Arte feita.*$", "", found[1]).strip()
        search_from = found[0] + 1

    if name in FIELD_CORRECTIONS:
        for key, value in FIELD_CORRECTIONS[name].items():
            fields[key] = value
            warnings.append(f"{name}: campo '{key}' preenchido manualmente ('{value}')")

    idx = desc_idx if desc_idx is not None else header_end
    remainder = " ".join(lines[idx:block_end]).strip()
    sections = {}
    if remainder:
        parts = LABEL_SPLIT_RE.split(remainder)
        # parts = ['', 'Descrição', 'texto...', 'Observações', 'texto...', ...]
        for j in range(1, len(parts), 2):
            label = parts[j]
            text = parts[j + 1].strip() if j + 1 < len(parts) else ""
            sections[label] = text
    else:
        warnings.append(f"{name}: sem Descrição/campos finais (bloco vazio)")

    if "Descrição" not in sections:
        warnings.append(f"{name}: sem seção 'Descrição' reconhecida")

    move_type = map_type(fields["type"]) if fields["type"] else None
    if fields["type"] and not move_type:
        warnings.append(f"{name}: tipo '{fields['type']}' não reconhecido")

    pp_unlimited = "ilimitado" in strip_accents_lower(fields.get("pp", ""))
    pp_match = re.search(r"\d+", fields["pp"]) if fields["pp"] else None
    pp_value = int(pp_match.group()) if pp_match else 0
    if fields["pp"] and not pp_match and not pp_unlimited:
        warnings.append(f"{name}: PP '{fields['pp']}' não é numérico")

    range_meters, melee = parse_range_meta(fields["range"]) if fields["range"] else (0.0, False)

    activation_type = "action"
    act_lower = strip_accents_lower(fields.get("activation", ""))
    if act_lower.startswith("1 reacao") or act_lower.startswith("1 reação"):
        activation_type = "reaction"
    elif "acao bonus" in act_lower or "ação bônus" in fields.get("activation", "").lower():
        activation_type = "bonus"

    priority = 1 if "prioridade 1" in strip_accents_lower(sections.get("Descrição", "")) else 0

    base_formula = ""
    scaling = []
    desc_text = sections.get("Descrição", "")
    # Formato de dano/cura no texto é sempre "<verbo> XdY + MOVE" (ex.: "causando 2d4 + MOVE de
    # dano", "recupera 1d6 + MOVE pontos de vida"). Deliberadamente NÃO inclui "Role"/"role", que
    # introduz a rolagem de ataque/resistência (ex.: "Role 1d20 + MOVE + 4"), não dano.
    dmg_match = re.search(
        r"\b(?:causando|causa|cause|sofrendo|sofre|sofrer|sofrem|recupera|recuperando|"
        r"recuperar|recupere|recebendo|recebe|restaura)\s+(\d+d\d+)\s*\+\s*MOVE",
        desc_text
    )
    if dmg_match:
        base_formula = dmg_match.group(1)

    higher_text = sections.get("Níveis Superiores", "")
    if higher_text:
        for lvl_match in re.finditer(r"(\d+d\d+)\s+no nível (\d+)", higher_text):
            scaling.append({"level": int(lvl_match.group(2)), "formula": lvl_match.group(1)})
        scaling.sort(key=lambda s: s["level"])

    system = {
        "moveType": move_type or "normal",
        "category": "",
        "power": fields["power"],
        "powerAbilities": map_power_abilities(fields["power"]) if fields["power"] else [],
        "activation": {"type": activation_type, "raw": fields["activation"]},
        "pp": {"value": pp_value, "max": pp_value, "unlimited": pp_unlimited},
        "duration": fields["duration"],
        "range": {"raw": fields["range"], "meters": range_meters, "melee": melee},
        "priority": priority,
        "description": f"<p>{sections.get('Descrição', '')}</p>" if sections.get("Descrição") else "",
        "higherLevels": f"<p>{higher_text}</p>" if higher_text else "",
        "observations": f"<p>{sections.get('Observações', '')}</p>" if sections.get("Observações") else "",
        "damage": {"baseFormula": base_formula, "scaling": scaling}
    }
    return name, system, warnings


def slugify(name):
    slug = strip_accents_lower(name)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug or "move"


def make_id(name, used_ids):
    import hashlib
    h = hashlib.sha1(name.encode("utf-8")).hexdigest()
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
        print("Uso: python scripts/parse-moves.py \"<pasta com os PDFs>\"")
        sys.exit(1)
    pdf_dir = sys.argv[1]
    pdf_path = os.path.join(pdf_dir, "Livro de Regras - Pokémon Mundo Perfeito (2).pdf")

    print(f"Extraindo páginas {FIRST_PAGE}-{LAST_PAGE} de {pdf_path} (column-aware)...")
    raw = extract_range(pdf_path, FIRST_PAGE, LAST_PAGE, n_columns=2)
    cleaned = strip_noise(raw)
    lines = [l for l in cleaned.split("\n") if l.strip()]

    headers = find_move_headers(lines)
    print(f"{len(headers)} blocos de Move identificados.")

    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))

    used_ids = set()
    all_warnings = []
    written = 0
    names_seen = {}

    for i, header in enumerate(headers):
        block_end = headers[i + 1]["start"] if i + 1 < len(headers) else len(lines)
        name, system, warnings = parse_block(lines, header, block_end)

        if name in names_seen:
            names_seen[name] += 1
            warnings.append(f"{name}: nome duplicado (ocorrência #{names_seen[name] + 1})")
        else:
            names_seen[name] = 1

        all_warnings.extend(warnings)

        doc_id = make_id(name + str(names_seen[name]), used_ids)
        doc = {
            "_id": doc_id,
            "name": name,
            "type": "pokemon-mundo-perfeito.move",
            "img": "icons/svg/item-bag.svg",
            "system": system,
            "effects": [],
            "folder": None,
            "flags": {},
            "_stats": {
                "coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                "compendiumSource": None, "duplicateSource": None
            },
            "sort": i * 10,
            "ownership": {"default": 0}
        }
        filename = f"{slugify(name)}.json" if names_seen[name] == 1 else f"{slugify(name)}-{names_seen[name]}.json"
        with open(os.path.join(OUT_DIR, filename), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        written += 1

    print(f"\n{written} Moves escritos em {OUT_DIR}")
    print(f"{len(all_warnings)} avisos para revisão manual:")
    for w in all_warnings[:80]:
        print(f"  - {w}")
    if len(all_warnings) > 80:
        print(f"  ... e mais {len(all_warnings) - 80} avisos (veja o log completo se necessário)")

    report_path = os.path.join(ROOT, "scripts", "parse-moves-report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(f"{written} Moves escritos.\n{len(all_warnings)} avisos:\n")
        for w in all_warnings:
            fh.write(f"- {w}\n")
    print(f"\nRelatório completo em {report_path}")


if __name__ == "__main__":
    main()
