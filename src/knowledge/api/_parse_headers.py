import os, re, json, glob

inc = r"C:\Program Files\ZWSOFT\ZW3D 2025\api\inc"
out_dir = r"C:\Users\infoa\EfestoAI\knowledge\api"
os.makedirs(out_dir, exist_ok=True)

headers = sorted(glob.glob(os.path.join(inc, "*.h")))
print("header totali:", len(headers))

pat = re.compile(r'^\s*ZW_API_C\s+([A-Za-z_][A-Za-z0-9_\s\*]*?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*;', re.S|re.M)

all_decls = {}
by_header = {}
for h in headers:
    name_h = os.path.basename(h)
    txt = open(h, encoding='utf-8', errors='ignore').read().replace('\r', '')
    no_block = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
    no_comment = re.sub(r'//.*', '', no_block)
    found = pat.findall(no_comment)
    decls = []
    for ret, nm, params in found:
        ret = re.sub(r'\s+', ' ', ret.strip())
        params = re.sub(r'\s+', ' ', params.strip())
        proto = f"{ret} {nm}({params})"
        decls.append({"header": name_h, "ret": ret, "name": nm, "params": params, "proto": proto})
    if decls:
        by_header[name_h] = decls
        for d in decls:
            all_decls.setdefault(d["name"], []).append(d)

print("header con dichiarazioni:", len(by_header))
prefix = {}
for d in all_decls.values():
    d0 = d[0]
    m = re.match(r'([A-Za-z]+)', d0["name"])
    pre = m.group(1) if m else "?"
    prefix[pre] = prefix.get(pre, 0) + 1
print("totale firme uniche estratte:", len(all_decls))
print("top prefissi:", sorted(prefix.items(), key=lambda x:-x[1])[:30])

out = {"total": len(all_decls), "by_prefix": prefix,
       "entries": [{"name": k, "header": v[0]["header"], "ret": v[0]["ret"], "params": v[0]["params"], "proto": v[0]["proto"], "alt_headers": sorted({x["header"] for x in v[1:]})} for k,v in sorted(all_decls.items())]}
with open(os.path.join(out_dir, "ZW3D-NATIVE-SIGNATURES.json"), "w") as f:
    json.dump(out, f, indent=1)
print("scritto ZW3D-NATIVE-SIGNATURES.json con", out["total"], "firme")

# by header
bh = {h: [d["proto"] for d in decls] for h, decls in by_header.items()}
with open(os.path.join(out_dir, "ZW3D-SIGNATURES-BY-HEADER.json"), "w") as f:
    json.dump(bh, f, indent=1)
print("scritto ZW3D-SIGNATURES-BY-HEADER.json con", len(bh), "header")
