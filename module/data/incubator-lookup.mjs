// Incubadoras agora são Items de verdade no compêndio trainer-features (bonusDice fica em
// flags["pokemon-mundo-perfeito"].incubator.bonusDice, editável pelo Mestre via "Configurar
// Flags" nativo do Foundry no próprio Item) — este módulo é quem sabe ler isso, pra
// egg-sheet.mjs/create-egg-dialog.mjs nunca precisarem conhecer o formato interno da flag.
const MODULE_ID = "pokemon-mundo-perfeito";

function trainerFeaturesPack() {
  return game.packs.get(`${MODULE_ID}.trainer-features`);
}

/**
 * @returns {Promise<{id:string, name:string, price:number, bonusDice:string}[]>} Ordenadas do
 * mais barato pro mais caro.
 */
export async function listIncubators() {
  const pack = trainerFeaturesPack();
  if (!pack) return [];
  const index = await pack.getIndex({ fields: ["flags.pokemon-mundo-perfeito.incubator", "system.price.value"] });
  return index
    .filter((e) => e.flags?.[MODULE_ID]?.incubator)
    .map((e) => ({
      id: e._id, name: e.name,
      price: e.system?.price?.value ?? 0,
      bonusDice: e.flags[MODULE_ID].incubator.bonusDice
    }))
    .sort((a, b) => a.price - b.price);
}

export async function fetchIncubatorByName(name) {
  if (!name) return null;
  const incubators = await listIncubators();
  return incubators.find((i) => i.name === name) ?? null;
}
