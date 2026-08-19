// Ficha de Item para Ovos Pokémon (type "loot" + flags["pokemon-mundo-perfeito"].egg).
// Não usa Handlebars (o módulo não registra templates em nenhum outro lugar) — segue o
// mesmo estilo de sheet-extras.mjs: HTML cru + addEventListener manual em _onRender, em
// vez do sistema declarativo `actions` do ApplicationV2, para ficar consistente com o
// único padrão já testado em produção neste módulo.
import {
  SR_OPTIONS, INCUBATORS, HISTORY_TYPES, EGG_STATES,
  resolveRequirement, defaultRequirementForSr, buildIncubationFormula, deriveState,
  canHatch, makeHistoryEntry
} from "../data/egg-rules.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";

function getEgg(item) {
  return foundry.utils.mergeObject(
    { species: "", shiny: false, sr: "1", requirementCustom: null, progress: 0, incubator: null,
      revealed: false, hatched: false, history: [], ownerUserId: null },
    item.getFlag(MODULE_ID, "egg") ?? {},
    { inplace: false }
  );
}

async function setEgg(item, egg) {
  await item.setFlag(MODULE_ID, "egg", egg);
}

async function appendHistory(item, egg, type, delta, note = "") {
  egg.progress = Math.max(0, egg.progress + delta);
  egg.history = [...egg.history, makeHistoryEntry(type, delta, egg.progress, note)];
  await setEgg(item, egg);
  return egg;
}

async function rollIncubation(item, egg, { asGM }) {
  const formula = buildIncubationFormula(egg.incubator);
  const roll = new Roll(formula);
  await roll.evaluate();
  await roll.toMessage({
    speaker: ChatMessage.getSpeaker({ actor: item.parent }),
    flavor: `🎲 Incubação — ${item.parent?.name ?? "Ovo"}`
  });
  const type = asGM ? "gmRoll" : "playerRoll";
  await appendHistory(item, egg, type, roll.total, `Rolagem: ${formula}`);
}

function progressBar(progress, requirement) {
  const pct = requirement > 0 ? Math.min(100, Math.round((progress / requirement) * 100)) : 0;
  return `
    <div class="pmp-egg-bar">
      <div class="pmp-egg-bar-fill" style="width:${pct}%"></div>
      <span class="pmp-egg-bar-label">${progress} / ${requirement}</span>
    </div>`;
}

function stateBadge(stateKey) {
  const label = EGG_STATES[stateKey]?.label ?? stateKey;
  return `<span class="pmp-egg-badge pmp-egg-badge--${stateKey}">${label}</span>`;
}

function historyList(history) {
  if (!history.length) return `<p class="pmp-egg-muted">Nenhum registro ainda.</p>`;
  const rows = [...history].reverse().map((h) => {
    const meta = HISTORY_TYPES[h.type] ?? { icon: "•", label: h.type };
    const sign = h.delta >= 0 ? "+" : "";
    const when = new Date(h.ts).toLocaleString("pt-BR");
    return `
      <li class="pmp-egg-history-row">
        <span class="pmp-egg-history-icon">${meta.icon}</span>
        <span class="pmp-egg-history-body">
          <strong>${meta.label}</strong>${h.note ? ` — ${h.note}` : ""}
          <small>${when}</small>
        </span>
        <span class="pmp-egg-history-delta">${sign}${h.delta} <em>(${h.total})</em></span>
      </li>`;
  }).join("");
  return `<ul class="pmp-egg-history">${rows}</ul>`;
}

function styleBlock() {
  return `
    <style>
      .pmp-egg-sheet { font-family: var(--font-primary, sans-serif); padding: 0.5rem 0.75rem; }
      .pmp-egg-sheet h3 { margin: 0.75rem 0 0.35rem; font-size: 1rem; border-bottom: 1px solid #ccc; }
      .pmp-egg-summary { display: grid; grid-template-columns: 1fr 1fr; gap: 0.15rem 1rem; font-size: 0.85rem; margin-bottom: 0.5rem; }
      .pmp-egg-summary div { display: flex; justify-content: space-between; gap: 0.5rem; border-bottom: 1px dotted #ddd; }
      .pmp-egg-summary label { opacity: 0.7; }
      .pmp-egg-bar { position: relative; height: 22px; background: #e4e4e4; border: 1px solid #999; border-radius: 4px; overflow: hidden; margin: 0.35rem 0; }
      .pmp-egg-bar-fill { height: 100%; background: linear-gradient(90deg, #6b8f47, #9bc06a); }
      .pmp-egg-bar-label { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.8rem; text-shadow: 0 0 2px #fff; }
      .pmp-egg-badge { display: inline-block; padding: 0.1rem 0.6rem; border-radius: 999px; font-size: 0.8rem; color: #fff; background: #777; }
      .pmp-egg-badge--novo { background: #888; }
      .pmp-egg-badge--incubando { background: #d19a2b; }
      .pmp-egg-badge--pronto { background: #2b9e4f; }
      .pmp-egg-badge--chocado { background: #4a6fd1; }
      .pmp-egg-row { display: flex; align-items: center; gap: 0.4rem; margin: 0.3rem 0; flex-wrap: wrap; }
      .pmp-egg-row label { min-width: 8.5rem; font-weight: 600; font-size: 0.85rem; }
      .pmp-egg-actions { display: flex; gap: 0.4rem; flex-wrap: wrap; margin: 0.5rem 0; }
      .pmp-egg-actions button { flex: 1 1 auto; }
      .pmp-egg-muted { opacity: 0.6; font-size: 0.85rem; }
      .pmp-egg-history { list-style: none; margin: 0; padding: 0; max-height: 220px; overflow-y: auto; }
      .pmp-egg-history-row { display: flex; align-items: center; gap: 0.5rem; padding: 0.25rem 0; border-bottom: 1px solid #eee; font-size: 0.8rem; }
      .pmp-egg-history-icon { font-size: 1.1rem; }
      .pmp-egg-history-body { flex: 1; }
      .pmp-egg-history-body small { display: block; opacity: 0.6; }
      .pmp-egg-history-delta { font-weight: 700; white-space: nowrap; }
      .pmp-egg-player-title { font-size: 1.2rem; font-weight: 700; margin-bottom: 0.25rem; }
    </style>`;
}

