// Pokémon são Actors "npc" nativos do dnd5e, e o dnd5e não dá a esse tipo de Actor nem
// Inspiração nem XP acumulado com "atual/próximo nível" (isso só existe no schema do
// Actor "character"). Este arquivo injeta as duas coisas na ficha via flags próprias do
// módulo, sem mexer no Actor "npc" nativo do sistema. Também injeta, na ficha de
// "character" (Treinador), um painel com o Nível de Treinador calculado pela regra própria
// do livro (soma dos níveis da equipe) — porque o dnd5e nativo assume que "character" sobe
// de nível por XP acumulado, e a regra de Treinador deste sistema não funciona assim.
import { computeTrainerLevelInfo } from "./data/trainer-level.mjs";
import { STAGE_STATS, getStages, stepStage, clearStages } from "./combat/status-stages.mjs";
import { TYPE_LABELS } from "./combat/type-chart.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";

// Tabela de XP necessário por nível (Livro de Regras, pág. 38 — "Experiência do Pokémon").
const XP_TABLE = {
  2: 200, 3: 800, 4: 2000, 5: 6000, 6: 12000, 7: 20000, 8: 30000, 9: 44000, 10: 62000,
  11: 82000, 12: 104000, 13: 128000, 14: 158000, 15: 194000, 16: 234000, 17: 278000,
  18: 326000, 19: 382000, 20: 450000
};

function pokemonLevel(actor) {
  const classItem = actor.items.find((i) => i.type === "class");
  return classItem?.system?.levels ?? 1;
}

function formatXp(n) {
  return n.toLocaleString("pt-BR");
}

async function onInspirationClick(actor, el) {
  const current = actor.getFlag(MODULE_ID, "inspiration") ?? false;
  await actor.setFlag(MODULE_ID, "inspiration", !current);
  // relê a flag em vez de confiar no !current calculado antes do await — se o re-render
  // automático da ficha reconstruir o painel entre o clique e aqui, este "el" antigo fica
  // órfão; reler garante que o próximo clique sempre parta do valor realmente salvo.
  const updated = actor.getFlag(MODULE_ID, "inspiration") ?? false;
  el.classList.toggle("pmp-active", updated);
  el.setAttribute("aria-pressed", String(updated));
}

async function onXpChange(actor, value) {
  const n = Math.max(0, Number(value) || 0);
  await actor.setFlag(MODULE_ID, "xp", n);
}

// A ficha de NPC do dnd5e não mostra botão de Dado de Vida (isso normalmente só aparece
// na ficha de Personagem), mas actor.rollHitDie() já funciona pra NPC nativamente — o
// sistema deriva o dado (system.attributes.hd.denomination) da "formula" de PV que o
// conversor grava (ex. "d6"), e o total de dados (hd.max) soma os níveis da classe
// "<Espécie> Level" automaticamente. Só faltava o botão pra chamar o método existente.
async function onRollHitDie(actor) {
  if (!actor.system.attributes.hd.value) {
    ui.notifications.warn(`${actor.name} não tem Dados de Vida disponíveis.`);
    return;
  }
  await actor.rollHitDie();
}

// Ícone de tipo do próprio Pokémon (mesmo SVG usado no dropdown de tipo de dano dos Moves,
// ver combat/type-chart.mjs) — mostrado no topo do painel, ao lado de XP/Inspiração, pra dar
// uma identificação visual rápida do(s) tipo(s) sem precisar abrir a Pokédex.
function typeBadgeHtml(actor) {
  const types = actor.getFlag(MODULE_ID, "species")?.types;
  if (!types?.type1) return "";
  const chip = (t) => `
    <span class="pmp-type-chip">
      <img src="modules/${MODULE_ID}/assets/types/${t}.svg" alt="${TYPE_LABELS[t] ?? t}" />
      ${TYPE_LABELS[t] ?? t}
    </span>`;
  return `<span class="pmp-type-badges">${chip(types.type1)}${types.type2 ? chip(types.type2) : ""}</span>`;
}

