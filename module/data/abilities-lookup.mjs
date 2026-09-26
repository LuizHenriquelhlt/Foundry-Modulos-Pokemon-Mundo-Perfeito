// Busca de Habilidades Passivas no compêndio "abilities" — usado quando uma Mega Evolução
// concede uma Habilidade Passiva nova que não é nenhuma das opções normais da espécie (ex.:
// Sharpedo vira Strong Jaw ao Mega Evoluir, mas essa não é uma das habilidades do Sharpedo
// comum), então não dá pra copiar de um Item já existente no Actor.
const MODULE_ID = "pokemon-mundo-perfeito";

function abilitiesPack() {
  return game.packs.get(`${MODULE_ID}.abilities`);
}

/** @returns {Promise<{description: string, img: string}>} */
export async function fetchAbilityInfo(name) {
  const pack = abilitiesPack();
  if (!pack) return { description: "<p>Veja a Lista de Habilidades Passivas no Livro de Regras.</p>", img: "icons/svg/aura.svg" };
  const index = await pack.getIndex();
  const entry = index.find((e) => e.name.toLowerCase() === name.trim().toLowerCase());
  if (!entry) return { description: "<p>Veja a Lista de Habilidades Passivas no Livro de Regras.</p>", img: "icons/svg/aura.svg" };
  const doc = await pack.getDocument(entry._id);
  return { description: doc.system.description.value, img: doc.img };
}
