/**
 * Pokémon type effectiveness (Gen 6+ chart, 18 types incl. Fairy — matches Gen 1-9 coverage of PMP).
 *
 * Kept as our own CONFIG.PMP.types namespace rather than remapped onto CONFIG.DND5E.damageTypes:
 * dnd5e's damage types (acid, bludgeoning, fire, ...) are a fixed, differently-shaped set used by
 * every other dnd5e module/system content in the same world. Overwriting it with 18 Pokémon types
 * would corrupt damage typing for anything non-Pokémon sharing the world. Instead, type effectiveness
 * is applied explicitly when resolving a Move's damage (see combat/moves.mjs, added in a later phase).
 */

export const TYPES = [
  "normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison",
  "ground", "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy"
];

/** attacker type -> { defenderType: multiplier }. Omitted pairs default to 1 (neutral). */
export const EFFECTIVENESS = {
  normal: { rock: 0.5, ghost: 0, steel: 0.5 },
  fire: { fire: 0.5, water: 0.5, grass: 2, ice: 2, bug: 2, rock: 0.5, dragon: 0.5, steel: 2 },
  water: { fire: 2, water: 0.5, grass: 0.5, ground: 2, rock: 2, dragon: 0.5 },
  electric: { water: 2, electric: 0.5, grass: 0.5, ground: 0, flying: 2, dragon: 0.5 },
  grass: { fire: 0.5, water: 2, grass: 0.5, poison: 0.5, ground: 2, flying: 0.5, bug: 0.5, rock: 2, dragon: 0.5, steel: 0.5 },
  ice: { fire: 0.5, water: 0.5, grass: 2, ice: 0.5, ground: 2, flying: 2, dragon: 2, steel: 0.5 },
  fighting: { normal: 2, ice: 2, poison: 0.5, flying: 0.5, psychic: 0.5, bug: 0.5, rock: 2, ghost: 0, dark: 2, steel: 2, fairy: 0.5 },
  poison: { grass: 2, poison: 0.5, ground: 0.5, rock: 0.5, ghost: 0.5, steel: 0, fairy: 2 },
  ground: { fire: 2, electric: 2, grass: 0.5, poison: 2, flying: 0, bug: 0.5, rock: 2, steel: 2 },
  flying: { electric: 0.5, grass: 2, fighting: 2, bug: 2, rock: 0.5, steel: 0.5 },
  psychic: { fighting: 2, poison: 2, psychic: 0.5, dark: 0, steel: 0.5 },
  bug: { fire: 0.5, grass: 2, fighting: 0.5, poison: 0.5, flying: 0.5, psychic: 2, ghost: 0.5, dark: 2, steel: 0.5, fairy: 0.5 },
  rock: { fire: 2, ice: 2, fighting: 0.5, ground: 0.5, flying: 2, bug: 2, steel: 0.5 },
  ghost: { normal: 0, psychic: 2, ghost: 2, dark: 0.5 },
  dragon: { dragon: 2, steel: 0.5, fairy: 0 },
  dark: { fighting: 0.5, psychic: 2, ghost: 2, dark: 0.5, fairy: 0.5 },
  steel: { fire: 0.5, water: 0.5, electric: 0.5, ice: 2, rock: 2, steel: 0.5, fairy: 2 },
  fairy: { fire: 0.5, fighting: 2, poison: 0.5, dragon: 2, dark: 2, steel: 0.5 }
};

/**
 * @param {string} attackType Type of the incoming Move.
 * @param {string} defenderType1 Defender's primary type.
 * @param {string|null} [defenderType2] Defender's secondary type, if any.
 * @returns {number} Combined multiplier (0, 0.25, 0.5, 1, 2, or 4).
 */
export function getTypeMultiplier(attackType, defenderType1, defenderType2 = null) {
  const table = EFFECTIVENESS[attackType] ?? {};
  const m1 = table[defenderType1] ?? 1;
  const m2 = defenderType2 ? table[defenderType2] ?? 1 : 1;
  return m1 * m2;
}

export function registerTypeConfig() {
  const CONFIG_PMP = (globalThis.CONFIG.PMP ??= {});
  CONFIG_PMP.types = TYPES;
  CONFIG_PMP.typeEffectiveness = EFFECTIVENESS;
  CONFIG_PMP.getTypeMultiplier = getTypeMultiplier;
}