function stageRowHtml(actor) {
  const stages = getStages(actor);
  const cells = STAGE_STATS.map(({ key, label }) => {
    const value = stages[key];
    const cls = value > 0 ? "pmp-stage-pos" : value < 0 ? "pmp-stage-neg" : "";
    // <a>, não <button>: a ficha do dnd5e desabilita todo <button>/<input>/<select> dentro
    // dela quando está no modo "trancado" (um <fieldset disabled> nativo do HTML, que o CSS
    // não consegue driblar) — <a role="button"> não é um controle de formulário de verdade,
    // então continua clicável mesmo com a ficha trancada (mesmo motivo pelo qual Inspiração
    // e Rolar Dado de Vida, logo acima, já usavam <span>/<a> em vez de <button>). Reforçado
    // com "pointer-events: auto !important" no CSS abaixo — se o "trancado" algum dia passar
    // a bloquear cliques também por CSS (não só pelo <fieldset disabled> nativo), o !important
    // sobrepõe isso pra esses elementos específicos.
    const minusDisabled = value <= -6 ? "pmp-stage-btn-disabled" : "";
    const plusDisabled = value >= 6 ? "pmp-stage-btn-disabled" : "";
    return `
      <span class="pmp-stage ${cls}" data-key="${key}">
        <a role="button" class="pmp-stage-btn ${minusDisabled}" data-key="${key}" data-delta="-1">−</a>
        <span class="pmp-stage-label" title="${label}">${label}</span>
        <span class="pmp-stage-value">${value > 0 ? "+" : ""}${value}</span>
        <a role="button" class="pmp-stage-btn ${plusDisabled}" data-key="${key}" data-delta="1">+</a>
      </span>`;
  }).join("");
  const anyStage = Object.values(stages).some((v) => v !== 0);
  return `
    <div class="pmp-stage-row">
      ${cells}
      <a role="button" class="pmp-stage-reset ${anyStage ? "" : "pmp-stage-btn-disabled"}"
         title="Resetar todas as Mudanças de Status">↺ Resetar Estágios</a>
    </div>`;
}

