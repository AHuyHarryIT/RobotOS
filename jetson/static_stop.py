# static_stop.py
import cv2 as cv
import numpy as np

class StaticParams:
    def __init__(self,
                 DEBUG_STATIC=False,
                 THR_MODE="fixed",     # "fixed" | "flex"
                 THR_L=135,
                 THR_OFFSET=2,
                 ILLUM_NORM="none",      # "none" | "flatfield" | "clahe"
                 NORM_BLUR_K=41,         # large odd kernel for flatfield
                 NORM_EPS=1e-6,
                 CLAHE_CLIP=2.0,
                 CLAHE_TILE=8,
                 MIN_AREA=500, MIN_THICK=6, ASPECT_MAX=1.4,
                 LINE_AR_REJECT=3.0, LINE_FILL_MAX=0.22,
                 AREA_PCT=2.5) -> None:
        self.DEBUG = DEBUG_STATIC

        # Threshold config
        self.THR_MODE = THR_MODE
        self.THR_L = THR_L
        self.THR_OFFSET = THR_OFFSET

        # Other params
        self.MIN_AREA = MIN_AREA
        self.MIN_THICK = MIN_THICK
        self.ASPECT_MAX = ASPECT_MAX
        self.LINE_AR_REJECT = LINE_AR_REJECT
        self.LINE_FILL_MAX = LINE_FILL_MAX
        self.AREA_PCT = AREA_PCT
        self.MORPH = (3, 3)

        self.ILLUM_NORM = ILLUM_NORM
        self.NORM_BLUR_K = NORM_BLUR_K
        self.NORM_EPS = NORM_EPS
        self.CLAHE_CLIP = CLAHE_CLIP
        self.CLAHE_TILE = CLAHE_TILE

    def normalize_L(self, L, roi_mask):
        """Return illumination-normalized L (uint8 0..255)."""
        L_roi = cv.bitwise_and(L, L, mask=roi_mask)

        if self.ILLUM_NORM == "none":
            return L_roi

        if self.ILLUM_NORM == "clahe":
            clahe = cv.createCLAHE(
                clipLimit=float(self.CLAHE_CLIP),
                tileGridSize=(int(self.CLAHE_TILE), int(self.CLAHE_TILE))
            )
            return clahe.apply(L_roi)

        if self.ILLUM_NORM == "flatfield":
            k = int(self.NORM_BLUR_K)
            if k % 2 == 0:  # must be odd
                k += 1
            bg = cv.GaussianBlur(L_roi, (k, k), 0)
            # division-based flatfield
            Lf = L_roi.astype(np.float32) / (bg.astype(np.float32) + float(self.NORM_EPS))
            Lf = cv.normalize(Lf, None, 0, 255, cv.NORM_MINMAX)
            return Lf.astype(np.uint8)

        # fallback
        return L_roi
    def compute_thr_L(self, L_img, roi_mask=None):
        """
        Return threshold for LAB L channel (0..255).

        L_img: uint8 image (often L_norm or L_roi)
        roi_mask: optional uint8 mask (0/255). If provided, stats are computed only inside ROI.
        """

        # Fixed threshold
        if str(self.THR_MODE).lower() == "fixed":
            return int(np.clip(self.THR_L, 0, 255))

        # Build a 1D vector of pixels to measure (exclude masked-out zeros)
        if roi_mask is not None:
            vals = L_img[roi_mask > 0]
        else:
            # fallback: ignore zeros (common when L_img already has ROI applied)
            vals = L_img[L_img > 0]

        if vals.size < 10:
            # not enough pixels -> fallback
            return int(np.clip(self.THR_L, 0, 255))

        # Robust range: percentiles instead of min/max (handles glare/noise)
        lo = np.percentile(vals, 10)
        hi = np.percentile(vals, 90)
        if hi <= lo:
            return int(np.clip(self.THR_L, 0, 255))

        thr = int((lo + hi) / 2.0) + int(self.THR_OFFSET)
        return int(np.clip(thr, 0, 255))

