/** Wrist placement from hand landmarks + a canvas-drawn watch (case, dial, live hands, strap). */

import type { WristTryOn } from "../../lib/types";

export interface Point {
  x: number;
  y: number;
}

export interface WristPose {
  center: Point; // where the watch sits (px)
  angle: number; // canvas rotation that points 12 o'clock the right way (radians)
  pxPerMm: number;
  wristWidth: number; // px across the wrist
}

// Average adult hand breadth across the knuckles (index → pinky MCP) ≈ 80 mm; it converts pixels to mm
// so a 36 mm watch looks smaller than a 42 mm one, as in real life.
const KNUCKLE_SPAN_MM = 80;

const sub = (a: Point, b: Point) => ({ x: a.x - b.x, y: a.y - b.y });
const len = (a: Point) => Math.hypot(a.x, a.y);

/** MediaPipe hand landmarks (already in canvas pixels): 0 wrist, 5 index MCP, 9 middle MCP, 17 pinky MCP. */
export function wristPose(lm: Point[]): WristPose | null {
  const wrist = lm[0];
  const index = lm[5];
  const middle = lm[9];
  const pinky = lm[17];
  const along = sub(middle, wrist); // wrist → fingers
  const alongLen = len(along);
  const span = len(sub(index, pinky));
  if (alongLen < 8 || span < 8) return null; // hand too small / edge-on
  const u = { x: along.x / alongLen, y: along.y / alongLen };
  // A watch sits a little up the forearm from the wrist crease.
  const center = { x: wrist.x - u.x * alongLen * 0.3, y: wrist.y - u.y * alongLen * 0.3 };
  // 12 o'clock points across the wrist towards the thumb side (index knuckle).
  const across = { x: -u.y, y: u.x };
  const towardThumb = (index.x - pinky.x) * across.x + (index.y - pinky.y) * across.y;
  const d12 = towardThumb >= 0 ? across : { x: -across.x, y: -across.y };
  return {
    center,
    angle: Math.atan2(d12.x, -d12.y),
    pxPerMm: span / KNUCKLE_SPAN_MM,
    wristWidth: span * 0.78,
  };
}

/** Exponential smoothing so the watch doesn't jitter frame to frame. */
export function smooth(prev: WristPose | null, next: WristPose, k = 0.45): WristPose {
  if (!prev) return next;
  let da = next.angle - prev.angle;
  da = Math.atan2(Math.sin(da), Math.cos(da)); // shortest way round
  const mix = (a: number, b: number) => a + (b - a) * k;
  return {
    center: { x: mix(prev.center.x, next.center.x), y: mix(prev.center.y, next.center.y) },
    angle: prev.angle + da * k,
    pxPerMm: mix(prev.pxPerMm, next.pxPerMm),
    wristWidth: mix(prev.wristWidth, next.wristWidth),
  };
}

function shade(hex: string, amount: number): string {
  const n = parseInt(hex.slice(1), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) =>
    Math.max(0, Math.min(255, Math.round(amount < 0 ? v * (1 + amount) : v + (255 - v) * amount))),
  );
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

const isLight = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return 0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255) > 150;
};