function renderGmView(item, egg) {
  const requirement = resolveRequirement(egg);
  const requirementDefault = defaultRequirementForSr(egg.sr);
  const state = deriveState(egg);
  const ownerName = game.users.get(egg.ownerUserId)?.name ?? item.parent?.name ?? "—";
  const srOptions = SR_OPTIONS.map((sr) =>
    `<option value="${sr}" ${sr === egg.sr ? "selected" : ""}>${sr}</option>`).join("");
  const incubatorOptions = `<option value="" ${!egg.incubator ? "selected" : ""}>Nenhuma</option>` +
    Object.values(INCUBATORS).map((i) =>
      `<option value="${i.key}" ${i.key === egg.incubator ? "selected" : ""}>${i.label}</option>`).join("");

  return `
    ${styleBlock()}
    <div class="pmp-egg-sheet">
      <h3>Resumo</h3>
      <div class="pmp-egg-summary">
        <div><label>ID do ovo</label><span>${item.id}</span></div>
        <div><label>Jogador</label><span>${ownerName}</span></div>
        <div><label>Espécie</label><span>${egg.species || "—"}</span></div>
        <div><label>Shiny</label><span>${egg.shiny ? "Sim ✨" : "Não"}</span></div>
        <div><label>SR</label><span>${egg.sr}</span></div>
        <div><label>Requisito padrão (SR)</label><span>${requirementDefault ?? "—"}</span></div>
        <div><label>Requisito personalizado</label><span>${Number.isFinite(egg.requirementCustom) ? egg.requirementCustom : "—"}</span></div>
        <div><label>Requisito atual</label><span>${requirement}</span></div>
        <div><label>Incubadora</label><span>${egg.incubator ? INCUBATORS[egg.incubator].label : "Nenhuma"}</span></div>
        <div><label>Revelado ao jogador</label><span>${egg.revealed || egg.hatched ? "Sim" : "Não"}</span></div>
      </div>

      ${progressBar(egg.progress, requirement)}
      <div class="pmp-egg-row"><label>Estado</label>${stateBadge(state)}</div>

      <h3>Editar configuração</h3>
      <div class="pmp-egg-row"><label>Espécie</label><input type="text" data-field="species" value="${egg.species}" /></div>
      <div class="pmp-egg-row"><label>Shiny</label><input type="checkbox" data-field="shiny" ${egg.shiny ? "checked" : ""} /></div>
      <div class="pmp-egg-row"><label>SR</label><select data-field="sr">${srOptions}</select></div>
      <div class="pmp-egg-row">
        <label>Requisito personalizado</label>
        <input type="number" data-field="requirementCustom" value="${Number.isFinite(egg.requirementCustom) ? egg.requirementCustom : ""}" placeholder="usar padrão da tabela" />
        <button type="button" data-action="reset-requirement">Restaurar padrão</button>
      </div>
      <div class="pmp-egg-row"><label>Incubadora</label><select data-field="incubator">${incubatorOptions}</select></div>
      <div class="pmp-egg-actions"><button type="button" data-action="save-config">💾 Salvar alterações</button></div>

      <h3>Progresso manual</h3>
      <div class="pmp-egg-row">
        <label>Ajuste (+/-)</label>
        <input type="number" data-field="delta" value="0" style="width:5rem" />
        <input type="text" data-field="note" placeholder="motivo (opcional)" style="flex:1" />
        <button type="button" data-action="adjust-progress">Aplicar</button>
      </div>

      <div class="pmp-egg-actions">
        <button type="button" data-action="roll-gm">🎲 Rolar Incubação (Mestre)</button>
        <button type="button" data-action="reveal" ${egg.revealed || egg.hatched ? "disabled" : ""}>👁️ Revelar informações</button>
        <button type="button" data-action="hatch" ${canHatch(egg) ? "" : "disabled"}>🥚✨ Chocar Ovo</button>
      </div>

      <h3>Histórico de Incubação</h3>
      ${historyList(egg.history)}
    </div>`;
}

