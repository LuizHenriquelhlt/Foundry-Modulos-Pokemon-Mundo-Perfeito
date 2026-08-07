#!/usr/bin/env python3
"""
SUPERADO — mantido só como registro histórico da Fase 0.

Gerava a amostra curada à mão (Fase 0) de packs/_source/{moves,pokedex,pokeballs,tms},
usada para validar o pipeline module.json -> DataModel -> compilePack antes de investir
na extração automatizada completa. As Fases 2-5 (scripts/parse-moves.py,
parse-pokedex.py, parse-items.py, parse-tm-prices.py) já cobrem os mesmos 17 Moves + o
Bulbasaur + a Pokébola + a TM gerados aqui, com mais precisão (ex.: os níveis do
moveTable do Bulbasaur aqui foram corrigidos manualmente de forma equivocada — o
parser da Fase 3 tem os valores corretos, conferidos por posição de palavra no PDF).

NÃO rode este script depois dos parsers das Fases 2-5: como os nomes de arquivo
coincidem (ex.: "absorb.json"), ele sobrescreveria dados mais completos e corretos
com esta versão mais antiga e mais simples.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "packs", "_source")

ITEM_ICON = "icons/svg/item-bag.svg"
ACTOR_ICON = "icons/svg/mystery-man.svg"

STATS = {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
         "compendiumSource": None, "duplicateSource": None}

POWER_ABILITY_MAP = {
    "FOR/DES": ["str", "dex"], "FOR/CAR": ["str", "cha"], "CON": ["con"],
    "DES": ["dex"], "DES/CAR": ["dex", "cha"], "CON/CAR": ["con", "cha"], "Nenhum": []
}


def base_item(doc_id, name, item_type, system, img=ITEM_ICON):
    collection = "actors" if item_type == "pokemon-mundo-perfeito.pokemon" else "items"
    return {
        "_key": f"!{collection}!{doc_id}",
        "_id": doc_id,
        "name": name,
        "type": item_type,
        "img": img,
        "system": system,
        "effects": [],
        "folder": None,
        "flags": {},
        "_stats": STATS,
        "sort": 0,
        "ownership": {"default": 0}
    }


def move(doc_id, name, move_type, power, activation_raw, pp, duration, range_raw,
         description, higher_levels, base_formula="", scaling=None, priority=0,
         range_meters=0.0, melee=False, observations=""):
    system = {
        "moveType": move_type,
        "category": "",
        "power": power,
        "powerAbilities": POWER_ABILITY_MAP.get(power, []),
        "activation": {"type": "action", "raw": activation_raw},
        "pp": {"value": pp, "max": pp, "unlimited": False},
        "duration": duration,
        "range": {"raw": range_raw, "meters": range_meters, "melee": melee},
        "priority": priority,
        "description": f"<p>{description}</p>",
        "higherLevels": f"<p>{higher_levels}</p>" if higher_levels else "",
        "observations": f"<p>{observations}</p>" if observations else "",
        "zPowerEffect": "",
        "damage": {"baseFormula": base_formula, "scaling": scaling or []}
    }
    return base_item(doc_id, name, "pokemon-mundo-perfeito.move", system)


def scale(*pairs):
    return [{"level": lvl, "formula": f} for lvl, f in pairs]


MOVES = [
    move("oCLrZ3aWZkSBvrjn", "Absorb", "grass", "FOR/DES", "1 ação", 15, "Instantânea",
         "20 pés (6 metros)",
         "Você dispara feixes vermelhos que envolvem o alvo e drenam sua força vital. Faça um "
         "ataque à distância em uma criatura, causando 1d4 + MOVE de dano de grama. Metade do "
         "dano causado é convertido em cura para o usuário (arredondado para cima).",
         "O dado de dano para esse Move muda para 1d6 no nível 5, 1d8 no nível 10 e 1d10 no nível 17.",
         base_formula="1d4", scaling=scale((5, "1d6"), (10, "1d8"), (17, "1d10")), range_meters=6.0),

    move("9Wvgfygw2wMqZcUD", "Tackle", "normal", "FOR/DES", "1 ação", 20, "Instantânea",
         "Corpo a corpo",
         "Você avança e se choca contra uma criatura. Faça um ataque corpo a corpo contra um "
         "alvo, causando 2d4 + MOVE de dano normal em um acerto.",
         "Os dados de dano para este Move mudam para 2d6 no nível 5, 2d8 no nível 10 e 2d10 no nível 17.",
         base_formula="2d4", scaling=scale((5, "2d6"), (10, "2d8"), (17, "2d10")), melee=True),

    move("Ih7yfJs1ON43xKmT", "Growl", "normal", "FOR/CAR", "1 ação", 20, "Enquanto ativo",
         "Pessoal (cone de 60 pés / 18 metros)",
         "Você mira nas criaturas à sua frente com um rosnado intimidador em um cone de 60 pés "
         "(18 metros). Qualquer criatura inimiga pega no cone deve ter sucesso em um teste de "
         "resistência de SAB contra sua CD de Move, reduzindo o Ataque em 1 estágio em caso de "
         "falha, podendo ser acumulado em até -6 estágios.",
         "", range_meters=18.0, observations="Growl é um Move baseado em som."),

    move("ecQoXsf2o3gyrDO1", "Vine Whip", "grass", "FOR/DES", "1 ação", 15, "Instantânea",
         "Corpo a corpo (alcance de 15 pés / 4,5 metros)",
         "Você estende uma vinha alongada para chicotear o alvo. Faça um ataque corpo a corpo "
         "com alcance estendido de até 15 pés (4,5 metros), causando 1d10 + MOVE de dano de "
         "grama em um acerto.",
         "O dado de dano para este Move muda para 2d6 no nível 5, 3d6 no nível 10 e 2d12 no nível 17.",
         base_formula="1d10", scaling=scale((5, "2d6"), (10, "3d6"), (17, "2d12")),
         range_meters=4.5, melee=True),

    move("xkxwnQrS7RPeMOkI", "Leech Seed", "grass", "DES", "1 ação", 5, "Enquanto ativo",
         "80 pés (24 metros)",
         "Você envia uma semente que se implanta na pele de uma criatura dentro do alcance. "
         "Faça um ataque à distância -1. Em um acerto, uma semente se implanta na pele do alvo. "
         "O alvo recebe dano sem tipo igual ao nível dele no final de cada um dos próprios "
         "turnos subsequentes até desmaiar ou ser trocado. O dano causado retorna como cura ao "
         "usuário, ou qualquer outra criatura ativa que o treinador tenha na batalha, mesmo que "
         "o atacante original desmaie ou seja devolvido à sua Pokébola. Apenas uma criatura pode "
         "ser semeada pelo atacante de cada vez. Criaturas do tipo grama são imunes ao dano "
         "deste Move.",
         "", range_meters=24.0),

    move("UpkDyr7OSJoRu1XX", "Poison Powder", "poison", "CON", "1 ação", 20, "Instantânea",
         "20 pés (6 metros)",
         "Você libera um aglomerado de esporos venenosos que explodem no ar acima de uma "
         "criatura dentro do alcance. Role 1d20 + MOVE + 4 e compare o resultado com 10 + CON "
         "do alvo. Em um resultado maior ou igual, o alvo fica Envenenado.",
         "", range_meters=6.0),

    move("do0cZuzren68K4Tu", "Sleep Powder", "grass", "CON", "1 ação", 10, "Instantânea",
         "20 pés (6 metros)",
         "Você libera um aglomerado de esporos em direção a uma criatura dentro do alcance, "
         "tentando deixá-la sonolenta. Role 1d20 + MOVE + 4 e compare o resultado com 10 + CON "
         "do alvo. Em um resultado maior ou igual, o alvo fica Sonolento.",
         "", range_meters=6.0),

    move("nPFz46PDjqipVJIq", "Razor Leaf", "grass", "FOR/DES", "1 ação", 15, "Instantânea",
         "Pessoal (cone de 40 pés / 12 metros)",
         "Você envia diversas folhas afiadas em tremenda velocidade à sua frente, em um cone de "
         "40 pés (12 metros). Qualquer criatura pega no cone deve ter sucesso em um teste de DES "
         "contra sua CD de Move -1, sofrendo 1d12 + MOVE de dano de grama em uma falha, ou "
         "metade do dano em um sucesso. Qualquer criatura que rolar um resultado natural de 3 ou "
         "menos no teste sofrerá um dano crítico.",
         "O dado de dano para este Move muda para 4d4 no nível 5, 2d12 no nível 10 e 3d10 no nível 17.",
         base_formula="1d12", scaling=scale((5, "4d4"), (10, "2d12"), (17, "3d10")), range_meters=12.0),

    move("VLB5LzxoiGFfWd3h", "Take Down", "normal", "FOR", "1 ação", 10, "Instantânea",
         "Corpo a corpo",
         "Você investe contra uma criatura para uma cabeçada potente. Faça um ataque corpo a "
         "corpo -2, causando 3d6 + MOVE de dano normal em um acerto, sofrendo um quarto do dano "
         "causado (arredondado para baixo) como recuo de dano sem tipo.",
         "Os dados de dano para este Move mudam para 3d10 no nível 5, 3d12 no nível 10 e 4d12 "
         "no nível 17.",
         base_formula="3d6", scaling=scale((5, "3d10"), (10, "3d12"), (17, "4d12")), melee=True),

    move("jOkYRBMeyyMDHqJ3", "Sweet Scent", "normal", "CON/CAR", "1 ação", 10, "Instantânea",
         "Pessoal (cone de 30 pés / 9 metros)",
         "Você libera um cheiro doce direcionado em um cone de 30 pés (9 metros), na tentativa "
         "de distrair os inimigos. Qualquer criatura pega no cone deve ter sucesso em um teste "
         "de resistência de CAR contra sua CD de Move, reduzindo a Evasão em 2 estágios em caso "
         "de falha, podendo ser acumulado em até -6 estágios.",
         "", range_meters=9.0),

    move("8aRUhR4IWrXPvhsB", "Double-Edge", "normal", "FOR/DES", "1 ação", 10, "Instantânea",
         "Corpo a corpo",
         "Você se lança com todo o corpo, colidindo com força contra uma criatura. Faça um "
         "ataque corpo a corpo contra um alvo, causando 3d8 + MOVE de dano normal em um acerto, "
         "mas sofrendo 1/3 do dano causado (arredondado para baixo) em recuo de dano sem tipo.",
         "Os dados de dano para este Move mudam para 6d6 no nível 5, 6d8 no nível 10 e 6d10 no "
         "nível 17.",
         base_formula="3d8", scaling=scale((5, "6d6"), (10, "6d8"), (17, "6d10")), melee=True),

    move("kDa9U4UqGWlG6g3O", "Growth", "normal", "Nenhum", "1 ação", 10, "Enquanto ativo",
         "Pessoal",
         "Você gera forças interiores que fortificam seu corpo, aumentando seu Ataque e Ataque "
         "Especial em 1 estágio, podendo ser acumulado em até 6 estágios cada. Durante luz solar "
         "intensa, o aumento passa a ser de 2 estágios cada.",
         ""),

    move("t1OGMmjxWkI9X7H6", "Power Whip", "grass", "FOR/DES", "1 ação", 5, "Instantânea",
         "Corpo a corpo",
         "Você gira violentamente seus tentáculos ou cipós em direção a um alvo. Faça um ataque "
         "corpo a corpo -2 contra uma criatura, causando 3d8 + MOVE de dano de grama em um acerto.",
         "Os dados de dano para este Move mudam para 6d6 no nível 5, 6d8 no nível 10 e 6d10 no "
         "nível 17.",
         base_formula="3d8", scaling=scale((5, "6d6"), (10, "6d8"), (17, "6d10")), melee=True),

    move("aMuFbh7x41Ztpdp4", "Synthesis", "grass", "CON", "1 ação", 3, "Instantânea",
         "Pessoal",
         "Seu corpo brilha e cintila diante da luz solar, curando seus ferimentos. A cura base é "
         "3d6 + MOVE sem clima ativo (veja a tabela do livro para variações com Luz Solar "
         "Intensa, Chuva, Granizo ou Tempestade de Areia). Se usado durante a noite, recebe "
         "metade da cura total (mesmo com o efeito de Luz Solar Intensa).",
         "", base_formula="3d6"),

    move("K8ffUF0eWIXiiQE8", "Worry Seed", "grass", "DES/CAR", "1 ação", 5, "Enquanto ativo",
         "30 pés (9 metros)",
         "Você dispara uma semente bizarra que implanta preocupação em outra criatura. Role "
         "1d20 + MOVE + 9 e compare o resultado com 10 + CON do alvo. Em um resultado maior ou "
         "igual, a habilidade passiva do alvo é substituída por Insomnia durante a duração, "
         "impedindo-o de ficar Sonolenta ou Dormindo. Caso o alvo já esteja Sonolento ou "
         "Dormindo, ele acorda no início do próximo turno dele.",
         "", range_meters=9.0),

    move("JkqH3MB9n7IWUSmT", "Solar Beam", "grass", "FOR/DES", "1 ação, carga", 5,
         "1 rodada, Concentração", "Pessoal (linha de 80 pés / 24 metros)",
         "Ao usar este Move, você absorve energia solar e se prepara para liberar um raio "
         "devastador. No seu próximo turno, se você mantiver a concentração, use uma ação para "
         "criar uma linha de energia solar de 80 pés (24 metros), com 5 pés (1,5 metros) de "
         "largura. Qualquer criatura pega na linha deve ter sucesso em um teste de DES contra "
         "sua CD de Move, sofrendo 3d8 + MOVE de dano de grama em caso de falha e metade disso "
         "em caso de sucesso. Se este Move for usado sob luz solar intensa, ele pode ser "
         "executado imediatamente no momento em que for ativado, sem necessidade de concentração.",
         "Os dados de dano para este Move mudam para 6d6 no nível 5, 6d8 no nível 10 e 6d10 no "
         "nível 17.",
         base_formula="3d8", scaling=scale((5, "6d6"), (10, "6d8"), (17, "6d10")), range_meters=24.0),

    move("tzQPxC5HChpoevbL", "Seed Bomb", "grass", "FOR/DES", "1 ação", 10, "Instantânea",
         "30 pés (9 metros)",
         "Você dispara uma série de sementes luminosas que explodem ao atingir o alvo. Faça um "
         "ataque à distância, causando 4d4 + MOVE de dano de grama em um acerto.",
         "Os dados de dano para este Move mudam para 4d6 no nível 5, 4d8 no nível 10 e 4d10 no "
         "nível 17.",
         base_formula="4d4", scaling=scale((5, "4d6"), (10, "4d8"), (17, "4d10")), range_meters=9.0),
]


def pokemon_actor():
    system = {
        "species": "bulbasaur",
        "dexNumber": 1,
        "types": {"type1": "grass", "type2": "poison"},
        "speciesRank": {"value": 0.5, "display": "1/2"},
        "size": "tiny",
        "heightMeters": 0.7,
        "minLevelFound": 1,
        "eggGroups": ["Grama", "Monstro"],
        "gender": {"malePercent": 88, "femalePercent": 12, "genderless": False},
        "evolutionStage": {"current": 1, "max": 3},
        "evolution": "Bulbasaur pode evoluir para Ivysaur no nível 6 ou superior. Quando evolui, "
                     "seus pontos de vida aumentam no dobro do seu nível.",
        "biography": "<p>O Pokémon Semente. Bulbasaur pode ser visto cochilando sob a luz solar "
                     "intensa. Há uma semente nas costas. Ao absorver os raios solares, a "
                     "semente cresce progressivamente.</p>",
        "abilities": {
            "str": {"value": 13}, "dex": {"value": 12}, "con": {"value": 12},
            "int": {"value": 6}, "wis": {"value": 10}, "cha": {"value": 10}
        },
        "skills": ["Atletismo", "Natureza"],
        "armorClass": {"value": 13},
        "hitPoints": {"value": 17, "max": 17, "hitDie": "d6"},
        "movement": {"walk": 9, "other": ""},
        "senses": "",
        "passiveAbility": {"options": ["Overgrow"], "active": "Overgrow"},
        "hiddenAbility": "Chlorophyll",
        "level": 1,
        "moveTable": [
            {"level": 1, "moves": ["Growl", "Tackle"]},
            {"level": 4, "moves": ["Leech Seed", "Vine Whip"]},
            {"level": 7, "moves": ["Poison Powder", "Sleep Powder"]},
            {"level": 10, "moves": ["Razor Leaf", "Take Down"]},
            {"level": 11, "moves": ["Sweet Scent"]},
            {"level": 13, "moves": ["Double-Edge", "Growth"]}
        ],
        "knownMoves": ["Growl", "Tackle"],
        "tms": ["Acid Spray", "Attract", "Bind", "Body Slam", "Bullet Seed", "Charm", "Confide",
                "Curse", "Double Team", "Double-Edge", "Echoed Voice", "Endure", "Energy Ball",
                "Facade", "False Swipe", "Frustration", "Giga Drain", "Grass Knot",
                "Grass Pledge", "Grassy Glide", "Grassy Terrain", "Helping Hand", "Hidden Power",
                "Knock Off", "Leaf Storm", "Light Screen", "Magical Leaf", "Nature Power",
                "Protect", "Rest", "Return", "Round", "Safeguard", "Seed Bomb", "Sleep Talk",
                "Sludge Bomb", "Snore", "Solar Beam", "Substitute", "Sunny Day", "Swagger",
                "Swords Dance", "Synthesis", "Take Down", "Tera Blast", "Toxic", "Trailblaze",
                "Venoshock", "Weather Ball", "Work Up", "Worry Seed"],
        "eggMoves": ["Amnesia", "Charm", "Curse", "Endure", "Giga Drain", "Grass Whistle",
                     "Grassy Terrain", "Ingrain", "Leaf Storm", "Magical Leaf", "Nature Power",
                     "Petal Dance", "Power Whip", "Skull Bash", "Sludge", "Toxic"],
        "typeDefenseOverrides": {},
        "nature": {"name": "", "increased": "", "decreased": ""},
        "loyalty": 0,
        "shiny": False,
        "evs": {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0}
    }
    doc = base_item("OhbVrpoiVgRV5IfL", "Bulbasaur", "pokemon-mundo-perfeito.pokemon", system, img=ACTOR_ICON)
    doc["prototypeToken"] = {"name": "Bulbasaur", "actorLink": False}
    return doc


def pokeball():
    system = {"description": {"value": "<p>Uma Pokébola padrão usada para capturar Pokémon "
                                         "selvagens.</p>"}}
    doc = base_item("JoLoaeTOdoe5c3ve", "Pokébola", "consumable", system)
    doc["flags"] = {"pokemon-mundo-perfeito": {"captureBonus": 0}}
    return doc


def tm():
    system = {"description": {"value": "<p>TM que ensina o Move Solar Beam a um Pokémon "
                                        "compatível.</p>"}}
    doc = base_item("GprQFnIiU74KKEpY", "TM: Solar Beam", "consumable", system)
    doc["flags"] = {"pokemon-mundo-perfeito": {"teachesMove": "Solar Beam"}}
    return doc


def write_json(folder, filename, doc):
    path = os.path.join(SRC, folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    for m in MOVES:
        write_json("moves", f"{m['name'].lower().replace(' ', '-').replace('-edge','-edge')}.json", m)
    write_json("pokedex", "bulbasaur.json", pokemon_actor())
    write_json("pokeballs", "pokebola.json", pokeball())
    write_json("tms", "tm-solar-beam.json", tm())
    print(f"Gerados: {len(MOVES)} moves, 1 Pokémon, 1 Pokébola, 1 TM.")


if __name__ == "__main__":
    main()
