import concurrent.futures
import requests
import time
import argparse
from typing import Optional
import threading
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Stats:
    response_codes: Counter = field(default_factory=Counter)
    error_count: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


def make_request(url: str, start_time: float, period: float, stop_event: threading.Event, 
                stats: Stats, verbose: bool):
    next_request_time = time.time()
    
    while not stop_event.is_set():
        scheduled_time = next_request_time
        now = time.time()
        if now < scheduled_time:
            remaining = scheduled_time - now
            if stop_event.wait(timeout=remaining):
                break
        
        try:
            actual_start = time.time()
            response = requests.get(url)

            with stats.lock:
                stats.response_codes[response.status_code] += 1

            if verbose:
                end_time = time.time()
                response_time = round(end_time - actual_start, 3)
                relative_time = round(end_time - start_time, 3)
                print(
                    f"time: {relative_time}, "
                    f"query: {url}, response_time: {response_time}, "
                    f"response_code: {response.status_code}"
                )
                
        except Exception as e:
            with stats.lock:
                stats.error_count += 1
                
            if verbose and not stop_event.is_set():
                relative_time = round(scheduled_time - start_time, 3)
                print(
                    f"time: {relative_time}, query: {url}, error: {str(e)}"
                )
        
        next_request_time = scheduled_time + period


def print_final_stats(stats: Stats):
    print("Response Codes:")
    for code, count in sorted(stats.response_codes.items()):
        print(f"  {code}: {count}")
    if stats.error_count > 0:
        print(f"Total Errors: {stats.error_count}")


def main(duration_seconds: Optional[int], period: int, verbose: bool):
    urls = [
        f"http://localhost:8011/wines/recommendations?query={i}" for i in range(10)
    ]
    
    start_time = time.time()
    stop_event = threading.Event()
    stats = Stats()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(make_request, urls[i], start_time, period, stop_event, stats, verbose)
            for i in range(len(urls))
        ]
        
        try:
            if duration_seconds:
                time.sleep(duration_seconds)
            else:
                concurrent.futures.wait(futures)
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
            concurrent.futures.wait(futures, timeout=5)
            print_final_stats(stats)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run rate-limited parallel HTTP requests')
    parser.add_argument('--duration', type=int, help='Duration to run in seconds', default=None)
    parser.add_argument('--period', type=float, help='Time between requests in seconds', default=1)
    parser.add_argument('--verbose', action='store_true', help='Print detailed per-request results')
    args = parser.parse_args()
    main(args.duration, args.period, args.verbose)
