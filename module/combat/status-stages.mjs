// Mudanças de Status (Livro de Regras, pág. 71): 8 estágios acumuláveis de -6 a +6.
//
// HISTÓRICO — pra não cair no mesmo buraco uma quarta vez:
// - v1.19 tentava interceptar o clique no HUD do Token via um hook "applyTokenStatusEffect"
//   que não existe em nenhuma versão real do dnd5e — nunca disparava.
// - v1.20/v1.21 tentaram usar um mecanismo de "condição com nível" (CONFIG.DND5E.
//   conditionTypes[id].levels + ConditionData/_applyDelta, do jeito que a Exaustão parece
//   funcionar) — só que essa pesquisa foi feita direto no branch de DESENVOLVIMENTO do dnd5e
//   no GitHub, que fica na FRENTE do que está de fato lançado. Conferido depois contra a tag
//   real "release-5.3.3" (a versão que este mundo roda de verdade — "system:dnd5e(5.3.3)"
//   no erro que apareceu uma vez): esse mecanismo genérico simplesmente NÃO EXISTE nela.
// - v1.22 passou a criar o efeito na mão (sem depender de "levels"), mas ainda tentava
//   cancelar a criação PADRÃO do Foundry via hook "preCreateActiveEffect" pra substituir por
//   uma própria — dependia de detalhes internos de COMO Actor#toggleStatusEffect cria esse
//   efeito por baixo (código fechado, não dá pra conferir contra nenhum repositório), e
//   continuou não funcionando de forma confiável.
//
// Desenho atual (v1.23): não depende mais de NADA do caminho padrão do Foundry pro clique no
// HUD. Cada direção (Ataque ↑ / Ataque ↓ etc.) é registrada em CONFIG.DND5E.conditionTypes só
// pra aparecer com o ícone certo na grade — mas o clique em si é interceptado direto no DOM
// (hook "renderTokenHUD", padrão e estável em qualquer versão do Foundry), com
// stopPropagation pra garantir que o toggle padrão do Foundry nunca chega a rodar, e o
// próprio módulo cuida de tudo via createEmbeddedDocuments/update/delete na mão — a base mais
// simples e estável que existe no sistema de documentos do Foundry, sem nenhuma suposição
// sobre comportamento interno de toggleStatusEffect ou de hooks de criação. Um clique liga a
// direção em magnitude 1 (igual Envenenado/Agarrado), outro desliga. Estágios 2-6 só dá pra
// alcançar pelos botões +/- da própria ficha, que gerenciam esse mesmo efeito do mesmo jeito.
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

// Livro de Regras, tabela "Efeito de 1 estágio" (todas as chaves conferidas no dnd5e 5.3.3):
// - Precisão: +1 nas rolagens de ataque e na CD dos Moves. As Activities de ataque dos Moves
//   são "weapon" corpo a corpo/à distância (bonuses.mwak/rwak.attack), e a CD de um Move vem
//   de abilities.<x>.dc, que já soma bonuses.spell.dc (templates/common.mjs).
// - Evasão: +1 na CA e nos testes de resistência. ac.bonus só conta porque a Pokédex usa
//   ac.calc "natural" — no modo "flat" o dnd5e ignora qualquer bônus de CA.
// - Velocidade: +5 pés em todos os deslocamentos e +prof na iniciativa. movement.bonus só é
//   somado aos deslocamentos maiores que zero (prepareMovement), então um Pokémon sem nado
//   ou voo não "ganha" esses deslocamentos — somar direto em movement.<tipo> fazia isso.
// - Margem de Crítico: não tem chave de Active Effect que valha para Moves (Items "feat" não
//   leem weaponCriticalThreshold), então é aplicada no hook dnd5e.preRollAttackV2 abaixo.
// - Ataque/Atq. Especial ficam por conta do jogador somar na hora de rolar (Moves "limpos",
//   decisão da v1.23.0), e Defesa/Def. Especial reduzem dano por corpo a corpo/à distância,
//   distinção que a aplicação de dano do dnd5e não oferece — só registro visível no painel.
const SPEED_STEP = { ft: 5, m: 1.5 };

function changesFor(key, value, actor = null) {
  const add = (k, v) => (v ? [{ key: k, mode: 2, value: String(v), priority: null }] : []);
  switch (key) {
    case "acc":
      return [
        ...add("system.bonuses.mwak.attack", value),
        ...add("system.bonuses.rwak.attack", value),
        ...add("system.bonuses.spell.dc", value)
      ];
    case "eva":
      return [...add("system.attributes.ac.bonus", value), ...add("system.bonuses.abilities.save", value)];
    case "spe": {
      const units = actor?.system?.attributes?.movement?.units ?? "ft";
      return [
        ...add("system.attributes.init.bonus", `${value} * @prof`),
        ...add("system.attributes.movement.bonus", value * (SPEED_STEP[units] ?? 5))
      ];
    }
    default:
      return []; // atk, spa, def, spd: registro visível; crit: hook de ataque
  }
}

