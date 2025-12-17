#!/usr/bin/env python3
"""
Test script for Command Aggregator

This script tests the command aggregation system to ensure:
- Command validation works correctly
- Statistics are tracked properly
- Different sources are handled correctly
- Priority system functions as expected

Run this script before deploying to verify the aggregator.

Usage:
    python3 test_aggregator.py
"""

import sys
import json
from command_aggregator import (
    get_aggregator, 
    CommandSource, 
    CommandPriority
)


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_basic_validation():
    """Test basic command validation."""
    print_section("Test 1: Basic Command Validation")
    
    agg = get_aggregator()
    
    test_cases = [
        # (command, expected_success, description)
        ("forward", True, "Simple forward command"),
        ("forward 2", True, "Forward with duration"),
        ("left:1.5", True, "Left with colon format"),
        ("invalid_cmd", False, "Invalid command name"),
        ("", False, "Empty command"),
        ("stop", True, "Stop command"),
        ("seq forward 2; right 1; stop", True, "Sequence command"),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, expected, desc in test_cases:
        success, processed, msg = agg.process_command(
            cmd, CommandSource.MANUAL, CommandPriority.NORMAL
        )
        
        if success == expected:
            print(f"✓ PASS: {desc}")
            print(f"  Command: {cmd!r} -> Success: {success}")
            passed += 1
        else:
            print(f"✗ FAIL: {desc}")
            print(f"  Command: {cmd!r}")
            print(f"  Expected: {expected}, Got: {success}")
            print(f"  Message: {msg}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_source_tracking():
    """Test command source tracking."""
    print_section("Test 2: Source Tracking")
    
    agg = get_aggregator()
    agg.clear_history()  # Start fresh
    
    # Send commands from different sources
    sources_to_test = [
        (CommandSource.JETSON, "left 1"),
        (CommandSource.CONTROLLER, "forward"),
        (CommandSource.MANUAL, "right"),
        (CommandSource.JETSON, "stop"),
        (CommandSource.CONTROLLER, "backward"),
    ]
    
    for source, cmd in sources_to_test:
        agg.process_command(cmd, source, CommandPriority.NORMAL)
    
    # Check statistics
    stats = agg.get_stats()
    
    print(f"Total commands: {stats['total_commands']}")
    print(f"Commands by source:")
    for source, count in stats['by_source'].items():
        print(f"  - {source}: {count}")
    
    # Verify counts
    expected_jetson = 2
    expected_controller = 2
    expected_manual = 1
    
    actual_jetson = stats['by_source'].get(CommandSource.JETSON, 0)
    actual_controller = stats['by_source'].get(CommandSource.CONTROLLER, 0)
    actual_manual = stats['by_source'].get(CommandSource.MANUAL, 0)
    
    success = (
        actual_jetson == expected_jetson and
        actual_controller == expected_controller and
        actual_manual == expected_manual
    )
    
    if success:
        print("\n✓ Source tracking working correctly")
    else:
        print("\n✗ Source tracking failed")
        print(f"  Expected: jetson={expected_jetson}, controller={expected_controller}, manual={expected_manual}")
        print(f"  Actual: jetson={actual_jetson}, controller={actual_controller}, manual={actual_manual}")
    
    return success


def test_history():
    """Test command history tracking."""
    print_section("Test 3: Command History")
    
    agg = get_aggregator()
    agg.clear_history()
    
    # Send some commands
    commands = ["forward", "left 1", "right", "stop"]
    for cmd in commands:
        agg.process_command(cmd, CommandSource.MANUAL, CommandPriority.NORMAL)
    
    # Get history
    history = agg.get_recent_history(10)
    
    print(f"History size: {len(history)}")
    print("Recent commands:")
    for entry in history:
        print(f"  {entry['source']:10} -> {entry['processed']}")
    
    success = len(history) == len(commands)
    
    if success:
        print("\n✓ History tracking working correctly")
    else:
        print(f"\n✗ History tracking failed")
        print(f"  Expected {len(commands)} entries, got {len(history)}")
    
    return success


def test_priority_handling():
    """Test priority level handling."""
    print_section("Test 4: Priority Handling")
    
    agg = get_aggregator()
    
    # Test different priority levels
    priorities = [
        (CommandPriority.LOW, "Background task"),
        (CommandPriority.NORMAL, "Regular command"),
        (CommandPriority.HIGH, "Emergency stop"),
    ]
    
    all_success = True
    
    for priority, desc in priorities:
        success, processed, msg = agg.process_command(
            "forward", CommandSource.MANUAL, priority
        )
        
        if success:
            print(f"✓ Priority {priority} ({desc}): OK")
        else:
            print(f"✗ Priority {priority} ({desc}): FAILED")
            all_success = False
    
    if all_success:
        print("\n✓ Priority handling working correctly")
    else:
        print("\n✗ Priority handling failed")
    
    return all_success


def test_error_handling():
    """Test error handling and validation."""
    print_section("Test 5: Error Handling")
    
    agg = get_aggregator()
    initial_stats = agg.get_stats()
    initial_errors = initial_stats['errors']
    
    # Send invalid commands
    invalid_commands = [
        "invalid_cmd",
        "bad_command 123",
        "",
        "xyz",
    ]
    
    for cmd in invalid_commands:
        success, processed, msg = agg.process_command(
            cmd, CommandSource.MANUAL, CommandPriority.NORMAL
        )
        if not success:
            print(f"✓ Correctly rejected: {cmd!r}")
        else:
            print(f"✗ Should have rejected: {cmd!r}")
    
    # Check error count increased
    final_stats = agg.get_stats()
    final_errors = final_stats['errors']
    errors_added = final_errors - initial_errors
    
    print(f"\nErrors tracked: {errors_added}/{len(invalid_commands)}")
    
    success = errors_added == len(invalid_commands)
    
    if success:
        print("✓ Error handling working correctly")
    else:
        print("✗ Error handling failed")
    
    return success


def main():
    """Run all tests."""
    print("="*60)
    print("  Command Aggregator Test Suite")
    print("="*60)
    
    tests = [
        ("Basic Validation", test_basic_validation),
        ("Source Tracking", test_source_tracking),
        ("History Management", test_history),
        ("Priority Handling", test_priority_handling),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed with exception: {e}")
            results.append((name, False))
    
    # Print summary
    print_section("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Aggregator is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
