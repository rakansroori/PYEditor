"""
Performance Optimization System for PyVideoEditor
Handles caching, memory management, parallel processing, and resource optimization
"""

import os
import sys
import time
import threading
import multiprocessing
import psutil
import gc
import weakref
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import lru_cache, wraps
import pickle
import hashlib
import json
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("Installing numpy...")
    os.system("pip install numpy")
    import numpy as np

try:
    import psutil
except ImportError:
    print("Installing psutil...")
    os.system("pip install psutil")
    import psutil

class OptimizationLevel(Enum):
    """Performance optimization levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CUSTOM = "custom"

class CacheType(Enum):
    """Types of caching available"""
    MEMORY = "memory"
    DISK = "disk"
    HYBRID = "hybrid"
    DISTRIBUTED = "distributed"

@dataclass
class PerformanceProfile:
    """System performance profile and optimization settings"""
    cpu_cores: int = field(default_factory=lambda: multiprocessing.cpu_count())
    total_ram: int = field(default_factory=lambda: psutil.virtual_memory().total)
    available_ram: int = field(default_factory=lambda: psutil.virtual_memory().available)
    gpu_available: bool = False
    disk_speed: str = "unknown"  # SSD, HDD, NVME
    optimization_level: OptimizationLevel = OptimizationLevel.MEDIUM
    max_cache_size: int = field(default_factory=lambda: min(1024 * 1024 * 1024, psutil.virtual_memory().available // 4))  # 1GB or 25% of available RAM
    enable_parallel_processing: bool = True
    enable_gpu_acceleration: bool = False
    enable_memory_mapping: bool = True
    prefetch_enabled: bool = True
    background_optimization: bool = True

class MemoryManager:
    """Advanced memory management system"""
    
    def __init__(self, max_memory_usage: int = None):
        self.max_memory_usage = max_memory_usage or (psutil.virtual_memory().total * 0.8)
        self.memory_pool = {}
        self.weak_references = weakref.WeakValueDictionary()
        self.memory_pressure_callbacks = []
        self.last_gc_time = time.time()
        self.gc_threshold = 60  # seconds
        
    def allocate_memory(self, size: int, identifier: str = None) -> Optional[bytes]:
        """Allocate memory with tracking"""
        try:
            current_usage = self.get_current_memory_usage()
            if current_usage + size > self.max_memory_usage:
                self._handle_memory_pressure()
                
            data = bytearray(size)
            if identifier:
                self.memory_pool[identifier] = data
                
            return data
            
        except MemoryError:
            self._handle_memory_pressure()
            return None
    
    def deallocate_memory(self, identifier: str):
        """Explicitly deallocate memory"""
        if identifier in self.memory_pool:
            del self.memory_pool[identifier]
            
    def get_current_memory_usage(self) -> int:
        """Get current memory usage by the application"""
        process = psutil.Process()
        return process.memory_info().rss
        
    def _handle_memory_pressure(self):
        """Handle memory pressure situations"""
        # Force garbage collection
        gc.collect()
        
        # Clear half of the memory pool (LRU-style)
        if self.memory_pool:
            items_to_remove = len(self.memory_pool) // 2
            keys_to_remove = list(self.memory_pool.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self.memory_pool[key]
        
        # Call registered callbacks
        for callback in self.memory_pressure_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Memory pressure callback error: {e}")
    
    def register_memory_pressure_callback(self, callback: Callable):
        """Register callback for memory pressure situations"""
        self.memory_pressure_callbacks.append(callback)
    
    def auto_gc(self):
        """Automatic garbage collection based on time and memory pressure"""
        current_time = time.time()
        if current_time - self.last_gc_time > self.gc_threshold:
            if self.get_current_memory_usage() > self.max_memory_usage * 0.7:
                gc.collect()
                self.last_gc_time = current_time

class SmartCache:
    """Intelligent caching system with multiple storage backends"""
    
    def __init__(self, cache_type: CacheType = CacheType.HYBRID, max_size: int = 1024*1024*1024):
        self.cache_type = cache_type
        self.max_size = max_size
        self.memory_cache = {}
        self.disk_cache_path = Path.home() / ".pyvideo_cache"
        self.disk_cache_path.mkdir(exist_ok=True)
        self.access_times = {}
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
        self.lock = threading.RLock()
        
    def _generate_key(self, data: Any) -> str:
        """Generate cache key from data"""
        if isinstance(data, (str, int, float)):
            return hashlib.md5(str(data).encode()).hexdigest()
        elif hasattr(data, '__dict__'):
            return hashlib.md5(str(data.__dict__).encode()).hexdigest()
        else:
            return hashlib.md5(str(data).encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            # Check memory cache first
            if key in self.memory_cache:
                self.access_times[key] = time.time()
                self.cache_stats["hits"] += 1
                return self.memory_cache[key]
            
            # Check disk cache
            if self.cache_type in [CacheType.DISK, CacheType.HYBRID]:
                disk_file = self.disk_cache_path / f"{key}.cache"
                if disk_file.exists():
                    try:
                        with open(disk_file, 'rb') as f:
                            data = pickle.load(f)
                        
                        # Move to memory cache if hybrid
                        if self.cache_type == CacheType.HYBRID:
                            self.memory_cache[key] = data
                            
                        self.access_times[key] = time.time()
                        self.cache_stats["hits"] += 1
                        return data
                    except Exception as e:
                        print(f"Error loading from disk cache: {e}")
            
            self.cache_stats["misses"] += 1
            return None
    
    def put(self, key: str, value: Any):
        """Put item in cache"""
        with self.lock:
            current_time = time.time()
            
            # Memory cache
            if self.cache_type in [CacheType.MEMORY, CacheType.HYBRID]:
                self.memory_cache[key] = value
                self.access_times[key] = current_time
                
                # Check if we need to evict items
                if len(self.memory_cache) > self.max_size // 1024:  # Rough item count limit
                    self._evict_lru_memory()
            
            # Disk cache
            if self.cache_type in [CacheType.DISK, CacheType.HYBRID]:
                try:
                    disk_file = self.disk_cache_path / f"{key}.cache"
                    with open(disk_file, 'wb') as f:
                        pickle.dump(value, f)
                    self.access_times[key] = current_time
                except Exception as e:
                    print(f"Error saving to disk cache: {e}")
    
    def _evict_lru_memory(self):
        """Evict least recently used items from memory cache"""
        if not self.memory_cache:
            return
            
        # Sort by access time and remove oldest 25%
        sorted_items = sorted(self.access_times.items(), key=lambda x: x[1])
        items_to_remove = len(sorted_items) // 4
        
        for key, _ in sorted_items[:items_to_remove]:
            if key in self.memory_cache:
                del self.memory_cache[key]
                del self.access_times[key]
                self.cache_stats["evictions"] += 1
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.memory_cache.clear()
            self.access_times.clear()
            
            # Clear disk cache
            if self.cache_type in [CacheType.DISK, CacheType.HYBRID]:
                for cache_file in self.disk_cache_path.glob("*.cache"):
                    try:
                        cache_file.unlink()
                    except Exception:
                        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0
            
            return {
                "hits": self.cache_stats["hits"],
                "misses": self.cache_stats["misses"],
                "evictions": self.cache_stats["evictions"],
                "hit_rate": hit_rate,
                "memory_items": len(self.memory_cache),
                "disk_items": len(list(self.disk_cache_path.glob("*.cache")))
            }

class ParallelProcessor:
    """Parallel processing manager for CPU-intensive tasks"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 8)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=self.max_workers)
        self.active_tasks = []
        
    def submit_thread_task(self, func: Callable, *args, **kwargs):
        """Submit task to thread pool"""
        future = self.thread_pool.submit(func, *args, **kwargs)
        self.active_tasks.append(future)
        return future
    
    def submit_process_task(self, func: Callable, *args, **kwargs):
        """Submit task to process pool"""
        future = self.process_pool.submit(func, *args, **kwargs)
        self.active_tasks.append(future)
        return future
    
    def map_parallel(self, func: Callable, items: List[Any], use_processes: bool = False) -> List[Any]:
        """Map function over items in parallel"""
        if use_processes:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                return list(executor.map(func, items))
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                return list(executor.map(func, items))
    
    def batch_process(self, items: List[Any], batch_func: Callable, batch_size: int = None, use_processes: bool = False) -> List[Any]:
        """Process items in batches"""
        if batch_size is None:
            batch_size = max(1, len(items) // self.max_workers)
        
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        if use_processes:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(batch_func, batch) for batch in batches]
                results = []
                for future in as_completed(futures):
                    results.extend(future.result())
                return results
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(batch_func, batch) for batch in batches]
                results = []
                for future in as_completed(futures):
                    results.extend(future.result())
                return results
    
    def wait_for_completion(self, timeout: float = None):
        """Wait for all active tasks to complete"""
        completed = []
        for future in as_completed(self.active_tasks, timeout=timeout):
            completed.append(future)
        
        # Clean up completed tasks
        self.active_tasks = [f for f in self.active_tasks if f not in completed]
        return completed
    
    def cancel_all_tasks(self):
        """Cancel all pending tasks"""
        for future in self.active_tasks:
            future.cancel()
        self.active_tasks.clear()
    
    def shutdown(self):
        """Shutdown the parallel processor"""
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)

