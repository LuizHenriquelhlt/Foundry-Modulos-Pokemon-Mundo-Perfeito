import { registerTypeConfig, TYPES } from "./combat/type-chart.mjs";
import * as capture from "./combat/capture.mjs";
import * as zMoves from "./combat/z-moves.mjs";
import * as megaEvolution from "./combat/mega-evolution.mjs";
import { registerSheetExtras } from "./sheet-extras.mjs";
import { registerEggSheet } from "./apps/egg-sheet.mjs";
import { openCreateEggDialog } from "./apps/create-egg-dialog.mjs";

// Os Pokémon são Actors "npc" e os Moves são Items "feat" NATIVOS do dnd5e (com
// Activities), então rendem na ficha moderna do sistema sem nenhuma ficha custom —
// mesma arquitetura do módulo pokemon5e. Os dados específicos de PMP de cada
// documento (moveTable, TMs, SR, PP...) vivem em flags["pokemon-mundo-perfeito"].
const MODULE_ID = "pokemon-mundo-perfeito";

const ABILITY_LABELS = { str: "FOR", dex: "DES", con: "CON", int: "INT", wis: "SAB", cha: "CHA" };

const TYPE_LABELS = {
  normal: "Normal", fire: "Fogo", water: "Água", electric: "Elétrico", grass: "Grama", ice: "Gelo",
  fighting: "Lutador", poison: "Venenoso", ground: "Terrestre", flying: "Voador", psychic: "Psíquico",
  bug: "Inseto", rock: "Pedra", ghost: "Fantasma", dragon: "Dragão", dark: "Sombrio", steel: "Aço", fairy: "Fada"
};

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | Inicializando`);

  registerTypeConfig();
  CONFIG.PMP.abilityLabels = ABILITY_LABELS;
  CONFIG.PMP.typeLabels = TYPE_LABELS;
  registerSheetExtras();
  registerEggSheet();

  globalThis.game.pmp = { capture, zMoves, megaEvolution, TYPES, eggs: { openCreateEggDialog } };
});

Hooks.once("ready", async () => {
  if (game.system.id !== "dnd5e") {
    ui.notifications.warn(game.i18n.localize("PMP.Warnings.RequiresDnd5e"));
  }
  await ensureCreateEggMacro();
});

// Cria uma macro de conveniência pro Mestre abrir o diálogo de criação de ovo sem precisar
// decorar o comando — só roda uma vez (idempotente: não recria se já existir uma com o
// mesmo nome).
async function ensureCreateEggMacro() {
  if (!game.user.isGM) return;
  const name = "Criar Ovo Pokémon";
  if (game.macros.find((m) => m.name === name)) return;
  await Macro.create({
    name, type: "script", img: "icons/commodities/gems/pearl-storm.webp",
    command: "game.pmp.eggs.openCreateEggDialog();",
    flags: { [MODULE_ID]: { autoCreated: true } }
  });
}

// TM colocado na ficha de um Pokémon => o Pokémon aprende o Move automaticamente
// (o Move correspondente é copiado do compêndio, com fórmula/PP/atividade prontos).
Hooks.on("createItem", async (item, options, userId) => {
  if (game.user.id !== userId) return;
  const teaches = item.getFlag(MODULE_ID, "teachesMove");
  const actor = item.parent;
  if (!teaches || !actor || actor.documentName !== "Actor") return;

  if (actor.items.some((i) => i.name === teaches && i.id !== item.id)) {
    ui.notifications.info(`${actor.name} já conhece ${teaches}.`);
    return;
  }

  const pack = game.packs.get(`${MODULE_ID}.moves`);
  if (!pack) return;
  const index = await pack.getIndex();
  const entry = index.find((e) => e.name === teaches);
  if (!entry) {
    ui.notifications.warn(`Move "${teaches}" não encontrado no compêndio de Moves.`);
    return;
  }
  const move = await pack.getDocument(entry._id);
  const data = move.toObject();
  delete data._id;
  await actor.createEmbeddedDocuments("Item", [data]);
  ui.notifications.info(`${actor.name} aprendeu ${teaches} com ${item.name}!`);
});