function buildPanel(actor) {
  const level = pokemonLevel(actor);
  const current = XP_TABLE[level] ?? 0;
  const next = XP_TABLE[level + 1];
  const inspired = actor.getFlag(MODULE_ID, "inspiration") ?? false;
  const xp = actor.getFlag(MODULE_ID, "xp") ?? current;
  const hd = actor.system.attributes.hd;

  const panel = document.createElement("div");
  panel.className = "pmp-sheet-panel";
  panel.innerHTML = `
    <style>
      .pmp-sheet-panel { display: flex; flex-direction: column; gap: 4px; padding: 4px 8px;
        margin: 4px 0; font-size: 12px; }
      .pmp-sheet-panel .pmp-top-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
      .pmp-sheet-panel .pmp-inspiration { cursor: pointer; opacity: 0.35; font-size: 16px;
        line-height: 1; user-select: none; }
      .pmp-sheet-panel .pmp-inspiration.pmp-active { opacity: 1; color: #ffd700;
        text-shadow: 0 0 4px #ffd700; }
      .pmp-sheet-panel .pmp-xp-label, .pmp-sheet-panel .pmp-hd-label { opacity: 0.8; }
      .pmp-sheet-panel input.pmp-xp-input { width: 70px; }
      .pmp-sheet-panel .pmp-hd-roll { cursor: pointer; margin-left: 4px; }
      .pmp-sheet-panel .pmp-hd-roll:hover { text-decoration: underline; }
      .pmp-type-badges { display: flex; gap: 4px; }
      .pmp-type-chip { display: inline-flex; align-items: center; gap: 3px; border: 1px solid #999;
        border-radius: 10px; padding: 1px 7px 1px 4px; font-size: 10px; opacity: 0.9; }
      .pmp-type-chip img { width: 12px; height: 12px; }
      .pmp-stage-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
      .pmp-stage { display: flex; align-items: center; gap: 3px; border: 1px solid #ccc;
        border-radius: 4px; padding: 1px 4px; }
      .pmp-stage-pos { border-color: #2b9e4f; background: rgba(43,158,79,0.12); }
      .pmp-stage-neg { border-color: #b0413e; background: rgba(176,65,62,0.12); }
      .pmp-stage-label { opacity: 0.75; font-size: 10px; }
      .pmp-stage-value { min-width: 1.4em; text-align: center; font-weight: 700; }
      .pmp-stage-reset { cursor: pointer; opacity: 0.75; font-size: 11px; margin-left: auto;
        white-space: nowrap; }
      .pmp-stage-reset:hover { text-decoration: underline; }
      /* !important pra garantir clique mesmo se a ficha "trancada" algum dia bloquear por CSS
         em vez de só pelo <fieldset disabled> nativo (ver comentário em stageRowHtml). A regra
         de -disabled vem DEPOIS no arquivo, então continua vencendo onde as duas classes coexistem. */
      .pmp-inspiration, .pmp-hd-roll, .pmp-stage-btn, .pmp-stage-reset { pointer-events: auto !important; }
      .pmp-stage-btn { cursor: pointer; line-height: 1; padding: 0 3px; }
      .pmp-stage-btn-disabled { opacity: 0.3; cursor: default; pointer-events: none !important; }
    </style>
    <div class="pmp-top-row">
      <span class="pmp-inspiration${inspired ? " pmp-active" : ""}" role="button"
            aria-pressed="${inspired}" title="Inspiração">★ Inspiração</span>
      <span class="pmp-xp-label">XP:
        <input type="number" class="pmp-xp-input" value="${xp}" min="0" />
        / ${next !== undefined ? formatXp(next) : "MÁX"}
      </span>
      <span class="pmp-hd-label">Dado de Vida: ${hd.value}/${hd.max} d${hd.denomination}
        <a class="pmp-hd-roll" role="button" title="Rolar Dado de Vida">🎲 Rolar</a>
      </span>
      ${typeBadgeHtml(actor)}
    </div>
    ${stageRowHtml(actor)}
  `;

  panel.querySelector(".pmp-inspiration").addEventListener("click", (ev) =>
    onInspirationClick(actor, ev.currentTarget));
  panel.querySelector(".pmp-xp-input").addEventListener("change", (ev) =>
    onXpChange(actor, ev.currentTarget.value));
  panel.querySelector(".pmp-hd-roll").addEventListener("click", () => onRollHitDie(actor));
  panel.querySelectorAll(".pmp-stage-btn").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      const { key, delta } = ev.currentTarget.dataset;
      await stepStage(actor, key, Number(delta));
    });
  });
  panel.querySelector(".pmp-stage-reset").addEventListener("click", () => clearStages(actor));

  return panel;
}

function buildTrainerPanel(actor) {
  const info = computeTrainerLevelInfo(actor);
  const mismatch = info.indicatedLevel !== info.currentLevel;

  const panel = document.createElement("div");
  panel.className = "pmp-sheet-panel pmp-trainer-panel";
  panel.innerHTML = `
    <style>
      .pmp-trainer-panel { display: flex; align-items: center; gap: 12px; padding: 4px 8px;
        margin: 4px 0; font-size: 12px; flex-wrap: wrap; }
      .pmp-trainer-panel .pmp-trainer-label { opacity: 0.8; }
      .pmp-trainer-panel .pmp-trainer-mismatch { font-weight: 700; color: #b45309; }
    </style>
    <span class="pmp-trainer-label">Nível de Treinador: <strong>${info.currentLevel}º</strong></span>
    <span class="pmp-trainer-label">Pokéslots: ${info.slots}</span>
    <span class="pmp-trainer-label" title="${info.counted.join(" + ") || "—"}">
      Soma da equipe: ${info.sum}
    </span>
    <span class="pmp-trainer-label ${mismatch ? "pmp-trainer-mismatch" : ""}">
      ${mismatch
        ? `⚠️ Tabela indica nível ${info.indicatedLevel}º — atualize o nível do Treinador`
        : info.next ? `Próximo nível (${info.next.level}º) em: soma ${info.next.sum}` : "Nível máximo"}
    </span>
  `;
  return panel;
}

