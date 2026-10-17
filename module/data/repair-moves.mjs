// Uma nova versão do módulo só atualiza os COMPÊNDIOS — um Move ou Habilidade que já foi
// copiado pra dentro de um Actor (ao chocar, capturar ou aprender via TM/Egg Move) fica
// congelado com os dados de quando foi copiado. Esta função varre os Pokémon do mundo e
// sincroniza essas cópias com o compêndio atual.
//
// Moves: sincroniza o que é dado "de regra" — nome (Moves renomeados por correção de
// extração), texto, PP máximo, tempo de execução, tipo de dano, fórmula de bônus (os Moves são
// "limpos" de propósito, só dado + modificador), template de área e modificador de CD do livro.
// NUNCA troca o atributo escolhido pelo jogador ("attack.ability", "save.ability" e o atributo
// da CD, ver scripts/convert-to-dnd5e-native.py) nem os usos já gastos.
// Habilidades: só preenche as cópias que ainda têm o texto-marcador "Regra completa não
// encontrada..." (Habilidades de Gen 8/9 antes da v1.34) — texto escrito à mão fica como está.
import { fetchMoveDocument } from "./move-pack.mjs";
import { fetchAbilityInfo } from "./abilities-lookup.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const ABILITY_STUB = "Regra completa não encontrada";
const ABILITY_KEYS = ["str", "dex", "con", "int", "wis", "cha"];

// Nome antigo (quebrado pela extração do PDF) -> nome atual no compêndio.
const RENAMED_MOVES = {
  "S urging Strikes": "Surging Strikes"
};

function patchActivities(currentActivities, freshActivities) {
  let changed = false;
  const currentList = Object.values(currentActivities);
  Object.values(freshActivities).forEach((freshAct, index) => {
    // por _id; se o Move foi renomeado os _id mudaram (são derivados do nome), então cai na
    // posição — Moves com mais de uma Activity sempre as listam na mesma ordem (ataque, teste)
    const current = currentActivities[freshAct._id]
      ?? (currentList[index]?.type === freshAct.type ? currentList[index] : null);
    if (!current) return; // activity foi reestruturada (raro) — fora do escopo do reparo automático

    const freshParts = freshAct.damage?.parts ?? [];
    const currentParts = current.damage?.parts ?? [];
    freshParts.forEach((freshPart, i) => {
      const currentPart = currentParts[i];
      if (!currentPart) return;

      const freshTypes = freshPart.types ?? [];
      if (JSON.stringify(currentPart.types ?? []) !== JSON.stringify(freshTypes)) {
        currentPart.types = freshTypes;
        changed = true;
      }

      const bonus = freshPart.bonus ?? "";
      if (currentPart.bonus !== bonus) {
        currentPart.bonus = bonus;
        changed = true;
      }
    });

    // CD com modificador do livro ("contra sua CD de Move -2"): no compêndio vira fórmula sobre
    // a CD do atributo (@abilities.<x>.dc - 2). Uma cópia antiga ainda no seletor de atributo
    // passa pra fórmula usando o atributo que o JOGADOR já tinha escolhido ali; uma cópia que já
    // está em fórmula (a do módulo ou uma escrita à mão) fica como está.
    const freshDc = freshAct.save?.dc;
    const currentDc = current.save?.dc;
    if (freshDc?.formula && !freshDc.calculation && currentDc?.calculation) {
      const chosen = ABILITY_KEYS.includes(currentDc.calculation) ? currentDc.calculation : null;
      const formula = chosen
        ? freshDc.formula.replace(/@abilities\.\w+\.dc/, `@abilities.${chosen}.dc`)
        : freshDc.formula;
      current.save.dc = { ...currentDc, calculation: "", formula };
      changed = true;
    }

    const activationType = freshAct.activation?.type;
    if (activationType && current.activation?.type !== activationType) {
      current.activation = { ...(current.activation ?? {}), type: activationType };
      changed = true;
    }

    if (freshAct.target?.template?.type
        && JSON.stringify(current.target) !== JSON.stringify(freshAct.target)) {
      current.target = foundry.utils.deepClone(freshAct.target);
      changed = true;
    }
  });
  return changed;
}

