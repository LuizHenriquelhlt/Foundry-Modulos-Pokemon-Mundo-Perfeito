// Cria o Actor Pokémon de verdade quando um ovo choca — copia o Actor da Pokédex (mesmo
// bloco de estatísticas, Moves iniciais, token), marca o Shiny na instância nova (o
// registro do compêndio é sempre não-Shiny; brilhante é uma característica do indivíduo,
// não da espécie) e entrega a posse ao jogador dono do ovo.
import { fetchSpeciesDocument } from "./pokedex-lookup.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";

/**
 * @param {object} egg Dados do ovo (species, shiny, ownerUserId).
 * @param {Actor|null} trainerActor Ator do Treinador dono do ovo, se houver (define a posse do Pokémon novo).
 * @returns {Promise<{status: "created", actor: Actor}|{status: "species-not-found"|"permission-denied"}>}
 */
export async function createHatchedActor(egg, trainerActor) {
  const speciesDoc = await fetchSpeciesDocument(egg.species);
  if (!speciesDoc) return { status: "species-not-found" };

  // Por padrão, só o Mestre pode criar Actors no mundo — mas a seção 10 do pedido também
  // deixa o jogador dono chocar o ovo. Se quem clicou não tiver essa permissão (mesa não
  // liberou "Create New Actors" pros jogadores), falha graciosamente em vez de estourar erro:
  // o ovo ainda revela os dados, só não cria o Actor sozinho.
  if (!game.user.can("ACTOR_CREATE")) return { status: "permission-denied" };

  const data = speciesDoc.toObject();
  delete data._id;
  foundry.utils.setProperty(data, `flags.${MODULE_ID}.species.shiny`, !!egg.shiny);

  // Copia a permissão de quem já é dono do Treinador em vez de depender só do
  // ownerUserId guardado no ovo — a Configuração de Propriedade do Actor é a fonte da
  // verdade de "de quem é isso" no Foundry, então o Pokémon nasce com a mesma posse.
  const ownership = { default: 0, ...(trainerActor?.ownership ?? {}) };
  if (egg.ownerUserId) ownership[egg.ownerUserId] = CONST.DOCUMENT_OWNERSHIP_LEVELS.OWNER;
  data.ownership = ownership;

  // Não escolhe pasta sozinho — nasce na raiz do diretório de Actors, e o Mestre decide
  // onde organizar (botão "📁 Mover para pasta" na ficha do ovo já chocado). Cada mesa
  // organiza diferente; melhor deixar essa decisão manual e explícita.

  try {
    const actor = await Actor.create(data);
    return { status: "created", actor };
  } catch (err) {
    console.error(`${MODULE_ID} | Falha ao criar Actor do Pokémon chocado`, err);
    return { status: "permission-denied" };
  }
}
