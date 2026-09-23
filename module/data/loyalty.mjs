// Lealdade (Livro de Regras, pág. 37): a relação entre o Pokémon e o Treinador, numa escala
// de -3 a +3 decidida pelo Mestre conforme o que acontece na história — capturar de forma
// injusta, deixar no PC por muito tempo, vencer uma batalha difícil junto, etc. Diferente de
// Mudança de Status: não é um efeito de combate, persiste entre sessões, então vive como flag
// do Actor (igual Inspiração/XP), não como uma condição do Token HUD.
//
// Só o bônus/penalidade de teste de resistência é automatizado (mesma chave já usada pelo
// estágio de Evasão, system.bonuses.abilities.save). O resto — chance do Move falhar nos
// níveis mais baixos, aumento de PV máximo, escolha de perícia proficiente/especialista —
// fica só como texto de referência no painel: automatizar a ESCOLHA de uma perícia ou
// recalcular PV máximo é fora do escopo seguro deste módulo. O Mestre aplica na hora que o
// nível de Lealdade mudar.
const MODULE_ID = "pokemon-mundo-perfeito";

export const LOYALTY_LEVELS = [
  { value: -3, name: "Desleal", saveBonus: -1,
    note: "Antes de ativar um Move, o Treinador deve rolar mais que 15 em 1d20 ou o Move falha." },
  { value: -2, name: "Indiferente", saveBonus: -1,
    note: "Antes de ativar um Move, o Treinador deve rolar mais que 10 em 1d20 ou o Move falha." },
  { value: -1, name: "Chateado", saveBonus: -1, note: "" },
  { value: 0, name: "Neutro", saveBonus: 0, note: "" },
  { value: 1, name: "Contente", saveBonus: 1, note: "" },
  { value: 2, name: "Satisfeito", saveBonus: 1,
    note: "PV máximo +metade do nível (arred. p/ cima). Ganha 1 perícia proficiente à escolha." },
  { value: 3, name: "Leal", saveBonus: 1,
    note: "PV máximo +nível. A perícia proficiente escolhida (em Satisfeito) vira especialista." }
];

export function loyaltyLevel(value) {
  return LOYALTY_LEVELS.find((l) => l.value === value) ?? LOYALTY_LEVELS.find((l) => l.value === 0);
}

export function getLoyalty(actor) {
  return Math.max(-3, Math.min(3, actor.getFlag(MODULE_ID, "loyalty") ?? 0));
}

async function syncLoyaltyEffect(actor, value) {
  const existing = actor.effects.find((e) => e.getFlag(MODULE_ID, "loyaltyEffect"));
  const bonus = loyaltyLevel(value).saveBonus;
  if (!bonus) {
    if (existing) await existing.delete();
    return;
  }
  const data = {
    name: `Lealdade (${loyaltyLevel(value).name})`,
    img: "icons/magic/life/heart-cross-blue.webp",
    changes: [{ key: "system.bonuses.abilities.save", mode: 2, value: String(bonus), priority: null }],
    disabled: false,
    transfer: false,
    flags: { [MODULE_ID]: { loyaltyEffect: true } }
  };
  if (existing) await existing.update(data);
  else await actor.createEmbeddedDocuments("ActiveEffect", [data]);
}

export async function setLoyalty(actor, value) {
  const clamped = Math.max(-3, Math.min(3, value));
  await actor.setFlag(MODULE_ID, "loyalty", clamped);
  await syncLoyaltyEffect(actor, clamped);
  if (actor.sheet?.rendered) actor.sheet.render(false);
}
