// Uma nova versão do módulo só atualiza os COMPÊNDIOS — um Move que já foi copiado pra
// dentro de um Actor (ao chocar, capturar ou aprender via TM/Egg Move) fica congelado com os
// dados de quando foi copiado. É por isso que tipo/ícone/bônus de dano/área de Moves batidos
// numa versão anterior deste módulo não acompanham correções feitas depois — o compêndio já
// está certo, mas a cópia no Pokémon não. Esta função varre os Pokémon do mundo e corrige as
// cópias, comparando com o Move atual do compêndio "moves".
//
// Só mexe no que é dado "de regra" (tipo de dano, fórmula de bônus — incluindo STAB, já que
// o compêndio "moves" sozinho nunca carrega STAB, isso só existe nas cópias que nascem
// dentro de uma espécie da Pokédex — e template de área). NUNCA toca em "attack.ability"/
// "save.ability"/"save.dc.calculation": esse campo é intencionalmente editável pelo jogador
// (ver comentário em scripts/convert-to-dnd5e-native.py), então uma escolha que o jogador já
// tenha feito ali é preservada.
import { fetchMoveDocument } from "./move-pack.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const STAB_FORMULA = "floor((@details.level + 1) / 4)";

function actorTypes(actor) {
  const types = actor.getFlag(MODULE_ID, "species")?.types;
  const set = new Set();
  if (types?.type1) set.add(types.type1);
  if (types?.type2) set.add(types.type2);
  return set;
}

function patchActivities(currentActivities, freshActivities, stab) {
  let changed = false;
  for (const [id, freshAct] of Object.entries(freshActivities)) {
    const current = currentActivities[id];
    if (!current) continue; // activity foi reestruturada (raro) — fora do escopo do reparo automático

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

      let bonus = freshPart.bonus ?? "";
      if (stab && bonus.startsWith("@mod") && !bonus.includes(STAB_FORMULA)) bonus += ` + ${STAB_FORMULA}`;
      if (currentPart.bonus !== bonus) {
        currentPart.bonus = bonus;
        changed = true;
      }
    });

    if (freshAct.target?.template?.type
        && JSON.stringify(current.target) !== JSON.stringify(freshAct.target)) {
      current.target = foundry.utils.deepClone(freshAct.target);
      changed = true;
    }
  }
  return changed;
}

/**
 * @returns {Promise<{actorsTouched: number, movesTouched: number}|null>} null se quem chamou não é GM.
 */
export async function repairPokemonMoves() {
  if (!game.user.isGM) {
    ui.notifications.warn("Só o Mestre pode rodar o reparo de Moves.");
    return null;
  }

  let actorsTouched = 0;
  let movesTouched = 0;
  const cache = new Map();

  for (const actor of game.actors) {
    if (actor.type !== "npc" || !actor.getFlag(MODULE_ID, "species")) continue;
    const types = actorTypes(actor);
    let touchedHere = false;

    for (const item of Array.from(actor.items)) {
      const moveFlag = item.getFlag(MODULE_ID, "move");
      if (item.type !== "feat" || !moveFlag) continue;

      if (!cache.has(item.name)) cache.set(item.name, await fetchMoveDocument(item.name));
      const fresh = cache.get(item.name);
      if (!fresh) continue;

      const activities = foundry.utils.deepClone(item.toObject().system.activities ?? {});
      const stab = types.has(moveFlag.moveType);
      const changed = patchActivities(activities, fresh.toObject().system.activities ?? {}, stab);
      const imgChanged = Boolean(fresh.img) && fresh.img !== item.img;

      if (changed || imgChanged) {
        const update = { "system.activities": activities };
        if (imgChanged) update.img = fresh.img;
        await item.update(update);
        movesTouched++;
        touchedHere = true;
      }
    }
    if (touchedHere) actorsTouched++;
  }

  const message = movesTouched
    ? `Reparo concluído: ${movesTouched} Move(s) atualizado(s) em ${actorsTouched} Pokémon.`
    : "Nenhum Move precisava de reparo — tudo já está atualizado.";
  ui.notifications.info(message);
  return { actorsTouched, movesTouched };
}
