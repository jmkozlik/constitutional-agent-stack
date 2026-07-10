#!/usr/bin/env node
// God-space SACRED MACHINERY. Usage: node clerk.js <run-id>
// Compiles the anonymized grievance digest from debriefs. Mechanical
// concatenation; strips identity; censors NOTHING; no opinions.
const fs = require('fs');
const path = require('path');
const runId = process.argv[2];
if (!runId) { console.error('usage: clerk.js <run-id>'); process.exit(1); }
const dir = (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault')) + `/executors/archive/${runId}`;
if (!fs.existsSync(dir)) { console.error(`clerk: no archive dir for ${runId}: ${dir}`); process.exit(1); }
// Numeric sort: debrief-2 before debrief-10.
const num = (f) => parseInt((f.match(/debrief-(\d+)/) || [])[1] || '0', 10);
const files = fs.readdirSync(dir).filter((f) => f.startsWith('debrief-')).sort((a, b) => num(a) - num(b));
let redactions = 0;
let out = `---\ntype: log\nlabels: [run, governance]\nrun-id: ${runId}\nstatus: final\n---\n# Grievance Digest — ${runId} (clerk-compiled, anonymized, complete)\n`;
files.forEach((f, i) => {
  const body = fs.readFileSync(path.join(dir, f), 'utf8')
    .replace(/^---[\s\S]*?---\n/, '')            // strip frontmatter (has agent id)
    .replace(/^# Debrief.*$/m, '')               // strip identifying title
    // Body-level identity scrub: agent-id lines and state-note paths leak
    // identity even inside prose. Redact, never drop the rest of the line's
    // section — anonymity and completeness are BOTH promises.
    .replace(/^.*\bagent:\s*\S+.*$/gim, () => { redactions++; return '[identity-line redacted by clerk]'; })
    .replace(/executors\/active\/\S+/g, () => { redactions++; return '[state-note]'; })
    .trim();
  out += `\n## Executor ${i + 1} (anonymized)\n${body}\n`;
});
fs.writeFileSync(path.join(dir, 'digest.md'), out);
console.log(`digest.md written: ${files.length} debriefs compiled, 0 dropped, ${redactions} identity redactions`);
