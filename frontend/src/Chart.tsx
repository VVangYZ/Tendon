import { useState, type MouseEvent } from "react";
import type { CalculationResult, ProfileInput } from "./types";
import { getProfile } from "./chartProfiles";
import "./chart.css";

const fmt = (value: number, digits = 2) => value.toFixed(digits);

function junctionXs(profile: ProfileInput | undefined) {
  if (!profile) return [];
  const points = profile.points;
  if (profile.mode === "xyb") return points.map(point => point.x);
  const xs = [points[0].x];
  for (let index = 1; index < points.length - 1; index++) {
    const previous = points[index - 1], current = points[index], next = points[index + 1], radius = current.value;
    const inX = current.x - previous.x, inY = current.y - previous.y, outX = next.x - current.x, outY = next.y - current.y;
    const inLength = Math.hypot(inX, inY), outLength = Math.hypot(outX, outY);
    const angle = Math.acos(Math.max(-1, Math.min(1, (inX * outX + inY * outY) / (inLength * outLength))));
    const tangent = radius > 0 ? radius * Math.tan(angle / 2) : 0;
    xs.push(current.x - inX / inLength * tangent, current.x + outX / outLength * tangent);
  }
  xs.push(points.at(-1)!.x);
  return xs;
}

export default function Chart({ result, planProfile, elevationProfile }: { result: CalculationResult; planProfile?: ProfileInput; elevationProfile?: ProfileInput }) {
  const [tip, setTip] = useState<{ i: number; x: number; y: number; leftward: boolean } | null>(null);
  const distribution = result.distribution, width = 920, rowHeight = 150, left = 88, right = 25;
  const xStart = distribution[0].x, xEnd = distribution.at(-1)!.x, plotWidth = width - left - right;
  const sx = (x: number) => left + (x - xStart) / (xEnd - xStart) * plotWidth;
  const rows: [keyof typeof distribution[number], string, string, ProfileInput | undefined][] = [
    ["plan_y", "平面 y", "m", planProfile ?? getProfile("平面线形")],
    ["elevation_y", "立面 y", "m", elevationProfile ?? getProfile("立面线形")],
    ["stress", "应力", "MPa", undefined],
    ["elongation_mm", "伸长量", "mm", undefined],
  ];
  const hover = (event: MouseEvent<SVGRectElement>) => {
    const bounds = event.currentTarget.ownerSVGElement!.getBoundingClientRect();
    const progress = Math.max(0, Math.min(1, (event.clientX - bounds.left - bounds.width * left / width) / (bounds.width * plotWidth / width)));
    const x = xStart + progress * (xEnd - xStart);
    const index = distribution.reduce((best, point, candidate) => Math.abs(point.x - x) < Math.abs(distribution[best].x - x) ? candidate : best, 0);
    const localX = event.clientX - bounds.left;
    setTip({ i: index, x: localX, y: event.clientY - bounds.top, leftward: localX > bounds.width - 210 });
  };
  return <section className="panel chart"><h2>钢束综合分布</h2><div className="chart-wrap"><svg viewBox={`0 0 ${width} ${rowHeight * 4 + 46}`} onMouseLeave={() => setTip(null)}>{rows.map(([key, title, unit, profile], rowIndex) => {
    const values = distribution.map(point => key === "elongation_mm" ? Math.max(0, point[key] as number) : point[key] as number);
    const maximum = Math.max(...values), minimum = rowIndex === 3 ? 0 : Math.min(...values);
    const low = maximum - minimum < 0.001 ? maximum - 0.001 : minimum, high = maximum;
    const top = rowIndex * rowHeight + 20, frameHeight = rowHeight - 34;
    const sy = (value: number) => top + frameHeight - (value - low) / (high - low) * frameHeight;
    const value = (point: typeof distribution[number]) => key === "elongation_mm" ? Math.max(0, point[key] as number) : point[key] as number;
    const path = distribution.map((point, index) => `${index ? "L" : "M"}${sx(point.x)},${sy(value(point))}`).join(" ");
    const nearest = (x: number) => distribution.reduce((best, point, index) => Math.abs(point.x - x) < Math.abs(distribution[best].x - x) ? index : best, 0);
    return <g key={title}><rect x={left} y={top} width={plotWidth} height={frameHeight} className="frame"/>{[.25, .5, .75].map(progress => <line key={`h${progress}`} x1={left} x2={width - right} y1={top + frameHeight * progress} y2={top + frameHeight * progress} className="gridline"/>)}{[.2, .4, .6, .8].map(progress => <line key={`v${progress}`} x1={left + plotWidth * progress} x2={left + plotWidth * progress} y1={top} y2={top + frameHeight} className="gridline"/>)}<text x="18" y={top + frameHeight / 2 - 5} className="y-title">{title}</text><text x="18" y={top + frameHeight / 2 + 10} className="y-title unit">({unit})</text><text x={left - 8} y={top + 11} textAnchor="end" className="tick">{fmt(high, key === "stress" ? 0 : 2)}</text><text x={left - 8} y={top + frameHeight - 2} textAnchor="end" className="tick">{fmt(low, key === "stress" ? 0 : 2)}</text><path d={path} className={`line line${rowIndex}`}/>{profile && junctionXs(profile).map((x, index) => { const point = distribution[nearest(x)]; return <circle key={index} cx={sx(x)} cy={sy(value(point))} r="3" className={`keypoint keypoint${rowIndex}`}/>; })}{result.balance_x !== null && <><line x1={sx(result.balance_x)} x2={sx(result.balance_x)} y1={top} y2={top + frameHeight} className="balance"/>{rowIndex === 0 && <text x={sx(result.balance_x) + 4} y={top + 13} className="red">不动点</text>}</>}<rect x={left} y={top} width={plotWidth} height={frameHeight} className="hover-zone" onMouseMove={hover}/></g>;
  })}{[0, .2, .4, .6, .8, 1].map(progress => <text key={progress} x={left + plotWidth * progress} y={rowHeight * 4 + 24} textAnchor={progress === 0 ? "start" : progress === 1 ? "end" : "middle"} className="tick">{fmt(xStart + (xEnd - xStart) * progress)}</text>)}<text x={width / 2} y={rowHeight * 4 + 40} textAnchor="middle" className="x-title">x (m)</text></svg>{tip && <div className="tooltip" style={{ left: `${tip.leftward ? tip.x - 190 : tip.x + 14}px`, top: `${Math.max(tip.y - 52, 24)}px` }}>x = {fmt(distribution[tip.i].x)} m<br/>平面 y = {fmt(distribution[tip.i].plan_y)} m<br/>立面 y = {fmt(distribution[tip.i].elevation_y)} m<br/>应力 = {fmt(distribution[tip.i].stress, 1)} MPa<br/>伸长量 = {fmt(Math.max(0, distribution[tip.i].elongation_mm))} mm</div>}</div></section>;
}
