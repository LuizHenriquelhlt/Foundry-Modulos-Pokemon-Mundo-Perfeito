# Pokémon Mundo Perfeito — Módulo Foundry VTT

Módulo que integra o sistema de RPG **Pokémon Mundo Perfeito (PMP)** ao Foundry VTT, rodando por cima do sistema oficial **dnd5e** (v4/v5, Foundry v12+). O PMP é um hack completo de D&D 5e — este módulo reaproveita toda a engine de rolagens/perícias/CA/PV/descansos do dnd5e e adiciona por cima: Pokémon como Actors, Moves como Items, tabela de tipos, captura, Mega Evolução, Z-Moves, Dynamax/Terastal (referência) e a Pokédex completa.

**Status: conteúdo completo das 5 fases planejadas**, extraído dos 6 livros do sistema (Livro de Regras, Livro dos Pokémon, Mega Evoluções, Z-Moves, Geração 8, Geração 9) via parsers dedicados em `scripts/`. Ainda não commitado nem testado dentro de um Foundry real — só gerado e validado estruturalmente (JSON bem formado, sem duplicatas, campos cruzados contra o PDF fonte).

## Conteúdo dos compêndios

| Compêndio | Itens | Fonte |
|---|---|---|
| Pokédex | 1.149 espécies/formas | Livro dos Pokémon (596 páginas, ~2 por página) |
| Moves | 832 Moves (674 da lista principal + 158 exclusivos de Gen 8/9) | Livro de Regras + Geração 8/9 |
| TMs | 321 | Livro de Regras (tabela de preços) |
| Pokébolas | 20 | Livro de Regras |
| Mega Evoluções | 93 (90 padrão + Mega Rayquaza/Kyogre Primal/Groudon Primal) | Livro de Mega Evoluções |
| Recursos de Treinador | 401 (Especializações, Habilidades Gerais, Regiões de Origem inc. Paldea, Origens de Jornada, Classes de Treinador, mecânicas de Dynamax/Terastal, itens/equipamentos) | Livro de Regras + Geração 8/9 |

Cada Move traz, quando aplicável, o **Efeito de Poder-Z** (bônus ao converter o Move de Status em Z-Move) e a fórmula de dano/escala por nível já estruturada. A tabela de tipos, o cálculo de Teste de Captura e a tabela de dano de Z-Move (geral + as 55 exceções por Move) estão implementadas em código (`module/combat/`), não só como referência de texto.

## Pré-requisitos

- Foundry VTT v12 ou v13.
- Sistema **dnd5e** instalado (v4.0.0+) e ativo no mundo.
- Node.js instalado **apenas na sua máquina de desenvolvimento**, para compilar os compêndios uma vez. Não é necessário no servidor Foundry.
- Python 3 + `pdfplumber` (`pip install pdfplumber`) **apenas se for re-rodar os parsers** contra os PDFs originais (não incluídos no módulo — são grandes demais e sujeitos a direitos autorais de terceiros).

## Instalação no Foundry

1. Copie a pasta `pokemon-mundo-perfeito` para a pasta `Data/modules/` da sua instalação do Foundry (ou instale via manifesto, quando publicado).
2. Ative o módulo no seu mundo (o mundo precisa estar rodando o sistema `dnd5e`).
3. Os compêndios (Pokédex, Moves, TMs, Pokébolas, Mega Evoluções, Recursos de Treinador) aparecerão na aba de Compêndios.

## Compilando os compêndios (uma vez, antes de usar)

Os dados-fonte ficam em `packs/_source/<nome>/*.json` (um arquivo por Actor/Item, legível e versionável). O Foundry lê os compêndios já compilados em `packs/<nome>/` (LevelDB), que **não são editados à mão** — são gerados a partir do `_source`.

```bash
npm install
npm run build:packs
```

Isso compila cada pasta `packs/_source/<nome>/` para `packs/<nome>/`. Rode de novo sempre que os arquivos em `_source` mudarem.

Para limpar os compêndios compilados (útil se algo ficar inconsistente):

```bash
npm run clean:packs
```

## Estrutura

