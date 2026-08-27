// Mudanças de Status (Livro de Regras, pág. 71): 8 estágios acumuláveis de -6 a +6.
//
// Até a v1.19 este módulo tentava interceptar o clique no HUD do Token via um hook
// "applyTokenStatusEffect" pra rodar a própria lógica de estágio por cima — só que esse
// hook não existe nesse ponto do fluxo real do dnd5e (conferido lendo o código-fonte:
// module/applications/hud/token-hud.mjs). O clique no HUD do dnd5e vai direto pra
// TokenHUD5e#onToggleEffect -> actor.toggleStatusEffect(id, {levels}) -> quando o status
// tem "levels" configurado, ConditionData._applyDelta cria/incrementa/decrementa/remove um
// ActiveEffect do tipo "condition" sozinho, sem chamar nenhum hook nosso — por isso nada
// acontecia (o efeito "bonito" com tint que a v1.19 criava simplesmente nunca era o mesmo
// que o dnd5e usa pra decidir o que mostrar).
//
// A v1.20 usa o MESMO mecanismo nativo que o dnd5e já usa pra Exaustão — uma condição de 1
// a 6 níveis, com ícone próprio por nível (module/data/active-effect/condition.mjs:
// ConditionData#getIconByLevel sempre troca a imagem pra "<base>-<nível>.<ext>", por isso
// os SVGs em assets/stages/ existem numerados de 1 a 6, gerados por
// scripts/generate-stage-icons.mjs). Cada direção (Ataque ↑ / Ataque ↓ etc.) é registrada
// como sua própria condição com "levels: 6" em CONFIG.DND5E.conditionTypes — o dnd5e cuida
// sozinho de criar/incrementar/decrementar/remover o efeito ao clicar no HUD (botão esquerdo
// = +1 nível, botão direito = -1, igual Exaustão), inclusive aparecer selecionado/destacado
// na grade e visível no token, sem nenhum código nosso no meio do clique.
//
// Como uma condição do dnd5e só cresce num sentido, um estágio bidirecional -6..+6 precisa
// de duas condições independentes por atributo ("-up"/"-down"), mantidas mutuamente
// exclusivas por este módulo (reage a qualquer uma mudar e zera a oposta), mais um terceiro
// efeito "mecânico" próprio — sem vínculo com o HUD, invisível no token — que carrega os
// "changes" de bônus de fato. Os três ficam sincronizados via hooks reativos
// (createActiveEffect/updateActiveEffect/deleteActiveEffect) sempre que qualquer um muda,
// seja pelo HUD do Token ou pelos botões +/- da própria ficha (que chamam o mesmíssimo
// Actor#toggleStatusEffect nativo, não uma lógica própria separada).
//
// Nem todo estágio tem um "bônus" no sentido de Active Effect do dnd5e:
// - Ataque/Ataque Especial: bônus de proficiência × estágio, separado por dano corpo a
//   corpo (mwak) e à distância (rwak) — system.bonuses.mwak.damage / rwak.damage
//   (confirmado contra o próprio Rage do dnd5e). Usa "@prof" na fórmula em vez de
//   multiplicar na hora, então o bônus continua certo sozinho se o Pokémon subir de nível.
// - Precisão: +1/estágio nas rolagens de ataque — system.bonuses.mwak.attack / rwak.attack.
// - Evasão: +1/estágio na CA e nos testes de resistência — system.attributes.ac.bonus e
//   system.bonuses.abilities.save (bônus global de resistência, chave conhecida do dnd5e).
// - Velocidade: iniciativa em prof×estágio (system.attributes.init.bonus, via "@prof") +
//   5 pés por estágio em todo tipo de deslocamento.
// - Defesa/Defesa Especial (redução de dano recebido) e Margem de Crítico não têm uma
//   chave de Active Effect confirmada no dnd5e pra automatizar com segurança — ficam só
//   como registro visível (nome do efeito) e no painel da ficha.
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

function conditionId(key, direction) {
  return `${MODULE_ID}-${key}-${direction}`;
}

function iconPath(key, direction) {
  return `modules/${MODULE_ID}/assets/stages/${key}-${direction}.svg`;
}

function parseConditionId(statusId) {
  const prefix = `${MODULE_ID}-`;
  if (!statusId?.startsWith(prefix)) return null;
  const rest = statusId.slice(prefix.length);
  const sep = rest.lastIndexOf("-");
  const key = rest.slice(0, sep);
  const direction = rest.slice(sep + 1);
  if (!STAGE_STATS.some((s) => s.key === key) || (direction !== "up" && direction !== "down")) return null;
  return { key, direction };
}

function conditionEffect(actor, statusId) {
  return actor.effects.find((e) => e.type === "condition" && e.system?.type === statusId);
}

function conditionLevel(actor, statusId) {
  return conditionEffect(actor, statusId)?.system?.level ?? 0;
}

