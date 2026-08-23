#!/usr/bin/env node
// Extract cli.js from an ARBITRARY native binary (not the live symlink) by
// calling tweakcc-fixed's dist entry point directly, and verify the version.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const [bin, ver, out] = process.argv.slice(2);
if (!bin || !ver || !out) { console.error('usage: extract-clijs.mjs <binary> <version> <out>'); process.exit(1); }
const distDir = path.join(os.homedir(), 'repos/tweakcc-fixed/dist');
const mod = fs.readdirSync(distDir).find((f) => /^nativeInstallation-.*\.mjs$/.test(f));
if (!mod) { console.error('dist nativeInstallation module not found - run pnpm build'); process.exit(2); }
const { extractClaudeJsFromNativeInstallation } = await import(path.join(distDir, mod));
const r = await extractClaudeJsFromNativeInstallation(bin, ver);
const data = r?.data ?? r;
const buf = Buffer.isBuffer(data) ? data : Buffer.from(String(data));
if (buf.length < 1_000_000) { console.error(`extracted cli.js too small: ${buf.length} bytes`); process.exit(3); }
const first = (buf.toString('utf8').match(/\d+\.\d+\.\d+/) || [])[0];
if (first !== ver) { console.error(`extracted version ${first} != requested ${ver} (wrong binary?)`); process.exit(4); }
fs.writeFileSync(out, buf);
console.log(`extracted ${(buf.length / 1048576).toFixed(1)}MB -> ${out} (version ${first})`);
