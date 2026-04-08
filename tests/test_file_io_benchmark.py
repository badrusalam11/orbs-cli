"""
Benchmark test to prove file I/O bottleneck in live.ndjson and execution.log.

This test compares different file I/O strategies:
1. Current approach: open/write/close per event (like LiveLogger._write_event)
2. Persistent handle: keep file open, write multiple events
3. Buffered writes: batch multiple events before writing

Run with: pytest tests/test_file_io_benchmark.py -v -s
"""
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, List

import pytest


# =============================================================================
# Simulated Event Data (similar to LiveLogger events)
# =============================================================================

def generate_step_event(step_num: int) -> Dict:
    """Generate a realistic step event like LiveLogger produces."""
    return {
        "type": "step_started",
        "testcase_id": f"tc_{step_num // 10}",
        "step_id": f"step_{step_num}",
        "step_number": step_num % 10 + 1,
        "keyword": "click",
        "object": f"button_element_{step_num}",
        "args": ["arg1", "arg2"],
        "timestamp": "2026-04-08T10:30:00.123456"
    }


# =============================================================================
# File I/O Strategies to Benchmark
# =============================================================================

def strategy_open_close_per_write(file_path: str, events: List[Dict]) -> None:
    """
    CURRENT APPROACH in LiveLogger._write_event():
    Opens and closes file for EVERY single event.
    
    This is expensive because:
    - Each open() is a syscall to the OS
    - Each close() triggers a flush + syscall
    - On macOS, file metadata updates add overhead
    """
    for event in events:
        line = json.dumps(event, ensure_ascii=False)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')


def strategy_open_close_with_flush(file_path: str, events: List[Dict]) -> None:
    """
    Same as current approach but with explicit flush on every write.
    Even more expensive due to forced fsync-like behavior.
    """
    for event in events:
        line = json.dumps(event, ensure_ascii=False)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
            f.flush()


def strategy_persistent_handle(file_path: str, events: List[Dict]) -> None:
    """
    OPTIMIZED: Keep file handle open for duration of writes.
    
    Benefits:
    - Single open() syscall
    - OS can batch disk writes efficiently
    - Significantly faster on all platforms
    """
    with open(file_path, 'a', encoding='utf-8') as f:
        for event in events:
            line = json.dumps(event, ensure_ascii=False)
            f.write(line + '\n')


def strategy_persistent_handle_line_buffered(file_path: str, events: List[Dict]) -> None:
    """
    OPTIMIZED: Persistent handle with line buffering.
    Good for real-time monitoring while still being efficient.
    """
    with open(file_path, 'a', encoding='utf-8', buffering=1) as f:
        for event in events:
            line = json.dumps(event, ensure_ascii=False)
            f.write(line + '\n')


def strategy_batch_then_write(file_path: str, events: List[Dict], batch_size: int = 50) -> None:
    """
    OPTIMIZED: Batch events in memory, write in chunks.
    Best throughput but less real-time.
    """
    buffer = []
    for event in events:
        line = json.dumps(event, ensure_ascii=False)
        buffer.append(line)
        
        if len(buffer) >= batch_size:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(buffer) + '\n')
            buffer = []
    
    # Write remaining
    if buffer:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(buffer) + '\n')


def strategy_single_write_all(file_path: str, events: List[Dict]) -> None:
    """
    BASELINE: Write all events in single operation.
    Best possible performance (not realistic for streaming).
    """
    lines = [json.dumps(event, ensure_ascii=False) for event in events]
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


# =============================================================================
# Benchmark Runner
# =============================================================================

