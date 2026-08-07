const { StringField, NumberField, ArrayField, SchemaField, BooleanField, HTMLField, ObjectField } =
  foundry.data.fields;

const ABILITY_KEYS = ["str", "dex", "con", "int", "wis", "cha"];

function abilitySchema(initial = 10) {
  return new SchemaField({
    value: new NumberField({ required: true, integer: true, initial, min: 1 })
  });
}

/**
 * DataModel for the "pokemon-mundo-perfeito.pokemon" Actor sub-type.
 * Mirrors the "Bloco de Estatística" fields from the Livro dos Pokémon / Livro de Regras.
 */
export default class PokemonData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      species: new StringField({ initial: "" }),
      dexNumber: new NumberField({ integer: true, initial: 0, min: 0 }),

      types: new SchemaField({
        type1: new StringField({ required: true, blank: false, initial: "normal" }),
        type2: new StringField({ required: false, nullable: true, initial: null })
      }),

      speciesRank: new SchemaField({
        value: new NumberField({ required: true, initial: 0.5, min: 0 }),
        display: new StringField({ initial: "1/2" })
      }),

      size: new StringField({ initial: "tiny" }),
      heightMeters: new NumberField({ initial: 0, min: 0 }),

      minLevelFound: new NumberField({ integer: true, initial: 1, min: 1 }),
      eggGroups: new ArrayField(new StringField()),

      gender: new SchemaField({
        malePercent: new NumberField({ initial: 50, min: 0, max: 100 }),
        femalePercent: new NumberField({ initial: 50, min: 0, max: 100 }),
        genderless: new BooleanField({ initial: false })
      }),

      evolutionStage: new SchemaField({
        current: new NumberField({ integer: true, initial: 1, min: 1 }),
        max: new NumberField({ integer: true, initial: 1, min: 1 })
      }),
      evolution: new StringField({ initial: "" }),

      biography: new HTMLField({ initial: "" }),

      abilities: new SchemaField(Object.fromEntries(ABILITY_KEYS.map((k) => [k, abilitySchema()]))),

      skills: new ArrayField(new StringField()),

      armorClass: new SchemaField({
        value: new NumberField({ required: true, integer: true, initial: 10 })
      }),

      hitPoints: new SchemaField({
        value: new NumberField({ integer: true, initial: 1, min: 0 }),
        max: new NumberField({ integer: true, initial: 1, min: 1 }),
        hitDie: new StringField({ initial: "d6" })
      }),

      movement: new SchemaField({
        walk: new NumberField({ initial: 9, min: 0 }),
        other: new StringField({ initial: "" })
      }),

      senses: new StringField({ initial: "" }),

      passiveAbility: new SchemaField({
        options: new ArrayField(new StringField()),
        active: new StringField({ initial: "" })
      }),
      hiddenAbility: new StringField({ initial: "" }),

      level: new NumberField({ integer: true, initial: 1, min: 1, max: 20 }),

      moveTable: new ArrayField(
        new SchemaField({
          level: new NumberField({ integer: true, min: 1 }),
          moves: new ArrayField(new StringField())
        })
      ),
      knownMoves: new ArrayField(new StringField()),
      tms: new ArrayField(new StringField()),
      eggMoves: new ArrayField(new StringField()),

      typeDefenseOverrides: new ObjectField({ initial: {} }),

      nature: new SchemaField({
        name: new StringField({ initial: "" }),
        increased: new StringField({ initial: "" }),
        decreased: new StringField({ initial: "" })
      }),
      loyalty: new NumberField({ integer: true, initial: 0 }),
      shiny: new BooleanField({ initial: false }),
      evs: new SchemaField(
        Object.fromEntries(ABILITY_KEYS.map((k) => [k, new NumberField({ integer: true, initial: 0, min: 0 })]))
      )
    };
  }

  prepareDerivedData() {
    for (const key of ABILITY_KEYS) {
      const ability = this.abilities[key];
      ability.mod = Math.floor((ability.value - 10) / 2);
    }

    // Proficiency bonus follows the standard 5e progression by character level.
    this.proficiencyBonus = Math.ceil(1 + this.level / 4);
  }
}
