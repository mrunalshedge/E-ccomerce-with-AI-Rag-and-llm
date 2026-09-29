// Dev API server that restarts when backend code changes.
//
// Why not `uvicorn --reload`? On Windows its reloader restarts the worker by sending Ctrl+C to the
// whole console, which also stops Vite and makes npm ask "Terminate batch job (Y/N)?", killing
// `npm run dev`. Here we stop only our own process tree and start it again.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, watch } from "node:fs";
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

const args = ["-m", "uvicorn", "app.main:app", "--port", "8000"];
let child = null;
let restarting = false;

function start() {
  child = spawn(python, args, { cwd: backend, stdio: "inherit" });
  child.on("exit", (code) => {
    child = null;
    if (restarting) {
      restarting = false;
      start();
    } else if (code !== 0) {
      console.error(`API exited with code ${code}; waiting for a code change to restart.`);
    }
  });
}

function stop() {
  if (!child) return;
  if (process.platform === "win32") {
    // The venv python.exe is a launcher with the real interpreter as a child: end the whole tree.
    spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  } else {
    child.kill("SIGTERM");
  }
}

let timer = null;
watch(join(backend, "app"), { recursive: true }, (_event, file) => {
  if (!file || !file.endsWith(".py") || file.includes("__pycache__")) return;
  clearTimeout(timer);
  timer = setTimeout(() => {
    console.log(`\n[api] ${file} changed, restarting…`);
    if (child) {
      restarting = true;
      stop();
    } else {
      start();
    }
  }, 300);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    restarting = false;
    stop();
    process.exit(0);
  });
}

start();
