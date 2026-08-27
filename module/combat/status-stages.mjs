// Mudanças de Status (Livro de Regras, pág. 71): 8 estágios acumuláveis de -6 a +6.
//
// HISTÓRICO — pra não cair no mesmo buraco uma terceira vez:
// - v1.19 tentava interceptar o clique no HUD do Token via um hook "applyTokenStatusEffect"
//   que não existe em nenhuma versão real do dnd5e — nunca disparava.
// - v1.20/v1.21 tentaram usar um mecanismo de "condição com nível" (CONFIG.DND5E.
//   conditionTypes[id].levels + ConditionData/_applyDelta, do jeito que a Exaustão parece
//   funcionar) — só que essa pesquisa foi feita direto no branch de DESENVOLVIMENTO do dnd5e
//   no GitHub, que fica na FRENTE do que está de fato lançado. Conferido depois contra a tag
//   real "release-5.3.3" (a versão que este mundo roda de verdade — "system:dnd5e(5.3.3)"
//   no erro que apareceu uma vez): esse mecanismo genérico simplesmente NÃO EXISTE nela.
//   Em 5.3.3, Exaustão é tratada por código só dela, sem nenhum gancho reaproveitável por
//   um módulo de fora (module/documents/active-effect.mjs#_prepareExhaustionLevel e
//   #_manageExhaustion nessa tag são bem diferentes do ConditionData genérico que só existe
//   no branch principal). "levels" no CONFIG era só um campo extra ignorado, e
//   Actor#toggleStatusEffect em 5.3.3 (module/documents/actor/actor.mjs) é só um liga/desliga
//   simples baseado em existência — sem NENHUM suporte a incremento.
//
// Desenho atual (v1.22, conferido contra a tag release-5.3.3, não o branch principal): cada
// direção (Ataque ↑ / Ataque ↓ etc.) é registrada em CONFIG.DND5E.conditionTypes só pra
// aparecer com o ícone certo na grade do HUD do Token — sem "levels" (não faz nada nessa
// versão). O módulo mesmo cuida de tudo o resto: um hook "preCreateActiveEffect" (esse sim
// um hook padrão e estável do próprio Foundry, não algo específico de uma versão do dnd5e)
// cancela a criação "crua" que o Foundry faria sozinho ao clicar no HUD (sem os nossos
// "changes" e sem o ícone certo do estágio) e cria um efeito PRÓPRIO completo no lugar —
// ligando aquela direção em magnitude 1, exatamente como Envenenado/Agarrado (um clique liga,
// outro desliga — isso último já acontece sozinho, porque nessa hora o Foundry vê o efeito
// existente de verdade e apaga ele direto, sem passar pelo hook). Estágios 2-6 só dá pra
// alcançar pelos botões +/- da própria ficha, que gerenciam esse mesmo efeito diretamente
// (create/update/delete na mão — sem depender de toggleStatusEffect, que não incrementa nada
// nessa versão do dnd5e).
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

function baseIconPath(key, direction) {
  return `modules/${MODULE_ID}/assets/stages/${key}-${direction}.svg`;
}

