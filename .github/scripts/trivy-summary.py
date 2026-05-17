"""Parse a Trivy JSON report, write a rich markdown summary to
GITHUB_STEP_SUMMARY, and apply the CRITICAL+fixed gate.

Usage: python3 trivy-summary.py <report.json> [<display-image-name>]

Exits 1 if the gate fails (any CRITICAL CVE with a known fix found),
0 otherwise. Always writes the summary, regardless of gate outcome.

Run by the Backend · Scan image / Frontend · Scan image CI jobs.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")
SEVERITY_ICON = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🔵",
    "UNKNOWN": "⚪",
}


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: trivy-summary.py <report.json> [<display-image>]", file=sys.stderr)
        sys.exit(2)

    report_path = sys.argv[1]
    display_image = sys.argv[2] if len(sys.argv) > 2 else None

    with open(report_path) as f:
        report = json.load(f)

    artifact = display_image or report.get("ArtifactName", "?")
    metadata = report.get("Metadata", {}) or {}
    os_info = metadata.get("OS", {}) or {}
    os_str = f"{os_info.get('Family', '?')} {os_info.get('Name', '')}".strip() or "?"
    image_id = (metadata.get("ImageID") or "")[:19] or "?"

    counts: dict[str, dict[str, int]] = {s: {"total": 0, "fixable": 0} for s in SEVERITIES}
    fixable_examples: dict[str, list[dict]] = defaultdict(list)
    pkg_count = 0

    for result in report.get("Results", []) or []:
        # Each result is one target (an OS layer or an in-image lockfile).
        for pkg in result.get("Packages", []) or []:
            pkg_count += 1

        for vuln in result.get("Vulnerabilities", []) or []:
            sev = vuln.get("Severity", "UNKNOWN")
            if sev not in counts:
                sev = "UNKNOWN"
            counts[sev]["total"] += 1
            fixed = bool(vuln.get("FixedVersion"))
            if fixed:
                counts[sev]["fixable"] += 1
                if len(fixable_examples[sev]) < 8:
                    fixable_examples[sev].append(
                        {
                            "id": vuln.get("VulnerabilityID", "?"),
                            "pkg": vuln.get("PkgName", "?"),
                            "have": vuln.get("InstalledVersion", "?"),
                            "fix": vuln.get("FixedVersion", "-"),
                            "title": (vuln.get("Title") or "").split(": ", 1)[-1][:80],
                        }
                    )

    total = sum(c["total"] for c in counts.values())
    fixable = sum(c["fixable"] for c in counts.values())
    crit_fixable = counts["CRITICAL"]["fixable"]
    crit_total = counts["CRITICAL"]["total"]

    lines: list[str] = []
    lines.append(f"### 🛡️ Trivy scan — `{artifact}`")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| **Base image** | `{os_str}` |")
    if image_id != "?":
        lines.append(f"| **Image ID** | `{image_id}` |")
    if pkg_count:
        lines.append(f"| **Packages scanned** | {pkg_count} |")
    lines.append(f"| **Total CVEs** | {total} ({fixable} with a known fix) |")
    lines.append(f"| **Gate** | CRITICAL severity, fix available → block build |")
    lines.append("")

    lines.append("**Severity breakdown**")
    lines.append("")
    lines.append("| | Severity | Total | Fixable |")
    lines.append("|---|---|---:|---:|")
    for sev in SEVERITIES:
        c = counts[sev]
        if c["total"] == 0:
            continue
        block_marker = "❌" if sev == "CRITICAL" and c["fixable"] > 0 else "  "
        lines.append(f"| {block_marker} | {SEVERITY_ICON[sev]} {sev} | {c['total']} | {c['fixable']} |")
    if total == 0:
        lines.append("| ✅ | _no vulnerabilities found_ | 0 | 0 |")
    lines.append("")

    # Verdict
    if crit_fixable > 0:
        lines.append(f"**❌ Gate FAILED:** {crit_fixable} CRITICAL CVE(s) with an available fix.")
        lines.append("")
        lines.append("<details><summary>Top fixable CRITICAL findings</summary>")
        lines.append("")
        lines.append("| CVE | Package | Installed | Fixed in |")
        lines.append("|---|---|---|---|")
        for v in fixable_examples["CRITICAL"]:
            lines.append(f"| `{v['id']}` | `{v['pkg']}` | {v['have']} | **{v['fix']}** |")
        lines.append("")
        lines.append("</details>")
    else:
        lines.append("**✅ Gate passed** — no CRITICAL CVE with a known fix.")
        notes = []
        if crit_total > 0:
            notes.append(
                f"{crit_total} CRITICAL CVE(s) reported but unfixable (no patch published yet)"
            )
        high_total = counts["HIGH"]["total"]
        if high_total > 0:
            notes.append(
                f"{high_total} HIGH reported (not gated — raise the threshold in the workflow if you want stricter)"
            )
        if notes:
            lines.append("")
            for n in notes:
                lines.append(f"- _Note: {n}._")

    summary = "\n".join(lines) + "\n"

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(summary)
    # Also echo to stdout so it shows in the live log
    print(summary)

    sys.exit(1 if crit_fixable > 0 else 0)


if __name__ == "__main__":
    main()
