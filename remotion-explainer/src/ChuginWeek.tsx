import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill, continueRender, delayRender, Easing, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';

// 色(元画像に合わせる)
const BG = '#F0F2F7';
const INK = '#1F2937';
const SUB = '#4B5563';
const FOOT = '#6B7280';
const MARK = '#F7D44C';
const ARROW = '#9AA5C4';
const DASH = '#E1E4EA';

// タイムライン(30fps のコマ番号)。各要素が出る順＝見る順。全文は約170字なので8字/秒で読み切れる18秒にしている
const T = {
  pill: 6,        // 誰向けかを先に言う
  title: 12,      // フック「今週は中銀ウィーク」
  mark: 34,       // 「中銀ウィーク」に蛍光ペン
  sub: 50,        // 「この順番で見る」で、次のカードに目線を下ろす
  card1: 80,      // ① FOMC
  arrow1: 150,    // 順番を矢印で示す
  card2: 165,     // ② ECB
  arrow2: 235,
  card3: 250,     // ③ 日銀
  bar: 330,       // 結論「予想とのズレ」と「次の一手」
  word1: 350,
  word2: 362,
  foot: 380,      // 注記(中銀の意味・日本時間・出典)
  tour: 410,      // 読み切る間に、①→②→③ の順をもう一度なぞる
};
export const TOTAL = 540;

const CARDS = [
  {
    no: '①FOMC', region: 'アメリカ', head: '#2F4FC4', ink: '#2F4FC4', flag: 'us',
    date: '29日(木)', big: ['朝 3:00'], small: '議長会見 3:30〜', desc: ['アメリカの金利と', '議長の発言'],
    x: 70, at: T.card1,
  },
  {
    no: '②ECB', region: 'ヨーロッパ', head: '#1B2A6B', ink: '#1B2A6B', flag: 'eu',
    date: '29日(木)', big: ['夜 22:15'], small: '総裁会見 22:45〜', desc: ['ヨーロッパの金利と', '今後の方針'],
    x: 580, at: T.card2,
  },
  {
    no: '③日銀', region: '日本', head: '#D93030', ink: '#D93030', flag: 'jp',
    date: '30日(金)', big: ['会合が', '終わりしだい'], small: '総裁会見 15:30〜', desc: ['日本の金利と', '総裁の発言'],
    x: 1090, at: T.card3,
  },
] as const;

const ease = Easing.bezier(0.22, 1, 0.36, 1);
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const useFonts = () => {
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const faces = [new FontFace('NotoJP', `url(${staticFile('fonts/NotoSansJP.ttf')})`, {weight: '100 900'})];
    Promise.all(faces.map((f) => f.load())).then((loaded) => {
      loaded.forEach((f) => document.fonts.add(f));
      continueRender(handle);
    });
  }, [handle]);
};

// 小さな要素: 素早く入り、行き過ぎない
const useIn = (start: number, dur = 12, dy = 24) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [start, start + dur], [0, 1], {...clamp, easing: ease});
  return {opacity: p, transform: `translateY(${(1 - p) * dy}px)`};
};

// 大事な数字: 少し行き過ぎてから止まる
const usePop = (start: number) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - start, fps, config: {damping: 11, stiffness: 160}});
  return {opacity: interpolate(frame, [start, start + 4], [0, 1], clamp), transform: `scale(${0.6 + 0.4 * s})`};
};

const Flag: React.FC<{kind: string}> = ({kind}) => {
  if (kind === 'us') {
    return (
      <svg width="76" height="50" viewBox="0 0 76 50">
        <rect width="76" height="50" fill="#fff" />
        {Array.from({length: 7}).map((_, i) => (
          <rect key={i} x="0" y={(i * 100) / 13} width="76" height={50 / 13} fill="#C8102E" />
        ))}
        <rect x="0" y="0" width="34" height="27" fill="#3C3B6E" />
      </svg>
    );
  }
  if (kind === 'eu') {
    return (
      <svg width="76" height="50" viewBox="0 0 76 50">
        <rect width="76" height="50" fill="#003399" />
        {Array.from({length: 12}).map((_, i) => {
          const a = (i / 12) * Math.PI * 2;
          return <circle key={i} cx={38 + Math.cos(a) * 14} cy={25 + Math.sin(a) * 14} r="1.8" fill="#FFCC00" />;
        })}
      </svg>
    );
  }
  return (
    <svg width="76" height="50" viewBox="0 0 76 50">
      <rect width="76" height="50" fill="#fff" />
      <circle cx="38" cy="25" r="15" fill="#BC002D" />
    </svg>
  );
};

