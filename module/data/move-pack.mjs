// Empresta um Move do compêndio "moves" pra um Actor, copiando o Item pronto (fórmula,
// PP, Activities) em vez de recriar os dados na mão. Usado pelo aprendizado automático via
// TM (pmp.mjs) e pelos Egg Moves escolhidos ao chocar um ovo (egg-moves-dialog.mjs) — os
// dois precisam exatamente do mesmo "copia o Item do compêndio pro Actor, sem duplicar se
// já for conhecido", então fica num lugar só.
const MODULE_ID = "pokemon-mundo-perfeito";

export async function fetchMoveDocument(moveName) {
  const pack = game.packs.get(`${MODULE_ID}.moves`);
  if (!pack) return null;
  const index = await pack.getIndex();
  const entry = index.find((e) => e.name === moveName);
  if (!entry) return null;
  return pack.getDocument(entry._id);
}

/**
 * @returns {Promise<"already-known"|"not-found"|"learned">}
 */
export async function learnMove(actor, moveName) {
  if (actor.items.some((i) => i.name === moveName)) return "already-known";
  const move = await fetchMoveDocument(moveName);
  if (!move) return "not-found";
  const data = move.toObject();
  delete data._id;
  await actor.createEmbeddedDocuments("Item", [data]);
  return "learned";
}
