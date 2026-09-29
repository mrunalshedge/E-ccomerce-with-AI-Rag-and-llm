/** Fit maths for the 3D fit visualiser: a simple parametric body from the shopper's measurements and
 *  a garment built from one row of the seller's size chart (all circumferences in cm, full round).
 *  It is a guide, not a simulation: cloth is treated as a rigid shell around the body. */

import type { SizeChartRow } from "../../lib/types";

export type BodyShape = "female" | "male";

export interface Body {
  shape: BodyShape;
  height: number;
  chest: number; // bust for the female shape
  waist: number;
  hip: number;
}

export const DEFAULT_BODIES: Record<BodyShape, Body> = {
  female: { shape: "female", height: 160, chest: 86, waist: 72, hip: 96 },
  male: { shape: "male", height: 172, chest: 94, waist: 82, hip: 96 },
};

export const BODY_LIMITS = {
  height: [120, 210],
  chest: [60, 160],
  waist: [50, 160],
  hip: [60, 170],
} as const;

/** Heights of body landmarks as fractions of total height (standing, feet at 0). */
const LANDMARKS: Record<BodyShape, { crotch: number; hip: number; waist: number; chest: number; shoulder: number; neck: number }> = {
  female: { crotch: 0.47, hip: 0.51, waist: 0.615, chest: 0.715, shoulder: 0.815, neck: 0.84 },
  male: { crotch: 0.47, hip: 0.51, waist: 0.6, chest: 0.72, shoulder: 0.82, neck: 0.845 },
};

export interface Ring {
  y: number; // height above the floor (cm)
  circ: number; // circumference (cm)
}

export function landmarks(body: Body) {
  const f = LANDMARKS[body.shape];
  const h = body.height;
  return {
    crotch: f.crotch * h,
    hip: f.hip * h,
    waist: f.waist * h,
    chest: f.chest * h,
    shoulder: f.shoulder * h,
    neck: f.neck * h,
    armLength: (body.shape === "male" ? 0.44 : 0.43) * h, // shoulder to wrist
  };
}

/** Torso outline from crotch to neck, bottom to top. */
export function torsoProfile(body: Body): Ring[] {
  const y = landmarks(body);
  return [
    { y: y.crotch - 2, circ: body.hip * 0.85 },
    { y: y.hip, circ: body.hip },
    { y: y.waist, circ: body.waist },
    { y: y.chest, circ: body.chest },
    { y: y.shoulder - 3, circ: body.chest * 0.97 },
    { y: y.shoulder + 1, circ: body.chest * 0.62 },
    { y: y.neck, circ: body.chest * 0.4 },
  ];
}

/** Linear interpolation of a profile (sorted by y) at height ``y``. */
export function circAt(profile: Ring[], y: number): number {
  if (y <= profile[0].y) return profile[0].circ;
  for (let i = 1; i < profile.length; i++) {
    const a = profile[i - 1];
    const b = profile[i];
    if (y <= b.y) return a.circ + ((b.circ - a.circ) * (y - a.y)) / (b.y - a.y);
  }
  return profile[profile.length - 1].circ;
}

export type EaseLevel = "tight" | "snug" | "comfortable" | "loose";

/** Room between garment and body (cm) → how it will feel. */
export function easeLevel(ease: number): EaseLevel {
  if (ease < 0) return "tight";
  if (ease < 4) return "snug";
  if (ease <= 16) return "comfortable";
  return "loose";
}

export interface Garment {
  rings: (Ring & { ease: number })[]; // from the bottom hem up to the shoulder line
  top: number;
  bottom: number;
  sleeve: number | null; // sleeve length from the shoulder (cm), null = sleeveless
}

/** A kurta/jacket-style shell from one size-chart row. Unknown measurements fall back sensibly:
 *  waist → chest, hip → the larger of chest and waist (a straight or A-line cut). */
