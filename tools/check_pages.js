/* Syntax-check every page's inline script without a browser:  node tools/check_pages.js

   A literal newline inside a quoted JavaScript string is a syntax error that takes the whole page script with it — the
   cards still render from the static HTML, so the page looks merely empty rather than broken. The full page verifier
   catches it as "no JavaScript error", but only after starting a server and a browser; this names the file and the line
   in under a second, so it runs first. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.join(__dirname, '..');
const files = fs.readdirSync(root).filter(f => f.endsWith('.html')).sort();
let bad = 0, n = 0;

for (const f of files) {
  const src = fs.readFileSync(path.join(root, f), 'utf8');
  // only inline scripts (a src= tag is checked by Node when it is required, or by the page verifier)
  const re = /<script>([\s\S]*?)<\/script>/g;
  let m, i = 0;
  while ((m = re.exec(src)) !== null) {
    i++;
    const body = m[1];
    if (!body.trim()) continue;
    const before = src.slice(0, m.index);
    const startLine = before.split('\n').length;
    n++;
    try {
      new vm.Script(body, { filename: f });
    } catch (e) {
      bad++;
      // report the line in the FILE, not in the fragment
      const mm = /<anonymous>:(\d+)|:(\d+)\n/.exec(e.stack || '');
      const frag = (e.stack || '').split('\n').slice(0, 3).join(' ');
      console.log(`  FAIL ${f} (inline script ${i}, starting at file line ${startLine}): ${e.message}`);
      const lines = body.split('\n');
      const guess = lines.findIndex(l => (l.match(/'/g) || []).length % 2 === 1 && !/\\'/.test(l));
      if (guess >= 0) console.log(`       likely file line ${startLine + guess}: ${lines[guess].trim().slice(0, 120)}`);
    }
  }
}
console.log(`${bad ? 'SYNTAX FAIL' : 'SYNTAX PASS'}  ${n} inline scripts in ${files.length} pages${bad ? `, ${bad} broken` : ''}`);
process.exit(bad ? 1 : 0);
