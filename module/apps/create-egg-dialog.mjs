// Diálogo do Mestre para criar um Ovo Pokémon e atribuí-lo direto a um jogador (seção 1
// do pedido). Não é ligado a nenhum documento — por isso estende ApplicationV2 puro, não
// DocumentSheetV2 (que é para editar um documento já existente).
import { SR_OPTIONS, defaultRequirementForSr, defaultEgg, makeHistoryEntry } from "../data/egg-rules.mjs";
import { listIncubators } from "../data/incubator-lookup.mjs";
import { EGG_SHEET_CLASS_ID } from "./egg-sheet.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const EGG_ICON = "icons/commodities/gems/pearl-storm.webp";

async function fetchPokedexNames() {
  const pack = game.packs.get(`${MODULE_ID}.pokedex`);
  if (!pack) return [];
  const index = await pack.getIndex();
  return [...index.map((e) => e.name)].sort((a, b) => a.localeCompare(b, "pt-BR"));
}

// Quem "é dono" de um Treinador é definido pela permissão real do Actor (Configuração de
// Propriedade), não pelo "Personagem" padrão do usuário em Configurações — muita mesa nunca
// preenche esse campo, então depender dele trava a criação de ovo sem necessidade.
function findOwningUser(actor) {
  const ownerId = Object.entries(actor.ownership ?? {}).find(([id, level]) =>
    id !== "default" && level >= CONST.DOCUMENT_OWNERSHIP_LEVELS.OWNER && !game.users.get(id)?.isGM
  )?.[0];
  return ownerId ? game.users.get(ownerId) : null;
}

export class CreateEggDialog extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "pmp-create-egg",
    classes: ["pmp-egg-sheet-app"],
    window: { title: "Criar Ovo Pokémon", icon: "fa-solid fa-egg", resizable: true },
    position: { width: 460, height: "auto" }
  };

  async _prepareContext() {
    const trainers = game.actors.filter((a) => a.type === "character");
    const speciesNames = await fetchPokedexNames();
    const incubators = await listIncubators();
    return { trainers, speciesNames, incubators };
  }

  async _renderHTML(context) {
    const trainerOptions = context.trainers.map((a) => {
      const owner = findOwningUser(a);
      return `<option value="${a.id}">${a.name}${owner ? ` (${owner.name})` : ""}</option>`;
    }).join("");
    const srOptions = SR_OPTIONS.map((sr) => `<option value="${sr}">${sr} (${defaultRequirementForSr(sr)})</option>`).join("");
    const incubatorOptions = `<option value="">Nenhuma</option>` +
      context.incubators.map((i) => `<option value="${i.name}">${i.name} — ₽${i.price.toLocaleString("pt-BR")}</option>`).join("");
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
        <div class="pmp-egg-row"><label>Treinador</label><select data-field="actorId"><option value="">— selecione —</option>${trainerOptions}</select></div>
        ${!context.trainers.length ? `<p class="pmp-egg-hint" style="margin-left:0;color:#c0392b;">Nenhum Actor do tipo "character" encontrado — crie a ficha do Treinador antes de criar o ovo.</p>` : ""}
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
    const actorId = read("actorId").value;
    const species = read("species").value.trim();
    const sr = read("sr").value;
    const requirementValue = Number(read("requirement").value);
    const defaultValue = defaultRequirementForSr(sr);

    if (!actorId) {
      ui.notifications.warn("Escolha o Treinador que vai receber o ovo.");
      return;
    }
    const actor = game.actors.get(actorId);
    if (!actor) {
      ui.notifications.error("Esse Treinador não existe mais — feche e abra o diálogo de novo.");
      return;
    }
    if (!species) {
      ui.notifications.warn("Defina a espécie do Pokémon dentro do ovo.");
      return;
    }

    const owner = findOwningUser(actor);
    const progress = Number(read("progress").value) || 0;
    const egg = defaultEgg({
      species, shiny: read("shiny").checked, sr,
      requirementCustom: Number.isFinite(requirementValue) && requirementValue !== defaultValue ? requirementValue : null,
      progress, incubator: read("incubator").value || null, ownerUserId: owner?.id ?? null
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
