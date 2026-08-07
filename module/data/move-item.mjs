const { StringField, NumberField, ArrayField, SchemaField, BooleanField, HTMLField } = foundry.data.fields;

/**
 * DataModel for the "pokemon-mundo-perfeito.move" Item sub-type.
 * Mirrors the fixed template used throughout the "Lista de Moves" in the Livro de Regras
 * (Tipo / Poder do Move / Tempo de Execução / PP / Duração / Alcance / Descrição / Níveis Superiores).
 */
export default class MoveData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      moveType: new StringField({ initial: "normal" }),
      category: new StringField({ initial: "" }),

      power: new StringField({ initial: "" }),
      powerAbilities: new ArrayField(new StringField()),

      activation: new SchemaField({
        type: new StringField({ initial: "action" }),
        raw: new StringField({ initial: "" })
      }),

      pp: new SchemaField({
        value: new NumberField({ integer: true, initial: 0, min: 0 }),
        max: new NumberField({ integer: true, initial: 0, min: 0 }),
        unlimited: new BooleanField({ initial: false })
      }),

      duration: new StringField({ initial: "Instantânea" }),

      range: new SchemaField({
        raw: new StringField({ initial: "" }),
        meters: new NumberField({ initial: 0, min: 0 }),
        melee: new BooleanField({ initial: false })
      }),

      priority: new NumberField({ integer: true, initial: 0 }),

      description: new HTMLField({ initial: "" }),
      higherLevels: new HTMLField({ initial: "" }),
      observations: new HTMLField({ initial: "" }),
      zPowerEffect: new StringField({ initial: "" }),

      damage: new SchemaField({
        baseFormula: new StringField({ initial: "" }),
        scaling: new ArrayField(
          new SchemaField({
            level: new NumberField({ integer: true, min: 1 }),
            formula: new StringField()
          })
        )
      })
    };
  }
}
