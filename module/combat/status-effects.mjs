// Ícones de "Mudança de Status" (aumento/redução de atributo — Livro de Regras, seção de
// Dano: "Mudanças de Status do usuário/alvo") pro HUD de Token do Foundry. São só
// marcadores visuais (sem Active Effect numérico anexado) — o valor exato de cada estágio
// não está confirmado nos dados já extraídos deste módulo, então em vez de arriscar um
// número errado, isso fica como indicador visual pro Mestre/jogador aplicar manualmente,
// igual a qualquer condição nativa do dnd5e nesse mesmo menu.
const MODULE_ID = "pokemon-mundo-perfeito";
const UP_ICON = "icons/skills/movement/arrow-upward-yellow.webp";
const DOWN_ICON = "icons/skills/movement/arrow-downward-red.webp";

// Nomeado pelo atributo (FOR/DES/CON/INT/SAB/CAR), igual ao "Poder do Move" do livro, em
// vez de nomes de stat do jogo (Ataque/Defesa Especial/etc.) — evita inventar um
// mapeamento atributo↔stat que não está confirmado em lugar nenhum deste módulo. CA entra
// junto porque Naturezas já a tratam como um "atributo" (ex. Natureza Tímido: "+1 CA").
const STATS = [
  { key: "for", label: "FOR" },
  { key: "des", label: "DES" },
  { key: "con", label: "CON" },
  { key: "int", label: "INT" },
  { key: "sab", label: "SAB" },
  { key: "car", label: "CAR" },
  { key: "ca", label: "CA" }
];

export function registerStatusEffects() {
  const entries = STATS.flatMap(({ key, label }) => [
    { id: `${MODULE_ID}-${key}-mais`, name: `${label} ↑`, img: UP_ICON },
    { id: `${MODULE_ID}-${key}-menos`, name: `${label} ↓`, img: DOWN_ICON }
  ]);
  CONFIG.statusEffects.push(...entries);
}
