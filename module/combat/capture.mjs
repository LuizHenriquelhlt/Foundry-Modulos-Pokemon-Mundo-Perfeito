/**
 * Teste de Captura (Livro de Regras, "Capturando Pokémon"):
 * Rolagem: 1d20 + 2 × Bônus de Proficiência (do Treinador) + Bônus da Pokébola
 * CD: 10 + SR base do Pokémon (arred. p/ baixo) + nível do Pokémon + vida restante ÷ 10 (arred. p/ baixo)
 */

/**
 * @param {object} params
 * @param {number} params.speciesRank SR base do Pokémon (ex.: 0.5 para "1/2").
 * @param {number} params.level Nível atual do Pokémon selvagem.
 * @param {number} params.currentHp Vida atual do Pokémon selvagem.
 * @returns {number} CD de Captura.
 */
export function computeCaptureDC({ speciesRank, level, currentHp }) {
  return 10 + Math.floor(speciesRank) + level + Math.floor(currentHp / 10);
}

/**
 * @param {object} params
 * @param {Actor} params.trainerActor Ficha do Treinador (Actor "character" do dnd5e).
 * @param {number} [params.pokeballBonus=0] Bônus da Pokébola usada.
 * @param {string} [params.pokeballLabel="Pokébola"]
 * @param {boolean} [params.advantage=false] Vantagem (Pokémon com condição de status não-volátil ou impedido).
 * @returns {Promise<Roll>}
 */
export async function rollCapture({
  trainerActor,
  pokeballBonus = 0,
  pokeballLabel = "Pokébola",
  advantage = false
} = {}) {
  const proficiencyBonus = trainerActor?.system?.attributes?.prof ?? 2;
  const formula = advantage
    ? `2d20kh1 + ${2 * proficiencyBonus} + ${pokeballBonus}`
    : `1d20 + ${2 * proficiencyBonus} + ${pokeballBonus}`;

  const roll = new Roll(formula);
  await roll.evaluate();
  await roll.toMessage({
    speaker: ChatMessage.getSpeaker({ actor: trainerActor }),
    flavor: `Teste de Captura (${pokeballLabel})`
  });
  return roll;
}
