#!/usr/bin/env python3
"""競合ショートのタイトルの型が、チャンネルをまたいで効くかを測る。

  python3 competitor_patterns.py research/competitors_2026-10-25.json
各チャンネルの中で「再生数 ÷ そのチャンネルの中央値」に直し、型あり/なしの中央値の比(倍率)を出す。
再現の判定: 8チャンネル以上で比較でき、倍率の中央値が 1.2 以上(または 0.83 以下)で、同じ向きのチャンネルが 65% 以上。
限界: タイトルだけを見ている(映像・サムネは見ていない)/古い動画ほど再生が積み上がる/相関であって因果ではない。
"""
import json,re,statistics as st,sys
D=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'research/competitors_2026-10-25.json'))
def money(t):
    vals=[]
    for m in re.finditer(r'([\d,.]+)\s*(億|万|千)?円?',t):
        num=m.group(1).replace(',','')
        try: v=float(num)
        except: continue
        u=m.group(2); after=t[m.end()-1:m.end()]
        if not (u or '円' in m.group(0)): continue
        v*= {'億':1e8,'万':1e4,'千':1e3}.get(u,1)
        vals.append(v)
    return vals
F={
 "金額あり": lambda t: bool(money(t)),
 "100万円以上": lambda t: any(v>=1e6 for v in money(t)),
 "1万円未満の金額": lambda t: any(v<1e4 for v in money(t)),
 "金額2つ(比較・変化)": lambda t: len(money(t))>=2,
 "倍": lambda t: bool(re.search(r'\d+(\.\d+)?倍',t)),
 "矢印→": lambda t: '→' in t or '⇒' in t,
 "？": lambda t: bool(re.search(r'[？?]',t)),
 "！": lambda t: bool(re.search(r'[！!]',t)),
 "結果": lambda t: '結果' in t,
 "PSA": lambda t: 'PSA' in t.upper(),
 "鑑定": lambda t: '鑑定' in t,
 "開封": lambda t: '開封' in t or 'パック' in t or '開け' in t,
 "神引き・当たり": lambda t: bool(re.search(r'神引き|当た|引いた|出た',t)),
 "N選・ランキング": lambda t: bool(re.search(r'\d+選|ランキング|TOP|トップ|第\d位',t,re.I)),
 "相場・高騰・暴落": lambda t: bool(re.search(r'相場|高騰|暴落|値上が|値下が|爆上|価格',t)),
 "時間比較(年前・当時・今)": lambda t: bool(re.search(r'年前|当時|昔|今では|今の|現在',t)),
 "本物・偽物": lambda t: bool(re.search(r'本物|偽物|偽造|フェイク',t)),
 "損・注意・NG": lambda t: bool(re.search(r'損|注意|ダメ|やめ|NG|失敗|罠|危険',t)),
 "希少(世界・唯一・枚だけ)": lambda t: bool(re.search(r'世界|唯一|\d+枚(だけ|しか)|激レア|幻',t)),
 "理由・なぜ": lambda t: bool(re.search(r'なぜ|理由|どうして|秘密|違い',t)),
 "1人称(買った・俺・僕)": lambda t: bool(re.search(r'買った|買って|俺|僕|私|自分',t)),
 "感情語(やばい・神・まさか)": lambda t: bool(re.search(r'やば|ヤバ|神|まさか|驚|衝撃|鳥肌|泣|震え|エグ|えぐ',t)),
 "ポケカ": lambda t: bool(re.search(r'ポケカ|ポケモン|ピカチュウ|リザードン',t)),
 "遊戯王": lambda t: '遊戯王' in t or 'ブルーアイズ' in t or '青眼' in t,
 "ハッシュタグ3個以上": lambda t: t.count('#')>=3,
 "20字以下(タグ除く)": lambda t: len(re.sub(r'#\S+','',t).strip())<=20,
 "30字超(タグ除く)": lambda t: len(re.sub(r'#\S+','',t).strip())>30,
}

CONTENT={
 "賭け型(オリパ・くじ・引退品・開封)": lambda t: bool(re.search(r'オリパ|くじ|引退品|ルーレット|開封|福袋|BOX|ボックス|自販機|確率機|パック',t,re.I)),
 "鑑定の返却・結果(PSA/ARS/BGS)": lambda t: bool(re.search(r'PSA|鑑定|ARS|BGS',t,re.I)),
 "相場ランキング・値動き": lambda t: bool(re.search(r'相場ランキング|値動き|初動|TOP\d+|高騰|下落|暴落|値下が',t,re.I)),
 "安く買った(円の・円で・激安・たった)": lambda t: bool(re.search(r'(\d[\d,]*円の|激安|たった|\d[\d,]*円で|円分)',t)),
 "トラブル・悲報・偽物": lambda t: bool(re.search(r'偽|詐欺|悲報|許せ|炎上|サ終|ぐちゃ|被害|最悪|怒',t)),
 "意外な結果(まさか・衝撃・！？)": lambda t: bool(re.search(r'まさか|衝撃|！？|!\?|！\?|!？|あれが|あの|やつが',t)),
 "低い結果・失敗(PSA5・瞬殺)": lambda t: bool(re.search(r'PSA[1-8](?!\d)|瞬殺|敗れ|失敗|ハズレ|爆死|外れ',t,re.I)),
 "知識・解説(解説・現在・かかる)": lambda t: bool(re.search(r'解説|の現在|かかる|違い|とは|理由|方法|見分け',t)),
 "連載(part・日目・編)": lambda t: bool(re.search(r'part|日目|\d/\d|編】|編$|シリーズ|第\d+',t,re.I)),
}

def analyse(min_n=20):
    res={}
    for f,fn in F.items():
        lifts=[];chs=[]
        for ch,v in D.items():
            if ch=='tt': continue
            rows=[r for r in v['shorts'] if r['views']>0]
            if len(rows)<min_n: continue
            med=st.median(r['views'] for r in rows)
            a=[r['views']/med for r in rows if fn(r['title'])]
            b=[r['views']/med for r in rows if not fn(r['title'])]
            if len(a)>=3 and len(b)>=3:
                lifts.append(st.median(a)/st.median(b)); chs.append(ch)
        if lifts:
            up=sum(l>1 for l in lifts)/len(lifts)
            res[f]=(len(lifts),st.median(lifts),up)
    return res
if __name__=='__main__':
    r=analyse(); F.update(CONTENT); r=analyse()
    n_ch=sum(1 for k,v in D.items() if k!='tt' and len([x for x in v['shorts'] if x['views']>0])>=20)
    print('channels used',n_ch,' shorts',sum(len(v['shorts']) for k,v in D.items() if k!='tt'))
    for f,(n,l,up) in sorted(r.items(),key=lambda x:-x[1][1]):
        tag=''
        if n>=8 and l>=1.2 and up>=0.65: tag='◎再現'
        elif n>=8 and l<=1/1.2 and up<=0.35: tag='×再現(逆効果)'
        print(f"{f:<22} ch={n:>2} 倍率中央値={l:4.2f} 上がったch={up*100:3.0f}% {tag}")
