#!/usr/bin/env python3
"""
Compêndio "Itens" (packs/_source/items) — itens seguráveis genéricos que só existem pra
destravar mecânicas na ficha, sem um catálogo por espécie como as Mega Pedras. Hoje: o
"Fator Terastal", equivalente a portar uma Orbe Tera sintonizada — enquanto EQUIPADO
(system.equipped=true) num Pokémon, libera o botão "✨ Terastalizar" na ficha (o Tipo Tera em
si é escolhido no diálogo a cada uso, já que é um traço individual do indivíduo, não da
espécie — ver module/combat/terastal.mjs).

Idempotente: pode rodar de novo, sempre reescreve os mesmos arquivos.

Uso: python scripts/seed-special-items.py
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "items")
FOLDER_ID_SEED = "items-folder-root"


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


FOLDER_ID = make_id(FOLDER_ID_SEED)


def stats():
    return {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
            "compendiumSource": None, "duplicateSource": None}


def write_folder():
    doc = {
        "_key": f"!folders!{FOLDER_ID}",
        "_id": FOLDER_ID, "name": "Itens", "type": "Item", "folder": None,
        "sorting": "a", "color": "#8fbcbb", "flags": {}, "_stats": {}, "sort": 0
    }
    with open(os.path.join(OUT_DIR, "folder-itens.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def equipment_item(slug, name, description, category, img="icons/svg/aura.svg", rarity="rare"):
    item_id = make_id(f"item-{slug}")
    doc = {
        "_key": f"!items!{item_id}",
        "_id": item_id, "name": name, "type": "equipment", "img": img,
        "system": {
            "description": {"value": description, "chat": ""},
            "type": {"value": "trinket", "subtype": ""},
            "price": {"value": 0, "denomination": "gp"},
            "weight": {"value": 0, "units": "lb"},
            "quantity": 1,
            "rarity": rarity,
            "identified": True,
            "attunement": "",
            "attuned": False,
            "equipped": False,
            "armor": {"value": None, "dex": None, "magicalBonus": None},
            "properties": []
        },
        "effects": [],
        "folder": FOLDER_ID,
        "flags": {"pokemon-mundo-perfeito": {"category": category}},
        "_stats": stats(),
        "sort": 0,
        "ownership": {"default": 0}
    }
    with open(os.path.join(OUT_DIR, f"item-{slug}.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def build_fator_terastal():
    description = """
    <p>Um dispositivo que canaliza a energia Terastal, equivalente a portar uma Orbe Tera
    sintonizada especificamente a este Pokémon.</p>
    <p>Enquanto <strong>equipado</strong>, libera o botão "✨ Terastalizar" na ficha do
    Pokémon. Ao usá-lo, escolha o Tipo Tera deste indivíduo — por padrão, o mesmo que seu
    tipo primário, a menos que o Mestre indique um Tipo Tera diferente para ele.</p>
    <p><em>Veja a página "Terastalização" no compêndio de Regras &gt; Mecânicas Especiais
    para as regras completas.</em></p>
    """
    equipment_item("fator-terastal", "Fator Terastal", description, "tera-factor")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))
    write_folder()
    build_fator_terastal()
    print(f"Compêndio de Itens gerado em {OUT_DIR}")


if __name__ == "__main__":
    main()