export function getStages(actor) {
  const stages = {};
  for (const { key } of STAGE_STATS) {
    stages[key] = conditionLevel(actor, conditionId(key, "up")) - conditionLevel(actor, conditionId(key, "down"));
  }
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
      return []; // def, spd, crit — sem chave confirmada, só o registro visível
  }
}

// Efeito próprio que carrega os "changes" de bônus de verdade — sem "statuses", então não
// aparece por conta própria no token (a arte/seleção no HUD já vêm do efeito nativo de
// condição "-up"/"-down"; ter os dois com "statuses" duplicaria o ícone no token).
async function syncMechanicalEffect(actor, key) {
  const value = getStages(actor)[key];
  const meta = STAGE_STATS.find((s) => s.key === key);
  const existing = actor.effects.find((e) => e.getFlag(MODULE_ID, "mechKey") === key);
  if (value === 0) {
    if (existing) await existing.delete();
    return;
  }
  const data = {
    name: `${meta.label} ${value > 0 ? "+" : ""}${value}`,
    img: iconPath(key, value > 0 ? "up" : "down"),
    changes: changesFor(key, value),
    disabled: false,
    transfer: false,
    flags: { [MODULE_ID]: { mechKey: key } }
  };
  if (existing) await existing.update(data);
  else await actor.createEmbeddedDocuments("ActiveEffect", [data]);
}

// Só chega a coexistir "-up" e "-down" ao mesmo tempo clicando os dois separadamente no HUD
// do Token (os botões da própria ficha nunca deixam isso acontecer, ver stepStage) — quando
// isso acontece, a direção que acabou de mudar vence e a oposta é zerada.
async function enforceExclusive(actor, touchedId) {
  const info = parseConditionId(touchedId);
  if (!info) return;
  const opposite = conditionEffect(actor, conditionId(info.key, info.direction === "up" ? "down" : "up"));
  if (opposite) await opposite.delete();
}

async function onStatusEffectTouched(effect, { deleted = false } = {}) {
  if (effect?.type !== "condition") return;
  const info = parseConditionId(effect.system?.type);
  const actor = effect.parent;
  if (!info || actor?.documentName !== "Actor") return;

  if (!deleted) await enforceExclusive(actor, effect.system.type);
  await syncMechanicalEffect(actor, info.key);
}

// Chamado pelos botões +/- da própria ficha — dá um passo de ±1 no estágio (-6..+6) usando
// o MESMO caminho nativo que um clique no HUD do Token usaria (Actor#toggleStatusEffect com
// "levels"), então o efeito nativo de condição, o efeito mecânico e o HUD ficam sempre
// sincronizados não importa por onde o Mestre mexeu no estágio.
export async function stepStage(actor, key, delta) {
  const step = Math.sign(delta);
  if (!step) return;
  const current = getStages(actor)[key];
  const target = Math.max(-6, Math.min(6, current + step));
  if (target === current) return;

  const direction = (target || current) > 0 ? "up" : "down";
  const magnitudeGrew = Math.abs(target) > Math.abs(current);
  await actor.toggleStatusEffect(conditionId(key, direction), { levels: magnitudeGrew ? 1 : -1 });
}

export async function clearStages(actor) {
  for (const { key } of STAGE_STATS) {
    for (const direction of ["up", "down"]) {
      const effect = conditionEffect(actor, conditionId(key, direction));
      if (effect) await effect.delete();
    }
  }
}

// O dnd5e RECONSTRÓI CONFIG.statusEffects inteiro (de array pra objeto por id) durante o
// próprio hook "setup" dele, a partir de CONFIG.DND5E.conditionTypes + CONFIG.DND5E.statusEffects
// — nosso hook "init" roda antes disso, então empilhar direto em CONFIG.statusEffects.push(...)
// (como se fosse um array puro do Foundry) simplesmente desaparecia quando o "setup" do dnd5e
// sobrescrevia o array inteiro logo em seguida. O jeito certo é registrar em
// CONFIG.DND5E.conditionTypes (mesmo lugar que o módulo "(pk5e)" usa e que o próprio dnd5e usa
// pra Exaustão) — o dnd5e lê isso durante o "setup" dele e monta o CONFIG.statusEffects final
// incluindo essas entradas, "levels" e tudo.
export function registerStatusEffects() {
  for (const { key, label } of STAGE_STATS) {
    CONFIG.DND5E.conditionTypes[conditionId(key, "up")] =
      { name: `${label} ↑`, img: iconPath(key, "up"), levels: 6, pseudo: true };
    CONFIG.DND5E.conditionTypes[conditionId(key, "down")] =
      { name: `${label} ↓`, img: iconPath(key, "down"), levels: 6, pseudo: true };
  }

  Hooks.on("createActiveEffect", (effect) => onStatusEffectTouched(effect));
  Hooks.on("updateActiveEffect", (effect) => onStatusEffectTouched(effect));
  Hooks.on("deleteActiveEffect", (effect) => onStatusEffectTouched(effect, { deleted: true }));
}
