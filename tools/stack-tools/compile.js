#!/usr/bin/env node
'use strict';

// compile.js — single-source law re-assembly for agent definitions.
//
// Regenerates law-embedded agent defs from vault law (core.md + role charter)
// injected into a stored BODY TEMPLATE, writing ONLY to a STAGING dir. NEVER
// writes to the live agents dir. Gated by an INDEPENDENT SHA-256 match against
// a chair-recorded hash file.
//
// Node builtins only. No deps.
//
// Modes:
//   compile (default):
//     node compile.js --vault PATH --agents-dir PATH --staging-dir PATH \
//                     --templates PATH --manifest PATH [--hashes PATH]
//   extract (build step — regenerate templates/ from live defs):
//     node compile.js --extract --agents-dir PATH --templates PATH --manifest PATH

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MARKER = '@@AGENT-STACK-LAW@@';
const LAW_OPEN = '<agent-stack-law>';
const LAW_CLOSE = '</agent-stack-law>';

function die(msg) {
  process.stderr.write('compile.js: ERROR: ' + msg + '\n');
  process.exit(1);
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--extract') {
      args.extract = true;
    } else if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) {
        die('flag --' + key + ' requires a value');
      }
      args[key] = next;
      i++;
    } else {
      args._.push(a);
    }
  }
  return args;
}

function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function readManifest(manifestPath) {
  let raw;
  try {
    raw = fs.readFileSync(manifestPath, 'utf8');
  } catch (e) {
    die('cannot read manifest ' + manifestPath + ': ' + e.message);
  }
  let obj;
  try {
    obj = JSON.parse(raw);
  } catch (e) {
    die('manifest is not valid JSON: ' + e.message);
  }
  const VALID = new Set(['executor', 'observer', 'council', 'none']);
  for (const k of Object.keys(obj)) {
    if (!VALID.has(obj[k])) {
      die('manifest entry "' + k + '" has invalid charter "' + obj[k] +
          '" (must be executor|observer|council|none)');
    }
  }
  return obj;
}

// Charter basename -> charter file under <vault>/_system/charters/<name>.md
function charterPath(vault, charter) {
  return path.join(vault, '_system', 'charters', charter + '.md');
}

function corePath(vault) {
  return path.join(vault, '_system', 'core.md');
}

// Assemble the full law block (the bytes that occupy the <agent-stack-law>..
// </agent-stack-law> slot, INCLUSIVE of both tag lines).
//   line `<agent-stack-law>`\n
//   + full bytes of core.md (incl trailing newline)
//   + one blank line (\n)
//   + full bytes of role charter (incl trailing newline)
//   + line `</agent-stack-law>`\n
function assembleLawBlock(vault, charter) {
  const coreP = corePath(vault);
  const charP = charterPath(vault, charter);
  let core, char;
  try {
    core = fs.readFileSync(coreP);
  } catch (e) {
    die('cannot read core.md at ' + coreP + ': ' + e.message);
  }
  try {
    char = fs.readFileSync(charP);
  } catch (e) {
    die('cannot read charter at ' + charP + ': ' + e.message);
  }
  return Buffer.concat([
    Buffer.from(LAW_OPEN + '\n', 'utf8'),
    core,
    Buffer.from('\n', 'utf8'),
    char,
    Buffer.from(LAW_CLOSE + '\n', 'utf8'),
  ]);
}

// Split a live def into [before, after] around the law block, INCLUSIVE of the
// two tag lines. Returns null if no law block present. Errors if malformed.
function splitLawBlock(text, defName) {
  const lines = text.split('\n');
  let openIdx = -1, closeIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i] === LAW_OPEN) {
      if (openIdx !== -1) die('def ' + defName + ' has multiple ' + LAW_OPEN + ' lines');
      openIdx = i;
    }
    if (lines[i] === LAW_CLOSE) {
      closeIdx = i; // last close wins via final check below
    }
  }
  if (openIdx === -1 && closeIdx === -1) return null;
  if (openIdx === -1) die('def ' + defName + ' has ' + LAW_CLOSE + ' without ' + LAW_OPEN);
  if (closeIdx === -1) die('def ' + defName + ' has ' + LAW_OPEN + ' without ' + LAW_CLOSE);
  if (closeIdx < openIdx) die('def ' + defName + ' has law tags out of order');
  // Reconstruct using the raw byte offsets so we never lose trailing-newline info.
  // Find byte offset of start of openIdx line and end of closeIdx line.
  const before = lines.slice(0, openIdx).join('\n');
  const after = lines.slice(closeIdx + 1).join('\n');
  // before, if non-empty, is followed by a newline then LAW_OPEN; if openIdx==0
  // there is no leading newline. We rebuild template as before + (\n if before
  // non-empty or openIdx>0) ... but join semantics: original text =
  // beforeLines.join('\n') + '\n' + lawLines.join('\n') + '\n' + afterLines.join('\n')
  // provided openIdx>0 and closeIdx<last. Handle edges precisely below.
  return { lines, openIdx, closeIdx, before, after };
}

