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

function changesFor(key, value) {
  const add = (k, v) => (v ? [{ key: k, mode: 2, value: String(v), priority: null }] : []);
  switch (key) {
    // Ataque/Atq. Especial não entram aqui de propósito: os Moves foram deixados "limpos"
    // (só dado + modificador, sem fórmula embutida) pro jogador somar o bônus de estágio na
    // hora de rolar, do jeito que preferir — igual Defesa/Def. Especial/Marg. Crítico, só
    // registro visível no painel, sem automação mecânica.
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