# ---------- DEBUG HELPERS----------
def _shape_metrics(w, h, area):
    box_area = max(1, w * h)
    fill  = area / float(box_area)                 # pixels / bbox area
    elong = max(w / max(1, h), h / max(1, w))      # ≥1.0; big → elongated
    return fill, elong

def _passes_shape_filters(w, h, area, p: StaticParams):
    # print(f'[LOG] THRESHOLD {p.THR_L}')
    """Same logic as before, but prints debug info."""
    fill, elong = _shape_metrics(w, h, area)

    passed = True
    reason = "PASS"
    if area < p.MIN_AREA:
        passed, reason = False, "small"
    elif min(w, h) < p.MIN_THICK:
        passed, reason = False, "thin"
    elif elong > p.ASPECT_MAX:
        passed, reason = False, "absurd"
    elif (elong >= p.LINE_AR_REJECT) or (fill <= p.LINE_FILL_MAX):
        passed, reason = False, "line"

    if p.DEBUG:
        # w,h, fill, elong + verdict
        print(f"[Static] area={area:5d} w={w:3d} h={h:3d} "
              f"fill={fill:.3f} elong={elong:.2f} → {reason}")

    return passed,fill,elong

def static_stop_detect(frame_bgr, roi_mask, danger_mask, params: StaticParams = StaticParams()):
    """
    Static obstacle check with FIXED L* threshold and shape filters.
    Returns: (stop: bool, bbox: (x,y,w,h) or None, debug dict)
    """
    lab = cv.cvtColor(frame_bgr, cv.COLOR_BGR2LAB)
    L = lab[:, :, 0]

    L_norm = params.normalize_L(L, roi_mask)   # NEW: normalize illumination
    thr = params.compute_thr_L(L_norm)         # compute threshold on normalized
    _, floor = cv.threshold(L_norm, thr, 255, cv.THRESH_BINARY)

    nonfloor = cv.bitwise_not(floor)

    # Cleanup
    kernel = cv.getStructuringElement(cv.MORPH_RECT, params.MORPH)
    nonfloor = cv.morphologyEx(nonfloor, cv.MORPH_OPEN, kernel, iterations=1)
    nonfloor = cv.morphologyEx(nonfloor, cv.MORPH_CLOSE, kernel, iterations=1)

    # Only danger band within ROI
    nf_danger = cv.bitwise_and(nonfloor, danger_mask)

    # Connected components + shape filtering
    roi_pix = max(1, int(np.count_nonzero(roi_mask)))
    
    # Checking when the number of unwanted pixels exceed the satisfied ones
    print(f'[LOG] THRESHOLD {thr}')
    if int(np.count_nonzero(nf_danger))>=int(np.count_nonzero(nf_danger==0)):
        print('[Static] Detected pixels exceed the maximum area allowed! -> STOP')
        debug = {
            "nonfloor": nonfloor,
            "nf_danger": nf_danger,
            "area_pct": 0,
            "elong" : 0,
            "fill": 0
        }
        return True, None, debug
        

    num, lbl, stats, _ = cv.connectedComponentsWithStats(nf_danger, connectivity=4)
    best_bbox, best_area, fill, elong = None, 0, 0, 0
    params_dbg=None
    for i in range(1, num):
        x, y, w2, h2, area = stats[i]
        passed,fill,elong=_passes_shape_filters(w2, h2, area, params)
        if passed:
            if area > best_area:
                best_bbox, best_area, params_dbg = (x, y, w2, h2), int(area), (elong, fill)

    # Global decision: area% over ROI polygon
    area_pct = (100.0 * best_area / roi_pix) if best_area > 0 else 0.0
    stop = area_pct >= params.AREA_PCT

    if params.DEBUG:
        print(f"[Static] Best={best_bbox} area_pct={area_pct:.2f}% STOP={stop}")

    debug = {
        "nonfloor": nonfloor,
        "nf_danger": nf_danger,
        "area_pct": area_pct,
        "elong" : params_dbg[0] if params_dbg is not None else 0,
        "fill": params_dbg[1] if params_dbg is not None else 0
    }
    return stop, best_bbox, debug
