"""元動画を共有リンクから取り込む。

使い方:
    python3 fetch_source.py <共有リンク> [-o 名前]

対応するリンク:
    - ギガファイル便   https://105.gigafile.nu/1107-xxxx
    - Google ドライブ  https://drive.google.com/file/d/<ID>/view?... (「リンクを知っている全員」にしておく)
    - Dropbox          https://www.dropbox.com/scl/fi/...?...&dl=0
    - そのほかの直リンク(.mp4 など)

保存先は shorts-kit/source/<名前>.mp4(git には入れない)。
保存後に ffprobe で動画かどうかを確かめ、長さ・解像度を表示する。動画でなければ消して exit 1。

YouTube の URL は受け付けない。YouTube はクラウドからのダウンロードをボット確認で止めており、
それを回避する操作はしない。チャンネルの動画は YouTube Studio(コンテンツ → ︙ → ダウンロード)で
保存し、上のどれかで共有する。
"""
import argparse, json, os, re, subprocess, sys, tempfile
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "source")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def plan(url):
    """リンクの種類を見分け、(種類, 取得に使う URL, 先に開くページ or None) を返す。"""
    u = urlparse(url)
    host = u.netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        raise SystemExit("YouTube の URL は使えません。Studio でダウンロードして、ギガファイル便・Google ドライブ・Dropbox で共有してください。")
    if host.endswith("gigafile.nu"):
        file_id = u.path.strip("/")
        if not file_id:
            raise SystemExit("ギガファイル便のリンクにファイルIDがありません: " + url)
        return "gigafile", f"{u.scheme}://{u.netloc}/download.php?file={file_id}", url
    if host in ("drive.google.com", "docs.google.com", "drive.usercontent.google.com"):
        m = re.search(r"/d/([A-Za-z0-9_-]{10,})", u.path)
        fid = m.group(1) if m else parse_qs(u.query).get("id", [None])[0]
        if not fid:
            raise SystemExit("Google ドライブのリンクからファイルIDが読めません: " + url)
        return "gdrive", f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t", None
    if host.endswith("dropbox.com"):
        q = parse_qs(u.query)
        q["dl"] = ["1"]
        return "dropbox", urlunparse(u._replace(query=urlencode(q, doseq=True))), None
    return "direct", url, None


def curl(args):
    r = subprocess.run(["curl", "-sS", "-L", "--fail", "-A", UA, "--retry", "3", "--retry-delay", "3"] + args)
    if r.returncode != 0:
        raise SystemExit(f"ダウンロードに失敗しました(curl exit {r.returncode})。リンクの期限・共有設定を確認してください。")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v:
        return None
    return {"duration": float(d["format"].get("duration", 0)), "width": v.get("width"), "height": v.get("height"),
            "audio": any(s.get("codec_type") == "audio" for s in d["streams"]), "size_mb": os.path.getsize(path) / 1e6}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("-o", "--name", help="保存名(拡張子なし)。省略時は source_<種類>")
    a = ap.parse_args()

    kind, dl_url, page = plan(a.url)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, (a.name or f"source_{kind}") + ".mp4")
    part = out + ".part"
    print(f"[{kind}] {dl_url}")
    with tempfile.TemporaryDirectory() as td:
        jar = os.path.join(td, "cookies.txt")
        extra = []
        if page:  # ギガファイル便: ページを開いて cookie を受け取り、同じ cookie と Referer で本体を取る
            curl(["-c", jar, "-o", os.devnull, page])
            extra = ["-b", jar, "-e", page]
        curl(extra + ["-o", part, dl_url])
    info = probe(part)
    if not info:
        head = open(part, "rb").read(300)
        os.remove(part)
        raise SystemExit("動画ではないファイルが返りました(共有設定が「制限付き」・期限切れ・ログインが必要な可能性)。先頭: " + repr(head[:120]))
    os.replace(part, out)
    m, s = divmod(info["duration"], 60)
    print(f"OK {out}\n  長さ {int(m)}:{s:05.2f}  {info['width']}x{info['height']}  音声 {'あり' if info['audio'] else 'なし'}  {info['size_mb']:.1f}MB")


if __name__ == "__main__":
    main()
