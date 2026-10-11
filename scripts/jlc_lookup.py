#!/usr/bin/env python3
"""Query the JLCPCB parts catalogue (the API its own assembly page uses).

jlc-client's search goes through a public index that is currently unreliable, so this
uses JLCPCB's own endpoint. Results include the LCSC id, stock and library type
(base = no setup fee, expand = extended), i.e. exactly what SMT assembly needs.

Usage:  python3 scripts/jlc_lookup.py "22uH inductor" ["another query" ...]
        python3 scripts/jlc_lookup.py --csv "0.33F 5.5V"      # csv output for piping
"""
import json
import sys
import time
import urllib.request

API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
HDRS = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}


def search(keyword, page_size=25, tries=4):
    body = json.dumps({"keyword": keyword, "currentPage": 1, "pageSize": page_size}).encode()
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(API, data=body, headers=HDRS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            break
        except Exception as e:  # rate limits / transient HTML interstitials
            last = e
            time.sleep(2 * (attempt + 1))
    else:
        raise SystemExit(f"query failed for {keyword!r}: {last}")
    info = (data.get("data") or {}).get("componentPageInfo") or {}
    lst = info.get("list") or []
    out = []
    for it in lst:
        url = it.get("lcscGoodsUrl") or ""
        lcsc = url.rsplit("_", 1)[-1].replace(".html", "") if "_C" in url else ""
        prices = it.get("componentPrices") or []
        out.append(dict(
            lcsc=lcsc,
            name=it.get("componentModelEn") or it.get("erpComponentName") or "",
            desc=it.get("erpComponentName") or "",
            type=it.get("componentTypeEn") or "",
            pkg=it.get("componentSpecificationEn") or "",
            stock=it.get("stockCount") or 0,
            lib=it.get("componentLibraryType") or "",
            price=(prices[0].get("price") if prices else None),
        ))
    return out, info.get("total", 0)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_csv = "--csv" in sys.argv
    for kw in args:
        rows, total = search(kw)
        time.sleep(1)
        if as_csv:
            for r in rows:
                print(f"{r['lcsc']},{r['name']},{r['type']},{r['pkg']},{r['lib']},{r['stock']},{r['price']}")
            continue
        print(f"### {kw}  ({total} matches, showing {len(rows)})")
        if not rows:
            print("  -- no parts in the JLCPCB catalogue --\n")
            continue
        for r in rows:
            lib = "BASE" if r["lib"] == "base" else r["lib"].upper()
            print(f"  {r['lcsc']:<11} {lib:<7} stk {r['stock']:>7}  {r['type'][:22]:<22} {r['pkg'][:18]:<18} {r['desc'][:56]}")
        print()


if __name__ == "__main__":
    main()
