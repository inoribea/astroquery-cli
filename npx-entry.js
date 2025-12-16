#!/usr/bin/env node
/**
 * Lightweight npx wrapper that bootstraps the Python CLI into an isolated venv.
 * Requires a local Python 3 installation but avoids polluting the global site-packages.
 */

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import os from "node:os";

const args = process.argv.slice(2);

const log = {
  info: (message) => process.stdout.write(`${message}\n`),
  error: (message) => process.stderr.write(`${message}\n`),
};

const binDir = process.platform === "win32" ? "Scripts" : "bin";
const pythonBinName = process.platform === "win32" ? "python.exe" : "python";
const defaultVenvRoot = join(os.homedir(), ".cache", "astroquery-cli");
const venvDir = join(process.env.AQC_VENV_DIR || defaultVenvRoot, "venv");
const venvPython = join(venvDir, binDir, pythonBinName);

function fail(message, code = 1) {
  log.error(message);
  process.exit(code);
}

function tryCommand(cmd, cmdArgs = [], options = {}) {
  return spawnSync(cmd, cmdArgs, { stdio: "inherit", ...options });
}

function findPython() {
  const candidates = process.env.AQC_PYTHON
    ? [process.env.AQC_PYTHON]
    : ["python3", "python"];

  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["--version"], { stdio: "ignore" });
    if (result.status === 0) {
      return candidate;
    }
  }

  return null;
}

function ensureVenv(pythonCmd) {
  if (existsSync(venvPython)) {
    return;
  }

  mkdirSync(venvDir, { recursive: true });
  const creation = tryCommand(pythonCmd, ["-m", "venv", venvDir]);
  if (creation.status !== 0) {
    fail("无法创建虚拟环境。请确认本地 Python 3 可用。");
  }
}

function needInstall() {
  if (process.env.AQC_FORCE_INSTALL === "1") {
    return true;
  }

  const check = spawnSync(venvPython, ["-m", "pip", "show", "astroquery-cli"], {
    stdio: "ignore",
  });
  return check.status !== 0;
}

function ensureCliInstalled() {
  if (!needInstall()) {
    return;
  }

  log.info("正在安装/更新 astroquery-cli 到本地虚拟环境……");
  const install = tryCommand(venvPython, [
    "-m",
    "pip",
    "install",
    "--upgrade",
    "pip",
    "astroquery-cli",
  ]);

  if (install.status !== 0) {
    fail("安装 astroquery-cli 失败，请检查网络或 PyPI 访问。");
  }
}

function runCli() {
  const execution = tryCommand(venvPython, ["-m", "astroquery_cli.main", ...args]);
  process.exit(execution.status ?? 1);
}

function main() {
  const pythonCmd = findPython();
  if (!pythonCmd) {
    fail("未找到 Python 3，可通过环境变量 AQC_PYTHON 指定解释器路径。");
  }

  ensureVenv(pythonCmd);
  ensureCliInstalled();
  runCli();
}

main();
