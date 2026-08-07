import { registerTypeConfig, TYPES } from "./combat/type-chart.mjs";
import * as capture from "./combat/capture.mjs";
import * as zMoves from "./combat/z-moves.mjs";
import * as megaEvolution from "./combat/mega-evolution.mjs";

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

  globalThis.game.pmp = { capture, zMoves, megaEvolution, TYPES };
});

Hooks.once("ready", () => {
  if (game.system.id !== "dnd5e") {
    ui.notifications.warn(game.i18n.localize("PMP.Warnings.RequiresDnd5e"));
  }
});
