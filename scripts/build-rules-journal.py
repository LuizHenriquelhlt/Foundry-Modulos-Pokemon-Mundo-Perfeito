#!/usr/bin/env python3
"""
Compêndio de Regras (packs/_source/regras): traz pra dentro do Foundry, em JournalEntry bem
formatado (não é o texto cru extraído do PDF — foi reorganizado/limpo pra ficar fácil de
consultar na mesa), os capítulos do Livro de Regras que só existiam em PDF até agora:
Mudanças de Status (+ regras opcionais de acúmulo), Lealdade, Evolução, Condições (de
Pokémon e gerais), Itens Seguráveis/Consumíveis (mecânica — o catálogo completo de itens já
existe como Item de verdade no compêndio, não repetido aqui) e o Guia de Pesca.

Cada tópico é uma JournalEntry própria (facilita achar pelo nome na barra lateral do
compêndio), todas dentro de uma pasta "Regras". Números de página citados são do Livro de
Regras - Pokémon Mundo Perfeito.pdf.

Idempotente: pode rodar de novo, sempre reescreve os mesmos arquivos.

Uso: python scripts/build-rules-journal.py
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "regras")
FOLDER_ID = "RegrasFolderRoot1"


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


def stats():
    return {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
            "compendiumSource": None, "duplicateSource": None}


def write_folder():
    doc = {
        "_key": f"!folders!{FOLDER_ID}",
        "_id": FOLDER_ID, "name": "Regras", "type": "JournalEntry", "folder": None,
        "sorting": "m", "color": "#88c0d0", "flags": {}, "_stats": {}, "sort": 0
    }
    with open(os.path.join(OUT_DIR, "folder-regras.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def journal(slug, name, sections, sort):
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
        "folder": FOLDER_ID, "sort": sort,
        "ownership": {"default": 2}, "flags": {}, "_stats": stats()
    }
    with open(os.path.join(OUT_DIR, f"regra-{slug}.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


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


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))
    write_folder()

    build_mudancas_de_status()
    build_lealdade()
    build_evolucao()
    build_condicoes()
    build_itens_segundaveis()
    build_pesca()

    print(f"Compêndio de Regras gerado em {OUT_DIR}")


if __name__ == "__main__":
    main()
