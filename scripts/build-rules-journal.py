#!/usr/bin/env python3
"""
Compêndio de Regras (packs/_source/regras): traz pra dentro do Foundry, em JournalEntry bem
formatado (não é o texto cru extraído do PDF — foi reorganizado/limpo pra ficar fácil de
consultar na mesa), os capítulos do Livro de Regras que só existiam em PDF até agora: Bloco de
Estatísticas, Experiência do Treinador, Capturando Pokémon/Shiny, Condições (de Pokémon e
gerais), Mecânicas Especiais (Mega/Z-Move/Dynamax/Terastal), Mudanças de Status (+ regras
opcionais de acúmulo), Cuidados do Pokémon, Lealdade, Reprodução e Ovos, Evolução, Mecânica de
Combate/Batalhas em Dupla, Iniciativa e Ações em Combate, Movimento e Posição, Tabela de
Efetividade de Tipos, Moves (Poder/PP/Alcance/Duração), Itens Seguráveis/Consumíveis (mecânica —
o catálogo completo de itens já existe como Item de verdade no compêndio, não repetido aqui),
Guia de Pesca, Clima, Apêndice de Experiência por Nível e SR, e Regras Opcionais (Alpha/Totem).
Também traz uma subpasta "Homebrews" com regras não-oficiais criadas pela mesa (hoje: Sistema
de Captura Pokémon Ajustado, e Elo Rotomi — armazenamento/troca/porte de equipe).

Cada tópico é uma JournalEntry própria (facilita achar pelo nome na barra lateral do
compêndio), dentro da pasta "Regras" (ou da subpasta "Homebrews", pro conteúdo não-oficial).
Números de página citados são do Livro de Regras - Pokémon Mundo Perfeito.pdf; as homebrews
não têm página de livro — vieram de PDFs próprios da mesa.

Idempotente: pode rodar de novo, sempre reescreve os mesmos arquivos.

Uso: python scripts/build-rules-journal.py
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "regras")


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


# Foundry exige IDs com EXATAMENTE 16 caracteres alfanuméricos — "RegrasFolderRoot1" (17
# caracteres) passava despercebido no build, mas o Foundry rejeita o documento ao carregar o
# compêndio e derruba o carregamento do mundo inteiro. Gerado por hash pra não repetir esse
# erro de contagem manual (mesmo golpe em scripts/split-talentos.py).
FOLDER_ID = make_id("regras-folder-root")
# Subpasta dentro de "Regras" pra guardar homebrews de mesa (regras não-oficiais, criadas pelo
# grupo) separadas do conteúdo oficial do Livro de Regras.
HOMEBREW_FOLDER_ID = make_id("regras-folder-homebrews")


def stats():
    return {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
            "compendiumSource": None, "duplicateSource": None}


def write_folder(folder_id=FOLDER_ID, name="Regras", parent=None, filename=None, color="#88c0d0"):
    doc = {
        "_key": f"!folders!{folder_id}",
        "_id": folder_id, "name": name, "type": "JournalEntry", "folder": parent,
        "sorting": "m", "color": color, "flags": {}, "_stats": {}, "sort": 0
    }
    path = os.path.join(OUT_DIR, filename or f"folder-{name.lower()}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def journal(slug, name, sections, sort, folder=FOLDER_ID):
    """sections: lista de (título da página|None, html). Uma JournalEntryPage por seção."""
    entry_id = make_id(f"regras-{slug}")
    pages = []
    for i, (title, html) in enumerate(sections):
        page_id = make_id(f"regras-{slug}-page-{i}")
        pages.append({
            "_id": page_id,
            "name": title or name,
            "type": "text",
            "title": {"show": True, "level": 1},
            "text": {"content": html, "format": 1, "markdown": ""},
            "src": None,
            "system": {},
            "sort": (i + 1) * 100,
            "ownership": {"default": -1},
            "flags": {},
            "_stats": stats(),
            "_key": f"!journal.pages!{entry_id}.{page_id}"
        })
    doc = {
        "_key": f"!journal!{entry_id}",
        "_id": entry_id, "name": name, "pages": pages,
        "folder": folder, "sort": sort,
        "ownership": {"default": 2}, "flags": {}, "_stats": stats()
    }
    with open(os.path.join(OUT_DIR, f"regra-{slug}.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def build_experiencia_treinador():
    html = """
    <p>Os aumentos de nível para Treinadores acontecem imediatamente e não exigem descansos
    longos. O Livro de Regras (pág. 33) apresenta três opções — o Mestre escolhe qual delas usar
    na campanha (ou cria a própria, misturando ideias das três).</p>
    <h2>Opção 1 — Soma dos níveis da equipe</h2>
    <p>O nível do Treinador é definido pela soma dos níveis dos X Pokémon de <strong>maior
    nível</strong> em sua equipe, sendo X igual ao número atual de Pokéslots do Treinador. O
    Pokémon de maior nível não precisa estar sendo carregado por esse Treinador para contar.</p>
    <table>
      <thead><tr><th>Soma dos níveis</th><th>Nível do Treinador</th><th>Soma dos níveis</th><th>Nível do Treinador</th></tr></thead>
      <tbody>
        <tr><td>3</td><td>2º</td><td>50</td><td>11º</td></tr>
        <tr><td>6</td><td>3º</td><td>55</td><td>12º</td></tr>
        <tr><td>9</td><td>4º</td><td>60</td><td>13º</td></tr>
        <tr><td>12</td><td>5º</td><td>65</td><td>14º</td></tr>
        <tr><td>20</td><td>6º</td><td>70</td><td>15º</td></tr>
        <tr><td>24</td><td>7º</td><td>90</td><td>16º</td></tr>
        <tr><td>28</td><td>8º</td><td>96</td><td>17º</td></tr>
        <tr><td>32</td><td>9º</td><td>102</td><td>18º</td></tr>
        <tr><td>36</td><td>10º</td><td>108</td><td>19º</td></tr>
        <tr><td></td><td></td><td>114</td><td>20º</td></tr>
      </tbody>
    </table>
    <p><em>Exemplo: Ash está no nível 4 e tem quatro Pokémon nos níveis 4, 4, 3 e 2. Nesse nível
    ele só recebe três Pokéslots, então soma os três mais altos: 4+4+3=11, o que o mantém no 4º
    nível. Se um deles subir para o nível 5, o total (5+4+3=12) o leva ao 5º nível — e como ele
    ganha outro Pokéslot nesse nível, seu total para o PRÓXIMO cálculo passa a somar quatro
    Pokémon: 5+4+3+2=14.</em></p>
    <p>Este método pode atrapalhar quem não busca treinar vários Pokémon ao mesmo tempo, e um
    Treinador com Pokémon capturados recentemente em nível alto tende a ser mais fraco na prática
    do que um que cuidou dos mesmos Pokémon desde cedo, através de suas evoluções.</p>
    <h2>Opção 2 — Pokédex registrada</h2>
    <p>O nível do Treinador é baseado na quantidade de espécies diferentes que já capturou (ou
    seja, registradas na Pokédex). Alternativamente, o Mestre pode permitir registrar uma espécie
    de outras formas — lendo um livro específico, encontrando um artefato, conversando com um
    professor etc.</p>
    <table>
      <thead><tr><th>Pokémon registrados</th><th>Nível</th><th>Pokémon registrados</th><th>Nível</th></tr></thead>
      <tbody>
        <tr><td>8</td><td>2º</td><td>110</td><td>11º</td></tr>
        <tr><td>15</td><td>3º</td><td>122</td><td>12º</td></tr>
        <tr><td>25</td><td>4º</td><td>138</td><td>13º</td></tr>
        <tr><td>35</td><td>5º</td><td>154</td><td>14º</td></tr>
        <tr><td>45</td><td>6º</td><td>168</td><td>15º</td></tr>
        <tr><td>58</td><td>7º</td><td>178</td><td>16º</td></tr>
        <tr><td>75</td><td>8º</td><td>186</td><td>17º</td></tr>
        <tr><td>87</td><td>9º</td><td>192</td><td>18º</td></tr>
        <tr><td>100</td><td>10º</td><td>197</td><td>19º</td></tr>
        <tr><td></td><td></td><td>200</td><td>20º</td></tr>
      </tbody>
    </table>
    <p>É uma opção interessante para campanhas que começam em níveis mais altos, já que os
    jogadores podem escolher (com aprovação do Mestre) quais Pokémon já viram — o que costuma
    render histórias de fundo interessantes.</p>
    <h2>Opção 3 — XP determinado pelo Mestre</h2>
    <p>Nem todo jogador quer ser um Mestre Pokémon: alguns preferem colecionar, capturar shinys
    ou lendários, virar mestres de culinária, competir em concursos de beleza, ou se dedicar à
    pesquisa científica. Esta opção evita amarrar o nível do Treinador só a batalhas:</p>
    <ul>
      <li>O Mestre define a quantidade de XP concedida ao fim de cada cena ou sessão.</li>
      <li>É possível dar XP conforme cada jogador conclui atividades ligadas aos seus objetivos
      pessoais, recompensando ações que não envolvam batalha.</li>
      <li>Todos os Pokémon podem subir de nível automaticamente acompanhando o nível do
      Treinador (por exemplo: todo Pokémon tem no mínimo metade do nível do Treinador, ou no
      máximo 2 níveis a menos — assim, sempre que o Treinador sobe, os Pokémon sobem junto).</li>
    </ul>
    <p>Essa abordagem permite ajustar os níveis do Treinador e dos Pokémon conforme o ritmo da
    campanha e a dificuldade desejada, inclusive estabelecendo um nível máximo para o jogo.</p>
    """
    journal("experiencia-do-treinador", "Experiência do Treinador", [(None, html)], sort=30)


def build_bloco_estatisticas():
    html = """
    <p>São os dados informativos de cada Pokémon, encontrados na Pokédex deste módulo (compêndio
    "Pokédex"). Esta página explica o que cada ponto-chave do bloco de estatísticas significa —
    útil tanto pra ler uma ficha de Pokémon quanto pra entender as regras que citam esses campos.</p>
    <ul>
      <li><strong>Tipo:</strong> a tipagem do Pokémon, que impacta seu STAB e suas resistências,
      vulnerabilidades e imunidades (veja a Tabela de Efetividade de Tipos).</li>
      <li><strong>SR (Classificação de Espécie):</strong> um número que representa a força,
      raridade e complexidade de treinamento da espécie como um todo, independente do nível —
      um Pidgey de nível 10 (SR 1/8) não é tão forte quanto um Bulbasaur de nível 10 (SR 1/2).
      Serve de guia pra comparar espécies e para calcular a recompensa de experiência.</li>
      <li><strong>Nível Mínimo Encontrado:</strong> o nível mínimo em que este Pokémon pode ser
      encontrado na natureza.</li>
      <li><strong>Grupo de Ovos:</strong> este Pokémon só pode se reproduzir com outros do mesmo
      Grupo de Ovos (com algumas exceções — veja Reprodução e Ovos).</li>
      <li><strong>Gênero:</strong> a taxa de gênero encontrada na natureza, e a taxa com que um
      ovo que choque este Pokémon será macho ou fêmea.</li>
      <li><strong>Estágio Evolutivo:</strong> o estágio atual dentre os estágios evolutivos
      possíveis desta espécie (ex.: 2/3 — já evoluiu uma vez, ainda pode evoluir mais uma).</li>
      <li><strong>CA:</strong> não está vinculada à DES de forma alguma — é um número fixo por
      espécie, só aumentado por itens, Moves ou o talento "Aumento de CA".</li>
      <li><strong>Pontos de Vida / Dado de Vida:</strong> os PV são os encontrados no Nível
      Mínimo Encontrado da espécie; o Dado de Vida é usado em descansos curtos e para calcular o
      ganho de PV em níveis superiores.</li>
      <li><strong>Deslocamento:</strong> todos os tipos e alcances de deslocamento possíveis
      desta espécie (caminhada, natação, voo etc.).</li>
      <li><strong>Atributos:</strong> Força, Destreza, Constituição, Inteligência, Sabedoria e
      Carisma da espécie no Nível Mínimo Encontrado.</li>
      <li><strong>Perícias:</strong> este Pokémon adiciona seu bônus de proficiência em testes
      feitos com estas perícias. Perícias adicionais ou especializações podem ser adicionadas com
      aumentos de Lealdade.</li>
      <li><strong>Habilidade Passiva:</strong> um Pokémon só pode ter uma habilidade dentre as
      listadas nesse espaço. Se evoluir e a forma evoluída não tiver a habilidade atual, deve
      trocá-la por uma das opções não ocultas da forma evoluída.</li>
      <li><strong>Habilidade Oculta:</strong> só pode ser desbloqueada com o item Ability Patch,
      e substitui a Habilidade Passiva.</li>
      <li><strong>Sentidos:</strong> capacidades sensoriais especiais (visão no escuro, percepção
      às cegas etc.). Pokémon sem sentidos especiais não têm este campo.</li>
      <li><strong>Evolução:</strong> nível e método necessário para esta espécie evoluir (veja a
      página de Evolução).</li>
      <li><strong>Moves adquiridos em cada nível:</strong> um Pokémon pode conhecer, a qualquer
      momento, até quatro desses Moves (ou o talento Move Extra aumenta esse limite), incluindo
      os de níveis abaixo do atual. Pode trocar os Moves conhecidos a cada aumento de nível. Um
      Pokémon que evolui no mesmo nível em que aprenderia um Move novo (2, 6, 10, 14, 18) só pode
      aprender Moves do bloco de estatísticas da sua forma evoluída.</li>
      <li><strong>TMs:</strong> Moves que podem ser ensinados a esta espécie por TM.</li>
      <li><strong>Egg Moves:</strong> Moves que um filhote pode herdar dos Moves conhecidos pelos
      pais no momento da reprodução.</li>
      <li><strong>Defesas de tipo:</strong> indica as resistências (½ e ¼), vulnerabilidades (x2
      e x4) e imunidades (0) desta espécie contra os demais tipos — espaço em branco significa
      dano neutro. Veja a Tabela de Efetividade de Tipos para os valores completos.</li>
    </ul>
    """
    journal("bloco-de-estatisticas", "Lidando com Pokémon", [(None, html)], sort=20)


def build_capturando_e_shiny():
    html = """
    <h2>Capturando Pokémon</h2>
    <ul>
      <li>Um Treinador não pode carregar mais Pokémon do que seus Pokéslots permitem. Se estiverem
      cheios quando um Pokémon é capturado, o Treinador deve escolher um Pokémon para enviar ao
      PC.</li>
      <li>Uma Pokébola é destruída em uma tentativa fracassada de captura.</li>
      <li>Um Pokémon capturado mantém seu nível, as condições de status não-voláteis e a vida
      atual no momento da captura.</li>
      <li>Um Pokémon capturado recebe a quantidade mínima de experiência para o nível em que foi
      encontrado.</li>
      <li>Capturar um Pokémon também concede 1/5 do XP normal ao Treinador.</li>
      <li>Um Pokémon desmaiado não pode ser capturado.</li>
    </ul>
    <h3>Arremessar Pokébola</h3>
    <p><strong>Tempo de Execução:</strong> 1 ação. <strong>Alcance:</strong> 18 metros (60 pés).</p>
    <p>Ao realizar um Teste de Captura, role:</p>
    <p style="text-align:center"><strong>1d20 + 2 × Bônus de Proficiência + Bônus da Pokébola</strong></p>
    <p>O Bônus da Pokébola depende do tipo usado (veja a lista de Pokébolas no compêndio de
    Itens). Você tem vantagem na rolagem se o Pokémon estiver Envenenado, Queimado, Paralisado,
    Congelado, Sonolento, Dormindo, Confuso, Encantado ou Impedido.</p>
    <p>A CD de Captura é igual a:</p>
    <p style="text-align:center"><strong>10 + SR base do Pokémon (arred. p/ baixo) + nível do
    Pokémon + vida restante ÷ 10 (arred. p/ baixo)</strong></p>
    <p><em>Este módulo já calcula a CD de Captura automaticamente (ver <code>module/combat/capture.mjs</code>).</em></p>
    <p>Pokémon selvagens amigáveis e felizes podem se juntar a um Treinador sem uma Pokébola,
    através de um teste de Adestrar Animais (ou apenas pela narrativa da mesa).</p>
    <h2>Pokémon Brilhantes (Shiny)</h2>
    <p>Nem todos os Pokémon têm as mesmas cores que seus semelhantes — alguns nascem com
    pigmentações únicas e raríssimas. Apesar da aparência incomum, Pokémon Brilhantes
    <strong>não têm vantagens mecânicas</strong>: atributos, Natureza e potencial de combate são
    idênticos aos de qualquer outro indivíduo da mesma espécie. A singularidade é puramente
    estética.</p>
    <ul>
      <li><strong>Encontrando um Pokémon Brilhante:</strong> sempre que um Treinador encontrar um
      Pokémon selvagem, ele pode rolar 1d100 pra testar a sorte — em um resultado de 100, o
      Pokémon é Brilhante.</li>
      <li><strong>Hereditariedade Brilhante:</strong> sempre que um ovo Pokémon for gerado, role
      1d100. Se um dos pais for Brilhante, o filhote é Brilhante em um resultado de 96+. Se
      <em>ambos</em> os pais forem Brilhantes, o filhote é Brilhante em um resultado de 91+.</li>
    </ul>
    """
    journal("capturando-pokemon-e-shiny", "Capturando Pokémon e Pokémon Brilhantes", [(None, html)], sort=40)


def build_mecanicas_especiais():
    html = """
    <p>Pokémon Mundo Perfeito reúne quatro mecânicas de transformação em batalha, cada uma
    detalhada em seu próprio livro de regras — aqui vai só um resumo de quando cada uma se
    aplica.</p>
    <h2>Mega Evolução</h2>
    <p>Transforma um Pokémon numa versão muito mais poderosa de si mesmo durante a batalha. Só é
    possível quando o Treinador possui uma <strong>Pedra-Chave</strong> e o Pokémon está
    segurando uma <strong>Mega Pedra</strong> correspondente. É uma ação bônus, no início do
    turno; mudanças de atributos/estatísticas são imediatas (o aumento de DES só afeta a
    Iniciativa a partir da rodada seguinte). Sempre concede uma nova Habilidade Passiva
    (substituindo a anterior, mesmo se for Oculta), e pode alterar tipagem e tamanho. Atributos
    podem passar de 20, mas nunca de 30.</p>
    <h2>Z-Moves</h2>
    <p>Um Move especial criado pela combinação do poder de um Treinador com seu Pokémon —
    extremamente poderoso, mas usável só uma vez por batalha. Exige que o Pokémon possua um
    <strong>Cristal-Z</strong> e o Treinador um <strong>Bracelete-Z</strong> pra ativá-lo. Esses
    itens são raros, geralmente distribuídos por membros da Liga Pokémon.</p>
    <h2>Dynamax e Gigantamax</h2>
    <p>O Fenômeno Dynamax permite que um Pokémon assuma uma forma gigantesca durante a batalha,
    ampliando poder e resistência, e transformando seus Moves em versões muito mais impactantes.
    Só é possível quando o Treinador possui um item capaz de canalizar a energia Dynamax (como
    uma Pulseira Dynamax) e as condições do ambiente permitem. Gigantamax é uma variação ainda
    mais rara, que altera a aparência e concede acesso a Moves exclusivos — só pode ser usado por
    Pokémon que possuam essa capacidade especial.</p>
    <h2>Efeito Terastal</h2>
    <p>Um fenômeno raro que envolve um Pokémon em energia cristalina, fortalecendo sua ligação
    com um Tipo Tera específico — durante a batalha, pode alterar ou reforçar a tipagem do
    Pokémon. Só é possível quando o Treinador possui um <strong>Tera Orb</strong> carregado. Por
    ser uma energia intensa e difícil de controlar, seu uso costuma ser limitado a um momento
    certo da batalha.</p>
    <p><em>Cada uma dessas mecânicas tem regras completas em seu próprio livro (Mega Evoluções,
    Z-Moves, Geração 8 e Geração 9). Este módulo automatiza a Mega Evolução (ver
    <code>module/combat/mega-evolution.mjs</code> e o compêndio de Mega Evoluções) — Z-Move,
    Dynamax/Gigantamax e Terastalização ainda são conduzidos manualmente pelo Mestre.</em></p>
    """
    journal("mecanicas-especiais", "Mecânicas Especiais (Mega, Z-Move, Dynamax, Terastal)", [(None, html)], sort=60)


def build_cuidados_pokemon():
    html = """
    <h2>Cura</h2>
    <p>Existem quatro maneiras de curar um Pokémon:</p>
    <ul>
      <li>Levá-lo a um Centro Pokémon.</li>
      <li>Fazer um descanso curto ou longo.</li>
      <li>Dar-lhe poções ou comida.</li>
      <li>Usar habilidades de classe do Treinador ou Moves de cura.</li>
    </ul>
    <p>Um Pokémon reduzido a 0 PV fica inconsciente e não pode receber qualquer forma de cura até
    passar por um descanso longo, ser tratado em um Centro Pokémon, ou usar itens específicos
    como Revive.</p>
    <h2>Centros Pokémon</h2>
    <p>Instalações semelhantes a hospitais que curam Pokémon completamente em menos de 30
    minutos — gratuitas para quem tem Licença de Treinador, encontradas em abundância pelo
    mundo.</p>
    <h2>Descansando</h2>
    <p>Descansos longos (pelo menos 8 horas) renovam completamente saúde, status e PP de todos os
    Pokémon. Descansos curtos (pelo menos 30 minutos) recuperam pontos de vida a partir dos Dados
    de Vida do Pokémon — os PP não são recuperados, e um descanso curto não revive Pokémon
    desmaiados nem cura condições de status.</p>
    <h2>Poções/Comida</h2>
    <p>Itens perecíveis podem ser dados a um Pokémon como uma ação para restaurar instantaneamente
    pontos de vida ou aumentar temporariamente suas habilidades.</p>
    <h2>Vínculo</h2>
    <p>Criar um vínculo com o Pokémon é parte importante da rotina de um Treinador. Em cada
    descanso longo, é possível dedicar um tempo especial a um dos Pokémon — praticar exercícios,
    comer juntos, jogar, ou simplesmente desfrutar da companhia. Criar um vínculo tem dois
    benefícios, que duram até o próximo descanso longo:</p>
    <ul>
      <li>O Pokémon ganha pontos de vida temporários iguais ao seu nível.</li>
      <li>O Pokémon ganha uma Inspiração (gaste-a para conceder vantagem em uma jogada de
      ataque, teste de resistência ou teste de perícia).</li>
    </ul>
    <p><em>Este módulo já traz um botão de Inspiração no painel da ficha do Pokémon, pra marcar
    quando esse benefício foi concedido.</em></p>
    """
    journal("cuidados-do-pokemon", "Cuidados do Pokémon", [(None, html)], sort=150)


def build_reproducao_ovos():
    html = """
    <p>Ao final de cada dia da campanha (ou sessão), um jogador pode fazer com que dois de seus
    Pokémon carregados "se reproduzam" na tentativa de criar um ovo.</p>
    <h2>Regras Gerais</h2>
    <ul>
      <li>Pokémon só se reproduzem com outros pertencentes ao mesmo Treinador.</li>
      <li>Pokémon com Lealdade menor que +1 se recusam a reproduzir.</li>
      <li>Dois Pokémon só podem se reproduzir se forem de gêneros opostos e estiverem no mesmo
      Grupo de Ovos (com exceções — veja Ditto, abaixo).</li>
      <li>A espécie do Pokémon resultante é a forma evolutiva mais baixa da mãe, no nível mínimo
      encontrado do seu bloco de estatísticas (exceto se um Ditto tiver assumido o lugar da
      mãe).</li>
      <li>Segurar um ovo ocupa um Pokéslot do Treinador.</li>
    </ul>
    <p>Para saber se a tentativa foi bem-sucedida, role 1d20 direto contra uma CD baseada na soma
    das Lealdades dos dois pais:</p>
    <table>
      <thead><tr><th>Lealdade total</th><th>Sucesso na CD</th></tr></thead>
      <tbody>
        <tr><td>2</td><td>16</td></tr>
        <tr><td>3</td><td>14</td></tr>
        <tr><td>4+</td><td>10</td></tr>
      </tbody>
    </table>
    <h2>Incubação</h2>
    <p>Ao criar um ovo, ele inicia uma contagem regressiva de incubação. O progresso só avança se
    o ovo estiver sendo carregado pelo Treinador durante a noite ou boa parte da sessão anterior —
    role 1d100 no início de cada dia de campanha e reduza o contador pelo resultado. O tempo de
    eclosão depende da SR da espécie dentro do ovo:</p>
    <table>
      <thead><tr><th>SR</th><th>Tempo</th><th>SR</th><th>Tempo</th></tr></thead>
      <tbody>
        <tr><td>1/8</td><td>125</td><td>7</td><td>1200</td></tr>
        <tr><td>1/4</td><td>250</td><td>8</td><td>1300</td></tr>
        <tr><td>1/2</td><td>500</td><td>9</td><td>1400</td></tr>
        <tr><td>1</td><td>600</td><td>10</td><td>1500</td></tr>
        <tr><td>2</td><td>700</td><td>11</td><td>1600</td></tr>
        <tr><td>3</td><td>800</td><td>12</td><td>1700</td></tr>
        <tr><td>4</td><td>900</td><td>13</td><td>1800</td></tr>
        <tr><td>5</td><td>1000</td><td>14</td><td>1900</td></tr>
        <tr><td>6</td><td>1100</td><td>15</td><td>2000</td></tr>
      </tbody>
    </table>
    <p>Incubadoras (compradas por Treinadores mais abastados) reduzem esse tempo ainda mais —
    veja o item "Incubadora" no compêndio de Itens.</p>
    <h2>Momento de Espera — características do filhote</h2>
    <ul>
      <li><strong>Formas regionais:</strong> filhotes sempre nascem na forma nativa da região dos
      pais. Exceção: se um dos pais for de forma estrangeira e estiver segurando uma Everstone
      (e for da mesma linha evolutiva da mãe), o filhote nasce na forma desse pai.</li>
      <li><strong>Natureza:</strong> determinada por 1d20 contra a tabela de Natureza, sem
      relação com os pais — a menos que a mãe (ou o Ditto no lugar dela) esteja segurando uma
      Everstone, o que dá 50% de chance de manter a Natureza dela.</li>
      <li><strong>Gênero:</strong> determinado por 1d100 contra a Taxa de Gênero do bloco de
      estatísticas do filhote.</li>
      <li><strong>Moves herdados:</strong> ao chocar, é possível escolher quaisquer "Moves
      Iniciais" da lista de Moves do filhote como seus Moves conhecidos no nível 1. Dois tipos de
      Move entram automaticamente nessa lista: (1) qualquer Egg Move do filhote que seja
      <em>conhecido</em> por qualquer um dos pais no momento da reprodução; (2) qualquer Move
      conhecido por <em>ambos</em> os pais, desde que o filhote consiga aprendê-lo em sua
      progressão natural (TMs não contam).</li>
      <li><strong>Habilidade Passiva:</strong> role 1d20 ao chocar — em 5+, mantém a habilidade
      da mãe (ou do pai, se um Ditto ocupar o lugar dela); caso contrário, recebe a outra
      habilidade não oculta disponível (se houver). Se a mãe/Ditto tiver usado Ability Patch ou
      Ability Capsule, essa habilidade é passada ao filhote.</li>
      <li><strong>Lealdade:</strong> todo Pokémon chocado começa com Lealdade +1 (Contente). Se
      passar todo o período de incubação na equipe, sobe pra +2 (Satisfeito).</li>
    </ul>
    <h2>Casos especiais</h2>
    <ul>
      <li><strong>Ditto:</strong> é um Pokémon sem gênero — qualquer Pokémon pode se reproduzir
      com ele, independente de gênero ou Grupo de Ovos. A espécie resultante é sempre baseada no
      Pokémon "não Ditto".</li>
      <li>Pokémon Bebês e Lendários não podem se reproduzir (Grupo de Ovos "Não Descoberto").</li>
      <li>Algumas espécies têm gêneros com blocos de estatísticas próprios (ex.: Nidoran); cruzar
      com elas pode resultar numa espécie diferente da própria — role 1d100 contra a Taxa de
      Gênero listada.</li>
    </ul>
    <h2>Grupos de Ovos</h2>
    <p>Cada espécie pertence a um ou mais Grupos de Ovos (Monstro, Água 1/2/3, Humanoide,
    Inseto, Mineral, Fada, Voador, Ditto, Amorfo, Dragão, Campo, Grama, Não Descoberto), que
    determinam com quem ela pode se reproduzir. O Grupo de Ovos de cada espécie já está
    registrado em sua própria entrada na Pokédex — não repetido aqui.</p>
    """
    journal("reproducao-e-ovos", "Reprodução e Ovos", [(None, html)], sort=250)


def build_mecanica_combate():
    html = """
    <p>Esta página reúne as regras básicas do combate Pokémon — Jogadores e Mestre, Treinadores e
    Pokémon jogam pelas mesmas regras. O Mestre controla os Pokémon selvagens e os Treinadores
    controlados por ele; cada jogador controla seu Treinador e seus Pokémon.</p>
    <ul>
      <li>Durante um combate, cada Treinador normalmente mantém apenas um de seus Pokémon no
      campo por vez, a menos que as regras do combate digam o contrário. Fora de combate, os
      Pokémon podem ficar fora das Pokébolas e acompanhar o Treinador livremente.</li>
      <li>Um Treinador só consegue comandar um Pokémon a até 30 metros (100 pés) de distância —
      além disso, o Pokémon deixa de ouvir comandos e passa a agir por conta própria.</li>
      <li>No turno, Treinador e Pokémon têm ações de movimento e reações independentes, mas
      apenas um dos dois pode usar uma ação padrão ou bônus naquele turno.</li>
      <li>O papel do Treinador em combate é auxiliar seus Pokémon: interagir com o ambiente, usar
      itens, dar poções/melhorias, comandar ataques, tentar fugir etc.</li>
      <li>Trocar um Pokémon antes de ele desmaiar consome uma ação e acontece imediatamente — o
      novo Pokémon mantém a posição de iniciativa do anterior até a rodada seguinte, quando rola
      a própria. Se a troca ocorre <em>depois</em> de um desmaio, pode ser feita como ação livre,
      mas o novo Pokémon só entra no início da próxima rodada.</li>
      <li>É preciso ter ao menos um Pokémon em batalha o tempo todo — sem Pokémon disponíveis, o
      combate é perdido.</li>
      <li>Se um Pokémon ficar sem PP para todos os Moves, o único que pode usar é Struggle, a
      qualquer momento, independente dos PP restantes em outros Moves.</li>
    </ul>
    <h2>Batalhas em Dupla e em Grupo</h2>
    <p>Quando um Treinador tem mais de um Pokémon em campo ao mesmo tempo, Treinador e Pokémon
    passam a compartilhar uma reserva de ações:</p>
    <ul>
      <li>A quantidade de ações compartilhadas é igual à quantidade de Pokémon daquele Treinador
      em campo (2 numa batalha 2x2, 3 numa 3x3 etc.).</li>
      <li>Cada ação compartilhada pode ser usada como ação padrão ou bônus por qualquer membro do
      grupo — mas cada participante ainda só pode fazer uma ação desse tipo por turno.</li>
      <li>As ações compartilhadas podem ser distribuídas livremente: por exemplo, um Pokémon usa
      um Move enquanto o Treinador usa um item em outro Pokémon (que, por já ter recebido essa
      ação, não pode agir de novo naquele turno).</li>
      <li>As ações de movimento continuam independentes — Treinador e cada Pokémon se movem
      normalmente, mesmo sem gastar uma ação compartilhada.</li>
      <li>O grupo tem reações compartilhadas por rodada também iguais à quantidade de Pokémon em
      campo.</li>
      <li>Sempre que um Pokémon aliado for impedido de agir (Atordoamento, Paralisia, Confusão,
      Encantamento ou efeito parecido), o grupo perde 1 ação compartilhada naquele turno — essas
      perdas são cumulativas.</li>
      <li>Se todos os Pokémon de um Treinador estiverem impedidos de agir, ele ainda pode se
      mover, mas não pode usar ações compartilhadas naquele turno.</li>
    </ul>
    """
    journal("mecanica-de-combate", "Mecânica de Combate e Batalhas em Dupla", [(None, html)], sort=350)


def build_iniciativa_e_acoes():
    html = """
    <h2>Passo a Passo do Combate</h2>
    <ol>
      <li><strong>Determine surpresa.</strong> O Mestre decide se alguém está surpreso.</li>
      <li><strong>Estabeleça posições.</strong> O Mestre decide onde todos estão localizados.</li>
      <li><strong>Jogue iniciativa.</strong> Todos rolam para determinar a ordem dos turnos.</li>
      <li><strong>Jogue os turnos.</strong> Cada participante age na ordem da iniciativa.</li>
      <li><strong>Comece a próxima rodada.</strong> Repita até o combate acabar.</li>
    </ol>
    <h2>Iniciativa</h2>
    <p>Cada participante faz um teste de Destreza para definir sua posição na ordem — o Mestre
    joga pelos inimigos e NPCs. Do valor mais alto ao mais baixo; empates se resolvem pelo valor
    de Destreza (e, se ainda empatado, por 1d20). No início de uma batalha, o Treinador escolhe
    um de seus Pokémon para começar. Em combates entre Treinadores, ambos podem lançar seus
    Pokémon simultaneamente em segredo, ou cada Treinador pode rolar sua própria iniciativa
    primeiro (o de menor resultado lança seu Pokémon primeiro, dando ao oponente a vantagem de
    reagir).</p>
    <p>Uma rodada representa 6 segundos no mundo do jogo. O final de um turno é quando o jogador
    decide não fazer mais nada, passando a vez ao próximo na ordem.</p>
    <h3>Ordem de resolução no final do turno</h3>
    <ol>
      <li>Efeitos de Cura.</li>
      <li>Efeitos de Dano (Moves, habilidades, itens, clima, condição de status etc.).</li>
      <li>Contadores finais (habilidades passivas, término de efeitos como Perish Song/Yawn).</li>
    </ol>
    <h3>Surpresa</h3>
    <p>Se nenhum lado tenta ser furtivo, todos se percebem automaticamente. Caso contrário, o
    Mestre compara Destreza (Furtividade) de quem está escondido contra Sabedoria (Percepção
    Passiva) do lado oposto — quem não notar a ameaça está surpreso no início do encontro (e não
    pode se mover, agir ou reagir no primeiro turno).</p>
    <h2>Tipos de Ação</h2>
    <p>No turno, é possível fazer: <strong>uma ação padrão + uma ação de movimento</strong>,
    <strong>duas ações de movimento</strong> (chamado de "Disparada"), ou <strong>uma ação
    completa</strong> (abre mão das duas pra fazer algo que exige todo o esforço da rodada).
    Também é possível usar uma ação bônus e uma reação (1 vez por rodada cada), além de ações
    livres (quantas vezes quiser).</p>
    <ul>
      <li><strong>Ação Padrão:</strong> executa uma tarefa — usar um Move ou item são as mais
      comuns.</li>
      <li><strong>Ação de Movimento:</strong> normalmente percorrer uma distância até o
      deslocamento máximo; também cobre levantar-se ou pegar um item.</li>
      <li><strong>Ação Completa:</strong> exige abrir mão da ação padrão e da de movimento
      (ainda permite ações bônus, livres e reações).</li>
      <li><strong>Ação Bônus:</strong> concedida por habilidades, Moves ou características —
      apenas 1 por turno.</li>
      <li><strong>Reação:</strong> resposta automática a algo, mesmo fora do próprio turno
      (ataques de oportunidade são o tipo mais comum) — apenas 1 até o início do próximo turno.</li>
      <li><strong>Ação Livre:</strong> não exige quase nenhum tempo/esforço, mas só pode ser
      feita no próprio turno (jogar-se no chão, sacar uma Pokébola, gritar uma ordem curta
      etc.).</li>
    </ul>
    <h2>Ações em Combate</h2>
    <ul>
      <li><strong>Ajudar:</strong> concede vantagem a um aliado no próximo teste relacionado à
      atividade, ou no próximo ataque dele contra um alvo a até 1,5m de você.</li>
      <li><strong>Atacar:</strong> realiza um ataque corpo a corpo ou à distância.</li>
      <li><strong>Ativar um Move:</strong> Pokémon usam Moves pra causar dano ou aplicar
      efeitos — cada um tem seu próprio tempo de execução, alcance, duração e custo de PP.</li>
      <li><strong>Desengajar:</strong> seu movimento não provoca ataques de oportunidade pelo
      resto do turno.</li>
      <li><strong>Disparada:</strong> troca a ação padrão por uma segunda ação de movimento,
      ganhando deslocamento adicional igual ao seu deslocamento normal.</li>
      <li><strong>Esconder:</strong> teste de Destreza (Furtividade) pra tentar se esconder.</li>
      <li><strong>Esquivar:</strong> até o início do próximo turno, jogadas de ataque contra você
      sofrem desvantagem (se puder ver o atacante) e você tem vantagem em testes de Destreza.</li>
      <li><strong>Improvisar uma Ação:</strong> qualquer coisa não coberta pelas ações listadas —
      o Mestre decide se é possível e que teste ela exige.</li>
      <li><strong>Preparar Ação:</strong> usa a ação padrão pra definir um gatilho e a reação que
      ocorrerá quando ele acontecer (inclusive preparar um Move, reduzindo o PP na hora).</li>
      <li><strong>Procurar:</strong> foca a atenção em encontrar algo (teste de Percepção ou
      Investigação, conforme o caso).</li>
      <li><strong>Recolher/Liberar um Pokémon:</strong> trocar um Pokémon é uma ação no turno; se
      for por causa de um desmaio, pode ser uma ação livre.</li>
    </ul>
    """
    journal("iniciativa-e-acoes-em-combate", "Iniciativa e Ações em Combate", [(None, html)], sort=360)


def build_movimento_posicao():
    html = """
    <p>Durante o combate, Treinadores e Pokémon mudam de posição com frequência pra ganhar
    vantagem.</p>
    <h2>Movimento</h2>
    <p>Na ação de movimento, é possível se mover até o deslocamento máximo (ou menos), e é
    possível quebrar o movimento em partes antes/depois de uma ação, ou mesmo entre múltiplos
    ataques de uma mesma ação. Com mais de um tipo de deslocamento (ex.: caminhada e voo), dá pra
    intercalar entre eles durante o mesmo movimento.</p>
    <h2>Tipos de Terreno</h2>
    <table>
      <thead><tr><th>Terreno</th><th>Efeito resumido</th></tr></thead>
      <tbody>
        <tr><td>Difícil</td><td>Cada 1,5m custa 1,5m adicional (o espaço de outra criatura também
        conta como terreno difícil).</td></tr>
        <tr><td>Perigoso</td><td>Causa dano igual ao seu nível ao ser atravessado (apenas uma vez
        por turno, mesmo cruzando vários).</td></tr>
        <tr><td>Macio</td><td>Reduz pela metade o dano de queda.</td></tr>
        <tr><td>Sólido</td><td>Impede deslocamento de escavação (Moves como Dig não funcionam
        aqui).</td></tr>
        <tr><td>Escorregadio</td><td>Só dá pra se mover em linha reta; golpes corpo a corpo
        empurram atacante e alvo 1,5m para trás.</td></tr>
        <tr><td>Oculto</td><td>Permite se esconder como numa área fortemente obscurecida.</td></tr>
        <tr><td>Molhado</td><td>Moves elétricos de alvo único causam dano em área a criaturas
        próximas em contato com a água (teste de Destreza CD 10 pra metade do dano).</td></tr>
        <tr><td>Lamacento</td><td>Moves elétricos causam metade do dano nele.</td></tr>
        <tr><td>Movediço</td><td>É preciso se mover ao menos 1,5m no próprio turno, ou fica
        Impedido; pode se libertar com um teste de Força CD 10.</td></tr>
      </tbody>
    </table>
    <h2>Caído</h2>
    <p>Jogar-se no chão é uma ação livre; levantar-se custa metade do deslocamento. Enquanto
    caído, a única opção de movimento é rastejar (custa o dobro).</p>
    <h2>Elevado e No Chão</h2>
    <p>Uma criatura "Elevada" usa deslocamento de voo/flutuação, tem a habilidade Levitate/
    Eelevate, segura um Air Balloon, ou está sob efeito de Magnet Rise/Telekinesis — não é afetada
    por Moves do tipo Terra, Spikes, Toxic Spikes, Sticky Web, Arena Trap ou terreno difícil
    limitado ao chão. Uma criatura "No Chão" é qualquer uma sem essas condições (ou que teve seu
    voo/flutuação reduzido a zero).</p>
    <h2>Montarias e Saltos</h2>
    <p>Qualquer Pokémon com força adequada pode servir de montaria — o Treinador passa a usar as
    velocidades de deslocamento do Pokémon enquanto estiver nele (respeitando Capacidade de Carga
    e Sobrecarga). A Força determina a distância de salto: horizontalmente, 0,6m + 0,3m por ponto
    positivo de modificador de Força (metade disso sem pelo menos 3m de corrida antes); saltos
    verticais seguem a mesma lógica, na metade da distância se for sem corrida.</p>
    <h2>Cobertura</h2>
    <table>
      <thead><tr><th>Tipo</th><th>Bônus</th></tr></thead>
      <tbody>
        <tr><td>Meia-cobertura</td><td>+2 na CA e nos testes de resistência de Destreza.</td></tr>
        <tr><td>Três-quartos de cobertura</td><td>+5 na CA e nos testes de resistência de
        Destreza.</td></tr>
        <tr><td>Cobertura total</td><td>Não pode ser atacado diretamente.</td></tr>
      </tbody>
    </table>
    """
    journal("movimento-e-posicao", "Movimento e Posição", [(None, html)], sort=370)


def build_tabela_efetividade():
    labels = {
        "normal": "Normal", "fire": "Fogo", "water": "Água", "electric": "Elétrico",
        "grass": "Grama", "ice": "Gelo", "fighting": "Lutador", "poison": "Venenoso",
        "ground": "Terrestre", "flying": "Voador", "psychic": "Psíquico", "bug": "Inseto",
        "rock": "Pedra", "ghost": "Fantasma", "dragon": "Dragão", "dark": "Sombrio",
        "steel": "Aço", "fairy": "Fada"
    }
    # Mantido em sincronia manual com module/combat/type-chart.mjs (EFFECTIVENESS) — atacante -> {defensor: multiplicador}.
    effectiveness = {
        "normal": {"rock": 0.5, "ghost": 0, "steel": 0.5},
        "fire": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 2, "bug": 2, "rock": 0.5, "dragon": 0.5, "steel": 2},
        "water": {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2, "rock": 2, "dragon": 0.5},
        "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2, "dragon": 0.5},
        "grass": {"fire": 0.5, "water": 2, "grass": 0.5, "poison": 0.5, "ground": 2, "flying": 0.5, "bug": 0.5, "rock": 2, "dragon": 0.5, "steel": 0.5},
        "ice": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 0.5, "ground": 2, "flying": 2, "dragon": 2, "steel": 0.5},
        "fighting": {"normal": 2, "ice": 2, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2, "ghost": 0, "dark": 2, "steel": 2, "fairy": 0.5},
        "poison": {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0, "fairy": 2},
        "ground": {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2, "flying": 0, "bug": 0.5, "rock": 2, "steel": 2},
        "flying": {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2, "rock": 0.5, "steel": 0.5},
        "psychic": {"fighting": 2, "poison": 2, "psychic": 0.5, "dark": 0, "steel": 0.5},
        "bug": {"fire": 0.5, "grass": 2, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2, "ghost": 0.5, "dark": 2, "steel": 0.5, "fairy": 0.5},
        "rock": {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5, "flying": 2, "bug": 2, "steel": 0.5},
        "ghost": {"normal": 0, "psychic": 2, "ghost": 2, "dark": 0.5},
        "dragon": {"dragon": 2, "steel": 0.5, "fairy": 0},
        "dark": {"fighting": 0.5, "psychic": 2, "ghost": 2, "dark": 0.5, "fairy": 0.5},
        "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2, "rock": 2, "steel": 0.5, "fairy": 2},
        "fairy": {"fire": 0.5, "fighting": 2, "poison": 0.5, "dragon": 2, "dark": 2, "steel": 0.5}
    }
    types = list(labels.keys())

    def fmt(m):
        return {2: "×2", 0.5: "½", 0: "0"}.get(m, "")

    header = "<tr><th>Atacante ↓ / Defensor →</th>" + "".join(f"<th>{labels[t]}</th>" for t in types) + "</tr>"
    rows = []
    for atk in types:
        cells = "".join(f"<td>{fmt(effectiveness[atk].get(d, 1))}</td>" for d in types)
        rows.append(f"<tr><td><strong>{labels[atk]}</strong></td>{cells}</tr>")
    table_html = f"""
    <p>Multiplicador de dano de um ataque do <strong>tipo da linha (atacante)</strong> contra um
    Pokémon do <strong>tipo da coluna (defensor)</strong>. Células em branco são dano neutro
    (×1). Se o defensor tiver dois tipos, os dois multiplicadores se combinam (ex.: um Pokémon
    Dragão/Voador recebe ×4 de Gelo, e ÷4 de Grama).</p>
    <table style="font-size:0.72rem">
      <thead>{header}</thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    <p>Se um Pokémon é imune a um tipo de dano, não sofre nem o dano nem os efeitos secundários
    de Moves ofensivos desse tipo (embora ainda possa ser afetado por Moves não danosos do mesmo
    tipo). Pokémon são imunes a dano do próprio tipo quando esse dano não vem de um Move (ex.: um
    Pokémon do tipo Fogo não sofre dano ao atravessar chamas comuns) — Pokémon do tipo Fantasma
    são imunes a qualquer dano fora de um Move. Essa imunidade ambiental não se aplica a Moves.</p>
    """
    journal("tabela-de-efetividade-de-tipos", "Tabela de Efetividade de Tipos", [(None, table_html)], sort=380)


def build_moves_mecanicas():
    html = """
    <h2>Poder do Move</h2>
    <p>A maioria dos Moves tem um Poder do Move — o atributo focado por ele, referenciado nas
    descrições simplesmente como "MOVE". Determina qual modificador usar para ataque, dano e CD
    de testes de resistência:</p>
    <p style="text-align:center"><strong>Bônus de Rolagem de Ataque = MOVE + Proficiência</strong><br/>
    <strong>Bônus de Dano = MOVE (+ STAB, se aplicável)</strong><br/>
    <strong>CD de Testes de Resistência = 8 + Proficiência + MOVE</strong></p>
    <h2>PP do Move</h2>
    <p>Cada Move tem Pontos de Poder (PP), que determinam quantas vezes pode ser usado. PP é
    recarregado em descansos longos, ou com itens como Ether. Sem PP em nenhum Move, o único que
    pode ser usado é Struggle, a qualquer momento.</p>
    <h2>Alcance</h2>
    <p>O alvo de um Move precisa estar dentro do alcance dele — expresso em metros, ou como
    "Pessoal" (afeta só quem usa, ou cones/linhas originados no usuário), ou exigindo toque.</p>
    <h2>Duração</h2>
    <ul>
      <li><strong>Instantâneo:</strong> causa dano, cura ou altera algo de imediato, não pode ser
      dissipado.</li>
      <li><strong>Concentração:</strong> o efeito exige concentração contínua — termina se ela for
      quebrada (sofrer dano exige um teste de Constituição, CD 10 ou metade do dano recebido, o
      que for maior; ativar outro Move de concentração; ficar incapacitado ou morrer).</li>
      <li><strong>Enquanto ativo:</strong> o efeito dura enquanto o alvo permanecer em combate —
      termina se ele voltar pra Pokébola ou o combate acabar. Todas as Mudanças de Status usam
      esta duração.</li>
    </ul>
    <h2>Áreas de Efeito</h2>
    <p>Alguns Moves cobrem uma área inteira. Cada área tem um ponto de origem, e o efeito se
    espalha em linha reta a partir dele (locais atrás de cobertura total ficam de fora):</p>
    <ul>
      <li><strong>Cone:</strong> se estende numa direção, aumentando de largura com a
      distância.</li>
      <li><strong>Linha:</strong> se estende em linha reta, com comprimento e largura
      definidos.</li>
      <li><strong>Círculo/Raio:</strong> se expande em todas as direções a partir da origem — o
      tamanho de um círculo é o dobro do seu raio.</li>
    </ul>
    <h2>Testes de Resistência de Moves</h2>
    <p>Muitos Moves permitem um teste de resistência pra evitar parte ou todo o efeito. A CD é:</p>
    <p style="text-align:center"><strong>CD = 8 + Poder do Move + Bônus de Proficiência</strong></p>
    <p>Um 20 natural no teste de resistência sempre anula dano e efeitos do Move para aquele
    alvo. Um 1 natural torna o ataque um acerto crítico, dobrando os dados de dano recebidos.</p>
    """
    journal("moves-poder-pp-alcance-e-duracao", "Moves: Poder, PP, Alcance e Duração", [(None, html)], sort=390)


def build_clima():
    def weather_table(rows):
        body = "".join(
            f"<tr><td>{d100}</td><td>{clima}</td><td>{moves}</td></tr>" for d100, clima, moves in rows
        )
        return f"""
        <table>
          <thead><tr><th>d100</th><th>Clima</th><th>Moves Afetados (vantagem no dano)</th></tr></thead>
          <tbody>{body}</tbody>
        </table>"""

    spring_summer = weather_table([
        ("1-25", "Sol Forte, Calmo", "Grama, Terra, Fogo"),
        ("26-35", "Sol Forte, Ventoso", "Grama, Terra, Fogo, Voador, Dragão, Psíquico"),
        ("36-65", "Nublado, Calmo", "Normal, Pedra, Fada, Lutador, Venenoso"),
        ("66-75", "Nublado, Ventoso", "Normal, Pedra, Fada, Lutador, Venenoso, Voador, Dragão, Psíquico"),
        ("76-80", "Nebuloso", "Sombrio, Fantasma"),
        ("81-90", "Garoa Leve", "Água, Elétrico, Inseto"),
        ("91-99", "Chuva Forte", "Água, Elétrico, Inseto"),
        ("100", "Tempestade Perigosa", "Água, Elétrico, Inseto")
    ])
    fall_winter = weather_table([
        ("1-15", "Sol Forte, Calmo", "Grama, Terra, Fogo"),
        ("16-25", "Sol Forte, Ventoso", "Grama, Terra, Fogo, Voador, Dragão, Psíquico"),
        ("26-40", "Nublado, Calmo", "Normal, Pedra, Fada, Lutador, Venenoso"),
        ("41-50", "Nublado, Ventoso", "Normal, Pedra, Fada, Lutador, Venenoso, Voador, Dragão, Psíquico"),
        ("51-60", "Nebuloso", "Sombrio, Fantasma"),
        ("61-70", "Garoa Leve", "Água, Elétrico, Inseto"),
        ("71-80", "Chuva Forte", "Água, Elétrico, Inseto"),
        ("81-90", "Neve Leve", "Gelo, Aço"),
        ("91-99", "Nevasca Forte", "Gelo, Aço"),
        ("100", "Tempestade de Neve", "Gelo, Aço")
    ])
    html = f"""
    <p>O clima desempenha um grande papel no jogo — muitos Pokémon têm habilidades afetadas pelo
    clima ou terreno ao redor, e o clima pode reforçar certos tipos. Role 1d100 no início de cada
    dia (ou defina pelo que está acontecendo de verdade fora da mesa) contra a tabela da estação
    atual. Os efeitos abaixo são simplificados dos jogos principais e são totalmente opcionais:
    cada Move do tipo listado em "Moves Afetados" pode rolar seus dados de dano duas vezes e usar
    o resultado mais alto.</p>
    <h2>Primavera/Verão</h2>
    {spring_summer}
    <h2>Outono/Inverno</h2>
    {fall_winter}
    <h2>Granizo e Tempestade de Areia</h2>
    <p>Fenômenos especiais que podem surgir naturalmente ou serem criados por Moves/habilidades
    (Hail, Sandstorm, Snow Warning, Sand Stream). Quando gerados por um desses, seguem as regras
    da própria origem. Quando naturais (sem um Pokémon causando), valem estas regras:</p>
    <ul>
      <li>Não causam dano ao final do turno.</li>
      <li>Visibilidade reduzida (9, 6 ou 3 metros, conforme a intensidade).</li>
      <li>Ataques à distância sempre em desvantagem.</li>
      <li>Exposição de 30+ minutos sem proteção causa 1d4 de dano sem tipo a cada intervalo
      (hipotermia/ferimentos leves).</li>
      <li>Pokémon do tipo Gelo ignoram penalidades e têm vantagem contra Granizo; Pokémon dos
      tipos Terra, Pedra e Aço ignoram penalidades e têm vantagem contra Tempestade de Areia.</li>
    </ul>
    <p><em>Use os botões "🌦️ Rolar Clima (Primavera/Verão)" e "❄️ Rolar Clima (Outono/Inverno)"
    nas macros deste módulo pra rolar 1d100 contra a tabela certa e postar o resultado no chat
    automaticamente.</em></p>
    """
    journal("clima", "Clima", [(None, html)], sort=600)


def build_apendice_xp():
    header_low = ["1/8", "1/4", "1/2", "1", "2", "3", "4", "5", "6"]
    table_low = [
        [20, 40, 80, 160, 360, 560, 880, 1400, 1800],
        [40, 80, 160, 360, 560, 880, 1400, 1800, 2300],
        [80, 150, 340, 530, 840, 1400, 1700, 2200, 3000],
        [140, 320, 500, 790, 1300, 1700, 2100, 2800, 3600],
        [360, 560, 880, 1400, 1800, 2300, 3100, 4000, 4700],
        [530, 840, 1400, 1700, 2200, 3000, 3800, 4500, 5500],
        [820, 1300, 1700, 2200, 2900, 3700, 4400, 5400, 6200],
        [1300, 1700, 2100, 2800, 3600, 4300, 5200, 6100, 7300],
        [1600, 2000, 2700, 3500, 4200, 5100, 5900, 7000, 8100],
        [2300, 3100, 4000, 4700, 5800, 6700, 8000, 9200, 10400],
        [3000, 3800, 4500, 5500, 6500, 7700, 8800, 10000, 10800],
        [3800, 4400, 5400, 6300, 7500, 8600, 9800, 10500, 11100],
        [4300, 5300, 6200, 7400, 8500, 9600, 10300, 10900, 11400],
        [5200, 6000, 7200, 8300, 9400, 10100, 10600, 11200, 11900],
        [5900, 7000, 8100, 9200, 9900, 10400, 10900, 11600, 12700],
        [6900, 7900, 8900, 9600, 10100, 10700, 11400, 12400, 13400],
        [9200, 10400, 11200, 11800, 12400, 13200, 14400, 15600, 16800],
        [10000, 10800, 11300, 11900, 12700, 13800, 15000, 16100, 17700],
        [10500, 11100, 11700, 12400, 13500, 14700, 15800, 17300, 18800],
        [10900, 11400, 12100, 13200, 14400, 15500, 16900, 18400, 19900]
    ]
    header_high = ["7", "8", "9", "10", "11", "12", "13", "14", "15"]
    table_high = [
        [2300, None, None, None, None, None, None, None, None],
        [3100, None, None, None, None, None, None, None, None],
        [3800, None, None, None, None, None, None, None, None],
        [4200, None, None, None, None, None, None, None, None],
        [5800, 6700, 8000, 9200, 10400, None, None, None, None],
        [6400, 7600, 8700, 9900, 10600, None, None, None, None],
        [7400, 8600, 9700, 10400, 11000, None, None, None, None],
        [8400, 9500, 10200, 10700, 11300, 12200, 13400, None, None],
        [9200, 9900, 10400, 10900, 11600, 12600, 14200, None, None],
        [11200, 11800, 12400, 13200, 14400, 15600, 16800, 18400, None],
        [11300, 11900, 12700, 13800, 15000, 16100, 17700, 19200, None],
        [11700, 12400, 13500, 14700, 15800, 17300, 18800, 20300, None],
        [12100, 13200, 14400, 15500, 16900, 18400, 19900, 21700, None],
        [13000, 14000, 15100, 16600, 18000, 19400, 21200, 23000, None],
        [13700, 14800, 16200, 17600, 19000, 20800, 22500, 24600, 26800],
        [14400, 15800, 17200, 18600, 20300, 22000, 24100, 26100, 28200],
        [18400, 20000, 21600, 23600, 25600, 28000, 30400, 32800, 36000],
        [19200, 20700, 22700, 24600, 26900, 29200, 31500, 34600, 38400],
        [20300, 22200, 24100, 26300, 28600, 30800, 33800, 37600, 42300],
        [21700, 23600, 25800, 28000, 30200, 33100, 36800, 41400, 46000]
    ]

    def render(header, table):
        head = "<tr><th>Nível \\ SR</th>" + "".join(f"<th>{h}</th>" for h in header) + "</tr>"
        rows = []
        for i, row in enumerate(table, start=1):
            cells = "".join(f"<td>{v:,}</td>" if v is not None else "<td>—</td>" for v in row)
            rows.append(f"<tr><td><strong>{i}º</strong></td>{cells}</tr>")
        return f"<table style='font-size:0.75rem'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"

    html = f"""
    <p>Experiência dada ao Treinador por derrotar um Pokémon selvagem, cruzando o
    <strong>nível</strong> do Pokémon derrotado com sua <strong>SR</strong> (já indicada no bloco
    de estatísticas de cada espécie na Pokédex deste módulo). Capturar em vez de derrotar concede
    apenas 1/5 desse valor.</p>
    {render(header_low, table_low)}
    {render(header_high, table_high)}
    <p><em>Este módulo mostra, na biografia de cada Pokémon da Pokédex, o XP dado ao ser
    derrotado no seu Nível Mínimo Encontrado — para outros níveis, use esta tabela.</em></p>
    """
    journal("apendice-de-experiencia-por-nivel-e-sr", "Apêndice: Experiência por Nível e SR", [(None, html)], sort=700)


def build_alpha_totem():
    alpha = """
    <p>Um Pokémon Alpha é uma criatura selvagem que se destaca por tamanho, força e presença
    intimidadora — versões excepcionais de suas espécies, visivelmente maiores e mais poderosas
    que os exemplares comuns. Seus olhos costumam brilhar em tom avermelhado.</p>
    <h2>Características</h2>
    <ul>
      <li>Tamanho aumentado em duas escalas em relação ao normal da espécie.</li>
      <li>Nível superior ao encontrado normalmente na natureza.</li>
      <li>+2 em três atributos, sendo Constituição obrigatoriamente um deles.</li>
      <li>Possui 1 Move de nível avançado (ou proveniente de sua evolução).</li>
      <li>Possui naturalmente o talento Aumento de CA.</li>
      <li>+5 na CD de Captura.</li>
      <li>Natureza orgulhosa e dominante — mais difícil de conquistar, mais propenso a perder
      Lealdade se sentir desrespeito.</li>
    </ul>
    <h3>Habilidade: Liderança</h3>
    <p>Pokémon do mesmo tipo em um raio de 18 metros do Alpha recebem +1 em jogadas de ataque e
    +1 no dano. Não é cumulativo — se dois ou mais Alphas aliados estiverem em campo, todos
    perdem esta habilidade (entram em conflito pela supremacia).</p>
    <h3>Pokémon Alpha Selvagens</h3>
    <p>Enquanto não forem derrotados ou capturados: olhos brilham em vermelho intenso, +1 em
    todos os atributos, e sofrem metade do dano causado por Condições de Status.</p>
    """
    totem = """
    <p>Um Pokémon Totem é reverenciado como espírito guardião de um território, ou manifestação
    da força vital de uma área sagrada — reconhecido pelo tamanho incomum e pela aura poderosa
    que emana. Normalmente pertence a um Treinador (líderes regionais, guardiões espirituais), o
    que o torna não capturável, embora exemplares selvagens possam existir em locais isolados.</p>
    <h2>Características</h2>
    <ul>
      <li>Tamanho aumentado em duas escalas em relação ao normal da espécie.</li>
      <li>Nível superior ao encontrado normalmente na natureza.</li>
      <li>+2 em três atributos, sendo Constituição obrigatoriamente um deles.</li>
      <li>Possui naturalmente o talento Aumento de CA.</li>
      <li>Pode conhecer TMs, por ser criado por um Mestre Pokémon.</li>
    </ul>
    <h3>Habilidade: Aura Totêmica</h3>
    <p>Pokémon da mesma espécie (independente do estágio evolutivo) a até 18 metros do Totem
    recebem +1 em jogadas de ataque e +1 em dano. O Totem tem vantagem em todos os testes de
    perícia contra outros Pokémon de sua espécie (incluindo evoluções ou pré-evoluções).</p>
    <h3>Pokémon Totem Selvagens</h3>
    <p>Podem chamar reforços da mesma espécie. Como ação bônus, role 1d20 (máximo de 2 aliados
    invocados por Treinador enfrentando o Totem, por batalha):</p>
    <table>
      <thead><tr><th>d20</th><th>Resultado</th></tr></thead>
      <tbody>
        <tr><td>1–10</td><td>Nada acontece.</td></tr>
        <tr><td>11–18</td><td>Surge 1 aliado.</td></tr>
        <tr><td>19–20</td><td>Surgem 2 aliados.</td></tr>
      </tbody>
    </table>
    """
    journal("regras-opcionais-alpha-e-totem", "Regras Opcionais: Pokémon Alpha e Pokémon Totem", [
        ("Pokémon Alpha", alpha),
        ("Pokémon Totem", totem)
    ], sort=800)


def build_mudancas_de_status():
    intro = """
    <p>As Mudanças de Status representam alterações temporárias nos atributos de um Pokémon
    durante a batalha, sempre provocadas por Moves ou habilidades passivas. Elas expressam
    momentos em que o Pokémon ganha ou perde foco, confiança, precisão ou força, afetando
    diretamente seu desempenho em combate.</p>
    <p>Essas variações são medidas em <strong>estágios</strong>, que indicam aumentos ou
    reduções em valores de Ataque, Ataque Especial, Defesa, Defesa Especial, Velocidade,
    Precisão, Evasão e Margem de Crítico.</p>
    <p>Como são efeitos dinâmicos, as Mudanças de Status não são permanentes. Elas duram
    apenas enquanto o Pokémon afetado permanecer em combate, e podem ser substituídas,
    acumuladas ou anuladas por novos efeitos. O uso fora de combate dura 1 minuto, e se o
    combate começar nesse intervalo, o efeito permanece ativo até o fim dele.</p>
    <table>
      <thead><tr><th>Mudança de Status</th><th>Efeito de 1 estágio</th></tr></thead>
      <tbody>
        <tr><td>Ataque</td><td>Adicione seu bônus de proficiência ao dano de ataques corpo a corpo.</td></tr>
        <tr><td>Ataque Especial</td><td>Adicione seu bônus de proficiência ao dano de ataques à distância.</td></tr>
        <tr><td>Defesa</td><td>Reduza o dano recebido de ataques corpo a corpo em um valor igual ao seu bônus de proficiência.</td></tr>
        <tr><td>Defesa Especial</td><td>Reduza o dano recebido de ataques à distância em um valor igual ao seu bônus de proficiência.</td></tr>
        <tr><td>Velocidade</td><td>Seu deslocamento aumenta em 5 pés (1,5 metros), aplicável a todos os tipos de deslocamento. Sua iniciativa também aumenta num valor igual ao seu bônus de proficiência.</td></tr>
        <tr><td>Precisão</td><td>Adicione +1 nas rolagens de ataque e na CD dos Moves.</td></tr>
        <tr><td>Evasão</td><td>Adicione +1 na CA e nos testes de resistência.</td></tr>
        <tr><td>Margem de Crítico</td><td>Aumente a margem de crítico em +3.</td></tr>
      </tbody>
    </table>
    <ul>
      <li>Considere ataques à distância todos aqueles que não forem corpo a corpo — isso inclui tanto Moves de acerto quanto Moves que exigem testes de resistência.</li>
      <li>Quando os bônus de Velocidade forem removidos ou dissipados, o Pokémon retorna à sua iniciativa original. Alterações na iniciativa causadas por modificações na Velocidade passam a valer apenas a partir da rodada seguinte.</li>
      <li>Moves que possuem múltiplos golpes só podem aplicar ou serem afetados por Mudanças de Status no primeiro golpe.</li>
      <li>Quando um Move acerta um golpe crítico, os estágios negativos do atacante e os estágios positivos do defensor são sempre ignorados.</li>
    </ul>
    <h2>Estágios negativos</h2>
    <p>As Mudanças de Status podem se acumular de maneira negativa, gerando o efeito oposto ao
    da tabela acima: Ataque e Ataque Especial <strong>reduzem</strong> o dano causado em um
    valor igual ao bônus de proficiência do próprio usuário, enquanto Defesa e Defesa Especial
    <strong>aumentam</strong> o dano recebido com base na proficiência de quem possui os
    estágios negativos (não na do atacante). As demais mudanças reduzem de maneira
    equivalente. Margem de Crítico é a única incapaz de ser reduzida.</p>
    <h2>Acumulando estágios</h2>
    <p>Cada status pode ser acumulado até um máximo de <strong>6 estágios positivos ou 6
    negativos</strong>, sendo que um tipo de estágio reduz a quantidade do outro. Exemplo: se
    um Pokémon possui 2 estágios positivos de Ataque e o inimigo usa um Move que reduz seu
    Ataque em 3 estágios, o Pokémon passa a ter 1 estágio negativo de Ataque.</p>
    <ul>
      <li>Ataque e Ataque Especial adicionam/subtraem seu bônus de proficiência ×1/×2/×3/×4/×5/×6 ao dano.</li>
      <li>Defesa e Defesa Especial reduzem/aumentam o dano recebido em um valor igual ao seu bônus de proficiência ×1/×2/×3/×4/×5/×6.</li>
      <li>Velocidade aumenta/reduz o deslocamento em 5 pés (1,5 metros) ×1/×2/×3/×4/×5/×6, e adiciona/subtrai o bônus de proficiência ×1/×2/×3/×4/×5/×6 na ordem de iniciativa.</li>
      <li>Precisão e Evasão aumentam/reduzem seus respectivos valores em 1/2/3/4/5/6.</li>
      <li>Margem de Crítico aumenta em +3/+6/+9/+12/+15/+18 — vale tanto para rolagens de acerto (abaixo de 20 no dado) quanto para testes de resistência (acima de 1 no dado).</li>
    </ul>
    <p><em>Este módulo já aplica automaticamente o bônus de Precisão/Evasão/Velocidade
    (Defesa, Defesa Especial e Margem de Crítico ficam só como registro visível no painel de
    estágios da ficha — sem uma chave de efeito automática confirmada). O bônus de dano de
    Ataque/Ataque Especial fica por conta do jogador somar na hora de rolar, para manter a
    fórmula de dano do Move sempre visível e simples.</em></p>
    """
    optional = """
    <p>O acúmulo de estágios pode gerar desequilíbrios, especialmente em combates mais
    amplos: Pokémon podem aproveitar posições estratégicas ou passar vários turnos usando
    Moves que aumentam Mudanças de Status sem limites, tornando algumas batalhas mais longas
    ou previsíveis do que o desejado. Para equilibrar o jogo, é <strong>extremamente
    recomendado</strong> que o Mestre adote uma das regras opcionais abaixo.</p>
    <h2>Acúmulos de fontes diferentes</h2>
    <p>Uma forma de evitar o uso repetitivo de um mesmo Move para Mudança de Status, sem
    eliminar completamente a mecânica de acúmulos, é determinar que aumentos ou reduções em
    Mudanças de Status só podem ocorrer quando vindos de <strong>fontes diferentes</strong>.
    Usar repetidamente o mesmo Move não gera efeito adicional.</p>
    <ul>
      <li>Moves de Status (que não causam dano direto) que aumentem ou diminuam Mudanças de
      Status em si ou em um inimigo não acumulam efeitos se usados repetidas vezes, exceto
      para repor uma quantidade perdida. Exemplo: se um Pokémon usar Work Up (Ataque +1) e
      depois tiver o Ataque reduzido para -2 por um Move inimigo, ele pode usar Work Up de
      novo pra recuperar os estágios perdidos, mas só até voltar ao máximo anterior de +1.</li>
      <li>Moves danosos com Mudança de Status como efeito secundário, e habilidades passivas,
      são as únicas exceções — seus efeitos podem se acumular normalmente mesmo vindos do
      mesmo Move ou habilidade.</li>
    </ul>
    <h2>Sem acúmulo de estágios</h2>
    <p>Se o objetivo é tornar o combate mais prático, o Mestre pode optar por ignorar o
    acúmulo de estágios por completo — as batalhas ficam mais dinâmicas e próximas da
    experiência vista no anime e no mangá. Todo Move ou habilidade passiva que aumente ou
    diminua Mudanças de Status só produz a quantidade de estágios indicada em sua descrição,
    sem acumular efeitos de usos ou ativações repetidas, nem de outros Moves.</p>
    <ul>
      <li>Ao usar Swords Dance, o Ataque aumenta em 2 estágios. Usar de novo não tem efeito, a
      menos que o Ataque tenha sido reduzido, permitindo usar de novo até recuperar o máximo
      de 2 estágios.</li>
      <li>Se um Pokémon usa um Move que aumenta 1 estágio e depois outro que aumenta 2 do
      mesmo status, o total fica limitado a 2 estágios (o maior dos dois, não a soma).</li>
      <li>Se o Pokémon já possui 2 estágios de Ataque (por Swords Dance) e usa Work Up
      (+1 Ataque e +1 Ataque Especial), o Ataque não recebe efeito adicional, mas o Ataque
      Especial ainda ganha seu +1 normalmente.</li>
    </ul>
    """
    journal("mudancas-de-status", "Mudanças de Status", [
        ("Mudanças de Status", intro),
        ("Regras Opcionais de Acúmulo", optional)
    ], sort=100)


def build_lealdade():
    html = """
    <p>O vínculo entre um Pokémon e seu Treinador nem sempre é estável; pode aumentar e
    diminuir à medida que as duas partes interagem entre si. A relação passa por vários
    níveis de <strong>Lealdade</strong>, que afetam a capacidade do Pokémon, como ele obedece
    ao Treinador, e até se certos Pokémon podem evoluir.</p>
    <p>O nível de Lealdade é sempre determinado pelo Mestre. Exemplos de aumento: criar um
    vínculo com o Pokémon várias vezes, procurar petiscos que ele goste, vencer uma batalha
    particularmente difícil. Exemplos de redução: capturar um Pokémon de forma não merecida,
    deixá-lo no PC por muito tempo, permitir que desmaie envenenado em vez de curá-lo com
    antídoto. Os extremos da escala devem ser mais difíceis de alcançar do que os níveis
    próximos do Neutro — raramente um Pokémon deve alcançar -3 ou +3 sem circunstâncias
    extremas.</p>
    <table>
      <thead><tr><th>Nível</th><th>Emoção</th><th>Efeito</th></tr></thead>
      <tbody>
        <tr><td>-3</td><td>Desleal</td><td>Têm desdém por serem capturados e preferiam ser
        livres — desobedecem ativamente ordens. Mesma penalidade de resistência que
        "Chateado"/"Indiferente" (-1). Antes de ativar um Move, o Treinador deve rolar mais
        que 15 em 1d20 ou o Move falha.</td></tr>
        <tr><td>-2</td><td>Indiferente</td><td>Não se importam se o Treinador ganha ou perde;
        às vezes obedecem, às vezes se recusam. Mesma penalidade de resistência que
        "Chateado" (-1). Antes de ativar um Move, o Treinador deve rolar mais que 10 em 1d20
        ou o Move falha.</td></tr>
        <tr><td>-1</td><td>Chateado</td><td>Mantêm um pequeno rancor que os afeta em
        batalha: -1 em qualquer teste de resistência.</td></tr>
        <tr><td>0</td><td>Neutro</td><td>Age normalmente, sem modificadores. Responde aos
        comandos do Treinador e age por conta própria fora de combate. A maioria dos Pokémon
        recém-capturados começa neste nível ou abaixo.</td></tr>
        <tr><td>+1</td><td>Contente</td><td>Mostra afeto e respeito pelo Treinador. Pokémon
        capturados raramente começam num nível mais alto que este. +1 em qualquer teste de
        resistência.</td></tr>
        <tr><td>+2</td><td>Satisfeito</td><td>Deposita grande confiança no Treinador. Mesmo
        bônus de resistência que "Contente" (+1). Além disso, aumenta os PV máximos em metade
        do nível (arredondado para cima) e ganha uma perícia proficiente à escolha (se cair
        abaixo deste nível e voltar, a mesma perícia deve ser escolhida de novo).</td></tr>
        <tr><td>+3</td><td>Leal</td><td>Vínculo incrível, disposto a arriscar a própria vida
        pela segurança do Treinador. Mesmo bônus de resistência e perícia proficiente que
        "Satisfeito". O aumento máximo de PV se torna igual ao nível cheio (não mais metade),
        e a perícia escolhida vira especialista (dobro do bônus de proficiência).</td></tr>
      </tbody>
    </table>
    <p><em>Este módulo já traz um campo de Lealdade na própria ficha do Pokémon (painel
    superior, ao lado de Inspiração/XP), com o bônus/penalidade de teste de resistência de
    cada nível aplicado automaticamente. O restante dos efeitos de cada nível (chance do Move
    falhar, aumento de PV máximo, escolha de perícia) fica documentado no próprio campo — é
    o Mestre quem aplica na hora que o nível mudar.</em></p>
    """
    journal("lealdade", "Lealdade", [(None, html)], sort=200)


def build_evolucao():
    steps = """
    <p>Um Pokémon pode evoluir para uma nova forma após cumprir os requisitos apropriados em
    sua ficha de estatísticas, e apenas no momento em que sobe de nível. A evolução pode ser
    adiada a critério do jogador, mas, uma vez tomada a decisão, o Pokémon não pode evoluir
    até alcançar o próximo nível.</p>
    <p>Quando um Pokémon evolui, o seguinte ocorre, nesta ordem:</p>
    <ol>
      <li>Substitui seus atributos base pelos atributos base de sua nova forma. Depois disso,
      soma normalmente todos os Pontos de EV já investidos e aplica os ajustes de sua
      Natureza.</li>
      <li>Ganha um bônus de PV igual ao <strong>dobro de seu nível</strong>. Ao alcançar o
      nível em que deve evoluir, ainda ganha os pontos de vida correspondentes à sua forma
      atual; só a partir do próximo nível o dado de vida da nova forma passa a ser usado
      para os PV adicionais.</li>
      <li>Adquire os dados de vida de sua forma evoluída para aumentar o PV neste nível e
      para rolagens futuras.</li>
      <li>Adquire a CA base de sua forma evoluída, todas as novas proficiências e
      vulnerabilidades/resistências/imunidades.</li>
      <li>Se perder sua habilidade passiva atual ao evoluir, deve trocá-la por qualquer uma
      das habilidades passivas não ocultas da forma evoluída.</li>
      <li>Mantém os Moves conhecidos que tinha antes da evolução, mas só pode aprender Moves
      futuros da nova lista de Moves. Exemplo: um Pikachu evoluindo para Raichu no nível 10
      não pode aprender nenhum dos Moves de nível 10 do Pikachu.</li>
      <li>Se evoluir num nível em que ganharia Pontos de EV, adicione-os agora.</li>
    </ol>
    <p><em>Nota de implementação: hoje esta é uma regra de referência, sem um botão que
    execute a transformação sozinho — mas os 7 passos acima foram deixados numerados e
    estruturados de propósito, para servir de roteiro caso uma ferramenta assistida (troca de
    espécie + recálculo automático) seja construída no futuro.</em></p>
    """
    example = """
    <p>Vamos acompanhar cada etapa da evolução de um Pikachu de Natureza Corajoso no nível
    10, capturado no nível 1. Cada item abaixo corresponde ao passo de mesmo número na página
    de Evolução.</p>
    <ol>
      <li><strong>Atributos base + EV + Natureza.</strong> Pela regra de Pontos de EV, esse
      Pikachu já teria recebido 5 pontos (níveis 2, 4, 6, 8, 10), distribuídos por exemplo
      como FOR +1 / DES +2 / CON +2. Um Raichu selvagem no nível mínimo tem FOR 12 / DES 18 /
      CON 15 / INT 6 / SAB 12 / CAR 10. Ao evoluir, Pikachu substitui seus atributos pelos do
      Raichu e reaplica os EVs + Natureza (Corajoso: +2 FOR, -2 SAB):
      FOR 12+2+1=15, DES 18+2=20, CON 15+2=17, INT 6, SAB 12-2=10, CAR 10.</li>
      <li><strong>PV do nível + bônus de evolução.</strong> No nível 10, com dado de vida d6,
      a média (metade+1) é 4; com +2 de Constituição, ganha 6 PV neste nível. Ao evoluir,
      ganha também um bônus de PV igual ao dobro do nível (10×2 = 20 PV extras). A partir do
      próximo nível, passa a usar o d10 do Raichu.</li>
      <li><strong>Dado de vida da forma evoluída.</strong> A partir do nível 10, Pikachu usa
      1d10 (do Raichu) para PV adicionais.</li>
      <li><strong>CA da forma evoluída.</strong> Um Raichu Corajoso tem CA 15 no Livro dos
      Pokémon — essa passa a ser a CA do Pikachu evoluído.</li>
      <li><strong>Habilidade passiva.</strong> A habilidade do Pikachu era Static; como é
      também a única habilidade do Raichu, ele mantém Static (se o Raichu só tivesse
      "Lightning Rod", a troca seria obrigatória).</li>
      <li><strong>Lista de Moves.</strong> No nível 10, Pikachu poderia aprender novos Moves —
      mas por estar evoluindo neste nível, ele renuncia aos Moves de nível 10 do Pikachu e só
      pode aprender Moves novos a partir da lista do Raichu daqui em diante. Os Moves que já
      conhecia permanecem; uma vez esquecidos, só podem ser reaprendidos se também estiverem
      na lista do Raichu.</li>
    </ol>
    """
    journal("evolucao", "Evolução", [
        ("Evolução", steps),
        ("Exemplo: Pikachu → Raichu", example)
    ], sort=300)


def build_condicoes():
    pokemon_status = """
    <p>São condições específicas que só afetam Pokémon em batalha. Um Pokémon só pode ser
    afetado por um <strong>status não-volátil</strong> por vez — se já estiver afetado por um,
    não pode ser afetado por outro até ser curado do original. Todos os efeitos de final de
    turno ocorrem sempre depois de qualquer outro efeito de final de turno de outras fontes.
    Um Pokémon pode ser afetado por um status <strong>volátil</strong> e um não-volátil ao
    mesmo tempo; ao contrário dos não-voláteis, os voláteis terminam imediatamente fora de
    combate.</p>
    <p><em>Período de Carência: quando um Pokémon se recupera de uma Condição de Status, ele
    não pode sucumbir à mesma condição até o final de seu próximo turno.</em></p>
    <h2>Status não-voláteis</h2>
    <h3>Queimado</h3>
    <p>Tem o dano de ataques corpo a corpo reduzido pela metade (arredondado para baixo).
    Sofre dano sem tipo igual ao seu bônus de proficiência no final de cada turno, até
    desmaiar ou ser curado. Pokémon do tipo Fogo são imunes.</p>
    <h3>Congelado</h3>
    <p>Fica incapacitado e impedido. No início de cada turno, rola 1d6 para descongelar: no
    primeiro turno precisa de 6; a cada turno seguinte o resultado mínimo necessário diminui
    em 1, até que qualquer resultado seja suficiente. Se descongelar no início do turno, pode
    agir normalmente nesse mesmo turno. Fora de combate dura meia hora. Termina imediatamente
    se sofrer dano de um Move que possa causar Queimado. Pokémon do tipo Gelo são imunes.</p>
    <h3>Paralisado</h3>
    <p>Tem desvantagem em testes de resistência de FOR ou DES, move-se à metade do
    deslocamento e tem a iniciativa reduzida à metade (arredondado para baixo) enquanto
    permanecer paralisado. No início de cada turno, rola 1d4: em um resultado de 1, fica
    incapacitado e impedido até o início do próximo turno, e o Treinador perde quaisquer
    ações compartilhadas com ele. Se estiver paralisado e confuso ao mesmo tempo, a rolagem
    de paralisia ocorre primeiro (se falhar, não rola confusão naquele turno). Pokémon do
    tipo Elétrico são imunes.</p>
    <h3>Envenenado</h3>
    <p>Sofre dano sem tipo igual à metade do nível (arredondado para cima, mínimo 2) no final
    de cada turno, até desmaiar ou ser curado. Pokémon dos tipos Venenoso e Aço são imunes.</p>
    <h3>Gravemente Envenenado</h3>
    <p>Sofre dano sem tipo e <strong>cumulativo</strong>, igual à metade do nível (arred. para
    cima, mínimo 2) multiplicado pelo número de turnos consecutivos com a condição, até
    desmaiar ou ser curado — o contador reinicia ao sair de combate ou ser trocado. Curado por
    qualquer item/efeito que cure Envenenado. Ao final do combate, esta condição vira
    Envenenado comum. Pokémon dos tipos Venenoso e Aço são imunes.</p>
    <h3>Sonolento</h3>
    <p>Tudo fica mais lento: deslocamento reduzido pela metade. No primeiro turno após ficar
    sonolento ainda age normalmente; a partir do segundo, entra em sonolência em turnos
    alternados, incapaz de usar Moves em turnos seguidos. Um golpe crítico remove a condição.
    Moves de preparação (como Fly) falham no turno seguinte; Moves de recarga (como Hyper
    Beam) fazem o Pokémon ficar sonolento e recarregar no mesmo turno. Se afetado de novo
    enquanto sonolento, passa a ficar Dormindo. Se retornado à Pokébola, o próximo turno é em
    estado de não-sonolência.</p>
    <h3>Dormindo</h3>
    <p>Fica incapacitado, impedido e faz todos os testes de resistência com desvantagem. Ao
    final de cada turno rola 1d6 pra acordar: no primeiro turno acorda com 5 ou 6; no segundo,
    com 4 a 6; ao final do terceiro turno acorda automaticamente (se não agiu no turno
    anterior por sonolência, essas rolagens passam a ser feitas no início do turno). Um golpe
    crítico acorda o Pokémon imediatamente e também remove Sonolento. Se retornado à
    Pokébola, a contagem de rodadas é pausada até ser liberado de novo.</p>
    <h2>Status voláteis</h2>
    <h3>Atordoado</h3>
    <p>Fica incapacitado e impedido até o final do próximo turno. Todas as ações e reações
    daquele período são consumidas — o Treinador também perde quaisquer ações compartilhadas
    com esse Pokémon. Se atordoado durante o próprio turno (por exemplo, pela reação de um
    Move inimigo), a condição o afeta imediatamente e dura até o início do próximo turno.</p>
    <h3>Confuso</h3>
    <p>Afetado imediatamente, dura 1d4+1 turnos, e não pode realizar reações enquanto durar
    (se retornado à Pokébola, a contagem é pausada). Sempre que o Pokémon confuso tenta usar
    um Move, rola 1d6 primeiro: em 5 ou 6, ele perde a concentração, sofre dano sem tipo igual
    à metade do nível (arred. para baixo, mínimo 1), e o Move falha, consumindo a ação. Em 4
    ou menos, o Move é usado normalmente.</p>
    <h3>Encantado</h3>
    <p>Está apaixonado pelo adversário que o encantou. Sempre que tenta usar um Move, rola
    1d20: com 10 ou menos, o Move falha sem gastar PP mas consome a ação, e o Pokémon fica
    incapacitado e impedido até o início do próximo turno — mesmo que o Move tivesse outro
    alvo. Se encantado, confuso e paralisado ao mesmo tempo, a ordem de verificação é
    paralisia, confusão, encanto. Termina assim que qualquer um dos dois Pokémon envolvidos
    sai da batalha; receber dano não remove o encanto. Um Pokémon já encantado é imune a
    novas tentativas (inclusive de mudar o alvo). Pokémon de gênero desconhecido não pode
    encantar nem ser encantado. Não pode ser passado com Baton Pass. Quando um Pokémon usa um
    Move que causaria Encantado num humano, o humano recebe a condição Enfeitiçado (veja
    Condições Gerais) em vez disso — não confundir as duas.</p>
    """
    generic = """
    <p>A maioria das condições abaixo não é resultado direto de um ataque, Move ou habilidade
    específica — representam estados físicos, mentais ou ambientais que podem surgir de
    diversas circunstâncias narrativas. Cabe ao Mestre interpretar o contexto e decidir quando
    e como ocorrem. Uma condição termina ao ser remediada, ou conforme a duração do efeito que
    a impôs. Se mais de um efeito impuser a mesma condição, cada aplicação tem sua própria
    duração, mas os efeitos não se agravam — ou a criatura tem a condição, ou não.</p>
    <h3>Agarrado</h3>
    <p>Deslocamento se torna 0 (sem bônus de deslocamento) — exceto que, para cada categoria
    de tamanho acima da criatura que a agarra, ela pode se mover 3 metros arrastando o
    agarrador. Ataques feitos pela criatura agarrada e por quem a agarra são feitos em
    desvantagem. Ataques à distância contra uma criatura agarrada têm 50% de chance de acertar
    o alvo errado. Termina se quem agarrou ficar incapacitado, ou se a criatura agarrada sair
    do alcance de quem agarrou ou do efeito. O alvo pode gastar a ação padrão pra escapar
    (Força/Atletismo ou Destreza/Acrobacia contra Força/Atletismo de quem agarra), exceto onde
    o Move especificar o contrário. Cada agarrão é independente — escapar de vários exige um
    teste por agarrador.</p>
    <h3>Amedrontado</h3>
    <p>Desvantagem em testes de perícia e jogadas de ataque enquanto a fonte do medo estiver
    na linha de visão. Não pode se mover voluntariamente para mais perto da fonte do medo.</p>
    <h3>Atordoado (humanos)</h3>
    <p>Está incapacitado, não pode se mover e só fala hesitantemente. Falha automaticamente em
    testes de resistência de Força ou Destreza. Jogadas de ataque contra a criatura têm
    vantagem.</p>
    <h3>Caído</h3>
    <p>A única opção de movimento é rastejar (cada 1,5m custa 1,5m adicional), a menos que se
    levante (custa metade do deslocamento), encerrando a condição. Sofre desvantagem nas
    jogadas de ataque. Um ataque contra a criatura caída tem vantagem se o atacante estiver a
    1,5m dela; de qualquer outra forma, o ataque sofre desvantagem.</p>
    <h3>Cego</h3>
    <p>Falha automaticamente em qualquer teste de perícia que exija visão. Jogadas de ataque
    contra a criatura têm vantagem, e os ataques dela sofrem desvantagem. Considerada cega
    enquanto estiver em escuridão total, a menos que algo permita perceber no escuro.</p>
    <h3>Confuso (humanos)</h3>
    <p>Comporta-se de modo aleatório: role 1d6 no início de cada turno. 1-2: move-se numa
    direção aleatória (1d8, sentido horário a partir do norte), podendo sofrer ataques de
    oportunidade. 3-4: não pode agir, balbucia incoerentemente. 5-6: a condição termina e pode
    agir normalmente.</p>
    <h3>Desanimado / Frustrado</h3>
    <p>Desvantagem em testes de Inteligência, Sabedoria e Carisma, e em perícias baseadas
    nesses atributos.</p>
    <h3>Em Chamas (humanos)</h3>
    <p>Sofre 1d6 de dano de fogo ao final de cada turno. Pode gastar uma ação padrão para
    apagar o fogo com as mãos; imersão em água também apaga as chamas.</p>
    <h3>Enfeitiçado (humanos)</h3>
    <p>Não pode atacar quem o enfeitiçou nem torná-lo alvo de habilidades/efeitos nocivos.
    Quem enfeitiçou tem vantagem em testes de perícia para interagir socialmente com a
    criatura. É a condição que um humano recebe quando afetado por um efeito que causaria
    Encantado em um Pokémon — não confundir as duas.</p>
    <h3>Enjoado</h3>
    <p>Só pode realizar uma ação padrão OU uma ação de movimento (não as duas) por rodada, e
    sofre desvantagem em testes de perícia.</p>
    <h3>Envenenado (humanos)</h3>
    <p>O efeito varia conforme o veneno: pode ser perda de 1d6 PV ao final dos turnos, ou
    outra condição (como Fraco ou Enjoado).</p>
    <h3>Exausto</h3>
    <p>Medida em 6 níveis, imposta por certas habilidades e perigos ambientais (fome,
    exposição prolongada ao frio/calor extremo). Uma criatura já exausta que sofre novo efeito
    de exaustão aumenta seu nível conforme descrito no efeito, e sofre todos os efeitos do
    nível atual e dos anteriores.</p>
    <table>
      <thead><tr><th>Nível</th><th>Efeito</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>Desvantagem em testes de perícia.</td></tr>
        <tr><td>2</td><td>Deslocamento reduzido pela metade.</td></tr>
        <tr><td>3</td><td>Desvantagem em jogadas de ataque e testes de resistência.</td></tr>
        <tr><td>4</td><td>Máximo de pontos de vida reduzido pela metade.</td></tr>
        <tr><td>5</td><td>Deslocamento reduzido a 0.</td></tr>
        <tr><td>6</td><td>Morte.</td></tr>
      </tbody>
    </table>
    <p>Um efeito que remova exaustão reduz o nível (todos os efeitos somem se cair abaixo de
    1). Terminar um descanso longo reduz a exaustão em 1 nível, desde que a criatura também
    tenha ingerido água e comida. Um Pokémon curado num Centro Pokémon reduz a exaustão em 1
    nível, podendo recuperar outro nível só no dia seguinte.</p>
    <h3>Fascinado</h3>
    <p>Desvantagem em testes de Percepção; só pode observar aquilo que a fascinou, sem
    realizar outras ações. Anulada por ações hostis contra a criatura, ou se o alvo do fascínio
    deixar de estar visível. Balançar a criatura fascinada pra tirá-la desse estado custa uma
    ação.</p>
    <h3>Fraco / Debilitado</h3>
    <p>Desvantagem em testes de Força, Destreza e Constituição, e em perícias baseadas nesses
    atributos.</p>
    <h3>Impedido</h3>
    <p>Deslocamento se torna 0, sem bônus de deslocamento. Jogadas de ataque contra a criatura
    têm vantagem, e os ataques dela sofrem desvantagem.</p>
    <h3>Incapacitado</h3>
    <p>Não pode realizar ação padrão, ação bônus ou reação.</p>
    <h3>Inconsciente / Dormindo (humanos)</h3>
    <p>Está incapacitada, não pode se mover, falar, nem tem ciência dos arredores. Larga tudo
    que segurava e fica caída. Falha automaticamente em testes de resistência de Força ou
    Destreza. Jogadas de ataque contra ela têm vantagem, e qualquer ataque dentro de 1,5m que
    a atinja é um acerto crítico.</p>
    <h3>Invisível</h3>
    <p>Impossível de ver sem ajuda de um Move ou sentido especial (para se esconder, é
    considerada em escuridão densa; sua localização pode ser detectada por barulho ou
    rastros). Jogadas de ataque contra a criatura sofrem desvantagem, e os ataques dela têm
    vantagem, mesmo com sua posição conhecida.</p>
    <h3>Lento</h3>
    <p>Desvantagem em jogadas de ataque e testes de resistência.</p>
    <h3>Paralisado (humanos)</h3>
    <p>Está incapacitado, não pode se mover nem falar. Falha automaticamente em testes de
    resistência de Força e Destreza. Jogadas de ataque contra a criatura têm vantagem, e
    qualquer ataque que a atinja é um acerto crítico se o atacante estiver a 1,5m dela.</p>
    <h3>Petrificado</h3>
    <p>Transformada (com tudo que carrega) numa substância sólida inanimada, geralmente pedra
    — peso multiplicado por dez, para de envelhecer. Está incapacitada, não pode se mover,
    falar, nem tem ciência dos arredores. Jogadas de ataque contra ela têm vantagem, e falha
    automaticamente em testes de resistência de Força e Destreza. Tem resistência a todos os
    tipos de dano, e é imune a veneno e doenças (um veneno/doença já presente fica suspenso,
    não neutralizado).</p>
    <h3>Sangrando</h3>
    <p>No início do turno, faz um teste de Constituição (CD 15). Se falhar, perde 1d6 PV e
    continua sangrando; se passar, remove a condição.</p>
    <h3>Sufocado</h3>
    <p>Enquanto respira fumaça, gases, poeira ou esporos densos, não consegue falar
    normalmente. No início de cada turno faz um teste de resistência de Constituição contra a
    CD do agente; em falha, gasta a ação padrão daquele turno tossindo ou recuperando o
    fôlego. Sofre desvantagem em testes de Percepção baseados no olfato e para manter
    concentração. Após ficar exposta por 1 + modificador de Constituição minutos consecutivos
    (mínimo 1), repete o teste; em falha, sofre 1 nível de Exaustão — e o teste se repete a
    cada novo intervalo de exposição. Termina ao voltar a respirar ar puro (se não puder
    respirar, aplicam-se as regras de Asfixia).</p>
    <h3>Surdo</h3>
    <p>Falha automaticamente em qualquer teste de perícia que exija audição.</p>
    """
    journal("condicoes", "Condições", [
        ("Condições de Status (Pokémon)", pokemon_status),
        ("Condições Gerais", generic)
    ], sort=50)


def build_itens_segundaveis():
    html = """
    <p>Os Pokémon podem receber um único item para segurar (<em>Held Item</em>), com efeitos
    variados — alguns desencadeados por eventos, outros estáticos, sempre presentes. Um item
    segurado <strong>não pode ser trocado, equipado ou descartado durante um combate</strong>,
    a menos que seja forçado por um Move, habilidade ou outro efeito.</p>
    <h2>Berries</h2>
    <p>Berries são encontradas na natureza e vendidas em lojas e mercados. Podem ser usadas de
    duas formas:</p>
    <ol>
      <li><strong>Como item consumível:</strong> o Treinador gasta uma ação padrão pra aplicar
      os efeitos da Berry (restaurar PV, remover uma condição), ignorando seu gatilho de
      ativação normal — precisa estar em alcance corpo a corpo do Pokémon.</li>
      <li><strong>Como item segurado:</strong> o Pokémon ativa a Berry sozinho quando o
      gatilho descrito no item é atendido. Diferente dos jogos de vídeo game, essa ativação é
      <strong>opcional</strong> e pode ser adiada para uma ocorrência posterior do mesmo
      gatilho.</li>
    </ol>
    <h2>Itens Seguráveis não consumíveis</h2>
    <p>Não são perdidos após o uso — voltam ao estado normal ao final do combate. Seus efeitos
    podem ser passivos (benefício constante) ou condicionais (ativados só quando uma situação
    específica ocorre).</p>
    <h2>Itens Seguráveis consumíveis</h2>
    <p>Desaparecem após o uso ou ativação do efeito. Geralmente são ativados quando uma
    condição específica é atendida, concedendo um benefício imediato, ou permanecem ativos até
    determinada condição ocorrer. Uma vez consumidos, não retornam ao final do combate —
    precisam ser obtidos de novo.</p>
    <h2>Itens Evolutivos</h2>
    <p>Uma evolução por item ocorre no momento em que todos os requisitos forem atendidos. O
    item não precisa ser segurado no momento da evolução, mas o Pokémon precisa entrar em
    contato com o objeto, que é consumido na evolução (a Pedra-Chave é a exceção — não é
    consumida).</p>
    <h2>Vitaminas e Hortelãs de Natureza</h2>
    <p>Vitaminas adiantam 2 Pontos de EV num atributo (tirados dos pontos que o Pokémon
    receberia em níveis futuros, começando pelo nível 20 e descendo), respeitando o limite de
    10 EVs totais e 4 por atributo. Hortelãs de Natureza alteram permanentemente a Natureza de
    um Pokémon, cada erva correspondendo a uma Natureza específica.</p>
    <p><em>O catálogo completo de itens (Restauradores, Pokébolas, Itens-X, Berries, Itens
    Seguráveis específicos de espécie, Vitaminas, Hortelãs etc. — com preço e efeito de cada
    um) já existe como Item de verdade nos compêndios deste módulo, prontos pra arrastar pra
    dentro do inventário de um Treinador ou Pokémon; não foi duplicado aqui.</em></p>
    """
    journal("itens-seguraveis-e-consumiveis", "Itens Seguráveis e Consumíveis", [(None, html)], sort=400)


def build_pesca():
    html = """
    <p><em>"Pescar não é só jogar a linha na água… é um jogo de paciência, sorte e jeito.
    Deixa eu te ensinar como se faz direito!" — o Velho Pescador</em></p>
    <h2>O Tempo da Pescaria</h2>
    <p>Pescar leva tempo — às vezes minutos, às vezes horas, nunca dá pra saber. Antes de
    jogar a linha, role <strong>1d6 × 5 minutos</strong>: esse é o tempo que a pescaria vai
    gastar. Se passar da hora disponível, dá pra desistir e guardar a vara a qualquer momento.
    O movimento na água espanta os Pokémon — só dá pra tentar a sorte até <strong>3 vezes por
    dia no mesmo local</strong>; depois disso, é melhor procurar outro canto.</p>
    <h2>Fisgar a Isca</h2>
    <p>Jogou a linha? Faça um teste de <strong>Sobrevivência</strong>. A dificuldade depende
    de onde você está e da vara que usa:</p>
    <table>
      <thead><tr><th>Local</th><th>Old Rod</th><th>Good Rod</th><th>Super Rod</th></tr></thead>
      <tbody>
        <tr><td>Rio</td><td>CD 10</td><td>CD 10, com vantagem</td><td>Pesca garantida</td></tr>
        <tr><td>Lago</td><td>CD 15</td><td>CD 10</td><td>CD 5</td></tr>
        <tr><td>Praia</td><td>CD 20</td><td>CD 15</td><td>CD 10</td></tr>
        <tr><td>Oceano</td><td>CD 25</td><td>CD 20</td><td>CD 15</td></tr>
      </tbody>
    </table>
    <ul>
      <li><strong>Falha:</strong> nada mordeu — recolha e tente de novo (custa mais tempo).</li>
      <li><strong>Sucesso:</strong> um Pokémon mordeu a isca! O Mestre faz a busca de um
      Pokémon adequado ao ambiente.</li>
      <li><strong>Acerto Crítico:</strong> fisgou um baita troféu — vem um Pokémon à sua
      escolha (desde que faça sentido pro local), e você só precisa de 1 sucesso pra puxá-lo
      depois.</li>
    </ul>
    <h2>Ferramentas de Pesca</h2>
    <p>Cada vara tem suas manhas — só um tolo vai pro oceano com uma tralha ruim.</p>
    <ul>
      <li><strong>Old Rod:</strong> boa pra iniciantes. Só aguenta Pokémon de SR até 5.</li>
      <li><strong>Good Rod:</strong> aguenta Pokémon de SR até 10. Dá +1 nos testes de Força
      pra puxar.</li>
      <li><strong>Super Rod:</strong> a joia dos pescadores — encara qualquer Pokémon. Dá +2
      nos testes de Força pra puxar.</li>
    </ul>
    <h2>Puxar o Pokémon</h2>
    <p>Fisgar é fácil — difícil é trazer o bicho até você! Faça <strong>3 testes resistidos de
    Força</strong> contra o Pokémon. Vencendo 2 deles, ele é seu; perdendo, ele escapa com sua
    isca. Depois de tanto se debater, um Pokémon pescado fica mais fácil de capturar: reduza
    a CD da captura em 5, 10 ou 15 pontos, dependendo da vara usada.</p>
    <h2>Hora da Captura</h2>
    <p>Puxou o Pokémon? O combate começa na hora, e você sempre age primeiro — tem um turno
    inteiro antes de rolar a ordem de iniciativa, já que o Pokémon já está cansado da luta.</p>
    """
    journal("guia-de-pesca", "Guia de Pesca", [(None, html)], sort=500)


def build_homebrew_captura():
    html = """
    <p><em>Homebrew — substitui, se a mesa optar por usá-la, a "Arremessar Pokébola" padrão
    (veja "Capturando Pokémon e Pokémon Brilhantes"). Troca o Teste de Captura de rolagem única
    por uma disputa de 2 sucessos contra 2 falhas.</em></p>
    <h2>Arremessar Pokébola</h2>
    <p><strong>Tempo de Execução:</strong> 1 ação. <strong>Alcance:</strong> 18 metros.</p>
    <p>Você arremessa uma Pokébola em um Pokémon selvagem na tentativa de capturá-lo.</p>
    <h2>Teste de Captura</h2>
    <p style="text-align:center"><strong>Adestrar Animais + Proficiência do Treinador +
    Sabedoria do Treinador + Bônus da Pokébola</strong></p>
    <p>O resultado deve ser igual ou maior que a CD do Pokémon.</p>
    <h2>CD de Captura</h2>
    <p style="text-align:center"><strong>CD = 10 + Nível do Pokémon + SR do Pokémon</strong>
    (arredonde o valor de SR para cima)</p>
    <h2>Captura em 2 Sucessos</h2>
    <p>Para capturar o Pokémon, o treinador precisa conseguir 2 sucessos no Teste de Captura.</p>
    <table>
      <thead><tr><th>Resultado</th><th>Efeito</th></tr></thead>
      <tbody>
        <tr><td>Sucesso</td><td>Marque 1 sucesso.</td></tr>
        <tr><td>Falha</td><td>Marque 1 falha.</td></tr>
        <tr><td>2 sucessos</td><td>O Pokémon é capturado!</td></tr>
      </tbody>
    </table>
    <h2>Fuga do Pokémon</h2>
    <p>Se o treinador acumular <strong>2 falhas</strong> antes de conseguir os 2 sucessos, o
    Pokémon tem uma chance de fugir.</p>
    <p style="text-align:center"><strong>Teste de Fuga: 1d20 + Nível do Pokémon</strong>, contra
    <strong>CD 10 + Nível do Treinador</strong></p>
    <table>
      <thead><tr><th>Resultado</th><th>Efeito</th></tr></thead>
      <tbody>
        <tr><td>Sucesso</td><td>O Pokémon foge da batalha.</td></tr>
        <tr><td>Falha</td><td>O Pokémon permanece na batalha e o treinador pode tentar
        capturá-lo novamente.</td></tr>
      </tbody>
    </table>
    <h2>Captura com PV 0 — Estado de Negação</h2>
    <p>Se um treinador capturar um Pokémon quando ele estiver com PV 0, o Pokémon entra
    imediatamente no estado de <strong>Negação</strong> — representa a resistência do Pokémon
    em aceitar o novo treinador após ser capturado enquanto estava incapacitado.</p>
    <ul>
      <li><strong>Duração:</strong> um número de dias igual ao Nível do Pokémon.</li>
      <li><strong>Lealdade:</strong> durante esse período, o Pokémon possui o nível de Lealdade
      Desleal.</li>
      <li><strong>Comportamento:</strong> o Pokémon rejeita o treinador — ao agir contra ele ou
      em situações relacionadas à sua obediência, realiza suas ações com desvantagem, conforme
      as regras da mesa. Após o término da duração, o estado de Negação termina, salvo se outra
      regra de Lealdade determinar o contrário.</li>
    </ul>
    <h2>Exemplos</h2>
    <p>Um Pokémon Nível 5, SR 2 possui CD 10+5+2=17. O treinador tem Adestrar Animais +4,
    Proficiência +2, Sabedoria +3 e usa uma Pokébola com +1 — o teste de captura totaliza
    4+2+3+1=10. Como 10 é menor que a CD 17, o teste resulta em falha; pra capturá-lo, precisa
    de 2 sucessos antes de acumular 2 falhas.</p>
    <p>Um treinador captura um Pokémon de Nível 4 enquanto ele está com PV 0 — o Pokémon entra
    no estado de Negação por 4 dias, com Lealdade Desleal e ações em desvantagem durante esse
    período.</p>
    <h2>Resumo</h2>
    <table>
      <thead><tr><th>Regra</th><th>Resultado</th></tr></thead>
      <tbody>
        <tr><td>2 sucessos</td><td>Captura</td></tr>
        <tr><td>2 falhas</td><td>Teste de Fuga</td></tr>
        <tr><td>Fuga — sucesso</td><td>Pokémon foge da batalha</td></tr>
        <tr><td>Fuga — falha</td><td>Pokémon permanece e nova tentativa é possível</td></tr>
        <tr><td>Captura com PV 0</td><td>Estado de Negação</td></tr>
        <tr><td>Duração da Negação</td><td>Nível do Pokémon em dias</td></tr>
        <tr><td>Lealdade durante a Negação</td><td>Desleal</td></tr>
        <tr><td>Ações durante a Negação</td><td>Desvantagem</td></tr>
      </tbody>
    </table>
    """
    journal("homebrew-sistema-de-captura-ajustado", "Sistema de Captura Pokémon (Ajustado)",
            [(None, html)], sort=100, folder=HOMEBREW_FOLDER_ID)


def build_homebrew_elo_rotomi():
    conceito = """
    <p><em>Homebrew — regra de logística de equipe: define armazenamento, troca e porte de
    Pokémon através da rede Rotomi.</em></p>
    <h2>Conceito</h2>
    <p>O Elo Rotomi permite que cada treinador licenciado mantenha seis Pokémon vinculados à
    sua rede, enquanto o limite de porte determina quantos podem acompanhá-lo e agir
    diretamente.</p>
    <p><strong>Regra-chave:</strong> os seis Pokémon vinculados formam a <strong>Equipe
    Vinculada</strong>. Em condições normais, apenas os Pokémon <strong>portados</strong> podem
    agir.</p>
    <h2>1. Equipe Vinculada</h2>
    <p>Todo treinador licenciado mantém 6 Pokémon ancorados no Elo Rotomi, divididos entre
    <strong>portados</strong> (ocupam Pokéslots — são os únicos que agem, seja em batalha,
    exploração ou qualquer cena) e <strong>em espera</strong> (ficam ancorados no Elo; não agem,
    não entram em combate e não recebem XP). Portados + Em espera soma sempre 6.</p>
    <table>
      <thead><tr><th>Nível do Treinador</th><th>Portados (Pokéslots)</th><th>Em espera</th></tr></thead>
      <tbody>
        <tr><td>1º a 4º</td><td>3</td><td>3</td></tr>
        <tr><td>5º a 9º</td><td>4</td><td>2</td></tr>
        <tr><td>10º a 14º</td><td>5</td><td>1</td></tr>
        <tr><td>15º a 20º</td><td>6</td><td>0</td></tr>
      </tbody>
    </table>
    <h2>2. Trocas no Elo</h2>
    <p>As trocas são declaradas ao concluir o descanso — nunca no meio de uma cena, encontro ou
    combate.</p>
    <table>
      <thead><tr><th>Momento</th><th>Permitido</th></tr></thead>
      <tbody>
        <tr><td>Descanso longo (8h)</td><td>Reorganizar livremente a Equipe Vinculada, com
        qualquer número de trocas.</td></tr>
        <tr><td>Descanso curto (30 min)</td><td>Até 2 trocas entre portados e em espera.</td></tr>
        <tr><td>Fora de descanso</td><td>Nada, salvo com Rotom Dex: 2 trocas por dia, de
        qualquer lugar.</td></tr>
        <tr><td>Centro Pokémon ou PC legalizado</td><td>Acesso total ao PC: depositar, retirar e
        redefinir quais são os 6 ancorados.</td></tr>
      </tbody>
    </table>
    <p><strong>No campo:</strong> você pode rearranjar os seis que já escolheu. Somente no
    Centro Pokémon você escolhe quais seis ficam ancorados no Elo.</p>
    """
    limites = """
    <h2>3. Limites do Elo</h2>
    <ol>
      <li><strong>Armazenar não cura.</strong> O Pokémon entra e volta com os mesmos PV, PP e
      condições de status. Pokémon desmaiado continua desmaiado.</li>
      <li><strong>Sem XP em espera.</strong> Só recebe XP quem participou da batalha, podendo
      receber somente o XP de quest.</li>
      <li><strong>Exige cobertura.</strong> O Elo depende da rede Rotomi. Em áreas sem sinal —
      cavernas profundas, ruínas antigas, tempestades e zonas de interferência, a critério do
      Mestre — não há troca possível.</li>
      <li><strong>Não altera o Controle de SR.</strong> Um Pokémon acima do seu nível de
      controle continua Desleal (ou Indiferente, no caso do talento Guru), esteja portado ou
      ancorado.</li>
    </ol>
    <h2>4. Batalha Oficial — Liberação de Equipe Completa</h2>
    <p>A exceção de porte se aplica somente aos confrontos sancionados pela Liga: Batalhas de
    Ginásio, Provas de Kahuna, Torneios registrados, Desafios de Elite ou Campeão. Qualquer
    outro confronto segue os Pokéslots normais.</p>
    <p><strong>Durante o evento:</strong> a restrição de porte é suspensa pela duração do
    evento, e o Rotomi entrega no local toda a Equipe Vinculada — o treinador enfrenta o
    desafio com sua equipe completa, seguindo as regras estabelecidas no próprio desafio.</p>
    """
    referencia = """
    <h2>5. Termo</h2>
    <p><strong>Equipe Vinculada:</strong> os 6 Pokémon ancorados no Elo Rotomi, portados ou em
    espera. Sempre que uma regra exigir que o treinador tenha determinado Pokémon "em sua
    equipe" — como a condição de evolução do Pancham, que pede outro Pokémon do tipo Sombrio —,
    considera-se a Equipe Vinculada.</p>
    <h2>Resumo de mesa</h2>
    <table>
      <thead><tr><th>Situação</th><th>Regra</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td>Exploração / cena</td><td>Somente Pokémon portados podem agir.</td><td>Só portados</td></tr>
        <tr><td>Descanso curto</td><td>Até 2 trocas entre portados e em espera.</td><td>2 trocas</td></tr>
        <tr><td>Descanso longo</td><td>Reorganização livre da Equipe Vinculada.</td><td>Livre</td></tr>
        <tr><td>Centro Pokémon / PC legalizado</td><td>Escolha e redefinição dos 6 ancorados.</td><td>Acesso total</td></tr>
        <tr><td>Sem cobertura</td><td>Nenhuma troca pelo Elo.</td><td>Bloqueado</td></tr>
        <tr><td>Batalha Oficial</td><td>Restrição suspensa; todos os 6 ficam disponíveis no local.</td><td>Equipe completa</td></tr>
      </tbody>
    </table>
    <p><em><strong>Princípio:</strong> o Elo Rotomi amplia a gestão da equipe sem transformar
    armazenamento em cura, experiência passiva ou substituição livre durante cenas e
    combates.</em></p>
    """
    journal("homebrew-elo-rotomi", "Elo Rotomi", [
        ("Elo Rotomi — Conceito e Equipe Vinculada", conceito),
        ("Elo Rotomi — Limites e Batalha Oficial", limites),
        ("Elo Rotomi — Termos e Referência Rápida", referencia)
    ], sort=200, folder=HOMEBREW_FOLDER_ID)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))
    write_folder()
    write_folder(HOMEBREW_FOLDER_ID, "Homebrews", parent=FOLDER_ID,
                 filename="folder-homebrews.json", color="#d08770")

    build_bloco_estatisticas()
    build_experiencia_treinador()
    build_capturando_e_shiny()
    build_condicoes()
    build_mecanicas_especiais()
    build_mudancas_de_status()
    build_cuidados_pokemon()
    build_lealdade()
    build_reproducao_ovos()
    build_evolucao()
    build_mecanica_combate()
    build_iniciativa_e_acoes()
    build_movimento_posicao()
    build_tabela_efetividade()
    build_moves_mecanicas()
    build_itens_segundaveis()
    build_pesca()
    build_clima()
    build_apendice_xp()
    build_alpha_totem()
    build_homebrew_captura()
    build_homebrew_elo_rotomi()

    print(f"Compêndio de Regras gerado em {OUT_DIR}")


if __name__ == "__main__":
    main()
