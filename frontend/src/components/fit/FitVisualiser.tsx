import { Loader2, X } from "lucide-react";
import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "../../i18n/I18nProvider";
import type { SizeChartRow, SizeStock } from "../../lib/types";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { Input } from "../ui/primitives";
import { EASE_COLORS } from "./easeColors";
import { BODY_LIMITS, DEFAULT_BODIES, buildGarment, fitReport, suggestSize, type Body, type BodyShape, type EaseLevel } from "./fitModel";

// three.js (~600 KB) is only downloaded when the fit view is opened.
const FitCanvas = lazy(() => import("./FitCanvas"));

const STORAGE_KEY = "shopsense.body";
const CM_PER_INCH = 2.54;
const FIELDS = ["height", "chest", "waist", "hip"] as const;
const LEVELS: EaseLevel[] = ["tight", "snug", "comfortable", "loose"];

function loadBody(): Body {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as Body | null;
    if (saved && (saved.shape === "female" || saved.shape === "male") && FIELDS.every((f) => typeof saved[f] === "number")) return saved;
  } catch {
    /* private mode or bad data: fall back to a typical body */
  }
  return DEFAULT_BODIES.female;
}

function saveBody(body: Body) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(body));
  } catch {
    /* ignore */
  }
}

interface Props {
  open: boolean;
  onClose: () => void;
  chart: SizeChartRow[];
  sizes: SizeStock[];
  initialSize: string | null;
  onChoose: (size: string) => void;
}

/** "See how it fits": a 3D mannequin of the shopper's body wearing any size from the chart. */
export function FitVisualiser({ open, onClose, chart, sizes, initialSize, onChoose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="fit-title"
      className="m-auto max-h-[calc(100dvh-2rem)] w-[min(60rem,calc(100vw-2rem))] overflow-y-auto rounded-2xl border border-line bg-surface p-0 text-fg shadow-xl backdrop:bg-black/50"
    >
      {open && <FitContent chart={chart} sizes={sizes} initialSize={initialSize} onClose={onClose} onChoose={onChoose} />}
    </dialog>
  );
}

