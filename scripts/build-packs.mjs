import { compilePack } from "@foundryvtt/foundryvtt-cli";
import { readdirSync, statSync, rmSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const sourceRoot = path.join(root, "packs", "_source");
const outRoot = path.join(root, "packs");

const packNames = readdirSync(sourceRoot).filter((name) =>
  statSync(path.join(sourceRoot, name)).isDirectory()
);

if (packNames.length === 0) {
  console.warn(`Nenhuma pasta encontrada em ${sourceRoot}. Nada para compilar.`);
  process.exit(0);
}

for (const name of packNames) {
  const src = path.join(sourceRoot, name);
  const dest = path.join(outRoot, name);

  const entryCount = readdirSync(src, { recursive: true }).filter((f) =>
    f.toString().endsWith(".json")
  ).length;

  if (entryCount === 0) {
    console.warn(`Pulando "${name}": nenhum .json em ${src}`);
    continue;
  }

  rmSync(dest, { recursive: true, force: true });

  console.log(`Compilando pack "${name}" (${entryCount} documentos)...`);
  await compilePack(src, dest, { log: true, recursive: true });
}

console.log("\nBuild de compêndios concluído. Ative o módulo no Foundry para ver os compêndios.");
