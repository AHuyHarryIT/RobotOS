#!/usr/bin/env python3
"""
Jetson Calibration Main Program
================================
Processes camera feed for lane detection and object detection,
then sends control commands (left, right, stop) to miniPC client.

This integrates:
- Camera calibration and angle estimation
- Object detection (stop sign detection)
- Vision client to send commands to miniPC

"""

import cv2 as cv
import numpy as np
import math
import os
import time
import sys
import threading
import json
import pathlib
from datetime import datetime
import argparse
from dotenv import load_dotenv
from config import Config, reload_all_env


# Import from AUTO_CAR_V2
PARENT_ENV= os.path.dirname(__file__)
DOTENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

from ROI import ROI
from helpers import rotate, draw_arrow_by_angle
from static_stop import static_stop_detect, StaticParams
from calibrate import Calibrate

# Import vision client
from vision_client import VisionClient

# Check whether .env file exist
# dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
# print("[ENV] loading:", dotenv_path, "exists:", os.path.exists(dotenv_path))
# print("[ENV] STOP_HOLD_FRAMES =", os.getenv("STOP_HOLD_FRAMES"))



def console_stop_listener(stop_event):
    """
    Listen to stdin. If user types 'q' + Enter, set stop_event.
    Runs in a separate thread.
    """
    print("[CTRL] Type 'q' then press Enter to stop the program.")
    for line in sys.stdin:
        if line.strip().lower() == 'q':
            print("[CTRL] Stop requested via console.")
            stop_event.set()
            break

def safe_read(cap, flush=0):
    """Grab and retrieve a COMPLETE frame (avoids partial updates)."""
    for _ in range(flush):
        cap.grab()
    ok = cap.grab()
    if not ok:
        return False, None
    ok, frame = cap.retrieve()
    return ok, frame


def log_message(logfile, msg):
    """Append message with timestamp to log file."""
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(f"[{t}] {msg}\n")


def update_hold_state(hold_active, hold_remaining, detected, hold_frames):
    """
    Hold state management for object detection.
    - If not holding and detected=True -> start hold with full count.
    - If holding:
        * detected=True  -> reset hold back to full (recount from start)
        * detected=False -> decrement; if reaches 0, release hold.
    Returns: (hold_active, hold_remaining)
    """
    if not hold_active:
        if detected:
            return True, hold_frames
        return False, 0
    else:
        if detected:
            return True, hold_frames
        # no detection this frame: count down
        hold_remaining -= 1
        if hold_remaining <= 0:
            return False, 0
        return True, hold_remaining


class CommandThrottler:
    """
    Throttle command sending to avoid spamming and respect movement duration.
    Prevents sending new move commands while the car is still physically moving.
    """
    
    def __init__(self, cooldown=0.1):
        self.cooldown = cooldown
        self.last_cmd = None
        self.busy_until = 0  # Timestamp when the current move finishes
        
    def should_send(self, cmd, duration=0.0):
        """Check if we should send this command."""
        now = time.time()
        
        # --- PRIORITY: STOP ---
        # Always send STOP immediately and clear busy status so we can resume quickly
        if cmd == "stop":
            self.last_cmd = cmd
            self.busy_until = 0
            return True
        
        # --- RULE: BUSY CHECK ---
        # If the car is still executing the previous command, do not send.
        if now < self.busy_until:
            return False
        
        # --- RULE: NETWORK HYGIENE ---
        # Even if not busy, don't spam the exact same command instantly
        # (Useful if duration is 0 or very short)
        if cmd == self.last_cmd and (now < self.busy_until + self.cooldown):
            return False
        
        self.last_cmd = cmd
        self.busy_until = now + duration
        return True

