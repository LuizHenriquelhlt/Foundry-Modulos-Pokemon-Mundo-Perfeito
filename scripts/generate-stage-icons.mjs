// Gera os 96 selos estáticos (8 atributos de Mudança de Status × estágios -6..+6, sem o
// zero) usados por module/combat/status-stages.mjs. Precisam ser arquivos de verdade (não
// um data URI gerado na hora) porque o schema de ActiveEffect do dnd5e valida que "img"
// termine numa extensão de arquivo reconhecida — testado e confirmado com o erro real do
// Foundry: "[ActiveEffect5e] validation errors: img does not have a valid file extension".
//
// Reaproveita as chaves de STAGE_STATS do próprio módulo em vez de duplicar a lista aqui.
// Idempotente — sobrescreve os mesmos 96 arquivos toda vez.
// Uso: node scripts/generate-stage-icons.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { STAGE_STATS } from "../module/combat/status-stages.mjs";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const OUT = path.join(ROOT, "assets", "stages");

// Tokens renderizam o ícone do efeito bem pequeno (20-30px de verdade na tela, mesmo que o
// SVG fonte seja 100x100) — sigla + número juntos (versão anterior) viravam uma mancha
// ilegível nesse tamanho. Só o número, gigante, ocupando quase todo o selo: continua
// legível de longe. A sigla do atributo já está no nome do efeito ("Ataque +1"), visível ao
// passar o mouse no ícone do token, então não precisa repetir dentro do desenho.
function svgFor(value) {
  const color = value > 0 ? "#2b9e4f" : "#b0413e";
  const text = `${value > 0 ? "+" : ""}${value}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">`
    + `<rect width="100" height="100" rx="14" fill="${color}"/>`
    + `<text x="50" y="72" font-size="64" font-family="sans-serif" font-weight="900" `
    + `fill="#fff" text-anchor="middle">${text}</text>`
    + `</svg>`;
}

function fileName(key, value) {
  const sign = value > 0 ? "plus" : "minus";
  return `${key}-${sign}${Math.abs(value)}.svg`;
}

fs.mkdirSync(OUT, { recursive: true });
let n = 0;
for (const { key } of STAGE_STATS) {
  for (let v = -6; v <= 6; v++) {
    if (v === 0) continue;
    fs.writeFileSync(path.join(OUT, fileName(key, v)), svgFor(v), "utf-8");
    n++;
  }
}
console.log(`${n} selos de Mudança de Status escritos em ${OUT}`);
