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

def damage_type_key(move_type):
    """"fire" -> "pmpFire": mesma chave que module/combat/type-chart.mjs registra em
    CONFIG.DND5E.damageTypes (prefixo "pmp" pra não colidir com os 3 tipos nativos do D&D
    que têm o mesmo nome — fire/poison/psychic). "" e "variable" (Judgment, Natural Gift —
    tipo depende do item segurado) não têm uma chave fixa, então ficam sem "types"."""
    if not move_type or move_type == "variable" or move_type not in TYPE_LABELS:
        return None
    return f"pmp{move_type[0].upper()}{move_type[1:]}"


# "Pessoal (raio de 20 pés / 6 metros)" / "... (cone de 30 pés / ...)" / "... (linha de 50 pés / ...)"
# — o único lugar onde a área de um Move de área fica registrada nos dados originais é essa
# frase solta dentro de "range.raw". "raio" sempre é centrado no próprio usuário (nunca um
# ponto à distância que o livro descreve), então mapeia pro tipo "radius" (Emanation) do
# dnd5e, não "circle" (que é uma área plantada num ponto escolhido) — confirmado no schema
# de CONFIG.DND5E.areaTargetTypes do próprio dnd5e. "cone"/"linha" mapeiam direto pros tipos
# "cone"/"line" nativos; "linha" não precisa de largura explícita (TargetField do dnd5e já
# preenche "width" com 5 pés sozinho quando o tipo pede largura e ela não veio definida).
AREA_SHAPE_MAP = {"raio": "radius", "cone": "cone", "linha": "line"}


def parse_area_template(pmp):
    raw = pmp.get("range", {}).get("raw", "")
    m = re.search(r"(raio|cone|linha) de (\d+)\s*p", raw, re.IGNORECASE)
    if not m:
        return None
    shape = m.group(1).lower()
    return {"type": AREA_SHAPE_MAP[shape], "size": m.group(2), "units": "ft"}


