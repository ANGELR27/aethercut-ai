import re, sys
f = sys.argv[1]; pat = sys.argv[2]
for i, l in enumerate(open(f, encoding="utf8", errors="ignore").read().split("\n")):
    if re.search(pat, l):
        print(i + 1, l[:160])
