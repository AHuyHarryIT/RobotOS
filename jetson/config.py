from dotenv import load_dotenv, dotenv_values
import os

DOTENV_PATH=os.path.join(os.path.dirname(__file__),'.env')
load_dotenv(dotenv_path=DOTENV_PATH, override=True)

def get_int(key, default):
    return int(os.getenv(key, default))

def get_float(key, default):
    return float(os.getenv(key, default))

def get_bool(key, default=False):
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes")

def get_text(key, default=''):
    return str(os.getenv(key, default)).lower()


class Config:
    # Camera
    CAM_DEVICE = get_int("CAM_DEVICE", 0)
    VIDEO_PATH = os.getenv("VIDEO_PATH", "")
    ROI_PT_PATH = os.getenv("ROI_PT_PATH","")
    W = get_int("FRAME_WIDTH", 640)
    H = get_int("FRAME_HEIGHT", 480)
    FPS = get_int("FPS", 30)
    OUT_SCALE=get_float('OUT_SCALE',0.7)

    # Preprocessing
    USE_NORMALIZATION = get_bool("USE_NORMALIZATION", True)
    NORMALIZATION_METHOD = os.getenv("NORMALIZATION_METHOD", "clahe")
    GAMMA = get_float("GAMMA", 1.0)
    BLUR_KSIZE = get_int("BLUR_KSIZE", 3)
    BLUR_SIGMA=get_int('BLUR_SIGMA',5)
    SAFE_FLUSH=get_int('SAFE_FLUSH',0)
    ACCEPTANCE=get_int('ACCEPTANCE',5)
    USE_BLUR=get_bool('USE_BLUR',True)
    # Threshold
    THRESHOLD_MODE = os.getenv("THRESHOLD_MODE", "otsu")
    FIXED_THRESHOLD = get_int("FIXED_THRESHOLD", 120)
    ADAPTIVE_BLOCK_SIZE = get_int("ADAPTIVE_BLOCK_SIZE", 21)
    ADAPTIVE_C = get_int("ADAPTIVE_C", 5)

    LRANGE=get_float('LRANGE',1.0)
    HRANGE=get_float('HRANGE',30.0)

    # Post-processing
    MORPH_KERNEL = get_int("MORPH_KERNEL", 3)
    MIN_OBJECT_AREA = get_int("MIN_OBJECT_AREA", 500)
    STOP_HOLD_FRAMES=get_int("STOP_HOLD_FRAMES",20)

    # Debug
    SHOW_DEBUG_WINDOWS = get_bool("SHOW_DEBUG_WINDOWS", False)
    SEND_COMMANDS=get_bool('SEND_COMMANDS',True)
    COMMAND_COOLDOWN=get_float('COMMAND_COOLDOWN',0.3)
    MOVEMENT_DURATION=get_float('MOVEMENT_DURATION',0.05)
    MOVEMENT_DURATION_TURN=get_float('MOVEMENT_DURATION_TURN',0.03)
    SAVE_DEBUG_IMAGES=get_bool('SAVE_DEBUG_IMAGES', False)
    ILLUM_NORMALIZATION=get_text('NORMALIZATION_METHOD','clahe')
    # Static stop
    DEBUG_STATIC=get_bool('DEBUG_STATIC', False)
    THR_MODE=get_text('THR_MODE')
    THR_L=get_int('THR_L',135)
    THR_OFFSET=get_int('THR_OFFSET', 2)
    MIN_AREA=get_int('MIN_AREA', 500)
    MIN_THICK=get_int('MIN_THICK',6)
    ASPECT_MAX=get_float('ASPECT_MAX',1.4)
    LINE_AR_REJECT=get_float('LINE_AR_REJECT', 3.9)
    LINE_FILL_MAX=get_float('LINE_FILL_MAX',0.22)
    AREA_PCT=get_float('AREA_PCT',2.5)

def reload_all_env(dotenv_path):
    """
    Re-read ALL parameters from .env and return a fresh dict
    """
    vals = dotenv_values(dotenv_path)

    def _int(k, d):   return int(vals.get(k, d)) if vals.get(k) is not None else d
    def _float(k, d): return float(vals.get(k, d)) if vals.get(k) is not None else d
    def _bool(k, d):  return str(vals.get(k, d)).lower() in ("1", "true", "yes")
    def _text(k, d): return str(vals.get(k, d))

    return {
        # Camera / runtime-safe params only
        "USE_BLUR": _bool("USE_BLUR", True),
        "BLUR_KSIZE": _int("BLUR_KSIZE", 3),
        "BLUR_SIGMA": _int("BLUR_SIGMA", 5),
        'LRANGE': _float('LRANGE',1.0),
        'HRANGE': _float('HRANGE',30.0),
        "SAFE_FLUSH": _int("SAFE_FLUSH", 0),
        "ACCEPTANCE": _int("ACCEPTANCE", 5),
        "STOP_HOLD_FRAMES": _int("STOP_HOLD_FRAMES", 20),

        "SEND_COMMANDS": _bool("SEND_COMMANDS", True),
        "COMMAND_COOLDOWN": _float("COMMAND_COOLDOWN", 0.3),
        "MOVEMENT_DURATION": _float("MOVEMENT_DURATION", 0.05),
        "MOVEMENT_DURATION_TURN": _float("MOVEMENT_DURATION_TURN", 0.03),
        
        'DEBUG_STATIC': _bool('DEBUG_STATIC',False),
        'THR_MODE': _text('THR_MODE', 'fixed'),
        'THR_L': _int('THR_L',135),
        'THR_OFFSET': _int('THR_OFFSET',2),
        'MIN_AREA': _int('MIN_AREA', 500),
        'MIN_THICK': _int('MIN_THICK',6),
        'ASPECT_MAX': _float('ASPECT_MAX', 1.4),
        'LINE_AR_REJECT': _float('LINE_AR_REJECT',3.0),
        'LINE_FILL_MAX': _float('LINE_FILL_MAX', 0.22),
        'AREA_PCT': _float('AREA_PCT',2.5)

    }