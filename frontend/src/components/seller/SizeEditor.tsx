import { Plus, Trash2 } from "lucide-react";

import { useI18n } from "../../i18n/I18nProvider";
import { MEASUREMENTS, type Measurement, type SizeChartRow, type SizeStock } from "../../lib/types";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { Input } from "../ui/primitives";

/** Chart values while typing: size → measurement → text in the input. */
export type ChartDraft = Record<string, Partial<Record<Measurement, string>>>;

export interface SizeDraft {
  sizes: SizeStock[];
  columns: Measurement[]; // which measurements the chart shows
  chart: ChartDraft;
}

const SUGGESTED = ["S", "M", "L", "XL", "XXL"];

export function draftFrom(sizes: SizeStock[] = [], chart: SizeChartRow[] | null = null): SizeDraft {
  const rows = chart ?? [];
  return {
    sizes,
    columns: MEASUREMENTS.filter((m) => rows.some((r) => r[m] !== undefined)),
    chart: Object.fromEntries(
      rows.map((r) => [r.size, Object.fromEntries(MEASUREMENTS.filter((m) => r[m] !== undefined).map((m) => [m, String(r[m])]))]),
    ),
  };
}

/** The API payload: sizes (trimmed) and chart rows for the current sizes and chosen columns. */
export function payloadFrom(draft: SizeDraft): { sizes: SizeStock[]; size_chart: SizeChartRow[] } {
  const sizes = draft.sizes.map((s) => ({ ...s, size: s.size.trim() }));
  const size_chart = draft.columns.length
    ? sizes.map(({ size }) => {
        const row: SizeChartRow = { size };
        for (const m of draft.columns) {
          const value = draft.chart[size]?.[m];
          if (value) row[m] = Number(value);
        }
        return row;
      })
    : [];
  return { sizes, size_chart };
}

export function draftProblems(draft: SizeDraft): boolean {
  const names = draft.sizes.map((s) => s.size.trim().toUpperCase());
  const badName = names.some((n) => !n) || new Set(names).size !== names.length;
  const badValue = Object.values(draft.chart).some((row) =>
    Object.values(row).some((v) => v !== undefined && v !== "" && !(Number(v) >= 1 && Number(v) <= 300)),
  );
  return badName || badValue;
}

export function SizeEditor({ draft, onChange }: { draft: SizeDraft; onChange: (draft: SizeDraft) => void }) {
  const { t } = useI18n();
  const setSizes = (sizes: SizeStock[]) => onChange({ ...draft, sizes });
  const total = draft.sizes.reduce((sum, s) => sum + s.stock, 0);
  const nextSuggestion = SUGGESTED.find((s) => !draft.sizes.some((x) => x.size.trim().toUpperCase() === s)) ?? "";
  const toggleColumn = (m: Measurement) =>
    onChange({ ...draft, columns: draft.columns.includes(m) ? draft.columns.filter((c) => c !== m) : MEASUREMENTS.filter((c) => c === m || draft.columns.includes(c)) });
  const setValue = (size: string, m: Measurement, value: string) =>
    onChange({ ...draft, chart: { ...draft.chart, [size]: { ...draft.chart[size], [m]: value.replace(/[^\d.]/g, "") } } });

  return (
    <fieldset className="space-y-4 rounded-xl border border-line p-4">
      <legend className="px-1 font-semibold">{t("seller_sizes")}</legend>
      <p className="-mt-2 text-xs text-muted">{t("seller_sizes_hint")}</p>

      {draft.sizes.length > 0 && (
        <ul className="space-y-2">
          {draft.sizes.map((s, i) => (
            <li key={i} className="flex items-center gap-2">
              <Input
                aria-label={t("seller_size_name")}
                value={s.size}
                maxLength={20}
                className="w-24"
                onChange={(e) => setSizes(draft.sizes.map((x, j) => (j === i ? { ...x, size: e.target.value } : x)))}
              />
              <Input
                aria-label={t("seller_size_stock")}
                type="number"
                min={0}
                value={s.stock}
                className="w-28"
                onChange={(e) => setSizes(draft.sizes.map((x, j) => (j === i ? { ...x, stock: Math.max(0, Number(e.target.value) || 0) } : x)))}
              />
              <Button type="button" variant="ghost" size="sm" aria-label={t("remove")} onClick={() => setSizes(draft.sizes.filter((_, j) => j !== i))}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" variant="secondary" size="sm" onClick={() => setSizes([...draft.sizes, { size: nextSuggestion, stock: 0 }])}>
          <Plus className="h-4 w-4" /> {t("seller_add_size")}
        </Button>
        {draft.sizes.length > 0 && <span className="text-sm text-muted tabular">{t("seller_total_stock", { n: total })}</span>}
      </div>

      {draft.sizes.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-medium">{t("seller_size_chart")}</p>
          <div className="flex flex-wrap gap-1.5" role="group" aria-label={t("seller_add_measurement")}>
            {MEASUREMENTS.map((m) => (
              <button
                key={m}
                type="button"
                aria-pressed={draft.columns.includes(m)}
                onClick={() => toggleColumn(m)}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs",
                  draft.columns.includes(m) ? "border-brand bg-brand-soft font-medium text-brand" : "border-line text-muted hover:border-brand",
                )}
              >
                {t(`m_${m}`)}
              </button>
            ))}
          </div>
          {draft.columns.length > 0 && (
            <div className="mt-3 overflow-x-auto">
              <table className="text-sm">
                <thead>
                  <tr className="text-left text-muted">
                    <th className="pb-1 pr-2 font-medium">{t("seller_size_name")}</th>
                    {draft.columns.map((m) => (
                      <th key={m} className="pb-1 pr-2 font-medium">
                        {t(`m_${m}`)} ({t("unit_cm")})
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {draft.sizes.map(({ size }, i) => (
                    <tr key={i}>
                      <th scope="row" className="pr-2 text-left font-semibold">{size || "—"}</th>
                      {draft.columns.map((m) => (
                        <td key={m} className="py-1 pr-2">
                          <Input
                            aria-label={`${size} ${t(`m_${m}`)}`}
                            inputMode="decimal"
                            className="h-9 w-20"
                            value={draft.chart[size]?.[m] ?? ""}
                            onChange={(e) => setValue(size, m, e.target.value)}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </fieldset>
  );
}
