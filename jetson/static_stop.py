# static_stop.py
import cv2 as cv
import numpy as np
from floor_profiler import FloorProfiler

class StaticParams:
    def __init__(self,
                 DEBUG_STATIC=False,
                 THR_MODE="fixed",     # "fixed" | "flex"
                 THR_L=135,
                 THR_OFFSET=2,
                 ILLUM_NORM="none",      # "none" | "flatfield" | "clahe"
                 NORM_BLUR_K=3,         # large odd kernel for flatfield
                 NORM_EPS=1e-6,
                 CLAHE_CLIP=1.0,
                 CLAHE_TILE=8,
                 MIN_AREA=500, MIN_THICK=6, ASPECT_MAX=1.4,
                 LINE_AR_REJECT=3.0, LINE_FILL_MAX=0.22,
                 AREA_PCT=2.5, LRANGE=1.0, HRANGE=30.0, GAMMA=0.2, 
                 FLOOR_PROFILE_PATH="./jetson/config/floor_profile.json",
                 MIN_SIGMA_LAB=5.0, MIN_SIGMA_S=15.0,
                 SIGMA_THRESH_COLOR=3.0, SIGMA_THRESH_LIGHT=6.0, GLARE_SIGMA_THRESH=3.0) -> None:

        self.DEBUG = DEBUG_STATIC
        self.THR_MODE = THR_MODE
        self.THR_L = THR_L
        self.THR_OFFSET = THR_OFFSET
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
        self.LRANGE = LRANGE
        self.HRANGE = HRANGE
        self.GAMMA = GAMMA
        self.FLOOR_PROFILE_PATH = FLOOR_PROFILE_PATH

        # --- OPTIMIZATION FIX ---
        # Initialize the profiler ONCE here, not in the loop
        self.profiler = FloorProfiler(
            profile_path=FLOOR_PROFILE_PATH,
            MIN_SIGMA_LAB=MIN_SIGMA_LAB,
            MIN_SIGMA_S=MIN_SIGMA_S,
            SIGMA_THRESH_COLOR=SIGMA_THRESH_COLOR,
            SIGMA_THRESH_LIGHT=SIGMA_THRESH_LIGHT,
            GLARE_SIGMA_THRESH=GLARE_SIGMA_THRESH
        )
        
        self.profile_loaded = self.profiler.load_profile()
        if not self.profile_loaded:
            print(f"[StaticParams] WARN: Could not load floor profile from {FLOOR_PROFILE_PATH}")
        else:
            print(f"[StaticParams] Floor profile loaded successfully.")

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

def static_stop_detect(frame_ori, roi_mask, danger_mask, params: StaticParams = StaticParams()):
    """
    Static obstacle check using FloorProfiler (Color/Sat check).
    IMPORTANT: frame_ori must be BGR (Color), not Grayscale!
    """
    profiler = FloorProfiler(profile_path=params.FLOOR_PROFILE_PATH)
    
    # --- ERROR HANDLING FIX ---
    if not params.profile_loaded:
        # Return SAFE empty masks so main loop doesn't crash
        h, w = frame_ori.shape[:2]
        empty = np.zeros((h, w), dtype=np.uint8)
        return False, None, {
            "nonfloor": empty,
            "nf_danger": empty,
            "area_pct": 0, "elong": 0, "fill": 0
        }

    # Get the defect mask (Calculates Z-scores for Color/Sat/Lightness)
    nonfloor_mask = profiler.get_defect_mask(frame_ori, roi_mask)

    # Only danger band within ROI
    nf_danger = cv.bitwise_and(nonfloor_mask, danger_mask)

    # Connected components + shape filtering
    roi_pix = max(1, int(np.count_nonzero(roi_mask)))
    
    # Checking when the number of unwanted pixels exceed the satisfied ones
    # print(f'[LOG] THRESHOLD {thr}')
    if int(np.count_nonzero(nf_danger))>=int(np.count_nonzero(nf_danger==0)):
        print('[Static] Detected pixels exceed the maximum area allowed! -> STOP')
        debug = {
            "nonfloor": nonfloor_mask,
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
        "nonfloor": nonfloor_mask,
        "nf_danger": nf_danger,
        "area_pct": area_pct,
        "elong" : params_dbg[0] if params_dbg is not None else 0,
        "fill": params_dbg[1] if params_dbg is not None else 0
    }
    return stop, best_bbox, debug
