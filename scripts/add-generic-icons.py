#!/usr/bin/env python3
"""
Ícones para os itens de treinador sem sprite no PokeAPI (equipamento genérico de nome
português). Usa os ícones NATIVOS do Foundry (icons/**, locais em qualquer instalação,
coloridos) — cada caminho abaixo foi colhido dos itens SRD do repositório oficial do
dnd5e, então é garantidamente válido. Alguns itens têm sprite no PokeAPI com slug
diferente do nome (Poção -> potion, X Special Attack -> x-sp-atk...) — esses usam o
sprite do jogo, verificado por HEAD.

Também remove entradas-lixo de extração (Lago/Oceano/Praia/Rio/Local/Terrain — células
de uma tabela de habitat, não itens) e conserta "Kit de Primeiros"+"Socorros" (nome de
item quebrado em duas linhas pela grade do PDF).

Roda DEPOIS de add-images.py. Uso: python scripts/add-generic-icons.py
"""
import json
import glob
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")

POKEAPI_ITEM = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{slug}.png"

JUNK_NAMES = {"Lago", "Local", "Oceano", "Praia", "Rio", "Terrain", "Socorros"}
RENAMES = {"Kit de Primeiros": "Kit de Primeiros Socorros"}

POKEAPI_SLUGS = {
    "Ability Patch": "ability-patch",
    "Poção": "potion",
    "Poção Super": "super-potion",
    "Poção Hyper": "hyper-potion",
    "Poção Max": "max-potion",
    "Repelente": "repel",
    "Upgrade": "up-grade",
    "X Special Attack": "x-sp-atk",
    "X Special Defense": "x-sp-def",
    "King's Rock": "kings-rock",
    "DNA Splicer": "dna-splicers",
    "Deep Sea Scale/Tooth": "deep-sea-scale",
    "Fairy Feather": "fairy-feather"
}

