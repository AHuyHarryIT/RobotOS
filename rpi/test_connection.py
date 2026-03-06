#!/usr/bin/env python3
"""
Connection Stress Test - Raspberry Pi Side

Tests the ZMQ server on Raspberry Pi by accepting connections and
monitoring server health for a specified duration (default 1 hour).

Features:
    - ZMQ REP server for test commands
    - Heartbeat PUB for client monitoring
    - Connection statistics tracking
    - Memory and CPU monitoring
    - Real-time terminal output

This script is meant to be run ON the Raspberry Pi to verify
the server can handle sustained connections without issues.

Usage:
    python test_connection.py                    # Run for 1 hour (default)
    python test_connection.py --duration 3600   # Run for 1 hour
    python test_connection.py --duration 60     # Run for 1 minute

Author: Auto-Bot Team
"""

import argparse
import json
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import zmq
from dotenv import load_dotenv

# Load environment (optional, hardcoded values take priority for testing)
load_dotenv()

# ============================================================
# Configuration - HARDCODED FOR TESTING
# ============================================================
# miniPC IP: 192.168.10.60
# RPi IP: 192.168.10.50 (this device)
ZMQ_PORT = 5555           # Command port
HEARTBEAT_PORT = 5556     # Heartbeat port

BIND_ADDR = f"tcp://0.0.0.0:{ZMQ_PORT}"
HB_ADDR = f"tcp://0.0.0.0:{HEARTBEAT_PORT}"

# Test parameters
DEFAULT_DURATION = 3600  # 1 hour in seconds
HEARTBEAT_INTERVAL = 1.0  # Send heartbeat every second


@dataclass
class ServerStats:
    """Track server statistics."""
    start_time: float = field(default_factory=time.time)
    total_requests: int = 0
    total_replies: int = 0
    total_errors: int = 0
    heartbeats_sent: int = 0
    max_request_time: float = 0.0
    min_request_time: float = float('inf')
    request_times: list = field(default_factory=list)
    client_connections: int = 0
    last_request_ts: float = 0.0
    last_error: str = ""
    
    @property
    def avg_request_time(self) -> float:
        if not self.request_times:
            return 0.0
        return sum(self.request_times) / len(self.request_times)
    
    @property
    def uptime(self) -> float:
        return time.time() - self.start_time
    
    @property
    def requests_per_minute(self) -> float:
        if self.uptime < 60:
            return self.total_requests * (60 / max(1, self.uptime))
        return self.total_requests / (self.uptime / 60)


# Global stats and control
stats = ServerStats()
stats_lock = threading.Lock()
running = True


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n\n[SIGNAL] Received interrupt signal, stopping server...")
    running = False


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    return str(timedelta(seconds=int(seconds)))


def get_system_info() -> dict:
    """Get basic system info (works on most Linux systems)."""
    info = {
        "cpu_percent": "N/A",
        "memory_percent": "N/A",
        "temperature": "N/A"
    }
    
    try:
        # Try to get CPU usage from /proc/stat
        with open('/proc/loadavg', 'r') as f:
            loadavg = f.read().split()
            info["cpu_load"] = float(loadavg[0])
    except:
        pass
    
    try:
        # Try to get memory info
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().split()[0]
                    meminfo[key] = int(value)
            
            if 'MemTotal' in meminfo and 'MemAvailable' in meminfo:
                total = meminfo['MemTotal']
                available = meminfo['MemAvailable']
                used_percent = ((total - available) / total) * 100
                info["memory_percent"] = f"{used_percent:.1f}%"
    except:
        pass
    
    try:
        # Try to get CPU temperature (Raspberry Pi specific)
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read().strip()) / 1000.0
            info["temperature"] = f"{temp:.1f}°C"
    except:
        pass
    
    return info


