#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google One 学生认证 —— 纯 HTTP 执行器
基于 PastKing/tgbot-verify 的 one/ 模块（programId 与本项目完全一致），
补三处它缺的东西：

  1. 传输层换成 curl_cffi + impersonate=chrome  → Chrome 的 TLS/JA3 指纹，不再是 httpx
  2. 补齐 Origin / Referer / UA / Accept-Language → 原版只发 Content-Type，一眼机器
  3. 支持住宅代理

用法：
  python run_one.py --vid <24位verificationId> --school 660 \
      --first ALEX --last MORGAN --dob 2004-03-14 \
      --email alex.morgan@student.csn.edu \
      --doc out/transcript_small.jpg \
      [--proxy http://user:pass@host:port]
"""
import argparse
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "_ref", "sheerid_alt", "b"))
sys.path.insert(0, REPO)

from curl_cffi import requests as creq          # noqa: E402
import one.sheerid_verifier as SV               # noqa: E402
from one import config as OCFG                  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

DEFAULT_SCHOOL = {
    "660": {
        "id": 660, "idExtended": "660",
        "name": "College of Southern Nevada",
        "city": "Las Vegas", "state": "NV", "country": "US",
        "type": "UNIVERSITY", "domain": "CSN.EDU",
        "latitude": 36.158115, "longitude": -115.2331,
    }
}


class _Resp:
    def __init__(self, r):
        self._r = r
        self.status_code = r.status_code
        self.text = r.text

    def json(self):
        return self._r.json()


class ChromeClient:
    """冒充 Chrome 的 HTTP 客户端，接口对齐 httpx.Client 中本流程用到的部分"""

    def __init__(self, proxy=None, referer=None):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        self.s = creq.Session(impersonate="chrome", proxies=proxies, timeout=40)
        self.referer = referer
        self.s.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://services.sheerid.com",
            "User-Agent": UA,
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        })
        if referer:
            self.s.headers["Referer"] = referer

    def request(self, method, url, json=None, headers=None):
        return _Resp(self.s.request(method, url, json=json, headers=headers))

    def put(self, url, content=None, headers=None, timeout=None):
        h = {"Origin": "https://services.sheerid.com"}
        h.update(headers or {})
        return _Resp(self.s.put(url, data=content, headers=h))

    def close(self):
        self.s.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vid", required=True, help="24 位 verificationId")
    ap.add_argument("--school", default="660")
    ap.add_argument("--first", default="ALEX")
    ap.add_argument("--last", default="MORGAN")
    ap.add_argument("--dob", default="2004-03-14")
    ap.add_argument("--email", default="alex.morgan@student.csn.edu")
    ap.add_argument("--doc", default=os.path.join(HERE, "out", "transcript_small.jpg"))
    ap.add_argument("--proxy", default="")
    ap.add_argument("--dry", action="store_true", help="只打印计划，不发任何请求")
    a = ap.parse_args()

    doc_path = a.doc if os.path.isabs(a.doc) else os.path.join(HERE, a.doc)
    if not os.path.exists(doc_path):
        sys.exit(f"材料不存在: {doc_path}")
    data = open(doc_path, "rb").read()
    if len(data) > 1024 * 1024:
        sys.exit(f"材料 {len(data)/1024:.0f}KB 超过 1MB 上限，先跑 compress.py")
    ext = os.path.splitext(doc_path)[1].lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "pdf": "application/pdf"}[ext]
    fname = "enrollment_verification." + ("jpg" if ext in ("jpg", "jpeg") else ext)

    OCFG.PROGRAM_ID = "67c8c14f5f17a83b745e3f82"
    OCFG.SCHOOLS.update(DEFAULT_SCHOOL)
    OCFG.DEFAULT_SCHOOL_ID = a.school

    referer = (f"https://services.sheerid.com/verify/{OCFG.PROGRAM_ID}/"
               f"?verificationId={a.vid}")

    print(f"""
  验证 ID   {a.vid}
  学校      {DEFAULT_SCHOOL[a.school]['name']}  (id {a.school})
  姓名      {a.first} {a.last}
  生日      {a.dob}
  邮箱      {a.email}
  材料      {os.path.basename(doc_path)}  {len(data)/1024:.0f}KB  {mime}
  代理      {a.proxy or '直连'}
  传输层    curl_cffi / chrome TLS
""")
    if a.dry:
        return

    v = SV.SheerIDVerifier(a.vid)
    v.http_client.close()
    v.http_client = ChromeClient(a.proxy or None, referer)

    # 用我们自己的材料替换它内置的学生证生成器
    SV.generate_image = lambda *args, **kwargs: data

    # 修正 docUpload 声明的文件名/MIME/大小
    _orig = v._sheerid_request

    def _patched(method, url, body=None):
        if url.endswith("/step/docUpload") and isinstance(body, dict) and body.get("files"):
            body["files"][0].update({"fileName": fname, "mimeType": mime, "fileSize": len(data)})
        return _orig(method, url, body)

    v._sheerid_request = _patched
    v._upload_to_s3 = lambda upload_url, blob: (
        lambda r: 200 <= r.status_code < 300
    )(v.http_client.put(upload_url, content=blob, headers={"Content-Type": mime}))

    result = v.verify(
        first_name=a.first, last_name=a.last,
        email=a.email, birth_date=a.dob, school_id=a.school,
    )
    print("\n" + "=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)[:1500])
    print("=" * 60)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
