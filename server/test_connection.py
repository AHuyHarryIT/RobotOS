import zmq
import json
import time
import random
import statistics  # Used for calculating average/median RTT

# --- HARDCODED CONFIGURATION ---
RPI_IP = "192.168.10.50" 
PORT = 5555

def print_stats(start_time, sent, received, rtts, errors):
    """Generates the final report when test stops"""
    duration = time.time() - start_time
    
    print("\n" + "="*50)
    print("       📊 STRESS TEST RESULTS       ")
    print("="*50)
    
    print(f"⏱️  Duration:      {duration:.2f} seconds")
    print(f"📤 Packets Sent:  {sent}")
    print(f"📥 Replies Recv:  {received}")
    
    # Calculate Loss
    loss = sent - received
    loss_percent = (loss / sent * 100) if sent > 0 else 0
    print(f"❌ Packet Loss:   {loss} ({loss_percent:.2f}%)")
    
    # Calculate RTT Stats
    if rtts:
        min_rtt = min(rtts)
        max_rtt = max(rtts)
        avg_rtt = sum(rtts) / len(rtts)
        
        print("-" * 30)
        print(f"⚡ Fastest RTT:   {min_rtt:.2f} ms")
        print(f"🐢 Slowest RTT:   {max_rtt:.2f} ms")
        print(f"⚖️  Average RTT:   {avg_rtt:.2f} ms")
        print(f"📈 Throughput:    {received / duration:.2f} packets/sec")
    
    print("="*50)

def run_stress_test():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 2000) # 2 second timeout
    
    print(f"🔌 Connecting to RPi at {RPI_IP}:{PORT}...")
    socket.connect(f"tcp://{RPI_IP}:{PORT}")

    # Fake commands to rotate through
    fake_commands = ["forward 1.0", "left 0.5", "right 0.5", "backward 1.0", "stop"]

    # --- TRACKING VARIABLES ---
    total_sent = 0
    total_received = 0
    total_errors = 0
    rtt_history = []
    
    start_time = time.time()

    print("🚀 Starting Stress Test. Press Ctrl+C to stop and view stats.")
    print("-" * 60)
    print(f"{'SEQ':<6} {'CMD':<15} {'STATUS':<10} {'RTT (ms)':<10}")
    print("-" * 60)

    try:
        while True:
            cmd_start = time.time()
            action = random.choice(fake_commands)

            # Payload mimicking your real architecture
            payload = {
                "mode": "sequence",
                "cmd": action,
                "_test_id": total_sent + 1,
                "_timestamp": time.time()
            }

            try:
                # 1. Send
                socket.send_json(payload)
                total_sent += 1

                # 2. Receive
                reply = socket.recv_json()
                total_received += 1
                
                # 3. Calculate RTT
                rtt_ms = (time.time() - cmd_start) * 1000
                rtt_history.append(rtt_ms)

                # Real-time simple log
                status = "OK" if reply.get("status") == "ok" else "ERR"
                print(f"{total_sent:<6} {action:<15} {status:<10} {rtt_ms:.2f}")

            except zmq.Again:
                print(f"{total_sent:<6} {action:<15} TIMEOUT    ----")
                total_errors += 1
                # Recreate socket on timeout to prevent lockup
                socket.close()
                socket = context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, 2000)
                socket.connect(f"tcp://{RPI_IP}:{PORT}")

            # Sleep slightly to control flood rate (optional)
            time.sleep(0.05) 

    except KeyboardInterrupt:
        # This block triggers when you hit Ctrl+C
        print("\n\n🛑 Test Stopped by User.")
        print_stats(start_time, total_sent, total_received, rtt_history, total_errors)
        
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    run_stress_test()   