def build_move_activity(pmp, move_name):
    """Constrói as Activities do dnd5e v4 a partir dos campos PMP do Move.
    Ataque ("Faça um ataque...") ou a mecânica "Role 1d20 + MOVE + N e compare com a defesa do
    alvo" (usada pelos Moves de status de alvo único, ex. Attract/Thunder Wave/Toxic) viram
    activity attack — nesse sistema o atacante sempre rola o dado, mesmo em Moves de status.
    "Teste de X contra sua CD de Move" (o alvo que rola) vira activity save, com CD exposta.
    Alguns Moves (ex. Mud-Slap, Poison Fang, Nuzzle) têm as DUAS coisas: um ataque que causa
    dano no acerto e, separadamente, um teste de resistência do alvo para um efeito secundário
    (sem dano extra) — nesse caso o Move ganha duas Activities (attack + save), uma pra cada
    rolagem, em vez de perder uma delas. Status sem nenhuma rolagem (buffs em si mesmo, ex.
    Agility) vira activity utility (botão Usar), para nunca ficar sem nenhuma ação executável.
    O bônus de MOVE do PMP (melhor atributo + proficiência) equivale ao mod do atributo +
    proficiência do dnd5e. Quando o Move do livro aceita mais de um atributo (ex. FOR/DES),
    NÃO escolhemos automaticamente o maior — isso tirava a escolha do jogador. Em vez disso
    a Activity usa "@mod" (a referência do próprio dnd5e pro atributo configurado na
    Activity) tanto no ataque quanto no dano, e o campo "Ability" da Activity já vem
    preenchido com o primeiro atributo listado no livro — o jogador pode trocar esse campo
    (dropdown nativo do dnd5e, na própria ficha do Move) pra outro atributo válido a
    qualquer momento, e ataque/dano/CD acompanham a troca juntos."""
    desc_plain = re.sub(r"<[^>]+>", " ", pmp.get("description", ""))
    base = pmp.get("damage", {}).get("baseFormula", "")
    power_abilities = pmp.get("powerAbilities") or []
    ability = power_abilities[0] if power_abilities else ""
    melee = pmp.get("range", {}).get("melee", False)

    activation_type = pmp.get("activation", {}).get("type", "action")
    if activation_type not in ("action", "bonus", "reaction"):
        activation_type = "action"

    m_dmg = re.match(r"(\d+)d(\d+)", base)
    damage_part = None
    if m_dmg:
        dtype = damage_type_key(pmp.get("moveType"))
        # Só dado + modificador — sem STAB nem bônus de estágio embutidos na fórmula. O
        # jogador soma isso na hora de rolar, do jeito que preferir (o painel da ficha mostra
        # o estágio atual, e a Pokédex/o item "Aumento de STAB" mostram a tabela de STAB por
        # nível). Golpe "limpo" de propósito — nada escondido atrás de uma fórmula.
        damage_part = {
            "number": int(m_dmg.group(1)),
            "denomination": int(m_dmg.group(2)),
            "bonus": "@mod",
            "types": [dtype] if dtype else []
        }

    m_save = re.search(r"teste (?:de resistência )?de (FOR|DES|CON|INT|SAB|CAR)\s+contra sua CD",
                        desc_plain)
    m_roll_vs_defense = re.search(r"[Rr]ole 1d20\s*\+\s*MOVE(?:\s*\+\s*(\d+))?", desc_plain)
    is_attack_phrase = bool(re.search(r"[Ff]aça (?:um|até \w+ rolagens? de)? ?ataque", desc_plain))
    is_attack = is_attack_phrase or bool(m_roll_vs_defense) or (bool(damage_part) and not m_save)
    # ataque com efeito secundário: quando o próprio ataque já causa o dano, o save que
    # acompanha é só para o efeito extra (veneno/paralisia/agarrão/etc.), sem dano dele
    dual_attack_and_save = is_attack and m_save

    uses_pp = pmp.get("pp", {})
    consumption = {"targets": [], "scaling": {"allowed": False, "max": ""}, "spellSlot": True}
    if uses_pp.get("max") and not uses_pp.get("unlimited"):
        consumption["targets"] = [{"type": "itemUses", "target": "", "value": "1", "scaling": {"mode": "", "formula": ""}}]

    area = parse_area_template(pmp)

    def base_activity(suffix):
        target = {"override": True, "template": area} if area else {"override": False}
        return {
            "_id": make_id(f"activity-{move_name}-{suffix}"),
            "name": "",
            "activation": {"type": activation_type, "value": None, "condition": "", "override": False},
            "consumption": consumption,
            "description": {"chatFlavor": ""},
            "duration": {"units": "inst", "concentration": False, "override": False},
            "range": {"override": False},
            "target": target
        }

    def attack_activity():
        common = base_activity("attack" if dual_attack_and_save else "act")
        flat_bonus = str(m_roll_vs_defense.group(1)) if (m_roll_vs_defense and m_roll_vs_defense.group(1)) else ""
        return common["_id"], {
            **common,
            "type": "attack",
            "attack": {
                "ability": ability,
                "bonus": flat_bonus,
                "critical": {"threshold": None},
                "flat": False,
                "type": {"value": "melee" if melee else "ranged", "classification": "weapon"}
            },
            "damage": {"critical": {"bonus": ""}, "includeBase": False,
                        "parts": [damage_part] if damage_part else []}
        }

    def save_activity(include_damage):
        common = base_activity("save" if dual_attack_and_save else "act")
        save_ability = ABILITY_PT.get(m_save.group(1), "dex")
        on_save = "half" if re.search(r"metade d", desc_plain) else "none"
        dc = {"calculation": ability or "str", "formula": "", "bonus": ""}
        return common["_id"], {
            **common,
            "type": "save",
            "save": {
                "ability": [save_ability],
                "dc": dc
            },
            "damage": {"onSave": on_save, "parts": ([damage_part] if damage_part else []) if include_damage else []}
        }

    if dual_attack_and_save:
        aid, act = attack_activity()
        sid, sv = save_activity(include_damage=False)
        return {aid: act, sid: sv}

    if m_save:
        sid, sv = save_activity(include_damage=True)
        return {sid: sv}

    if is_attack:
        aid, act = attack_activity()
        return {aid: act}

    # Status sem nenhuma rolagem de acerto/resistência (ex.: buff em si mesmo) — ainda precisa de
    # uma ação executável na ficha, então vira utility (botão "Usar") em vez de ficar sem activity.
    common = base_activity("use")
    return {common["_id"]: {
        **common,
        "type": "utility",
        "roll": {"prompt": False, "visible": False}
    }}


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
        if os.path.basename(f).startswith("folder-"):
            continue
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


