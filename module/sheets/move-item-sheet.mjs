// Foundry v13+ moveu as classes AppV1 e o TextEditor para namespaces; os globais
// antigos (ItemSheet, TextEditor) só existem até serem removidos de vez.
const ItemSheetBase = foundry.appv1?.sheets?.ItemSheet ?? globalThis.ItemSheet;
const TextEditorImpl =
  foundry.applications?.ux?.TextEditor?.implementation ?? globalThis.TextEditor;

export default class MoveItemSheet extends ItemSheetBase {
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
    context.enrichedDescription = await TextEditorImpl.enrichHTML(this.item.system.description, {
      relativeTo: this.item
    });
    context.enrichedHigherLevels = await TextEditorImpl.enrichHTML(this.item.system.higherLevels, {
      relativeTo: this.item
    });
    context.enrichedObservations = await TextEditorImpl.enrichHTML(this.item.system.observations, {
      relativeTo: this.item
    });
    return context;
  }
}
