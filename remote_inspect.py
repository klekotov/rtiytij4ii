import argparse
import re
import sys

import paramiko


def safe_print(text: str) -> None:
    enc = sys.stdout.encoding or "utf-8"
    print(text.encode(enc, errors="replace").decode(enc, errors="replace"))


def run_cmd(client: paramiko.SSHClient, cmd: str) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def summarize_logs(log_text: str) -> None:
    lines = [ln for ln in log_text.splitlines() if ln.strip()]
    patterns = {
        "proxy": re.compile(r"proxy|прокси", re.IGNORECASE),
        "timeout": re.compile(r"timeout|timed out|таймаут", re.IGNORECASE),
        "dns": re.compile(r"dns|resolve|hostname|name or service", re.IGNORECASE),
        "http_429": re.compile(r"\b429\b", re.IGNORECASE),
        "errors": re.compile(r"error|exception|traceback|ошиб", re.IGNORECASE),
    }
    counts = {k: 0 for k in patterns}
    matched_lines: list[str] = []

    for ln in lines:
        line_hit = False
        for key, rx in patterns.items():
            if rx.search(ln):
                counts[key] += 1
                line_hit = True
        if line_hit:
            matched_lines.append(ln)

    safe_print("Log keyword counts:")
    for k, v in counts.items():
        safe_print(f"  - {k}: {v}")

    safe_print("\nRecent relevant log lines (last 35):")
    for ln in matched_lines[-35:]:
        safe_print(ln)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect remote checker logs and proxies")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--service", default="checker227")
    parser.add_argument("--remote-dir", default="/opt/227")
    args = parser.parse_args()

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        hostname=args.host,
        username=args.user,
        password=args.password,
        look_for_keys=False,
        allow_agent=False,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
    )
    try:
        safe_print(f"Host: {args.host}")
        code, out, err = run_cmd(c, f"systemctl is-active {args.service}")
        safe_print(f"Service active: {out.strip() if out.strip() else f'code={code}'}")
        if err.strip():
            safe_print(f"service stderr: {err.strip()}")

        code, out, err = run_cmd(c, f"journalctl -u {args.service} -n 1200 --no-pager")
        if code != 0:
            safe_print(f"journalctl failed: {err or out}")
        else:
            summarize_logs(out)

        proxy_diag_cmd = f"""python3 - <<'PY'
import socket
from pathlib import Path

path = Path("{args.remote_dir}") / "proxies.txt"
if not path.exists():
    print("PROXY_FILE_MISSING")
    raise SystemExit(0)

lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip() and not ln.strip().startswith("#")]
print(f"PROXY_TOTAL={{len(lines)}}")

def parse_host_port(line: str):
    if "@" in line:
        addr, _ = line.split("@", 1)
    else:
        parts = line.split(":")
        if len(parts) >= 4:
            return parts[0], int(parts[1])
        addr = line
    host, port = addr.split(":", 1)
    return host, int(port)

ok = 0
fail = 0
fail_samples = []
for ln in lines:
    try:
        host, port = parse_host_port(ln)
        with socket.create_connection((host, port), timeout=2.5):
            ok += 1
    except Exception as e:
        fail += 1
        if len(fail_samples) < 10:
            fail_samples.append(f"{{ln}} -> {{type(e).__name__}}: {{e}}")

print(f"PROXY_TCP_OK={{ok}}")
print(f"PROXY_TCP_FAIL={{fail}}")
for s in fail_samples:
    print(f"SAMPLE_FAIL: {{s}}")
PY"""
        _, p_out, p_err = run_cmd(c, proxy_diag_cmd)
        safe_print("\nProxy connectivity diagnostics:")
        if p_out.strip():
            safe_print(p_out)
        if p_err.strip():
            safe_print("proxy diag stderr:")
            safe_print(p_err)

        proxy_http_diag_cmd = f"""python3 - <<'PY'
import urllib.request
from pathlib import Path

path = Path("{args.remote_dir}") / "proxies.txt"
if not path.exists():
    print("HTTP_PROXY_FILE_MISSING")
    raise SystemExit(0)

lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip() and not ln.strip().startswith("#")]

def normalize_proxy(line: str) -> str:
    if line.startswith("http://") or line.startswith("https://"):
        return line
    if "@" in line:
        return "http://" + line.replace("@", "@", 1)
    parts = line.split(":")
    if len(parts) >= 4:
        host, port, user, pwd = parts[0], parts[1], parts[2], ":".join(parts[3:])
        return f"http://{{user}}:{{pwd}}@{{host}}:{{port}}"
    return "http://" + line

target = "https://users.roblox.com/v1/users/1"
sample = lines[:20]
ok = 0
fail = 0
samples = []

for ln in sample:
    proxy = normalize_proxy(ln)
    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({{"http": proxy, "https": proxy}})
        )
        req = urllib.request.Request(target, headers={{"User-Agent": "Mozilla/5.0"}})
        with opener.open(req, timeout=10) as r:
            code = getattr(r, "status", None) or r.getcode()
        if 200 <= int(code) < 500:
            ok += 1
        else:
            fail += 1
            if len(samples) < 8:
                samples.append(f"{{ln}} -> bad_status: {{code}}")
    except Exception as e:
        fail += 1
        if len(samples) < 8:
            samples.append(f"{{ln}} -> {{type(e).__name__}}: {{e}}")

print(f"HTTP_TEST_TOTAL={{len(sample)}}")
print(f"HTTP_TEST_OK={{ok}}")
print(f"HTTP_TEST_FAIL={{fail}}")
for s in samples:
    print("HTTP_SAMPLE_FAIL:", s)
PY"""
        _, hp_out, hp_err = run_cmd(c, proxy_http_diag_cmd)
        safe_print("\nProxy Roblox HTTP diagnostics (sample 20):")
        if hp_out.strip():
            safe_print(hp_out)
        if hp_err.strip():
            safe_print("proxy http diag stderr:")
            safe_print(hp_err)
    finally:
        c.close()


if __name__ == "__main__":
    main()
