// Pokémon são Actors "npc" nativos do dnd5e, e o dnd5e não dá a esse tipo de Actor nem
// Inspiração nem XP acumulado com "atual/próximo nível" (isso só existe no schema do
// Actor "character"). Este arquivo injeta as duas coisas na ficha via flags próprias do
// módulo, sem mexer no Actor "npc" nativo do sistema. Também injeta, na ficha de
// "character" (Treinador), um painel com o Nível de Treinador calculado pela regra própria
// do livro (soma dos níveis da equipe) — porque o dnd5e nativo assume que "character" sobe
// de nível por XP acumulado, e a regra de Treinador deste sistema não funciona assim.
import { computeTrainerLevelInfo } from "./data/trainer-level.mjs";
import { STAGE_STATS, getStages, setStage } from "./combat/status-stages.mjs";

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

function stageRowHtml(actor) {
  const stages = getStages(actor);
  const cells = STAGE_STATS.map(({ key, label }) => {
    const value = stages[key];
    const cls = value > 0 ? "pmp-stage-pos" : value < 0 ? "pmp-stage-neg" : "";
    return `
      <span class="pmp-stage ${cls}" data-key="${key}">
        <button type="button" class="pmp-stage-btn" data-key="${key}" data-delta="-1" ${value <= -6 ? "disabled" : ""}>−</button>
        <span class="pmp-stage-label" title="${label}">${label}</span>
        <span class="pmp-stage-value">${value > 0 ? "+" : ""}${value}</span>
        <button type="button" class="pmp-stage-btn" data-key="${key}" data-delta="1" ${value >= 6 ? "disabled" : ""}>+</button>
      </span>`;
  }).join("");
  return `<div class="pmp-stage-row">${cells}</div>`;
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
      .pmp-stage-row { display: flex; gap: 6px; flex-wrap: wrap; }
      .pmp-stage { display: flex; align-items: center; gap: 3px; border: 1px solid #ccc;
        border-radius: 4px; padding: 1px 4px; }
      .pmp-stage-pos { border-color: #2b9e4f; background: rgba(43,158,79,0.12); }
      .pmp-stage-neg { border-color: #b0413e; background: rgba(176,65,62,0.12); }
      .pmp-stage-label { opacity: 0.75; font-size: 10px; }
      .pmp-stage-value { min-width: 1.4em; text-align: center; font-weight: 700; }
      .pmp-stage-btn { cursor: pointer; line-height: 1; padding: 0 3px; }
      .pmp-stage-btn:disabled { opacity: 0.3; cursor: default; }
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
      const stages = getStages(actor);
      await setStage(actor, key, stages[key] + Number(delta));
    });
  });

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