export function buildGarment(body: Body, row: SizeChartRow, samples = 40): Garment {
  const y = landmarks(body);
  const chest = row.chest ?? body.chest + 8;
  const waist = row.waist ?? chest;
  const hip = row.hip ?? Math.max(chest, waist);
  const top = y.shoulder + 1;
  const length = row.length ?? top - y.crotch + 10;
  const bottom = Math.max(top - length, body.height * 0.05);

  const garmentProfile: Ring[] = [
    { y: Math.min(bottom, y.crotch - 30), circ: hip * 1.08 }, // gentle flare below the hips
    { y: y.hip, circ: hip },
    { y: y.waist, circ: waist },
    { y: y.chest, circ: chest },
    { y: y.shoulder - 3, circ: chest * 0.97 },
    { y: top, circ: body.chest * 0.62 + 4 },
  ].sort((a, b) => a.y - b.y);
  const bodyProfile = torsoProfile(body);

  const rings = Array.from({ length: samples + 1 }, (_, i) => {
    const ry = bottom + ((top - bottom) * i) / samples;
    const g = circAt(garmentProfile, ry);
    const b = ry < y.crotch ? body.hip * 0.85 : circAt(bodyProfile, ry);
    // Above the chest the shell only drapes to the shoulders, so show the chest's fit there; below
    // the hips it hangs free over the legs, so show the hip's fit there.
    const ease = ry > y.chest ? chest - body.chest : ry < y.hip ? hip - body.hip : g - b;
    return { y: ry, circ: Math.max(g, b + 1.5), ease }; // never drawn inside the body
  });
  return { rings, top, bottom, sleeve: row.sleeve ?? null };
}

export interface FitReport {
  areas: { key: "chest" | "waist" | "hip"; ease: number; level: EaseLevel; estimated: boolean }[];
  length: "hips" | "thigh" | "knee" | "calf";
  sleeve: "short" | "forearm" | "wrist" | "long" | null;
}

/** Plain-language summary: room at chest/waist/hip (only where the chart has the measurement),
 *  where the hem ends and where the sleeves end. */
export function fitReport(body: Body, row: SizeChartRow, garment: Garment): FitReport {
  const y = landmarks(body);
  const chest = row.chest ?? body.chest + 8;
  const waist = row.waist ?? chest;
  // Same fallbacks as buildGarment, flagged as estimates so the text matches the colours.
  const garmentGirth = { chest, waist, hip: row.hip ?? Math.max(chest, waist) };
  const areas = (["chest", "waist", "hip"] as const)
    // Estimate the hip only when the hem reaches below the hip line (a short jacket never touches it).
    .filter((key) => row[key] !== undefined || (key === "hip" && garment.bottom < y.hip))
    .map((key) => {
      const ease = Math.round(garmentGirth[key] - body[key]);
      return { key, ease, level: easeLevel(ease), estimated: row[key] === undefined };
    });
  const hem = garment.bottom / body.height;
  const length = hem > 0.45 ? "hips" : hem > 0.36 ? "thigh" : hem > 0.26 ? "knee" : "calf";
  let sleeve: FitReport["sleeve"] = null;
  if (garment.sleeve !== null) {
    const r = garment.sleeve / y.armLength;
    sleeve = r < 0.45 ? "short" : r < 0.85 ? "forearm" : r <= 1.05 ? "wrist" : "long";
  }
  return { areas, length, sleeve };
}

/** Minimum comfortable room per girth, the same rule as the server's size advice (size_service.EASE_CM). */
const MIN_EASE = { chest: 6, waist: 4, hip: 6 } as const;

/** Smallest size with enough room everywhere the chart has a girth; the largest if none is enough. */
export function suggestSize(chart: SizeChartRow[], body: Body): string {
  const fits = (row: SizeChartRow) =>
    (["chest", "waist", "hip"] as const).every((m) => row[m] === undefined || (row[m] as number) - body[m] >= MIN_EASE[m]);
  return (chart.find(fits) ?? chart[chart.length - 1]).size;
}
