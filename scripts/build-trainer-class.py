#!/usr/bin/env python3
"""
Fase 2 — Classe base "Treinador" (Livro de Regras, páginas 19-28) + conversão das 12
"Classes de Treinador" (páginas 29-32, já extraídas por parse-trainer-classes.py como itens
"feat" soltos) em Subclasses de verdade do dnd5e, ligadas à classe "Treinador" no nível 2.

Cria:
- packs/_source/classes/treinador.json — Item type "class", com Advancement nativo do dnd5e
  (HitPoints, Trait de perícias, Subclass no nível 2, AbilityScoreImprovement nos níveis
  4/8/12/16/19, ItemGrant das 6 habilidades gerais nos níveis 10/11/13/14/17/20).
- packs/_source/classes/<habilidade-geral>.json — as 6 habilidades gerais de Treinador
  (Rastreador Pokémon, Aura de Treinador, Determinação do Treinador, Foco de Treinador,
  Atenção Aguçada, Treinador Mestre), como itens "feat" concedidos via ItemGrant.
- Reescreve cada packs/_source/trainer-features/classe-*.json (mesmo _id, preservado) de
  type "feat" pra type "subclass" (system.classIdentifier = "treinador"), com Advancement
  ItemGrant nos níveis 2/5/9/15 apontando pra 4 novos itens "feat" (um por recurso).
- packs/_source/trainer-features/<subclasse>-nivel-N-<recurso>.json — os 48 itens novos
  (4 por subclasse), extraídos automaticamente da descrição HTML já existente (que já tem
  cada recurso marcado com <h3>Nível N — Nome</h3><p>...</p>, formato fixo criado por
  parse-trainer-classes.py).

IMPORTANTE (avisar o Mestre/jogadores): quem já tiver arrastado uma dessas 12 Classes de
Treinador pro Actor ANTES desta versão está com uma cópia "feat" antiga incorporada — ela não
vira Subclasse sozinha. É preciso remover e arrastar de novo a versão nova do compêndio.

Sobre Pontos de Vida: a Classe Treinador usa Dado de Vida d8 (igual ao livro, usado pra reserva
de Dados de Vida em descansos), mas a progressão de PV do livro é linear (10 + CON no nível 1,
depois 2 + CON por nível) e NÃO bate com a conta padrão do dnd5e pra d8 (8 no nível 1, média de
5/nível). O assistente de "Subir de Nível" do Foundry deixa digitar um valor manual em vez de
"Rolar"/"Usar média" — oriente o jogador a digitar 2 em cada nível a partir do 2º (o 1º nível já
vem fixo com o valor máximo do dado, então precisa de um ajuste manual de +2 uma única vez pra
bater com os "10 + CON" do livro).

Uso: python scripts/build-trainer-class.py
"""
import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")
CLASSES_DIR = os.path.join(ROOT, "packs", "_source", "classes")
MODULE_ID = "pokemon-mundo-perfeito"

FEATURE_BLOCK_RE = re.compile(r"<h3>Nível (\d+) — (.*?)</h3><p>(.*?)</p>", re.DOTALL)

SKILL_CHOICES = ["acr", "ani", "ath", "ste", "itm", "inv", "med", "nat", "prc", "per", "slt", "sur"]

# (nível, nome, descrição HTML) — extraído de Livro de Regras, p.26-27 ("Habilidades gerais de
# Treinador"). Concedidas automaticamente via ItemGrant.
GENERAL_FEATURES = [
    (10, "Rastreador Pokémon",
     "<p>No nível 10, você já passou inúmeras horas na selva, procurando Pokémon altos e baixos. "
     "Uma vez por descanso longo, você pode fazer um teste de SAB CD 15 para procurar Pokémon nas "
     "proximidades. Se obtiver sucesso, seu Mestre deve lhe dizer quais Pokémon selvagens podem ser "
     "encontrados nesse local. Com um sucesso crítico, um Pokémon de sua escolha da lista do Mestre "
     "aparece no próximo encontro.</p>"),
    (11, "Aura de Treinador",
     "<p>Ao atingir o 11º nível, a presença do seu Pokémon se torna mais impactante quando ele está "
     "próximo de você. Escolha um de seus Pokémon para receber vantagem em testes de Atuação, "
     "Intimidação ou Persuasão enquanto estiver ao seu lado. Para isso, ele precisa estar a até 6 "
     "metros de você. O Pokémon escolhido pode ser trocado a cada descanso longo.</p>"),
    (13, "Determinação do Treinador",
     "<p>Quando você atinge o 13º nível, você já obteve bastante experiência em batalhas difíceis e "
     "saiu vitorioso e forte. Você agora possui vantagem em testes de resistência contra medo e pode "
     "escolher um teste de resistência para se tornar proficiente.</p>"),
    (14, "Foco de Treinador",
     "<p>Ao atingir o 14º nível, você aprofundou seu domínio em um campo de treinamento. Escolha uma "
     "perícia na qual já seja proficiente; você agora é especialista nela.</p>"),
    (17, "Atenção Aguçada",
     "<p>Ao atingir o 17º nível, sua experiência aguçou sua percepção, tornando-o extremamente atento "
     "ao ambiente ao seu redor. Enquanto estiver consciente, você não pode ser surpreendido, e "
     "inimigos escondidos não recebem vantagem nas jogadas de ataque contra você.</p>"),
    (20, "Treinador Mestre",
     "<p>No nível 20, você e seus Pokémon atingem o ápice de seu desempenho em combate. Quando você "
     "ou um de seus Pokémon for alvo de um Move que cause dano ou exigir um teste de resistência, "
     "você pode evitar completamente o ataque ou obter sucesso automático no teste, anulando todo o "
     "dano e quaisquer efeitos do Move. Você pode usar este recurso duas vezes por descanso longo.</p>")
]

