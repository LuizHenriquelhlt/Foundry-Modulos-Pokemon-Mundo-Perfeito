export default class MoveItemSheet extends ItemSheet {
  static get defaultOptions() {
    return foundry.utils.mergeObject(super.defaultOptions, {
      classes: ["pmp", "sheet", "item", "move"],
      template: "modules/pokemon-mundo-perfeito/templates/move-item-sheet.hbs",
      width: 520,
      height: 560
    });
  }

  /** @override */
  async getData(options) {
    const context = await super.getData(options);
    context.system = this.item.system;
    context.typeOptions = CONFIG.PMP?.types ?? [];
    context.typeLabels = CONFIG.PMP?.typeLabels ?? {};
    context.enrichedDescription = await TextEditor.enrichHTML(this.item.system.description, {
      relativeTo: this.item
    });
    context.enrichedHigherLevels = await TextEditor.enrichHTML(this.item.system.higherLevels, {
      relativeTo: this.item
    });
    context.enrichedObservations = await TextEditor.enrichHTML(this.item.system.observations, {
      relativeTo: this.item
    });
    return context;
  }
}
