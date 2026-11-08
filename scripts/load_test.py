"""Cautious end-to-end load test for the production order screen."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import math
import sys
from dataclasses import dataclass
from time import perf_counter
from urllib.parse import urlparse

import httpx

DEFAULT_BASE_URL = "https://datahub.honghadatahub.com"
MAX_CONCURRENCY = 50


@dataclass(frozen=True)
class RequestResult:
    endpoint: str
    status_code: int | None
    elapsed_seconds: float
    error: str | None = None

    @property
    def successful(self) -> bool:
        return self.error is None and self.status_code is not None and 200 <= self.status_code < 300


def parse_stages(raw_value: str) -> list[int]:
    try:
        stages = [int(part.strip()) for part in raw_value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Các mức tải phải là số nguyên, cách nhau bằng dấu phẩy.") from exc
    if not stages or any(stage < 1 or stage > MAX_CONCURRENCY for stage in stages):
        raise argparse.ArgumentTypeError(
            f"Mỗi mức tải phải nằm trong khoảng 1-{MAX_CONCURRENCY}."
        )
    if stages != sorted(set(stages)):
        raise argparse.ArgumentTypeError("Các mức tải phải tăng dần và không được trùng nhau.")
    return stages


def percentile(values: list[float], percent: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(math.ceil((percent / 100) * len(ordered)) - 1, 0)
    return ordered[index]


def validate_base_url(value: str, *, allow_http: bool) -> str:
    parsed = urlparse(value)
    allowed_schemes = {"https", "http"} if allow_http else {"https"}
    if parsed.scheme not in allowed_schemes or not parsed.hostname or parsed.path not in {"", "/"}:
        raise ValueError("URL phải là địa chỉ gốc HTTPS, không chứa path, query hoặc fragment.")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError("URL không được chứa thông tin đăng nhập, query hoặc fragment.")
    return value.rstrip("/")


async def timed_get(
    client: httpx.AsyncClient,
    *,
    endpoint: str,
    path: str,
    release: asyncio.Event,
) -> RequestResult:
    await release.wait()
    started = perf_counter()
    try:
        response = await client.get(path)
        return RequestResult(endpoint, response.status_code, perf_counter() - started)
    except httpx.RequestError as exc:
        return RequestResult(
            endpoint,
            None,
            perf_counter() - started,
            type(exc).__name__,
        )


async def run_stage(client: httpx.AsyncClient, users: int) -> list[RequestResult]:
    release = asyncio.Event()
    tasks: list[asyncio.Task[RequestResult]] = []
    for _ in range(users):
        tasks.append(
            asyncio.create_task(
                timed_get(
                    client,
                    endpoint="orders",
                    path=(
                        "/api/orders?page_number=1&page_size=20"
                        "&include_summary=false&sort_by=recent"
                    ),
                    release=release,
                )
            )
        )
        tasks.append(
            asyncio.create_task(
                timed_get(
                    client,
                    endpoint="summary",
                    path="/api/orders/summary",
                    release=release,
                )
            )
        )
    await asyncio.sleep(0)
    release.set()
    return await asyncio.gather(*tasks)


def print_stage(users: int, results: list[RequestResult]) -> tuple[float, float]:
    failures = [result for result in results if not result.successful]
    error_rate = len(failures) / len(results)
    elapsed = [result.elapsed_seconds for result in results]
    print(
        f"\nMức {users:>2} người | {len(results):>3} request | "
        f"thành công {len(results) - len(failures):>3}/{len(results)} | "
        f"p50={percentile(elapsed, 50):.2f}s | p95={percentile(elapsed, 95):.2f}s | "
        f"lỗi={error_rate:.1%}"
    )
    for endpoint in ("orders", "summary"):
        endpoint_results = [result for result in results if result.endpoint == endpoint]
        endpoint_elapsed = [result.elapsed_seconds for result in endpoint_results]
        endpoint_failures = [result for result in endpoint_results if not result.successful]
        print(
            f"  - {endpoint:<7}: p50={percentile(endpoint_elapsed, 50):.2f}s, "
            f"p95={percentile(endpoint_elapsed, 95):.2f}s, lỗi={len(endpoint_failures)}"
        )
    if failures:
        statuses: dict[str, int] = {}
        for failure in failures:
            key = failure.error or str(failure.status_code)
            statuses[key] = statuses.get(key, 0) + 1
        print("  - Phân loại lỗi: " + ", ".join(f"{key}={value}" for key, value in statuses.items()))
    return percentile(elapsed, 95), error_rate


async def logout(client: httpx.AsyncClient) -> None:
    csrf_token = client.cookies.get("hongha_csrf")
    if not csrf_token:
        return
    try:
        await client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    except httpx.RequestError:
        pass


async def execute(args: argparse.Namespace) -> int:
    base_url = validate_base_url(args.base_url, allow_http=args.allow_http)
    username = input("Tài khoản admin dự phòng (không dùng root): ").strip()
    password = getpass.getpass("Mật khẩu (ẩn): ")
    if not username or not password:
        print("Thiếu tài khoản hoặc mật khẩu.", file=sys.stderr)
        return 2

    limits = httpx.Limits(max_connections=120, max_keepalive_connections=60)
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "HongHaDataHub-SafeLoadTest/1.0"},
    ) as client:
        login = await client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        password = ""
        if login.status_code != 200:
            print(f"Đăng nhập thất bại (HTTP {login.status_code}).", file=sys.stderr)
            return 2
        try:
            user = login.json().get("user", {})
            if user.get("role") != "admin" or user.get("is_root_admin"):
                print(
                    "Chỉ được chạy bằng admin dự phòng; không dùng nhân viên hoặc root.",
                    file=sys.stderr,
                )
                return 2

            print(f"Đã đăng nhập @{user.get('username', username)}. Không hiển thị dữ liệu đơn hàng.")
            warmup = await client.get(
                "/api/orders?page_number=1&page_size=1&include_summary=false&sort_by=recent"
            )
            if warmup.status_code != 200:
                print(
                    f"Warm-up thất bại (HTTP {warmup.status_code}); dừng kiểm thử.",
                    file=sys.stderr,
                )
                return 2

            exit_code = 0
            for index, users in enumerate(args.stages):
                results = await run_stage(client, users)
                p95, error_rate = print_stage(users, results)
                if error_rate > args.max_error_rate or p95 > args.max_p95:
                    print(
                        "DỪNG AN TOÀN: kết quả vượt ngưỡng lỗi hoặc thời gian phản hồi cho phép."
                    )
                    exit_code = 1
                    break
                if index < len(args.stages) - 1:
                    await asyncio.sleep(args.pause)
            return exit_code
        finally:
            await logout(client)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Kiểm thử tải tăng dần cho màn hình đơn hàng Hồng Hà DataHub."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--stages", type=parse_stages, default=parse_stages("5,10,20,35,50"))
    parser.add_argument("--pause", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-p95", type=float, default=10.0)
    parser.add_argument("--max-error-rate", type=float, default=0.05)
    parser.add_argument("--allow-http", action="store_true", help=argparse.SUPPRESS)
    return parser


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main() -> None:
    configure_console()
    args = build_parser().parse_args()
    print("KIỂM THỬ TẢI AN TOÀN - mỗi người tạo 2 request giống màn hình đơn hàng.")
    print(f"Đích: {args.base_url} | các mức: {args.stages}")
    confirmation = input("Gõ KIEM TRA để bắt đầu: ").strip()
    if confirmation != "KIEM TRA":
        print("Đã hủy; chưa gửi tải đến máy chủ.")
        raise SystemExit(2)
    raise SystemExit(asyncio.run(execute(args)))


if __name__ == "__main__":
    main()
