import cv2 as cv
import numpy as np
import json
import os

class FloorProfiler:
    def __init__(self, profile_path="floor_profile.json", MIN_SIGMA_LAB=4.0, MIN_SIGMA_S=15.0,
                 SIGMA_THRESH_COLOR=3.0, SIGMA_THRESH_LIGHT=6.0, GLARE_SIGMA_THRESH=3.0):
        self.profile_path = profile_path
        self.stats = None
        
        # --- TUNING PARAMETERS ---
        # "Panic thresholds" to ignore tile grout or slight noise
        self.MIN_SIGMA_LAB = MIN_SIGMA_LAB   # Strict for Color/Lightness
        self.MIN_SIGMA_S = MIN_SIGMA_S    # Loose for Saturation (Glossy floor tolerance)
        
        # Z-Score Thresholds (How many sigmas away is an "object"?)
        self.SIGMA_THRESH_COLOR = SIGMA_THRESH_COLOR
        self.SIGMA_THRESH_LIGHT = SIGMA_THRESH_LIGHT
        self.GLARE_SIGMA_THRESH = GLARE_SIGMA_THRESH  # Veto bright spots

    def learn_from_frames(self, frames, roi_mask=None):
        """
        Input: List of frames (or a generator).
        Output: Calculates and stores the floor statistics.
        """
        print(f"[FloorProfiler] Learning from {len(frames)} frames...")
        s_L, s_A, s_B, s_S = [], [], [], []
        
        if roi_mask is None:
            h, w = frames[0].shape[:2]
            roi_mask = np.ones((h, w), dtype=np.uint8) * 255

        for frame in frames:
            blur = cv.GaussianBlur(frame, (5, 5), 0)
            
            # LAB Space
            lab = cv.cvtColor(blur, cv.COLOR_BGR2LAB)
            L, A, B = cv.split(lab)
            
            # HSV Space (Saturation only)
            hsv = cv.cvtColor(blur, cv.COLOR_BGR2HSV)
            _, S, _ = cv.split(hsv)
            
            # Sample pixels inside ROI
            mask_indices = np.where(roi_mask > 0)
            if len(mask_indices[0]) > 0:
                # Random subsample to keep memory low (1000 pixels per frame)
                idx = np.random.choice(len(mask_indices[0]), 1000)
                s_L.extend(L[mask_indices[0][idx], mask_indices[1][idx]])
                s_A.extend(A[mask_indices[0][idx], mask_indices[1][idx]])
                s_B.extend(B[mask_indices[0][idx], mask_indices[1][idx]])
                s_S.extend(S[mask_indices[0][idx], mask_indices[1][idx]])

        # Calculate Statistics with Noise Floor Clamping
        self.stats = {
            "L": {"mean": float(np.mean(s_L)), "sigma": float(max(np.std(s_L), self.MIN_SIGMA_LAB))},
            "A": {"mean": float(np.mean(s_A)), "sigma": float(max(np.std(s_A), self.MIN_SIGMA_LAB))},
            "B": {"mean": float(np.mean(s_B)), "sigma": float(max(np.std(s_B), self.MIN_SIGMA_LAB))},
            "S": {"mean": float(np.mean(s_S)), "sigma": float(max(np.std(s_S), self.MIN_SIGMA_S))}
        }
        print(f"[FloorProfiler] Profile Learned: {self.stats}")

    def save_profile(self):
        if self.stats:
            with open(self.profile_path, 'w') as f:
                json.dump(self.stats, f, indent=4)
            print(f"[FloorProfiler] Saved to {self.profile_path}")

    def load_profile(self):
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, 'r') as f:
                    self.stats = json.load(f)
                print(f"[FloorProfiler] Loaded profile from {self.profile_path}")
                return True
            except Exception as e:
                print(f"[FloorProfiler] Failed to load profile: {e}")
        return False

    def get_defect_mask(self, frame, roi_mask=None):
        """
        Input: Current frame.
        Output: Binary mask (255=Object, 0=Floor).
        This contains ONLY the math (Z-scores, Veto, Morph).
        """
        if self.stats is None:
            # Fallback if no profile: return empty mask
            return np.zeros(frame.shape[:2], dtype=np.uint8)

        # Unpack stats for speed
        mu_L, sig_L = self.stats["L"]["mean"], self.stats["L"]["sigma"]
        mu_A, sig_A = self.stats["A"]["mean"], self.stats["A"]["sigma"]
        mu_B, sig_B = self.stats["B"]["mean"], self.stats["B"]["sigma"]
        mu_S, sig_S = self.stats["S"]["mean"], self.stats["S"]["sigma"]

        # 1. Preprocess
        blur = cv.GaussianBlur(frame, (5, 5), 0)
        lab = cv.cvtColor(blur, cv.COLOR_BGR2LAB)
        L, A, B = cv.split(lab)
        hsv = cv.cvtColor(blur, cv.COLOR_BGR2HSV)
        _, S, _ = cv.split(hsv)

        # 2. Compute Z-Scores (Distance from Mean)
        # We add 1e-6 to sigma to avoid division by zero
        z_A = np.abs(A - mu_A) / (sig_A + 1e-6)
        z_B = np.abs(B - mu_B) / (sig_B + 1e-6)
        z_S = np.abs(S - mu_S) / (sig_S + 1e-6)

        # 3. Generate Channel Masks
        # Color & Saturation: Strict symmetric check
        mask_A = (z_A > self.SIGMA_THRESH_COLOR).astype(np.uint8) * 255
        mask_B = (z_B > self.SIGMA_THRESH_COLOR).astype(np.uint8) * 255
        mask_S = (z_S > self.SIGMA_THRESH_COLOR).astype(np.uint8) * 255
        
        # Lightness: Loose directional check (Only look for DARK objects)
        diff_L = mu_L - L
        mask_L = (diff_L > (sig_L * self.SIGMA_THRESH_LIGHT)).astype(np.uint8) * 255

        # 4. Combine Masks
        mask_combined = cv.bitwise_or(mask_L, mask_A)
        mask_combined = cv.bitwise_or(mask_combined, mask_B)
        mask_combined = cv.bitwise_or(mask_combined, mask_S)

        # 5. Glare Veto (The "Sunblock")
        # If a pixel is significantly BRIGHTER than the floor mean, ignore it.
        # It's likely a reflection, even if the saturation is weird.
        is_glare = (L > (mu_L + sig_L * self.GLARE_SIGMA_THRESH))
        mask_combined[is_glare] = 0

        # 6. Apply ROI
        if roi_mask is not None:
            mask_combined = cv.bitwise_and(mask_combined, roi_mask)

        # 7. Morphological Cleanup ("Blue Noise" Removal)
        # Use 5x5 kernel to eat up small salt-and-pepper noise
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (5, 5))
        mask_final = cv.morphologyEx(mask_combined, cv.MORPH_OPEN, kernel)
        
        # Optional: Close gaps in solid objects
        mask_final = cv.morphologyEx(mask_final, cv.MORPH_CLOSE, kernel)

        return mask_final