// Evolução (Livro de Regras — compêndio "Regras" > "Evolução", 7 passos). O Pokémon já é
// um Actor "npc" nativo do dnd5e (ver sheet-extras.mjs) — evoluir significa trocar o bloco
// de estatísticas pelo da nova espécie, mantendo o que o jogador já construiu: nível, Moves
// conhecidos (só a lista de Moves FUTUROS muda), Shiny, e o histórico de Dado de Vida/PV já
// gasto. O requisito em si (nível, pedra, troca, Lealdade, dia/noite etc.) está descrito em
// texto livre no campo "evolution" de cada espécie — variado demais pra validar sozinho de
// forma confiável (Eevee sozinho tem 8 caminhos diferentes) — por isso a ferramenta sugere
// candidatos lendo esse texto, mas quem decide se o requisito foi cumprido continua sendo
// o jogador/Mestre na mesa.
import { fetchSpeciesDocument, findSpeciesIndexEntry } from "./pokedex-lookup.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const ABILITY_KEYS = ["str", "dex", "con", "int", "wis", "cha"];

function pokedexPack() {
  return game.packs.get(`${MODULE_ID}.pokedex`);
}

export async function listSpeciesNames() {
  const pack = pokedexPack();
  if (!pack) return [];
  const index = await pack.getIndex();
  return [...index.map((e) => e.name)].sort((a, b) => a.localeCompare(b, "pt-BR"));
}

function pokemonLevel(actor) {
  const classItem = actor.items.find((i) => i.type === "class");
  return classItem?.system?.levels ?? 1;
}

/**
 * Lê o campo de texto livre "evolution" da espécie atual e sugere candidatos comparando
 * contra os nomes reais da Pokédex — cobre tanto o caso linear (Charmander → só bate com
 * "Charmeleon") quanto o ramificado (Eevee → bate com Vaporeon/Jolteon/Flareon/...). Não é
 * garantia de acerto (nomes ambíguos, erros de digitação no texto-fonte etc.) — por isso o
 * diálogo sempre deixa escolher qualquer espécie manualmente também.
 * @returns {Promise<string[]>}
 */
export async function suggestEvolutionCandidates(actor) {
  const species = actor.getFlag(MODULE_ID, "species");
  const text = species?.evolution ?? "";
  const ownName = species?.species ?? "";
  if (!text) return [];

  const pack = pokedexPack();
  if (!pack) return [];
  const index = await pack.getIndex();
  const candidates = index
    .map((e) => e.name)
    .filter((name) => name !== ownName && text.includes(name));

  // Nomes mais longos primeiro (ex.: "Raichu de Alola" antes de "Raichu", já que o texto
  // normalmente contém os dois — sem isso "Raichu" apareceria duas vezes na prática).
  candidates.sort((a, b) => b.length - a.length);
  return [...new Set(candidates)];
}

/** Estágio atual/máximo da espécie — usado só pra decidir se mostra o botão "Evoluir". */
export function canStillEvolve(actor) {
  const stage = actor.getFlag(MODULE_ID, "species")?.evolutionStage;
  if (!stage) return false;
  return stage.current < stage.max;
}

function abilityDelta(oldSpecies, key) {
  let delta = oldSpecies?.evs?.[key] ?? 0;
  if (oldSpecies?.nature?.increased === key) delta += 2;
  if (oldSpecies?.nature?.decreased === key) delta -= 2;
  return delta;
}

function cloneItemPlain(item) {
  const data = item.toObject ? item.toObject() : foundry.utils.deepClone(item);
  delete data._id;
  delete data._key;
  return data;
}

/**
 * Executa a transformação mecânica dos 7 passos da regra de Evolução sobre um Actor já
 * existente (não cria um novo — o jogador continua com a mesma ficha/token/posse).
 * @param {Actor} actor Pokémon (Actor "npc" com flags.species) que vai evoluir.
 * @param {string} targetSpeciesName Nome exato da nova espécie na Pokédex.
 * @returns {Promise<{status:"evolved", from:string, to:string, hpBonus:number, passiveKept:boolean, passiveOptions:string[]}|{status:"species-not-found"|"not-a-pokemon"}>}
 */
