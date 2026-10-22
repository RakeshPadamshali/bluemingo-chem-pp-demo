"""Build the offline bundle.

    python tools/build_zip.py [--out DIR]

Everything the demo needs to run with no server and no internet: the pages, the generated data, the vendored fonts,
icons and libraries, and `serve.py` for anyone who would rather open it over http. The verifiers, the screenshots and
the generator's cache are left out — this is the thing you hand over, not the thing you build with.
"""
import io
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(ROOT), "..", "Projects", "POC", "Bluemingo_Chemical_Spreciality")
for i, a in enumerate(sys.argv):
    if a == "--out" and i + 1 < len(sys.argv):
        OUT = sys.argv[i + 1]
OUT = os.path.abspath(OUT)
NAME = "Bluemingo_Chem_PP_Demo_offline.zip"

SKIP_DIRS = {"__pycache__", ".git", "shots", ".idea", ".vscode"}
SKIP_EXT = {".zip", ".pyc", ".log"}
# tools/ carries the verifiers and the generator; only the generator and the server are worth shipping
KEEP_TOOLS = {"generate_data.py", "build_zip.py"}

OPEN_ME = """Bluemingo PP - Specialty Chemicals & APIs
=========================================

Open index.html.

It runs with no server and no internet: the fonts, icons and every library are inside this folder, and a verifier
fails the build if any request would leave the site.

If your browser blocks local files from reading each other (some do, for pages opened straight off the disk), run:

    python serve.py

and open the address it prints.

Everything in the dataset is fictional. The plant, the products, the customers and the volumes are generated; what is
not invented is the shape of the rules. `python tools/generate_data.py` rewrites the whole dataset against the current
date, so the demo is never stale.
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    target = os.path.join(OUT, NAME)
    n, bytes_in = 0, 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            rel = os.path.relpath(base, ROOT).replace("\\", "/")
            if rel == ".":
                rel = ""
            if rel.startswith("tools"):
                files = [f for f in files if f in KEEP_TOOLS] if rel == "tools" else []
                if rel.startswith("tools/gen"):
                    files = [f for f in os.listdir(base) if f.endswith(".py")]
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() in SKIP_EXT:
                    continue
                p = os.path.join(base, f)
                arc = (rel + "/" + f) if rel else f
                z.write(p, arc)
                n += 1
                bytes_in += os.path.getsize(p)
        z.writestr("OPEN ME.txt", OPEN_ME)
        n += 1
    print("wrote %s" % target)
    print("  %d files, %.2f MB in, %.2f MB zipped" % (n, bytes_in / 1e6, os.path.getsize(target) / 1e6))


if __name__ == "__main__":
    main()
