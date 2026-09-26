import { Minus, Plus } from "lucide-react";

export function QuantityStepper({
  value,
  min = 1,
  max,
  onChange,
  disabled,
  label,
}: {
  value: number;
  min?: number;
  max: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  label: string;
}) {
  const btn =
    "flex h-9 w-9 items-center justify-center rounded-lg text-fg transition hover:bg-surface-2 disabled:opacity-40 disabled:hover:bg-transparent";
  return (
    <div className="inline-flex items-center rounded-xl border border-line bg-surface p-0.5" role="group" aria-label={label}>
      <button type="button" className={btn} onClick={() => onChange(value - 1)} disabled={disabled || value <= min} aria-label="−1">
        <Minus className="h-4 w-4" />
      </button>
      <span className="w-9 text-center font-semibold tabular" aria-live="polite">
        {value}
      </span>
      <button type="button" className={btn} onClick={() => onChange(value + 1)} disabled={disabled || value >= max} aria-label="+1">
        <Plus className="h-4 w-4" />
      </button>
    </div>
  );
}
