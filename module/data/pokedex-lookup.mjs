// Busca de espécies no compêndio "pokedex" — usado ao chocar um ovo, tanto pra achar o
// Actor a ser copiado quanto pra ler a lista de Egg Moves daquela espécie.
const MODULE_ID = "pokemon-mundo-perfeito";

function pokedexPack() {
  return game.packs.get(`${MODULE_ID}.pokedex`);
}

export async function findSpeciesIndexEntry(speciesName) {
  const pack = pokedexPack();
  if (!pack) return null;
  const index = await pack.getIndex();
  const needle = speciesName.trim().toLowerCase();
  return index.find((e) => e.name.toLowerCase() === needle) ?? null;
}

export async function fetchSpeciesDocument(speciesName) {
  const entry = await findSpeciesIndexEntry(speciesName);
  if (!entry) return null;
  return pokedexPack().getDocument(entry._id);
}

export async function fetchSpeciesEggMoves(speciesName) {
  const doc = await fetchSpeciesDocument(speciesName);
  return doc?.getFlag(MODULE_ID, "species")?.eggMoves ?? [];
}
