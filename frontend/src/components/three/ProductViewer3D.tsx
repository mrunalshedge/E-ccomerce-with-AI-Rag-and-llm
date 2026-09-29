import { Box, Hand, Loader2, Smartphone, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useI18n } from "../../i18n/I18nProvider";
import type { ModelViewerElement } from "./model-viewer";

// The 3D engine (~1 MB) is downloaded only when a shopper opens the 3D view.
let engine: Promise<unknown> | null = null;
const loadEngine = () => (engine ??= import("@google/model-viewer"));

interface Props {
  src: string;
  title: string;
  poster: string | null;
  credit: string | null;
}

/** Interactive 3D view + "View in your room" (WebXR on Android, Scene Viewer, Quick Look on iPhone).
 *  AR uses the model's real size (ar-scale="fixed"), so what you see in the room is what arrives. */
export function ProductViewer3D({ src, title, poster, credit }: Props) {
  const { t } = useI18n();
  const ref = useRef<ModelViewerElement>(null);
  const [ready, setReady] = useState(false); // engine registered
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");
  const [canAR, setCanAR] = useState(false);
  const [size, setSize] = useState<{ w: number; h: number; d: number } | null>(null);

  useEffect(() => {
    let alive = true;
    loadEngine().then(
      () => alive && setReady(true),
      () => alive && setStatus("error"),
    );
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!ready || !el) return;
    setStatus("loading");
    const onProgress = (e: Event) => setProgress((e as CustomEvent<{ totalProgress: number }>).detail.totalProgress);
    const onLoad = () => {
      setStatus("loaded");
      setCanAR(el.canActivateAR);
      const dim = el.getDimensions();
      setSize({ w: Math.round(dim.x * 100), h: Math.round(dim.y * 100), d: Math.round(dim.z * 100) });
    };
    const onError = () => setStatus("error");
    el.addEventListener("progress", onProgress);
    el.addEventListener("load", onLoad);
    el.addEventListener("error", onError);
    return () => {
      el.removeEventListener("progress", onProgress);
      el.removeEventListener("load", onLoad);
      el.removeEventListener("error", onError);
    };
  }, [ready, src]);

  return (
    <div>
      <div className="relative aspect-square overflow-hidden rounded-3xl border border-line bg-surface-2">
        {ready ? (
          <model-viewer
            ref={ref}
            src={src}
            alt={t("model_alt", { title })}
            poster={poster ?? undefined}
            loading="eager"
            camera-controls
            auto-rotate
            touch-action="pan-y"
            shadow-intensity="1"
            ar
            ar-modes="webxr scene-viewer quick-look"
            ar-scale="fixed"
            ar-placement="floor"
            style={{ width: "100%", height: "100%", background: "transparent" }}
          >
            {/* model-viewer shows this button only on devices that can do AR. */}
            <button
              slot="ar-button"
              className="absolute bottom-4 left-1/2 inline-flex -translate-x-1/2 items-center gap-2 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-on-brand shadow-lg"
            >
              <Box className="h-4 w-4" aria-hidden /> {t("view_in_room")}
            </button>
          </model-viewer>
        ) : null}

        {status === "loading" && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 p-4" aria-live="polite">
            <div className="mb-1.5 flex items-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {t("model_loading")}
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-line">
              <div className="h-full bg-brand transition-[width]" style={{ width: `${Math.round(progress * 100)}%` }} />
            </div>
          </div>
        )}
        {status === "error" && (
          <div role="alert" className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-6 text-center text-sm text-muted">
            <TriangleAlert className="h-6 w-6 text-warn" aria-hidden />
            {t("model_error")}
          </div>
        )}
      </div>

      {status === "loaded" && (
        <div className="mt-3 space-y-1.5 text-sm">
          {size && <p className="font-medium tabular">{t("model_size", { w: size.w, h: size.h, d: size.d })}</p>}
          <p className="flex items-center gap-1.5 text-muted">
            <Hand className="h-4 w-4 shrink-0" aria-hidden /> {t("model_drag_hint")}
          </p>
          {!canAR && (
            <p className="flex items-start gap-1.5 text-muted">
              <Smartphone className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {t("ar_on_phone")}
            </p>
          )}
        </div>
      )}
      {credit && <p className="mt-2 text-xs text-muted">{credit}</p>}
    </div>
  );
}
