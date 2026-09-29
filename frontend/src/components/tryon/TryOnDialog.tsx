import { Loader2, Watch, X } from "lucide-react";
import { Suspense, lazy, useEffect, useRef, useState } from "react";

import { useI18n } from "../../i18n/I18nProvider";
import type { WristTryOn } from "../../lib/types";

// The camera view (and MediaPipe) load only when the shopper opens try-on.
const WristTryOnView = lazy(() => import("./WristTryOnView"));

/** "Try it on your wrist" button + dialog. Closing the dialog unmounts the view, which stops the camera. */
export function TryOnButton({ spec, title }: { spec: WristTryOn; title: string }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-3 inline-flex items-center gap-2 rounded-xl border border-brand px-3 py-2 text-sm font-medium text-brand hover:bg-brand-soft"
      >
        <Watch className="h-4 w-4" aria-hidden /> {t("try_on_wrist")}
      </button>
      <dialog
        ref={ref}
        onClose={() => setOpen(false)}
        aria-labelledby="try-on-title"
        className="m-auto max-h-[calc(100dvh-2rem)] w-[min(44rem,calc(100vw-2rem))] overflow-y-auto rounded-2xl border border-line bg-surface p-0 text-fg shadow-xl backdrop:bg-black/60"
      >
        <div className="p-4 sm:p-5">
          <div className="mb-3 flex items-start justify-between gap-3">
            <h2 id="try-on-title" className="text-lg font-semibold">{t("try_on_title", { title })}</h2>
            <button type="button" onClick={() => setOpen(false)} className="rounded-lg p-1.5 text-muted hover:bg-surface-2 hover:text-fg" aria-label={t("close")}>
              <X className="h-5 w-5" />
            </button>
          </div>
          {open && (
            <Suspense
              fallback={
                <div className="flex aspect-[4/3] items-center justify-center gap-2 rounded-2xl bg-surface-2 text-sm text-muted">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {t("try_on_loading")}
                </div>
              }
            >
              <WristTryOnView spec={spec} title={title} />
            </Suspense>
          )}
        </div>
      </dialog>
    </>
  );
}
