// Regras de Ovos e Incubação (Livro de Regras, "Reprodução e Ovos", pág. 42-43). Fica
// separado de egg-sheet.mjs/create-egg-dialog.mjs de propósito: tabela de SR, incubadoras
// e o cálculo de requisito/estado são regras de sistema, não de interface — trocar um
// valor da tabela ou adicionar uma incubadora nova não deveria exigir mexer na ficha.

// Tempo de Eclosão por Classificação de Espécie (SR), pág. 42.
export const SR_HATCH_TABLE = {
  "1/8": 125, "1/4": 250, "1/2": 500, "1": 600, "2": 700, "3": 800, "4": 900, "5": 1000,
  "6": 1100, "7": 1200, "8": 1300, "9": 1400, "10": 1500, "11": 1600, "12": 1700,
  "13": 1800, "14": 1900, "15": 2000
};

export const SR_OPTIONS = Object.keys(SR_HATCH_TABLE);

// "Manuseio de Ovos" / tabela de Incubadoras, pág. 42: cada uma soma dados extras à
// rolagem de 1d100 contra o contador de incubação.
export const INCUBATORS = {
  basica: { key: "basica", label: "Básica", bonusDice: "1d20", price: "₽1.000" },
  plus: { key: "plus", label: "Plus", bonusDice: "2d20", price: "₽3.000" },
  super: {
    key: "super", label: "Super", bonusDice: "3d20", price: "₽10.000",
    note: "Ao atingir o requisito, o Treinador escolhe o momento de chocar o ovo."
  }
};

export const EGG_STATES = {
  novo: { key: "novo", label: "Novo" },
  incubando: { key: "incubando", label: "Incubando" },
  pronto: { key: "pronto", label: "Pronto para eclosão" },
  chocado: { key: "chocado", label: "Chocado" }
};

// Tipos de entrada do histórico (seção 13). O ícone/rótulo ficam centralizados aqui para
// não duplicar strings entre a ficha do Mestre e qualquer viewer futuro.
export const HISTORY_TYPES = {
  initial: { icon: "🥚", label: "Progresso inicial" },
  playerRoll: { icon: "🎲", label: "Rolagem de Incubação (Jogador)" },
  gmRoll: { icon: "🎲", label: "Rolagem de Incubação (Mestre)" },
  gmBonus: { icon: "➕", label: "Bônus concedido pelo Mestre" },
  gmCorrection: { icon: "➖", label: "Correção do Mestre" },
  admin: { icon: "⚙️", label: "Alteração administrativa" }
};

export function defaultRequirementForSr(sr) {
  return SR_HATCH_TABLE[sr] ?? null;
}

// "Requisito atualmente utilizado": o valor manual do Mestre sempre vence o da tabela,
// mas os dois continuam guardados separadamente (seção 8) para o Mestre saber depois que
// o valor foi alterado.
export function resolveRequirement(egg) {
  if (Number.isFinite(egg.requirementCustom)) return egg.requirementCustom;
  return defaultRequirementForSr(egg.sr) ?? 0;
}

export function buildIncubationFormula(incubatorKey) {
  const incubator = INCUBATORS[incubatorKey];
  return incubator ? `1d100 + ${incubator.bonusDice}` : "1d100";
}

// Progresso e requisito nunca são a mesma coisa (seção 9) — o estado é sempre recalculado
// a partir dos dois, nunca guardado como uma terceira fonte de verdade que possa dessincronizar.
export function deriveState(egg) {
  if (egg.hatched) return EGG_STATES.chocado.key;
  const requirement = resolveRequirement(egg);
  if (requirement > 0 && egg.progress >= requirement) return EGG_STATES.pronto.key;
  if (egg.progress > 0) return EGG_STATES.incubando.key;
  return EGG_STATES.novo.key;
}

export function canHatch(egg) {
  return !egg.hatched && egg.progress >= resolveRequirement(egg);
}

export function makeHistoryEntry(type, delta, total, note = "") {
  return { id: foundry.utils.randomID(), ts: Date.now(), type, delta, total, note };
}

export function defaultEgg(overrides = {}) {
  return {
    species: "", shiny: false, sr: "1", requirementCustom: null, progress: 0,
    incubator: null, revealed: false, hatched: false, history: [], ...overrides
  };
}
