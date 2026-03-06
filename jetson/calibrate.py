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
        
        # We need the frame width to figure out left/right lines
        H, W = frame.shape[:2]
        center_x = W / 2.0

        # 1. Detect Edges & Lines
        edges = detect_edges(frame, self.CANNY_T1, self.CANNY_T2, self.CANNY_APER)
        lines = detect_lines(edges, self.HOUGH_RHO, self.HOUGH_THETA, self.HOUGH_THRESH)

        if lines is not None:
            # --- PERFORMANCE FIX ---
            if len(lines) > self.MAX_LINES_TO_PROCESS:
                lines = lines[:self.MAX_LINES_TO_PROCESS]

            # 2. Cluster (Now safe because N is small)
            flines = cluster_lines(lines, self.RHO_BIAS, self.ANGLE_BIAS).reshape(-1, 2)
            
            # --- TILE NAVIGATION LOGIC ---
            vertical_lines = []
            
            for rho, theta in flines:
                # Normalize theta to [0, pi]
                if theta > np.pi:
                    theta -= np.pi
                    
                # A perfectly vertical line has theta approx 0 or pi
                # Our previous logic considered np.pi/2 as vertical? Let's check:
                # In OpenCV's HoughLines, theta=0 is a vertical line. theta=pi/2 is a horizontal line.
                # However, the previous logic `min_ang = min(angles, key=lambda x:abs(x-np.pi/2))` 
                # implies the robot was tracking lines that are horizontal in the camera frame?
                # Actually, no: in helpers.rotate we might have rotated it. 
                # Let's assume np.pi/2 is the target direction (straight ahead).
                
                # Check if it's "mostly vertical" (within ANGLE_BIAS of pi/2)
                if abs(theta - np.pi/2) < self.ANGLE_BIAS * 2: # Give it some wiggle room
                    # Calculate the x-intercept at the middle of the frame (y = H/2)
                    # For a line rho = x*cos(theta) + y*sin(theta)
                    # x = (rho - y*sin(theta)) / cos(theta)
                    # Note: if cos(theta) is near 0 (theta near pi/2), x is very sensitive.
                    
                    # Safe intercept calculation
                    try:
                        cal_x = (rho - (H / 2) * np.sin(theta)) / np.cos(theta)
                        vertical_lines.append({
                            'rho': rho,
                            'theta': theta,
                            'x_intercept': cal_x
                        })
                    except ZeroDivisionError:
                        pass
            
            # We need at least 1 vertical line to do anything useful, ideally 2.
            if len(vertical_lines) >= 2:
                # Sort by x_intercept to find left and right clusters
                vertical_lines.sort(key=lambda item: item['x_intercept'])
                
                # We want the line immediately to the left of center, and immediately to the right
                left_lines = [l for l in vertical_lines if l['x_intercept'] < center_x]
                right_lines = [l for l in vertical_lines if l['x_intercept'] > center_x]
                
                if left_lines and right_lines:
                    # Take the rightmost of the left lines, and leftmost of the right lines
                    left_line = left_lines[-1]
                    right_line = right_lines[0]
                    
                    # The center line is the average of their representations
                    center_theta = (left_line['theta'] + right_line['theta']) / 2.0
                    
                    # Return the estimated center angle
                    log = f'<LOG> Left X: {left_line["x_intercept"]:.1f} | Right X: {right_line["x_intercept"]:.1f} | Center: {center_theta:.3f} rad'
                    return center_theta, log
                
                elif left_lines: # Only left line visible
                    # Assume lane width is approximately half the frame width? 
                    # We just follow the left line's angle
                    log = f'<LOG> Only left lines visible. Tracking left line.'
                    return left_lines[-1]['theta'], log
                    
                elif right_lines: # Only right line visible
                    log = f'<LOG> Only right lines visible. Tracking right line.'
                    return right_lines[0]['theta'], log

            elif len(vertical_lines) == 1:
                # Only one line total
                log = f'<LOG> Only one vertical line detected. Tracking it.'
                return vertical_lines[0]['theta'], log

            # If we couldn't find good vertical lines, check if there's ANY line near pi/2
            angles = np.array(convert_angle(flines))
            if len(angles) > 0:
                min_ang = min(angles, key=lambda x:abs(x-np.pi/2)) 
                log = f'<LOG> Fallback to old logic. taken_angle: {np.rad2deg(min_ang):.1f}'
                if (np.pi/2 - self.ANGLE_BIAS) < min_ang < (self.ANGLE_BIAS + np.pi/2):
                    return min_ang, log
                    
            return None, '<LOG> Angle Not Found!'
            
        return None, '<LOG> Lines array is None!'