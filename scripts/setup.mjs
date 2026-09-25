// One-time setup: Python venv + backend packages, frontend packages, backend/.env.
// Safe to re-run (it only installs what's missing or changed).
import { execFileSync, execSync } from "node:child_process";
import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const backend = join(root, "backend");
const isWin = process.platform === "win32";
const venvPython = join(backend, ".venv", isWin ? "Scripts/python.exe" : "bin/python");

function run(cmd, args, cwd = root) {
  console.log(`\n> ${cmd} ${args.join(" ")}`);
  execFileSync(cmd, args, { cwd, stdio: "inherit" });
}

// npm is a .cmd script on Windows, which needs a shell; run it as one fixed command string.
function npmInstall(cwd) {
  console.log(`\n> npm install  (${cwd})`);
  execSync("npm install", { cwd, stdio: "inherit" });
}

// 1. Python virtual environment (Windows: the `py` launcher; elsewhere: python3)
if (!existsSync(venvPython)) {
  if (isWin) run("py", ["-3", "-m", "venv", ".venv"], backend);
  else run("python3", ["-m", "venv", ".venv"], backend);
}
run(venvPython, ["-m", "pip", "install", "--upgrade", "pip", "-q"], backend);
run(venvPython, ["-m", "pip", "install", "-r", "requirements.txt"], backend);

// 2. Node packages (root dev tools + frontend)
npmInstall(root);
npmInstall(join(root, "frontend"));

// 3. Environment file
const env = join(backend, ".env");
if (!existsSync(env)) {
  copyFileSync(join(backend, ".env.example"), env);
  console.log("\nCreated backend/.env from .env.example: fill in your database details and JWT_SECRET_KEY.");
}

console.log("\nSetup complete. Start everything with:  npm run dev");
