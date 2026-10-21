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
import re, urllib.parse, socket
from pathlib import Path

path = Path("{args.remote_dir}") / "proxies.txt"
if not path.exists():
    print("PROXY_FILE_MISSING")
    raise SystemExit(0)

lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip() and not ln.strip().startswith("#")]
print(f"PROXY_TOTAL={{len(lines)}}")

_VALID_SCHEMES = {{"http","https","socks5","socks5h","socks4","socks4a"}}
def _is_valid_port(p):
    return p.isdigit() and 1 <= int(p) <= 65535
def _is_hostport(s):
    if ":" not in s: return False
    if s.startswith("["):
        end=s.find("]")
        if end==-1: return False
        return _is_valid_port(s.rsplit(":",1)[-1])
    if " " in s or "/" in s or "@" in s: return False
    h, p = s.rsplit(":",1)
    return bool(h) and _is_valid_port(p)
def _is_creds(s):
    if ":" not in s: return False
    if _is_hostport(s): return False
    u,_=s.split(":",1)
    return bool(u) and " " not in u and "@" not in u
def _hp_split(s):
    return s.rsplit(":",1)
def _build(scheme, host, port, user=None, pwd=None):
    host=host.strip(); port=port.strip()
    hf=f"[{{host}}]" if ":" in host and not host.startswith("[") else host
    if user is not None:
        uq=urllib.parse.quote(user, safe=""); pq=urllib.parse.quote(pwd or "", safe="")
        return f"{{scheme}}://{{uq}}:{{pq}}@{{hf}}:{{port}}" if pwd else f"{{scheme}}://{{uq}}@{{hf}}:{{port}}"
    return f"{{scheme}}://{{hf}}:{{port}}"
def parse_proxy_line(raw):
    orig=raw.strip()
    if not orig or orig.startswith("#"): return None
    scheme="http"; line=orig
    if "://" in line:
        sp, rest=line.split("://",1)
        if sp.lower() in _VALID_SCHEMES:
            scheme=sp.lower(); line=rest
        else:
            line=rest
        line=line.strip().lstrip("/")
    line=re.sub(r"\\s+","",line).rstrip("/")
    if not line: return None
    if "@" in line:
        parts=line.split("@")
        for i in range(1,len(parts)):
            l="@".join(parts[:i]).strip(); r="@".join(parts[i:]).strip()
            if _is_hostport(l) and _is_creds(r):
                h,p=_hp_split(l); u,pw=r.split(":",1); return _build(scheme,h,p,u,pw)
            if _is_creds(l) and _is_hostport(r):
                u,pw=l.split(":",1); h,p=_hp_split(r); return _build(scheme,h,p,u,pw)
        return None
    else:
        if _is_hostport(line) and line.count(":")==1:
            h,p=_hp_split(line); return _build(scheme,h,p)
        parts=line.split(":")
        if len(parts)>=4:
            ha,pa=parts[0].strip(),parts[1].strip()
            if ha and _is_valid_port(pa):
                return _build(scheme,ha,pa,parts[2].strip(),":".join(parts[3:]))
            hb,pb=parts[-2].strip(),parts[-1].strip()
            if hb and _is_valid_port(pb):
                if len(parts)==4:
                    return _build(scheme,hb,pb,parts[0].strip(),parts[1].strip())
                else:
                    return _build(scheme,hb,pb,parts[0].strip(),":".join(parts[1:-2]))
        return None

def parse_host_port(line: str):
    url = parse_proxy_line(line)
    if not url:
        raise ValueError(f"unparseable: {{line}}")
    rest = url.split("://",1)[1]
    if "@" in rest:
        rest = rest.rsplit("@",1)[1]
    if rest.startswith("["):
        end = rest.find("]")
        host = rest[1:end]
        port = rest[end+2:]
    else:
        host, port = rest.rsplit(":",1)
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
    import urllib.parse, re
    orig = line.strip()
    scheme = "http"
    if "://" in orig:
        sp, rest = orig.split("://", 1)
        if sp.lower() in ("http","https","socks5","socks5h","socks4","socks4a"):
            scheme = sp.lower()
            orig = rest
        else:
            orig = rest
        orig = orig.strip().lstrip("/")
    orig = re.sub(r"\\s+", "", orig).rstrip("/")
    try:
        _VALID = {"http","https","socks5","socks5h","socks4","socks4a"}
        def _is_valid_port(pr): return pr.isdigit() and 1 <= int(pr) <= 65535
        def _is_hostport(s):
            if ":" not in s: return False
            if s.startswith("["):
                return _is_valid_port(s.rsplit(":",1)[-1])
            if " " in s or "/" in s or "@" in s: return False
            h, pr = s.rsplit(":",1)
            return bool(h) and _is_valid_port(pr)
        def _is_creds(s):
            if ":" not in s: return False
            if _is_hostport(s): return False
            u,_=s.split(":",1)
            return bool(u) and " " not in u and "@" not in u
        if "@" in orig:
            parts = orig.split("@")
            for j in range(1,len(parts)):
                l="@".join(parts[:j]).strip(); r="@".join(parts[j:]).strip()
                if _is_hostport(l) and _is_creds(r):
                    h, pr=l.rsplit(":",1); u,pw=r.split(":",1)
                    return scheme + "://" + urllib.parse.quote(u, safe="") + ":" + urllib.parse.quote(pw, safe="") + "@" + h + ":" + pr
                if _is_creds(l) and _is_hostport(r):
                    u,pw=l.split(":",1); h,pr=r.rsplit(":",1)
                    return scheme + "://" + urllib.parse.quote(u, safe="") + ":" + urllib.parse.quote(pw, safe="") + "@" + h + ":" + pr
        else:
            if _is_hostport(orig) and orig.count(":")==1:
                h,pr=orig.rsplit(":",1)
                return scheme + "://" + h + ":" + pr
            parts=orig.split(":")
            if len(parts)>=4:
                ha,pa=parts[0].strip(),parts[1].strip()
                if ha and _is_valid_port(pa):
                    return scheme + "://" + urllib.parse.quote(parts[2].strip(), safe="") + ":" + urllib.parse.quote(":".join(parts[3:]), safe="") + "@" + ha + ":" + pa
                hb,pb=parts[-2].strip(),parts[-1].strip()
                if hb and _is_valid_port(pb):
                    if len(parts)==4:
                        return scheme + "://" + urllib.parse.quote(parts[0].strip(), safe="") + ":" + urllib.parse.quote(parts[1].strip(), safe="") + "@" + hb + ":" + pb
                    else:
                        return scheme + "://" + urllib.parse.quote(parts[0].strip(), safe="") + ":" + urllib.parse.quote(":".join(parts[1:-2]), safe="") + "@" + hb + ":" + pb
    except Exception:
        pass
    parts = orig.split(":")
    if len(parts) >= 4:
        host, port, user, pwd = parts[0], parts[1], parts[2], ":".join(parts[3:])
        return scheme + "://" + urllib.parse.quote(user, safe="") + ":" + urllib.parse.quote(pwd, safe="") + "@" + host + ":" + port
    return scheme + "://" + orig

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
