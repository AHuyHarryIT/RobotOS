#!/usr/bin/env python3
"""
Quick test script for web dashboard
Tests the dashboard without needing RPi connection
"""
import time
from command_aggregator import get_aggregator

# Simulate some commands
aggregator = get_aggregator()

print("Simulating command activity for dashboard testing...")
print("This will add test commands to the aggregator\n")

# Add some test commands
test_commands = [
    ("forward", "CONTROLLER"),
    ("right 0.5", "JETSON"),
    ("stop", "MANUAL"),
    ("seq forward 1; stop", "SEQUENCE"),
    ("left 0.3", "CONTROLLER"),
    ("backward 2", "JETSON"),
]

for cmd, source in test_commands:
    result = aggregator.process_command(cmd, source)
    print(f"Added: {cmd:20} from {source:10} -> {result}")
    time.sleep(0.2)

print("\n" + "="*60)
print("Test data added!")
print("="*60)
print("\nNow start the web dashboard to see the data:")
print("  python3 web_dashboard.py")
print("\nThen open in browser:")
print("  http://localhost:5000")
print("="*60)

# Show current stats
stats = aggregator.get_stats()
print("\nCurrent Statistics:")
print(f"  Total commands: {stats['total_commands']}")
print(f"  By source:")
for source, count in stats['by_source'].items():
    print(f"    - {source}: {count}")
