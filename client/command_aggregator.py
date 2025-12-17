#!/usr/bin/env python3
"""
Command Aggregator - Central hub for processing all input commands.

This module acts as the central brain that:
1. Receives commands from multiple sources (Jetson vision, Xbox controller, manual input)
2. Validates and processes commands
3. Applies priority rules if needed
4. Forwards processed commands to RPi for execution

Architecture:
    [Jetson Vision] ──┐
    [Xbox Controller] ─┼──> [Command Aggregator] ──> [RPi GPIO Executor]
    [Manual Input] ────┘

Author: Auto-Bot Team
Date: 2024-12-17
"""

import time
import threading
import logging
from typing import Optional, Dict, Tuple
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CommandAggregator")


class CommandSource:
    """Enum for command sources"""
    JETSON = "jetson"
    CONTROLLER = "controller"
    MANUAL = "manual"
    SEQUENCE = "sequence"
    UNKNOWN = "unknown"


class CommandPriority:
    """Command priority levels (higher number = higher priority)"""
    LOW = 1        # Background tasks
    NORMAL = 5     # Regular commands
    HIGH = 10      # Emergency stops, critical commands


class CommandAggregator:
    """
    Central command processing hub.
    Aggregates, validates, and forwards commands from multiple sources.
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize the command aggregator.
        
        Args:
            max_history: Maximum number of commands to keep in history
        """
        self.lock = threading.Lock()
        self.command_history = deque(maxlen=max_history)
        self.last_command = None
        self.last_command_time = 0.0
        self.stats = {
            "total_commands": 0,
            "by_source": {},
            "errors": 0
        }
        
        # Command validation rules
        self.allowed_commands = {
            "forward", "backward", "left", "right", 
            "stop", "lock", "unlock", "sleep"
        }
        
        logger.info("Command Aggregator initialized")
    
    def process_command(
        self, 
        command: str, 
        source: str = CommandSource.UNKNOWN,
        priority: int = CommandPriority.NORMAL
    ) -> Tuple[bool, Optional[str], str]:
        """
        Process and validate a command from any source.
        
        Args:
            command: The command string to process
            source: Source of the command (jetson, controller, manual, etc.)
            priority: Priority level of the command
            
        Returns:
            Tuple of (success: bool, processed_command: Optional[str], message: str)
            - success: Whether the command is valid and should be executed
            - processed_command: The processed/normalized command (None if invalid)
            - message: Human-readable status message
        """
        with self.lock:
            # Update statistics
            self.stats["total_commands"] += 1
            self.stats["by_source"][source] = self.stats["by_source"].get(source, 0) + 1
            
            # Log incoming command
            logger.info(f"Processing command from {source} (priority={priority}): {command!r}")
            
            # Validate command
            try:
                validated, processed_cmd = self._validate_command(command)
                if not validated:
                    self.stats["errors"] += 1
                    logger.warning(f"Invalid command rejected: {command!r}")
                    return False, None, f"Invalid command: {command}"
                
                # Store in history
                self._add_to_history(command, source, priority, processed_cmd)
                
                # Update last command tracking
                self.last_command = processed_cmd
                self.last_command_time = time.time()
                
                logger.info(f"Command validated and ready: {processed_cmd!r}")
                return True, processed_cmd, "Command processed successfully"
                
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Error processing command: {e}")
                return False, None, f"Processing error: {str(e)}"
    
    def _validate_command(self, command: str) -> Tuple[bool, str]:
        """
        Validate and normalize a command.
        
        Args:
            command: Raw command string
            
        Returns:
            Tuple of (is_valid: bool, normalized_command: str)
        """
        if not command:
            return False, ""
        
        # Normalize: strip whitespace and convert to lowercase
        normalized = command.strip()
        
        # Handle sequence commands (keep as-is)
        if normalized.startswith("seq "):
            return True, normalized
        
        # Parse single command
        parts = normalized.split()
        if not parts:
            return False, ""
        
        base_cmd = parts[0].lower()
        
        # Check if base command is allowed
        if base_cmd not in self.allowed_commands:
            # Check for colon format (e.g., "left:1.5")
            if ":" in base_cmd:
                cmd_name = base_cmd.split(":")[0]
                if cmd_name in self.allowed_commands:
                    return True, normalized
            return False, ""
        
        # Command is valid
        return True, normalized
    
    def _add_to_history(self, raw_cmd: str, source: str, priority: int, processed_cmd: str):
        """
        Add command to history.
        
        Args:
            raw_cmd: Original raw command
            source: Command source
            priority: Command priority
            processed_cmd: Processed command
        """
        entry = {
            "timestamp": time.time(),
            "raw": raw_cmd,
            "processed": processed_cmd,
            "source": source,
            "priority": priority
        }
        self.command_history.append(entry)
    
    def get_stats(self) -> Dict:
        """
        Get aggregator statistics.
        
        Returns:
            Dictionary containing statistics
        """
        with self.lock:
            return {
                "total_commands": self.stats["total_commands"],
                "by_source": dict(self.stats["by_source"]),
                "errors": self.stats["errors"],
                "last_command": self.last_command,
                "last_command_age": time.time() - self.last_command_time if self.last_command_time > 0 else None,
                "history_size": len(self.command_history)
            }
    
    def get_recent_history(self, count: int = 10) -> list:
        """
        Get recent command history.
        
        Args:
            count: Number of recent commands to retrieve
            
        Returns:
            List of recent command entries
        """
        with self.lock:
            history_list = list(self.command_history)
            return history_list[-count:] if count < len(history_list) else history_list
    
    def clear_history(self):
        """Clear command history."""
        with self.lock:
            self.command_history.clear()
            logger.info("Command history cleared")


# Global aggregator instance (singleton)
_aggregator_instance = None
_aggregator_lock = threading.Lock()


def get_aggregator() -> CommandAggregator:
    """
    Get the global CommandAggregator instance (singleton pattern).
    
    Returns:
        CommandAggregator instance
    """
    global _aggregator_instance
    if _aggregator_instance is None:
        with _aggregator_lock:
            if _aggregator_instance is None:
                _aggregator_instance = CommandAggregator()
    return _aggregator_instance


if __name__ == "__main__":
    # Test the aggregator
    agg = get_aggregator()
    
    # Test various commands
    test_cases = [
        ("forward", CommandSource.MANUAL, CommandPriority.NORMAL),
        ("left 1.5", CommandSource.JETSON, CommandPriority.HIGH),
        ("invalid_cmd", CommandSource.CONTROLLER, CommandPriority.NORMAL),
        ("seq forward 2; right 1; stop", CommandSource.SEQUENCE, CommandPriority.NORMAL),
        ("stop", CommandSource.JETSON, CommandPriority.HIGH),
    ]
    
    print("\n=== Testing Command Aggregator ===\n")
    for cmd, src, pri in test_cases:
        success, processed, msg = agg.process_command(cmd, src, pri)
        print(f"Command: {cmd!r}")
        print(f"  Success: {success}")
        print(f"  Processed: {processed!r}")
        print(f"  Message: {msg}\n")
    
    print("=== Statistics ===")
    import json
    print(json.dumps(agg.get_stats(), indent=2))
    
    print("\n=== Recent History ===")
    for entry in agg.get_recent_history(5):
        print(f"{entry['timestamp']:.2f} | {entry['source']:10} | {entry['processed']}")
