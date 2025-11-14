from typing import Optional, Tuple, List
from states import ALIASES, CMD_PATTERN

def parse_command(token: str) -> Optional[Tuple[str, Optional[float]]]:
    """
    Returns (KEY, duration_seconds) or None if invalid.
    Accepts: 'forward', 'forward 2', 'right:1.5', 'sleep 0.3'
    """
    m = CMD_PATTERN.match(token)
    if not m:
        return None
    cmd_raw, dur_raw = m.group(1), m.group(2)
    name = ALIASES.get(cmd_raw.lower())
    if not name:
        return None
    dur = float(dur_raw) if dur_raw else None
    return (name, dur)

def split_sequence(seq_str: str) -> List[str]:
    """
    Split by comma/semicolon/newline and remove empty tokens.
    """
    import re
    tokens = re.split(r"[,\n;]+", seq_str)
    return [t for t in (tok.strip() for tok in tokens) if t]

