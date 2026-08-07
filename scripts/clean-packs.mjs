import { readdirSync, statSync, rmSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const outRoot = path.join(root, "packs");

const entries = readdirSync(outRoot).filter((name) => {
  const full = path.join(outRoot, name);
  return name !== "_source" && statSync(full).isDirectory();
});

for (const name of entries) {
  rmSync(path.join(outRoot, name), { recursive: true, force: true });
  console.log(`Removido pack compilado: ${name}`);
}
