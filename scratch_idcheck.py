import re, urllib.request, collections, sys
html = urllib.request.urlopen("http://127.0.0.1:8000/").read().decode("utf8")
ids = re.findall(r'\bid="([^"]+)"', html)
dup = [k for k, v in collections.Counter(ids).items() if v > 1]
js = open("web/static/js/app.js", encoding="utf8").read()
refs = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', js)) | set(re.findall(r'getElementById\("([A-Za-z0-9_-]+)"\)', js))
missing = sorted(r for r in refs if r not in ids)
print("DUP:", dup)
# unguarded: $("x") followed by . without ?
ung = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)\.(?!\?)', js))
print("MISSING:", missing)
print("MISSING_UNGUARDED:", sorted(m for m in missing if m in ung))
