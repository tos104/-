import React from 'react';
import {Composition} from 'remotion';
import {BojOutlook, TOTAL} from './BojOutlook';

export const Root: React.FC = () => (
  <Composition id="BojOutlook" component={BojOutlook} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
);
