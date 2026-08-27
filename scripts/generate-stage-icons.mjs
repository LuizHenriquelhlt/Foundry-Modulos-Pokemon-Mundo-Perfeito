// Gera os ícones de Mudança de Status (pág. 71) usados como "condições com nível" nativas
// do dnd5e — o mesmo mecanismo que o próprio sistema usa pra Exaustão (níveis 1-6, um ícone
// próprio por nível). Confirmado direto no repositório do dnd5e (module/data/active-effect/
// condition.mjs, ConditionData#getIconByLevel): pra QUALQUER condição registrada com
// "levels" em CONFIG.DND5E.conditionTypes, o sistema SEMPRE troca a imagem pra
// "<base>-<nível>.<ext>" — então precisam existir arquivos reais numerados de 1 a 6, além
// da imagem base (essa aparece na grade do HUD do Token antes de qualquer nível ativo).
// Confirmado no próprio pacote de ícones do dnd5e (icons/svg/statuses/exhaustion-1.svg até
// exhaustion-6.svg): cada nível soma um selo numérico a um desenho de base fixo — mesma
// ideia usada aqui, só que com formas temáticas por atributo em vez de um selo sozinho
// (o formato "só número" já foi tentado numa versão anterior e ficou ilegível/genérico
// demais no tamanho real do ícone do token).
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(__dirname, "..", "assets", "stages");
mkdirSync(OUT_DIR, { recursive: true });

const POSITIVE = "#4ade80";
const NEGATIVE = "#f87171";

// Uma forma simples e de alto contraste por atributo (espada, estrela cadente, escudo,
// hexágono/barreira, setas de velocidade, alvo, olho, estrela) — preenchida via
// currentColor pra reaproveitar o mesmo desenho tanto na versão "sobe" (verde) quanto
// "desce" (vermelho), só trocando a cor no momento de gerar o arquivo.
const SHAPES = {
  atk: `<polygon points="50,4 59,56 41,56"/><rect x="42" y="56" width="16" height="28"/>
        <rect x="27" y="56" width="46" height="9"/><rect x="38" y="85" width="24" height="10" rx="2"/>`,
  spa: `<path d="M50 2 L61 39 L98 50 L61 61 L50 98 L39 61 L2 50 L39 39 Z"/>`,
  def: `<path d="M50 4 L91 19 V50 C91 76 72 93 50 99 C28 93 9 76 9 50 V19 Z"/>`,
  spd: `<polygon points="50,2 94,26 94,74 50,98 6,74 6,26"/>`,
  spe: `<polygon points="6,18 42,50 6,82 23,82 59,50 23,18"/><polygon points="43,18 79,50 43,82 60,82 96,50 60,18"/>`,
  acc: `<circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" stroke-width="11"/>
        <circle cx="50" cy="50" r="22" fill="none" stroke="currentColor" stroke-width="11"/>
        <circle cx="50" cy="50" r="8"/>`,
  eva: `<path d="M3 50 C20 16 80 16 97 50 C80 84 20 84 3 50 Z"/><circle cx="50" cy="50" r="15" fill="#000"/>`,
  crit: `<polygon points="50,2 61,36 97,36 68,57 79,92 50,71 21,92 32,57 3,36 39,36"/>`
};

function iconSvg(key, color, level) {
  const badge = level ? `
    <circle cx="79" cy="80" r="19" fill="#000" fill-opacity="0.55" stroke="#fff" stroke-width="2.5"/>
    <text x="79" y="88" font-family="Arial, Helvetica, sans-serif" font-size="23" font-weight="700"
          fill="#fff" text-anchor="middle">${level}</text>` : "";
  return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <g fill="${color}" color="${color}">${SHAPES[key]}</g>
  ${badge}
</svg>
`;
}

let count = 0;
for (const key of Object.keys(SHAPES)) {
  for (const [direction, color] of [["up", POSITIVE], ["down", NEGATIVE]]) {
    const base = `${key}-${direction}`;
    writeFileSync(join(OUT_DIR, `${base}.svg`), iconSvg(key, color, null));
    count++;
    for (let level = 1; level <= 6; level++) {
      writeFileSync(join(OUT_DIR, `${base}-${level}.svg`), iconSvg(key, color, level));
      count++;
    }
  }
}

console.log(`Gerados ${count} ícones em ${OUT_DIR}`);