def meters_to_feet(m):
    """O livro dá o deslocamento só em metros, mas esses valores são a conversão métrica de
    incrementos de 5 pés do dnd5e (9m = 30pés, 1,5m = 5pés etc.), então arredondar pro múltiplo
    de 5 pés mais próximo reproduz o número "original" de forma confiável."""
    if not m:
        return 0
    return round((m * 3.28084) / 5) * 5


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
    for key in ("walk", "swim", "fly", "climb", "burrow"):
        result[key] = meters_to_feet(result[key])
    result["units"] = "ft"
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


# Tabela "Progressão de Níveis do Pokémon" (Livro de Regras): benefícios por nível.
# Chaves = slugs dos itens criados por seed-progression-features.py.
PROGRESSION_BY_LEVEL = {
    2: ["ponto-de-ev"],
    3: ["aumento-de-stab"],
    4: ["talento-de-pokemon", "ponto-de-ev"],
    5: ["aumento-de-proficiencia", "aumento-de-dano"],
    6: ["ponto-de-ev"],
    7: ["aumento-de-stab"],
    8: ["talento-de-pokemon", "ponto-de-ev"],
    9: ["aumento-de-proficiencia"],
    10: ["aumento-de-dano", "ponto-de-ev"],
    11: ["aumento-de-stab"],
    12: ["talento-de-pokemon", "ponto-de-ev"],
    13: ["aumento-de-proficiencia"],
    14: ["ponto-de-ev"],
    15: ["aumento-de-stab"],
    16: ["talento-de-pokemon", "ponto-de-ev"],
    17: ["aumento-de-proficiencia", "aumento-de-dano"],
    18: ["ponto-de-ev"],
    19: ["aumento-de-stab"],
    20: ["talento-de-pokemon", "ponto-de-ev"]
}



