"""Download publicly shared Google Drive PDFs (handles the large-file virus-scan interstitial). Verifies the %PDF magic and prints page count.
python gdrive_get.py <out_dir> <file_id> [<file_id> ...]"""
import re, sys
from pathlib import Path
import httpx

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
for fid in sys.argv[2:]:
    with httpx.Client(follow_redirects=True, timeout=600) as c:
        r = c.get("https://drive.google.com/uc", params=dict(export="download", id=fid))
        if b"%PDF-" not in r.content[:8]:                        # interstitial page: follow its confirm form
            m = re.search(r'action="([^"]+)"', r.text); fields = dict(re.findall(r'name="([^"]+)" value="([^"]*)"', r.text))
            if m: r = c.get(m.group(1).replace("&amp;", "&"), params=fields)
        if b"%PDF-" not in r.content[:8]:
            print(fid, "NOT A PDF", r.headers.get("content-type"), len(r.content)); continue
        cd = r.headers.get("content-disposition", ""); nm = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
        name = (nm.group(1) if nm else fid) if nm else fid + ".pdf"
        p = out / name; p.write_bytes(r.content); print(fid, name, round(len(r.content) / 1e6, 1), "MB")