function leveledIconPath(key, direction, level) {
  return `modules/${MODULE_ID}/assets/stages/${key}-${direction}-${level}.svg`;
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

function findStageEffect(actor, key, direction) {
  return actor.effects.find((e) =>
    e.getFlag(MODULE_ID, "stageKey") === key && e.getFlag(MODULE_ID, "stageDirection") === direction);
}

function stageValue(actor, key, direction) {
  return findStageEffect(actor, key, direction)?.getFlag(MODULE_ID, "stageValue") ?? 0;
}

export function getStages(actor) {
  const stages = {};
  for (const { key } of STAGE_STATS) {
    stages[key] = stageValue(actor, key, "up") - stageValue(actor, key, "down");
  }
  return stages;
}

function changesFor(key, value) {
  const add = (k, v) => (v ? [{ key: k, mode: 2, value: String(v), priority: null }] : []);
  switch (key) {
    // Ataque/Atq. Especial não entram aqui — o bônus deles já vem embutido direto na
    // fórmula de dano de cada Move (@pmpAtkStage/@pmpSpaStage, ver roll-data.mjs e scripts/
    // convert-to-dnd5e-native.py): o bônus global do dnd5e por classificação de ataque
    // (mwak/rwak) só existe pra Moves com activity "attack" — não alcança os com activity
    // "save" (a maioria dos Moves "especiais" deste sistema).
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

// Cria/atualiza/apaga o efeito de UMA direção (ex.: só "atk"+"up") pra bater com a magnitude
// pedida (0-6) — sempre o mesmo efeito, sem um segundo efeito "mecânico" separado: agora que
// o módulo cria o efeito inteiro na mão (em vez de deixar o Foundry criar um cru e completar
// depois), dá pra já nascer com ícone do nível certo, "statuses" (aparece selecionado na
// grade do HUD e visível no token) e "changes" (bônus mecânico) tudo junto.
async function setStageEffect(actor, key, direction, value) {
  const clamped = Math.max(0, Math.min(6, value));
  const existing = findStageEffect(actor, key, direction);
  if (clamped === 0) {
    if (existing) await existing.delete();
    return;
  }

  const meta = STAGE_STATS.find((s) => s.key === key);
  const signed = direction === "up" ? clamped : -clamped;
  const data = {
    name: `${meta.label} ${direction === "up" ? "+" : "-"}${clamped}`,
    img: leveledIconPath(key, direction, clamped),
    changes: changesFor(key, signed),
    disabled: false,
    transfer: false,
    statuses: [conditionId(key, direction)],
    flags: { [MODULE_ID]: { stageKey: key, stageDirection: direction, stageValue: clamped } }
  };
  if (existing) await existing.update(data);
  else await actor.createEmbeddedDocuments("ActiveEffect", [data]);
}

// Botões +/- da própria ficha: dá um passo de ±1 no estágio (-6..+6), gerenciando o efeito
// direto (não dá pra usar Actor#toggleStatusEffect pra incrementar — no dnd5e 5.3.3 esse
// método é só um liga/desliga por existência, sem nenhum conceito de "nível").
export async function stepStage(actor, key, delta) {
  const step = Math.sign(delta);
  if (!step) return;
  const current = getStages(actor)[key];
  const target = Math.max(-6, Math.min(6, current + step));
  if (target === current) return;

  await setStageEffect(actor, key, "up", target > 0 ? target : 0);
  await setStageEffect(actor, key, "down", target < 0 ? -target : 0);
}

export async function clearStages(actor) {
  for (const { key } of STAGE_STATS) {
    await setStageEffect(actor, key, "up", 0);
    await setStageEffect(actor, key, "down", 0);
  }
}

// O dnd5e RECONSTRÓI CONFIG.statusEffects inteiro (de array pra objeto por id) durante o
// próprio hook "setup" dele, a partir de CONFIG.DND5E.conditionTypes + CONFIG.DND5E.statusEffects
// — nosso hook "init" roda antes disso, então empilhar direto em CONFIG.statusEffects.push(...)
// (como se fosse um array puro do Foundry) simplesmente desaparecia quando o "setup" do dnd5e
// sobrescrevia o array inteiro logo em seguida. O jeito certo é registrar em
// CONFIG.DND5E.conditionTypes (mesmo lugar que o módulo "(pk5e)" usa) — o dnd5e lê isso
// durante o "setup" dele e monta o CONFIG.statusEffects final incluindo essas entradas.
export function registerStatusEffects() {
  for (const { key, label } of STAGE_STATS) {
    CONFIG.DND5E.conditionTypes[conditionId(key, "up")] =
      { name: `${label} ↑`, img: baseIconPath(key, "up"), pseudo: true };
    CONFIG.DND5E.conditionTypes[conditionId(key, "down")] =
      { name: `${label} ↓`, img: baseIconPath(key, "down"), pseudo: true };
  }

  // Clique no HUD do Token cria um ActiveEffect "cru" (só o que está registrado em
  // CONFIG.statusEffects — sem "changes", sem ícone por nível). "preCreateActiveEffect" é um
  // hook padrão do próprio Foundry (não específico de nenhuma versão do dnd5e): cancela essa
  // criação padrão (return false) e cria um efeito próprio completo no lugar. O handler
  // precisa ser SÍNCRONO — Hooks.call olha o valor de retorno na hora pra decidir se cancela;
  // se o handler fosse "async", o retorno seria sempre uma Promise (nunca "=== false"), e a
  // criação padrão nunca seria cancelada de verdade. Por isso o trabalho de verdade
  // (setStageEffect) roda à parte, sem o hook esperar por ele.
  Hooks.on("preCreateActiveEffect", (effect, data) => {
    if (data.flags?.[MODULE_ID]?.stageKey) return true; // já é nosso (criado por setStageEffect)
    const statusId = data.statuses?.[0];
    const info = parseConditionId(statusId);
    if (!info) return true;
    const actor = effect.parent;
    if (actor?.documentName !== "Actor") return true;

    const opposite = info.direction === "up" ? "down" : "up";
    setStageEffect(actor, info.key, opposite, 0)
      .then(() => setStageEffect(actor, info.key, info.direction, 1))
      .catch((err) => console.error(`${MODULE_ID} | Falha ao ligar ${statusId} pelo HUD do Token`, err));
    return false;
  });
}
