#!/usr/bin/env python3
"""
Converte os compêndios para documentos NATIVOS do dnd5e (arquitetura do módulo
pokemon5e, que o usuário usou como referência visual): em vez de subtipos custom
("pokemon-mundo-perfeito.pokemon"/".move") com ficha própria — que renderizava uma
ficha AppV1 crua e datada —, os Pokémon viram Actors "npc" e os Moves viram Items
"feat" com Activities (dnd5e v4+). Assim tudo abre na ficha moderna do dnd5e, com
rolagem de ataque/dano/CD, PP como "usos", resistências/vulnerabilidades por tipo, etc.

Os dados PMP originais (moveTable, TMs, Egg Moves, SR, EVs...) são preservados em
flags["pokemon-mundo-perfeito"] de cada documento, e as tabelas viram HTML na
biografia para continuarem visíveis na ficha.

Roda EM CIMA dos JSONs já gerados pelos parsers (reescreve packs/_source/moves e
packs/_source/pokedex no lugar). Ordem do pipeline completo:
    parsers -> add-images.py -> convert-to-dnd5e-native.py -> npm run build:packs

Uso: python scripts/convert-to-dnd5e-native.py
"""
import glob
import hashlib
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "packs", "_source")

TYPE_LABELS = {
    "normal": "Normal", "fire": "Fogo", "water": "Água", "electric": "Elétrico",
    "grass": "Grama", "ice": "Gelo", "fighting": "Lutador", "poison": "Venenoso",
    "ground": "Terrestre", "flying": "Voador", "psychic": "Psíquico", "bug": "Inseto",
    "rock": "Pedra", "ghost": "Fantasma", "dragon": "Dragão", "dark": "Sombrio",
    "steel": "Aço", "fairy": "Fada"
}

# espelho de module/combat/type-chart.mjs (atacante -> {defensor: multiplicador})
EFFECTIVENESS = {
    "normal": {"rock": 0.5, "ghost": 0, "steel": 0.5},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 2, "bug": 2, "rock": 0.5, "dragon": 0.5, "steel": 2},
    "water": {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2, "rock": 2, "dragon": 0.5},
    "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2, "dragon": 0.5},
    "grass": {"fire": 0.5, "water": 2, "grass": 0.5, "poison": 0.5, "ground": 2, "flying": 0.5,
               "bug": 0.5, "rock": 2, "dragon": 0.5, "steel": 0.5},
    "ice": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 0.5, "ground": 2, "flying": 2, "dragon": 2, "steel": 0.5},
    "fighting": {"normal": 2, "ice": 2, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5,
                  "rock": 2, "ghost": 0, "dark": 2, "steel": 2, "fairy": 0.5},
    "poison": {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0, "fairy": 2},
    "ground": {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2, "flying": 0, "bug": 0.5, "rock": 2, "steel": 2},
    "flying": {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2, "rock": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2, "poison": 2, "psychic": 0.5, "dark": 0, "steel": 0.5},
    "bug": {"fire": 0.5, "grass": 2, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2,
             "ghost": 0.5, "dark": 2, "steel": 0.5, "fairy": 0.5},
    "rock": {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5, "flying": 2, "bug": 2, "steel": 0.5},
    "ghost": {"normal": 0, "psychic": 2, "ghost": 2, "dark": 0.5},
    "dragon": {"dragon": 2, "steel": 0.5, "fairy": 0},
    "dark": {"fighting": 0.5, "psychic": 2, "ghost": 2, "dark": 0.5, "fairy": 0.5},
    "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2, "rock": 2, "steel": 0.5, "fairy": 2},
    "fairy": {"fire": 0.5, "fighting": 2, "poison": 0.5, "dragon": 2, "dark": 2, "steel": 0.5}
}

SKILL_PT_TO_KEY = {
    "acrobacia": ("acr", "dex"), "adestrar animais": ("ani", "wis"), "arcanismo": ("arc", "int"),
    "atletismo": ("ath", "str"), "atuacao": ("prf", "cha"), "enganacao": ("dec", "cha"),
    "furtividade": ("ste", "dex"), "historia": ("his", "int"), "intimidacao": ("itm", "cha"),
    "intuicao": ("ins", "wis"), "investigacao": ("inv", "int"), "medicina": ("med", "wis"),
    "natureza": ("nat", "int"), "percepcao": ("prc", "wis"), "persuasao": ("per", "cha"),
    "prestidigitacao": ("slt", "dex"), "religiao": ("rel", "int"), "sobrevivencia": ("sur", "wis")
}

