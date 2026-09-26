// Escolha da perícia da homebrew Afinidade (Livro de Regras pág. 37, nível Satisfeito: "ganha
// uma perícia proficiente à escolha"; Leal: essa mesma perícia vira especialista). A escolha
// persiste através de flutuações de PA — só muda quando o jogador/Mestre abrir este diálogo
// de novo (ex.: depois de uma evolução que já dá aquela perícia de outro jeito).
import { getAffinitySkill, setAffinitySkill } from "../data/loyalty.mjs";

export class AffinitySkillDialog extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "pmp-affinity-skill",
    classes: ["pmp-egg-sheet-app"],
    window: { title: "Perícia da Afinidade", icon: "fa-solid fa-star", resizable: true },
    position: { width: 360, height: "auto" }
  };

  constructor(actor, options = {}) {
    super(options);
    this.actor = actor;
  }

  async _renderHTML() {
    const current = getAffinitySkill(this.actor);
    const options = Object.entries(CONFIG.DND5E.skills)
      .map(([key, cfg]) => ({ key, label: game.i18n.localize(cfg.label) }))
      .sort((a, b) => a.label.localeCompare(b.label, "pt-BR"))
      .map(({ key, label }) => `<option value="${key}" ${key === current ? "selected" : ""}>${label}</option>`)
      .join("");

    return `
      <style>
        .pmp-affinity-skill { padding: 0.5rem 0.75rem; font-family: var(--font-primary, sans-serif); }
        .pmp-affinity-skill p { font-size: 0.82rem; opacity: 0.85; }
        .pmp-affinity-skill select { width: 100%; margin: 0.4rem 0 0.75rem; }
        .pmp-affinity-skill .pmp-affinity-skill-actions { display: flex; justify-content: flex-end; gap: 0.5rem; }
      </style>
      <div class="pmp-affinity-skill">
        <p>Perícia proficiente escolhida em Satisfeito (vira especialista em Leal). Fica
        registrada mesmo se a Afinidade cair e voltar depois.</p>
        <select data-field="skill"><option value="">— nenhuma —</option>${options}</select>
        <div class="pmp-affinity-skill-actions">
          <button type="button" data-action="cancel">Cancelar</button>
          <button type="button" data-action="confirm">Salvar</button>
        </div>
      </div>`;
  }

  _replaceHTML(result, content) {
    content.innerHTML = result;
    content.querySelector('[data-action="cancel"]').addEventListener("click", () => this.close());
    content.querySelector('[data-action="confirm"]').addEventListener("click", () => this._onConfirm(content));
  }

  async _onConfirm(root) {
    const skill = root.querySelector('[data-field="skill"]').value;
    await setAffinitySkill(this.actor, skill);
    this.close();
  }
}

export function openAffinitySkillDialog(actor) {
  new AffinitySkillDialog(actor).render(true);
}
