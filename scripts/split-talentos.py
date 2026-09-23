#!/usr/bin/env python3
"""
Divide a pasta única "Talentos" (packs/_source/trainer-features/talento-*.json) em duas:
"Talentos de Treinador" e "Talentos de Pokémon".

O Livro de Regras NÃO separa os Talentos em duas listas fechadas — é um único capítulo
(pág. 72-75) do qual tanto Treinadores (ao abrir mão de um Incremento de Valor de Atributo
nos níveis 4º/8º/12º/16º/19º, pág. 20) quanto Pokémon (nos níveis 4º/8º/12º/16º/20º, pág. 38)
podem escolher. A classificação abaixo foi feita lendo a descrição de cada Talento: os que
mencionam explicitamente "Pokémon"/Move/PP (mecânicas que só existem pro lado Pokémon do
jogo) foram classificados como Talento de Pokémon; os que concedem perícia/expressam um
talento genérico de personagem (furtividade, atuação, percepção, etc., sem nenhuma menção a
Pokémon/Move) foram classificados como Talento de Treinador. Um punhado (Mobilidade,
Resiliente, Resistente, Robusto, Disputador) é ambíguo/serve pros dois — ficou como Treinador
por ter o efeito principal genérico; dá pra arrastar pra outra pasta direto no compêndio do
Foundry se o Mestre achar melhor.

Roda EM CIMA dos arquivos talento-*.json já existentes (não precisa do PDF) — só reatribui a
pasta de cada um e substitui folder-talentos.json pelas duas pastas novas. Idempotente: pode
rodar de novo sem problema.

Uso: python scripts/split-talentos.py
"""
import glob
import hashlib
import json
import os
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")


def make_id(seed):
    # Foundry exige IDs com EXATAMENTE 16 caracteres alfanuméricos — os IDs "legíveis" usados
    # antes aqui (ex.: "TalentosTreinFolder1", 20 caracteres) passavam despercebido no build
    # (json.dump não valida tamanho de _id), mas o próprio Foundry rejeita o documento ao
    # carregar o compêndio (DataModelValidationError: "_id: must be a valid 16-character
    # alphanumeric ID"), derrubando o carregamento do mundo inteiro. Gerar por hash evita
    # repetir esse erro de contagem manual de novo.
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


TRAINER_FOLDER_ID = make_id("talentos-de-treinador-folder")
POKEMON_FOLDER_ID = make_id("talentos-de-pokemon-folder")

def _nfc(s):
    # Texto extraído de PDF via pdfplumber às vezes vem em NFD (acento como caractere
    # combinante separado) em vez de NFC (acento pré-composto) — comparação direta de string
    # falha silenciosamente nesse caso mesmo com os dois "parecendo" idênticos. Normaliza os
    # dois lados pra NFC antes de comparar.
    return unicodedata.normalize("NFC", s)


POKEMON_TALENTS = {_nfc(n) for n in {
    "Atacante Bestial", "Aumento de CA", "Controlador de área", "Corpo Apto",
    "Escultor de Poder", "Explorador das Profundezas", "Explorador dos Céus",
    "Explorador dos Mares", "Incansável", "Investida Poderosa",
    "Mestre de Combate à Distância", "Mestre de Combate Corpo a Corpo", "Move Extra",
}}


def write_folder(doc_id, name):
    doc = {
        "_key": f"!folders!{doc_id}",
        "_id": doc_id, "name": name, "type": "Item", "folder": None,
        "sorting": "a", "color": "#a3be8c", "flags": {}, "_stats": {}, "sort": 0
    }
    path = os.path.join(OUT_DIR, f"folder-{doc_id.lower()}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main():
    # Remove a pasta única antiga e qualquer "folder-talentos*.json" de uma rodada anterior
    # deste script (os nomes de arquivo mudam a cada rodada, já que agora derivam de um hash
    # em vez de um texto fixo — sem isso, arquivos órfãos de IDs antigos ficam pra trás e
    # voltam a quebrar a validação do Foundry, como aconteceu com os IDs "legíveis" originais).
    for path in glob.glob(os.path.join(OUT_DIR, "folder-talentos*.json")):
        os.remove(path)

    write_folder(TRAINER_FOLDER_ID, "Talentos de Treinador")
    write_folder(POKEMON_FOLDER_ID, "Talentos de Pokémon")

    moved = {"treinador": 0, "pokemon": 0}
    unmatched = []
    for path in sorted(glob.glob(os.path.join(OUT_DIR, "talento-*.json"))):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        name = _nfc(doc["name"])
        if name in POKEMON_TALENTS:
            doc["folder"] = POKEMON_FOLDER_ID
            moved["pokemon"] += 1
        else:
            doc["folder"] = TRAINER_FOLDER_ID
            moved["treinador"] += 1
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    print(f"Talentos de Treinador: {moved['treinador']}")
    print(f"Talentos de Pokémon: {moved['pokemon']}")
    if unmatched:
        print(f"Sem classificação (ficaram em Treinador por padrão): {unmatched}")


if __name__ == "__main__":
    main()
