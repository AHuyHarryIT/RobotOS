import numpy as np
from helpers import convert_angle, cluster_lines, detect_edges, detect_lines

class Calibrate:
    def __init__(self,
        CANNY_T1 = 40,
        CANNY_T2 = 120,
        CANNY_APER = 3,
        HOUGH_RHO = 1,
        HOUGH_THETA = np.pi / 180,
        HOUGH_THRESH = 40,
        ANGLE_BIAS = 0.3,
        RHO_BIAS = 20,
        MAX_LINES_TO_PROCESS = 30): # NEW PARAMETER

        self.CANNY_T1=CANNY_T1
        self.CANNY_T2=CANNY_T2
        self.CANNY_APER=CANNY_APER
        self.HOUGH_RHO=HOUGH_RHO
        self.HOUGH_THETA=HOUGH_THETA
        self.HOUGH_THRESH=HOUGH_THRESH
        self.RHO_BIAS=RHO_BIAS
        self.ANGLE_BIAS=ANGLE_BIAS
        self.MAX_LINES_TO_PROCESS = MAX_LINES_TO_PROCESS # Store it

    def update(self, frame):
        frame_ori = frame.copy()

        # 1. Detect Edges & Lines
        edges = detect_edges(frame, self.CANNY_T1, self.CANNY_T2, self.CANNY_APER)
        lines = detect_lines(edges, self.HOUGH_RHO, self.HOUGH_THETA, self.HOUGH_THRESH)

        if lines is not None:
            # --- PERFORMANCE FIX ---
            # HoughLines returns lines sorted by strength (votes).
            # We slice the list to keep only the Top N strongest lines.
            # This prevents the O(N^2) clustering loop from exploding.
            if len(lines) > self.MAX_LINES_TO_PROCESS:
                # Optional: Print warning to debug log if it happens often
                # print(f"[Calib] Capping lines: {len(lines)} -> {self.MAX_LINES_TO_PROCESS}")
                lines = lines[:self.MAX_LINES_TO_PROCESS]

            # 2. Cluster (Now safe because N is small)
            flines = cluster_lines(lines, self.RHO_BIAS, self.ANGLE_BIAS).reshape(-1, 2)
            angles = np.array(convert_angle(flines))
            
            # ... (Rest of your logic remains identical) ...
            min_ang = min(angles, key=lambda x:abs(x-np.pi/2)) 
            log = f'<LOG> max_angle: {np.rad2deg(np.max(angles))} min_angle: {np.rad2deg(np.min(angles))} taken_angle: '
            
            if (np.pi/2 - self.ANGLE_BIAS) < min_ang < (self.ANGLE_BIAS + np.pi/2):
                return min_ang, log + str(np.rad2deg(min_ang))
            return None, log + 'None'
            
        return None, '<LOG> Angle Not Found!'