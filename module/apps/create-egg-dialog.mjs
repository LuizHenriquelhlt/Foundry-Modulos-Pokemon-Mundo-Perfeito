// Diálogo do Mestre para criar um Ovo Pokémon e atribuí-lo direto a um jogador (seção 1
// do pedido). Não é ligado a nenhum documento — por isso estende ApplicationV2 puro, não
// DocumentSheetV2 (que é para editar um documento já existente).
import { SR_OPTIONS, INCUBATORS, defaultRequirementForSr, defaultEgg, makeHistoryEntry } from "../data/egg-rules.mjs";
import { EGG_SHEET_CLASS_ID } from "./egg-sheet.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const EGG_ICON = "icons/commodities/gems/pearl-storm.webp";

async function fetchPokedexNames() {
  const pack = game.packs.get(`${MODULE_ID}.pokedex`);
  if (!pack) return [];
  const index = await pack.getIndex();
  return [...index.map((e) => e.name)].sort((a, b) => a.localeCompare(b, "pt-BR"));
}

export class CreateEggDialog extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "pmp-create-egg",
    classes: ["pmp-egg-sheet-app"],
    window: { title: "Criar Ovo Pokémon", icon: "fa-solid fa-egg", resizable: true },
    position: { width: 460, height: "auto" }
  };

  async _prepareContext() {
    const players = game.users.filter((u) => !u.isGM);
    const speciesNames = await fetchPokedexNames();
    return { players, speciesNames };
  }

  async _renderHTML(context) {
    const playerOptions = context.players.map((u) => {
      const charName = u.character ? ` (${u.character.name})` : " — sem Ator atribuído";
      return `<option value="${u.id}">${u.name}${charName}</option>`;
    }).join("");
    const srOptions = SR_OPTIONS.map((sr) => `<option value="${sr}">${sr} (${defaultRequirementForSr(sr)})</option>`).join("");
    const incubatorOptions = `<option value="">Nenhuma</option>` +
      Object.values(INCUBATORS).map((i) => `<option value="${i.key}">${i.label} — ${i.price}</option>`).join("");
    const speciesList = context.speciesNames.map((n) => `<option value="${n}"></option>`).join("");

    return `
      <style>
        .pmp-create-egg { padding: 0.5rem 0.75rem; font-family: var(--font-primary, sans-serif); }
        .pmp-create-egg .pmp-egg-row { display: flex; align-items: center; gap: 0.4rem; margin: 0.35rem 0; }
        .pmp-create-egg .pmp-egg-row label { min-width: 10rem; font-weight: 600; font-size: 0.85rem; }
        .pmp-create-egg input, .pmp-create-egg select { flex: 1; }
        .pmp-create-egg .pmp-egg-hint { font-size: 0.75rem; opacity: 0.7; margin-left: 10.4rem; }
        .pmp-create-egg .pmp-egg-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.75rem; }
      </style>
      <div class="pmp-create-egg">
        <div class="pmp-egg-row"><label>Jogador</label><select data-field="userId"><option value="">— selecione —</option>${playerOptions}</select></div>
        <div class="pmp-egg-row"><label>Espécie (secreta)</label><input type="text" data-field="species" list="pmp-species-list" /></div>
        <datalist id="pmp-species-list">${speciesList}</datalist>
        <div class="pmp-egg-row"><label>Shiny (secreto)</label><input type="checkbox" data-field="shiny" /></div>
        <div class="pmp-egg-row"><label>SR (secreto)</label><select data-field="sr">${srOptions}</select></div>
        <div class="pmp-egg-row"><label>Requisito de eclosão</label><input type="number" data-field="requirement" /></div>
        <p class="pmp-egg-hint" data-hint="requirement">Preenchido automaticamente pela tabela de SR — edite se quiser um valor diferente.</p>
        <div class="pmp-egg-row"><label>Progresso inicial</label><input type="number" data-field="progress" value="0" /></div>
        <div class="pmp-egg-row"><label>Incubadora</label><select data-field="incubator">${incubatorOptions}</select></div>
        <div class="pmp-egg-actions">
          <button type="button" data-action="cancel">Cancelar</button>
          <button type="button" data-action="create">🥚 Criar Ovo</button>
        </div>
      </div>`;
  }

  _replaceHTML(result, content) {
    content.innerHTML = result;
    this._attachListeners(content);
  }

  _attachListeners(root) {
    const srSelect = root.querySelector('[data-field="sr"]');
    const reqInput = root.querySelector('[data-field="requirement"]');
    const syncDefault = () => { reqInput.value = defaultRequirementForSr(srSelect.value) ?? ""; };
    srSelect.addEventListener("change", syncDefault);
    syncDefault();

    root.querySelector('[data-action="cancel"]').addEventListener("click", () => this.close());
    root.querySelector('[data-action="create"]').addEventListener("click", () => this._onCreate(root));
  }

  async _onCreate(root) {
    const read = (name) => root.querySelector(`[data-field="${name}"]`);
    const userId = read("userId").value;
    const species = read("species").value.trim();
    const sr = read("sr").value;
    const requirementValue = Number(read("requirement").value);
    const defaultValue = defaultRequirementForSr(sr);

    if (!userId) {
      ui.notifications.warn("Escolha o jogador que vai receber o ovo.");
      return;
    }
    if (!species) {
      ui.notifications.warn("Defina a espécie do Pokémon dentro do ovo.");
      return;
    }
    const user = game.users.get(userId);
    const actor = user?.character;
    if (!actor) {
      ui.notifications.error(`${user?.name ?? "Esse jogador"} não tem um Ator atribuído. Atribua um Treinador a ele antes de criar o ovo.`);
      return;
    }

    const progress = Number(read("progress").value) || 0;
    const egg = defaultEgg({
      species, shiny: read("shiny").checked, sr,
      requirementCustom: Number.isFinite(requirementValue) && requirementValue !== defaultValue ? requirementValue : null,
      progress, incubator: read("incubator").value || null, ownerUserId: userId
    });
    if (progress > 0) egg.history = [makeHistoryEntry("initial", progress, progress, "Progresso inicial ao criar o ovo")];

    const [item] = await actor.createEmbeddedDocuments("Item", [{
      name: "Ovo Pokémon", type: "loot", img: EGG_ICON,
      system: { quantity: 1 },
      flags: { [MODULE_ID]: { egg }, core: { sheetClass: EGG_SHEET_CLASS_ID } }
    }]);

    ui.notifications.info(`Ovo criado e entregue a ${actor.name}.`);
    this.close();
    item.sheet.render(true);
  }
}

export async function openCreateEggDialog() {
  if (!game.user.isGM) {
    ui.notifications.warn("Apenas o Mestre pode criar ovos.");
    return;
  }
  new CreateEggDialog().render(true);
}
