import { Star } from "lucide-react";
import { useState } from "react";

import { useI18n } from "../../i18n/I18nProvider";
import { cn } from "../../lib/utils";

/** Read-only stars; supports fractions (4.3 fills 4 stars and 30% of the fifth). */
export function Stars({ value, size = "sm" }: { value: number; size?: "sm" | "md" | "lg" }) {
  const { t } = useI18n();
  const px = { sm: "h-3.5 w-3.5", md: "h-4 w-4", lg: "h-6 w-6" }[size];
  return (
    <span className="inline-flex items-center" role="img" aria-label={t("stars_label", { n: value })}>
      {[1, 2, 3, 4, 5].map((i) => {
        const fill = Math.max(0, Math.min(1, value - (i - 1)));
        return (
          <span key={i} className={cn("relative", px)}>
            <Star className={cn("absolute inset-0 text-line", px)} fill="currentColor" strokeWidth={0} aria-hidden />
            <span className="absolute inset-0 overflow-hidden" style={{ width: `${fill * 100}%` }}>
              <Star className={cn("text-amber-500", px)} fill="currentColor" strokeWidth={0} aria-hidden />
            </span>
          </span>
        );
      })}
    </span>
  );
}

/** "★ 4.2 (5)" chip for product cards. */
export function RatingChip({ average, count }: { average: number | null; count: number }) {
  if (!count || average === null) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium">
      <Star className="h-3.5 w-3.5 text-amber-500" fill="currentColor" strokeWidth={0} aria-hidden />
      <span className="tabular">{average.toFixed(1)}</span>
      <span className="text-muted">({count})</span>
    </span>
  );
}

/** Accessible 1–5 star picker (a radio group: arrow keys work). */
export function StarInput({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  const { t } = useI18n();
  const [hover, setHover] = useState(0);
  const shown = hover || value;
  return (
    <div className="flex gap-1" role="radiogroup" aria-label={t("your_rating")} onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <label key={n} className="cursor-pointer" onMouseEnter={() => setHover(n)}>
          <input type="radio" name="rating" value={n} checked={value === n} onChange={() => onChange(n)} className="peer sr-only" aria-label={t("rate_n", { n })} />
          <Star
            className={cn(
              "h-8 w-8 rounded transition peer-focus-visible:outline-2 peer-focus-visible:outline-brand",
              n <= shown ? "text-amber-500" : "text-line",
            )}
            fill="currentColor"
            strokeWidth={0}
            aria-hidden
          />
        </label>
      ))}
    </div>
  );
}
