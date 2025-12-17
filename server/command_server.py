#!/usr/bin/env python3
"""
Command server running on miniPC client.
Receives commands from external sources (Jetson, web API, etc.) via ZMQ REP socket.
Processes commands through the central aggregator and forwards to RPi for GPIO execution.

This server acts as the entry point for all Jetson vision commands.
"""
import threading
import time
import zmq
from zmq_client import send_command
from config import CLIENT_SERVER_PORT
from command_aggregator import get_aggregator, CommandSource, CommandPriority

server_running = False
server_thread = None


def command_server_loop(zmq_to_rpi_sock):
    """
    Main loop for command server.
    Binds REP socket to receive commands from Jetson/external sources.
    Processes commands through aggregator and forwards to RPi.
    
    Args:
        zmq_to_rpi_sock: The ZMQ REQ socket connected to RPi (shared from main)
    """
    global server_running
    
    # Get the global command aggregator instance
    aggregator = get_aggregator()
    
    ctx = zmq.Context.instance()
    server_sock = ctx.socket(zmq.REP)
    bind_addr = f"tcp://0.0.0.0:{CLIENT_SERVER_PORT}"
    server_sock.bind(bind_addr)
    
    print(f"[CMD SERVER] Listening on {bind_addr} for external commands")
    print("[CMD SERVER] Ready to receive from Jetson, web API, etc.")
    print("[CMD SERVER] All commands will be processed through central aggregator")
    
    server_running = True
    
    try:
        while server_running:
            try:
                # Set timeout to check server_running flag periodically
                if server_sock.poll(timeout=500):  # 500ms timeout
                    raw = server_sock.recv_string()
                    print(f"[CMD SERVER] <- Received: {raw}")
                    
                    # Parse incoming message
                    import json
                    try:
                        msg_obj = json.loads(raw)
                        payload = msg_obj.get("cmd", raw)
                    except:
                        # If not JSON, treat as plain command string
                        payload = raw.strip()
                    
                    # Process command through central aggregator
                    # Jetson commands typically have high priority for autonomous control
                    success, processed_cmd, msg = aggregator.process_command(
                        command=payload,
                        source=CommandSource.JETSON,
                        priority=CommandPriority.HIGH
                    )
                    
                    if success and processed_cmd:
                        # Forward validated command to RPi
                        try:
                            send_command(zmq_to_rpi_sock, processed_cmd)
                            reply = {
                                "status": "ok", 
                                "cmd": processed_cmd, 
                                "original": payload,
                                "forwarded": True,
                                "message": msg
                            }
                        except Exception as e:
                            print(f"[CMD SERVER] Error forwarding to RPi: {e}")
                            reply = {
                                "status": "error", 
                                "error": str(e), 
                                "forwarded": False
                            }
                    else:
                        # Command validation failed
                        reply = {
                            "status": "error",
                            "error": msg,
                            "forwarded": False
                        }
                    
                    # Reply to external source (Jetson)
                    server_sock.send_string(json.dumps(reply))
                    print(f"[CMD SERVER] -> Replied: {reply}")
                    
            except zmq.ZMQError as e:
                if server_running:
                    print(f"[CMD SERVER] ZMQ Error: {e}")
                break
            except Exception as e:
                print(f"[CMD SERVER] Error in server loop: {e}")
                time.sleep(0.1)
                
    finally:
        server_sock.close()
        print("[CMD SERVER] Server stopped")


def start_command_server(zmq_to_rpi_sock):
    """
    Start the command server in a background thread.
    
    Args:
        zmq_to_rpi_sock: The ZMQ REQ socket connected to RPi
    """
    global server_thread, server_running
    
    if server_thread and server_thread.is_alive():
        print("[CMD SERVER] Already running")
        return
    
    server_thread = threading.Thread(
        target=command_server_loop,
        args=(zmq_to_rpi_sock,),
        daemon=True
    )
    server_thread.start()
    print("[CMD SERVER] Started in background thread")


def stop_command_server():
    """Stop the command server gracefully."""
    global server_running
    
    if not server_running:
        return
    
    print("[CMD SERVER] Stopping...")
    server_running = False
    
    if server_thread and server_thread.is_alive():
        server_thread.join(timeout=2.0)
    
    print("[CMD SERVER] Stopped")