/**
 * Hook "dnd5e.preRollAttackV2" (BasicRoll.buildConfigure, release-5.3.3): a configuração da
 * rolagem já chega com rolls[0].options.criticalSuccess preenchido pela Activity e com a
 * própria Activity em config.subject. Cada estágio de Margem de Crítico baixa o número
 * necessário em 3 (20 → 17 → 14...), nunca abaixo de 2. Hooks.call síncrono: só mexe na
 * configuração, não cancela nada.
 */
function onPreRollAttack(config) {
  const actor = config?.subject?.actor;
  if (!actor) return;
  const crit = getStages(actor).crit;
  if (crit <= 0) return;
  for (const roll of config.rolls ?? []) {
    roll.options ??= {};
    const base = roll.options.criticalSuccess ?? 20;
    roll.options.criticalSuccess = Math.max(2, base - 3 * crit);
  }
}

/** Recalcula os "changes" dos estágios já ativos no Actor (usado pela migração de versão). */
export async function refreshStageEffects(actor) {
  const updates = [];
  for (const effect of actor.effects) {
    const key = effect.getFlag(MODULE_ID, "stageKey");
    const direction = effect.getFlag(MODULE_ID, "stageDirection");
    const value = effect.getFlag(MODULE_ID, "stageValue");
    if (!key || !direction || !value) continue;
    const changes = changesFor(key, direction === "up" ? value : -value, actor);
    if (JSON.stringify(changes) !== JSON.stringify(effect.changes.map((c) => ({ ...c })))) {
      updates.push({ _id: effect.id, changes });
    }
  }
  if (updates.length) await actor.updateEmbeddedDocuments("ActiveEffect", updates);
  return updates.length;
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
    changes: changesFor(key, signed, actor),
    disabled: false,
    transfer: false,
    statuses: [conditionId(key, direction)],
    flags: { [MODULE_ID]: { stageKey: key, stageDirection: direction, stageValue: clamped } }
  };
  if (existing) await existing.update(data);
  else await actor.createEmbeddedDocuments("ActiveEffect", [data]);

  // Criar/atualizar/apagar um ActiveEffect no Actor nem sempre dispara sozinho um novo
  // render da ficha a tempo (mesmo motivo pelo qual XP/Nível de Treinador em sheet-extras.mjs
  // já precisavam de um refresh forçado) — sem isso, os botões +/- da ficha pareciam "não
  // fazer nada": o efeito era criado certinho por baixo, só a ficha aberta continuava
  // mostrando o valor antigo. O HUD do Token tem o mesmo problema pro ícone "selecionado".
  if (actor.sheet?.rendered) actor.sheet.render(false);
  const hud = canvas?.hud?.token;
  if (hud?.rendered && hud.object?.actor?.id === actor.id) hud.render(false);
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

async function toggleFromHud(actor, statusId) {
  const info = parseConditionId(statusId);
  if (!info) return;
  if (stageValue(actor, info.key, info.direction) > 0) {
    await setStageEffect(actor, info.key, info.direction, 0);
    return;
  }
  const opposite = info.direction === "up" ? "down" : "up";
  await setStageEffect(actor, info.key, opposite, 0);
  await setStageEffect(actor, info.key, info.direction, 1);
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

  Hooks.on("dnd5e.preRollAttackV2", onPreRollAttack);

  // Clique no HUD do Token cria um ActiveEffect "cru" só com o que está registrado em
  // CONFIG.statusEffects (sem "changes", sem ícone certo) — usar Actor#toggleStatusEffect ou
  // tentar cancelar isso via hook (preCreateActiveEffect) depende de detalhes internos do
  // Foundry/dnd5e que já se mostraram version-frágeis demais nesse projeto (duas rodadas de
  // bugs). Em vez disso, intercepta o clique direto no DOM da grade do HUD (renderTokenHUD é
  // um hook padrão e simples do próprio Foundry) e cuida do toggle inteiro na mão, sem passar
  // pelo caminho padrão do Foundry em nenhum momento — só depende de criar/apagar
  // ActiveEffect, que é a base mais estável que existe no sistema de documentos do Foundry.
  Hooks.on("renderTokenHUD", (hud, html) => {
    const root = html instanceof HTMLElement ? html : html?.[0];
    const actor = hud.object?.actor ?? hud.token?.actor;
    if (!root || !actor) return;

    for (const el of root.querySelectorAll(`[data-status-id^="${MODULE_ID}-"]`)) {
      const statusId = el.dataset.statusId;
      // capture (terceiro argumento "true"): roda ANTES do listener delegado que o Foundry
      // liga na grade inteira, então stopPropagation aqui impede o toggle padrão dele de
      // sequer começar — não é uma corrida entre os dois, o nosso sempre chega primeiro.
      el.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        toggleFromHud(actor, statusId)
          .catch((err) => console.error(`${MODULE_ID} | Falha ao alternar ${statusId} pelo HUD do Token`, err));
      }, true);
      el.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        event.stopPropagation();
      }, true);
    }
  });
}
