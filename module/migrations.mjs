// Migrações dos Actors do MUNDO entre versões do módulo. Os compêndios são regerados a cada
// versão, mas um Pokémon já importado/chocado/capturado guarda uma cópia dos dados da versão
// em que entrou no mundo. Roda uma vez por mundo, só no cliente do Mestre, ao abrir o mundo;
// a versão já aplicada fica na configuração (oculta) "migrationVersion".
import { refreshStageEffects } from "./combat/status-stages.mjs";
import { repairPokemonMoves } from "./data/repair-moves.mjs";
import { fetchSpeciesDocumentBySlug } from "./data/pokedex-lookup.mjs";

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
  return {
    errors: report.errors,
    lines: [
      `${report.ac} com a CA passando a somar bônus (Evasão, Naturezas, Mega Evolução)`,
      `${report.stages} Mudança(s) de Status ativas recalculadas`,
      `${repair?.movesTouched ?? 0} Move(s) e ${repair?.abilitiesTouched ?? 0} Habilidade(s) sincronizados com os compêndios`
    ]
  };
}

/** v1.35.0 — Moves com modificador de CD no texto (-1 a -5) e áreas lidas da descrição. */
async function migrateTo2() {
  const repair = await repairPokemonMoves({ notify: false });
  return {
    errors: 0,
    lines: [`${repair?.movesTouched ?? 0} Move(s) com a CD do livro (ex.: "CD de Move -2") ou a área de efeito ajustadas`]
  };
}

const MOVEMENT_KEYS = ["walk", "swim", "fly", "climb", "burrow"];

/**
 * Deslocamento que a Pokédex ganhou: o leitor antigo parava na 1ª linha de "Deslocamento:" e
 * perdia natação/voo/escavação de 75 espécies e o "flutua" de 121. Só PREENCHE modo que está
 * em 0 no Actor (valor mexido à mão fica); Pokémon em Mega/Tera fica de fora, porque o
 * snapshot devolveria o deslocamento antigo ao reverter.
 */
function movementUpdate(actor, fresh) {
  if (actor.getFlag(MODULE_ID, "megaEvolutionSnapshot") || actor.getFlag(MODULE_ID, "terastalSnapshot")) return {};
  const current = actor._source.system?.attributes?.movement ?? {};
  const target = fresh._source.system?.attributes?.movement ?? {};
  const update = {};
  for (const key of MOVEMENT_KEYS) {
    if (!(current[key] > 0) && target[key] > 0) update[`system.attributes.movement.${key}`] = target[key];
  }
  if (target.hover && !current.hover) update["system.attributes.movement.hover"] = true;
  if (Object.keys(update).length) update[`flags.${MODULE_ID}.species.movement`] = fresh.getFlag(MODULE_ID, "species")?.movement;
  return update;
}

/**
 * Concessões de Moves dos níveis que o Pokémon AINDA não alcançou passam a ser as da Pokédex
 * (a releitura da tabela de níveis achou Moves que faltavam em 13 espécies). As dos níveis
 * já alcançados ficam: o que foi concedido já está na ficha.
 */
async function syncFutureGrants(actor, fresh) {
  const classItem = actor.items.find((i) => i.type === "class");
  const freshClass = fresh.items.find((i) => i.type === "class");
  if (!classItem || !freshClass) return false;
  const level = classItem.system.levels ?? 1;
  const isFuture = (a) => a.type === "ItemGrant" && a.level > level;
  const mine = classItem.toObject().system.advancement ?? [];
  const theirs = ((freshClass.toObject?.() ?? freshClass).system.advancement ?? []).filter(isFuture)
    .map((a) => ({ ...a, value: {} }));
  const comparable = (list) => JSON.stringify(list.map(({ value, ...rest }) => rest).sort((a, b) => a.level - b.level));
  if (comparable(mine.filter(isFuture)) === comparable(theirs)) return false;
  await classItem.update({ "system.advancement": [...mine.filter((a) => !isFuture(a)), ...theirs] });
  return true;
}

/**
 * v1.36.0 — correções do relatório do compêndio: Mega Pedras (dados e texto), Moves e
 * Habilidades sincronizados de novo, deslocamentos completos e Moves dos níveis futuros.
 */
async function migrateTo3() {
  const report = { movement: 0, grants: 0, errors: 0 };
  const cache = new Map();
  for (const actor of allPokemonActors()) {
    try {
      const slug = actor.getFlag(MODULE_ID, "species")?.species;
      if (!cache.has(slug)) cache.set(slug, await fetchSpeciesDocumentBySlug(slug));
      const fresh = cache.get(slug);
      if (!fresh) continue;
      const update = movementUpdate(actor, fresh);
      if (Object.keys(update).length) {
        await actor.update(update);
        report.movement++;
      }
      if (await syncFutureGrants(actor, fresh)) report.grants++;
    } catch (err) {
      report.errors++;
      console.error(`${MODULE_ID} | Falha ao migrar ${actor.name}`, err);
    }
  }
  const repair = await repairPokemonMoves({ notify: false });
  return {
    errors: report.errors,
    lines: [
      `${repair?.megasTouched ?? 0} Mega Pedra(s) com dados e texto do livro`,
      `${repair?.movesTouched ?? 0} Move(s) e ${repair?.abilitiesTouched ?? 0} Habilidade(s) sincronizados com os compêndios`,
      `${report.movement} Pokémon com deslocamento completado (natação, voo, flutuar...)`,
      `${report.grants} Pokémon com os Moves dos próximos níveis atualizados`
    ]
  };
}

const MIGRATIONS = [
  { version: 1, label: "v1.34.0", run: migrateTo1 },
  { version: 2, label: "v1.35.0", run: migrateTo2 },
  { version: 3, label: "v1.36.0", run: migrateTo3 }
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
        <ul>${report.lines.map((line) => `<li>${line}</li>`).join("")}</ul>
        ${report.errors ? `<p>⚠️ ${report.errors} Pokémon não puderam ser ajustados (veja o console, F12).</p>` : ""}`
    });
    await game.settings.set(MODULE_ID, SETTING, migration.version);
  }
}
