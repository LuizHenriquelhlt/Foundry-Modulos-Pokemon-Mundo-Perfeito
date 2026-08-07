import PokemonData from "./data/pokemon-actor.mjs";
import MoveData from "./data/move-item.mjs";
import PokemonActorSheet from "./sheets/pokemon-actor-sheet.mjs";
import MoveItemSheet from "./sheets/move-item-sheet.mjs";
import { registerTypeConfig, TYPES } from "./combat/type-chart.mjs";
import * as capture from "./combat/capture.mjs";
import * as zMoves from "./combat/z-moves.mjs";
import * as megaEvolution from "./combat/mega-evolution.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";

const ABILITY_LABELS = { str: "FOR", dex: "DES", con: "CON", int: "INT", wis: "SAB", cha: "CHA" };

const TYPE_LABELS = {
  normal: "Normal", fire: "Fogo", water: "Água", electric: "Elétrico", grass: "Grama", ice: "Gelo",
  fighting: "Lutador", poison: "Venenoso", ground: "Terrestre", flying: "Voador", psychic: "Psíquico",
  bug: "Inseto", rock: "Pedra", ghost: "Fantasma", dragon: "Dragão", dark: "Sombrio", steel: "Aço", fairy: "Fada"
};

Hooks.once("init", () => {
  console.log(`${MODULE_ID} | Inicializando`);

  CONFIG.Actor.dataModels["pokemon-mundo-perfeito.pokemon"] = PokemonData;
  CONFIG.Item.dataModels["pokemon-mundo-perfeito.move"] = MoveData;

  // Foundry v13+ moveu as coleções para foundry.documents.collections; os globais
  // antigos (Actors/Items) só existem até serem removidos de vez.
  const ActorsCollection = foundry.documents?.collections?.Actors ?? globalThis.Actors;
  const ItemsCollection = foundry.documents?.collections?.Items ?? globalThis.Items;

  ActorsCollection.registerSheet(MODULE_ID, PokemonActorSheet, {
    types: ["pokemon-mundo-perfeito.pokemon"],
    makeDefault: true,
    label: "Ficha de Pokémon"
  });
  ItemsCollection.registerSheet(MODULE_ID, MoveItemSheet, {
    types: ["pokemon-mundo-perfeito.move"],
    makeDefault: true,
    label: "Ficha de Move"
  });

  registerTypeConfig();
  CONFIG.PMP.abilityLabels = ABILITY_LABELS;
  CONFIG.PMP.typeLabels = TYPE_LABELS;

  Handlebars.registerHelper("eq", (a, b) => a === b);

  globalThis.game.pmp = { capture, zMoves, megaEvolution, TYPES };
});

Hooks.once("ready", () => {
  if (game.system.id !== "dnd5e") {
    ui.notifications.warn(game.i18n.localize("PMP.Warnings.RequiresDnd5e"));
  }
});