const Card: React.FC<{c: typeof CARDS[number]; i: number}> = ({c, i}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  // カードは下から上がって、行き過ぎずに止まる
  const s = spring({frame: frame - c.at, fps, config: {damping: 20, stiffness: 120}});
  const op = interpolate(frame, [c.at, c.at + 8], [0, 1], clamp);
  // 読み切る間に ①→②→③ の順で1枚ずつ少し持ち上げる
  const t0 = T.tour + i * 20;
  const lift = interpolate(frame, [t0, t0 + 8, t0 + 16, t0 + 24], [0, 1, 1, 0], clamp);
  const flag = usePop(c.at + 6);
  const date = useIn(c.at + 10);
  const big = usePop(c.at + 16);
  const small = useIn(c.at + 26);
  const line = interpolate(frame, [c.at + 28, c.at + 40], [0, 100], {...clamp, easing: ease});
  const desc = useIn(c.at + 32);
  const twoLine = c.big.length > 1;
  return (
    <div style={{
      position: 'absolute', left: c.x, top: 322, width: 440, height: 382, borderRadius: 18, overflow: 'hidden',
      background: '#fff', opacity: op,
      transform: `translateY(${(1 - s) * 60 - lift * 10}px) scale(${1 + lift * 0.025})`,
      boxShadow: `0 ${6 + lift * 14}px ${18 + lift * 24}px rgba(31,41,55,${0.08 + lift * 0.1})`,
    }}>
      <div style={{height: 98, background: c.head, display: 'flex', alignItems: 'center', padding: '0 26px', gap: 22}}>
        <div style={{...flag, display: 'flex', boxShadow: '0 0 0 1px rgba(0,0,0,.08)'}}><Flag kind={c.flag} /></div>
        <div style={{color: '#fff'}}>
          <div style={{fontSize: 42, fontWeight: 900, lineHeight: 1.05}}>{c.no}</div>
          <div style={{fontSize: 22, fontWeight: 700, marginTop: 4}}>{c.region}</div>
        </div>
      </div>
      <div style={{padding: '16px 28px 0'}}>
        <div style={{...date, fontSize: 32, fontWeight: 500, color: INK, lineHeight: 1.3}}>{c.date}</div>
        <div style={{...big, transformOrigin: 'left center', color: c.ink, fontWeight: 900,
          fontSize: twoLine ? 38 : 60, lineHeight: twoLine ? 1.15 : 1.1, marginTop: twoLine ? 2 : 0}}>
          {c.big.map((l) => <div key={l}>{l}</div>)}
        </div>
        <div style={{...small, fontSize: 22, fontWeight: 700, color: FOOT, marginTop: 4}}>{c.small}</div>
        <div style={{height: 0, borderTop: `2px dashed ${DASH}`, width: `${line}%`, margin: '10px 0 10px'}} />
        <div style={{...desc, fontSize: 26, fontWeight: 700, color: INK, lineHeight: 1.4}}>
          {c.desc.map((l) => <div key={l}>{l}</div>)}
        </div>
      </div>
    </div>
  );
};

const Arrow: React.FC<{x: number; at: number}> = ({x, at}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [at, at + 10], [0, 1], {...clamp, easing: ease});
  // 出たあとは右へ小さく押し出して「次へ」を示し続ける
  const nudge = frame > at + 10 ? Math.max(0, Math.sin((frame - at) / 6)) * 4 : 0;
  return (
    <svg width="46" height="60" viewBox="0 0 46 60" style={{
      position: 'absolute', left: x - 23, top: 485, opacity: p, transform: `translateX(${(p - 1) * 20 + nudge}px)`,
    }}>
      <path d="M0 0 L46 30 L0 60Z" fill={ARROW} />
    </svg>
  );
};

