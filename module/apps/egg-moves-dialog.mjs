// Diálogo pro Mestre escolher quais Egg Moves da espécie o filhote já nasce sabendo
// (Livro de Regras pág. 43: "Qualquer Egg Move... CONHECIDO por qualquer um dos pais no
// momento da reprodução"). Este módulo não rastreia os pais reprodutores — quem decide
// quais Egg Moves valem é o Mestre, na hora de chocar.
import { learnMove } from "../data/move-pack.mjs";

export class EggMovesDialog extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "pmp-egg-moves",
    classes: ["pmp-egg-sheet-app"],
    window: { title: "Escolher Egg Moves", icon: "fa-solid fa-dna", resizable: true },
    position: { width: 380, height: "auto" }
  };

  /**
   * @param {Actor} actor Pokémon recém-chocado que vai aprender os Moves.
   * @param {string[]} eggMoves Lista de nomes de Moves da espécie.
   */
  constructor(actor, eggMoves, options = {}) {
    super(options);
    this.actor = actor;
    this.eggMoves = eggMoves;
  }

  async _renderHTML() {
    const known = new Set(this.actor.items.map((i) => i.name));
    if (!this.eggMoves.length) {
      return `<div style="padding:0.75rem;">Esta espécie não tem Egg Moves cadastrados na Pokédex.</div>`;
    }
    const rows = this.eggMoves.map((name) => {
      const already = known.has(name);
      return `
        <label class="pmp-egg-move-row">
          <input type="checkbox" data-move="${name}" ${already ? "checked disabled" : ""} />
          ${name}${already ? " <em>(já conhece)</em>" : ""}
        </label>`;
    }).join("");

    return `
      <style>
        .pmp-egg-moves { padding: 0.5rem 0.75rem; font-family: var(--font-primary, sans-serif); }
        .pmp-egg-move-row { display: block; padding: 0.15rem 0; }
        .pmp-egg-move-row em { opacity: 0.6; font-size: 0.8rem; }
        .pmp-egg-moves-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.75rem; }
      </style>
      <div class="pmp-egg-moves">
        <p>O Pokémon já nasce sabendo:</p>
        ${rows}
        <div class="pmp-egg-moves-actions">
          <button type="button" data-action="cancel">Fechar</button>
          <button type="button" data-action="confirm">Adicionar selecionados</button>
        </div>
      </div>`;
  }

  _replaceHTML(result, content) {
    content.innerHTML = result;
    content.querySelector('[data-action="cancel"]')?.addEventListener("click", () => this.close());
    content.querySelector('[data-action="confirm"]')?.addEventListener("click", () => this._onConfirm(content));
  }

  async _onConfirm(root) {
    const boxes = root.querySelectorAll("input[data-move]:checked:not(:disabled)");
    let learned = 0;
    for (const box of boxes) {
      const result = await learnMove(this.actor, box.dataset.move);
      if (result === "learned") learned++;
    }
    ui.notifications.info(learned > 0
      ? `${this.actor.name} nasceu já sabendo ${learned} Egg Move(s).`
      : "Nenhum Move novo selecionado.");
    this.close();
  }
}

export function openEggMovesDialog(actor, eggMoves) {
  new EggMovesDialog(actor, eggMoves).render(true);
}
