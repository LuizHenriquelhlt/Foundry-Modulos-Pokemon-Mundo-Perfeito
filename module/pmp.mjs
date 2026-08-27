import { registerTypeConfig, TYPES } from "./combat/type-chart.mjs";
import * as capture from "./combat/capture.mjs";
import * as zMoves from "./combat/z-moves.mjs";
import * as megaEvolution from "./combat/mega-evolution.mjs";
import { registerSheetExtras } from "./sheet-extras.mjs";
import { registerEggSheet } from "./apps/egg-sheet.mjs";
import { openCreateEggDialog } from "./apps/create-egg-dialog.mjs";
import { openEggRollLog, refreshEggRollLogIfOpen } from "./apps/egg-roll-log.mjs";
import { registerStatusEffects } from "./combat/status-stages.mjs";
import { learnMove } from "./data/move-pack.mjs";

// Os Pokémon são Actors "npc" e os Moves são Items "feat" NATIVOS do dnd5e (com
// Activities), então rendem na ficha moderna do sistema sem nenhuma ficha custom —
// mesma arquitetura do módulo pokemon5e. Os dados específicos de PMP de cada
// documento (moveTable, TMs, SR, PP...) vivem em flags["pokemon-mundo-perfeito"].
const MODULE_ID = "pokemon-mundo-perfeito";

const ABILITY_LABELS = { str: "FOR", dex: "DES", con: "CON", int: "INT", wis: "SAB", cha: "CHA" };

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | Inicializando`);

  registerTypeConfig();
  CONFIG.PMP.abilityLabels = ABILITY_LABELS;
  registerSheetExtras();
  registerEggSheet();
  registerStatusEffects();

  globalThis.game.pmp = {
    capture, zMoves, megaEvolution, TYPES,
    eggs: { openCreateEggDialog, openRollLog: openEggRollLog }
  };
});

Hooks.once("ready", async () => {
  if (game.system.id !== "dnd5e") {
    ui.notifications.warn(game.i18n.localize("PMP.Warnings.RequiresDnd5e"));
  }
  await ensureMacro("Criar Ovo Pokémon", "game.pmp.eggs.openCreateEggDialog();");
  await ensureMacro("Log de Incubação de Ovos", "game.pmp.eggs.openRollLog();");
});

// Cria uma macro de conveniência pro Mestre sem precisar decorar o comando — só roda uma
// vez (idempotente: não recria se já existir uma com o mesmo nome).
async function ensureMacro(name, command) {
  if (!game.user.isGM) return;
  if (game.macros.find((m) => m.name === name)) return;
  await Macro.create({
    name, type: "script", img: "icons/commodities/gems/pearl-storm.webp", command,
    flags: { [MODULE_ID]: { autoCreated: true } }
  });
}

// Mantém o Log de Rolagens de Incubação (se estiver aberto) sincronizado sempre que
// qualquer ovo do mundo muda — sem isso, o Mestre precisaria fechar e abrir de novo depois
// de cada rolagem pra ver a linha nova.
Hooks.on("updateItem", (item) => {
  if (item.getFlag(MODULE_ID, "egg")) refreshEggRollLogIfOpen();
});

// TM colocado na ficha de um Pokémon => o Pokémon aprende o Move automaticamente
// (o Move correspondente é copiado do compêndio, com fórmula/PP/atividade prontos).
Hooks.on("createItem", async (item, options, userId) => {
  if (game.user.id !== userId) return;
  const teaches = item.getFlag(MODULE_ID, "teachesMove");
  const actor = item.parent;
  if (!teaches || !actor || actor.documentName !== "Actor") return;

  const result = await learnMove(actor, teaches);
  if (result === "already-known") {
    ui.notifications.info(`${actor.name} já conhece ${teaches}.`);
  } else if (result === "not-found") {
    ui.notifications.warn(`Move "${teaches}" não encontrado no compêndio de Moves.`);
  } else {
    ui.notifications.info(`${actor.name} aprendeu ${teaches} com ${item.name}!`);
  }
});
