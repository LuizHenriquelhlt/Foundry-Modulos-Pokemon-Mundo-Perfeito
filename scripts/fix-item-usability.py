#!/usr/bin/env python3
"""
Torna os itens USÁVEIS/EQUIPÁVEIS (feedback do usuário: estavam como "loot"/Saque,
sem botão de usar):

- Consumíveis (Berries, Hortelãs, Doces, Poções, Nectars, Itens-X, vitaminas,
  curativos, comidas, Repelente, TMs, Pokébolas): tipo "consumable" com 1 uso,
  activity de utilização (botão Usar) e autodestruição ao consumir.
- Demais itens do catálogo (roupas, itens seguráveis, kits, equipamento): tipo
  "equipment" (acessório equipável).
- Mega Pedras: schema de equipment válido (a descrição era string solta fora do
  formato do dnd5e); os dados PMP (deltas de atributo etc.) vão para flags e a
  descrição exibe os benefícios formatados.
- Preço: era string ("₽1.200") que o dnd5e zerava na validação — vira número, com
  denominação gp (leia ₽ onde o sistema mostrar po/gp).

Idempotente; roda depois de parse-items/parse-tm-prices/parse-mega-evolutions e
dos scripts de imagem. Uso: python scripts/fix-item-usability.py
"""
import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "packs", "_source")

TYPE_LABELS = {
    "normal": "Normal", "fire": "Fogo", "water": "Água", "electric": "Elétrico",
    "grass": "Grama", "ice": "Gelo", "fighting": "Lutador", "poison": "Venenoso",
    "ground": "Terrestre", "flying": "Voador", "psychic": "Psíquico", "bug": "Inseto",
    "rock": "Pedra", "ghost": "Fantasma", "dragon": "Dragão", "dark": "Sombrio",
    "steel": "Aço", "fairy": "Fada"
}

ABILITY_LABELS = {"str": "FOR", "dex": "DES", "con": "CON", "int": "INT",
                   "wis": "SAB", "cha": "CAR"}

CONSUMABLE_KEYWORDS = [
    " berry", "hortelã", "candy", "poção", "nectar", "cookie", "milk", "soda",
    "lemonade", "fresh water", "honey", "gateau", "crunchies", "casteliacone",
    "heal", "revive", "restore", "ether", "elixir", "antidote", "awakening",
    "repelente", "ração", "malasada", "sweet heart", "juice", "mint"
]
CONSUMABLE_EXACT = {
    "X Attack", "X Defense", "X Special Attack", "X Special Defense", "X Speed",
    "X Accuracy", "Dire Hit", "Guard Spec", "Ability Capsule", "Ability Patch",
    "PP Up", "PP Max", "HP Up", "Protein", "Iron", "Calcium", "Zinc", "Carbos",
    "Candy Bar", "Sacred Ash", "Pomeg", "Rare Candy"
}
FOOD_KEYWORDS = [" berry", "hortelã", "candy", "nectar", "cookie", "milk", "soda",
                  "lemonade", "honey", "gateau", "crunchies", "ração", "malasada",
                  "juice", "mint"]


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


def price_number(doc):
    raw = doc.get("flags", {}).get("pokemon-mundo-perfeito", {}).get("priceRaw", "")
    if not raw:
        val = doc.get("system", {}).get("price", {}).get("value", "")
        raw = val if isinstance(val, str) else ""
    m = re.search(r"[\d.]+", str(raw).replace(".", ""))
    if not m:
        return 0
    try:
        return int(m.group())
    except ValueError:
        return 0


def is_consumable(name):
    low = name.lower()
    if name in CONSUMABLE_EXACT:
        return True
    return any(k in low for k in CONSUMABLE_KEYWORDS)


def utility_activity(name, consume=True):
    act_id = make_id(f"use-{name}")
    consumption = {"targets": [], "scaling": {"allowed": False, "max": ""}, "spellSlot": True}
    if consume:
        consumption["targets"] = [{"type": "itemUses", "target": "", "value": "1",
                                    "scaling": {"mode": "", "formula": ""}}]
    return {act_id: {
        "_id": act_id,
        "type": "utility",
        "name": "Usar",
        "activation": {"type": "action", "value": None, "condition": "", "override": False},
        "consumption": consumption,
        "description": {"chatFlavor": ""},
        "duration": {"units": "inst", "concentration": False, "override": False},
        "range": {"override": False},
        "target": {"override": False},
        "roll": {"prompt": False, "visible": False}
    }}


def description_of(doc):
    desc = doc.get("system", {}).get("description", {})
    if isinstance(desc, dict):
        return desc.get("value", "")
    return desc if isinstance(desc, str) else ""