async function repairMoveItem(item, cache) {
  const freshName = RENAMED_MOVES[item.name] ?? item.name;
  if (!cache.has(freshName)) cache.set(freshName, await fetchMoveDocument(freshName));
  const fresh = cache.get(freshName);
  if (!fresh) return false;

  const source = item.toObject();
  const freshSource = fresh.toObject();
  const update = {};

  const activities = foundry.utils.deepClone(source.system.activities ?? {});
  if (patchActivities(activities, freshSource.system.activities ?? {})) update["system.activities"] = activities;
  if (freshName !== item.name) update.name = freshName;
  if (fresh.img && fresh.img !== item.img) update.img = fresh.img;
  for (const path of ["system.description.value", "system.requirements", "system.uses.max"]) {
    const value = foundry.utils.getProperty(freshSource, path);
    if (value !== undefined && value !== foundry.utils.getProperty(source, path)) update[path] = value;
  }
  const freshMove = freshSource.flags?.[MODULE_ID]?.move;
  if (freshMove && JSON.stringify(freshMove) !== JSON.stringify(source.flags?.[MODULE_ID]?.move)) {
    update[`flags.${MODULE_ID}.move`] = freshMove;
  }

  if (!Object.keys(update).length) return false;
  await item.update(update);
  return true;
}

/** Mega Pedra no inventário: dados mecânicos e descrição do compêndio "mega-evolutions"
 * (ex.: a Pinsirite antiga somava os bônus da Aerodactylite). Equipada/quantidade ficam. */
async function repairMegaStone(item, cache) {
  const key = `mega:${item.name}`;
  if (!cache.has(key)) {
    const pack = game.packs.get(`${MODULE_ID}.mega-evolutions`);
    const entry = pack ? (await pack.getIndex()).find((e) => e.name === item.name) : null;
    cache.set(key, entry ? await pack.getDocument(entry._id) : null);
  }
  const fresh = cache.get(key);
  if (!fresh) return false;
  const freshMega = fresh.getFlag(MODULE_ID, "mega");
  const update = {};
  if (JSON.stringify(freshMega) !== JSON.stringify(item.getFlag(MODULE_ID, "mega"))) {
    update[`flags.${MODULE_ID}.mega`] = freshMega;
  }
  if (fresh.system.description?.value !== item.system.description?.value) {
    update["system.description.value"] = fresh.system.description.value;
  }
  if (!Object.keys(update).length) return false;
  await item.update(update);
  return true;
}

async function repairAbilityItem(item) {
  const match = item.name.match(/^Habilidade (?:Passiva|Oculta|Mega): (.+)$/);
  if (!match || !item.system.description?.value?.includes(ABILITY_STUB)) return false;
  const info = await fetchAbilityInfo(match[1]);
  if (!info.description || info.description.includes(ABILITY_STUB)) return false;
  await item.update({ "system.description.value": info.description });
  return true;
}

/**
 * @param {object} [options]
 * @param {boolean} [options.notify=true] Mostra a notificação com o resumo no fim.
 * @returns {Promise<{actorsTouched: number, movesTouched: number, abilitiesTouched: number}|null>}
 *   null se quem chamou não é GM.
 */
export async function repairPokemonMoves({ notify = true } = {}) {
  if (!game.user.isGM) {
    ui.notifications.warn("Só o Mestre pode rodar o reparo de Moves.");
    return null;
  }

  let actorsTouched = 0;
  let movesTouched = 0;
  let abilitiesTouched = 0;
  let megasTouched = 0;
  const cache = new Map();

  for (const actor of game.actors) {
    // Mega Pedras também ficam no inventário de Treinadores (character), não só de Pokémon
    const isPokemon = actor.type === "npc" && actor.getFlag(MODULE_ID, "species");
    if (!isPokemon && actor.type !== "character") continue;
    let touchedHere = false;

    for (const item of Array.from(actor.items)) {
      if (item.getFlag(MODULE_ID, "mega")) {
        if (await repairMegaStone(item, cache)) {
          megasTouched++;
          touchedHere = true;
        }
        continue;
      }
      if (item.type !== "feat") continue;
      if (item.getFlag(MODULE_ID, "move")) {
        if (await repairMoveItem(item, cache)) {
          movesTouched++;
          touchedHere = true;
        }
      } else if (await repairAbilityItem(item)) {
        abilitiesTouched++;
        touchedHere = true;
      }
    }
    if (touchedHere) actorsTouched++;
  }
  // Mega Pedras soltas no diretório de Itens do mundo
  for (const item of game.items ?? []) {
    if (item.getFlag(MODULE_ID, "mega") && await repairMegaStone(item, cache)) megasTouched++;
  }

  if (notify) {
    const message = movesTouched || abilitiesTouched || megasTouched
      ? `Reparo concluído: ${movesTouched} Move(s), ${abilitiesTouched} Habilidade(s) e ${megasTouched} Mega Pedra(s) atualizados em ${actorsTouched} ficha(s).`
      : "Nenhum Move, Habilidade ou Mega Pedra precisava de reparo — tudo já está atualizado.";
    ui.notifications.info(message);
  }
  return { actorsTouched, movesTouched, abilitiesTouched, megasTouched };
}
