# Pokémon Mundo Perfeito — Módulo Foundry VTT

Módulo que integra o sistema de RPG **Pokémon Mundo Perfeito (PMP)** ao Foundry VTT, rodando por cima do sistema oficial **dnd5e** (v4/v5, Foundry v12+). O PMP é um hack completo de D&D 5e — este módulo reaproveita toda a engine de rolagens/perícias/CA/PV/descansos do dnd5e e adiciona por cima: Pokémon como Actors, Moves como Items, tabela de tipos, captura, Mega Evolução, Z-Moves, Terastal, Dynamax (referência) e a Pokédex completa.

**Status: conteúdo completo das 5 fases planejadas**, extraído dos 6 livros do sistema (Livro de Regras, Livro dos Pokémon, Mega Evoluções, Z-Moves, Geração 8, Geração 9) via parsers dedicados em `scripts/`. O pipeline `npm install && npm run build:packs` foi testado de ponta a ponta (Node.js instalado, compêndios compilados e conferidos por tamanho/contagem de documentos) — ainda **não foi testado dentro de um Foundry real rodando**, então ajustes de sheet/CSS podem aparecer na primeira ativação.

## Conteúdo dos compêndios

| Compêndio | Itens | Fonte |
|---|---|---|
| Pokédex | 1.149 espécies/formas | Livro dos Pokémon (596 páginas, ~2 por página) |
| Moves | 833 Moves (675 da lista principal + 158 de Gen 8/9: 89 da Oitava e 69 da Nona Geração) | Livro de Regras + Geração 8/9 |
| TMs | 321 | Livro de Regras (tabela de preços) |
| Pokébolas | 20 | Livro de Regras |
| Mega Evoluções | 93 (90 padrão + Mega Rayquaza/Kyogre Primal/Groudon Primal) | Livro de Mega Evoluções |
| Recursos de Treinador | 584 (Especializações, Habilidades Gerais, Regiões de Origem inc. Paldea, Origens de Jornada, Classes de Treinador, Talentos, Naturezas, mecânicas de Dynamax/Terastal, itens/equipamentos — incluindo os 77 itens dos suplementos: 34 de Galar e 43 de Paldea, com 19 Tera Shards numa subpasta própria) | Livro de Regras + Geração 8/9 |

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
  pmp.mjs                 # entry point: tabela de tipos, painel da ficha, estágios, macros
  migrations.mjs           # ajustes nos Pokémon do mundo ao atualizar o módulo (roda 1x, só o Mestre)
  sheet-extras.mjs         # painel injetado na ficha nativa do dnd5e (XP, estágios, Afinidade, Mega/Tera)
  combat/                  # tipos e defesas, captura, Z-Moves, Mega Evolução, Terastal, Mudanças de Status
  data/                    # evolução, Afinidade, reparo de Moves/Habilidades, buscas nos compêndios
  apps/                    # diálogos (evolução, Mega, Tera, ovos)
