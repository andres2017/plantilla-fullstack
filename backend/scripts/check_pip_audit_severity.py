"""Filtra el resultado de `pip-audit --format json` y falla solo si hay CVEs HIGH/CRITICAL.

pip-audit no incluye severidad en su propio JSON (solo id/aliases/fix_versions/
descripcion), asi que consultamos la API publica de OSV.dev por cada vulnerabilidad
para obtener la severidad real (etiqueta de GHSA o score CVSS calculado con la
libreria `cvss`). Uso: python check_pip_audit_severity.py pip-audit-output.json
"""
import json
import sys

import requests
from cvss import CVSS2, CVSS3, CVSS4

OSV_URL = "https://api.osv.dev/v1/vulns/{id}"
BLOCKING = {"HIGH", "CRITICAL"}
CVSS_PARSERS = {"CVSS_V4": CVSS4, "CVSS_V3": CVSS3, "CVSS_V2": CVSS2}


def _score_to_level(score: float) -> str:
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    if score > 0.0:
        return "LOW"
    return "NONE"


def _severity_for_id(vuln_id: str) -> str:
    try:
        resp = requests.get(OSV_URL.format(id=vuln_id), timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        print(f"  ! no se pudo consultar OSV para {vuln_id}: {exc}", file=sys.stderr)
        return "UNKNOWN"

    label = (data.get("database_specific") or {}).get("severity")
    if label:
        return label.upper()

    for entry in data.get("severity", []):
        parser = CVSS_PARSERS.get(entry.get("type"))
        if parser is None:
            continue
        try:
            score = parser(entry["score"]).base_score
        except Exception:
            continue
        return _score_to_level(score)

    return "UNKNOWN"


def main() -> int:
    with open(sys.argv[1], encoding="utf-8") as f:
        report = json.load(f)

    cache: dict[str, str] = {}
    blocking = []
    other = []

    for dep in report.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            candidate_ids = [vuln["id"], *vuln.get("aliases", [])]
            severity = "UNKNOWN"
            for candidate in candidate_ids:
                if candidate not in cache:
                    cache[candidate] = _severity_for_id(candidate)
                severity = cache[candidate]
                if severity != "UNKNOWN":
                    break
            entry = (dep["name"], dep["version"], vuln["id"], severity, vuln.get("fix_versions") or [])
            (blocking if severity in BLOCKING else other).append(entry)

    if other:
        print("Vulnerabilidades encontradas por debajo del umbral (no bloquean el build):")
        for name, version, vid, severity, fixes in other:
            print(f"  - [{severity}] {name}=={version} ({vid}) -> fix: {fixes or 'sin fix conocido'}")

    if blocking:
        print("\nVulnerabilidades HIGH/CRITICAL (bloquean el build):")
        for name, version, vid, severity, fixes in blocking:
            print(f"  - [{severity}] {name}=={version} ({vid}) -> fix: {fixes or 'sin fix conocido'}")
        return 1

    print("\nSin vulnerabilidades HIGH/CRITICAL en las dependencias de backend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
