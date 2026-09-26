/**
 * Mega Evolução (compêndio "Mega Evoluções", Regras > Mecânicas Especiais > "Mega Evolução").
 *
 * Pokémon são Actors "npc" nativos do dnd5e (ver sheet-extras.mjs) — os campos que este
 * arquivo mexia antes (system.types, system.armorClass.value, system.passiveAbility.active,
 * system.size) pertenciam a um DataModel customizado antigo (module/data/pokemon-actor.mjs)
 * que nunca chegou a ser registrado; nesta versão os efeitos são aplicados nos caminhos reais
 * do schema nativo (flags.species.types, system.attributes.ac.flat, itens "feat" de
 * Tipo/Habilidade Passiva embutidos, system.traits.size) — mesmo padrão já usado em
 * module/data/evolution.mjs.
 *
 * O botão "Mega Evoluir" na ficha (sheet-extras.mjs) só aparece quando o Pokémon está
 * segurando (Item "equipment" com system.equipped=true) uma Mega Pedra da própria espécie —
 * cada Mega Pedra do compêndio "mega-evolutions" já carrega os dados mecânicos prontos em
 * flags.pokemon-mundo-perfeito.mega.
 */
import { TYPE_LABELS } from "./type-chart.mjs";
import { fetchAbilityInfo } from "../data/abilities-lookup.mjs";

const MODULE_ID = "pokemon-mundo-perfeito";
const SNAPSHOT_FLAG = "megaEvolutionSnapshot";
const MAX_ABILITY_SCORE = 30;
const MOVEMENT_KEYS = ["walk", "swim", "fly", "climb", "burrow"];

function normalize(name) {
  return (name ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]/g, "").toLowerCase();
}

/** Mega Pedra da própria espécie no inventário do Pokémon, esteja equipada ou não. */
export function findMatchingMegaStone(actor) {
  const species = actor?.getFlag(MODULE_ID, "species");
  if (!species) return null;
  return actor.items.find((i) => {
    const mega = i.getFlag(MODULE_ID, "mega");
    return mega && normalize(mega.species) === normalize(species.species);
  }) ?? null;
}

/** Mega Pedra equipada que corresponde à espécie deste Pokémon, se houver. */
export function findEquippedMegaStone(actor) {
  const stone = findMatchingMegaStone(actor);
  return stone && stone.system.equipped ? stone : null;
}

export function isMegaEvolved(actor) {
  return !!actor?.getFlag(MODULE_ID, SNAPSHOT_FLAG);
}

export function canMegaEvolve(actor) {
  return !isMegaEvolved(actor) && !!findEquippedMegaStone(actor);
}

function typeFeatItem(typeKey) {
  const label = TYPE_LABELS[typeKey] ?? typeKey;
  return {
    name: `Tipo ${label}`,
    type: "feat",
    img: `modules/${MODULE_ID}/assets/types/${typeKey}.svg`,
    system: {
      description: { value: `<p>Este Pokémon é do tipo ${label}.</p>`, chat: "" },
      type: { value: "", subtype: "" },
      requirements: "",
      uses: { spent: 0, max: "", recovery: [] },
      activities: {}
    },
    effects: [], flags: {}, sort: 0
  };
}

function passiveAbilityFeatItem(name, description, img) {
  return {
    name: `Habilidade Passiva: ${name}`,
    type: "feat",
    img,
    system: {
      description: { value: description, chat: "" },
      type: { value: "", subtype: "" },
      requirements: "",
      uses: { spent: 0, max: "", recovery: [] },
      activities: {}
    },
    effects: [], flags: {}, sort: 0
  };
}

/**
 * @param {Actor} actor Pokémon (Actor "npc" com flags.species).
 * @param {Record<string,string>} [chosenAbilities] Pra cada abilityChoice da Mega Pedra
 *   (chave = options.join("/")), qual atributo o jogador escolheu. Se omitido, usa a
 *   primeira opção de cada escolha.
 */