def print_header():
    """Print test header."""
    print("=" * 70)
    print("   RobotOS Connection Stress Test - RPi Server")
    print("=" * 70)
    print(f"  Bind Address:   {BIND_ADDR}")
    print(f"  Heartbeat:      {HB_ADDR}")
    print(f"  Started at:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()


def print_status(elapsed: float, duration: float):
    """Print current status to terminal."""
    with stats_lock:
        s = stats
        remaining = max(0, duration - elapsed)
        sys_info = get_system_info()
        
        # Clear lines and print status
        status = (
            f"\r[{format_duration(elapsed)}/{format_duration(duration)}] "
            f"Req: {s.total_requests} | "
            f"Rep: {s.total_replies} | "
            f"Err: {s.total_errors} | "
            f"HB: {s.heartbeats_sent} | "
            f"RPM: {s.requests_per_minute:.1f} | "
            f"Mem: {sys_info.get('memory_percent', 'N/A')} | "
            f"Temp: {sys_info.get('temperature', 'N/A')}"
        )
        print(status, end="", flush=True)


def print_info(msg: str):
    """Print info message on new line."""
    print(f"\nℹ️  [INFO] {msg}")


def print_warning(msg: str):
    """Print warning message on new line."""
    print(f"\n⚠️  [WARNING] {msg}")


def print_error(msg: str):
    """Print error message on new line."""
    print(f"\n❌ [ERROR] {msg}")


def print_success(msg: str):
    """Print success message on new line."""
    print(f"\n✅ [OK] {msg}")


def heartbeat_publisher(ctx: zmq.Context):
    """
    Publish heartbeat messages periodically.
    """
    global running, stats
    
    pub = ctx.socket(zmq.PUB)
    pub.bind(HB_ADDR)
    
    print(f"[HB] Heartbeat publishing on {HB_ADDR}")
    
    while running:
        try:
            msg = {
                "type": "heartbeat",
                "ts": time.time(),
                "status": "ok",
                "uptime": stats.uptime,
                "requests": stats.total_requests
            }
            pub.send_json(msg)
            
            with stats_lock:
                stats.heartbeats_sent += 1
                
            time.sleep(HEARTBEAT_INTERVAL)
            
        except Exception as e:
            if running:
                print_error(f"Heartbeat error: {e}")
            time.sleep(1.0)
    
    pub.close()
    print("\n[HB] Heartbeat publisher stopped")


def handle_request(payload: str) -> dict:
    """
    Handle incoming test request.
    
    Returns:
        Response dictionary
    """
    start = time.time()
    
    try:
        # Try to parse as JSON
        try:
            data = json.loads(payload)
            cmd = data.get("cmd", "")
            test_id = data.get("_test_id", 0)
        except json.JSONDecodeError:
            cmd = payload.strip()
            test_id = 0
        
        # For stress test, we just acknowledge the command
        # Don't actually execute GPIO commands
        response = {
            "status": "ok",
            "ok": True,
            "test_id": test_id,
            "cmd_received": cmd[:50],  # Truncate for safety
            "server_ts": time.time(),
            "processing_time_ms": (time.time() - start) * 1000
        }
        
        return response, time.time() - start
        
    except Exception as e:
        return {
            "status": "error",
            "ok": False,
            "error": str(e)
        }, time.time() - start


def run_server(duration: int):
    """
    Main server loop for stress testing.
    
    Args:
        duration: Test duration in seconds
    """
    global running, stats
    
    print(f"[SERVER] Starting stress test server...")
    print(f"         Duration: {format_duration(duration)}")
    print()
    print("Press Ctrl+C to stop early")
    print("-" * 70)
    
    # Initialize ZMQ
    ctx = zmq.Context.instance()
    
    # REP socket for receiving commands
    sock = ctx.socket(zmq.REP)
    sock.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout for non-blocking check
    sock.bind(BIND_ADDR)
    
    print(f"[ZMQ] Listening on {BIND_ADDR}")
    
    # Start heartbeat publisher
    hb_thread = threading.Thread(target=heartbeat_publisher, args=(ctx,), daemon=True)
    hb_thread.start()
    
    # Main server loop
    stats.start_time = time.time()
    last_status_time = time.time()
    
    try:
        while running:
            elapsed = time.time() - stats.start_time
            
            # Check if test duration completed
            if elapsed >= duration:
                print_success(f"Test duration completed ({format_duration(duration)})")
                break
            
            try:
                # Wait for request (with timeout for responsiveness)
                raw = sock.recv(flags=0)
                payload = raw.decode("utf-8", errors="replace")
                
                with stats_lock:
                    stats.total_requests += 1
                    stats.last_request_ts = time.time()
                
                # Handle request
                response, proc_time = handle_request(payload)
                
                # Send reply
                sock.send_string(json.dumps(response))
                
                with stats_lock:
                    stats.total_replies += 1
                    stats.request_times.append(proc_time)
                    # Keep only last 1000 measurements
                    if len(stats.request_times) > 1000:
                        stats.request_times = stats.request_times[-1000:]
                    stats.max_request_time = max(stats.max_request_time, proc_time)
                    if proc_time > 0:
                        stats.min_request_time = min(stats.min_request_time, proc_time)
                        
            except zmq.Again:
                # Timeout - no request received, continue loop
                pass
                
            except zmq.ZMQError as e:
                with stats_lock:
                    stats.total_errors += 1
                    stats.last_error = str(e)
                print_error(f"ZMQ error: {e}")
                time.sleep(0.1)
                
            except Exception as e:
                with stats_lock:
                    stats.total_errors += 1
                    stats.last_error = str(e)
                print_error(f"Server error: {e}")
            
            # Update status display
            if time.time() - last_status_time >= 1.0:
                print_status(elapsed, duration)
                last_status_time = time.time()
                
    except KeyboardInterrupt:
        print("\n[SERVER] Interrupted by user")
    finally:
        running = False
        sock.close()
        time.sleep(0.5)  # Let heartbeat thread clean up
    
    return stats


def print_final_report(stats: ServerStats, duration: float):
    """Print final test report."""
    print("\n")
    print("=" * 70)
    print("   STRESS TEST SERVER FINAL REPORT")
    print("=" * 70)
    print()
    
    actual_duration = stats.uptime
    sys_info = get_system_info()
    
    print(f"  Test Duration:      {format_duration(actual_duration)}")
    print(f"  Server Address:     {BIND_ADDR}")
    print()
    
    print("  📊 REQUEST STATISTICS")
    print("  " + "-" * 40)
    print(f"  Total Requests:          {stats.total_requests:,}")
    print(f"  Successful Replies:      {stats.total_replies:,}")
    print(f"  Errors:                  {stats.total_errors:,}")
    print(f"  Requests per Minute:     {stats.requests_per_minute:.1f}")
    print()
    
    print("  ⏱️  PROCESSING TIME")
    print("  " + "-" * 40)
    if stats.request_times:
        print(f"  Average:                 {stats.avg_request_time*1000:.3f} ms")
        print(f"  Min:                     {stats.min_request_time*1000:.3f} ms")
        print(f"  Max:                     {stats.max_request_time*1000:.3f} ms")
    else:
        print("  No requests processed")
    print()
    
    print("  💓 HEARTBEAT STATISTICS")
    print("  " + "-" * 40)
    print(f"  Heartbeats Sent:         {stats.heartbeats_sent:,}")
    if actual_duration > 0:
        expected_hb = int(actual_duration / HEARTBEAT_INTERVAL)
        print(f"  Expected:                ~{expected_hb:,}")
        hb_rate = (stats.heartbeats_sent / expected_hb) * 100 if expected_hb > 0 else 0
        print(f"  Heartbeat Rate:          {hb_rate:.1f}%")
    print()
    
    print("  🖥️  SYSTEM INFO")
    print("  " + "-" * 40)
    print(f"  Memory Usage:            {sys_info.get('memory_percent', 'N/A')}")
    print(f"  CPU Temperature:         {sys_info.get('temperature', 'N/A')}")
    if 'cpu_load' in sys_info:
        print(f"  CPU Load (1min):         {sys_info['cpu_load']:.2f}")
    print()
    
    # Overall verdict
    print("  🏁 VERDICT")
    print("  " + "-" * 40)
    
    error_rate = (stats.total_errors / max(1, stats.total_requests)) * 100
    
    if stats.total_errors == 0 and stats.total_requests > 0:
        print("  ✅ EXCELLENT - Server handled all requests without errors")
    elif error_rate < 1.0:
        print("  ✅ GOOD - Server is stable with minimal errors")
    elif error_rate < 5.0:
        print("  ⚠️  FAIR - Some errors occurred, investigate logs")
    else:
        print("  ❌ POOR - High error rate, server may be unstable")
    
    if stats.last_error:
        print(f"\n  Last Error: {stats.last_error}")
    
    print()
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Stress test ZMQ server on Raspberry Pi"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=DEFAULT_DURATION,
        help=f"Test duration in seconds (default: {DEFAULT_DURATION} = 1 hour)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=ZMQ_PORT,
        help=f"ZMQ port to listen on (default: {ZMQ_PORT})"
    )
    
    args = parser.parse_args()
    
    # Override port if specified - use local variables
    bind_addr = BIND_ADDR
    if args.port != ZMQ_PORT:
        bind_addr = f"tcp://0.0.0.0:{args.port}"
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print_header()
    
    # Run server
    final_stats = run_server(args.duration)
    
    # Print report
    print_final_report(final_stats, args.duration)
    
    # Exit with appropriate code
    error_rate = (final_stats.total_errors / max(1, final_stats.total_requests)) * 100
    if error_rate < 5.0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