function cmdExtract(args) {
  const agentsDir = args['agents-dir'];
  const templatesDir = args.templates;
  const manifestPath = args.manifest;
  if (!agentsDir) die('--agents-dir required');
  if (!templatesDir) die('--templates required');
  if (!manifestPath) die('--manifest required');

  const manifest = readManifest(manifestPath);

  // ensure templates dir exists (owned path)
  fs.mkdirSync(templatesDir, { recursive: true });

  let count = 0;
  for (const defName of Object.keys(manifest)) {
    const charter = manifest[defName];
    const live = path.join(agentsDir, defName + '.md');
    let raw;
    try {
      raw = fs.readFileSync(live, 'utf8');
    } catch (e) {
      die('cannot read live def ' + live + ': ' + e.message);
    }

    let template;
    if (charter === 'none') {
      // utility: whole file verbatim, NO marker
      if (raw.indexOf(LAW_OPEN) !== -1) {
        die('def ' + defName + ' has charter "none" but contains a law block');
      }
      template = raw;
    } else {
      const idxOpen = raw.indexOf('\n' + LAW_OPEN + '\n');
      const startsAtBOF = raw.startsWith(LAW_OPEN + '\n');
      if (idxOpen === -1 && !startsAtBOF) {
        die('def ' + defName + ' (charter ' + charter +
            ') has no ' + LAW_OPEN + ' block — refusing to emit a law-less def');
      }
      // Compute precise byte boundaries of the law block inclusive of tag lines.
      let blockStart;
      if (startsAtBOF) {
        blockStart = 0;
      } else {
        blockStart = idxOpen + 1; // position of LAW_OPEN line (after the leading \n)
      }
      const closeNeedle = '\n' + LAW_CLOSE + '\n';
      const closeAtEnd = raw.endsWith('\n' + LAW_CLOSE);
      let blockEnd; // exclusive
      const idxClose = raw.indexOf(closeNeedle, blockStart);
      if (idxClose !== -1) {
        blockEnd = idxClose + closeNeedle.length; // include trailing newline
      } else if (closeAtEnd) {
        blockEnd = raw.length;
      } else {
        die('def ' + defName + ' has malformed law close tag');
      }
      const before = raw.slice(0, blockStart);
      const after = raw.slice(blockEnd);
      template = before + MARKER + '\n' + after;
    }

    const outPath = path.join(templatesDir, defName + '.body.md');
    safeWriteFile(outPath, template, templatesDir);
    count++;
  }
  process.stdout.write('extracted ' + count + ' templates to ' + templatesDir + '\n');
}

// Guard a write path: ensure it resolves under baseDir, and PER-FILE lstat to
// refuse writing through a symlink.
function safeWriteFile(outPath, data, baseDir) {
  const resolvedBase = fs.realpathSync(baseDir);
  // Per-file lstat: if the path exists and is a symlink, ABORT.
  let st = null;
  try {
    st = fs.lstatSync(outPath);
  } catch (e) {
    if (e.code !== 'ENOENT') die('lstat failed for ' + outPath + ': ' + e.message);
  }
  if (st && st.isSymbolicLink()) {
    die('refusing to write through symlink: ' + outPath);
  }
  if (st && !st.isFile()) {
    die('refusing to overwrite non-regular-file: ' + outPath);
  }
  // Ensure parent dir is within base (defense in depth).
  const parent = fs.realpathSync(path.dirname(outPath));
  if (parent !== resolvedBase && !parent.startsWith(resolvedBase + path.sep)) {
    die('output path escapes base dir: ' + outPath);
  }
  fs.writeFileSync(outPath, data);
}

function loadHashes(hashesPath) {
  let raw;
  try {
    raw = fs.readFileSync(hashesPath, 'utf8');
  } catch (e) {
    die('cannot read hashes file ' + hashesPath + ': ' + e.message);
  }
  const map = {};
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    // format: <hex>  <name.md>
    const m = t.match(/^([0-9a-fA-F]{64})\s+(.+)$/);
    if (!m) die('malformed hash line: ' + line);
    map[m[2].trim()] = m[1].toLowerCase();
  }
  return map;
}

