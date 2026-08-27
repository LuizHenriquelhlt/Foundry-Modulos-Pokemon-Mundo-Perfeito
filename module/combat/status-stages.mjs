// Mudanças de Status (Livro de Regras, pág. 71): 8 estágios acumuláveis de -6 a +6, cada um
// com um efeito fixo por estágio. Cada atributo alterado vira seu PRÓPRIO ActiveEffect
// (transfer:false, recriado a cada mudança), usando um ícone temático fixo por atributo
// (espada = Ataque, cérebro = Ataque Especial, escudo = Defesa etc. — todos já usados em
// algum outro lugar deste módulo, então o caminho é garantidamente válido) tingido de verde
// (estágio positivo) ou vermelho (negativo) via "tint" — em vez de gerar um selo numérico
// próprio por valor, que ficava ilegível no tamanho real que o token desenha o ícone.
//
// Nem todo estágio tem um "bônus" no sentido de Active Effect do dnd5e:
// - Ataque/Ataque Especial: bônus de proficiência × estágio, só que separado por dano
//   corpo a corpo (mwak) e à distância (rwak) — mapeado direto pra
//   system.bonuses.mwak.damage / rwak.damage (confirmado contra o próprio Rage do dnd5e).
//   Usa "@prof" na própria fórmula do Active Effect em vez de multiplicar na hora, então o
//   bônus continua certo sozinho se o Pokémon subir de nível depois.
// - Precisão: +1/estágio nas rolagens de ataque — system.bonuses.mwak.attack / rwak.attack.
// - Evasão: +1/estágio na CA e nos testes de resistência — system.attributes.ac.bonus e
//   system.bonuses.abilities.save (bônus global de resistência, chave conhecida do dnd5e).
// - Velocidade: iniciativa em prof×estágio (system.attributes.init.bonus, também via
//   fórmula "@prof") + 5 pés por estágio em todo tipo de deslocamento.
// - Defesa/Defesa Especial (redução de dano recebido) e Margem de Crítico não têm uma
//   chave de Active Effect confirmada no dnd5e pra automatizar com segurança — ficam só
//   como registro numérico no painel da ficha, aplicados manualmente.
const MODULE_ID = "pokemon-mundo-perfeito";

export const STAGE_STATS = [
  { key: "atk", label: "Ataque", icon: "icons/skills/melee/weapons-crossed-swords-yellow.webp" },
  { key: "spa", label: "Atq. Esp.", icon: "icons/commodities/biological/organ-brain-pink-purple.webp" },
  { key: "def", label: "Defesa", icon: "icons/equipment/shield/heater-crystal-blue.webp" },
  { key: "spd", label: "Def. Esp.", icon: "icons/magic/defensive/barrier-shield-dome-blue-purple.webp" },
  { key: "spe", label: "Velocidade", icon: "icons/commodities/treasure/trinket-wing-white.webp" },
  { key: "acc", label: "Precisão", icon: "icons/skills/ranged/target-bullseye-arrow-glowing.webp" },
  { key: "eva", label: "Evasão", icon: "icons/creatures/eyes/human-single-blue.webp" },
  { key: "crit", label: "Marg. Crítico", icon: "icons/magic/nature/symbol-moon-stars-white.webp" }
];

const POSITIVE_TINT = "#4ade80";
const NEGATIVE_TINT = "#f87171";

export function getStages(actor) {
  const stored = actor.getFlag(MODULE_ID, "stages") ?? {};
  const stages = {};
  for (const { key } of STAGE_STATS) stages[key] = stored[key] ?? 0;
  return stages;
}

function changesFor(key, value) {
  const add = (k, v) => (v ? [{ key: k, mode: 2, value: String(v), priority: null }] : []);
  switch (key) {
    case "atk": return add("system.bonuses.mwak.damage", `${value} * @prof`);
    case "spa": return add("system.bonuses.rwak.damage", `${value} * @prof`);
    case "acc":
      return [...add("system.bonuses.mwak.attack", value), ...add("system.bonuses.rwak.attack", value)];
    case "eva":
      return [...add("system.attributes.ac.bonus", value), ...add("system.bonuses.abilities.save", value)];
    case "spe": {
      const changes = add("system.attributes.init.bonus", `${value} * @prof`);
      for (const move of ["walk", "swim", "fly", "climb", "burrow"]) {
        changes.push(...add(`system.attributes.movement.${move}`, value * 5));
      }
      return changes;
    }
    default:
      return []; // def, spd, crit — sem chave confirmada, só o registro no painel
  }
}

function findEffect(actor, key) {
  return actor.effects.find((e) => e.getFlag(MODULE_ID, "stageKey") === key);
}

