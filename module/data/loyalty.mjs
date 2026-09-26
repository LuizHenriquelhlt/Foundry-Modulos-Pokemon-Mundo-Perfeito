// Lealdade + Afinidade (Livro de Regras pág. 37, + homebrew "Afinidade" no compêndio de
// Regras > Homebrews). Por pedido explícito do Luiz, o campo de Lealdade da ficha deixou de
// ser editável diretamente: agora é só um DISPLAY calculado a partir dos Pontos de Afinidade
// (PA) acumulados — o jogador/Mestre soma ou subtrai PA (positivos ou negativos, conforme os
// eventos da mesa), e o nível de Lealdade (Desleal..Leal) muda sozinho ao cruzar os limiares
// da Escala da homebrew. PA não é limitado a -3..+3 como a Lealdade antiga era: pode passar de
// +12 ou de -12 à vontade, só que o nível nomeado já não muda mais depois desses extremos.
//
// Automatizado: bônus/penalidade de teste de resistência (system.bonuses.abilities.save,
// mesma chave já usada pelo estágio de Evasão), aumento de PV máximo em Satisfeito/Leal
// (system.attributes.hp.max, fórmula baseada em @details.level — confirmado real pesquisando
// module/data/abstract/actor-data-model.mjs na tag release-5.3.3: getRollData() faz
// `{...this}`, então @details.level espelha system.details.level de qualquer Actor "npc"),
// a perícia proficiente/especialista de Satisfeito/Leal (system.skills.<key>.value, modo
// UPGRADE pra nunca *piorar* uma perícia que já fosse melhor por outro motivo) e a chance do
// Move falhar em Indiferente/Desleal (hook "dnd5e.preUseActivity", confirmado real e
// cancelável pesquisando module/documents/activity/mixin.mjs na mesma tag — retornar `false`
// no hook cancela o uso da Activity antes de qualquer rolagem/consumo).
//
// O restante (o Mestre decidir SE a perícia deve ser trocada quando repetida por evolução,
// etc.) continua manual — só a mecânica numérica é automatizada.
const MODULE_ID = "pokemon-mundo-perfeito";

// Escala da homebrew "Afinidade": "threshold" é o PA em que aquele nível é alcançado (positivo
// = precisa ter PA >= threshold; negativo = precisa ter PA <= threshold). Nomes/notas mantidos
// iguais aos da Lealdade original (mesmos 7 níveis do Controle de SR).
export const AFFINITY_LEVELS = [
  { value: -3, name: "Desleal", threshold: -12, saveBonus: -1, moveFailThreshold: 15,
    note: "Antes de ativar um Move, o Treinador deve rolar mais que 15 em 1d20 ou o Move falha." },
  { value: -2, name: "Indiferente", threshold: -7, saveBonus: -1, moveFailThreshold: 10,
    note: "Antes de ativar um Move, o Treinador deve rolar mais que 10 em 1d20 ou o Move falha." },
  { value: -1, name: "Chateado", threshold: -3, saveBonus: -1, moveFailThreshold: null, note: "" },
  { value: 0, name: "Neutro", threshold: 0, saveBonus: 0, moveFailThreshold: null, note: "" },
  { value: 1, name: "Contente", threshold: 3, saveBonus: 1, moveFailThreshold: null, note: "" },
  { value: 2, name: "Satisfeito", threshold: 7, saveBonus: 1, moveFailThreshold: null,
    hpBonusFormula: "ceil(@details.level / 2)", skillProficiency: 1,
    note: "PV máximo +metade do nível (arred. p/ cima). Ganha 1 perícia proficiente à escolha." },
  { value: 3, name: "Leal", threshold: 12, saveBonus: 1, moveFailThreshold: null,
    hpBonusFormula: "@details.level", skillProficiency: 2,
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

/** Perícia escolhida (pág. 37: "ganha uma perícia proficiente à escolha") — chave de 3 letras
 * do dnd5e (ex.: "ath"), ou "" se ainda não escolhida. Persiste através de flutuações de PA. */
export function getAffinitySkill(actor) {
  return actor.getFlag(MODULE_ID, "affinitySkill") ?? "";
}

export async function setAffinitySkill(actor, skillKey) {
  await actor.setFlag(MODULE_ID, "affinitySkill", skillKey);
  await syncLoyaltyEffect(actor, getAffinity(actor));
  if (actor.sheet?.rendered) actor.sheet.render(false);
}

async function syncLoyaltyEffect(actor, pa) {
  const level = affinityLevel(pa);
  const existing = actor.effects.find((e) => e.getFlag(MODULE_ID, "loyaltyEffect"));

  const changes = [];
  if (level.saveBonus) {
    changes.push({ key: "system.bonuses.abilities.save", mode: 2, value: String(level.saveBonus), priority: null });
  }
  if (level.hpBonusFormula) {
    changes.push({ key: "system.attributes.hp.max", mode: 2, value: level.hpBonusFormula, priority: null });
  }
  const skillKey = getAffinitySkill(actor);
  if (level.skillProficiency && skillKey) {
    changes.push({ key: `system.skills.${skillKey}.value`, mode: 4, value: String(level.skillProficiency), priority: null });
  }

  if (!changes.length) {
    if (existing) await existing.delete();
    return;
  }
  const data = {
    name: `Lealdade (${level.name})`,
    img: "icons/magic/life/heart-cross-blue.webp",
    changes,
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

// Hooks.call (não Hooks.callAll) checa `=== false` de forma SÍNCRONA — um handler async
// nunca consegue cancelar a tempo, porque a Promise que ele retorna não é literalmente
// `false`. Por isso a rolagem de 1d20 aqui usa Math.random() em vez de `new Roll(...)`
// (que só resolve via Promise) — é o único jeito de decidir sincronamente dentro do hook.
// O resultado ainda é anunciado no chat, só não é uma Roll "de verdade" do Foundry.
function rollD20() {
  return Math.floor(Math.random() * 20) + 1;
}

/** Hook "dnd5e.preUseActivity" (pág. 37): antes de ativar um Move com o Pokémon Indiferente
 * ou Desleal, o Treinador precisa "rolar mais que 10/15" ou o Move falha. Só entra em ação
 * quando a Activity pertence a um Item embutido num Actor Pokémon (flags.species) — Talentos
 * de Treinador, Habilidades Passivas etc. não têm Activity nenhuma pra usar (feat_stub() cria
 * elas sempre com activities:{}), então nunca disparam este hook de qualquer forma. */
function onPreUseActivity(activity) {
  const actor = activity.item?.actor;
  if (!actor || !actor.getFlag(MODULE_ID, "species")) return;

  const level = affinityLevel(getAffinity(actor));
  if (!level.moveFailThreshold) return;

  const roll = rollD20();
  const success = roll > level.moveFailThreshold;
  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `<p>💔 <strong>${actor.name}</strong> (${level.name}) — ${activity.item.name}: precisa de mais que
      ${level.moveFailThreshold} em 1d20 pra obedecer. Resultado: <strong>${roll}</strong> —
      ${success ? "obedece normalmente." : "<strong>o Move falha!</strong>"}</p>`
  });
  if (!success) return false;
}

export function registerLoyaltyAutomation() {
  Hooks.on("dnd5e.preUseActivity", onPreUseActivity);
}
