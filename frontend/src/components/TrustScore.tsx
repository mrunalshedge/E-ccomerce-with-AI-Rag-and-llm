import { ShieldCheck } from "lucide-react";

import { cn } from "../lib/utils";

export function trustTone(score: number): "brand" | "warn" | "danger" {
  if (score >= 90) return "brand";
  if (score >= 70) return "warn";
  return "danger";
}

const TONE_TEXT = { brand: "text-brand", warn: "text-warn", danger: "text-danger" };
const TONE_BAR = { brand: "bg-brand", warn: "bg-warn", danger: "bg-danger" };

/** Compact "shield + score" chip used on product cards. */
export function TrustChip({ score, label }: { score: number; label: string }) {
  const tone = trustTone(score);
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium", TONE_TEXT[tone])}>
      <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
      {label}
    </span>
  );
}

/** Labelled meter used on the seller details card. */
export function TrustMeter({ score, label, help }: { score: number; label: string; help: string }) {
  const tone = trustTone(score);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span className={cn("text-lg font-bold tabular", TONE_TEXT[tone])}>{Math.round(score)}/100</span>
      </div>
      <div
        className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-2"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(score)}
        aria-label={label}
      >
        <div className={cn("h-full rounded-full", TONE_BAR[tone])} style={{ width: `${score}%` }} />
      </div>
      <p className="mt-1.5 text-xs text-muted">{help}</p>
    </div>
  );
}