async function syncStat(actor, key, value, meta) {
  const existing = findEffect(actor, key);
  if (value === 0) {
    if (existing) await existing.delete();
    return;
  }
  const direction = value > 0 ? "up" : "down";
  const data = {
    name: `${meta.label} ${value > 0 ? "+" : ""}${value}`,
    img: meta.icon,
    tint: value > 0 ? POSITIVE_TINT : NEGATIVE_TINT,
    changes: changesFor(key, value),
    disabled: false, transfer: false,
    // O Foundry só desenha o ícone no token pra effects "temporários" (isTemporary), decidido
    // por ter duration>0 OU pelo menos uma entrada em "statuses" — sem nenhum dos dois o
    // effect funciona mecanicamente mas fica invisível no token. Inclui o id persistente
    // (pra achar de novo em findEffect) E o id de ↑/↓ do menu de status do Token — assim o
    // ícone "Ataque ↑" aparece MARCADO/selecionado no grid sempre que o estágio for positivo,
    // e "Ataque ↓" quando negativo, do mesmo jeito que Envenenado/Agarrado ficam marcados.
    statuses: [`${MODULE_ID}-stage-${key}`, `${MODULE_ID}-${key}-${direction}`],
    flags: { [MODULE_ID]: { stageKey: key } }
  };
  if (existing) await existing.update(data);
  else await actor.createEmbeddedDocuments("ActiveEffect", [data]);
}

export async function setStage(actor, key, value) {
  const clamped = Math.max(-6, Math.min(6, value));
  await actor.setFlag(MODULE_ID, "stages", { ...getStages(actor), [key]: clamped });
  const meta = STAGE_STATS.find((s) => s.key === key);
  await syncStat(actor, key, clamped, meta);
}

export async function clearStages(actor) {
  for (const { key } of STAGE_STATS) {
    const existing = findEffect(actor, key);
    if (existing) await existing.delete();
  }
  const stages = {};
  for (const { key } of STAGE_STATS) stages[key] = 0;
  await actor.setFlag(MODULE_ID, "stages", stages);
}

// O dnd5e RECONSTRÓI CONFIG.statusEffects inteiro (de array pra objeto por id) durante o
// próprio hook "setup" dele, a partir de CONFIG.DND5E.conditionTypes + CONFIG.DND5E.statusEffects
// — nosso hook "init" roda antes disso, então empilhar direto em CONFIG.statusEffects.push(...)
// (como se fosse um array puro do Foundry) simplesmente desaparecia quando o "setup" do dnd5e
// sobrescrevia o array inteiro logo em seguida. O jeito certo é registrar em
// CONFIG.DND5E.conditionTypes (mesmo lugar que o módulo "(pk5e)" usa) — o dnd5e lê isso
// durante o "setup" dele e monta o CONFIG.statusEffects final incluindo essas entradas.
export function registerStatusEffects() {
  for (const { key, label, icon } of STAGE_STATS) {
    CONFIG.DND5E.conditionTypes[`${MODULE_ID}-${key}-up`] = { name: `${label} ↑`, img: icon, pseudo: true };
    CONFIG.DND5E.conditionTypes[`${MODULE_ID}-${key}-down`] = { name: `${label} ↓`, img: icon, pseudo: true };
  }
}

// Hook applyTokenStatusEffect(token, statusId): dispara ANTES do Foundry aplicar o toggle
// padrão dele. Clicar liga o estágio em +1 (ou -1) igual a qualquer condição normal
// (Envenenado, Agarrado); clicar de novo no MESMO ícone desliga (volta a 0) — não empilha
// estágios maiores por clique repetido no token (isso é só pros botões +/- da própria
// ficha, que continuam indo até 6). Clicar no ícone OPOSTO enquanto o atributo já está
// alterado no outro sentido substitui a mudança em vez de somar (Ataque não fica ao mesmo
// tempo "pra cima" e "pra baixo").
export function handleTokenStatusEffect(token, statusId) {
  const prefix = `${MODULE_ID}-`;
  if (!statusId.startsWith(prefix)) return true;
  const rest = statusId.slice(prefix.length);
  const sepIndex = rest.lastIndexOf("-");
  const key = rest.slice(0, sepIndex);
  const direction = rest.slice(sepIndex + 1);
  if ((direction !== "up" && direction !== "down") || !STAGE_STATS.some((s) => s.key === key)) return true;

  const actor = token.actor;
  if (!actor) return false;
  const current = getStages(actor)[key];
  const isUp = direction === "up";
  const alreadyOn = isUp ? current > 0 : current < 0;
  setStage(actor, key, alreadyOn ? 0 : (isUp ? 1 : -1));
  return false;
}