function cmdCompile(args) {
  const vault = args.vault;
  const agentsDir = args['agents-dir'];
  const stagingDir = args['staging-dir'];
  const templatesDir = args.templates;
  const manifestPath = args.manifest;
  const hashesPath = args.hashes ||
    (process.env.VAULT_ROOT || require('path').join(require('os').homedir(), 'vault')) + '/executors/contracts/r003-stack-tools/DEF-HASHES.txt';

  if (!vault) die('--vault required');
  if (!agentsDir) die('--agents-dir required');
  if (!stagingDir) die('--staging-dir required');
  if (!templatesDir) die('--templates required');
  if (!manifestPath) die('--manifest required');

  // WRITE-GUARD: staging must not be the agents dir.
  const realStagingParent = (() => {
    // staging may not exist yet; resolve its eventual real path via parent.
    try {
      return fs.realpathSync(stagingDir);
    } catch (e) {
      if (e.code === 'ENOENT') return null;
      die('realpath staging failed: ' + e.message);
    }
  })();
  let realAgents;
  try {
    realAgents = fs.realpathSync(agentsDir);
  } catch (e) {
    die('realpath agents-dir failed: ' + e.message);
  }
  if (realStagingParent && realStagingParent === realAgents) {
    die('staging-dir resolves to the same path as agents-dir — refusing');
  }

  // lstat staging-dir: if it exists as a non-directory, abort.
  let stStaging = null;
  try {
    stStaging = fs.lstatSync(stagingDir);
  } catch (e) {
    if (e.code !== 'ENOENT') die('lstat staging-dir failed: ' + e.message);
  }
  if (stStaging) {
    if (stStaging.isSymbolicLink()) die('staging-dir is a symlink — refusing');
    if (!stStaging.isDirectory()) die('staging-dir exists and is not a directory');
  } else {
    fs.mkdirSync(stagingDir, { recursive: true });
  }

  // Re-check: after ensuring it exists, realpath staging must differ from agents.
  const realStaging = fs.realpathSync(stagingDir);
  if (realStaging === realAgents) {
    die('staging-dir resolves to the same path as agents-dir — refusing');
  }
  // W4 hardening (panel red-teamer / refuter): staging must not be UNDER agents-dir
  // either — writing inside the live agents tree pollutes god-space even without a clobber.
  if (realStaging.startsWith(realAgents + require('path').sep)) {
    die('staging-dir resolves to a path inside agents-dir — refusing (W4)');
  }

  const manifest = readManifest(manifestPath);
  const refHashes = loadHashes(hashesPath);

  const mismatches = [];
  let compiled = 0;

  for (const defName of Object.keys(manifest)) {
    const charter = manifest[defName];
    const tplPath = path.join(templatesDir, defName + '.body.md');
    let tpl;
    try {
      tpl = fs.readFileSync(tplPath);
    } catch (e) {
      die('cannot read template ' + tplPath + ': ' + e.message);
    }

    let out;
    if (charter === 'none') {
      // utility: template is whole file verbatim, no marker expected
      if (tpl.indexOf(MARKER) !== -1) {
        die('template ' + tplPath + ' has charter "none" but contains the law marker');
      }
      out = tpl;
    } else {
      const tplStr = tpl.toString('utf8');
      const markerLine = MARKER;
      const occurrences = tplStr.split(markerLine).length - 1;
      if (occurrences === 0) {
        die('template ' + tplPath + ' (charter ' + charter +
            ') is missing the law marker ' + MARKER +
            ' — refusing to emit a law-less def');
      }
      if (occurrences > 1) {
        die('template ' + tplPath + ' has multiple law markers');
      }
      const lawBlock = assembleLawBlock(vault, charter); // Buffer, ends with \n
      // The marker occupies a full line: `...<before>@@AGENT-STACK-LAW@@\n<after>`.
      // We replace the marker token (without its trailing newline) with the law
      // block bytes MINUS the trailing newline, so the line's existing newline
      // closes the </agent-stack-law> line — matching the live layout.
      const idx = tpl.indexOf(Buffer.from(MARKER, 'utf8'));
      const before = tpl.slice(0, idx);
      const after = tpl.slice(idx + Buffer.byteLength(MARKER, 'utf8'));
      // lawBlock ends with '</agent-stack-law>\n'; strip the final newline so the
      // template's own newline after the marker provides it.
      let lawNoTrailing = lawBlock;
      if (lawBlock[lawBlock.length - 1] === 0x0a) {
        lawNoTrailing = lawBlock.slice(0, lawBlock.length - 1);
      }
      out = Buffer.concat([before, lawNoTrailing, after]);
    }

    const outPath = path.join(stagingDir, defName + '.md');
    safeWriteFile(outPath, out, stagingDir);
    compiled++;

    // GATE: independent hash match.
    const got = sha256(out);
    const want = refHashes[defName + '.md'];
    if (!want) {
      mismatches.push(defName + '.md (NO recorded hash)');
    } else if (got !== want) {
      mismatches.push(defName + '.md (got ' + got.slice(0, 12) +
        ' want ' + want.slice(0, 12) + ')');
    }
  }

  process.stdout.write('compiled ' + compiled + ' defs to ' + stagingDir + '\n');

  if (mismatches.length > 0) {
    const failTxt = 'GATE FAILED — these defs differ from recorded hashes:\n' +
      mismatches.map((m) => '  ' + m).join('\n') + '\n';
    try {
      safeWriteFile(path.join(stagingDir, '_gate-fail.txt'), failTxt, stagingDir);
    } catch (e) {
      process.stderr.write('(could not write _gate-fail.txt: ' + e.message + ')\n');
    }
    process.stderr.write(failTxt);
    process.stdout.write('GATE: FAIL (' + mismatches.length + ' mismatch)\n');
    process.exit(1);
  }

  process.stdout.write('GATE: PASS (all ' + compiled + ' hashes match)\n');
  process.exit(0);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.extract) {
    cmdExtract(args);
  } else {
    cmdCompile(args);
  }
}

main();
