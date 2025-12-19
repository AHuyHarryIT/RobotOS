import cv2 as cv
import numpy as np
import json
import os
from dotenv import load_dotenv
from config import Config
from ROI import ROI
from static_stop import StaticParams, _passes_shape_filters

# --- CONFIGURATION ---
LOAD_FROM_PROFILE = True  

# --- TUNING PARAMETERS ---
MIN_SIGMA_LAB = 4.0        # Keep strict for Color/Lightness
MIN_SIGMA_S   = 15.0       # <--- INCREASED: High noise floor for Saturation (Gloss tolerance)

SIGMA_THRESH_COLOR = 3.0   
SIGMA_THRESH_LIGHT = 6.0   
GLARE_SIGMA_THRESH = 3.0   
CONSISTENT_FRAMES_NEEDED = 2

# Visualization
OUTPUT_VIDEO_NAME = "./jetson/histogram/analysis_refined_sensitivity_v3.avi"
PROFILE_FILENAME = "./jetson/floor_profile_v2.json"

load_dotenv(override=True)
VIDEO_PATH = Config.VIDEO_PATH
ROI_PATH = Config.ROI_PT_PATH
params = StaticParams()

def load_roi(w, h):
    if not os.path.exists(ROI_PATH): return None, None, []
    roi_helper = ROI(saved_path=ROI_PATH, W=w, H=h)
    roi_helper.load_points()
    roi_mask, danger_mask = roi_helper.build_masks((h, w), danger_frac=0.85, edge_pad=0)
    return roi_mask, danger_mask, roi_helper.corner_points

def save_profile(stats):
    with open(PROFILE_FILENAME, 'w') as f:
        json.dump(stats, f, indent=4)
    print(f"[INFO] Profile saved to {PROFILE_FILENAME}")

def load_profile():
    if not os.path.exists(PROFILE_FILENAME): return None
    try:
        with open(PROFILE_FILENAME, 'r') as f: return json.load(f)
    except: return None

