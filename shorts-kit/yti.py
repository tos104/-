import json, sys, urllib.request, base64
API="https://youtubei.googleapis.com/youtubei/v1/"
CTX={"client":{"clientName":"WEB","clientVersion":"2.20260918.00.00","hl":"ja","gl":"JP"}}
def call(ep, body):
    body=dict(body); body["context"]=CTX
    r=urllib.request.Request(API+ep+"?prettyPrint=false", json.dumps(body).encode(), {"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(r, timeout=30))
def walk(o, key):
    if isinstance(o, dict):
        for k,v in o.items():
            if k==key: yield v
            yield from walk(v, key)
    elif isinstance(o, list):
        for v in o: yield from walk(v, key)
def resolve(url):
    d=call("navigation/resolve_url",{"url":url})
    return next(walk(d,"browseEndpoint"))["browseId"]
def txt(x):
    if not x: return ""
    if "simpleText" in x: return x["simpleText"]
    if "content" in x: return x["content"]
    return "".join(r.get("text","") for r in x.get("runs",[]))
def shorts(bid, pages=6):
    d=call("browse",{"browseId":bid,"params":"EgZzaG9ydHPyBgUKA5oBAA%3D%3D"}); out=[]
    for _ in range(pages):
        for s in walk(d,"shortsLockupViewModel"):
            om=s.get("overlayMetadata",{})
            vid=s.get("onTap",{}).get("innertubeCommand",{}).get("reelWatchEndpoint",{}).get("videoId")
            out.append((vid, om.get("primaryText",{}).get("content"), om.get("secondaryText",{}).get("content")))
        tok=[c["continuationCommand"]["token"] for c in walk(d,"continuationEndpoint") if "continuationCommand" in c]
        if not tok: break
        d=call("browse",{"continuation":tok[-1]})
    return out
def views(s):
    s=(s or "").replace("回視聴","").replace(",","").strip()
    m=1
    if s.endswith("万"): m=1e4; s=s[:-1]
    elif s.endswith("億"): m=1e8; s=s[:-1]
    try: return float(s)*m
    except: return 0