SIZE_TO_DND5E = {"tiny": "tiny", "small": "sm", "medium": "med", "large": "lg",
                  "huge": "huge", "gigantic": "grg"}

ABILITY_PT = {"FOR": "str", "DES": "dex", "CON": "con", "INT": "int", "SAB": "wis", "CAR": "cha"}


def strip_accents_lower(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


def save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Moves -> Items "feat" nativos com Activities
# ---------------------------------------------------------------------------

def build_move_activity(pmp, move_name):
    """Constrói uma Activity do dnd5e v4 a partir dos campos PMP do Move.
    Ataque ("Faça um ataque...") vira activity attack; teste de resistência vira save.
    O bônus de MOVE do PMP (melhor atributo + proficiência) equivale ao mod do
    atributo + proficiência do dnd5e, então @mod nas partes de dano e o cálculo
    padrão de acerto/CD reproduzem a matemática do livro."""
    desc_plain = re.sub(r"<[^>]+>", " ", pmp.get("description", ""))
    base = pmp.get("damage", {}).get("baseFormula", "")
    power_abilities = pmp.get("powerAbilities") or []
    ability = power_abilities[0] if power_abilities else ""

    activation_type = pmp.get("activation", {}).get("type", "action")
    if activation_type not in ("action", "bonus", "reaction"):
        activation_type = "action"

    m_dmg = re.match(r"(\d+)d(\d+)", base)
    damage_part = None
    if m_dmg:
        damage_part = {
            "number": int(m_dmg.group(1)),
            "denomination": int(m_dmg.group(2)),
            "bonus": "@mod" if ability else "",
            "types": []
        }

    is_attack = bool(re.search(r"[Ff]aça (?:um|até \w+ rolagens? de)? ?ataque", desc_plain))
    m_save = re.search(r"teste (?:de resistência )?de (FOR|DES|CON|INT|SAB|CAR)", desc_plain)

    uses_pp = pmp.get("pp", {})
    consumption = {"targets": [], "scaling": {"allowed": False, "max": ""}, "spellSlot": True}
    if uses_pp.get("max") and not uses_pp.get("unlimited"):
        consumption["targets"] = [{"type": "itemUses", "target": "", "value": "1", "scaling": {"mode": "", "formula": ""}}]

    activity_id = make_id(f"activity-{move_name}")
    common = {
        "_id": activity_id,
        "name": "",
        "activation": {"type": activation_type, "value": None, "condition": "", "override": False},
        "consumption": consumption,
        "description": {"chatFlavor": ""},
        "duration": {"units": "inst", "concentration": False, "override": False},
        "range": {"override": False},
        "target": {"override": False}
    }

    if is_attack and damage_part:
        melee = pmp.get("range", {}).get("melee", False)
        return {activity_id: {
            **common,
            "type": "attack",
            "attack": {
                "ability": ability,
                "bonus": "",
                "critical": {"threshold": None},
                "flat": False,
                "type": {"value": "melee" if melee else "ranged", "classification": "weapon"}
            },
            "damage": {"critical": {"bonus": ""}, "includeBase": False,
                        "parts": [damage_part] if damage_part else []}
        }}

    if m_save:
        save_ability = ABILITY_PT.get(m_save.group(1), "dex")
        on_save = "half" if re.search(r"metade d", desc_plain) else "none"
        act = {
            **common,
            "type": "save",
            "save": {
                "ability": [save_ability],
                "dc": {"calculation": ability or "str", "formula": ""}
            },
            "damage": {"onSave": on_save, "parts": [damage_part] if damage_part else []}
        }
        return {activity_id: act}

    if damage_part:
        # dano sem rolagem de acerto nem save (ex.: acerto garantido) — activity de dano puro
        return {activity_id: {
            **common,
            "type": "damage",
            "damage": {"critical": {"allow": False, "bonus": ""}, "parts": [damage_part]}
        }}

    return {}


def move_description_html(pmp, name):
    parts = []
    header_bits = []
    mtype = pmp.get("moveType", "")
    if mtype:
        header_bits.append(f"<strong>Tipo:</strong> {TYPE_LABELS.get(mtype, mtype)}")
    if pmp.get("power"):
        header_bits.append(f"<strong>Poder do Move:</strong> {pmp['power']}")
    act_raw = pmp.get("activation", {}).get("raw", "")
    if act_raw:
        header_bits.append(f"<strong>Tempo de Execução:</strong> {act_raw}")
    pp = pmp.get("pp", {})
    pp_label = "Ilimitado" if pp.get("unlimited") else str(pp.get("max", ""))
    header_bits.append(f"<strong>PP:</strong> {pp_label}")
    if pmp.get("duration"):
        header_bits.append(f"<strong>Duração:</strong> {pmp['duration']}")
    rng = pmp.get("range", {}).get("raw", "")
    if rng:
        header_bits.append(f"<strong>Alcance:</strong> {rng}")
    parts.append("<p>" + " &nbsp;•&nbsp; ".join(header_bits) + "</p>")

    if pmp.get("description"):
        parts.append(pmp["description"])
    if pmp.get("higherLevels"):
        parts.append(f"<p><strong>Níveis Superiores:</strong></p>{pmp['higherLevels']}")
    if pmp.get("observations"):
        parts.append(f"<p><strong>Observações:</strong></p>{pmp['observations']}")
    if pmp.get("zPowerEffect"):
        parts.append(f"<p><strong>Efeito de Poder-Z:</strong> {pmp['zPowerEffect']}</p>")
    return "".join(parts)


def convert_moves():
    n = 0
    for f in glob.glob(os.path.join(SRC, "moves", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if doc.get("type") == "feat":
            # já convertido: reconstrói a partir dos dados PMP preservados em flags
            pmp = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("move")
            if not pmp:
                continue
        else:
            pmp = doc["system"]
        name = doc["name"]

        pp = pmp.get("pp", {})
        uses = {"spent": 0, "max": "", "recovery": []}
        if pp.get("max") and not pp.get("unlimited"):
            uses = {"spent": 0, "max": str(pp["max"]),
                    "recovery": [{"period": "lr", "type": "recoverAll", "formula": ""}]}

        mtype = pmp.get("moveType", "")
        doc["type"] = "feat"
        doc["system"] = {
            "description": {"value": move_description_html(pmp, name), "chat": ""},
            "requirements": f"Move de Pokémon — Tipo {TYPE_LABELS.get(mtype, mtype)}",
            "type": {"value": "", "subtype": ""},
            "uses": uses,
            "activities": build_move_activity(pmp, name)
        }
        doc.setdefault("flags", {}).setdefault("pokemon-mundo-perfeito", {})["move"] = pmp
        save(f, doc)
        n += 1
    print(f"moves: {n} convertidos para Item 'feat' nativo com Activities")


# ---------------------------------------------------------------------------
# Pokédex -> Actors "npc" nativos
# ---------------------------------------------------------------------------

def type_defense_traits(type1, type2):
    di, dr, dv = [], [], []
    for attack in EFFECTIVENESS:
        m1 = EFFECTIVENESS[attack].get(type1, 1)
        m2 = EFFECTIVENESS[attack].get(type2, 1) if type2 else 1
        mult = m1 * m2
        label = f"Tipo {TYPE_LABELS[attack]}"
        if mult == 0:
            di.append(label)
        elif mult < 1:
            dr.append(label + (" (x1/4)" if mult == 0.25 else ""))
        elif mult > 1:
            dv.append(label + (" (x4)" if mult == 4 else ""))
    return di, dr, dv


def parse_movement(pmp):
    result = {"walk": pmp.get("movement", {}).get("walk", 9) or 0, "swim": 0, "fly": 0,
              "climb": 0, "burrow": 0, "hover": False, "units": "m"}
    other = pmp.get("movement", {}).get("other", "") or ""
    for m in re.finditer(r"([\d,.]+)\s*m de (caminhada|natação|nado|voo|vôo|escalada|escavação|flutuação)",
                          other, re.IGNORECASE):
        val = float(m.group(1).replace(",", "."))
        mode = strip_accents_lower(m.group(2))
        if mode == "caminhada":
            result["walk"] = val
        elif mode in ("natacao", "nado"):
            result["swim"] = val
        elif mode in ("voo",):
            result["fly"] = val
        elif mode == "escalada":
            result["climb"] = val
        elif mode == "escavacao":
            result["burrow"] = val
        elif mode == "flutuacao":
            result["fly"] = max(result["fly"], val)
            result["hover"] = True
    return result


def parse_senses(raw):
    senses = {"darkvision": 0, "blindsight": 0, "tremorsense": 0, "truesight": 0, "units": "m", "special": ""}
    if not raw:
        return senses
    if m := re.search(r"Visão no Escuro\s*([\d,.]+)\s*m", raw, re.IGNORECASE):
        senses["darkvision"] = float(m.group(1).replace(",", "."))
    if m := re.search(r"Visão Verdadeira\s*([\d,.]+)\s*m", raw, re.IGNORECASE):
        senses["truesight"] = float(m.group(1).replace(",", "."))
    if m := re.search(r"Visão às Cegas\s*([\d,.]+)\s*m", raw, re.IGNORECASE):
        senses["blindsight"] = float(m.group(1).replace(",", "."))
    if m := re.search(r"Sentido Sísmico\s*([\d,.]+)\s*m", raw, re.IGNORECASE):
        senses["tremorsense"] = float(m.group(1).replace(",", "."))
    return senses


def skills_object(skill_names):
    skills = {}
    names = [strip_accents_lower(s) for s in skill_names]
    if any(n == "todas" for n in names):
        for key, abil in SKILL_PT_TO_KEY.values():
            skills[key] = {"value": 1, "ability": abil}
        return skills
    for n in names:
        entry = SKILL_PT_TO_KEY.get(n)
        if entry:
            skills[entry[0]] = {"value": 1, "ability": entry[1]}
    return skills


def feat_stub(item_id, name, description, img):
    return {
        "_id": item_id, "name": name, "type": "feat", "img": img,
        "system": {"description": {"value": description, "chat": ""},
                    "type": {"value": "", "subtype": ""}, "requirements": "",
                    "uses": {"spent": 0, "max": "", "recovery": []}, "activities": {}},
        "effects": [], "flags": {}, "sort": 0
    }


def biography_html(pmp, name):
    parts = []
    if pmp.get("biography"):
        parts.append(pmp["biography"])

    info = []
    sr = pmp.get("speciesRank", {}).get("display", "")
    if sr:
        info.append(f"<strong>SR:</strong> {sr}")
    info.append(f"<strong>Nível Mínimo Encontrado:</strong> {pmp.get('minLevelFound', 1)}")
    egg = ", ".join(pmp.get("eggGroups") or []) or "Não Descoberto"
    info.append(f"<strong>Grupo de Ovos:</strong> {egg}")
    g = pmp.get("gender", {})
    gender = "Sem gênero" if g.get("genderless") else f"{g.get('malePercent', 50)}% M / {g.get('femalePercent', 50)}% F"
    info.append(f"<strong>Gênero:</strong> {gender}")
    stage = pmp.get("evolutionStage", {})
    info.append(f"<strong>Estágio Evolutivo:</strong> {stage.get('current', 1)}/{stage.get('max', 1)}")
    parts.append("<p>" + " &nbsp;•&nbsp; ".join(info) + "</p>")

    if pmp.get("evolution"):
        parts.append(f"<p><strong>Evolução:</strong> {pmp['evolution']}</p>")

    table = pmp.get("moveTable") or []
    if table:
        rows = "".join(f"<tr><td style='text-align:center'>{r['level']}</td><td>{', '.join(r['moves'])}</td></tr>"
                        for r in table)
        parts.append("<h3>Moves por Nível</h3><table><thead><tr><th>Nível</th><th>Moves adquiridos"
                      "</th></tr></thead><tbody>" + rows + "</tbody></table>")

    if pmp.get("tms"):
        parts.append(f"<h3>TMs</h3><p>{', '.join(pmp['tms'])}</p>")
    if pmp.get("eggMoves"):
        parts.append(f"<h3>Egg Moves</h3><p>{', '.join(pmp['eggMoves'])}</p>")
    return "".join(parts)


def normalize_name(name):
    """Chave tolerante a ruído de extração: minúsculas, sem acento e só alfanumérico —
    casa 'Confu se Ray', 'Double- Edge', 'G ro wl', 'Land's/Land’s Wrath' etc."""
    return re.sub(r"[^a-z0-9]", "", strip_accents_lower(name))


def convert_pokedex():
    # índice dos Moves já convertidos, por nome exato e por chave normalizada
    moves_by_name = {}
    moves_by_norm = {}
    for f in glob.glob(os.path.join(SRC, "moves", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        moves_by_name[d["name"]] = d
        moves_by_norm[normalize_name(d["name"])] = d

    tm_sprite = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/tm-{t}.png"
    n = 0
    missing_moves = set()
    for f in glob.glob(os.path.join(SRC, "pokedex", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        if doc.get("type") == "npc":
            # já convertido: reconstrói a partir dos dados PMP preservados em flags
            pmp = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("species")
            if not pmp:
                continue
        else:
            pmp = doc["system"]
        name = doc["name"]

        type1 = pmp["types"].get("type1") or "normal"
        type2 = pmp["types"].get("type2")
        di, dr, dv = type_defense_traits(type1, type2)

        sr_value = pmp.get("speciesRank", {}).get("value", 0) or 0
        cr = min(max(sr_value, 0), 30)

        level = pmp.get("level") or pmp.get("minLevelFound", 1)

        embedded = []
        for t in [type1] + ([type2] if type2 else []):
            embedded.append(feat_stub(
                make_id(f"{name}-tipo-{t}"), f"Tipo {TYPE_LABELS.get(t, t)}",
                f"<p>Este Pokémon é do tipo {TYPE_LABELS.get(t, t)}.</p>", tm_sprite.format(t=t)))

        passive = pmp.get("passiveAbility", {}).get("active", "")
        if passive:
            embedded.append(feat_stub(
                make_id(f"{name}-passiva-{passive}"), f"Habilidade Passiva: {passive}",
                "<p>Veja a Lista de Habilidades Passivas no Livro de Regras.</p>",
                "icons/svg/aura.svg"))
        hidden = pmp.get("hiddenAbility", "")
        if hidden:
            embedded.append(feat_stub(
                make_id(f"{name}-oculta-{hidden}"), f"Habilidade Oculta: {hidden}",
                "<p>Habilidade Oculta — normalmente inativa; veja o Livro de Regras.</p>",
                "icons/svg/mystery-man.svg"))

        known = []
        for row in pmp.get("moveTable") or []:
            if row["level"] <= level:
                known.extend(row["moves"])
        if not known and (pmp.get("moveTable") or []):
            known = pmp["moveTable"][0]["moves"]
        known.append("Struggle")  # todo Pokémon conhece Struggle (Livro de Regras)

        seen = set()
        for move_name in known:
            if move_name in seen:
                continue
            seen.add(move_name)
            src_move = moves_by_name.get(move_name) or moves_by_norm.get(normalize_name(move_name))
            if not src_move:
                missing_moves.add(move_name)
                continue
            embed = {k: v for k, v in src_move.items()
                     if k in ("_id", "name", "type", "img", "system", "effects", "flags")}
            embed["sort"] = 100
            embedded.append(embed)

        doc["type"] = "npc"
        doc["system"] = {
            "abilities": {k: {"value": v.get("value", 10)} for k, v in pmp["abilities"].items()},
            "attributes": {
                "ac": {"flat": pmp.get("armorClass", {}).get("value", 10), "calc": "flat"},
                "hp": {"value": pmp.get("hitPoints", {}).get("max", 1),
                        "max": pmp.get("hitPoints", {}).get("max", 1), "temp": 0, "tempmax": 0,
                        "formula": ""},
                "movement": parse_movement(pmp),
                "senses": parse_senses(pmp.get("senses", ""))
            },
            "details": {
                "cr": cr,
                "type": {"value": "custom", "subtype": "", "custom": "Pokémon"},
                "biography": {"value": biography_html(pmp, name), "public": ""},
                "alignment": ""
            },
            "traits": {
                "size": SIZE_TO_DND5E.get(pmp.get("size", "medium"), "med"),
                "di": {"value": [], "custom": "; ".join(di)},
                "dr": {"value": [], "custom": "; ".join(dr)},
                "dv": {"value": [], "custom": "; ".join(dv)},
                "languages": {"value": [], "custom": ""}
            },
            "skills": skills_object(pmp.get("skills") or [])
        }
        # o compilePack do foundryvtt-cli exige _key também nos documentos embutidos,
        # no formato hierárquico "!actors.items!<actorId>.<itemId>"
        actor_id = doc["_id"]
        for item in embedded:
            item["_key"] = f"!actors.items!{actor_id}.{item['_id']}"
        doc["items"] = embedded
        doc.setdefault("flags", {}).setdefault("pokemon-mundo-perfeito", {})["species"] = pmp
        save(f, doc)
        n += 1

    print(f"pokedex: {n} espécies convertidas para Actor 'npc' nativo")
    if missing_moves:
        print(f"{len(missing_moves)} nomes de Move citados em moveTable sem entrada no compêndio "
              f"(mantidos só na tabela da biografia): {sorted(missing_moves)[:15]}...")


def main():
    convert_moves()
    convert_pokedex()


if __name__ == "__main__":
    main()
