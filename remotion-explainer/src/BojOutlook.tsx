import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill, continueRender, delayRender, Easing, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';

// 色(元スライドに合わせる)
const BG = '#F8F5EE';
const INK = '#2F3437';
const GREEN = '#3E7A63';
const CHIP = '#E3EEE8';
const LINE = '#E2DDD3';
const SUB = '#8A8F8C';
const MARK = '#F6D96B';

// タイムライン(30fps のコマ番号)。文の長さ÷8字/秒+余裕で読み切れる長さにしている
const T = {
  title: 0,       // 見出しが入る
  card1: 30,      // ① 定義
  card2: 170,     // ② 具体例
  card3: 360,     // ③ 読み方
  mark: 400,      // 「前回との差」にマーカー
  all: 550,       // 3つとも明るく戻して締め
};
export const TOTAL = 620;

const STEPS = [
  {
    no: '1', label: '定義', at: T.card1,
    lines: ['日銀が年4回（1・4・7・10月）出す「この先の物価と景気の見通し」です。'],
    term: '用語　見通し＝日銀による先の予想のこと',
  },
  {
    no: '2', label: '具体例', at: T.card2,
    lines: ['物価の見通しが前回より上に変わる →「利上げが続きやすい」', 'と市場が考える → 円が買われる場合があります。'],
    term: '用語　利上げ＝政策金利を引き上げること',
  },
  {
    no: '3', label: '読み方', at: T.card3,
    lines: ['数字そのものより「前回との差」を見ます。', '同じ内容でも、市場の受け止め方で円の動きは変わります。'],
    term: '用語　上方修正＝見通しを上に直すこと',
  },
];

const ease = Easing.bezier(0.22, 1, 0.36, 1);

const useFonts = () => {
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const faces = [
      new FontFace('Rounded', `url(${staticFile('fonts/MPLUSRounded1c-Black.ttf')})`),
      new FontFace('NotoJP', `url(${staticFile('fonts/NotoSansJP.ttf')})`, {weight: '100 900'}),
    ];
    Promise.all(faces.map((f) => f.load())).then((loaded) => {
      loaded.forEach((f) => document.fonts.add(f));
      continueRender(handle);
    });
  }, [handle]);
};

// 「前回との差」だけ蛍光ペンを左から引く
const Marked: React.FC<{text: string; start: number}> = ({text, start}) => {
  const frame = useCurrentFrame();
  const key = '「前回との差」';
  const i = text.indexOf(key);
  if (i < 0) return <>{text}</>;
  const w = interpolate(frame, [start, start + 14], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
  return (
    <>
      {text.slice(0, i)}
      <span style={{backgroundImage: `linear-gradient(${MARK}, ${MARK})`, backgroundRepeat: 'no-repeat',
        backgroundSize: `${w}% 38%`, backgroundPosition: '0 88%'}}>{key}</span>
      {text.slice(i + key.length)}
    </>
  );
};

const Card: React.FC<{step: typeof STEPS[number]; index: number; next?: number}> = ({step, index, next}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  // カードは下から上がって、行き過ぎずに止まる
  const p = spring({frame: frame - step.at, fps, config: {damping: 200, stiffness: 120}, durationInFrames: 20});
  const y = interpolate(p, [0, 1], [48, 0]);
  // 番号は少しだけ弾む(主役なので、ここだけ行き過ぎを許す)
  const n = spring({frame: frame - step.at - 4, fps, config: {damping: 11, stiffness: 160}});
  const chip = interpolate(frame, [step.at + 16, step.at + 28], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
  // 次のステップが出たら控えめにし、最後に全部戻す
  const dim = next === undefined ? 1 : interpolate(frame, [next, next + 12, T.all, T.all + 15], [1, 0.45, 0.45, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const top = 250 + index * 272;
  return (
    <div style={{position: 'absolute', left: 92, top, width: 1738, height: 250, opacity: p * dim,
      transform: `translateY(${y}px)`, background: '#fff', border: `2px solid ${LINE}`, borderRadius: 20}}>
      <div style={{position: 'absolute', left: 38, top: 38, width: 102, height: 102, borderRadius: 51, background: GREEN,
        color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Rounded', fontSize: 56,
        transform: `scale(${n})`}}>{step.no}</div>
      <div style={{position: 'absolute', left: 0, width: 178, top: 165, textAlign: 'center', fontFamily: 'Rounded',
        fontSize: 38, color: GREEN}}>{step.label}</div>
      <div style={{position: 'absolute', left: 210, top: 38, fontFamily: 'NotoJP', fontWeight: 700, fontSize: 40,
        lineHeight: 1.55, color: INK, letterSpacing: '0.02em'}}>
        {step.lines.map((l, k) => (
          <div key={k} style={{opacity: interpolate(frame, [step.at + 6 + k * 6, step.at + 18 + k * 6], [0, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
            <Marked text={l} start={T.mark} />
          </div>
        ))}
      </div>
      <div style={{position: 'absolute', left: 208, top: 178, padding: '6px 22px', borderRadius: 8, background: CHIP,
        fontFamily: 'NotoJP', fontWeight: 500, fontSize: 30, color: GREEN, opacity: chip,
        transform: `translateX(${interpolate(chip, [0, 1], [-12, 0])}px)`}}>{step.term}</div>
    </div>
  );
};

const Arrow: React.FC<{at: number; index: number}> = ({at, index}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [at - 8, at + 4], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <div style={{position: 'absolute', left: 950, top: 502 + index * 272, width: 0, height: 0, opacity: o,
    borderLeft: '20px solid transparent', borderRight: '20px solid transparent', borderTop: `16px solid ${GREEN}`}} />;
};

export const BojOutlook: React.FC = () => {
  useFonts();
  const frame = useCurrentFrame();
  const t = (a: number, b: number) => interpolate(frame, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', left: 92, top: 70, fontFamily: 'Rounded', fontSize: 36, color: GREEN,
        opacity: t(0, 12)}}>やさしい教科書</div>
      <div style={{position: 'absolute', left: 92, top: 118, fontFamily: 'Rounded', fontSize: 72, color: INK,
        letterSpacing: '-0.01em', opacity: t(4, 20), transform: `translateY(${interpolate(t(4, 20), [0, 1], [24, 0])}px)`}}>
        日銀の「展望レポート」を3ステップで
      </div>
      <div style={{position: 'absolute', right: 92, top: 138, fontFamily: 'NotoJP', fontWeight: 700, fontSize: 34,
        color: SUB, opacity: t(14, 28)}}>10月30日（金）日銀会合</div>
      <div style={{position: 'absolute', left: 92, top: 212, height: 3, background: LINE, width: 1738 * t(10, 34)}} />
      {STEPS.map((s, i) => <Card key={i} step={s} index={i} next={STEPS[i + 1]?.at} />)}
      <Arrow at={T.card2} index={0} />
      <Arrow at={T.card3} index={1} />
    </AbsoluteFill>
  );
};
