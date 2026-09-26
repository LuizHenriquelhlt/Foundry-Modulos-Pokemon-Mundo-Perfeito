// Diálogo do botão "🔷 Mega Evoluir" — só abre quando a Mega Pedra equipada tem pelo menos
// uma escolha de atributo (ex.: Alakazite dá +4 em Inteligência OU Sabedoria). Sem escolha
// nenhuma, o botão da ficha aplica a Mega Evolução direto, sem precisar deste diálogo.
import { findEquippedMegaStone, applyMegaEvolution } from "../combat/mega-evolution.mjs";

export class MegaEvolutionDialog extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "pmp-mega-evolution",
    classes: ["pmp-egg-sheet-app"],
    window: { title: "Mega Evolução", icon: "fa-solid fa-gem", resizable: true },
    position: { width: 380, height: "auto" }
  };

  constructor(actor, stone, options = {}) {
    super(options);
    this.actor = actor;
    this.stone = stone;
  }

  async _renderHTML() {
    const mega = this.stone.getFlag("pokemon-mundo-perfeito", "mega");
    const labels = CONFIG.PMP.abilityLabels;
    const rows = (mega.abilityChoices ?? []).map((choice, i) => {
      const options = choice.options.map((k) => `<option value="${k}">${labels[k] ?? k.toUpperCase()}</option>`).join("");
      return `
        <div class="pmp-mega-row">
          <label>+${choice.delta} em</label>
          <select data-choice="${choice.options.join("/")}">${options}</select>
        </div>`;
    }).join("");

    return `
      <style>
        .pmp-mega-evolution { padding: 0.5rem 0.75rem; font-family: var(--font-primary, sans-serif); }
        .pmp-mega-row { display: flex; align-items: center; gap: 0.5rem; margin: 0.4rem 0; }
        .pmp-mega-row label { min-width: 6rem; font-weight: 600; font-size: 0.85rem; }
        .pmp-mega-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.75rem; }
      </style>
      <div class="pmp-mega-evolution">
        <p>${this.stone.name} permite escolher onde aplicar o bônus:</p>
        ${rows}
        <div class="pmp-mega-actions">
          <button type="button" data-action="cancel">Cancelar</button>
          <button type="button" data-action="confirm">🔷 Mega Evoluir</button>
        </div>
      </div>`;
  }

  _replaceHTML(result, content) {
    content.innerHTML = result;
    content.querySelector('[data-action="cancel"]').addEventListener("click", () => this.close());
    content.querySelector('[data-action="confirm"]').addEventListener("click", () => this._onConfirm(content));
  }

  async _onConfirm(root) {
    const chosen = {};
    root.querySelectorAll("[data-choice]").forEach((select) => {
      chosen[select.dataset.choice] = select.value;
    });
    await applyMegaEvolution(this.actor, chosen);
    this.close();
  }
}

export async function openMegaEvolutionOrApply(actor) {
  const stone = findEquippedMegaStone(actor);
  if (!stone) {
    ui.notifications.warn(`${actor.name} precisa estar segurando a Mega Pedra da própria espécie (equipada) pra Mega Evoluir.`);
    return;
  }
  const mega = stone.getFlag("pokemon-mundo-perfeito", "mega");
  if (mega.abilityChoices?.length) {
    new MegaEvolutionDialog(actor, stone).render(true);
  } else {
    await applyMegaEvolution(actor);
  }
}
