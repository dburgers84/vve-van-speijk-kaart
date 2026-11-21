#!/usr/bin/env python3
"""Nummercontrole over alle bladen: welke indexnummers 181-356 (85 woningen 181-265 + 91 bergingen 266-356, ondersplitsing)
staan als vak op welk blad. Leest de gebouwde datasets (bg, f1-f4); schrijft data/inventory/number_check.json.
'Dubbel' = op meer dan één blad (bij woningen meestal een meerlaagse woning/maisonnette: niet als fout gemarkeerd,
wel gerapporteerd); 'dubbel op één blad' = twee vakken met hetzelfde nummer op hetzelfde blad (te controleren)."""
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = [("BG", "bg.v2.json", 81), ("1e", "f1.v2.json", 82), ("2e", "f2.v2.json", 83), ("3e", "f3.v2.json", 84), ("4e", "f4.v2.json", 85)]
WON, BERG = range(181, 266), range(266, 357)
KINDS = {"apartment_dwelling": "woning", "storage_unit": "berging", "apartment_part": "deel (onzeker)"}


def run():
    where = defaultdict(list)
    for fl, fn, page in SETS:
        with open(os.path.join(ROOT, "data", fn), encoding="utf-8") as f:
            d = json.load(f)
        for o in d["objects"]:
            n = o.get("index_number")
            if n and str(n).isdigit() and 181 <= int(n) <= 356 and o["kind"] in KINDS:
                where[int(n)].append({"floor": fl, "page": page, "object_id": o["id"], "kind": KINDS[o["kind"]]})
    def full(n):
        return [w for w in where.get(n, []) if w["kind"] != "deel (onzeker)"]
    out = {
        "generated_by": "tools/number_check.py",
        "expected": {"woningen": "181-265 (85)", "bergingen": "266-356 (91)"},
        "woningen_found": sum(1 for n in WON if full(n)), "bergingen_found": sum(1 for n in BERG if full(n)),
        "woningen_missing": [n for n in WON if not full(n)], "bergingen_missing": [n for n in BERG if not full(n)],
        "woningen_on_multiple_sheets": {str(n): sorted({w["floor"] for w in full(n)}, key=[s[0] for s in SETS].index)
                                        for n in WON if len({w["floor"] for w in full(n)}) > 1},
        "bergingen_on_multiple_sheets": {str(n): sorted({w["floor"] for w in full(n)}) for n in BERG if len({w["floor"] for w in full(n)}) > 1},
        "duplicate_on_same_sheet": {str(n): [w["object_id"] for w in full(n)] for n in where
                                    if len(full(n)) != len({w["floor"] for w in full(n)})},
        "wrong_kind_for_range": [w | {"number": n} for n, ws in where.items() for w in ws
                                 if (n in WON and w["kind"] == "berging") or (n in BERG and w["kind"] == "woning")],
        "parts_only": {str(n): [w["object_id"] for w in ws] for n, ws in where.items() if ws and not full(n)},
        "by_number": {str(n): where[n] for n in sorted(where)},
        "note": "Meerdere bladen bij woningen 216-225, 230-237 en 256-259: vermoedelijk meerlaagse woningen (dezelfde nummers op de "
                "opeenvolgende verdiepingen); niet als fout aangemerkt, niet bewezen.",
    }
    with open(os.path.join(ROOT, "data", "inventory", "number_check.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    o = run()
    print("woningen", o["woningen_found"], "/85 ontbrekend", o["woningen_missing"])
    print("bergingen", o["bergingen_found"], "/91 ontbrekend", o["bergingen_missing"])
    print("meerdere bladen", o["woningen_on_multiple_sheets"], o["bergingen_on_multiple_sheets"])
    print("dubbel op één blad", o["duplicate_on_same_sheet"], "verkeerde soort", o["wrong_kind_for_range"], "alleen deel", o["parts_only"])
