#!/usr/bin/env python3
"""
Incubadoras (Livro de Regras, "Manuseio de Ovos", pág. 42) como Items "equipment" de
verdade no compêndio trainer-features — antes só existiam como uma lista fixa no
código (module/data/egg-rules.mjs), sem Item nenhum pro Mestre dar ao jogador, ver o
preço ou ajustar o bônus. O bônus de dado (flags.pokemon-mundo-perfeito.incubator.bonusDice)
fica editável pelo Mestre via "Configurar Flags" (nativo do Foundry) no próprio Item —
module/data/incubator-lookup.mjs lê esse valor direto do compêndio na hora de montar a
fórmula de incubação, então mudar aqui muda o bônus de verdade sem editar código.

Idempotente. Uso: python scripts/add-incubator-items.py
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")
FOLDER_ID = "Zm6FGQvH27WXnke5"  # pasta "Itens de Treinador" (mesma dos outros item-*.json)


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


INTRO = ("Para os Treinadores mais abastados, Incubadoras oferecem um habitat artificial e "
         "autocontido especialmente projetado para manter um ovo em condições imaculadas "
         "enquanto ele choca. Incubadoras normalmente não cabem em uma mochila comum, sendo "
         "necessário transportá-las manualmente ou de outras formas — mas o ovo não precisa "
         "estar perto do Treinador para chocar, podendo rolar o d100 e seus bônus onde quer "
         "que esteja.")

INCUBATORS = [
    {
        "slug": "incubadora-basica", "name": "Incubadora Básica", "price": 1000,
        "bonus_dice": "1d20", "extra": "",
        "img": "icons/commodities/gems/pearl-purple-dark.webp"
    },
    {
        "slug": "incubadora-plus", "name": "Incubadora Plus", "price": 3000,
        "bonus_dice": "2d20", "extra": "",
        "img": "icons/commodities/treasure/token-brass-round.webp"
    },
    {
        "slug": "incubadora-super", "name": "Incubadora Super", "price": 10000,
        "bonus_dice": "3d20",
        "extra": " Além disso, ao atingir o requisito de eclosão, o Treinador pode escolher o "
                 "momento de chocar o ovo.",
        "img": "icons/commodities/treasure/statue-runed-blue-grey.webp"
    },
]


def build_item(entry):
    item_id = make_id(f"incubadora-{entry['slug']}")
    desc = (f"<p>{INTRO}</p><p>Esta Incubadora permite ao Treinador reduzir o Tempo de "
            f"Eclosão do ovo em um adicional de {entry['bonus_dice']} ao rolar contra o "
            f"contador de incubação.{entry['extra']}</p>")
    return {
        "_key": f"!items!{item_id}",
        "_id": item_id,
        "name": entry["name"],
        "type": "equipment",
        "img": entry["img"],
        "system": {
            "description": {"value": desc, "chat": ""},
            "price": {"value": entry["price"], "denomination": "gp"},
            "weight": {"value": 0, "units": "lb"},
            "quantity": 1,
            "rarity": "",
            "identified": True,
            "attunement": "",
            "attuned": False,
            "equipped": False,
            "type": {"value": "trinket", "subtype": ""},
            "armor": {"value": None, "dex": None, "magicalBonus": None},
            "properties": []
        },
        "effects": [],
        "folder": FOLDER_ID,
        "flags": {
            "pokemon-mundo-perfeito": {
                "category": "item-treinador",
                "priceRaw": f"₽{entry['price']:,}".replace(",", "."),
                "incubator": {"bonusDice": entry["bonus_dice"]}
            }
        },
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": 0, "ownership": {"default": 0}
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for entry in INCUBATORS:
        doc = build_item(entry)
        with open(os.path.join(OUT_DIR, f"{entry['slug']}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    print(f"{len(INCUBATORS)} Incubadoras escritas em {OUT_DIR}")


if __name__ == "__main__":
    main()