def analyze_full_video():
    print("="*60)
    print(" 1. REFINED PROFILING (Separate S-Sigma)")
    print("="*60)
    
    cap = cv.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"[ERR] Could not open video: {VIDEO_PATH}")
        return

    W = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    FPS = cap.get(cv.CAP_PROP_FPS)
    
    roi_mask, _, roi_pts = load_roi(W, H)
    if roi_mask is None: roi_mask = np.ones((H, W), dtype=np.uint8) * 255
    roi_pix = max(1, int(np.count_nonzero(roi_mask)))

    stats = None
    if LOAD_FROM_PROFILE: stats = load_profile()
    
    if stats is None:
        print("[INFO] Learning Phase...")
        s_L, s_A, s_B, s_S = [], [], [], [] 
        
        for i in range(50):
            ok, frame = cap.read()
            if not ok: break
            
            blur = cv.GaussianBlur(frame, (5,5), 0)
            lab = cv.cvtColor(blur, cv.COLOR_BGR2LAB)
            L, A, B = cv.split(lab)
            hsv = cv.cvtColor(blur, cv.COLOR_BGR2HSV)
            _, S, _ = cv.split(hsv)
            
            mask_indices = np.where(roi_mask > 0)
            if len(mask_indices[0]) > 0:
                idx = np.random.choice(len(mask_indices[0]), 1000)
                s_L.extend(L[mask_indices[0][idx], mask_indices[1][idx]])
                s_A.extend(A[mask_indices[0][idx], mask_indices[1][idx]])
                s_B.extend(B[mask_indices[0][idx], mask_indices[1][idx]])
                s_S.extend(S[mask_indices[0][idx], mask_indices[1][idx]])
        
        # Calculate Stats with SEPARATE Clamps
        stats = {
            "L": {"mean": float(np.mean(s_L)), "sigma": float(max(np.std(s_L), MIN_SIGMA_LAB))},
            "A": {"mean": float(np.mean(s_A)), "sigma": float(max(np.std(s_A), MIN_SIGMA_LAB))},
            "B": {"mean": float(np.mean(s_B)), "sigma": float(max(np.std(s_B), MIN_SIGMA_LAB))},
            # Use the higher Clamp for S
            "S": {"mean": float(np.mean(s_S)), "sigma": float(max(np.std(s_S), MIN_SIGMA_S))}
        }
        cap.set(cv.CAP_PROP_POS_FRAMES, 0)
        save_profile(stats)

    mu_L, sig_L = stats["L"]["mean"], stats["L"]["sigma"]
    mu_A, sig_A = stats["A"]["mean"], stats["A"]["sigma"]
    mu_B, sig_B = stats["B"]["mean"], stats["B"]["sigma"]
    mu_S, sig_S = stats["S"]["mean"], stats["S"]["sigma"]

    print(f"[STATS] L:{mu_L:.1f}/{sig_L:.1f}  A:{mu_A:.1f}/{sig_A:.1f}  B:{mu_B:.1f}/{sig_B:.1f}")
    print(f"[STATS] S:{mu_S:.1f}/{sig_S:.1f} (High Noise Floor Applied)")

    print("\n" + "="*60)
    print(" 2. PROCESSING")
    print("="*60)
    
    fourcc = cv.VideoWriter_fourcc(*'XVID')
    out = cv.VideoWriter(OUTPUT_VIDEO_NAME, fourcc, FPS, (W * 2, H))
    
    consecutive_detections = 0
    
    while True:
        ok, frame = cap.read()
        if not ok: break

        blur = cv.GaussianBlur(frame, (5,5), 0)
        
        lab = cv.cvtColor(blur, cv.COLOR_BGR2LAB)
        L, A, B = cv.split(lab)
        hsv = cv.cvtColor(blur, cv.COLOR_BGR2HSV)
        _, S, _ = cv.split(hsv)

        # 1. Z-Scores
        z_A = np.abs(A - mu_A) / (sig_A + 1e-6)
        z_B = np.abs(B - mu_B) / (sig_B + 1e-6)
        z_S = np.abs(S - mu_S) / (sig_S + 1e-6)
        
        # 2. Masks
        mask_A = (z_A > SIGMA_THRESH_COLOR).astype(np.uint8) * 255
        mask_B = (z_B > SIGMA_THRESH_COLOR).astype(np.uint8) * 255
        mask_S = (z_S > SIGMA_THRESH_COLOR).astype(np.uint8) * 255
        
        diff_L = mu_L - L 
        mask_L = (diff_L > (sig_L * SIGMA_THRESH_LIGHT)).astype(np.uint8) * 255

        mask_combined = cv.bitwise_or(mask_L, mask_A)
        mask_combined = cv.bitwise_or(mask_combined, mask_B)
        mask_combined = cv.bitwise_or(mask_combined, mask_S)
        
        # 3. Glare Veto (Applies to ALL channels)
        # If it's too bright, we ignore everything (even weird saturation)
        is_glare = (L > (mu_L + sig_L * GLARE_SIGMA_THRESH))
        mask_combined[is_glare] = 0

        # 4. Shape Filtering
        mask_final = cv.bitwise_and(mask_combined, roi_mask)
        
        # INCREASED KERNEL SIZE (3x3 -> 5x5) to remove "Blue Noise"
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (5,5))
        mask_final = cv.morphologyEx(mask_final, cv.MORPH_OPEN, kernel)
        
        num, lbl, stats_cc, _ = cv.connectedComponentsWithStats(mask_final, connectivity=4)
        
        frame_has_object = False
        vis_frame = frame.copy()
        
        if roi_pts:
            pts = np.array(roi_pts, np.int32).reshape((-1, 1, 2))
            cv.polylines(vis_frame, [pts], True, (255, 255, 0), 2)

        for i in range(1, num):
            x, y, w, h, area = stats_cc[i]
            passed, fill, elong = _passes_shape_filters(w, h, area, params)
            
            # Ratio check
            area_pct = (100.0 * area / roi_pix) if area > 0 else 0.0
            passed_pct = area_pct >= params.AREA_PCT
            
            if passed and passed_pct:
                frame_has_object = True
                cv.rectangle(vis_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                cx, cy = x + w//2, y + h//2
                trigger = ""
                if mask_L[cy, cx]: trigger += "DRK "
                if mask_S[cy, cx]: trigger += "SAT "
                if mask_A[cy, cx] or mask_B[cy, cx]: trigger += "COL"
                
                cv.putText(vis_frame, f"{trigger}", (x, y-5), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                # Show rejected noise in RED to confirm we are filtering it out
                cv.rectangle(vis_frame, (x, y), (x+w, y+h), (0, 0, 255), 1)

        if frame_has_object: consecutive_detections += 1
        else: consecutive_detections = 0
            
        status_text = "CLEAR"
        col = (0, 255, 0)
        if consecutive_detections >= CONSISTENT_FRAMES_NEEDED:
            status_text = f"STOP ({consecutive_detections})"
            col = (0, 0, 255)

        cv.putText(vis_frame, status_text, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)
        
        vis_mask = cv.cvtColor(mask_final, cv.COLOR_GRAY2BGR)
        s_only = cv.bitwise_and(mask_S, roi_mask)
        vis_mask[s_only > 0] = [255, 0, 0] # Blue for Saturation
        
        out.write(np.hstack((vis_frame, vis_mask)))

    cap.release()
    out.release()
    print(f"\n[DONE] Saved to {OUTPUT_VIDEO_NAME}")

if __name__ == "__main__":
    analyze_full_video()