GENERIC_ICON = "icons/svg/upgrade.svg"


def strip_accents_lower(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", strip_accents_lower(name)).strip("-")


def make_id(seed, used_ids):
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


def stats():
    return {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
            "compendiumSource": None, "duplicateSource": None}


def feat_item(doc_id, name, description, img, folder):
    return {
        "_key": f"!items!{doc_id}", "_id": doc_id, "name": name, "type": "feat", "img": img,
        "system": {
            "description": {"value": description},
            "type": {"value": "", "subtype": ""},
            "requirements": "",
            "uses": {"spent": 0, "max": "", "recovery": []},
            "activities": {}
        },
        "effects": [], "folder": folder, "flags": {}, "sort": 0,
        "_stats": stats(), "ownership": {"default": 0}
    }


def item_grant_advancement(adv_id, level, item_uuids):
    return {
        "_id": adv_id, "type": "ItemGrant", "level": level,
        "configuration": {"items": [{"uuid": u, "optional": False} for u in item_uuids],
                           "optional": False, "spell": None},
        "value": {}, "flags": {}
    }


def asi_advancement(adv_id, level):
    return {
        "_id": adv_id, "type": "AbilityScoreImprovement", "level": level,
        "configuration": {"cap": 2, "fixed": {}, "locked": [], "points": 2},
        "value": {}, "flags": {}
    }


def build_class(used_ids):
    os.makedirs(CLASSES_DIR, exist_ok=True)
    class_id = make_id("classe-base-treinador", used_ids)

    general_items = []
    for level, name, desc in GENERAL_FEATURES:
        item_id = make_id(f"treinador-habilidade-geral-{slugify(name)}", used_ids)
        general_items.append((level, name, feat_item(item_id, name, desc, GENERIC_ICON, None)))

    advancement = {}

    hp_id = make_id("treinador-advancement-hitpoints", used_ids)
    advancement[hp_id] = {"_id": hp_id, "type": "HitPoints", "configuration": {}, "value": {}, "flags": {}}

    skills_id = make_id("treinador-advancement-pericias", used_ids)
    advancement[skills_id] = {
        "_id": skills_id, "type": "Trait", "level": 1,
        "configuration": {
            "allowReplacements": False,
            "choices": [{"count": 2, "pool": [f"skills:{k}" for k in SKILL_CHOICES]}],
            "grants": [], "mode": "default"
        },
        "value": {}, "flags": {}
    }

    subclass_id = make_id("treinador-advancement-subclasse", used_ids)
    advancement[subclass_id] = {"_id": subclass_id, "type": "Subclass", "level": 2,
                                 "configuration": {}, "value": {}, "flags": {}}

    for level in (4, 8, 12, 16, 19):
        aid = make_id(f"treinador-advancement-asi-{level}", used_ids)
        advancement[aid] = asi_advancement(aid, level)

    for level, name, _item in general_items:
        uuid = f"Compendium.{MODULE_ID}.classes.Item.{_item['_id']}"
        gid = make_id(f"treinador-advancement-itemgrant-{level}", used_ids)
        advancement[gid] = item_grant_advancement(gid, level, [uuid])

    class_description = (
        "<p>Enquanto a Origem diz como você nasceu, a Classe de Treinador é como uma profissão ou "
        "objetivo de vida — escolhida a partir do 2º nível (veja as Subclasses \"Caminho de "
        "Treinador\" disponíveis).</p>"
        "<h3>Características Base</h3>"
        "<p><strong>Dado de Vida:</strong> d8. Pontos de Vida no 1º nível: 10 + modificador de "
        "Constituição. Pontos de Vida nos níveis seguintes: 2 + modificador de Constituição. "
        "<em>Nota para o assistente de Subir de Nível do Foundry: o 1º nível já preenche sozinho "
        "com o valor máximo do dado — ajuste manualmente para 10 uma única vez. Nos níveis "
        "seguintes, digite 2 no campo de pontos de vida (não use os botões de rolar/usar média).</em>"
        "</p>"
        "<p><strong>Classe de Armadura:</strong> 10 + modificador de Destreza.</p>"
        "<p><strong>Deslocamento:</strong> 9 metros.</p>"
        "<p><strong>Perícias:</strong> escolha duas entre Acrobacia, Adestrar Animais, Atletismo, "
        "Furtividade, Intimidação, Investigação, Medicina, Natureza, Percepção, Persuasão, "
        "Prestidigitação ou Sobrevivência.</p>"
        "<p><strong>Incremento no Valor de Atributo:</strong> nos níveis 4, 8, 12, 16 e 19 (ou um "
        "Talento no lugar).</p>"
    )

    class_doc = {
        "_key": f"!items!{class_id}", "_id": class_id, "name": "Treinador", "type": "class",
        "img": GENERIC_ICON,
        "system": {
            "description": {"value": class_description},
            "identifier": "treinador",
            "levels": 1,
            "hd": {"denomination": "d8", "additional": "", "spent": 0},
            "primaryAbility": {"value": [], "all": True},
            "properties": [],
            "spellcasting": {"progression": "none", "ability": ""},
            "advancement": advancement,
            "startingEquipment": []
        },
        "effects": [], "folder": None, "flags": {}, "sort": 0,
        "_stats": stats(), "ownership": {"default": 0}
    }

    with open(os.path.join(CLASSES_DIR, "treinador.json"), "w", encoding="utf-8") as fh:
        json.dump(class_doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    for _level, name, item in general_items:
        with open(os.path.join(CLASSES_DIR, f"{slugify(name)}.json"), "w", encoding="utf-8") as fh:
            json.dump(item, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    print(f"Classe \"Treinador\" escrita em {CLASSES_DIR} (1 classe + {len(general_items)} habilidades gerais)")


def convert_subclasses(used_ids):
    paths = sorted(glob.glob(os.path.join(FEATURES_DIR, "classe-*.json")))
    converted = 0
    features_written = 0

    for path in paths:
        doc = json.load(open(path, encoding="utf-8"))
        if doc.get("type") != "feat":
            continue  # já convertido numa rodada anterior

        description = doc["system"]["description"]["value"]
        blocks = FEATURE_BLOCK_RE.findall(description)
        if not blocks:
            print(f"AVISO: nenhum recurso encontrado em {path}, pulando")
            continue

        subclass_name = doc["name"]
        subclass_slug = slugify(subclass_name)
        subclass_advancement = {}

        for level_str, feature_name, feature_html in blocks:
            level = int(level_str)
            feature_id = make_id(f"subclasse-{subclass_slug}-nivel-{level}-{slugify(feature_name)}", used_ids)
            feature_doc = feat_item(feature_id, feature_name, f"<p>{feature_html}</p>", doc["img"], doc["folder"])
            out_name = f"{subclass_slug}-nivel-{level}-{slugify(feature_name)}.json"
            with open(os.path.join(FEATURES_DIR, out_name), "w", encoding="utf-8") as fh:
                json.dump(feature_doc, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            features_written += 1

            uuid = f"Compendium.{MODULE_ID}.trainer-features.Item.{feature_id}"
            gid = make_id(f"subclasse-{subclass_slug}-advancement-nivel-{level}", used_ids)
            subclass_advancement[gid] = item_grant_advancement(gid, level, [uuid])

        doc["type"] = "subclass"
        doc["system"] = {
            "description": {"value": description},
            "identifier": subclass_slug,
            "classIdentifier": "treinador",
            "spellcasting": {"progression": "none", "ability": ""},
            "advancement": subclass_advancement
        }
        # flags.category / features (metadados antigos) continuam úteis como referência rápida.
        doc.setdefault("flags", {}).setdefault(MODULE_ID, {})["classIdentifier"] = "treinador"

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        converted += 1

    print(f"{converted} Subclasses convertidas, {features_written} recursos individuais escritos em {FEATURES_DIR}")


def main():
    used_ids = set()
    for path in glob.glob(os.path.join(ROOT, "packs", "_source", "**", "*.json"), recursive=True):
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(doc, dict) and "_id" in doc:
            used_ids.add(doc["_id"])

    build_class(used_ids)
    convert_subclasses(used_ids)


if __name__ == "__main__":
    main()
