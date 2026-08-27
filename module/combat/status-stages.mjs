// Mudanças de Status (Livro de Regras, pág. 71): 8 estágios acumuláveis de -6 a +6, cada um
// com um efeito fixo por estágio. Cada atributo alterado vira seu PRÓPRIO ActiveEffect
// (transfer:false, recriado a cada mudança), com um selo próprio (verde pra estágio
// positivo, vermelho pra negativo, só o número — sem a sigla do atributo dentro do desenho:
// o ícone do token renderiza bem pequeno de verdade na tela, e sigla+número juntos viravam
// uma mancha ilegível nesse tamanho; a sigla continua no NOME do efeito, "Ataque +1", visível
// ao passar o mouse no ícone). Assim cada atributo alterado aparece como selo separado no
// token, em vez de um ícone genérico só avisando "tem algo ativo". Os 96 selos (8 atributos
// × estágios -6..+6, sem o zero) são arquivos .svg estáticos em assets/stages/ (gerados por
// scripts/generate-stage-icons.mjs) — o schema do dnd5e valida que "img" termine numa
// extensão de arquivo reconhecida, então um data URI gerado na hora (testado e rejeitado:
// "does not have a valid file extension") não funciona; os arquivos existem de antemão pra
// cobrir todas as combinações possíveis.
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
//   como registro numérico (no painel e no selo do token), aplicados manualmente.
const MODULE_ID = "pokemon-mundo-perfeito";

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

function stageIcon(key, value) {
  const sign = value > 0 ? "plus" : "minus";
  return `modules/${MODULE_ID}/assets/stages/${key}-${sign}${Math.abs(value)}.svg`;
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
      return []; // def, spd, crit — sem chave confirmada, só o selo visual
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
  const data = {
    name: `${meta.label} ${value > 0 ? "+" : ""}${value}`,
    img: stageIcon(key, value),
    changes: changesFor(key, value),
    disabled: false, transfer: false,
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