export async function applyMegaEvolution(actor, chosenAbilities = {}) {
  const stone = findEquippedMegaStone(actor);
  if (!stone) return { status: "no-stone" };
  if (isMegaEvolved(actor)) return { status: "already-evolved" };

  const mega = stone.getFlag(MODULE_ID, "mega");
  const species = actor.getFlag(MODULE_ID, "species");
  const rawSys = actor._source.system;

  // Snapshot pra reverter depois — abilities/AC/tamanho/deslocamento/tipo/habilidade, tudo
  // que este método pode alterar.
  const snapshot = {
    abilities: Object.fromEntries(Object.entries(rawSys.abilities).map(([k, a]) => [k, a.value])),
    ac: foundry.utils.deepClone(rawSys.attributes.ac),
    size: rawSys.traits.size,
    movement: foundry.utils.deepClone(rawSys.attributes.movement),
    types: { ...species.types },
    passiveActive: species.passiveAbility?.active ?? "",
    passiveOptions: [...(species.passiveAbility?.options ?? [])]
  };

  const update = { [`flags.${MODULE_ID}.${SNAPSHOT_FLAG}`]: snapshot };

  // Atributos: deltas fixos + escolhas (options[0] por padrão, como o mega-evolution.mjs já
  // documentava antes desta correção).
  const deltas = { ...(mega.abilityDeltas ?? {}) };
  for (const choice of mega.abilityChoices ?? []) {
    const picked = chosenAbilities[choice.options.join("/")] ?? choice.options[0];
    deltas[picked] = (deltas[picked] ?? 0) + choice.delta;
  }
  for (const [key, delta] of Object.entries(deltas)) {
    const current = rawSys.abilities[key]?.value ?? 10;
    update[`system.abilities.${key}.value`] = Math.min(current + delta, MAX_ABILITY_SCORE);
  }

  if (mega.armorClassDelta) {
    update["system.attributes.ac.flat"] = (rawSys.attributes.ac.flat ?? 10) + mega.armorClassDelta;
  }

  if (mega.size) update["system.traits.size"] = mega.size;

  // Deslocamento: bônus fixo (só nos tipos que o Pokémon já tem) + concessões de novos tipos
  // (ex.: "ganha deslocamento de voo igual ao de caminhada").
  const movement = foundry.utils.deepClone(rawSys.attributes.movement);
  if (mega.movementBonusFeet) {
    const bonusMeters = Math.round(mega.movementBonusFeet * 0.3 * 10) / 10;
    for (const key of MOVEMENT_KEYS) {
      if (movement[key]) movement[key] += bonusMeters;
    }
  }
  for (const grant of mega.movementGrants ?? []) {
    const walk = movement.walk ?? 0;
    if (grant.type === "voo") movement.fly = walk;
    else if (grant.type === "flutuação" || grant.type === "flutuacao") { movement.fly = walk; movement.hover = true; }
  }
  update["system.attributes.movement"] = movement;

  const typeChanged = !!mega.types?.type1;
  if (typeChanged) {
    update[`flags.${MODULE_ID}.species.types`] = { type1: mega.types.type1, type2: mega.types.type2 ?? null };
  }

  let passiveInfo = null;
  if (mega.passiveAbility) {
    passiveInfo = await fetchAbilityInfo(mega.passiveAbility);
    update[`flags.${MODULE_ID}.species.passiveAbility`] = {
      options: [mega.passiveAbility], active: mega.passiveAbility
    };
  }

  await actor.update(update);

  const toDelete = [];
  for (const item of actor.items) {
    if (item.type !== "feat") continue;
    if (typeChanged && item.name.startsWith("Tipo ")) toDelete.push(item.id);
    else if (passiveInfo && item.name.startsWith("Habilidade Passiva: ")) toDelete.push(item.id);
  }
  if (toDelete.length) await actor.deleteEmbeddedDocuments("Item", toDelete);

  const toCreate = [];
  if (typeChanged) {
    toCreate.push(typeFeatItem(mega.types.type1));
    if (mega.types.type2) toCreate.push(typeFeatItem(mega.types.type2));
  }
  if (passiveInfo) toCreate.push(passiveAbilityFeatItem(mega.passiveAbility, passiveInfo.description, passiveInfo.img));
  if (toCreate.length) await actor.createEmbeddedDocuments("Item", toCreate);

  if (actor.sheet?.rendered) actor.sheet.render(false);

  const extra = [...(mega.movementGrants ?? []).map((g) => `Ganha deslocamento de ${g.type} igual ao de ${g.equalTo}.`),
    ...(mega.otherEffects ?? [])];
  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `<p>🔷 <strong>${actor.name}</strong> Mega Evoluiu para <strong>${mega.megaForm}</strong>!</p>
      ${extra.length ? `<p><em>Efeitos adicionais (aplique manualmente): ${extra.join(" ")}</em></p>` : ""}`
  });

  return { status: "evolved", megaForm: mega.megaForm };
}

/** Reverte a Mega Evolução ao estado salvo em applyMegaEvolution. */
export async function revertMegaEvolution(actor) {
  const snapshot = actor.getFlag(MODULE_ID, SNAPSHOT_FLAG);
  if (!snapshot) return { status: "not-evolved" };

  const update = {
    "system.traits.size": snapshot.size,
    "system.attributes.ac": snapshot.ac,
    "system.attributes.movement": snapshot.movement,
    [`flags.${MODULE_ID}.species.types`]: snapshot.types,
    [`flags.${MODULE_ID}.-=${SNAPSHOT_FLAG}`]: null
  };
  for (const [key, value] of Object.entries(snapshot.abilities)) {
    update[`system.abilities.${key}.value`] = value;
  }

  const toDelete = [];
  for (const item of actor.items) {
    if (item.type !== "feat") continue;
    if (item.name.startsWith("Tipo ") || item.name.startsWith("Habilidade Passiva: ")) toDelete.push(item.id);
  }

  const toCreate = [typeFeatItem(snapshot.types.type1)];
  if (snapshot.types.type2) toCreate.push(typeFeatItem(snapshot.types.type2));
  if (snapshot.passiveActive) {
    const info = await fetchAbilityInfo(snapshot.passiveActive);
    update[`flags.${MODULE_ID}.species.passiveAbility`] = {
      options: snapshot.passiveOptions, active: snapshot.passiveActive
    };
    toCreate.push(passiveAbilityFeatItem(snapshot.passiveActive, info.description, info.img));
  }

  await actor.update(update);
  if (toDelete.length) await actor.deleteEmbeddedDocuments("Item", toDelete);
  await actor.createEmbeddedDocuments("Item", toCreate);

  if (actor.sheet?.rendered) actor.sheet.render(false);

  ChatMessage.create({
    speaker: ChatMessage.getSpeaker({ actor }),
    content: `<p>🔷 <strong>${actor.name}</strong> reverteu a Mega Evolução.</p>`
  });

  return { status: "reverted" };
}
