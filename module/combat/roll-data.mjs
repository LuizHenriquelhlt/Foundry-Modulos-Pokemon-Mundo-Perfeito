// Expõe o estágio atual de Ataque/Ataque Especial como "@pmpAtkStage"/"@pmpSpaStage" pras
// fórmulas de dano dos Moves (ver scripts/convert-to-dnd5e-native.py, damage_part["bonus"]).
// Não existe nenhum hook do dnd5e pra "actor acabou de montar o roll data" — o jeito seguro
// e amplamente usado por outros módulos pra isso é envolver Actor#getRollData uma vez no
// init, chamando a implementação original por dentro (em vez de reescrever do zero, o que
// quebraria "@mod"/"@prof"/etc. de todo o resto do sistema).
import { getStages } from "./status-stages.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";

export function registerRollDataExtension() {
  const ActorClass = CONFIG.Actor.documentClass;
  const original = ActorClass.prototype.getRollData;

  ActorClass.prototype.getRollData = function (options) {
    const data = original.call(this, options);
    // getRollData é chamado o tempo todo (qualquer fórmula do sistema, incluindo durante a
    // própria preparação de dados do Actor, antes de qualquer sheet ou HUD aparecer) — um
    // erro aqui dentro não pode vazar pra fora e quebrar esse cálculo pro resto do dnd5e.
    try {
      if (this.type === "npc" && this.getFlag(MODULE_ID, "species")) {
        const stages = getStages(this);
        data.pmpAtkStage = stages.atk;
        data.pmpSpaStage = stages.spa;
      }
    } catch (err) {
      console.error(`${MODULE_ID} | Falha ao calcular pmpAtkStage/pmpSpaStage`, err);
    }
    return data;
  };
}
