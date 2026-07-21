#!/usr/bin/env node
// Filtra `yarn audit --json` y falla solo si hay vulnerabilidades HIGH/CRITICAL.
// El exit code nativo de `yarn audit` es un bitmask de TODAS las severidades
// encontradas (incluye low/moderate), por eso no sirve para "fallar solo en
// HIGH/CRITICAL" y hay que leer el resumen del JSON directamente.
const fs = require("fs");

const path = process.argv[2];
if (!path) {
  console.error("Uso: node check-audit-severity.js <yarn-audit-output.json>");
  process.exit(2);
}

const lines = fs.readFileSync(path, "utf8").split("\n").filter(Boolean);
let summary = null;
for (const line of lines) {
  const parsed = JSON.parse(line);
  if (parsed.type === "auditSummary") summary = parsed.data.vulnerabilities;
}

if (!summary) {
  console.error("No se encontro un resumen (auditSummary) en la salida de yarn audit.");
  process.exit(1);
}

console.log("Vulnerabilidades encontradas:", summary);

if (summary.high > 0 || summary.critical > 0) {
  console.error(`Bloqueando build: ${summary.high} HIGH, ${summary.critical} CRITICAL.`);
  process.exit(1);
}

console.log("Sin vulnerabilidades HIGH/CRITICAL en dependencias de frontend.");