function injectPanel(app, htmlEl) {
  const actor = app.document ?? app.actor;
  if (!actor) return;

  // Remove qualquer painel antigo antes de reconstruir: como a ficha do dnd5e usa
  // renderização parcial por partes (PARTS), nosso painel injetado fica fora desse
  // ciclo e pode sobreviver "congelado" entre re-renders se só checarmos e pularmos —
  // reconstruir do zero sempre garante que ele reflita o estado atual da flag.
  htmlEl.querySelectorAll(".pmp-sheet-panel").forEach((el) => el.remove());

  let panel;
  if (actor.type === "npc" && actor.getFlag(MODULE_ID, "species")) {
    panel = buildPanel(actor);
  } else if (actor.type === "character") {
    panel = buildTrainerPanel(actor);
  } else {
    return;
  }

  const header = htmlEl.querySelector(".sheet-header") ?? htmlEl.querySelector("header");
  if (header?.parentNode) header.insertAdjacentElement("afterend", panel);
  else htmlEl.prepend(panel);
}

function refreshOpenSheet(actor) {
  // Subir de nível mexe no item de classe embutido (Advancement Manager), não no Actor
  // em si — isso nem sempre dispara um novo render a tempo de atualizar nosso painel
  // (nível, PV/Dado de Vida dependem do item de classe). Forçar o render aqui garante que
  // Inspiração/XP/Dado de Vida (Pokémon) e Nível de Treinador acompanhem qualquer subida.
  const relevant = (actor?.type === "npc" && actor.getFlag(MODULE_ID, "species"))
    || actor?.type === "character";
  if (relevant && actor.sheet?.rendered) actor.sheet.render(false);
}

// Um Pokémon subindo de nível muda a "soma da equipe" de qualquer Treinador que o tenha
// na mesma pasta — não só o próprio Actor do Pokémon. Sem isso, o painel de Nível de
// Treinador ficaria desatualizado até a próxima ação que force um re-render manual.
function refreshTrainerSheetsInSameFolder(pokemonActor) {
  if (pokemonActor?.type !== "npc" || !pokemonActor.getFlag(MODULE_ID, "species")) return;
  const folderId = pokemonActor.folder?.id ?? null;
  for (const actor of game.actors) {
    if (actor.type === "character" && (actor.folder?.id ?? null) === folderId && actor.sheet?.rendered) {
      actor.sheet.render(false);
    }
  }
}

export function registerSheetExtras() {
  Hooks.on("renderNPCActorSheet", (app, htmlEl) => {
    try {
      const root = htmlEl instanceof HTMLElement ? htmlEl : htmlEl?.[0];
      if (root) injectPanel(app, root);
    } catch (err) {
      console.error(`${MODULE_ID} | Falha ao injetar painel de Inspiração/XP`, err);
    }
  });

  Hooks.on("renderCharacterActorSheet", (app, htmlEl) => {
    try {
      const root = htmlEl instanceof HTMLElement ? htmlEl : htmlEl?.[0];
      if (root) injectPanel(app, root);
    } catch (err) {
      console.error(`${MODULE_ID} | Falha ao injetar painel de Nível de Treinador`, err);
    }
  });

  // Item de classe (nível/PV) e outros itens (Moves/Talentos ganhos ao subir de nível)
  // vivem embutidos no Actor — qualquer mudança neles pode afetar o painel.
  const onEmbeddedItemChange = (item) => {
    refreshOpenSheet(item.parent);
    refreshTrainerSheetsInSameFolder(item.parent);
  };
  Hooks.on("updateItem", onEmbeddedItemChange);
  Hooks.on("createItem", onEmbeddedItemChange);
  Hooks.on("deleteItem", onEmbeddedItemChange);
  Hooks.on("updateActor", refreshOpenSheet);
}
