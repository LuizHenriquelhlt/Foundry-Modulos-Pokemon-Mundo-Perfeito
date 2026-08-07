/**
 * Tabela geral de dano de Z-Move (Livro de Z-Moves, seção "Dano"), verificada campo a campo
 * contra o PDF fonte (pdfplumber extract_tables, ver scripts/parse-z-move-exceptions.py).
 * Chave = dado base do Move, valor = dado do Z-Move correspondente.
 */
export const BASE_DAMAGE_TO_Z_MOVE = {
  "1d4": "5d10", "2d4": "5d10", "3d4": "5d10", "4d4": "5d10",
  "1d6": "5d10", "2d6": "5d10", "3d6": "5d10", "4d6": "5d10", "5d6": "6d10", "6d6": "7d10",
  "1d8": "5d10", "2d8": "5d10", "3d8": "5d10", "4d8": "6d10", "5d8": "8d10", "6d8": "9d10",
  "7d8": "9d10", "8d8": "8d12",
  "1d10": "5d10", "2d10": "5d10", "3d10": "5d10", "4d10": "8d10", "5d10": "9d10",
  "6d10": "8d12", "7d10": "10d10", "8d10": "10d10", "9d10": "10d10", "10d10": "10d10", "12d10": "10d10",
  "1d12": "5d10", "2d12": "5d10", "3d12": "7d10", "4d12": "9d10", "6d12": "10d10",
  "7d12": "10d10", "8d12": "10d10", "9d12": "10d10",
  "1d20": "5d10", "2d20": "8d10", "4d20": "10d10"
};

/**
 * Moves com tabela de dano por nível própria em vez da tabela geral acima (Livro de
 * Z-Moves, "Os seguintes Moves não seguem a tabela acima como base"). Chave = nome do
 * Move, valor = dano do Z-Move por nível do usuário do Move (1/5/10/17). Extraído por
 * grade de tabela (pdfplumber), 55 Moves — lista completa, sem pendências.
 */
export const SPECIAL_CASE_TABLE = {
  "Beat Up": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Bide": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Bone Rush": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Bullet Seed": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Core Enforcer": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Counter": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Crush Grip": { 1: "2d20", 5: "7d8", 10: "4d20", 17: "8d12" },
  "Double Hit": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Dragon Rage": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Electro Ball": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Endeavor": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Final Gambit": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Fissure": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Flail": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Fling": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Flying Press": { 1: "3d12", 5: "7d8", 10: "7d10", 17: "9d10" },
  "Frustration": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Gear Grind": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Grass Knot": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Guillotine": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Gyro Ball": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Heat Crash": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Heavy Slam": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Hex": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Horn Drill": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Icicle Spear": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Land's Wrath": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Low Kick": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Luster Purge": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Magnitude": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Mega Drain": { 1: "3d8", 5: "6d6", 10: "6d8", 17: "6d10" },
  "Metal Burst": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Mirror Coat": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Mist Ball": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Multi-Attack": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Natural Gift": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Nature's Madness": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Night Shade": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Pin Missile": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Power Trip": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Present": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Psywave": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Punishment": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Return": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Reversal": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Seismic Toss": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Sheer Cold": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Sonic Boom": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Spit Up": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Stored Power": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Super Fang": { 1: "2d10", 5: "5d6", 10: "5d8", 17: "5d10" },
  "Tail Slap": { 1: "3d10", 5: "4d10", 10: "7d8", 17: "7d10" },
  "Thousand Arrows": { 1: "6d6", 5: "7d8", 10: "6d12", 17: "9d10" },
  "Triple Kick": { 1: "3d8", 5: "6d6", 10: "6d8", 17: "6d10" },
  "Trump Card": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "V-create": { 1: "5d8", 5: "8d8", 10: "7d12", 17: "9d12" },
  "Weather Ball": { 1: "4d8", 5: "4d12", 10: "8d8", 17: "8d10" },
  "Wring Out": { 1: "2d20", 5: "7d8", 10: "4d20", 17: "8d12" }
};

/**
 * @param {string} baseFormula Dado de dano do Move base (ex.: "2d6"). Ignorado para Moves
 *   na SPECIAL_CASE_TABLE, que usam o próprio nível do usuário em vez do dado base.
 * @param {string} [moveName] Nome do Move.
 * @param {number} [userLevel] Nível do Pokémon que usa o Move (necessário para os 55 Moves
 *   com tabela própria; usa o tier igual ou mais alto disponível que não exceda o nível).
 * @returns {{formula: string|null, needsManualLookup: boolean}}
 */
export function resolveZMoveDamage(baseFormula, moveName, userLevel = 1) {
  const special = moveName ? SPECIAL_CASE_TABLE[moveName] : null;
  if (special) {
    const tier = [17, 10, 5, 1].find((lvl) => userLevel >= lvl) ?? 1;
    return { formula: special[tier], needsManualLookup: false };
  }
  const formula = BASE_DAMAGE_TO_Z_MOVE[baseFormula] ?? null;
  return { formula, needsManualLookup: formula === null };
}
