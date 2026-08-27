// Mudanças de Status (Livro de Regras, pág. 71): 8 estágios acumuláveis de -6 a +6, cada um
// com um efeito fixo por estágio. Guardado em flags["pokemon-mundo-perfeito"].stages e
// sincronizado num único ActiveEffect gerenciado (recriado a cada mudança) — assim o efeito
// mecânico nunca fica fora de sincronia com os números mostrados no painel da ficha.
//
// Nem todo estágio tem um "bônus" no sentido de Active Effect do dnd5e:
// - Ataque/Ataque Especial: bônus de proficiência × estágio, só que separado por dano
//   corpo a corpo (mwak) e à distância (rwak) — mapeado direto pra
//   system.bonuses.mwak.damage / rwak.damage (confirmado contra o próprio Rage do dnd5e).
// - Precisão: +1/estágio nas rolagens de ataque — system.bonuses.mwak.attack / rwak.attack.
// - Evasão: +1/estágio na CA e nos testes de resistência — system.attributes.ac.bonus e
//   system.bonuses.abilities.save (bônus global de resistência, chave conhecida do dnd5e).
// - Velocidade: iniciativa em prof×estágio (system.attributes.init.bonus) + 5 pés por
//   estágio em todo tipo de deslocamento.
// - Defesa/Defesa Especial (redução de dano recebido) e Margem de Crítico não têm uma
//   chave de Active Effect confirmada no dnd5e pra automatizar com segurança — ficam só
//   como registro numérico no painel, aplicados manualmente pelo Mestre por enquanto.
const MODULE_ID = "pokemon-mundo-perfeito";
const EFFECT_LABEL = "Mudanças de Status";

export const STAGE_STATS = [
  { key: "atk", label: "Ataque" },
  { key: "spa", label: "Atq. Esp." },
  { key: "def", label: "Defesa" },
  { key: "spd", label: "Def. Esp." },
  { key: "spe", label: "Velocidade" },
  { key: "acc", label: "Precisão" },
  { key: "eva", label: "Evasão" },
  { key: "crit", label: "Marg. Crítico" }
];

export function getStages(actor) {
  const stored = actor.getFlag(MODULE_ID, "stages") ?? {};
  const stages = {};
  for (const { key } of STAGE_STATS) stages[key] = stored[key] ?? 0;
  return stages;
}

function buildChanges(stages, prof) {
  const changes = [];
  const add = (key, value) => {
    if (!value) return;
    changes.push({ key, mode: 2, value: String(value), priority: null });
  };

  add("system.bonuses.mwak.damage", stages.atk * prof);
  add("system.bonuses.rwak.damage", stages.spa * prof);
  add("system.bonuses.mwak.attack", stages.acc);
  add("system.bonuses.rwak.attack", stages.acc);
  add("system.attributes.ac.bonus", stages.eva);
  add("system.bonuses.abilities.save", stages.eva);
  add("system.attributes.init.bonus", stages.spe * prof);
  for (const move of ["walk", "swim", "fly", "climb", "burrow"]) {
    add(`system.attributes.movement.${move}`, stages.spe * 5);
  }
  return changes;
}

function findEffect(actor) {
  return actor.effects.find((e) => e.getFlag(MODULE_ID, "statStages"));
}

async function syncEffect(actor, stages) {
  const prof = actor.system.attributes?.prof ?? 2;
  const changes = buildChanges(stages, prof);
  const existing = findEffect(actor);

  if (!changes.length) {
    if (existing) await existing.delete();
    return;
  }
  const data = {
    name: EFFECT_LABEL, img: "icons/skills/movement/arrow-upward-yellow.webp",
    changes, disabled: false, transfer: false,
    flags: { [MODULE_ID]: { statStages: true } }
  };
  if (existing) await existing.update(data);
  else await actor.createEmbeddedDocuments("ActiveEffect", [data]);
}

export async function setStage(actor, key, value) {
  const clamped = Math.max(-6, Math.min(6, value));
  const stages = { ...getStages(actor), [key]: clamped };
  await actor.setFlag(MODULE_ID, "stages", stages);
  await syncEffect(actor, stages);
}

export async function clearStages(actor) {
  const stages = {};
  for (const { key } of STAGE_STATS) stages[key] = 0;
  await actor.setFlag(MODULE_ID, "stages", stages);
  const existing = findEffect(actor);
  if (existing) await existing.delete();
}