def fix_catalog_and_consumables():
    n_cons = n_equip = 0
    targets = glob.glob(os.path.join(SRC, "trainer-features", "item-*.json")) \
        + glob.glob(os.path.join(SRC, "pokeballs", "*.json")) \
        + glob.glob(os.path.join(SRC, "tms", "*.json"))
    for f in targets:
        if os.path.basename(f).startswith("folder-"):
            continue
        doc = json.load(open(f, encoding="utf-8"))
        name = doc["name"]
        desc = description_of(doc)
        price = price_number(doc)
        is_ball = os.sep + "pokeballs" + os.sep in f or "/pokeballs/" in f.replace("\\", "/")
        is_tm = "/tms/" in f.replace("\\", "/")

        base_system = {
            "description": {"value": desc, "chat": ""},
            "price": {"value": price, "denomination": "gp"},
            "weight": {"value": 0, "units": "lb"},
            "quantity": 1,
            "rarity": "",
            "identified": True,
            "attunement": "",
            "attuned": False,
            "equipped": False
        }

        if is_ball or is_tm or is_consumable(name):
            doc["type"] = "consumable"
            subtype = "trinket"
            low = name.lower()
            if low.startswith("poção") or "heal" in low or "revive" in low or "restore" in low:
                subtype = "potion"
            elif any(k in low for k in FOOD_KEYWORDS):
                subtype = "food"
            doc["system"] = {
                **base_system,
                "type": {"value": subtype, "subtype": ""},
                "uses": {"spent": 0, "max": "1", "recovery": [], "autoDestroy": True},
                "activities": utility_activity(name, consume=True),
                "properties": []
            }
            n_cons += 1
        else:
            doc["type"] = "equipment"
            doc["system"] = {
                **base_system,
                "type": {"value": "trinket", "subtype": ""},
                "armor": {"value": None, "dex": None, "magicalBonus": None},
                "properties": []
            }
            n_equip += 1
        save(f, doc)
    print(f"catálogo: {n_cons} consumíveis com botão Usar, {n_equip} equipamentos equipáveis")


def mega_description(sysdata):
    parts = []
    if sysdata.get("species") and sysdata.get("megaForm"):
        parts.append(f"<p>Permite que <strong>{sysdata['species']}</strong> Mega Evolua para "
                      f"<strong>{sysdata['megaForm']}</strong> enquanto segura esta pedra.</p>")
    bullets = []
    if sysdata.get("passiveAbility"):
        bullets.append(f"Habilidade Passiva muda para <strong>{sysdata['passiveAbility']}</strong>")
    types = sysdata.get("types") or {}
    if types.get("type1"):
        label = TYPE_LABELS.get(types["type1"], types["type1"])
        if types.get("type2"):
            label += f"/{TYPE_LABELS.get(types['type2'], types['type2'])}"
        bullets.append(f"Tipo muda para <strong>{label}</strong>")
    if sysdata.get("armorClassDelta"):
        bullets.append(f"{sysdata['armorClassDelta']:+d} na CA")
    for key, delta in (sysdata.get("abilityDeltas") or {}).items():
        bullets.append(f"{delta:+d} em {ABILITY_LABELS.get(key, key.upper())}")
    for choice in sysdata.get("abilityChoices") or []:
        opts = " ou ".join(ABILITY_LABELS.get(k, k.upper()) for k in choice.get("options", []))
        bullets.append(f"{choice.get('delta', 0):+d} em {opts} (à escolha do jogador)")
    if sysdata.get("size"):
        bullets.append(f"Tamanho muda para {sysdata['size']}")
    if sysdata.get("movementBonusFeet"):
        bullets.append(f"{sysdata['movementBonusFeet']:+d} pés em todos os deslocamentos")
    for grant in sysdata.get("movementGrants") or []:
        bullets.append(f"Ganha deslocamento de {grant.get('type')} igual ao de {grant.get('equalTo')}")
    for other in sysdata.get("otherEffects") or []:
        bullets.append(other)
    if bullets:
        parts.append("<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>")
    if sysdata.get("description"):
        parts.append(sysdata["description"])
    return "".join(parts)


def fix_megas():
    n = 0
    for f in glob.glob(os.path.join(SRC, "mega-evolutions", "*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        sysdata = doc.get("system", {})
        if "description" in sysdata and isinstance(sysdata.get("description"), dict):
            continue  # já convertido
        flags = doc.setdefault("flags", {}).setdefault("pokemon-mundo-perfeito", {})
        flags["mega"] = sysdata
        doc["type"] = "equipment"
        doc["system"] = {
            "description": {"value": mega_description(sysdata), "chat": ""},
            "type": {"value": "trinket", "subtype": ""},
            "price": {"value": 0, "denomination": "gp"},
            "weight": {"value": 0, "units": "lb"},
            "quantity": 1,
            "rarity": "veryRare",
            "identified": True,
            "attunement": "",
            "attuned": False,
            "equipped": False,
            "armor": {"value": None, "dex": None, "magicalBonus": None},
            "properties": []
        }
        save(f, doc)
        n += 1
    print(f"mega-evolutions: {n} pedras com schema de equipment válido")


CONTAINER_FILES = ["item-mochila.json", "item-mochila-energizada.json"]


def fix_containers():
    n = 0
    for fname in CONTAINER_FILES:
        f = os.path.join(SRC, "trainer-features", fname)
        if not os.path.exists(f):
            continue
        doc = json.load(open(f, encoding="utf-8"))
        desc = description_of(doc)
        price = price_number(doc)
        cap_m = re.search(r"(\d+)\s*kg", desc)
        capacity = int(cap_m.group(1)) if cap_m else None
        doc["type"] = "container"
        doc["system"] = {
            "description": {"value": desc, "chat": ""},
            "price": {"value": price, "denomination": "gp"},
            "weight": {"value": 0, "units": "lb"},
            "quantity": 1,
            "rarity": "",
            "identified": True,
            "container": None,
            "capacity": {"type": "weight", "value": capacity},
            "properties": []
        }
        save(f, doc)
        n += 1
    print(f"contêineres: {n} mochilas convertidas para type container")


def main():
    fix_catalog_and_consumables()
    fix_megas()
    fix_containers()


if __name__ == "__main__":
    main()
