import React from 'react';
import {Composition} from 'remotion';
import {BojOutlook, TOTAL} from './BojOutlook';
import {ChuginWeek, TOTAL as CHUGIN_TOTAL} from './ChuginWeek';

export const Root: React.FC = () => (
  <>
    <Composition id="BojOutlook" component={BojOutlook} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
    <Composition id="ChuginWeek" component={ChuginWeek} durationInFrames={CHUGIN_TOTAL} fps={30} width={1920} height={1080} />
  </>
);