function renderPlayerView(item, egg) {
  const requirement = resolveRequirement(egg);
  const state = deriveState(egg);
  const showSecrets = egg.revealed || egg.hatched;

  return `
    ${styleBlock()}
    <div class="pmp-egg-sheet">
      <div class="pmp-egg-player-title">
        ${showSecrets ? `🥚 ${egg.species}${egg.shiny ? " ✨" : ""}` : "🥚 Ovo Pokémon"}
      </div>
      <div class="pmp-egg-row"><label>Incubadora</label><span>${egg.incubator ? INCUBATORS[egg.incubator].label : "Nenhuma"}</span></div>
      ${progressBar(egg.progress, requirement)}
      <div class="pmp-egg-row"><label>Estado</label>${stateBadge(state)}</div>
      ${showSecrets ? `<div class="pmp-egg-row"><label>SR</label><span>${egg.sr}</span></div>` : ""}

      <div class="pmp-egg-actions">
        <button type="button" data-action="roll-player" ${egg.hatched ? "disabled" : ""}>🎲 Incubar</button>
        <button type="button" data-action="hatch" ${canHatch(egg) ? "" : "disabled"}>🥚✨ Chocar Ovo</button>
      </div>
    </div>`;
}

export class EggItemSheet extends foundry.applications.api.DocumentSheetV2 {
  static DEFAULT_OPTIONS = {
    classes: ["pmp-egg-sheet-app"],
    window: { icon: "fa-solid fa-egg", resizable: true },
    position: { width: 480, height: "auto" }
  };

  get item() {
    return this.document;
  }

  get title() {
    const egg = getEgg(this.item);
    if (game.user.isGM) {
      return egg.species ? `Ovo — ${egg.species}${egg.shiny ? " ✨" : ""}` : "Ovo Pokémon (vazio)";
    }
    return egg.revealed || egg.hatched ? `Ovo — ${egg.species}` : "Ovo Pokémon";
  }

  async _renderHTML(_context, _options) {
    const egg = getEgg(this.item);
    return game.user.isGM ? renderGmView(this.item, egg) : renderPlayerView(this.item, egg);
  }

  _replaceHTML(result, content) {
    content.innerHTML = result;
    this._attachListeners(content);
  }

  _attachListeners(root) {
    const item = this.item;
    const readField = (name) => root.querySelector(`[data-field="${name}"]`);

    root.querySelector('[data-action="save-config"]')?.addEventListener("click", async () => {
      const egg = getEgg(item);
      const reqRaw = readField("requirementCustom").value;
      egg.species = readField("species").value.trim();
      egg.shiny = readField("shiny").checked;
      egg.sr = readField("sr").value;
      egg.requirementCustom = reqRaw === "" ? null : Number(reqRaw);
      egg.incubator = readField("incubator").value || null;
      await setEgg(item, egg);
      this.render();
    });

    root.querySelector('[data-action="reset-requirement"]')?.addEventListener("click", async () => {
      readField("requirementCustom").value = "";
    });

    root.querySelector('[data-action="adjust-progress"]')?.addEventListener("click", async () => {
      const egg = getEgg(item);
      const delta = Number(readField("delta").value) || 0;
      if (delta === 0) return;
      const note = readField("note").value.trim();
      const type = delta >= 0 ? "gmBonus" : "gmCorrection";
      await appendHistory(item, egg, type, delta, note);
      this.render();
    });

    root.querySelector('[data-action="roll-gm"]')?.addEventListener("click", async () => {
      const egg = getEgg(item);
      await rollIncubation(item, egg, { asGM: true });
      this.render();
    });

    root.querySelector('[data-action="roll-player"]')?.addEventListener("click", async () => {
      // Este botão só existe na visão de jogador (renderGmView cobre a rolagem do Mestre
      // com "roll-gm"), então quem clica aqui nunca é o Mestre.
      const egg = getEgg(item);
      await rollIncubation(item, egg, { asGM: false });
      this.render();
    });

    root.querySelector('[data-action="reveal"]')?.addEventListener("click", async () => {
      const egg = getEgg(item);
      egg.revealed = true;
      await setEgg(item, egg);
      this.render();
    });

    root.querySelector('[data-action="hatch"]')?.addEventListener("click", async () => {
      const egg = getEgg(item);
      if (!canHatch(egg)) return;
      egg.hatched = true;
      egg.revealed = true;
      await setEgg(item, egg);
      await item.update({ name: `Ovo Chocado — ${egg.species}${egg.shiny ? " ✨" : ""}` });
      ui.notifications.info(`${item.parent?.name ?? "O ovo"} chocou! Revelando ${egg.species}${egg.shiny ? " ✨ (Shiny)" : ""}.`);
      this.render();
    });
  }
}

export function registerEggSheet() {
  Items.registerSheet(MODULE_ID, EggItemSheet, {
    types: ["loot"],
    makeDefault: false,
    label: "Ovo Pokémon"
  });
}

export const EGG_SHEET_CLASS_ID = `${MODULE_ID}.EggItemSheet`;
