#!/usr/bin/env python3
"""
Cria os 5 itens de benefício da tabela "Progressão de Níveis do Pokémon" (Livro de
Regras) em packs/_source/trainer-features. O item de classe "<Espécie> Level" gerado
por convert-to-dnd5e-native.py concede esses itens automaticamente (ItemGrant) nos
níveis certos da tabela quando o Pokémon sobe de nível na ficha.

IDs determinísticos (mesmo make_id/seed usado pelo conversor) para que os UUIDs dos
ItemGrants apontem sempre para os mesmos documentos.
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


STAB_TABLE_HTML = (
    "<table><thead><tr><th>Nível</th><th>Bônus de STAB</th></tr></thead><tbody>"
    "<tr><td>1º-2º</td><td>+0</td></tr><tr><td>3º-6º</td><td>+1</td></tr>"
    "<tr><td>7º-10º</td><td>+2</td></tr><tr><td>11º-14º</td><td>+3</td></tr>"
    "<tr><td>15º-18º</td><td>+4</td></tr><tr><td>19º-20º</td><td>+5</td></tr>"
    "</tbody></table>"
)

FEATURES = [
    ("Ponto de EV", "ponto-de-ev",
     "<p>Ganhe 1 Ponto de EV para aumentar um valor de atributo do Pokémon em +1 "
     "(respeitando os limites de EV do Livro de Regras, seção Aprimorando seu Pokémon).</p>"),
    ("Aumento de STAB", "aumento-de-stab",
     "<p>O bônus de STAB (dano extra de Moves do mesmo tipo do Pokémon) aumenta conforme a "
     "tabela de Progressão de Níveis:</p>" + STAB_TABLE_HTML +
     "<p><em>Some esse bônus na hora de rolar o dano de qualquer Move do mesmo tipo do "
     "Pokémon — a fórmula de dano dos Moves mostra só o dado e o modificador, de propósito, "
     "pra você somar o que quiser (STAB, Mudança de Status etc.) do jeito que preferir.</em></p>"),
    ("Talento de Pokémon", "talento-de-pokemon",
     "<p>Escolha um Talento da lista de Talentos de Pokémon do Livro de Regras.</p>"),
    ("Aumento de Proficiência", "aumento-de-proficiencia",
     "<p>O Bônus de Proficiência do Pokémon aumenta (+2 nos níveis 1-4, +3 nos 5-8, +4 nos "
     "9-12, +5 nos 13-16, +6 nos 17-20). <em>Aplicado automaticamente pelo nível da classe "
     "— este item é só o registro do marco da tabela.</em></p>"),
    ("Aumento de Dano", "aumento-de-dano",
     "<p>Os dados de dano dos Moves aumentam conforme a seção \"Níveis Superiores\" de cada "
     "Move (patamares nos níveis 5, 10 e 17 — as fórmulas de cada patamar estão na descrição "
     "do próprio Move; atualize a fórmula de dano do Move na ficha).</p>")
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, slug, desc in FEATURES:
        doc_id = make_id(f"progressao-{slug}")
        doc = {
            "_key": f"!items!{doc_id}",
            "_id": doc_id, "name": name, "type": "feat", "img": "icons/svg/upgrade.svg",
            "system": {"description": {"value": desc, "chat": ""},
                        "type": {"value": "", "subtype": ""}, "requirements": "",
                        "uses": {"spent": 0, "max": "", "recovery": []}, "activities": {}},
            "effects": [], "folder": None,
            "flags": {"pokemon-mundo-perfeito": {"category": "progressao-de-nivel"}},
            "_stats": {"coreVersion": "12.331", "systemId": "dnd5e", "systemVersion": "4.3.5",
                       "compendiumSource": None, "duplicateSource": None},
            "sort": 960, "ownership": {"default": 0}
        }
        with open(os.path.join(OUT_DIR, f"progressao-{slug}.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    print(f"{len(FEATURES)} benefícios de progressão escritos em {OUT_DIR}")


if __name__ == "__main__":
    main()