class ResourceMonitor:
    """System resource monitoring and optimization"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self.monitoring_active = False
        self.monitoring_thread = None
        self.resource_history = []
        self.max_history_length = 300  # 5 minutes at 1 second intervals
        self.optimization_callbacks = []
        
    def start_monitoring(self):
        """Start resource monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitor_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                
                # Get process-specific metrics
                process = psutil.Process()
                process_memory = process.memory_info()
                process_cpu = process.cpu_percent()
                
                metrics = {
                    'timestamp': time.time(),
                    'system_cpu': cpu_percent,
                    'system_memory_percent': memory.percent,
                    'system_memory_available': memory.available,
                    'process_cpu': process_cpu,
                    'process_memory_rss': process_memory.rss,
                    'process_memory_vms': process_memory.vms,
                    'disk_read_bytes': disk_io.read_bytes if disk_io else 0,
                    'disk_write_bytes': disk_io.write_bytes if disk_io else 0,
                }
                
                # Add to history
                self.resource_history.append(metrics)
                if len(self.resource_history) > self.max_history_length:
                    self.resource_history.pop(0)
                
                # Check for optimization opportunities
                self._check_optimization_triggers(metrics)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                print(f"Error in resource monitoring: {e}")
                time.sleep(self.monitoring_interval)
    
    def _check_optimization_triggers(self, metrics: Dict[str, Any]):
        """Check if optimization should be triggered"""
        # High memory usage
        if metrics['system_memory_percent'] > 85:
            self._trigger_optimization('high_memory_usage', metrics)
        
        # High CPU usage sustained
        if len(self.resource_history) >= 10:
            recent_cpu = [m['system_cpu'] for m in self.resource_history[-10:]]
            if all(cpu > 90 for cpu in recent_cpu):
                self._trigger_optimization('high_cpu_usage', metrics)
        
        # Low available memory
        if metrics['system_memory_available'] < 500 * 1024 * 1024:  # Less than 500MB
            self._trigger_optimization('low_memory', metrics)
    
    def _trigger_optimization(self, trigger_type: str, metrics: Dict[str, Any]):
        """Trigger optimization callbacks"""
        for callback in self.optimization_callbacks:
            try:
                callback(trigger_type, metrics)
            except Exception as e:
                print(f"Optimization callback error: {e}")
    
    def register_optimization_callback(self, callback: Callable):
        """Register callback for optimization triggers"""
        self.optimization_callbacks.append(callback)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.resource_history:
            return {}
        
        recent_metrics = self.resource_history[-min(60, len(self.resource_history)):]  # Last minute
        
        avg_cpu = sum(m['system_cpu'] for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m['system_memory_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_process_cpu = sum(m['process_cpu'] for m in recent_metrics) / len(recent_metrics)
        
        return {
            'avg_system_cpu': avg_cpu,
            'avg_system_memory': avg_memory,
            'avg_process_cpu': avg_process_cpu,
            'current_memory_usage': recent_metrics[-1]['process_memory_rss'] if recent_metrics else 0,
            'monitoring_duration': len(self.resource_history) * self.monitoring_interval,
            'sample_count': len(self.resource_history)
        }

def performance_timer(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Store timing information
        if not hasattr(wrapper, 'timing_history'):
            wrapper.timing_history = []
        wrapper.timing_history.append(execution_time)
        
        # Keep only last 100 measurements
        if len(wrapper.timing_history) > 100:
            wrapper.timing_history = wrapper.timing_history[-100:]
        
        # Log slow operations
        if execution_time > 1.0:  # More than 1 second
            print(f"Slow operation detected: {func.__name__} took {execution_time:.3f}s")
        
        return result
    
    def get_timing_stats():
        if hasattr(wrapper, 'timing_history') and wrapper.timing_history:
            history = wrapper.timing_history
            return {
                'count': len(history),
                'avg_time': sum(history) / len(history),
                'min_time': min(history),
                'max_time': max(history),
                'total_time': sum(history)
            }
        return {}
    
    wrapper.get_timing_stats = get_timing_stats
    return wrapper

class PerformanceOptimizer:
    """Main performance optimization coordinator"""
    
    def __init__(self, profile: PerformanceProfile = None):
        self.profile = profile or PerformanceProfile()
        self.memory_manager = MemoryManager(self.profile.max_cache_size)
        self.cache = SmartCache(CacheType.HYBRID, self.profile.max_cache_size)
        self.parallel_processor = ParallelProcessor(self.profile.cpu_cores)
        self.resource_monitor = ResourceMonitor()
        
        # Register optimization callbacks
        self.resource_monitor.register_optimization_callback(self._handle_resource_pressure)
        self.memory_manager.register_memory_pressure_callback(self._handle_memory_pressure)
        
        # Start background monitoring if enabled
        if self.profile.background_optimization:
            self.resource_monitor.start_monitoring()
    
    def _handle_resource_pressure(self, trigger_type: str, metrics: Dict[str, Any]):
        """Handle resource pressure situations"""
        if trigger_type == 'high_memory_usage':
            # Clear caches
            self.cache.clear()
            self.memory_manager._handle_memory_pressure()
            
        elif trigger_type == 'high_cpu_usage':
            # Reduce parallel processing
            if self.parallel_processor.max_workers > 2:
                self.parallel_processor.max_workers = max(2, self.parallel_processor.max_workers // 2)
                
        elif trigger_type == 'low_memory':
            # Emergency memory cleanup
            self.cache.clear()
            self.memory_manager._handle_memory_pressure()
            gc.collect()
    
    def _handle_memory_pressure(self):
        """Handle memory pressure from memory manager"""
        self.cache._evict_lru_memory()
        gc.collect()
    
    def optimize_for_task(self, task_type: str) -> Dict[str, Any]:
        """Optimize system for specific task type"""
        optimizations = {}
        
        if task_type == 'video_export':
            # Optimize for sequential processing
            optimizations['parallel_threads'] = min(4, self.profile.cpu_cores)
            optimizations['cache_strategy'] = 'minimal'
            optimizations['memory_limit'] = self.profile.max_cache_size * 0.8
            
        elif task_type == 'real_time_preview':
            # Optimize for low latency
            optimizations['parallel_threads'] = self.profile.cpu_cores
            optimizations['cache_strategy'] = 'aggressive'
            optimizations['memory_limit'] = self.profile.max_cache_size * 1.2
            
        elif task_type == 'batch_processing':
            # Optimize for throughput
            optimizations['parallel_threads'] = self.profile.cpu_cores * 2
            optimizations['cache_strategy'] = 'moderate'
            optimizations['memory_limit'] = self.profile.max_cache_size
            
        elif task_type == 'effects_rendering':
            # Optimize for computational tasks
            optimizations['parallel_threads'] = self.profile.cpu_cores
            optimizations['cache_strategy'] = 'aggressive'
            optimizations['memory_limit'] = self.profile.max_cache_size * 1.5
        
        return optimizations
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'system_profile': {
                'cpu_cores': self.profile.cpu_cores,
                'total_ram': self.profile.total_ram,
                'available_ram': self.profile.available_ram,
                'optimization_level': self.profile.optimization_level.value
            },
            'cache_stats': self.cache.get_stats(),
            'resource_monitoring': self.resource_monitor.get_performance_summary(),
            'memory_usage': self.memory_manager.get_current_memory_usage(),
            'active_parallel_tasks': len(self.parallel_processor.active_tasks)
        }
    
    def shutdown(self):
        """Shutdown the performance optimizer"""
        self.resource_monitor.stop_monitoring()
        self.parallel_processor.shutdown()
        self.cache.clear()

# Global performance optimizer instance
global_optimizer = None

def get_global_optimizer() -> PerformanceOptimizer:
    """Get or create global performance optimizer"""
    global global_optimizer
    if global_optimizer is None:
        global_optimizer = PerformanceOptimizer()
    return global_optimizer

def auto_optimize(task_type: str = None):
    """Decorator for automatic performance optimization"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            optimizer = get_global_optimizer()
            
            if task_type:
                optimizations = optimizer.optimize_for_task(task_type)
                print(f"Optimizing for {task_type}: {optimizations}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
