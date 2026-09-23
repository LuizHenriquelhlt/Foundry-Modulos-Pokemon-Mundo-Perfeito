// Clima (Livro de Regras, pág. 66): duas tabelas de d100 (Primavera/Verão e Outono/Inverno)
// pra sortear o clima do dia. Espelha packs/_source/regras (build-rules-journal.py,
// build_clima) — qualquer mudança nas tabelas deve ser feita nos dois lugares.
const SPRING_SUMMER = [
  { max: 25, name: "Sol Forte, Calmo", moves: "Grama, Terra, Fogo" },
  { max: 35, name: "Sol Forte, Ventoso", moves: "Grama, Terra, Fogo, Voador, Dragão, Psíquico" },
  { max: 65, name: "Nublado, Calmo", moves: "Normal, Pedra, Fada, Lutador, Venenoso" },
  { max: 75, name: "Nublado, Ventoso", moves: "Normal, Pedra, Fada, Lutador, Venenoso, Voador, Dragão, Psíquico" },
  { max: 80, name: "Nebuloso", moves: "Sombrio, Fantasma" },
  { max: 90, name: "Garoa Leve", moves: "Água, Elétrico, Inseto" },
  { max: 99, name: "Chuva Forte", moves: "Água, Elétrico, Inseto" },
  { max: 100, name: "Tempestade Perigosa", moves: "Água, Elétrico, Inseto" }
];

const FALL_WINTER = [
  { max: 15, name: "Sol Forte, Calmo", moves: "Grama, Terra, Fogo" },
  { max: 25, name: "Sol Forte, Ventoso", moves: "Grama, Terra, Fogo, Voador, Dragão, Psíquico" },
  { max: 40, name: "Nublado, Calmo", moves: "Normal, Pedra, Fada, Lutador, Venenoso" },
  { max: 50, name: "Nublado, Ventoso", moves: "Normal, Pedra, Fada, Lutador, Venenoso, Voador, Dragão, Psíquico" },
  { max: 60, name: "Nebuloso", moves: "Sombrio, Fantasma" },
  { max: 70, name: "Garoa Leve", moves: "Água, Elétrico, Inseto" },
  { max: 80, name: "Chuva Forte", moves: "Água, Elétrico, Inseto" },
  { max: 90, name: "Neve Leve", moves: "Gelo, Aço" },
  { max: 99, name: "Nevasca Forte", moves: "Gelo, Aço" },
  { max: 100, name: "Tempestade de Neve", moves: "Gelo, Aço" }
];

function pick(table, roll) {
  return table.find((entry) => roll <= entry.max) ?? table[table.length - 1];
}

async function rollWeather(table, seasonLabel) {
  const roll = new Roll("1d100");
  await roll.evaluate();
  const result = pick(table, roll.total);
  await roll.toMessage({
    flavor: `🌦️ Clima (${seasonLabel}) — <strong>${result.name}</strong><br/>
      <em>Moves com vantagem no dano: ${result.moves}</em>`
  });
  return result;
}

export function rollSpringSummer() {
  return rollWeather(SPRING_SUMMER, "Primavera/Verão");
}

export function rollFallWinter() {
  return rollWeather(FALL_WINTER, "Outono/Inverno");
}
