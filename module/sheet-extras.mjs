// Pokémon são Actors "npc" nativos do dnd5e, e o dnd5e não dá a esse tipo de Actor nem
// Inspiração nem XP acumulado com "atual/próximo nível" (isso só existe no schema do
// Actor "character"). Este arquivo injeta as duas coisas na ficha via flags próprias do
// módulo, sem mexer no Actor "npc" nativo do sistema.
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
  el.classList.toggle("pmp-active", !current);
  el.setAttribute("aria-pressed", String(!current));
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
      .pmp-sheet-panel { display: flex; align-items: center; gap: 12px; padding: 4px 8px;
        margin: 4px 0; font-size: 12px; flex-wrap: wrap; }
      .pmp-sheet-panel .pmp-inspiration { cursor: pointer; opacity: 0.35; font-size: 16px;
        line-height: 1; user-select: none; }
      .pmp-sheet-panel .pmp-inspiration.pmp-active { opacity: 1; color: #ffd700;
        text-shadow: 0 0 4px #ffd700; }
      .pmp-sheet-panel .pmp-xp-label, .pmp-sheet-panel .pmp-hd-label { opacity: 0.8; }
      .pmp-sheet-panel input.pmp-xp-input { width: 70px; }
      .pmp-sheet-panel .pmp-hd-roll { cursor: pointer; margin-left: 4px; }
      .pmp-sheet-panel .pmp-hd-roll:hover { text-decoration: underline; }
    </style>
    <span class="pmp-inspiration${inspired ? " pmp-active" : ""}" role="button"
          aria-pressed="${inspired}" title="Inspiração">★ Inspiração</span>
    <span class="pmp-xp-label">XP:
      <input type="number" class="pmp-xp-input" value="${xp}" min="0" />
      / ${next !== undefined ? formatXp(next) : "MÁX"}
    </span>
    <span class="pmp-hd-label">Dado de Vida: ${hd.value}/${hd.max} d${hd.denomination}
      <a class="pmp-hd-roll" role="button" title="Rolar Dado de Vida">🎲 Rolar</a>
    </span>
  `;

  panel.querySelector(".pmp-inspiration").addEventListener("click", (ev) =>
    onInspirationClick(actor, ev.currentTarget));
  panel.querySelector(".pmp-xp-input").addEventListener("change", (ev) =>
    onXpChange(actor, ev.currentTarget.value));
  panel.querySelector(".pmp-hd-roll").addEventListener("click", () => onRollHitDie(actor));

  return panel;
}

function injectPanel(app, htmlEl) {
  const actor = app.document ?? app.actor;
  if (!actor || actor.type !== "npc" || !actor.getFlag(MODULE_ID, "species")) return;
  if (htmlEl.querySelector(".pmp-sheet-panel")) return; // já injetado, evita duplicar em re-render

  const header = htmlEl.querySelector(".sheet-header") ?? htmlEl.querySelector("header");
  const panel = buildPanel(actor);
  if (header?.parentNode) header.insertAdjacentElement("afterend", panel);
  else htmlEl.prepend(panel);
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
}