export async function evolveActor(actor, targetSpeciesName) {
  if (actor?.type !== "npc" || !actor.getFlag(MODULE_ID, "species")) return { status: "not-a-pokemon" };

  const targetIndexEntry = await findSpeciesIndexEntry(targetSpeciesName);
  const targetDoc = targetIndexEntry ? await fetchSpeciesDocument(targetSpeciesName) : null;
  if (!targetDoc) return { status: "species-not-found" };

  const oldSpecies = actor.getFlag(MODULE_ID, "species");
  const targetFlags = targetDoc.flags?.[MODULE_ID]?.species ?? {};
  const targetSys = targetDoc.system;
  const level = pokemonLevel(actor);
  const hpBonus = level * 2;

  // Passo 1: atributos base da nova forma + EVs/Natureza já investidos no indivíduo.
  const abilities = {};
  for (const key of ABILITY_KEYS) {
    const base = targetSys.abilities?.[key]?.value ?? 10;
    abilities[key] = { value: Math.max(1, base + abilityDelta(oldSpecies, key)) };
  }

  // Passo 5: mantém a Habilidade Passiva atual se a nova forma também a tiver disponível;
  // senão, troca pra primeira opção da nova forma (o jogador pode trocar depois arrastando
  // outra opção do compêndio, se a nova forma tiver mais de uma).
  const targetPassiveOptions = targetFlags.passiveAbility?.options ?? [];
  const currentPassive = oldSpecies.passiveAbility?.active ?? "";
  const passiveKept = targetPassiveOptions.includes(currentPassive);
  const newPassiveActive = passiveKept ? currentPassive
    : (targetFlags.passiveAbility?.active || targetPassiveOptions[0] || "");

  const newSpeciesFlag = {
    ...targetFlags,
    // Traços do INDIVÍDUO, não da espécie — preservados através da evolução.
    shiny: oldSpecies.shiny ?? false,
    nature: oldSpecies.nature ?? targetFlags.nature,
    evs: oldSpecies.evs ?? targetFlags.evs,
    passiveAbility: { options: targetPassiveOptions, active: newPassiveActive }
  };

  const rawHp = actor._source.system.attributes.hp;
  const wasAutoNamed = actor.name === oldSpecies.species;

  const update = {
    "system.abilities": abilities,
    "system.attributes.ac": foundry.utils.deepClone(targetSys.attributes.ac),
    "system.attributes.movement": foundry.utils.deepClone(targetSys.attributes.movement),
    "system.attributes.senses": foundry.utils.deepClone(targetSys.attributes.senses),
    // Passos 2+3: PV do nível atual e Dado de Vida já gastos ficam como estão — só soma o
    // bônus de evolução agora e troca o Dado de Vida usado a partir do PRÓXIMO nível.
    "system.attributes.hp.formula": targetSys.attributes.hp.formula,
    "system.attributes.hp.max": (rawHp?.max ?? 0) + hpBonus,
    "system.attributes.hp.value": (rawHp?.value ?? 0) + hpBonus,
    // Passo 4: CA base, proficiências (perícias) e vulnerabilidades/resistências/imunidades.
    "system.traits": foundry.utils.deepClone(targetSys.traits),
    "system.skills": foundry.utils.deepClone(targetSys.skills),
    "system.details.type": foundry.utils.deepClone(targetSys.details.type),
    "system.details.cr": targetSys.details.cr,
    "system.details.biography": foundry.utils.deepClone(targetSys.details.biography),
    img: targetDoc.img,
    [`flags.${MODULE_ID}.species`]: newSpeciesFlag
  };
  if (targetDoc.prototypeToken?.texture?.src) {
    update["prototypeToken.texture.src"] = targetDoc.prototypeToken.texture.src;
  }
  if (wasAutoNamed) update.name = targetFlags.species || targetDoc.name;

  const evolutionLog = actor.getFlag(MODULE_ID, "evolutionHistory") ?? [];
  update[`flags.${MODULE_ID}.evolutionHistory`] = [
    ...evolutionLog,
    { from: oldSpecies.species, to: targetFlags.species, level, date: Date.now() }
  ];

  await actor.update(update);

  // Passo 6: os Moves já conhecidos (itens "feat" com o nome do Move) e o "Struggle" não são
  // tocados — só a lista de Moves FUTUROS muda, e isso já acontece sozinho porque
  // flags.species (moveTable/knownMoves/tms) acima passou a ser o da nova espécie.
  const toDelete = [];
  const toCreate = [];
  for (const item of actor.items) {
    if (item.type !== "feat") continue;
    if (item.name.startsWith("Tipo ")) toDelete.push(item.id);
    else if (item.name.startsWith("Habilidade Oculta: ")) toDelete.push(item.id);
    else if (!passiveKept && item.name.startsWith("Habilidade Passiva: ")) toDelete.push(item.id);
  }
  for (const targetItem of targetDoc.items) {
    if (targetItem.type !== "feat") continue;
    const isType = targetItem.name.startsWith("Tipo ");
    const isHidden = targetItem.name.startsWith("Habilidade Oculta: ");
    const isNewPassive = !passiveKept && targetItem.name === `Habilidade Passiva: ${newPassiveActive}`;
    if (isType || isHidden || isNewPassive) toCreate.push(cloneItemPlain(targetItem));
  }
  if (toDelete.length) await actor.deleteEmbeddedDocuments("Item", toDelete);
  if (toCreate.length) await actor.createEmbeddedDocuments("Item", toCreate);

  const classItem = actor.items.find((i) => i.type === "class");
  const targetClassItem = targetDoc.items.find((i) => i.type === "class");
  if (classItem && targetClassItem) {
    await actor.updateEmbeddedDocuments("Item", [{
      _id: classItem.id,
      name: targetClassItem.name,
      "system.hd.denomination": targetClassItem.system.hd.denomination
    }]);
  }

  if (actor.sheet?.rendered) actor.sheet.render(false);

  const passiveNote = passiveKept
    ? `Manteve a Habilidade Passiva <strong>${currentPassive}</strong>.`
    : `Habilidade Passiva trocada para <strong>${newPassiveActive}</strong>${
        targetPassiveOptions.length > 1
          ? ` (a nova forma também tem: ${targetPassiveOptions.filter((o) => o !== newPassiveActive).join(", ")} — troque manualmente se preferir outra)`
          : ""
      }.`;
  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `
      <p>🧬 <strong>${oldSpecies.species}</strong> evoluiu para <strong>${actor.link ?? actor.name}</strong>!</p>
      <p>Ganhou +${hpBonus} PV (o dobro do nível ${level}). Dado de Vida a partir do próximo nível: d${
        String(targetSys.attributes.hp.formula).replace(/\D/g, "")
      }. CA agora: ${targetSys.attributes.ac.flat ?? targetSys.attributes.ac.value ?? "?"}.</p>
      <p>${passiveNote}</p>
      <p><em>Moves já conhecidos foram mantidos — só os Moves futuros passam a vir da lista de ${targetFlags.species}.</em></p>`
  });

  return {
    status: "evolved",
    from: oldSpecies.species,
    to: targetFlags.species,
    hpBonus,
    passiveKept,
    passiveOptions: targetPassiveOptions
  };
}