# caminhos colhidos de packs/_source do repositório oficial foundryvtt/dnd5e (SRD)
CORE_ICONS = {
    "Acessório de Lanterna": "icons/sundries/lights/lantern-bullseye-signal-copper.webp",
    "Lanterna": "icons/sundries/lights/lantern-bullseye-signal-copper.webp",
    "Lanterna Solar": "icons/sundries/lights/lantern-steel.webp",
    "Lampião": "icons/sundries/lights/lantern-iron-yellow.webp",
    "Lampião Solar": "icons/sundries/lights/lantern-steel.webp",
    "Algemas": "icons/sundries/survival/cuffs-shackles-steel.webp",
    "Arpéu": "icons/tools/fishing/hook-multi-steel-brown.webp",
    "Bandana": "icons/equipment/head/hood-cloth-teal-gold.webp",
    "Bicicleta Cross": "icons/environment/creatures/horse-brown.webp",
    "Bicicleta de Corrida": "icons/environment/creatures/horse-brown.webp",
    "Binóculos": "icons/tools/navigation/spyglass-telescope-brass.webp",
    "Bracelete-Z": "icons/equipment/wrist/bracer-yellow-fancy.webp",
    "Mega Bracelete": "icons/equipment/wrist/bracer-banded-leather.webp",
    "Pulseira Sutil": "icons/equipment/wrist/bracer-banded-leather.webp",
    "Broche Religioso": "icons/equipment/neck/necklace-runed-white-red.webp",
    "Bússola": "icons/tools/navigation/compass-brass-blue-red.webp",
    "Calças Flexíveis": "icons/equipment/chest/shirt-collared-brown.webp",
    "Camisa Bufante": "icons/equipment/chest/shirt-collared-yellow.webp",
    "Camisa de Cores": "icons/equipment/chest/shirt-collared-yellow.webp",
    "Camisa Impermeável": "icons/equipment/chest/shirt-collared-brown.webp",
    "Camiseta de Treino": "icons/equipment/chest/shirt-collared-yellow.webp",
    "Candy Bar": "icons/consumables/food/berries-ration-round-red.webp",
    "Courage Candy": "icons/consumables/food/berries-ration-round-red.webp",
    "Health Candy": "icons/consumables/food/berries-ration-round-red.webp",
    "Mighty Candy": "icons/consumables/food/berries-ration-round-red.webp",
    "Quick Candy": "icons/consumables/food/berries-ration-round-red.webp",
    "Smart Candy": "icons/consumables/food/berries-ration-round-red.webp",
    "Tough Candy": "icons/consumables/food/berries-ration-round-red.webp",
    "Canivete de Bolso": "icons/weapons/daggers/knife-green.webp",
    "Multi-ferramenta": "icons/weapons/daggers/knife-green.webp",
    "Cantil": "icons/sundries/survival/waterskin-leather-brown.webp",
    "Garrafa térmica": "icons/consumables/potions/bottle-round-empty-glass.webp",
    "Capa Esvoaçante": "icons/equipment/back/cloak-heavy-fur-blue.webp",
    "Carregador Solar": "icons/magic/light/beam-rays-yellow.webp",
    "Casaco Impermeável": "icons/equipment/back/cloak-brown-accent-brown-layered-collared-fur.webp",
    "Célula de Energia": "icons/commodities/treasure/token-brass-round.webp",
    "Chaleira": "icons/consumables/drinks/tea-jug-gourd-brown.webp",
    "Cinto de Utensílios": "icons/equipment/waist/belt-thick-gemmed-steel-grey.webp",
    "Colar Aromático": "icons/consumables/potions/bottle-bulb-corked-purple.webp",
    "Colar Natural": "icons/equipment/neck/necklace-simple-mushroom-red.webp",
    "Pingente Sensorial": "icons/equipment/neck/pendant-bronze-gem-blue.webp",
    "Corda de 9 metros": "icons/sundries/survival/rope-wrapped-brown.webp",
    "Cristal-Z": "icons/equipment/neck/pendant-faceted-blue.webp",
    "Pedra-Chave": "icons/equipment/neck/amulet-carved-stone-purple.webp",
    "Mega Pedra": "icons/equipment/neck/pendant-faceted-red.webp",
    "Alola Stone": "icons/equipment/neck/pendant-faceted-green.webp",
    "Galar Stone": "icons/equipment/neck/pendant-faceted-blue.webp",
    "Hisui Stone": "icons/equipment/neck/pendant-faceted-red.webp",
    "Extender": "icons/commodities/treasure/token-brass-round.webp",
    "Ability Patch": "icons/commodities/treasure/token-brass-round.webp",
    "Fairy Feather": "icons/commodities/materials/feather-colored-blue.webp",
    "Filtro para Respirador": "icons/magic/water/bubbles-air-water-light.webp",
    "Respirador": "icons/magic/water/bubbles-air-water-light.webp",
    "Fogão": "icons/tools/smithing/furnace-fire-metal-orange.webp",
    "Kit de Cozinha": "icons/tools/laboratory/bowl-mixing.webp",
    "Kit de Escalada": "icons/sundries/survival/climbing-anchor-steel-grey.webp",
    "Kit de Jardinagem": "icons/containers/bags/pouch-leather-green.webp",
    "Kit de Mergulho": "icons/magic/water/bubbles-air-water-light.webp",
    "Kit de Primeiros Socorros": "icons/containers/bags/sack-leather-brown-green.webp",
    "Kit de Refeição": "icons/tools/cooking/fork-steel-tan.webp",
    "Livro de Bolso Ilustrado": "icons/sundries/books/book-worn-brown.webp",
    "Luvas de Couro": "icons/equipment/hand/glove-tooled-leather-blue.webp",
    "Mapa da Região": "icons/tools/navigation/map-chart-tan.webp",
    "Mochila": "icons/containers/bags/pack-simple-leather.webp",
    "Mochila Energizada": "icons/containers/bags/pack-leather-gold-brown.webp",
    "N-Lunarizer": "icons/magic/nature/symbol-moon-stars-white.webp",
    "N-Solarizer": "icons/magic/light/beam-rays-yellow.webp",
    "Nectar Amarelo": "icons/consumables/potions/potion-flask-corked-orange.webp",
    "Nectar Rosa": "icons/consumables/potions/potion-flask-corked-shiny-red.webp",
    "Nectar Roxo": "icons/consumables/potions/bottle-bulb-corked-purple.webp",
    "Nectar Vermelho": "icons/consumables/potions/potion-flask-corked-shiny-red.webp",
    "Óculos de Leitura": "icons/tools/scribal/spectacles-glasses.webp",
    "Óculos de Proteção": "icons/equipment/head/goggles-leather-blue.webp",
    "Óculos de Visão Noturna": "icons/equipment/head/goggles-leather-blue.webp",
    "Pacote de Aventureiro": "icons/containers/bags/pack-leather-gold-brown.webp",
    "Pacote de Biólogo": "icons/containers/bags/pack-leather-gold-brown.webp",
    "Pacote de Explorador": "icons/containers/bags/pack-leather-gold-brown.webp",
    "Pacote de Mergulhador": "icons/containers/bags/pack-leather-gold-brown.webp",
    "Pacote de Socorrista": "icons/containers/bags/pack-leather-gold-brown.webp",
    "Pederneira e Aço": "icons/sundries/lights/torch-black.webp",
    "Pokédex": "icons/sundries/documents/document-torn-diagram-tan.webp",
    "Rotom Dex": "icons/sundries/documents/document-torn-diagram-tan.webp",
    "Ração de Acampamento": "icons/consumables/food/berries-ration-round-red.webp",
    "Relógio Multifuncional": "icons/magic/time/hourglass-brown-orange.webp",
    "Saco de Dormir": "icons/sundries/survival/bedroll-grey.webp",
    "Tenda Grande": "icons/environment/wilderness/camp-improvised.webp",
    "Tenda Pequena": "icons/environment/wilderness/camp-improvised.webp",
    "Tênis Reforçados": "icons/equipment/feet/boots-collared-leather-brown.webp",
    "Tênis Silenciosos": "icons/equipment/feet/boots-leather-green.webp",
    "Tomato Berry": "icons/consumables/food/berries-ration-round-red.webp",
    # Hortelãs (mudam a Natureza) — erva
    **{f"Hortelã da {suf}": "icons/consumables/plants/herb-marjoram-basil-oregano-leaf-bunch-green.webp"
        for suf in ["Alegria", "Apatia", "Apressa", "Arrogância", "Astúcia", "Coragem",
                     "Curiosidade", "Determinação", "Energia", "Impulsividade", "Ingenuidade",
                     "Preguiça", "Prudência", "Sabedoria", "Serenidade", "Seriedade",
                     "Sociabilidade", "Teimosia", "Timidez", "Travessura"]}
}


