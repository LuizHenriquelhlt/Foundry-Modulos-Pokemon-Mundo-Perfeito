#!/usr/bin/env python3
"""
Fase 5 (parte 2) — mecânicas centrais dos suplementos de Geração 8 (Dynamax/Gigantamax,
Livro da Geração 8 pág. 6-11) e Geração 9 (Terastal, Livro da Geração 9 pág. 5-8), mais a
Região de Origem de Paldea (que só aparece no suplemento de Gen 9, não no Livro de Regras
principal — por isso falta na lista de 8 regiões da Fase 1).

Transcrito manualmente a partir do texto extraído (column-aware), não por um parser
genérico: ambas as seções têm formatação de prosa livre com múltiplas opções alternativas
para o Mestre escolher (ex.: 3 métodos diferentes de cálculo de PV do Dynamax), sem um
template repetido que justifique um parser dedicado.
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "packs", "_source", "trainer-features")


def make_id(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    out = []
    for _ in range(16):
        out.append(alphabet[n % len(alphabet)])
        n //= len(alphabet)
    return "".join(out)


def base_item(doc_id, name, system, category, img="icons/svg/upgrade.svg"):
    return {
        "_id": doc_id, "name": name, "type": "feat", "img": img, "system": system,
        "effects": [], "folder": None,
        "flags": {"pokemon-mundo-perfeito": {"category": category}},
        "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                   "compendiumSource": None, "duplicateSource": None},
        "sort": 950, "ownership": {"default": 0}
    }


DYNAMAX_DESCRIPTION = """
<h3>O que é</h3>
<p>Dynamax é uma transformação temporária de Galar que aumenta drasticamente o tamanho e
os PV de um Pokémon. Durante o Dynamax, todos os Moves conhecidos pelo Pokémon se tornam
Max Moves — mais poderosos, e muitos com efeitos adicionais que alteram o campo de
batalha. Alguns Pokémon específicos possuem o Fator Gigantamax: em vez de um Max Move
comum, ganham um G-Max Move exclusivo daquela espécie e mudam de aparência (mas não de
estatísticas, habilidade ou item segurado além do que o Dynamax já concede).</p>
<h3>O que é necessário para ativar</h3>
<ul>
<li>O Treinador precisa ter uma Pulseira Dynamax.</li>
<li>O Treinador precisa estar no nível 13 ou superior para controlar um Pokémon Dynamax;
caso contrário, o Pokémon fica descontrolado e com Lealdade -3 enquanto transformado.</li>
<li>Um Treinador pode usar a transformação Dynamax apenas duas vezes por descanso longo,
mas apenas 1 vez por combate. A partir do 17º nível, pode recuperar um uso em um descanso
curto (e ainda recuperar ambos os usos em um descanso longo).</li>
<li>Pokémon só podem Dynamaxar uma vez por descanso curto ou longo (a partir do nível 15,
duas vezes entre descansos), mas apenas 1 vez por combate.</li>
<li>A transformação só pode ocorrer em um Ginásio de Galar ou em uma Zona de Poder
(Pokémon Den) — regra opcional que o Mestre pode ajustar.</li>
<li>Apenas um Treinador por time pode ter um Pokémon Dynamaxado/Gigantamaxado por vez.</li>
<li>Um mesmo Pokémon não pode Mega Evoluir, usar Z-Move, Dynamaxar/Gigantamaxar ou
Terastalizar no mesmo combate — apenas uma dessas ações especiais por batalha.</li>
<li>Zacian, Zamazenta e Eternatus não podem Dynamaxar.</li>
<li>Um Pokémon pode usar sua Ação Livre + Ação de Movimento do Treinador para
Dynamaxar/Gigantamaxar no início do seu turno.</li>
</ul>
<h3>Efeitos em batalha</h3>
<ul>
<li>O Pokémon aumenta sua escala de tamanho para 50x50 pés (15x15 metros), independente
do tamanho original.</li>
<li>Dura 3 turnos (contando o atual); termina antes se o Pokémon cair a 0 PV ou for
substituído. Se ativado fora de combate, dura 1 minuto (vira 3 turnos se entrar em
batalha dentro desse tempo).</li>
<li>Itens segurados continuam funcionando, exceto Choice Band/Scarf/Specs, que ficam
suspensos enquanto Dynamaxado.</li>
</ul>
<h3>PV do Dynamax — Opção 1 (simples, recomendada para mesas ágeis)</h3>
<p>Sem progressão por nível: ao transformar, o Pokémon dobra seus PV máximos e atuais
imediatamente. Ao reverter, retorna ao PV máximo original e o PV atual é ajustado
proporcionalmente (divide o valor atual pela metade, arredondando para cima). O livro
também oferece opções mais detalhadas e próximas dos jogos — critério do Mestre.</p>
""".strip()

TERASTAL_DESCRIPTION = """
<h3>O que é</h3>
<p>Terastalização é a manifestação da energia da Área Zero de Paldea, que faz um Pokémon
cristalizar e assumir um Tera Tipo — geralmente igual a um de seus tipos naturais, mas
raramente um tipo completamente diferente. Ativada por uma Orbe Tera. Existe ainda o
raríssimo Tipo Estelar (19º tipo), ligado a Terapagos.</p>
<h3>O que é necessário para ativar</h3>
<ul>
<li>O Treinador precisa de uma Orbe Tera.</li>
<li>Uso único por descanso curto; recarrega em um Centro Pokémon ou ao tocar Cristais de
Tera Raid (não precisa entrar neles). Na Área Zero, ou se o Treinador tiver um Terapagos
na equipe, pode ser usada em todo combate (ainda uma vez por batalha).</li>
<li>Mesma regra de exclusividade de Mega Evolução/Z-Move/Dynamax: um Pokémon só pode
realizar uma dessas ações especiais por batalha.</li>
<li>Ação Bônus para Terastalizar no início do turno.</li>
</ul>
<h3>Efeitos em batalha</h3>
<ul>
<li>Recebe STAB para golpes do Tera Tipo E dos tipos originais. Se o Tera Tipo coincidir
com um tipo original, esse STAB é dobrado (mínimo de 1).</li>
<li>Defensivamente, o Pokémon passa a ser considerado apenas do seu Tera Tipo.</li>
<li>Moves de dano cujo dado máximo no nível 17 seja 30 ou menos passam a usar 2d6 (3d6 a
partir do nível 5, 3d8 a partir do nível 10, 5d6 a partir do nível 17).</li>
<li>O Tera Tipo não pode ser alterado por Soak/Transform/Protean; Transform usado antes de
Terastalizar não copia o Tera Tipo do oponente.</li>
<li>Dura até o fim da batalha ou até o Pokémon desmaiar (como Mega Evolução).</li>
<li>Tera Blast sempre assume o Tera Tipo do usuário.</li>
</ul>
<h3>Pokémon Tera selvagens</h3>
<p>Aparecem já Terastalizados e não podem ser capturados nesse estado. Quando o dano
reduziria seus PV a 20% ou menos do máximo, o dano restante é anulado, a Joia Tera se
quebra e o Pokémon fica Atordoado — só então pode ser capturado. Dano indireto
(envenenamento, queimadura) não quebra a Joia Tera, mas pode nocautear o Pokémon direto
sem ele nunca ficar capturável.</p>
<h3>Determinando o Tera Tipo de um selvagem</h3>
<p>Área comum: 1d10, resultado 10 = Pokémon Tera (role 1d6 → 1: tipo primário; 2: tabela
de tipos; 3: tipo secundário (senão, primário); 4: tipo primário; 5: tabela de tipos; 6:
se sair o próprio tipo do Pokémon, role de novo). Área Zero/Tera Raid: role direto a
Tabela de Tipos (1d20: 1 role de novo, 2-19 = Normal..Fada na ordem usual do jogo, 20 = o
jogador escolhe).</p>
<h3>Tipo Estelar (19º tipo)</h3>
<p>Mantém as características defensivas dos tipos originais. Recebe STAB para todos os
tipos; se usar um Move do mesmo tipo que os originais, o STAB é dobrado — mas cada bônus
de STAB (incluindo o dos tipos originais) só se aplica uma vez por tipo enquanto o
Pokémon estiver em campo.</p>
""".strip()

PALDEA_DESCRIPTION = """
<p>Você cresceu na vasta e ensolarada região de Paldea. Marcada por uma mistura única de
arquitetura clássica e tecnologia de ponta, Paldea é um lugar onde a educação e a
exploração caminham juntas. Seus cidadãos são incentivados desde cedo a sair em sua
própria "Busca pelo Tesouro" para descobrir quem realmente são.</p>
<h3>Espírito Acadêmico</h3>
<p>Seja na Academia Naranja ou Uva, você foi treinado para observar o mundo com
curiosidade e dedicação. O estudo constante e a vida social vibrante moldaram sua mente.
Você ganha +2 em sua Inteligência e +1 em seu Carisma.</p>
<h3>Em Busca do Tesouro</h3>
<p>O objetivo de todo cidadão de Paldea é encontrar seu "tesouro" pessoal, o que exige um
olhar atento aos detalhes e aos segredos escondidos na paisagem. Você ganha proficiência
na perícia Investigação.</p>
<h3>Brilho Terastal</h3>
<p>As jornadas por Paldea ensinaram você a viajar em perfeita sintonia com seus Pokémon.
Durante um descanso longo, você pode dedicar 1 hora a alongamentos e exercícios leves com
todos os Pokémon do seu grupo. Ao término do descanso, todos os Pokémon que o realizaram
com você aumentam seus deslocamentos em 5 pés (1,5 metro) até o início do seu próximo
descanso longo. Enquanto você estiver montado em um deles, o deslocamento de caminhada
desse Pokémon aumenta em 10 pés (3 metros), em vez de 5 pés (1,5 metro), e ele ignora o
custo adicional de terrenos difíceis naturais, como lama, areia, neve, vegetação densa e
solo acidentado.</p>
""".strip()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    entries = [
        ("Fenômeno Dynamax e Gigantamax", DYNAMAX_DESCRIPTION, "mecanica-dynamax", "dynamax-gigantamax"),
        ("Fenômeno Terastal", TERASTAL_DESCRIPTION, "mecanica-terastal", "terastal"),
    ]
    for name, desc, category, slug in entries:
        system = {"description": {"value": desc}, "type": {"value": "feat", "subtype": ""}}
        doc = base_item(make_id(f"gen89-{name}"), name, system, category)
        with open(os.path.join(OUT_DIR, f"{slug}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    system = {
        "description": {"value": PALDEA_DESCRIPTION},
        "type": {"value": "feat", "subtype": ""},
        "requirements": "Escolhida na criação do Treinador"
    }
    doc = base_item(make_id("regiao-Paldea"), "Paldea", system, "regiao-de-origem")
    doc["type"] = "feat"
    with open(os.path.join(OUT_DIR, "regiao-paldea.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"3 entradas de mecânica/região (Gen 8-9) escritas em {OUT_DIR}")


if __name__ == "__main__":
    main()
