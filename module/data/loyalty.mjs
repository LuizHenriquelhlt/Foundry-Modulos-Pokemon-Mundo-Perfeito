// Lealdade + Afinidade (Livro de Regras pág. 37, + homebrew "Afinidade" no compêndio de
// Regras > Homebrews). Por pedido explícito do Luiz, o campo de Lealdade da ficha deixou de
// ser editável diretamente: agora é só um DISPLAY calculado a partir dos Pontos de Afinidade
// (PA) acumulados — o jogador/Mestre soma ou subtrai PA (positivos ou negativos, conforme os
// eventos da mesa), e o nível de Lealdade (Desleal..Leal) muda sozinho ao cruzar os limiares
// da Escala da homebrew. PA não é limitado a -3..+3 como a Lealdade antiga era: pode passar de
// +12 ou de -12 à vontade, só que o nível nomeado já não muda mais depois desses extremos.
//
// Só o bônus/penalidade de teste de resistência é automatizado (mesma chave já usada pelo
// estágio de Evasão, system.bonuses.abilities.save). O resto — chance do Move falhar nos
// níveis mais baixos, aumento de PV máximo, escolha de perícia proficiente/especialista —
// fica só como texto de referência no painel: automatizar a ESCOLHA de uma perícia ou
// recalcular PV máximo é fora do escopo seguro deste módulo. O Mestre aplica na hora que o
// nível mudar.
const MODULE_ID = "pokemon-mundo-perfeito";

// Escala da homebrew "Afinidade": "threshold" é o PA em que aquele nível é alcançado (positivo
// = precisa ter PA >= threshold; negativo = precisa ter PA <= threshold). Nomes/notas mantidos
// iguais aos da Lealdade original (mesmos 7 níveis do Controle de SR).
export const AFFINITY_LEVELS = [
  { value: -3, name: "Desleal", threshold: -12, saveBonus: -1,
    note: "Antes de ativar um Move, o Treinador deve rolar mais que 15 em 1d20 ou o Move falha." },
  { value: -2, name: "Indiferente", threshold: -7, saveBonus: -1,
    note: "Antes de ativar um Move, o Treinador deve rolar mais que 10 em 1d20 ou o Move falha." },
  { value: -1, name: "Chateado", threshold: -3, saveBonus: -1, note: "" },
  { value: 0, name: "Neutro", threshold: 0, saveBonus: 0, note: "" },
  { value: 1, name: "Contente", threshold: 3, saveBonus: 1, note: "" },
  { value: 2, name: "Satisfeito", threshold: 7, saveBonus: 1,
    note: "PV máximo +metade do nível (arred. p/ cima). Ganha 1 perícia proficiente à escolha." },
  { value: 3, name: "Leal", threshold: 12, saveBonus: 1,
    note: "PV máximo +nível. A perícia proficiente escolhida (em Satisfeito) vira especialista." }
];

const BY_VALUE = Object.fromEntries(AFFINITY_LEVELS.map((l) => [l.value, l]));

/** Nível de Lealdade correspondente a um total de Pontos de Afinidade (Escala da homebrew). */
export function affinityLevel(pa) {
  if (pa >= 0) {
    if (pa >= 12) return BY_VALUE[3];
    if (pa >= 7) return BY_VALUE[2];
    if (pa >= 3) return BY_VALUE[1];
    return BY_VALUE[0];
  }
  if (pa <= -12) return BY_VALUE[-3];
  if (pa <= -7) return BY_VALUE[-2];
  if (pa <= -3) return BY_VALUE[-1];
  return BY_VALUE[0];
}

// Compatibilidade: quem já chamava loyaltyLevel(nível -3..3) da versão antiga — usado só pelo
// código deste módulo, mas mantido como alias claro em vez de quebrar silenciosamente.
export const loyaltyLevel = affinityLevel;

export function getAffinity(actor) {
  const stored = actor.getFlag(MODULE_ID, "affinity");
  if (stored !== undefined) return stored;
  // Migração de mundos que já tinham a Lealdade antiga (-3..+3) marcada antes desta homebrew:
  // usa o PA exato daquele nível na Escala, em vez de zerar a Afinidade de todo mundo.
  const oldLoyalty = actor.getFlag(MODULE_ID, "loyalty");
  if (oldLoyalty !== undefined) return BY_VALUE[oldLoyalty]?.threshold ?? 0;
  return 0;
}

async function syncLoyaltyEffect(actor, pa) {
  const level = affinityLevel(pa);
  const existing = actor.effects.find((e) => e.getFlag(MODULE_ID, "loyaltyEffect"));
  if (!level.saveBonus) {
    if (existing) await existing.delete();
    return;
  }
  const data = {
    name: `Lealdade (${level.name})`,
    img: "icons/magic/life/heart-cross-blue.webp",
    changes: [{ key: "system.bonuses.abilities.save", mode: 2, value: String(level.saveBonus), priority: null }],
    disabled: false,
    transfer: false,
    flags: { [MODULE_ID]: { loyaltyEffect: true } }
  };
  if (existing) await existing.update(data);
  else await actor.createEmbeddedDocuments("ActiveEffect", [data]);
}

/** Define o total de Pontos de Afinidade (não é clampado — pode passar de ±12 à vontade). */
export async function setAffinity(actor, pa) {
  const value = Math.trunc(pa) || 0;
  await actor.setFlag(MODULE_ID, "affinity", value);
  // Some mundos ainda tinham a flag antiga "loyalty" (nível -3..3) — some-la depois de definir
  // Afinidade evitaria confundir getAffinity() numa leitura futura sem a flag "affinity".
  if (actor.getFlag(MODULE_ID, "loyalty") !== undefined) {
    await actor.unsetFlag(MODULE_ID, "loyalty");
  }
  await syncLoyaltyEffect(actor, value);
  if (actor.sheet?.rendered) actor.sheet.render(false);
}