/** Draws the watch in local coordinates: origin at the case centre, 12 o'clock towards −y. */
export function drawWatch(ctx: CanvasRenderingContext2D, pose: WristPose, spec: WristTryOn, now: Date) {
  const r = (spec.case_mm / 2) * pose.pxPerMm;
  const strapW = r * 1.05;
  const strapLen = pose.wristWidth * 0.55; // visible part on each side before it wraps around

  ctx.save();
  ctx.translate(pose.center.x, pose.center.y);
  ctx.rotate(pose.angle);

  // Strap: darker towards its ends, where it curves round the wrist.
  const strap = ctx.createLinearGradient(0, -strapLen - r, 0, strapLen + r);
  strap.addColorStop(0, shade(spec.strap_color, -0.45));
  strap.addColorStop(0.5, spec.strap_color);
  strap.addColorStop(1, shade(spec.strap_color, -0.45));
  ctx.fillStyle = strap;
  ctx.beginPath();
  ctx.roundRect(-strapW / 2, -r - strapLen, strapW, 2 * (r + strapLen), strapW * 0.15);
  ctx.fill();
  // Stitching.
  ctx.strokeStyle = shade(spec.strap_color, 0.35);
  ctx.globalAlpha = 0.5;
  ctx.setLineDash([r * 0.08, r * 0.08]);
  ctx.lineWidth = Math.max(1, r * 0.025);
  ctx.strokeRect(-strapW / 2 + r * 0.08, -r - strapLen + r * 0.1, strapW - r * 0.16, 2 * (r + strapLen) - r * 0.2);
  ctx.setLineDash([]);
  ctx.globalAlpha = 1;

  // Case shadow, lugs, case with a metallic sheen, crown.
  ctx.shadowColor = "rgba(0,0,0,0.35)";
  ctx.shadowBlur = r * 0.35;
  ctx.shadowOffsetY = r * 0.08;
  ctx.fillStyle = spec.case_color;
  for (const s of [-1, 1]) ctx.fillRect(-strapW * 0.42, s > 0 ? r * 0.7 : -r * 1.12, strapW * 0.84, r * 0.42);
  const metal = ctx.createLinearGradient(-r, -r, r, r);
  metal.addColorStop(0, shade(spec.case_color, 0.55));
  metal.addColorStop(0.5, spec.case_color);
  metal.addColorStop(1, shade(spec.case_color, -0.35));
  ctx.fillStyle = metal;
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowColor = "transparent";
  ctx.fillStyle = shade(spec.case_color, -0.15);
  ctx.fillRect(r * 0.95, -r * 0.12, r * 0.18, r * 0.24);

  // Dial.
  const dialR = r * 0.86;
  const dial = ctx.createRadialGradient(-dialR * 0.3, -dialR * 0.3, dialR * 0.1, 0, 0, dialR);
  dial.addColorStop(0, shade(spec.dial_color, 0.12));
  dial.addColorStop(1, shade(spec.dial_color, -0.08));
  ctx.fillStyle = dial;
  ctx.beginPath();
  ctx.arc(0, 0, dialR, 0, Math.PI * 2);
  ctx.fill();

  // Hour markers and hands in a colour that contrasts with the dial.
  const ink = isLight(spec.dial_color) ? "#1f2328" : "#f4f4f2";
  ctx.strokeStyle = ink;
  ctx.lineCap = "round";
  for (let h = 0; h < 12; h++) {
    const a = (h / 12) * Math.PI * 2;
    const major = h % 3 === 0;
    ctx.lineWidth = Math.max(1, r * (major ? 0.06 : 0.035));
    const r1 = dialR * (major ? 0.72 : 0.8);
    ctx.beginPath();
    ctx.moveTo(Math.sin(a) * r1, -Math.cos(a) * r1);
    ctx.lineTo(Math.sin(a) * dialR * 0.9, -Math.cos(a) * dialR * 0.9);
    ctx.stroke();
  }
  const sec = now.getSeconds() + now.getMilliseconds() / 1000;
  const min = now.getMinutes() + sec / 60;
  const hour = (now.getHours() % 12) + min / 60;
  const hand = (turns: number, length: number, width: number, color: string) => {
    const a = turns * Math.PI * 2;
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(1, width);
    ctx.beginPath();
    ctx.moveTo(-Math.sin(a) * dialR * 0.12, Math.cos(a) * dialR * 0.12);
    ctx.lineTo(Math.sin(a) * length, -Math.cos(a) * length);
    ctx.stroke();
  };
  hand(hour / 12, dialR * 0.5, r * 0.08, ink);
  hand(min / 60, dialR * 0.75, r * 0.055, ink);
  hand(sec / 60, dialR * 0.82, r * 0.02, "#dc2626");
  ctx.fillStyle = ink;
  ctx.beginPath();
  ctx.arc(0, 0, r * 0.06, 0, Math.PI * 2);
  ctx.fill();

  // Glass reflection.
  const glass = ctx.createLinearGradient(-dialR, -dialR, dialR * 0.2, dialR * 0.2);
  glass.addColorStop(0, "rgba(255,255,255,0.28)");
  glass.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = glass;
  ctx.beginPath();
  ctx.arc(0, 0, dialR, Math.PI * 0.95, Math.PI * 1.75);
  ctx.fill();
  ctx.restore();
}
