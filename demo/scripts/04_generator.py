import requests
import time
import argparse
import threading

from typing import Optional
from collections import Counter
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, wait

import yaspin


@dataclass
class Stats:
    response_codes: Counter = field(default_factory=Counter)
    error_count: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def count_response(self, status_code: int):
        with self.lock:
            self.response_codes[status_code] += 1

    def count_error(self):
        with self.lock:
            self.error_count += 1


def make_request(
    url: str,
    start_time: float,
    period: float,
    stop_event: threading.Event,
    stats: Stats,
    verbose: bool,
):
    next_request_time = time.time()
    while not stop_event.is_set():
        scheduled_time = next_request_time
        now = time.time()
        if now < scheduled_time:
            remaining = scheduled_time - now
            if stop_event.wait(timeout=remaining):
                break

        try:
            id = threading.get_ident()
            actual_start = time.time()
            if verbose:
                print(f"event:starting, thread_id: {id}, url: {url}")

            response = requests.get(url)
            stats.count_response(status_code=response.status_code)

            if verbose:
                end_time = time.time()
                response_time = round(end_time - actual_start, 3)
                relative_time = round(end_time - start_time, 3)
                print(
                    f"event:returned, thread_id: {id}, time: {relative_time}, "
                    f"url: {url}, response_time: {response_time}, "
                    f"response_code: {response.status_code}"
                )

        except Exception as e:
            stats.count_error()

            if verbose and not stop_event.is_set():
                relative_time = round(scheduled_time - start_time, 3)
                print(f"time: {relative_time}, query: {url}, error: {str(e)}")

        next_request_time = scheduled_time + period


def print_final_stats(stats: Stats):
    print("Response Codes:")
    for code, count in sorted(stats.response_codes.items()):
        print(f"  {code}: {count}")
    if stats.error_count > 0:
        print(f"Total Errors: {stats.error_count}")


def main(url, vals, duration_seconds: Optional[int], period: int, verbose: bool):
    urls = [f"{url}{q}" for q in vals]

    start_time = time.time()
    stop_event = threading.Event()
    stats = Stats()

    with yaspin.kbi_safe_yaspin(timer=True, text="making recommendations requests..."):
        with ThreadPoolExecutor(max_workers=len(urls)) as executor:
            futures = [
                executor.submit(
                    make_request,
                    urls[i],
                    start_time,
                    period,
                    stop_event,
                    stats,
                    verbose,
                )
                for i in range(len(urls))
            ]
            try:
                if duration_seconds:
                    time.sleep(duration_seconds)
                else:
                    wait(futures)
            except KeyboardInterrupt:
                pass
            finally:
                stop_event.set()
                wait(futures, timeout=5)
    print_final_stats(stats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run rate-limited parallel HTTP requests"
    )
    parser.add_argument(
        "--duration", type=int, help="Duration to run in seconds", default=None
    )
    parser.add_argument(
        "--period", type=float, help="Time between requests in seconds", default=1
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print detailed per-request results"
    )
    parser.add_argument(
        "--url", type=str, help="The url prefix to request", default="http://localhost:8010/api/wine/recs?query="
    )
    parser.add_argument(
        "--vals", type=str, help="Comma separated list to attach to end of url", default="red,white,rose,pinot noir,france,italy,germany,greece,australia,portugal"
    )
    args = parser.parse_args()
    vals = args.vals.split(",")
    main(args.url, vals, args.duration, args.period, args.verbose)