const Word: React.FC<{text: string; at: number}> = ({text, at}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - at, fps, config: {damping: 9, stiffness: 180}});
  const on = frame >= at;
  return (
    <span style={{display: 'inline-block', color: on ? MARK : '#fff', transform: `scale(${on ? 0.85 + 0.15 * s : 1})`}}>
      {text}
    </span>
  );
};

export const ChuginWeek: React.FC = () => {
  useFonts();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pill = usePop(T.pill);
  const titleP = interpolate(frame, [T.title, T.title + 18], [0, 1], {...clamp, easing: ease});
  const mark = interpolate(frame, [T.mark, T.mark + 14], [0, 100], {...clamp, easing: ease});
  const sub = useIn(T.sub, 14);
  const finger = frame > T.sub + 14 ? Math.abs(Math.sin((frame - T.sub) / 7)) * 8 : 0;
  const barS = spring({frame: frame - T.bar, fps, config: {damping: 20, stiffness: 120}});
  const barOp = interpolate(frame, [T.bar, T.bar + 8], [0, 1], clamp);
  const foot = useIn(T.foot, 14, 10);

  return (
    <AbsoluteFill style={{background: BG, fontFamily: 'NotoJP, sans-serif'}}>
      {/* 元画像の 1600x900 の座標で組み、1920x1080 に拡大する */}
      <div style={{position: 'absolute', width: 1600, height: 900, transform: 'scale(1.2)', transformOrigin: '0 0'}}>
        <div style={{position: 'absolute', top: 45, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
          <div style={{...pill, background: INK, color: '#fff', fontSize: 27, fontWeight: 700, padding: '9px 32px', borderRadius: 40}}>
            FX初心者むけ・1分でわかる
          </div>
        </div>

        <div style={{position: 'absolute', top: 112, left: 0, right: 0, textAlign: 'center', overflow: 'hidden', height: 130}}>
          <div style={{display: 'inline-block', fontSize: 92, fontWeight: 900, color: INK, letterSpacing: -2,
            transform: `translateY(${(1 - titleP) * 120}px)`}}>
            今週は
            <span style={{backgroundImage: `linear-gradient(${MARK}, ${MARK})`, backgroundRepeat: 'no-repeat',
              backgroundSize: `${mark}% 46%`, backgroundPosition: '0 92%'}}>“中銀ウィーク”</span>
          </div>
        </div>

        <div style={{...sub, position: 'absolute', top: 250, left: 0, right: 0, textAlign: 'center', fontSize: 36, fontWeight: 700, color: SUB}}>
          ドル円は この順番で見る <span style={{display: 'inline-block', transform: `translateY(${finger}px)`}}>👇</span>
        </div>

        {CARDS.map((c, i) => <Card key={c.no} c={c} i={i} />)}
        <Arrow x={545} at={T.arrow1} />
        <Arrow x={1055} at={T.arrow2} />

        <div style={{
          position: 'absolute', left: 80, right: 80, top: 728, height: 94, borderRadius: 14, background: INK,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          color: '#fff', fontSize: 36, fontWeight: 700, opacity: barOp, transform: `translateY(${(1 - barS) * 40}px)`,
        }}>
          <span>💡 見るのは「金利が変わったか」より</span>
          <Word text="「予想とのズレ」" at={T.word1} />
          <span>と</span>
          <Word text="「次の一手」" at={T.word2} />
        </div>

        <div style={{...foot, position: 'absolute', top: 846, left: 0, right: 0, textAlign: 'center', fontSize: 21, fontWeight: 500, color: FOOT, whiteSpace: 'pre'}}>
          {'中銀＝中央銀行（金利を決めるところ）   ｜   時刻はすべて日本時間   ｜   出典：FRB・ECB・日本銀行の公式日程'}
        </div>
      </div>
    </AbsoluteFill>
  );
};
