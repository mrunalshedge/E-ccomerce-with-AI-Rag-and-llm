import { Ruler, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useI18n } from "../../i18n/I18nProvider";
import { MEASUREMENTS, type FitSummary, type SizeChartRow, type SizeStock } from "../../lib/types";
import { cn } from "../../lib/utils";

const CM_PER_INCH = 2.54;

interface SizePickerProps {
  sizes: SizeStock[];
  value: string | null;
  onChange: (size: string) => void;
  chart: SizeChartRow[] | null;
  fit: FitSummary | null;
  error?: boolean; // "choose a size first" was triggered
  onAskAssistant?: () => void;
}

/** Required size choice: sold-out sizes stay visible but can't be picked. */
export function SizePicker({ sizes, value, onChange, chart, fit, error, onAskAssistant }: SizePickerProps) {
  const { t } = useI18n();
  const [chartOpen, setChartOpen] = useState(false);
  const selected = sizes.find((s) => s.size === value);

  return (
    <fieldset id="size-picker" className="mt-6 scroll-mt-24" aria-describedby={error ? "size-error" : undefined}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <legend className="font-semibold">
          {t("size")}
          {value && <span className="ml-1.5 font-normal text-muted">: {value}</span>}
        </legend>
        {chart && chart.length > 0 && (
          <button type="button" onClick={() => setChartOpen(true)} className="inline-flex items-center gap-1.5 text-sm font-medium text-brand hover:underline">
            <Ruler className="h-4 w-4" aria-hidden /> {t("size_chart")}
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {sizes.map(({ size, stock }) => {
          const soldOut = stock === 0;
          return (
            <label
              key={size}
              title={soldOut ? t("size_sold_out", { s: size }) : undefined}
              className={cn(
                "relative min-w-12 rounded-xl border-2 px-3 py-2 text-center text-sm font-medium transition-colors focus-within:ring-2 focus-within:ring-ring",
                soldOut
                  ? "cursor-not-allowed border-line text-muted line-through opacity-60"
                  : value === size
                    ? "cursor-pointer border-brand bg-brand-soft text-brand"
                    : cn("cursor-pointer hover:border-brand", error ? "border-danger" : "border-line"),
              )}
            >
              <input
                type="radio"
                name="size"
                value={size}
                className="sr-only"
                disabled={soldOut}
                checked={value === size}
                onChange={() => onChange(size)}
                aria-label={soldOut ? t("size_sold_out", { s: size }) : size}
              />
              {size}
            </label>
          );
        })}
      </div>
      {error && !value && (
        <p id="size-error" role="alert" className="mt-2 text-sm font-medium text-danger">
          {t("choose_size_first")}
        </p>
      )}
      {selected && selected.stock > 0 && selected.stock <= 5 && (
        <p className="mt-2 text-sm font-medium text-warn">{t("size_left", { n: selected.stock, s: selected.size })}</p>
      )}
      {fit && <FitLine fit={fit} />}
      {onAskAssistant && (
        <button type="button" onClick={onAskAssistant} className="mt-2 inline-flex items-center gap-1.5 text-sm text-brand hover:underline">
          <Sparkles className="h-4 w-4" aria-hidden /> {t("size_help")}
        </button>
      )}
      {chart && <SizeChartDialog open={chartOpen} onClose={() => setChartOpen(false)} chart={chart} />}
    </fieldset>
  );
}

/** "Fit, from 5 verified buyers: True to size" plus a small three-part bar. */
function FitLine({ fit }: { fit: FitSummary }) {
  const { t } = useI18n();
  const total = fit.runs_small + fit.true_to_size + fit.runs_large;
  if (total === 0) return null;
  if (fit.verdict === null) return <p className="mt-3 text-sm text-muted">{t("fit_few_answers", { n: total })}</p>;
  const parts = [
    { key: "runs_small", n: fit.runs_small, cls: "bg-warn" },
    { key: "true_to_size", n: fit.true_to_size, cls: "bg-brand" },
    { key: "runs_large", n: fit.runs_large, cls: "bg-info" },
  ] as const;
  return (
    <div className="mt-3 rounded-xl border border-line p-3 text-sm">
      <p>
        <span className="text-muted">{t("fit_buyers_say", { n: total })}: </span>
        <strong>{fit.verdict === "mixed" ? t("fit_mixed") : t(`fit_${fit.verdict}`)}</strong>
      </p>
      <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-surface-2" aria-hidden>
        {parts.map((p) => p.n > 0 && <div key={p.key} className={p.cls} style={{ width: `${(p.n / total) * 100}%` }} />)}
      </div>
      <ul className="mt-1.5 flex flex-wrap gap-x-4 text-xs text-muted">
        {parts.map((p) => (
          <li key={p.key}>
            {t(`fit_${p.key}`)}: <span className="tabular">{p.n}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SizeChartDialog({ open, onClose, chart }: { open: boolean; onClose: () => void; chart: SizeChartRow[] }) {
  const { t } = useI18n();
  const ref = useRef<HTMLDialogElement>(null);
  const [unit, setUnit] = useState<"cm" | "inch">("cm");
  const columns = MEASUREMENTS.filter((m) => chart.some((row) => row[m] !== undefined));

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const show = (cm: number | undefined) =>
    cm === undefined ? "–" : unit === "cm" ? String(cm) : String(Math.round((cm / CM_PER_INCH) * 10) / 10);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()} // click on the backdrop
      aria-labelledby="size-chart-title"
      className="m-auto w-[min(40rem,calc(100vw-2rem))] rounded-2xl border border-line bg-surface p-0 text-fg shadow-xl backdrop:bg-black/50"
    >
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="size-chart-title" className="text-lg font-semibold">{t("size_chart")}</h2>
            <p className="mt-0.5 text-sm text-muted">{t("size_chart_note")}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-muted hover:bg-surface-2 hover:text-fg" aria-label={t("close")}>
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-4 inline-flex rounded-xl border border-line p-1" role="group">
          {(["cm", "inch"] as const).map((u) => (
            <button
              key={u}
              type="button"
              aria-pressed={unit === u}
              onClick={() => setUnit(u)}
              className={cn("rounded-lg px-3 py-1 text-sm font-medium", unit === u ? "bg-brand text-on-brand" : "text-muted hover:text-fg")}
            >
              {t(u === "cm" ? "unit_cm" : "unit_inch")}
            </button>
          ))}
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm tabular">
            <thead>
              <tr className="border-b border-line text-left text-muted">
                <th scope="col" className="py-2 pr-4 font-medium">{t("size")}</th>
                {columns.map((m) => (
                  <th key={m} scope="col" className="py-2 pr-4 font-medium">
                    {t(`m_${m}`)} <span className="font-normal">({t(unit === "cm" ? "unit_cm" : "unit_inch")})</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {chart.map((row) => (
                <tr key={row.size} className="border-b border-line last:border-0">
                  <th scope="row" className="py-2 pr-4 text-left font-semibold">{row.size}</th>
                  {columns.map((m) => (
                    <td key={m} className="py-2 pr-4">{show(row[m])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </dialog>
  );
}