```
module/
  pmp.mjs                 # entry point: registra tipos de documento, sheets, tabela de tipos
  data/                    # DataModels (Pokémon, Move)
  sheets/                  # fichas (Actor/Item)
  combat/                  # tabela de tipos, captura, Z-Moves, Mega Evolução
templates/                 # .hbs das fichas
styles/pmp.css
lang/pt-BR.json
packs/_source/              # fonte de verdade dos compêndios (JSON) — versionado no git
packs/                     # saída compilada (gerada por build:packs, não editar, não versionada)
scripts/
  lib/pdf_text.py           # extração de texto "column-aware" via pdfplumber (ver nota abaixo)
  parse-moves.py            # Lista de Moves principal (Livro de Regras)
  parse-gen89-moves.py      # Moves exclusivos de Geração 8/9
  parse-pokedex.py          # Pokédex completa (Livro dos Pokémon)
  parse-mega-evolutions.py  # Lista de Mega Evoluções
  seed-special-megas.py     # Mega Rayquaza / Kyogre Primal / Groudon Primal (formato de texto diferente)
  parse-trainer-*.py        # Especializações, Habilidades Gerais, Regiões, Origens, Classes de Treinador
  parse-items.py            # Itens/equipamentos gerais
  parse-tm-prices.py        # Tabela de preços de TM
  seed-gen89-mechanics.py   # Dynamax/Gigantamax, Terastal, Região de Paldea (texto de referência)
  build-packs.mjs           # compila packs/_source -> packs (Node, roda no Foundry/dev machine)
```

### Sobre a extração dos PDFs

`pdftotext -layout` (poppler) embaralha o texto em páginas de 2+ colunas — confirmado nas
tabelas de preço de TM e de dano de Z-Move, que saíram com colunas intercaladas. Os parsers
usam `pdfplumber` com posição de palavra (x0/top) para reconstruir a ordem de leitura
correta coluna a coluna, e `extract_tables()` para grades reais (Pokébolas, TMs, Itens,
Z-Power). Cada parser imprime um relatório de avisos para qualquer entrada ambígua — nenhum
dado incerto foi gerado silenciosamente; correções pontuais verificadas manualmente contra
o PDF ficam documentadas em dicionários `*_CORRECTIONS` no topo de cada script.

## Checklist de verificação manual

Depois de instalar e compilar:

1. Ative o módulo em um mundo `dnd5e`.
2. Abra o compêndio "Pokédex" e importe o Bulbasaur para o mundo.
3. Confira se a ficha mostra Tipo, SR, CA, PV, atributos, perícias, Habilidade Passiva/Oculta e a lista de Moves por nível igual ao Livro dos Pokémon.
4. Abra o compêndio "Moves" e confira o Move "Absorb": Tipo Grama, 1d4 + MOVE de dano, cura a metade do dano causado.
5. Role um teste de captura em um Pokémon e confira a fórmula `1d20 + 2×Bônus de Proficiência + Bônus da Pokébola`.
6. Abra uma Mega Pedra (ex.: "Charizardite X") no compêndio "Mega Evoluções" e confira os deltas de CA/atributos, tipo e habilidade contra o Livro de Mega Evoluções.

## Limitações conhecidas / próximos passos

- **Sem teste em Foundry real**: todo o trabalho até aqui foi gerar e validar arquivos; a primeira ativação em um mundo Foundry de verdade vai revelar ajustes de sheet/CSS/Handlebars que só aparecem em execução.
- **Classes de Treinador, Regiões, Origens e Especializações** viraram Items do tipo `feat`/`background` com o texto completo (fiel ao livro), mas não têm a progressão de nível conectada ao sistema de Advancement do dnd5e (isso exigiria reconstruir a classe inteira nesse sistema — escopo maior, não incluído aqui).
- **Catálogo geral de itens** (~347 itens) tem ~110 linhas descartadas pelo parser de tabela por ambiguidade (fragmento de descrição vs. nome de item) — descartadas em vez de gravadas erradas; ver `scripts/parse-items.py`.
- **Dynamax/Gigantamax e Terastal** ficaram como texto de referência (regras + requisitos), não como mecânica automatizada em código — o próprio livro oferece múltiplos métodos alternativos à escolha do Mestre para o cálculo de PV do Dynamax, o que não se resume a uma função determinística única.
- **PDFs de origem não incluídos no módulo** (grandes demais, direitos de terceiros) — os scripts esperam que você aponte para a pasta onde eles estão.
