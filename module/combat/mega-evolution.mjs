/**
 * Mega Evolução (Livro de Mega Evoluções, "Introdução" / "Mega Evolução em Batalha"):
 * - Ação bônus, no início do turno; mudanças de atributos/estatísticas são imediatas.
 * - DES aumentada só afeta a Iniciativa a partir da próxima rodada.
 * - Atributos podem passar de 20, mas nunca de 30.
 * - Sempre concede uma nova Habilidade Passiva, substituindo a anterior (mesmo se for Oculta).
 * - Pode alterar tipagem e tamanho.
 *
 * Diferente do que a Fase 0 assumia, os benefícios de CA e atributos são DELTAS (+N),
 * não valores absolutos — confirmado ao extrair as 93 Mega Evoluções do livro (Fase 4).
 * Tipo/Habilidade Passiva/Tamanho continuam sendo overrides absolutos, como o texto do
 * livro realmente descreve cada um ("muda para X").
 *
 * O estado original é guardado em flags para permitir reverter ao fim do combate.
 */

const FLAG_SCOPE = "pokemon-mundo-perfeito";
const FLAG_KEY = "megaEvolutionSnapshot";
const MAX_ABILITY_SCORE = 30;

/**
 * @param {Actor} pokemonActor Actor do subtipo pokemon-mundo-perfeito.pokemon.
 * @param {object} megaData Dados da Mega Evolução (tipicamente megaEvolutionItem.system,
 *   no schema gerado por scripts/parse-mega-evolutions.py).
 * @param {Record<string,string>} [chosenAbilities] Para cada entrada de megaData.abilityChoices,
 *   qual das opções (chave de atributo) o jogador escolheu. Se omitido, usa a primeira opção
 *   de cada escolha (documentar essa escolha padrão até haver UI dedicada).
 */
export async function applyMegaEvolution(pokemonActor, megaData, chosenAbilities = {}) {
  const system = pokemonActor.system;

  const snapshot = {
    types: { ...system.types },
    abilities: Object.fromEntries(
      Object.entries(system.abilities).map(([key, ability]) => [key, ability.value])
    ),
    armorClass: system.armorClass.value,
    passiveAbilityActive: system.passiveAbility.active,
    size: system.size
  };

  const update = { [`flags.${FLAG_SCOPE}.${FLAG_KEY}`]: snapshot };

  if (megaData.types?.type1) {
    update["system.types.type1"] = megaData.types.type1;
    update["system.types.type2"] = megaData.types.type2 ?? null;
  }

  const deltas = { ...(megaData.abilityDeltas ?? {}) };
  for (const choice of megaData.abilityChoices ?? []) {
    const picked = chosenAbilities[choice.options.join("/")] ?? choice.options[0];
    deltas[picked] = (deltas[picked] ?? 0) + choice.delta;
  }
  for (const [key, delta] of Object.entries(deltas)) {
    const current = system.abilities[key]?.value ?? 10;
    update[`system.abilities.${key}.value`] = Math.min(current + delta, MAX_ABILITY_SCORE);
  }

  if (megaData.armorClassDelta) {
    update["system.armorClass.value"] = system.armorClass.value + megaData.armorClassDelta;
  }
  if (megaData.passiveAbility) update["system.passiveAbility.active"] = megaData.passiveAbility;
  if (megaData.size) update["system.size"] = megaData.size;

  return pokemonActor.update(update);
}

/** Reverte a Mega Evolução ao estado salvo em applyMegaEvolution (ex.: fim de combate). */
export async function revertMegaEvolution(pokemonActor) {
  const snapshot = pokemonActor.getFlag(FLAG_SCOPE, FLAG_KEY);
  if (!snapshot) return null;

  const update = {
    "system.types.type1": snapshot.types.type1,
    "system.types.type2": snapshot.types.type2,
    "system.armorClass.value": snapshot.armorClass,
    "system.passiveAbility.active": snapshot.passiveAbilityActive,
    "system.size": snapshot.size,
    [`flags.${FLAG_SCOPE}.-=${FLAG_KEY}`]: null
  };
  for (const [key, value] of Object.entries(snapshot.abilities)) {
    update[`system.abilities.${key}.value`] = value;
  }

  return pokemonActor.update(update);
}
