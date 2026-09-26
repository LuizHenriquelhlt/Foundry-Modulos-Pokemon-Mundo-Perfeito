// Diálogo do botão "✨ Terastalizar" — escolhe o Tipo Tera (padrão: tipo primário do próprio
// Pokémon, conforme a regra "a menos que indicado o contrário, o Tera Tipo é igual ao seu
// tipo primário"). Sempre pergunta, já que o Tipo Tera é um traço individual, não fixo por
// item como a Mega Pedra.
import { TYPES, TYPE_LABELS } from "../combat/type-chart.mjs";
import { terastallize, findEquippedTeraFactor, STELLAR_KEY } from "../combat/terastal.mjs";

export class TerastalDialog extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "pmp-terastal",
    classes: ["pmp-egg-sheet-app"],
    window: { title: "Terastalização", icon: "fa-solid fa-gem", resizable: true },
    position: { width: 360, height: "auto" }
  };

  constructor(actor, options = {}) {
    super(options);
    this.actor = actor;
  }

  async _renderHTML() {
    const species = this.actor.getFlag("pokemon-mundo-perfeito", "species");
    const defaultType = species?.types?.type1 ?? "normal";
    const options = TYPES.map((t) => `<option value="${t}" ${t === defaultType ? "selected" : ""}>${TYPE_LABELS[t]}</option>`).join("");

    return `
      <style>
        .pmp-terastal { padding: 0.5rem 0.75rem; font-family: var(--font-primary, sans-serif); }
        .pmp-terastal select { width: 100%; margin: 0.4rem 0 0.75rem; }
        .pmp-terastal .pmp-terastal-actions { display: flex; justify-content: flex-end; gap: 0.5rem; }
      </style>
      <div class="pmp-terastal">
        <p>Escolha o Tipo Tera. Por padrão é igual ao tipo primário do Pokémon — mude se este
        indivíduo tiver um Tipo Tera diferente.</p>
        <select data-field="type">${options}<option value="${STELLAR_KEY}">✨ Estelar (19º tipo)</option></select>
        <div class="pmp-terastal-actions">
          <button type="button" data-action="cancel">Cancelar</button>
          <button type="button" data-action="confirm">✨ Terastalizar</button>
        </div>
      </div>`;
  }

  _replaceHTML(result, content) {
    content.innerHTML = result;
    content.querySelector('[data-action="cancel"]').addEventListener("click", () => this.close());
    content.querySelector('[data-action="confirm"]').addEventListener("click", () => this._onConfirm(content));
  }

  async _onConfirm(root) {
    const type = root.querySelector('[data-field="type"]').value;
    await terastallize(this.actor, type);
    this.close();
  }
}

export function openTerastalDialog(actor) {
  if (!findEquippedTeraFactor(actor)) {
    ui.notifications.warn(`${actor.name} precisa estar segurando um Fator Terastal (equipado) pra Terastalizar.`);
    return;
  }
  new TerastalDialog(actor).render(true);
}