def build_class_item(species_name, hit_die, level, book_hp, con_mod, move_grants, progression_ids,
                      talento_ids):
    """Item de classe "<Espécie> Level" no padrão do módulo pokemon5e: dá o seletor de
    nível na ficha, proficiência automática (mesma progressão da tabela do PMP) e o fluxo
    de Avanço do dnd5e ao subir de nível. Além do avanço de PV, concede via ItemGrant os
    Moves da tabela da espécie e os benefícios de STAB/Proficiência/Dano da tabela de
    Progressão de Níveis do Pokémon nos níveis ainda não alcançados. Ponto de EV vira um
    Aumento de Valor de Atributo nativo (+1 ponto livre) e Talento de Pokémon vira uma
    escolha real (ItemChoice) dentre os Talentos do compêndio, em vez de placeholders."""
    die_size = int(hit_die.lstrip("d") or 6)
    avg = die_size // 2 + 1
    # PV derivado da classe (1º nível = dado cheio, demais = média), como o dnd5e calcula
    class_hp = die_size + avg * (level - 1)
    # hp.max funciona como bônus somado ao PV de classe + CON — calibrado para o total
    # bater exatamente com os PV do bloco de estatística do livro (técnica do pokemon5e)
    hp_bonus = book_hp - (class_hp + con_mod * level)

    hp_values = {"1": "max"}
    for lvl in range(2, level + 1):
        hp_values[str(lvl)] = "avg"

    advancement = [{
        "type": "HitPoints",
        "title": "Aumento de Pontos de Vida",
        "_id": make_id(f"{species_name}-adv-hp"),
        "configuration": {},
        "value": hp_values
    }]

    talento_choice_levels = {}
    for lvl in range(level + 1, 21):
        uuids = []
        for move_id in move_grants.get(lvl, []):
            uuids.append(f"Compendium.pokemon-mundo-perfeito.moves.Item.{move_id}")
        for slug in PROGRESSION_BY_LEVEL.get(lvl, []):
            if slug == "ponto-de-ev":
                advancement.append({
                    "type": "AbilityScoreImprovement",
                    "title": "Ponto de EV (+1 Atributo)",
                    "_id": make_id(f"{species_name}-adv-ev-{lvl}"),
                    "level": lvl,
                    "configuration": {"points": 1, "cap": 2, "fixed": {}, "locked": []},
                    "value": {}
                })
                continue
            if slug == "talento-de-pokemon":
                talento_choice_levels[str(lvl)] = {"count": 1, "replacement": False}
                continue
            uuids.append(f"Compendium.pokemon-mundo-perfeito.trainer-features.Item.{progression_ids[slug]}")
        if not uuids:
            continue
        advancement.append({
            "type": "ItemGrant",
            "title": f"Nível {lvl}: Moves e benefícios da tabela",
            "_id": make_id(f"{species_name}-adv-grant-{lvl}"),
            "level": lvl,
            "configuration": {
                "items": [{"uuid": u, "optional": False} for u in uuids],
                "optional": False,
                "spell": None
            },
            "value": {}
        })

    if talento_choice_levels:
        advancement.append({
            "type": "ItemChoice",
            "title": "Talento de Pokémon",
            "_id": make_id(f"{species_name}-adv-talento"),
            "configuration": {
                "allowDrops": True,
                "choices": talento_choice_levels,
                "pool": [
                    {"sort": i * 10000,
                     "uuid": f"Compendium.pokemon-mundo-perfeito.trainer-features.Item.{tid}"}
                    for i, tid in enumerate(talento_ids)
                ],
                "restriction": {"level": "", "list": [], "subtype": "", "type": "feat"},
                "sorting": "a",
                "spell": None,
                "type": "feat"
            },
            "value": {}
        })

    return {
        "_id": make_id(f"{species_name}-class"),
        "name": f"{species_name} Level",
        "type": "class",
        "img": "icons/svg/upgrade.svg",
        "system": {
            "hd": {"denomination": hit_die if hit_die.startswith("d") else "d6",
                    "additional": "", "spent": 0},
            "description": {
                "value": "<p><strong>Não remova esta classe da ficha.</strong> Ela controla o "
                          "nível do Pokémon: ao subir de nível, o dnd5e aplica o aumento de PV e "
                          "concede os Moves da tabela da espécie e os benefícios da tabela de "
                          "Progressão de Níveis do Pokémon (Ponto de EV, Aumento de STAB, Talento, "
                          "Aumento de Proficiência/Dano) automaticamente.</p>",
                "chat": ""
            },
            "advancement": advancement,
            "levels": level,
            "identifier": "",
            "startingEquipment": [],
            "primaryAbility": {"value": [], "all": True},
            "spellcasting": {"progression": "none", "preparation": {}}
        },
        "effects": [], "flags": {}, "sort": -1
    }, hp_bonus


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
        if os.path.basename(f).startswith("folder-"):
            continue
        d = json.load(open(f, encoding="utf-8"))
        moves_by_name[d["name"]] = d
        moves_by_norm[normalize_name(d["name"])] = d

    # ícone de TIPO (svg, como no 5e/pokemon5e) para as características "Tipo X" — asset
    # local do módulo (scripts/localize-type-icons.py), não mais hotlink pro GitHub
    type_icon = "modules/pokemon-mundo-perfeito/assets/types/{t}.svg"
    # mesmos seeds de seed-progression-features.py — IDs determinísticos
    progression_ids = {slug: make_id(f"progressao-{slug}")
                        for slug in ["ponto-de-ev", "aumento-de-stab", "talento-de-pokemon",
                                      "aumento-de-proficiencia", "aumento-de-dano"]}
    talento_ids = []
    for tf in sorted(glob.glob(os.path.join(SRC, "trainer-features", "talento-*.json"))):
        talento_ids.append(json.load(open(tf, encoding="utf-8"))["_id"])
    ability_desc = {}
    for af in glob.glob(os.path.join(SRC, "abilities", "*.json")):
        ad = json.load(open(af, encoding="utf-8"))
        ability_desc[ad["name"]] = (ad["system"]["description"]["value"], ad["img"])
    n = 0
    missing_moves = set()
    for f in glob.glob(os.path.join(SRC, "pokedex", "*.json")):
        if os.path.basename(f).startswith("folder-"):
            continue
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
                f"<p>Este Pokémon é do tipo {TYPE_LABELS.get(t, t)}.</p>", type_icon.format(t=t)))

        passive_options = pmp.get("passiveAbility", {}).get("options") or []
        if not passive_options and pmp.get("passiveAbility", {}).get("active"):
            passive_options = [pmp["passiveAbility"]["active"]]
        multi_passive_note = ("<p><em>Se a espécie lista mais de uma Habilidade Passiva, o Pokémon "
                               "usa normalmente apenas uma delas (remova a que não for usar).</em></p>"
                               if len(passive_options) > 1 else "")
        for passive in passive_options:
            desc, img = ability_desc.get(passive, (
                "<p>Veja a Lista de Habilidades Passivas no Livro de Regras.</p>", "icons/svg/aura.svg"))
            embedded.append(feat_stub(
                make_id(f"{name}-passiva-{passive}"), f"Habilidade Passiva: {passive}",
                desc + multi_passive_note, img))
        hidden = pmp.get("hiddenAbility", "")
        if hidden:
            desc, img = ability_desc.get(hidden, (
                "<p>Habilidade Oculta — normalmente inativa; veja o Livro de Regras.</p>",
                "icons/svg/mystery-man.svg"))
            embedded.append(feat_stub(
                make_id(f"{name}-oculta-{hidden}"), f"Habilidade Oculta: {hidden}",
                desc + "<p><em>Habilidade Oculta — normalmente inativa, só entra em uso com o item "
                       "Ability Patch.</em></p>",
                img))

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
            embed = json.loads(json.dumps({k: v for k, v in src_move.items()
                                            if k in ("_id", "name", "type", "img", "system",
                                                     "effects", "flags")}))
            embed["sort"] = 100
            embedded.append(embed)

        # ItemGrants dos Moves de níveis futuros (acima do nível em que a espécie é encontrada)
        move_grants = {}
        for row in pmp.get("moveTable") or []:
            if row["level"] <= level or row["level"] > 20:
                continue
            ids = []
            for move_name in row["moves"]:
                src_move = moves_by_name.get(move_name) or moves_by_norm.get(normalize_name(move_name))
                if src_move:
                    ids.append(src_move["_id"])
                else:
                    missing_moves.add(move_name)
            if ids:
                move_grants[row["level"]] = ids

        hit_die = pmp.get("hitPoints", {}).get("hitDie", "d6")
        if not hit_die.startswith("d"):
            hit_die = "d6"
        book_hp = pmp.get("hitPoints", {}).get("max", 1)
        con_mod = (pmp["abilities"].get("con", {}).get("value", 10) - 10) // 2
        class_item, hp_bonus = build_class_item(name, hit_die, level, book_hp, con_mod,
                                                 move_grants, progression_ids, talento_ids)
        embedded.insert(0, class_item)

        doc["type"] = "npc"
        doc["system"] = {
            "abilities": {k: {"value": v.get("value", 10)} for k, v in pmp["abilities"].items()},
            "attributes": {
                "ac": {"flat": pmp.get("armorClass", {}).get("value", 10), "calc": "flat"},
                # com a classe embutida, o dnd5e deriva o PV máximo dos avanços de PV da
                # classe + mod de CON; "max" aqui vira um bônus fixo, calibrado para o
                # total bater com os PV do livro (mesma técnica do pokemon5e)
                "hp": {"value": book_hp, "max": hp_bonus, "temp": 0, "tempmax": 0,
                        "formula": hit_die},
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
