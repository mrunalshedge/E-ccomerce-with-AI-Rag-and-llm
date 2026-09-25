// Runs a command with the backend's virtualenv Python, from the backend/ folder.
// Usage: node scripts/py.mjs -m uvicorn app.main:app --reload
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const backend = join(root, "backend");
const python =
  process.platform === "win32"
    ? join(backend, ".venv", "Scripts", "python.exe")
    : join(backend, ".venv", "bin", "python");

if (!existsSync(python)) {
  console.error("Python environment not found. Run `npm run setup` first.");
  process.exit(1);
}

const child = spawn(python, process.argv.slice(2), { cwd: backend, stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 1));
