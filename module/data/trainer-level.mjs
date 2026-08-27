// Nível de Treinador (Livro de Regras, "Experiência do Treinador", pág. 33, Opção 1) — NÃO
// é acumulado por XP como o dnd5e nativo assume para Actors "character" (isso é a lógica
// de Pokémon, não a de Treinador). Aqui o nível vem da soma dos níveis dos N Pokémon mais
// fortes da equipe (N = Pokéslots do nível atual, tabela da pág. 20) comparada contra a
// tabela de níveis do Treinador — puramente informativo, sem subir de nível sozinho (mesma
// escolha já feita pro painel de XP dos Pokémon).
const MODULE_ID = "pokemon-mundo-perfeito";

// Soma mínima dos níveis dos Pokémon pra cada nível de Treinador (pág. 33, Opção 1).
export const TRAINER_LEVEL_TABLE = [
  { level: 2, sum: 3 }, { level: 3, sum: 6 }, { level: 4, sum: 9 }, { level: 5, sum: 12 },
  { level: 6, sum: 20 }, { level: 7, sum: 24 }, { level: 8, sum: 28 }, { level: 9, sum: 32 },
  { level: 10, sum: 36 }, { level: 11, sum: 50 }, { level: 12, sum: 55 }, { level: 13, sum: 60 },
  { level: 14, sum: 65 }, { level: 15, sum: 70 }, { level: 16, sum: 90 }, { level: 17, sum: 96 },
  { level: 18, sum: 102 }, { level: 19, sum: 108 }, { level: 20, sum: 114 }
];

// Pokéslots por nível de Treinador (pág. 20: 3 no nível 1, +1 nos níveis 5/10/15).
export function pokeslotsForLevel(level) {
  if (level >= 15) return 6;
  if (level >= 10) return 5;
  if (level >= 5) return 4;
  return 3;
}

export function trainerLevelForSum(sum) {
  let level = 1;
  for (const row of TRAINER_LEVEL_TABLE) {
    if (sum >= row.sum) level = row.level;
  }
  return level;
}

export function nextThreshold(level) {
  return TRAINER_LEVEL_TABLE.find((r) => r.level === level + 1) ?? null;
}

// Não existe um vínculo formal Treinador↔Pokémon neste módulo (cada Pokémon é um Actor
// avulso) — aproxima "time desse Treinador" pelos Pokémon do módulo que estão na MESMA
// pasta do diretório de Actors, a mesma convenção de organização já usada ao chocar um ovo
// (ver module/data/hatch-actor.mjs). Ordena do nível mais alto pro mais baixo, já que a
// regra soma os N mais fortes.
export function teamPokemonLevels(trainerActor) {
  const folderId = trainerActor.folder?.id ?? null;
  return game.actors
    .filter((a) => a.type === "npc" && a.getFlag(MODULE_ID, "species")
      && (a.folder?.id ?? null) === folderId)
    .map((a) => a.items.find((i) => i.type === "class")?.system?.levels ?? 1)
    .sort((a, b) => b - a);
}

export function computeTrainerLevelInfo(trainerActor) {
  const currentLevel = trainerActor.system?.details?.level ?? 1;
  const slots = pokeslotsForLevel(currentLevel);
  const teamLevels = teamPokemonLevels(trainerActor);
  const counted = teamLevels.slice(0, slots);
  const sum = counted.reduce((a, b) => a + b, 0);
  const indicatedLevel = trainerLevelForSum(sum);
  const next = nextThreshold(indicatedLevel);
  return { currentLevel, slots, teamLevels, counted, sum, indicatedLevel, next };
}