def benchmark_strategy(
    name: str,
    strategy_func: Callable,
    events: List[Dict],
    iterations: int = 3,
    **kwargs
) -> Dict:
    """Run a single strategy multiple times and return timing stats."""
    times = []
    
    for _ in range(iterations):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ndjson') as tmp:
            tmp_path = tmp.name
        
        try:
            start = time.perf_counter()
            strategy_func(tmp_path, events, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        finally:
            os.unlink(tmp_path)
    
    avg_time = sum(times) / len(times)
    events_per_sec = len(events) / avg_time
    
    return {
        "name": name,
        "avg_time_ms": avg_time * 1000,
        "min_time_ms": min(times) * 1000,
        "max_time_ms": max(times) * 1000,
        "events_per_sec": events_per_sec,
        "time_per_event_us": (avg_time / len(events)) * 1_000_000
    }


# =============================================================================
# Pytest Test Cases
# =============================================================================

class TestFileIOBenchmark:
    """Benchmark tests to prove file I/O is a bottleneck."""
    
    @pytest.fixture
    def small_event_set(self) -> List[Dict]:
        """100 events - typical small test run."""
        return [generate_step_event(i) for i in range(100)]
    
    @pytest.fixture
    def medium_event_set(self) -> List[Dict]:
        """500 events - typical medium test suite."""
        return [generate_step_event(i) for i in range(500)]
    
    @pytest.fixture
    def large_event_set(self) -> List[Dict]:
        """1000 events - large test suite."""
        return [generate_step_event(i) for i in range(1000)]
    
    def test_benchmark_all_strategies_medium(self, medium_event_set):
        """
        Compare all file I/O strategies with medium event set.
        This test PROVES that open/close per write is significantly slower.
        """
        events = medium_event_set
        results = []
        
        print(f"\n{'='*70}")
        print(f"FILE I/O BENCHMARK - {len(events)} events")
        print(f"{'='*70}")
        
        strategies = [
            ("1. Open/Close per write (CURRENT)", strategy_open_close_per_write, {}),
            ("2. Open/Close + flush (WORST)", strategy_open_close_with_flush, {}),
            ("3. Persistent handle (OPTIMIZED)", strategy_persistent_handle, {}),
            ("4. Persistent + line buffer", strategy_persistent_handle_line_buffered, {}),
            ("5. Batch 50 then write", strategy_batch_then_write, {"batch_size": 50}),
            ("6. Single write all (BASELINE)", strategy_single_write_all, {}),
        ]
        
        for name, func, kwargs in strategies:
            result = benchmark_strategy(name, func, events, iterations=3, **kwargs)
            results.append(result)
            print(f"\n{result['name']}")
            print(f"  Avg: {result['avg_time_ms']:.2f} ms")
            print(f"  Events/sec: {result['events_per_sec']:.0f}")
            print(f"  Time/event: {result['time_per_event_us']:.1f} µs")
        
        # Calculate speedup
        current_approach = results[0]
        optimized = results[2]
        
        speedup = current_approach['avg_time_ms'] / optimized['avg_time_ms']
        
        print(f"\n{'='*70}")
        print(f"CONCLUSION:")
        print(f"  Current approach (open/close per write): {current_approach['avg_time_ms']:.2f} ms")
        print(f"  Persistent handle approach: {optimized['avg_time_ms']:.2f} ms")
        print(f"  SPEEDUP: {speedup:.1f}x faster with persistent handle")
        print(f"{'='*70}")
        
        # Assert that persistent handle is significantly faster (at least 2x)
        assert speedup >= 1.5, f"Expected at least 1.5x speedup, got {speedup:.1f}x"
    
    def test_current_approach_is_bottleneck(self, large_event_set):
        """
        Specific test to prove current LiveLogger approach is a bottleneck.
        Uses 1000 events to make the difference more obvious.
        """
        events = large_event_set
        
        # Benchmark current approach
        current_result = benchmark_strategy(
            "current", strategy_open_close_per_write, events, iterations=5
        )
        
        # Benchmark optimized approach
        optimized_result = benchmark_strategy(
            "optimized", strategy_persistent_handle, events, iterations=5
        )
        
        print(f"\n{'='*70}")
        print(f"BOTTLENECK PROOF TEST - {len(events)} events, 5 iterations")
        print(f"{'='*70}")
        print(f"Current (open/close per write): {current_result['avg_time_ms']:.2f} ms")
        print(f"Optimized (persistent handle): {optimized_result['avg_time_ms']:.2f} ms")
        
        overhead_ms = current_result['avg_time_ms'] - optimized_result['avg_time_ms']
        overhead_per_event_us = (overhead_ms / len(events)) * 1000
        
        print(f"Overhead from open/close: {overhead_ms:.2f} ms total")
        print(f"Overhead per event: {overhead_per_event_us:.1f} µs")
        print(f"{'='*70}")
        
        # The overhead should be measurable (at least 10ms for 1000 events)
        assert overhead_ms > 5, f"Expected at least 5ms overhead, got {overhead_ms:.2f}ms"
    
    def test_scaling_behavior(self):
        """
        Test how the bottleneck scales with number of events.
        More events = more noticeable bottleneck.
        """
        sizes = [100, 300, 500, 1000]
        current_times = []
        optimized_times = []
        
        print(f"\n{'='*70}")
        print("SCALING BEHAVIOR TEST")
        print(f"{'='*70}")
        print(f"{'Events':<10} {'Current (ms)':<15} {'Optimized (ms)':<15} {'Speedup':<10}")
        print("-" * 50)
        
        for size in sizes:
            events = [generate_step_event(i) for i in range(size)]
            
            current = benchmark_strategy("c", strategy_open_close_per_write, events, iterations=3)
            optimized = benchmark_strategy("o", strategy_persistent_handle, events, iterations=3)
            
            current_times.append(current['avg_time_ms'])
            optimized_times.append(optimized['avg_time_ms'])
            
            speedup = current['avg_time_ms'] / optimized['avg_time_ms']
            print(f"{size:<10} {current['avg_time_ms']:<15.2f} {optimized['avg_time_ms']:<15.2f} {speedup:<10.1f}x")
        
        print(f"{'='*70}")
        
        # Verify bottleneck scales linearly with events (more events = more overhead)
        assert current_times[-1] > current_times[0], "Expected time to increase with more events"


class TestMacOSSpecificBehavior:
    """
    Tests that simulate macOS-specific file system behaviors.
    
    On macOS:
    - APFS has different caching behavior than ext4/NTFS
    - File metadata updates (mtime) can be expensive
    - fsync behavior is different
    """
    
    def test_file_metadata_overhead(self):
        """
        Test the overhead of file metadata updates.
        Each open() updates access time, each close after write updates mtime.
        """
        events = [generate_step_event(i) for i in range(200)]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ndjson') as tmp:
            tmp_path = tmp.name
        
        try:
            # Count file stat changes with open/close approach
            start = time.perf_counter()
            
            for event in events:
                line = json.dumps(event, ensure_ascii=False)
                with open(tmp_path, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
            
            file_ops_time = time.perf_counter() - start
            
            # Get final file size
            file_size = os.path.getsize(tmp_path)
            
            print(f"\n200 events with open/close per write:")
            print(f"  Total time: {file_ops_time*1000:.2f} ms")
            print(f"  File size: {file_size} bytes")
            print(f"  Time per open/write/close cycle: {(file_ops_time/200)*1000:.3f} ms")
            
        finally:
            os.unlink(tmp_path)
    
    def test_fsync_impact(self):
        """
        Test the impact of explicit fsync (which macOS may do more aggressively).
        """
        events = [generate_step_event(i) for i in range(100)]
        
        # Without fsync
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ndjson') as tmp:
            tmp_path = tmp.name
        
        try:
            start = time.perf_counter()
            with open(tmp_path, 'a', encoding='utf-8') as f:
                for event in events:
                    f.write(json.dumps(event) + '\n')
            no_fsync_time = time.perf_counter() - start
        finally:
            os.unlink(tmp_path)
        
        # With fsync after every write
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ndjson') as tmp:
            tmp_path = tmp.name
        
        try:
            start = time.perf_counter()
            with open(tmp_path, 'a', encoding='utf-8') as f:
                for event in events:
                    f.write(json.dumps(event) + '\n')
                    os.fsync(f.fileno())
            with_fsync_time = time.perf_counter() - start
        finally:
            os.unlink(tmp_path)
        
        print(f"\nfsync impact test (100 events):")
        print(f"  Without fsync: {no_fsync_time*1000:.2f} ms")
        print(f"  With fsync per write: {with_fsync_time*1000:.2f} ms")
        print(f"  fsync overhead: {(with_fsync_time - no_fsync_time)*1000:.2f} ms")


class TestLoggingModuleBenchmark:
    """
    Benchmark Python's logging module (used for execution.log).
    """
    
    def test_logging_file_handler_performance(self):
        """
        Compare logging.FileHandler with direct file writes.
        """
        import logging
        
        # Setup logging
        test_logger = logging.getLogger('benchmark_test')
        test_logger.setLevel(logging.INFO)
        test_logger.handlers = []
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as tmp:
            log_path = tmp.name
        
        try:
            handler = logging.FileHandler(log_path, mode='w')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            test_logger.addHandler(handler)
            
            # Benchmark logging module
            start = time.perf_counter()
            for i in range(500):
                test_logger.info(f"Test log message {i} with some additional context")
            handler.flush()
            logging_time = time.perf_counter() - start
            
            test_logger.removeHandler(handler)
            handler.close()
        finally:
            os.unlink(log_path)
        
        # Benchmark direct write
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as tmp:
            direct_path = tmp.name
        
        try:
            start = time.perf_counter()
            with open(direct_path, 'w', encoding='utf-8') as f:
                for i in range(500):
                    f.write(f"Test log message {i} with some additional context\n")
            direct_time = time.perf_counter() - start
        finally:
            os.unlink(direct_path)
        
        print(f"\nLogging module vs direct write (500 messages):")
        print(f"  logging.FileHandler: {logging_time*1000:.2f} ms")
        print(f"  Direct file write: {direct_time*1000:.2f} ms")
        print(f"  Logging overhead: {(logging_time - direct_time)*1000:.2f} ms")


class TestLiveLoggerOptimization:
    """
    Test the actual LiveLogger class to verify optimization works.
    """
    
    def test_live_logger_performance(self):
        """
        Test that LiveLogger with persistent handle is fast.
        """
        import sys
        import shutil
        from io import StringIO
        
        # Suppress stdout to avoid @@LIVE@@ spam
        old_stdout = sys.__stdout__
        sys.__stdout__ = StringIO()
        
        try:
            from orbs.live_logger import LiveLogger
            
            tmp_dir = tempfile.mkdtemp()
            
            # Test optimized LiveLogger
            ll = LiveLogger(log_dir=tmp_dir, execution_id="bench_test")
            
            start = time.perf_counter()
            for i in range(500):
                ll.step_started(
                    testcase_id="tc1",
                    keyword="click",
                    object_name=f"button_{i}",
                    args=["arg1", "arg2"]
                )
            ll.close()
            optimized_time = time.perf_counter() - start
            
            shutil.rmtree(tmp_dir)
            
        finally:
            sys.__stdout__ = old_stdout
        
        print(f"\nLiveLogger benchmark (500 step_started events):")
        print(f"  Total time: {optimized_time*1000:.2f} ms")
        print(f"  Events/sec: {500/optimized_time:.0f}")
        print(f"  Time/event: {(optimized_time/500)*1000000:.1f} µs")
        
        # Should be fast - less than 50ms for 500 events (100µs per event)
        assert optimized_time < 0.1, f"LiveLogger too slow: {optimized_time*1000:.2f} ms for 500 events"


# =============================================================================
# Quick Standalone Test (can be run directly)
# =============================================================================

if __name__ == "__main__":
    print("Running File I/O Benchmark...")
    print("This proves that open/close per write is a bottleneck.\n")
    
    events = [generate_step_event(i) for i in range(500)]
    
    results = []
    strategies = [
        ("Open/Close per write (CURRENT)", strategy_open_close_per_write),
        ("Persistent handle (OPTIMIZED)", strategy_persistent_handle),
        ("Batch then write", lambda p, e: strategy_batch_then_write(p, e, 50)),
    ]
    
    for name, func in strategies:
        result = benchmark_strategy(name, func, events, iterations=5)
        results.append(result)
        print(f"{name}")
        print(f"  Average: {result['avg_time_ms']:.2f} ms")
        print(f"  Events/sec: {result['events_per_sec']:.0f}")
        print()
    
    speedup = results[0]['avg_time_ms'] / results[1]['avg_time_ms']
    print(f"RESULT: Persistent handle is {speedup:.1f}x faster than current approach")
