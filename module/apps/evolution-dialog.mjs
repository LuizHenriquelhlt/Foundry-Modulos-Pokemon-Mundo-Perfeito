// Diálogo do botão "🧬 Evoluir" da ficha do Pokémon. Mostra o texto de requisito (livre,
// vem da Pokédex) só como referência — quem confirma se o requisito foi cumprido é o
// jogador/Mestre na mesa, a ferramenta só executa a troca mecânica depois de confirmada.
import { suggestEvolutionCandidates, evolveActor, listSpeciesNames } from "../data/evolution.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";

export class EvolutionDialog extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "pmp-evolution",
    classes: ["pmp-egg-sheet-app"],
    window: { title: "Evolução", icon: "fa-solid fa-dna", resizable: true },
    position: { width: 460, height: "auto" }
  };

  constructor(actor, options = {}) {
    super(options);
    this.actor = actor;
  }

  async _prepareContext() {
    const species = this.actor.getFlag(MODULE_ID, "species");
    const candidates = await suggestEvolutionCandidates(this.actor);
    const allNames = await listSpeciesNames();
    return { species, candidates, allNames };
  }

  async _renderHTML(context) {
    const { species, candidates, allNames } = context;
    const chips = candidates.map((name) => `<a role="button" class="pmp-evo-chip" data-name="${name}">${name}</a>`).join("");
    const speciesList = allNames.map((n) => `<option value="${n}"></option>`).join("");

    return `
      <style>
        .pmp-evolution { padding: 0.5rem 0.75rem; font-family: var(--font-primary, sans-serif); }
        .pmp-evolution .pmp-evo-req { font-size: 0.8rem; opacity: 0.85; border-left: 3px solid #999;
          padding: 0.25rem 0.6rem; margin: 0.4rem 0 0.7rem; }
        .pmp-evolution .pmp-evo-row { display: flex; align-items: center; gap: 0.4rem; margin: 0.35rem 0; }
        .pmp-evolution .pmp-evo-row label { min-width: 8rem; font-weight: 600; font-size: 0.85rem; }
        .pmp-evolution input { flex: 1; }
        .pmp-evolution .pmp-evo-chips { display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 0.3rem 0 0.6rem 8.4rem; }
        .pmp-evolution .pmp-evo-chip { border: 1px solid #999; border-radius: 10px; padding: 1px 8px;
          font-size: 0.75rem; cursor: pointer; }
        .pmp-evolution .pmp-evo-chip:hover { background: rgba(255,255,255,0.15); }
        .pmp-evolution .pmp-evo-hint { font-size: 0.72rem; opacity: 0.65; margin: 0.2rem 0 0 8.4rem; }
        .pmp-evolution .pmp-evo-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.75rem; }
      </style>
      <div class="pmp-evolution">
        <p><strong>${species?.species ?? this.actor.name}</strong> (Nível ${this.actor.items.find((i) => i.type === "class")?.system?.levels ?? 1}) — Estágio Evolutivo ${species?.evolutionStage?.current ?? "?"}/${species?.evolutionStage?.max ?? "?"}</p>
        <p class="pmp-evo-req">${species?.evolution || "Esta espécie não tem requisito de evolução cadastrado."}</p>
        <div class="pmp-evo-row">
          <label>Evolui para</label>
          <input type="text" data-field="target" list="pmp-evo-species-list"
                 value="${candidates.length === 1 ? candidates[0] : ""}" />
        </div>
        <datalist id="pmp-evo-species-list">${speciesList}</datalist>
        ${chips ? `<div class="pmp-evo-chips">${chips}</div>` : ""}
        <p class="pmp-evo-hint">Confirme só depois de checar na mesa que o requisito acima foi cumprido — a
          lista acima é uma sugestão lida do texto da Pokédex, não uma validação automática.</p>
        <div class="pmp-evo-actions">
          <button type="button" data-action="cancel">Cancelar</button>
          <button type="button" data-action="confirm">🧬 Evoluir</button>
        </div>
      </div>`;
  }

  _replaceHTML(result, content) {
    content.innerHTML = result;
    content.querySelectorAll(".pmp-evo-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        content.querySelector('[data-field="target"]').value = chip.dataset.name;
      });
    });
    content.querySelector('[data-action="cancel"]').addEventListener("click", () => this.close());
    content.querySelector('[data-action="confirm"]').addEventListener("click", () => this._onConfirm(content));
  }

  async _onConfirm(root) {
    const target = root.querySelector('[data-field="target"]').value.trim();
    if (!target) {
      ui.notifications.warn("Escolha pra qual espécie o Pokémon vai evoluir.");
      return;
    }
    const result = await evolveActor(this.actor, target);
    if (result.status === "species-not-found") {
      ui.notifications.warn(`"${target}" não foi encontrado na Pokédex — confira o nome exato.`);
      return;
    }
    if (result.status === "evolved") {
      ui.notifications.info(`${result.from} evoluiu para ${result.to}!`);
      this.close();
    }
  }
}

export function openEvolutionDialog(actor) {
  new EvolutionDialog(actor).render(true);
}
