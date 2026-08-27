/**
 * Pokémon type effectiveness (Gen 6+ chart, 18 types incl. Fairy — matches Gen 1-9 coverage of PMP).
 *
 * O cálculo de efetividade (getTypeMultiplier) usa nosso próprio CONFIG.PMP.types/typeEffectiveness,
 * não os 13 tipos de dano nativos do dnd5e (acid, bludgeoning, fire...) — a tabela de efetividade
 * Pokémon (fraquezas x4, imunidades, etc.) não tem equivalente no sistema padrão de resistência do
 * dnd5e, então essa conta continua sendo feita à parte na resolução do dano do Move.
 *
 * Só o REGISTRO de cada tipo em CONFIG.DND5E.damageTypes (registerDamageTypes) usa o dnd5e nativo —
 * necessário pra Moves conseguirem marcar seu "types" na Activity de dano (aparece no dropdown da
 * própria ficha do Move, mostra o ícone certo na aba de Ataques). Cada tipo usa uma chave própria
 * com prefixo "pmp" (pmpFire, pmpWater, ...) em vez de reaproveitar os 3 nomes que colidem com tipos
 * nativos do D&D (fire/poison/psychic) — mantém todos os 18 tipos com o mesmo padrão de chave, e
 * evita que Resistência a Fogo/Veneno/Psíquico de conteúdo não-Pokémon afete Moves Pokémon por
 * engano (o inverso também: fraqueza a Fogo de um Pokémon não empresta a semântica de dano de fogo
 * do D&D). Mesmo padrão do módulo "(pk5e)" que já convive no mesmo mundo (prefixa os tipos dele
 * também), então os dois aparecem lado a lado no dropdown sem se confundir.
 */

export const TYPES = [
  "normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison",
  "ground", "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy"
];

export const TYPE_LABELS = {
  normal: "Normal", fire: "Fogo", water: "Água", electric: "Elétrico", grass: "Grama", ice: "Gelo",
  fighting: "Lutador", poison: "Venenoso", ground: "Terrestre", flying: "Voador", psychic: "Psíquico",
  bug: "Inseto", rock: "Pedra", ghost: "Fantasma", dragon: "Dragão", dark: "Sombrio", steel: "Aço", fairy: "Fada"
};

/** "fire" -> "pmpFire" — chave usada em CONFIG.DND5E.damageTypes e em damage.parts[].types dos Moves. */
export function damageTypeKey(type) {
  return `pmp${type.charAt(0).toUpperCase()}${type.slice(1)}`;
}

export function registerDamageTypes() {
  for (const type of TYPES) {
    globalThis.CONFIG.DND5E.damageTypes[damageTypeKey(type)] = {
      label: `PMP: ${TYPE_LABELS[type]}`,
      icon: `modules/pokemon-mundo-perfeito/assets/types/${type}.svg`
    };
  }
}

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
  CONFIG_PMP.typeLabels = TYPE_LABELS;
  CONFIG_PMP.typeEffectiveness = EFFECTIVENESS;
  CONFIG_PMP.getTypeMultiplier = getTypeMultiplier;
  registerDamageTypes();
}