def main():
    parser = argparse.ArgumentParser(description="Jetson Calibration with Vision Client")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--no-send", action="store_true", help="Disable sending commands")

    # Load .env from the same folder as this script
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

    CAM_DEVICE = Config.CAM_DEVICE
    VIDEO_PATH = Config.VIDEO_PATH
    ROI_PT_PATH = Config.ROI_PT_PATH
    W = Config.W
    H = Config.H
    FPS = Config.FPS
    OUT_SCALE = Config.OUT_SCALE
    SHOW_DEBUG_WINDOWS = Config.SHOW_DEBUG_WINDOWS
    SAVE_DEBUG_IMAGES=Config.SAVE_DEBUG_IMAGES
    USE_BLUR = Config.USE_BLUR
    BLUR_KSIZE = Config.BLUR_KSIZE
    BLUR_SIGMA = Config.BLUR_SIGMA
    SAFE_FLUSH = Config.SAFE_FLUSH
    ACCEPTANCE = Config.ACCEPTANCE
    STOP_HOLD_FRAMES = Config.STOP_HOLD_FRAMES
    SEND_COMMANDS = Config.SEND_COMMANDS
    COMMAND_COOLDOWN = Config.COMMAND_COOLDOWN
    MOVEMENT_DURATION = Config.MOVEMENT_DURATION
    MOVEMENT_DURATION_TURN = Config.MOVEMENT_DURATION_TURN
    ILLUM_NORMALIZATION=Config.ILLUM_NORMALIZATION
    DEBUG_STATIC=Config.DEBUG_STATIC
    THR_MODE=Config.THR_MODE
    THR_L=Config.THR_L
    THR_OFFSET=Config.THR_OFFSET
    MIN_AREA=Config.MIN_AREA
    MIN_THICK=Config.MIN_THICK
    ASPECT_MAX=Config.ASPECT_MAX
    LINE_AR_REJECT=Config.LINE_AR_REJECT
    LINE_FILL_MAX=Config.LINE_FILL_MAX
    AREA_PCT=Config.AREA_PCT
    FLOOR_PROFILE_PATH=Config.FLOOR_PROFILE_PATH
    ENABLE_STATIC_STOP = Config.ENABLE_STATIC_STOP
    ENABLE_CALIBRATION = Config.ENABLE_CALIBRATION
    sp = StaticParams(DEBUG_STATIC=DEBUG_STATIC,
                    THR_MODE=THR_MODE,
                    THR_L=THR_L,
                    THR_OFFSET=THR_OFFSET,
                    MIN_AREA=MIN_AREA,
                    MIN_THICK=MIN_THICK,
                    ASPECT_MAX=ASPECT_MAX,
                    LINE_AR_REJECT=LINE_AR_REJECT,
                    LINE_FILL_MAX=LINE_FILL_MAX,
                    AREA_PCT=AREA_PCT,
                    ILLUM_NORM=ILLUM_NORMALIZATION,
                    FLOOR_PROFILE_PATH=FLOOR_PROFILE_PATH)

    # -------- ENV RELOAD SETUP --------
    ENV_RELOAD_INTERVAL = 30.0  # seconds
    last_env_reload = time.time()

    # Initialize ROI
    roi_helper = ROI(
        saved_path=ROI_PT_PATH,
        ROTATE_CW_DEG=180,
        FLIPCODE=-1,
        ANGLE_TRIANGLE=math.radians(60),
        W=W, H=H
    )
    roi_helper.get_roi()
    if not getattr(roi_helper, "corner_points", None) or len(roi_helper.corner_points) != 3:
        raise SystemExit("[ERR] ROI not set (need 3 points).")
    
    # Open camera
    if len(VIDEO_PATH) > 1:
        cap = cv.VideoCapture(VIDEO_PATH)
        print(f"[INFO] Using video file: {VIDEO_PATH}")
    else:
        cap = cv.VideoCapture(CAM_DEVICE)
        print(f"[INFO] Using camera device: {CAM_DEVICE}")
        
    if not cap.isOpened():
        raise SystemExit(f"[ERR] Could not open {VIDEO_PATH or CAM_DEVICE}")

    # Read first frame
    ok, frame0 = safe_read(cap, flush=SAFE_FLUSH)
    if not ok:
        raise SystemExit("[ERR] Camera read failed at start.")
    frame0 = rotate(frame0, roi_helper.ROTATE_CW_DEG)
    frame0 = cv.flip(frame0, roi_helper.FLIPCODE)
    frame0 = cv.resize(frame0, (roi_helper.W, roi_helper.H))

    # Initialize calibration and masks
    calib = Calibrate(MAX_LINES_TO_PROCESS=30)
    DANGER_YFRAC = 0.85
    EDGE_PAD = 4
    roi_mask, danger_mask = roi_helper.build_masks(
        frame0.shape, danger_frac=DANGER_YFRAC, edge_pad=EDGE_PAD
    )

    # Setup output
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/logs", exist_ok=True)

    out_path = os.path.join("output", "result_combined.avi")
    out_path_video_ori = os.path.join("output", "original.avi")
    fourcc = cv.VideoWriter_fourcc(*"XVID")
    out_w = int(W * OUT_SCALE * 3)
    out_h = int(H * OUT_SCALE)
    writer = cv.VideoWriter(out_path, fourcc, FPS, (out_w, out_h))
    writer2 = cv.VideoWriter(out_path_video_ori, fourcc, FPS, (W,H))

    print(f"[INFO] Writing combined video to: {out_path}")

    log_file = os.path.join("output/logs", "detection_log.txt")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("=== Object Detection Log ===\n")
    print(f"[INFO] Logging to: {log_file}")

    # Initialize vision client
    vision_client = None
    throttler = CommandThrottler(cooldown=COMMAND_COOLDOWN)
    
    if SEND_COMMANDS:
        vision_client = VisionClient()
        vision_client.connect()
        if not vision_client.connected:
            print("[WARN] Failed to connect to client. Running in simulation mode.")
            vision_client = None
        else:
            print("[INFO] Connected to client. Commands will be sent.")
    else:
        print("[INFO] Command sending disabled. Running in simulation mode.")

    # Initialize state

    frame_id = 0
    hold_active = False
    hold_remaining = 0

    # Stop event for headless mode
    stop_event = threading.Event()
    if not SHOW_DEBUG_WINDOWS:
        listener_thread = threading.Thread(
            target=console_stop_listener,
            args=(stop_event,),
            daemon=True
        )
        listener_thread.start()
    
    turning=False
    stop_detected=False
    bbox=None

    print("\n" + "="*50)
    print("  JETSON CALIBRATION STARTED")
    print("="*50)
    print("Press 'q' in console or Ctrl+C to stop\n")
    
    try:
        while True:
            # -------- PERIODIC ENV RELOAD --------
            # now = time.time()
            # if now - last_env_reload > ENV_RELOAD_INTERVAL:
            #     cfg = reload_all_env(DOTENV_PATH)

            #     USE_BLUR = cfg["USE_BLUR"]
            #     BLUR_KSIZE = cfg["BLUR_KSIZE"]
            #     BLUR_SIGMA = cfg["BLUR_SIGMA"]
            #     SAFE_FLUSH = cfg["SAFE_FLUSH"]
            #     ACCEPTANCE = cfg["ACCEPTANCE"]
            #     STOP_HOLD_FRAMES = cfg["STOP_HOLD_FRAMES"]

            #     SEND_COMMANDS = cfg["SEND_COMMANDS"]
            #     COMMAND_COOLDOWN = cfg["COMMAND_COOLDOWN"]
            #     MOVEMENT_DURATION = cfg["MOVEMENT_DURATION"]
            #     MOVEMENT_DURATION_TURN=cfg["MOVEMENT_DURATION_TURN"]

            #     DEBUG_STATIC=cfg['DEBUG_STATIC']
            #     THR_MODE=cfg['THR_MODE']
            #     THR_L=cfg['THR_L']
            #     THR_OFFSET=cfg['THR_OFFSET']
            #     MIN_AREA=cfg['MIN_AREA']
            #     MIN_THICK=cfg['MIN_THICK']
            #     ASPECT_MAX=cfg['ASPECT_MAX']
            #     LINE_AR_REJECT=cfg['LINE_AR_REJECT']
            #     LINE_FILL_MAX=cfg['LINE_FILL_MAX']
            #     AREA_PCT=cfg['AREA_PCT']
            #     sp = StaticParams(DEBUG_STATIC=cfg['DEBUG_STATIC'],
            #                     THR_MODE=cfg['THR_MODE'],
            #                     THR_L=cfg['THR_L'],
            #                     THR_OFFSET=cfg['THR_OFFSET'],
            #                     MIN_AREA=cfg['MIN_AREA'],
            #                     MIN_THICK=cfg['MIN_THICK'],
            #                     ASPECT_MAX=cfg['ASPECT_MAX'],
            #                     LINE_AR_REJECT=cfg['LINE_AR_REJECT'],
            #                     LINE_FILL_MAX=cfg['LINE_FILL_MAX'],
            #                     AREA_PCT=cfg['AREA_PCT'])
            #     print(f'[DEBUG] SHOW WINDOWS {SHOW_DEBUG_WINDOWS}')
            #     throttler.cooldown = COMMAND_COOLDOWN

            #     print(f"[ENV RELOAD] STOP_HOLD_FRAMES={STOP_HOLD_FRAMES}, "
            #         f"ACCEPTANCE={ACCEPTANCE}, BLUR={USE_BLUR}")

            #     last_env_reload = now

            if not SHOW_DEBUG_WINDOWS and stop_event.is_set():
                print("[INFO] Stop event detected. Exiting loop.")
                break
            
            ok, frame = safe_read(cap, flush=SAFE_FLUSH)
            if not ok:
                print("[INFO] End of stream.")
                break
            frame_id += 1

            # Preprocess frame
            frame = rotate(frame, roi_helper.ROTATE_CW_DEG)
            frame = cv.flip(frame, roi_helper.FLIPCODE)
            frame = cv.resize(frame, (roi_helper.W, roi_helper.H))
            
            frame_original=frame.copy()
            frame_color=frame.copy()
            frame_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            
            if USE_BLUR:
                frame_gray = cv.medianBlur(frame_gray, BLUR_KSIZE)

            start_t = time.time()
            if ENABLE_STATIC_STOP:
                stop_detected, bbox, dbg = static_stop_detect(frame_color, roi_mask, danger_mask, sp)
            elapsed_ms = (time.time() - start_t) * 1000

            # Update hold logic
            hold_active, hold_remaining = update_hold_state(
                hold_active, hold_remaining, detected=stop_detected, hold_frames=STOP_HOLD_FRAMES
            )

            # Prepare visualization
            vis = frame_color.copy()
            bbox_info = "None"
            if bbox:
                x, y, bw, bh = bbox
                cv.rectangle(vis, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                bbox_info = f"x={x},y={y},w={bw},h={bh}"

            if not ENABLE_STATIC_STOP:
                            cv.putText(vis, "OBJ DET: OFF", (10, H-20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            angle_est, cond, angle_log = None, None, None
            command_to_send = None
            current_duration = 0.0  # Initialize duration

            if hold_active:
                # STOP detected and holding
                cond = 'STOP'
                command_to_send = "stop"
                current_duration = 0.0  # Stop is immediate

                print(f'[FRAME {frame_id}] STOP DETECTED! (hold: {hold_remaining})')
                cv.putText(vis, "STOP", (10, 24), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv.putText(vis, f"hold:{hold_remaining}", (10, 48), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            elif ENABLE_CALIBRATION:
                # No stop detected - do angle estimation
                angle_est, angle_log = calib.update(frame)
                
                if angle_est is not None:
                    angle_deg = np.rad2deg(angle_est)
                    
                    if angle_est < np.pi/2 - np.deg2rad(ACCEPTANCE):
                        cond = 'LEFT'
                        command_to_send = f"left {MOVEMENT_DURATION_TURN}"
                        current_duration = MOVEMENT_DURATION_TURN  # Set turn duration
                        turning=True

                    elif angle_est > np.pi/2 + np.deg2rad(ACCEPTANCE):
                        cond = 'RIGHT'
                        command_to_send = f"right {MOVEMENT_DURATION_TURN}"
                        current_duration = MOVEMENT_DURATION_TURN  # Set turn duration
                        turning=True

                    else:
                        if turning:
                            # command_to_send = "stop"
                            current_duration = 0.0
                            turning=False
                        else:
                            cond = 'FORWARD'
                            # command_to_send = f"forward {MOVEMENT_DURATION}"
                            current_duration = MOVEMENT_DURATION  # Set forward duration
                    
                    print(f'[FRAME {frame_id}] Turn: {cond} (angle: {angle_deg:.1f}°)')
                    
                    cv.putText(vis, f"turn: {cond}", (10, 60), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Draw angle arrow
                    H_vis = H - 10
                    if SHOW_DEBUG_WINDOWS:
                        vis=draw_arrow_by_angle(vis, (W//2, H_vis), angle_deg, 100, (255, 0, 255), 5)
                    cv.putText(vis, f"{angle_deg:.1f}", (W//2+20, H_vis-5), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            else:
                # Calibration Disabled
                cv.putText(vis, "LANE CALIB: OFF", (W-150, H-20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            # === SEND COMMAND TO CLIENT ===
            if vision_client and command_to_send:
                if throttler.should_send(command_to_send, duration=current_duration):
                    result = vision_client.send_command(command_to_send)
                    if result.get("status") != "ok":
                        print(f"[ERROR] Command failed: {result}")

            # === PREPARE OUTPUT VIDEO ===
            if  ENABLE_STATIC_STOP:
                nf_color = cv.cvtColor(dbg["nonfloor"], cv.COLOR_GRAY2BGR)
                nd_color = cv.cvtColor(dbg["nf_danger"], cv.COLOR_GRAY2BGR)

            else:
                nf_color = np.zeros_like(vis)
                nd_color = np.zeros_like(vis)

            vis_s = cv.resize(vis, (int(W * OUT_SCALE), int(H * OUT_SCALE)))
            nf_s = cv.resize(nf_color, (int(W * OUT_SCALE), int(H * OUT_SCALE)))
            nd_s = cv.resize(nd_color, (int(W * OUT_SCALE), int(H * OUT_SCALE)))
            combined = np.hstack((vis_s, nf_s, nd_s))
            writer.write(combined)

            # Display windows
            if SHOW_DEBUG_WINDOWS:
                cv.imshow("Combined", combined)
                if cv.waitKey(1) & 0xFF == ord('q'):
                    break

            if SAVE_DEBUG_IMAGES:
                writer2.write(frame_original)

            # Log debug info
            if ENABLE_STATIC_STOP:
                log_msg = (
                    f"Frame {frame_id:05d} | DETECT={stop_detected} | HOLD={hold_active}({hold_remaining}) | "
                    f"{bbox_info} | area%={dbg['area_pct']:.2f} | elong={dbg['elong']:.2f} | "
                    f"fill={dbg['fill']:.2f} | elapsed={elapsed_ms:.1f}ms | "
                    f"angle: {angle_est} | angle_deg: {np.rad2deg(angle_est) if angle_est else None} | "
                    f"Turn: {cond} | Command: {command_to_send}"
                )
                log_message(log_file, log_msg)

            else:
                log_msg = (
                    f"Frame {frame_id:05d} | DETECT={stop_detected} | HOLD={hold_active}({hold_remaining}) | "
                    f"{bbox_info}"
                    f"| elapsed={elapsed_ms:.1f}ms | "
                    f"angle: {angle_est} | angle_deg: {np.rad2deg(angle_est) if angle_est else None} | "
                    f"Turn: {cond} | Command: {command_to_send}"
                )
                log_message(log_file, log_msg)


    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user (Ctrl+C)")
    finally:
        # Send final STOP
        if vision_client:
            print("[INFO] Sending final STOP command...")
            vision_client.send_command("stop")
            vision_client.close()
        
        cap.release()
        writer.release()
        print()
        if SAVE_DEBUG_IMAGES:
            print(f"[INFO] Finished. Original vid saved at: {out_path_video_ori}")
            writer2.release()
        cv.destroyAllWindows()
        print(f"[INFO] Finished. Logs saved at: {log_file}")
        print(f"[INFO] Video saved at: {out_path}")


if __name__ == "__main__":
    main()
