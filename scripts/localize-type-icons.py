#!/usr/bin/env python3
"""
Os ícones de tipo (usados no "img" dos Moves, dos itens "Tipo X" embutidos em cada
Pokémon da Pokédex, das Mega Evoluções e de alguns itens de Treinador) apontavam pra um
repositório do GitHub (raw.githubusercontent.com/MissingGlitch/...) — hotlink externo,
sujeito a rate-limit, fora do ar ou bloqueio de rede, o que fazia os ícones sumirem de
forma inconsistente (ex.: na aba de Ataques da ficha). Os 18 SVGs já foram baixados pra
assets/types/*.svg (dentro do próprio módulo); este script troca TODA ocorrência da URL
remota — onde quer que apareça, incluindo cópias embutidas dentro de Actors — pelo
caminho local.

Substituição de texto direto no JSON (não parseado), porque a mesma URL aparece em
lugares/profundidades diferentes (Move avulso, "Tipo X" embutido, Move embutido em cada
Pokémon da Pokédex, Mega Evolução, item de Treinador) — mais simples e seguro que navegar
a estrutura de cada tipo de documento separadamente.

Idempotente (a segunda rodada não encontra mais nada pra trocar). Uso:
python scripts/localize-type-icons.py
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "packs", "_source")

REMOTE_RE = re.compile(
    r"https://raw\.githubusercontent\.com/MissingGlitch/pokemon-images/[^\"]*?/types/([a-z]+)\.svg"
)


def main():
    files_changed = 0
    occurrences = 0
    for f in glob.glob(os.path.join(SOURCE, "**", "*.json"), recursive=True):
        with open(f, encoding="utf-8") as fh:
            text = fh.read()
        new_text, count = REMOTE_RE.subn(
            r"modules/pokemon-mundo-perfeito/assets/types/\1.svg", text
        )
        if count:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(new_text)
            files_changed += 1
            occurrences += count
    print(f"{occurrences} ocorrências trocadas em {files_changed} arquivos")


if __name__ == "__main__":
    main()