styles/pmp.css             # vazio de propósito: cada painel/diálogo traz o próprio estilo
lang/pt-BR.json
packs/_source/              # fonte de verdade dos compêndios (JSON) — versionado no git
packs/                     # saída compilada (gerada por build:packs, não editar, não versionada)
scripts/
  lib/pdf_text.py           # extração de texto "column-aware" via pdfplumber (ver nota abaixo)
  parse-moves.py            # Lista de Moves principal (Livro de Regras)
  sync-gen89-moves.py       # Moves de Geração 8/9: cria os novos e atualiza os existentes pela versão atual dos suplementos
  parse-gen89-items.py      # Itens de Geração 8/9 (com os ícones extraídos do próprio livro, em assets/items/)
  sync-gen89-abilities.py   # texto das 73 Habilidades Passivas de Geração 8/9 (compêndio + cópias na Pokédex)
  rebuild-moves.py          # regera os Moves (CD com modificador, áreas da descrição...) e as cópias na Pokédex
  fix-move-texts.py         # tira créditos de arte vazados no texto dos Moves e lê a prioridade (+N) da descrição
  parse-pokedex.py          # Pokédex completa (Livro dos Pokémon)
  fix-pokedex-movement.py   # relê "Deslocamento:" inteiro (natação/voo/escavação da 2ª linha, "flutua")
  sync-pokedex-move-lists.py # relê tabela de níveis, TMs e Egg Moves; refaz concessões e Moves conhecidos
  fix-evolution-texts.py    # textos de evolução que não nomeavam a forma de destino (regionais, Froslass...)
  parse-mega-evolutions.py  # Lista de Mega Evoluções
  seed-special-megas.py     # Mega Rayquaza / Kyogre Primal / Groudon Primal (formato de texto diferente)
  add-mega-abilities.py     # Habilidades que só existem na Mega (Desolate Land, Mega Sol, Spicy Spray...)
  fix-mega-data.py          # relê o livro de Megas: textos misturados, habilidades a lançar, Aerodactylite/Zygardite
  parse-trainer-*.py        # Especializações, Habilidades Gerais, Regiões, Origens, Classes de Treinador
  parse-items.py            # Itens/equipamentos gerais
  sync-rulebook-items.py    # relê o capítulo Itens com PyMuPDF: textos emendados, preços, itens que faltavam
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

- **Sem teste em Foundry real**: o pipeline de build (`npm install && npm run build:packs`) foi testado e os compêndios compilam corretamente com dados reais — mas a primeira ativação em um mundo Foundry de verdade ainda vai revelar ajustes de sheet/CSS/Handlebars que só aparecem em execução.
- **Ao rodar `npm install`, o npm pode avisar que bloqueou o script nativo do `classic-level`** (dependência de LevelDB do `@foundryvtt/foundryvtt-cli`) por segurança. Rode `npm approve-scripts classic-level` se quiser silenciar o aviso; na prática não afeta o resultado, já que `classic-level` traz binário pré-compilado para Windows/macOS/Linux.
- **Regiões, Origens e Especializações** viraram Items do tipo `feat`/`background`/`race` com o texto completo (fiel ao livro); a Classe base Treinador e as 12 Classes de Treinador (subclasses) já usam o Advancement do dnd5e.
- **Catálogo geral de itens**: o `parse-items.py` (pdfplumber) juntava linhas vizinhas em tabelas de célula centralizada e descartava ~110 linhas ambíguas. O `sync-rulebook-items.py` relê o capítulo com PyMuPDF e corrige textos, preços e itens faltantes; rode-o depois do `parse-items.py`.
- **Dynamax/Gigantamax** ficou como texto de referência (regras + requisitos) — o próprio livro oferece três métodos alternativos de PV à escolha do Mestre. **Terastal** troca tipo e defesas pelo botão da ficha; o STAB fica manual.
- **Mudanças de Status**: Precisão, Evasão, Velocidade e Margem de Crítico são automáticas; Defesa/Def. Especial (redução de dano por corpo a corpo/à distância) e o dano de Ataque/Atq. Especial ficam como registro no painel.

## Atualizando um mundo que já usa o módulo

Os compêndios mudam a cada versão, mas um Pokémon já importado, chocado ou capturado guarda a
cópia da versão em que entrou no mundo. Na primeira vez que o **Mestre** abre o mundo depois de
atualizar, o módulo ajusta esses Pokémon sozinho (uma vez só) e manda um resumo no chat. Na
v1.36.0 isso inclui completar deslocamentos que faltavam (só preenche modo em 0; o que foi
mexido à mão fica) e trocar os Moves dos níveis que o Pokémon ainda não alcançou pelos da
Pokédex. A macro **"Reparar Moves dos Pokémon"** faz a parte de Moves/Habilidades/Mega Pedras
de novo a qualquer momento (texto, PP, tempo de execução, tipo de dano, Habilidades ainda sem
texto e dados das Mega Pedras, inclusive no inventário de Treinadores e no diretório de Itens),
sem mexer no atributo que o jogador escolheu para cada Move.
- **PDFs de origem não incluídos no módulo** (grandes demais, direitos de terceiros) — os scripts esperam que você aponte para a pasta onde eles estão.
