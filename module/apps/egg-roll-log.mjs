// Log consolidado das rolagens de incubação de TODOS os ovos do mundo, pro Mestre não
// precisar abrir ficha por ficha pra saber quem rolou o quê e quando. Cada ovo já guarda o
// próprio histórico completo (progresso manual incluído) na sua ficha — aqui filtra só as
// entradas de rolagem de dado (🎲) e junta todas numa tabela só, mais recente primeiro.
import { HISTORY_TYPES } from "../data/egg-rules.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const ROLL_TYPES = new Set(["playerRoll", "gmRoll"]);

function collectEggRolls() {
  const rows = [];
  for (const actor of game.actors) {
    for (const item of actor.items) {
      const egg = item.getFlag(MODULE_ID, "egg");
      if (!egg) continue;
      const eggLabel = egg.revealed || egg.hatched ? (egg.species || item.name) : "Ovo secreto";
      for (const h of egg.history ?? []) {
        if (!ROLL_TYPES.has(h.type)) continue;
        rows.push({ ...h, actorName: actor.name, eggLabel });
      }
    }
  }
  return rows.sort((a, b) => b.ts - a.ts);
}

function renderRow(row) {
  const meta = HISTORY_TYPES[row.type] ?? { icon: "•", label: row.type };
  const when = new Date(row.ts).toLocaleString("pt-BR");
  const sign = row.delta >= 0 ? "+" : "";
  return `
    <tr>
      <td>${when}</td>
      <td>${row.actorName}</td>
      <td>${row.eggLabel}</td>
      <td>${meta.icon} ${meta.label}</td>
      <td>${sign}${row.delta}</td>
      <td>${row.total}</td>
    </tr>`;
}

export class EggRollLogApp extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "pmp-egg-roll-log",
    classes: ["pmp-egg-sheet-app"],
    window: { title: "Log de Rolagens de Incubação", icon: "fa-solid fa-dice", resizable: true },
    position: { width: 640, height: 480 }
  };

  async _renderHTML() {
    const rows = collectEggRolls();
    const body = rows.length
      ? rows.map(renderRow).join("")
      : `<tr><td colspan="6" style="text-align:center;opacity:0.6;">Nenhuma rolagem de incubação registrada ainda.</td></tr>`;
    return `
      <style>
        .pmp-roll-log { padding: 0.5rem 0.75rem; font-family: var(--font-primary, sans-serif); }
        .pmp-roll-log table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        .pmp-roll-log th { text-align: left; border-bottom: 2px solid #999; padding: 0.25rem 0.4rem; }
        .pmp-roll-log td { border-bottom: 1px solid #eee; padding: 0.25rem 0.4rem; }
        .pmp-roll-log-actions { display: flex; justify-content: flex-end; margin-bottom: 0.5rem; }
      </style>
      <div class="pmp-roll-log">
        <div class="pmp-roll-log-actions"><button type="button" data-action="refresh">🔄 Atualizar</button></div>
        <table>
          <thead><tr><th>Quando</th><th>Treinador</th><th>Ovo</th><th>Origem</th><th>Rolagem</th><th>Progresso</th></tr></thead>
          <tbody>${body}</tbody>
        </table>
      </div>`;
  }

  _replaceHTML(result, content) {
    content.innerHTML = result;
    content.querySelector('[data-action="refresh"]')?.addEventListener("click", () => this.render());
  }
}

let appInstance = null;

export function openEggRollLog() {
  if (!game.user.isGM) {
    ui.notifications.warn("Apenas o Mestre pode ver o log de rolagens.");
    return;
  }
  if (!appInstance) appInstance = new EggRollLogApp();
  appInstance.render(true);
}

// Chamado pelo hook updateItem em pmp.mjs sempre que um ovo muda — só re-renderiza se a
// janela já estiver aberta, pra não gastar trabalho à toa quando ninguém está olhando.
export function refreshEggRollLogIfOpen() {
  if (appInstance?.rendered) appInstance.render();
}
