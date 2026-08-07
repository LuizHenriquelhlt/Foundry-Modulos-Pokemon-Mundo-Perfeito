const ABILITY_KEYS = ["str", "dex", "con", "int", "wis", "cha"];

// Foundry v13+ moveu as classes AppV1 para foundry.appv1.sheets; o global antigo
// (ActorSheet) só existe até ser removido de vez. Resolve nos dois caminhos.
const ActorSheetBase = foundry.appv1?.sheets?.ActorSheet ?? globalThis.ActorSheet;

export default class PokemonActorSheet extends ActorSheetBase {
  static get defaultOptions() {
    return foundry.utils.mergeObject(super.defaultOptions, {
      classes: ["pmp", "sheet", "actor", "pokemon"],
      template: "modules/pokemon-mundo-perfeito/templates/pokemon-actor-sheet.hbs",
      width: 640,
      height: 760,
      tabs: [{ navSelector: ".sheet-tabs", contentSelector: ".sheet-body", initial: "stats" }]
    });
  }

  /** @override */
  async getData(options) {
    const context = await super.getData(options);
    context.system = this.actor.system;
    context.abilityKeys = ABILITY_KEYS;
    context.abilityLabels = CONFIG.PMP?.abilityLabels ?? {};
    context.typeOptions = CONFIG.PMP?.types ?? [];
    context.typeLabels = CONFIG.PMP?.typeLabels ?? {};
    context.moveItems = this.actor.items.filter((item) => item.type === "pokemon-mundo-perfeito.move");
    return context;
  }

  /** @override */
  activateListeners(html) {
    super.activateListeners(html);

    html.find("[data-action='roll-ability']").on("click", (event) => this._onRollAbility(event));
    html.find("[data-action='use-move']").on("click", (event) => this._onUseMove(event));

    if (!this.isEditable) return;
  }

  async _onRollAbility(event) {
    // Rola apenas o teste de atributo puro (1d20 + mod). "system.skills" guarda os nomes das
    // Perícias do bloco de estatística (ex.: "Atletismo", "Natureza"), não chaves de atributo,
    // então a proficiência por perícia fica para quando houver um mapeamento perícia -> atributo
    // (Fase 1, junto com o conteúdo de Treinador que usa as mesmas Perícias do dnd5e).
    event.preventDefault();
    const key = event.currentTarget.dataset.ability;
    const ability = this.actor.system.abilities[key];

    const roll = new Roll(`1d20 + ${ability.mod}`);
    await roll.evaluate();
    await roll.toMessage({
      speaker: ChatMessage.getSpeaker({ actor: this.actor }),
      flavor: `Teste de ${CONFIG.PMP?.abilityLabels?.[key] ?? key.toUpperCase()}`
    });
  }

  async _onUseMove(event) {
    event.preventDefault();
    const itemId = event.currentTarget.closest("[data-item-id]")?.dataset.itemId;
    const move = this.actor.items.get(itemId);
    if (!move) return;

    const sys = move.system;
    const ppLabel = sys.pp.unlimited ? "Ilimitado" : `${sys.pp.value}/${sys.pp.max}`;
    const content = `
      <div class="pmp-move-card">
        <h3>${move.name} <span class="pmp-move-type">(${CONFIG.PMP?.typeLabels?.[sys.moveType] ?? sys.moveType})</span></h3>
        <p><strong>PP:</strong> ${ppLabel} &nbsp; <strong>Alcance:</strong> ${sys.range.raw} &nbsp; <strong>Duração:</strong> ${sys.duration}</p>
        ${sys.description}
      </div>
    `;

    await ChatMessage.create({
      speaker: ChatMessage.getSpeaker({ actor: this.actor }),
      content
    });

    if (sys.damage?.baseFormula) {
      const roll = new Roll(sys.damage.baseFormula);
      await roll.evaluate();
      await roll.toMessage({
        speaker: ChatMessage.getSpeaker({ actor: this.actor }),
        flavor: `Dano de ${move.name}`
      });
    }

    if (!sys.pp.unlimited && sys.pp.value > 0) {
      await move.update({ "system.pp.value": sys.pp.value - 1 });
    }
  }
}
