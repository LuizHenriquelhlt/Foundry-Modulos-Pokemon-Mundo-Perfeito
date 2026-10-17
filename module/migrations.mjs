// Migrações dos Actors do MUNDO entre versões do módulo. Os compêndios são regerados a cada
// versão, mas um Pokémon já importado/chocado/capturado guarda uma cópia dos dados da versão
// em que entrou no mundo. Roda uma vez por mundo, só no cliente do Mestre, ao abrir o mundo;
// a versão já aplicada fica na configuração (oculta) "migrationVersion".
import { refreshStageEffects } from "./combat/status-stages.mjs";
import { repairPokemonMoves } from "./data/repair-moves.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const SETTING = "migrationVersion";

export function registerMigrationSettings() {
  game.settings.register(MODULE_ID, SETTING, {
    scope: "world", config: false, type: Number, default: 0
  });
}

function isPokemon(actor) {
  return actor?.type === "npc" && !!actor.getFlag(MODULE_ID, "species");
}

/** Pokémon do diretório de Actors + os de tokens NÃO vinculados nas cenas (Actor sintético). */
function allPokemonActors() {
  const actors = game.actors.filter(isPokemon);
  for (const scene of game.scenes) {
    for (const token of scene.tokens) {
      if (!token.actorLink && isPokemon(token.actor)) actors.push(token.actor);
    }
  }
  return actors;
}

/**
 * v1.34.0 — CA no modo "natural" (o "flat" do dnd5e 5.3.3 ignora ac.bonus: Evasão, Naturezas
 * Astuto/Tímido e o bônus de CA da Mega Evolução não faziam efeito), estágios ativos
 * recalculados (Precisão na CD, Velocidade só nos deslocamentos existentes) e Moves/Habilidades
 * sincronizados com os compêndios (texto de Gen 8/9, Obstruct/Burning Bulwark como reação,
 * Surging Strikes renomeado).
 */
async function migrateTo1() {
  const report = { ac: 0, stages: 0, errors: 0 };
  for (const actor of allPokemonActors()) {
    try {
      if (actor._source.system?.attributes?.ac?.calc === "flat") {
        await actor.update({ "system.attributes.ac.calc": "natural" });
        report.ac++;
      }
      report.stages += await refreshStageEffects(actor);
    } catch (err) {
      report.errors++;
      console.error(`${MODULE_ID} | Falha ao migrar ${actor.name}`, err);
    }
  }
  const repair = await repairPokemonMoves({ notify: false });
  return { ...report, moves: repair?.movesTouched ?? 0, abilities: repair?.abilitiesTouched ?? 0 };
}

const MIGRATIONS = [
  { version: 1, label: "v1.34.0", run: migrateTo1 }
];

export async function runMigrations() {
  if (!game.user.isGM) return;
  const applied = game.settings.get(MODULE_ID, SETTING) ?? 0;
  const pending = MIGRATIONS.filter((m) => m.version > applied);
  if (!pending.length) return;

  for (const migration of pending) {
    ui.notifications.info(`Pokémon Mundo Perfeito: atualizando os Pokémon do mundo (${migration.label})...`);
    const report = await migration.run();
    console.log(`${MODULE_ID} | Migração ${migration.label}`, report);
    ChatMessage.create({
      whisper: [game.user.id],
      speaker: { alias: "Pokémon Mundo Perfeito" },
      content: `<p><strong>Módulo atualizado (${migration.label}).</strong> Pokémon do mundo ajustados:</p>
        <ul>
          <li>${report.ac} com a CA passando a somar bônus (Evasão, Naturezas, Mega Evolução)</li>
          <li>${report.stages} Mudança(s) de Status ativas recalculadas</li>
          <li>${report.moves} Move(s) e ${report.abilities} Habilidade(s) sincronizados com os compêndios</li>
        </ul>
        ${report.errors ? `<p>⚠️ ${report.errors} Pokémon não puderam ser ajustados (veja o console, F12).</p>` : ""}`
    });
    await game.settings.set(MODULE_ID, SETTING, migration.version);
  }
}