function FitContent({ chart, sizes, initialSize, onClose, onChoose }: Omit<Props, "open">) {
  const { t } = useI18n();
  const [body, setBody] = useState<Body>(loadBody);
  const [unit, setUnit] = useState<"cm" | "inch">("cm");
  // Start on the size the shopper picked, else the one that suits their saved measurements.
  const [size, setSize] = useState<string>(() => initialSize ?? suggestSize(chart, body));
  const row = chart.find((r) => r.size === size) ?? chart[0];
  const garment = useMemo(() => buildGarment(body, row), [body, row]);
  const report = useMemo(() => fitReport(body, row, garment), [body, row, garment]);
  const stock = sizes.find((s) => s.size === size)?.stock ?? 0;

  const update = (next: Body) => {
    setBody(next);
    saveBody(next);
  };
  const shown = (cm: number) => (unit === "cm" ? Math.round(cm) : Math.round((cm / CM_PER_INCH) * 10) / 10);
  const setField = (field: (typeof FIELDS)[number], text: string) => {
    const value = Number(text);
    if (!Number.isFinite(value) || value <= 0) return;
    const cm = unit === "cm" ? value : value * CM_PER_INCH;
    const [lo, hi] = BODY_LIMITS[field];
    update({ ...body, [field]: Math.min(hi, Math.max(lo, cm)) });
  };
  const levelText = (level: EaseLevel) => t(`ease_${level}`);

  return (
    <div className="grid md:grid-cols-[1fr_22rem]">
      <div className="relative h-[55dvh] min-h-80 bg-surface-2 md:h-auto md:min-h-[34rem]">
        <Suspense
          fallback={
            <div className="absolute inset-0 flex items-center justify-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {t("model_loading")}
            </div>
          }
        >
          <FitCanvas body={body} garment={garment} label={t("fit_vis_alt", { size })} />
        </Suspense>
        <ul className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap gap-x-3 gap-y-1 rounded-lg bg-surface/85 px-2.5 py-1.5 text-xs">
          {LEVELS.map((level) => (
            <li key={level} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: EASE_COLORS[level] }} aria-hidden />
              {levelText(level)}
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-5 p-5">
        <div className="flex items-start justify-between gap-3">
          <h2 id="fit-title" className="text-lg font-semibold">{t("fit_vis_title", { size })}</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-muted hover:bg-surface-2 hover:text-fg" aria-label={t("close")}>
            <X className="h-5 w-5" />
          </button>
        </div>

        <fieldset>
          <legend className="mb-2 text-sm font-medium">{t("size")}</legend>
          <div className="flex flex-wrap gap-2">
            {chart.map((r) => (
              <button
                key={r.size}
                type="button"
                aria-pressed={size === r.size}
                onClick={() => setSize(r.size)}
                className={cn(
                  "min-w-11 rounded-xl border-2 px-2.5 py-1.5 text-sm font-medium",
                  size === r.size ? "border-brand bg-brand-soft text-brand" : "border-line hover:border-brand",
                )}
              >
                {r.size}
              </button>
            ))}
          </div>
        </fieldset>

        <section aria-live="polite">
          <ul className="space-y-1.5 text-sm">
            {report.areas.map((a) => (
              <li key={a.key} className="flex items-center justify-between gap-3">
                <span>
                  {t(`m_${a.key}`)}
                  {a.estimated && <span className="text-muted"> ({t("estimated")})</span>}
                </span>
                <span className="flex items-center gap-1.5 font-medium">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: EASE_COLORS[a.level] }} aria-hidden />
                  {levelText(a.level)} ·{" "}
                  <span className="tabular text-muted">
                    {a.ease >= 0 ? t("ease_room", { n: shown(a.ease), u: t(unit === "cm" ? "unit_cm" : "unit_inch") }) : t("ease_short", { n: shown(-a.ease), u: t(unit === "cm" ? "unit_cm" : "unit_inch") })}
                  </span>
                </span>
              </li>
            ))}
            <li className="text-muted">{t(`length_${report.length}`)}</li>
            {report.sleeve && <li className="text-muted">{t(`sleeve_${report.sleeve}`)}</li>}
          </ul>
          {stock > 0 ? (
            <Button className="mt-4 w-full" onClick={() => { onChoose(size); onClose(); }}>
              {t("choose_this_size", { size })}
            </Button>
          ) : (
            <p className="mt-4 text-sm font-medium text-muted">{t("size_sold_out", { s: size })}</p>
          )}
        </section>

        <fieldset className="space-y-3 border-t border-line pt-4">
          <legend className="sr-only">{t("your_measurements")}</legend>
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-medium" aria-hidden>{t("your_measurements")}</p>
            <div className="inline-flex rounded-lg border border-line p-0.5" role="group">
              {(["cm", "inch"] as const).map((u) => (
                <button
                  key={u}
                  type="button"
                  aria-pressed={unit === u}
                  onClick={() => setUnit(u)}
                  className={cn("rounded-md px-2 py-0.5 text-xs font-medium", unit === u ? "bg-brand text-on-brand" : "text-muted hover:text-fg")}
                >
                  {t(u === "cm" ? "unit_cm" : "unit_inch")}
                </button>
              ))}
            </div>
          </div>
          <div className="inline-flex rounded-xl border border-line p-1" role="group" aria-label={t("body_shape")}>
            {(["female", "male"] as BodyShape[]).map((shape) => (
              <button
                key={shape}
                type="button"
                aria-pressed={body.shape === shape}
                onClick={() => update({ ...DEFAULT_BODIES[shape], ...(body.shape === shape ? body : {}), shape })}
                className={cn("rounded-lg px-3 py-1 text-sm font-medium", body.shape === shape ? "bg-brand text-on-brand" : "text-muted hover:text-fg")}
              >
                {t(`body_${shape}`)}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {FIELDS.map((field) => (
              <label key={field} className="text-sm">
                <span className="mb-1 block text-muted">{t(field === "height" ? "body_height" : `m_${field}`)}</span>
                <Input
                  key={`${field}-${unit}-${body[field]}`} // re-seed the text when the unit or stored value changes
                  type="number"
                  inputMode="decimal"
                  defaultValue={shown(body[field])}
                  onBlur={(e) => setField(field, e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && setField(field, e.currentTarget.value)}
                  className="h-10"
                />
              </label>
            ))}
          </div>
          <p className="text-xs text-muted">{t("body_saved_note")}</p>
        </fieldset>

        <p className="text-xs text-muted">{t("fit_vis_note")}</p>
      </div>
    </div>
  );
}