def url_exists(url, cache={}):
    if url in cache:
        return cache[url]
    req = urllib.request.Request(url, method="HEAD",
                                  headers={"User-Agent": "pokemon-mundo-perfeito-foundry/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            cache[url] = resp.status == 200
    except Exception:
        cache[url] = False
    return cache[url]


def main():
    n_ok = n_removed = 0
    misses = []
    for f in glob.glob(os.path.join(DIR, "item-*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        name = doc["name"]

        if name in JUNK_NAMES:
            os.remove(f)
            n_removed += 1
            continue

        changed = False
        if name in RENAMES:
            name = RENAMES[name]
            doc["name"] = name
            changed = True

        if doc["img"].startswith("icons/svg/") or changed:
            url = None
            if name in POKEAPI_SLUGS:
                candidate = POKEAPI_ITEM.format(slug=POKEAPI_SLUGS[name])
                url = candidate if url_exists(candidate) else None
            if not url:
                url = CORE_ICONS.get(name)
            if url:
                doc["img"] = url
                n_ok += 1
                changed = True
            elif doc["img"].startswith("icons/svg/"):
                misses.append(name)

        if changed:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
                fh.write("\n")

    print(f"{n_ok} itens com ícone aplicado, {n_removed} entradas-lixo removidas")
    if misses:
        print(f"{len(misses)} sem correspondência (mantêm ícone padrão): {misses}")


if __name__ == "__main__":
    main()
