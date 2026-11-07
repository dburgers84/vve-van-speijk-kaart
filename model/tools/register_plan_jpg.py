#!/usr/bin/env python3
"""Registreer de al gepubliceerde img/plan_*.jpg op het native frame van de lokale bronscan.

Hypothese (visueel): plan_*.jpg = native scan 90° tegen de klok gedraaid en ~0,24x verkleind.
Methode: grove schaal/offset via template matching, verfijning met OpenCV ECC (affien).
Uitvoer: data/inventory/registration_plan_jpg.json met image->native affine per verdieping.
Draai lokaal: python3 model/tools/register_plan_jpg.py --scans /workspace/vve-source-audit
"""
import argparse, json, os
import cv2, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
FLOORS = {"BG": (81, "plan_bg.jpg"), "1e": (82, "plan_1e.jpg"), "2e": (83, "plan_2e.jpg"), "3e": (84, "plan_3e.jpg"), "4e": (85, "plan_4e.jpg")}


def register(native_path, plan_path):
    N = np.array(Image.open(native_path).convert("L"))
    P = np.array(Image.open(plan_path).convert("L"))
    H, W = N.shape
    R = np.rot90(N, 1)
    Pf = cv2.GaussianBlur(255 - P, (5, 5), 0).astype(np.float32)
    t = Pf[300:1400, 300:1600]
    best = None
    for s in np.linspace(0.225, 0.255, 13):
        Rs = cv2.resize(R, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        Rf = cv2.GaussianBlur(255 - Rs, (5, 5), 0).astype(np.float32)
        if t.shape[0] > Rf.shape[0] or t.shape[1] > Rf.shape[1]:
            continue
        m = cv2.matchTemplate(Rf, t, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(m)
        if best is None or mx > best[0]:
            best = (mx, s, loc)
    mx, s, (lx, ly) = best
    n2p0 = np.array([[0, s, 300 - lx], [-s, 0, s * (W - 1) - ly + 300], [0, 0, 1]], np.float64)
    k = 0.25
    Nd = cv2.resize(N, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    S = np.diag([k, k, 1.0])
    p2nd0 = (S @ np.linalg.inv(n2p0))[:2].astype(np.float32)
    tpl = cv2.GaussianBlur(255 - P, (3, 3), 0).astype(np.float32) / 255
    inp = cv2.GaussianBlur(255 - Nd, (3, 3), 0).astype(np.float32) / 255
    cc, Wr = cv2.findTransformECC(tpl, inp, p2nd0, cv2.MOTION_AFFINE,
                                  (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    p2n = np.diag([1 / k, 1 / k, 1.0]) @ np.vstack([Wr, [0, 0, 1]])
    return {"image_size": [int(P.shape[1]), int(P.shape[0])], "native_size": [W, H],
            "image_to_native_affine": [[round(float(v), 6) for v in row] for row in p2n[:2]],
            "template_score": round(float(mx), 4), "ecc_correlation": round(float(cc), 4),
            "method": "rot90 hypothesis + template match + OpenCV ECC affine"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scans", default="/workspace/vve-source-audit")
    a = ap.parse_args()
    out = {"note": "image_to_native_affine: [x_native, y_native] = A @ [x_img, y_img, 1]", "floors": {}}
    for f, (page, img) in FLOORS.items():
        r = register(os.path.join(a.scans, f"page-{page}.png"), os.path.join(REPO, "img", img))
        r["page"], r["image"] = page, f"img/{img}"
        out["floors"][f] = r
        print(f, r["ecc_correlation"], r["template_score"])
    json.dump(out, open(os.path.join(ROOT, "data", "inventory", "registration_plan_jpg.json"), "w"), indent=1)
