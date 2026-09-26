/**
 * Terastalização (compêndio de Regras > Mecânicas Especiais > "Terastalização").
 *
 * Diferente da Mega Evolução (que já tem um catálogo de Mega Pedras por espécie), o Tera
 * Tipo é um traço individual do Pokémon, não da espécie — por isso o item "Fator Terastal"
 * (compêndio "items") é genérico: ele só libera o botão "Terastalizar" na ficha (equivalente
 * a segurar uma Orbe Tera), e o Tipo Tera em si é escolhido no diálogo a cada uso, com o tipo
 * primário do próprio Pokémon como padrão (Livro de Regras: "a menos que indicado o
 * contrário, o Tera Tipo é igual ao seu tipo primário").
 *
 * Só a troca de tipagem DEFENSIVA é automatizada (igual ao efeito de tipo da Mega Evolução).
 * O bônus de STAB duplicado (e a regra do Tipo Estelar de só valer 1x por tipo em campo) não
 * é automatizado — o dano dos Moves já é deixado "limpo" neste módulo de propósito (ver
 * histórico de v1.23.0), pro jogador somar o que quiser na hora de rolar.
 */
import { TYPE_LABELS } from "./type-chart.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const SNAPSHOT_FLAG = "terastalSnapshot";
export const STELLAR_KEY = "stellar";

function typeFeatItem(typeKey) {
  const label = typeKey === STELLAR_KEY ? "Estelar" : (TYPE_LABELS[typeKey] ?? typeKey);
  return {
    name: `Tipo ${label}`,
    type: "feat",
    img: `modules/${MODULE_ID}/assets/types/${typeKey === STELLAR_KEY ? "normal" : typeKey}.svg`,
    system: {
      description: { value: `<p>Este Pokémon é do tipo ${label}.</p>`, chat: "" },
      type: { value: "", subtype: "" },
      requirements: "",
      uses: { spent: 0, max: "", recovery: [] },
      activities: {}
    },
    effects: [], flags: {}, sort: 0
  };
}

/** Item "Fator Terastal" no inventário do Pokémon, esteja equipado ou não. */
export function findMatchingTeraFactor(actor) {
  if (!actor?.getFlag(MODULE_ID, "species")) return null;
  return actor.items.find((i) => i.getFlag(MODULE_ID, "category") === "tera-factor") ?? null;
}

/** Item "Fator Terastal" equipado neste Pokémon, se houver. */
export function findEquippedTeraFactor(actor) {
  const factor = findMatchingTeraFactor(actor);
  return factor && factor.system.equipped ? factor : null;
}

export function isTerastallized(actor) {
  return !!actor?.getFlag(MODULE_ID, SNAPSHOT_FLAG);
}

export function canTerastallize(actor) {
  return !isTerastallized(actor) && !!findEquippedTeraFactor(actor);
}

/** @param {string} teraType Chave de tipo (ex.: "fire"), ou STELLAR_KEY pro Tipo Estelar. */
export async function terastallize(actor, teraType) {
  if (isTerastallized(actor)) return { status: "already" };
  if (!findEquippedTeraFactor(actor)) return { status: "no-factor" };

  const species = actor.getFlag(MODULE_ID, "species");
  const isStellar = teraType === STELLAR_KEY;
  const update = {
    [`flags.${MODULE_ID}.${SNAPSHOT_FLAG}`]: { types: { ...species.types }, teraType }
  };
  if (!isStellar) update[`flags.${MODULE_ID}.species.types`] = { type1: teraType, type2: null };

  await actor.update(update);

  if (!isStellar) {
    const toDelete = actor.items.filter((i) => i.type === "feat" && i.name.startsWith("Tipo ")).map((i) => i.id);
    if (toDelete.length) await actor.deleteEmbeddedDocuments("Item", toDelete);
    await actor.createEmbeddedDocuments("Item", [typeFeatItem(teraType)]);
  }

  if (actor.sheet?.rendered) actor.sheet.render(false);

  const label = isStellar ? "Estelar" : (TYPE_LABELS[teraType] ?? teraType);
  const defenseNote = isStellar
    ? "Tipo Estelar: mantém as resistências/fraquezas dos tipos originais, mas fica vulnerável a Moves do próprio Tipo Estelar (Tera Blast/Tera Starstorm)."
    : "Defensivamente, passa a ser considerado só do Tera Tipo (perde as resistências/fraquezas dos tipos originais).";
  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `<p>✨ <strong>${actor.name}</strong> Terastalizou pro Tipo <strong>${label}</strong>!</p>
      <p><em>Recebe STAB pro Tera Tipo e pros tipos originais (dobrado se coincidirem — some manualmente na
      hora de rolar). ${defenseNote}</em></p>`
  });

  return { status: "terastallized" };
}

export async function revertTerastal(actor) {
  const snapshot = actor.getFlag(MODULE_ID, SNAPSHOT_FLAG);
  if (!snapshot) return { status: "not-terastallized" };

  const wasStellar = snapshot.teraType === STELLAR_KEY;
  const update = { [`flags.${MODULE_ID}.-=${SNAPSHOT_FLAG}`]: null };
  if (!wasStellar) update[`flags.${MODULE_ID}.species.types`] = snapshot.types;

  await actor.update(update);

  if (!wasStellar) {
    const toDelete = actor.items.filter((i) => i.type === "feat" && i.name.startsWith("Tipo ")).map((i) => i.id);
    if (toDelete.length) await actor.deleteEmbeddedDocuments("Item", toDelete);
    const toCreate = [typeFeatItem(snapshot.types.type1)];
    if (snapshot.types.type2) toCreate.push(typeFeatItem(snapshot.types.type2));
    await actor.createEmbeddedDocuments("Item", toCreate);
  }

  if (actor.sheet?.rendered) actor.sheet.render(false);
  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `<p>✨ <strong>${actor.name}</strong> desfez a Terastalização.</p>`
  });

  return { status: "reverted" };
}
