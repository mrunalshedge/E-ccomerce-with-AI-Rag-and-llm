import type { HandLandmarker } from "@mediapipe/tasks-vision";
import { Camera, Hand, Loader2, ShieldCheck, SwitchCamera, TriangleAlert } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useI18n } from "../../i18n/I18nProvider";
import type { WristTryOn } from "../../lib/types";
import { Button } from "../ui/button";
import { drawWatch, smooth, wristPose, type WristPose } from "./watch";

// Hand tracking runs entirely in the browser (WebAssembly). Only these two static files are
// downloaded; camera frames never leave the device.
const MEDIAPIPE_VERSION = "1.0.1"; // keep in sync with package.json
const WASM_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MEDIAPIPE_VERSION}/wasm`;
const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";
const LOST_AFTER_MS = 400;

type Phase = "intro" | "starting" | "live" | "denied" | "no_camera" | "failed";

async function createLandmarker(): Promise<HandLandmarker> {
  const { FilesetResolver, HandLandmarker } = await import("@mediapipe/tasks-vision");
  const fileset = await FilesetResolver.forVisionTasks(WASM_URL);
  const make = (delegate: "GPU" | "CPU") =>
    HandLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: MODEL_URL, delegate },
      runningMode: "VIDEO",
      numHands: 1,
    });
  try {
    return await make("GPU");
  } catch {
    return make("CPU"); // older phones / no WebGL2
  }
}

/** Live "try it on your wrist": camera + hand tracking + a watch drawn at its real size. */
export default function WristTryOnView({ spec, title }: { spec: WristTryOn; title: string }) {
  const { t } = useI18n();
  const [phase, setPhase] = useState<Phase>("intro");
  const [facing, setFacing] = useState<"user" | "environment">("user");
  const [tracking, setTracking] = useState(false);
  const [canFlip, setCanFlip] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const landmarker = useRef<HandLandmarker | null>(null);
  const raf = useRef(0);

  const stopCamera = useCallback(() => {
    cancelAnimationFrame(raf.current);
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  }, []);

  // Always release the camera and the tracker when the view goes away.
  useEffect(
    () => () => {
      stopCamera();
      landmarker.current?.close();
      landmarker.current = null;
    },
    [stopCamera],
  );

  const start = useCallback(
    async (mode: "user" | "environment") => {
      stopCamera();
      setPhase("starting");
      if (!navigator.mediaDevices?.getUserMedia) {
        setPhase("no_camera");
        return;
      }
      try {
        const [media, tracker] = await Promise.all([
          navigator.mediaDevices.getUserMedia({ video: { facingMode: mode, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false }),
          landmarker.current ?? createLandmarker(),
        ]);
        landmarker.current = tracker;
        stream.current = media;
        const devices = await navigator.mediaDevices.enumerateDevices();
        setCanFlip(devices.filter((d) => d.kind === "videoinput").length > 1);
        const el = video.current!;
        el.srcObject = media;
        await el.play();
        setPhase("live");
      } catch (error) {
        stopCamera();
        const name = (error as DOMException)?.name;
        setPhase(name === "NotAllowedError" || name === "SecurityError" ? "denied" : name === "NotFoundError" || name === "OverconstrainedError" ? "no_camera" : "failed");
      }
    },
    [stopCamera],
  );

  // Tracking + drawing loop while live.
  useEffect(() => {
    if (phase !== "live") return;
    const el = video.current;
    const cv = canvas.current;
    const tracker = landmarker.current;
    if (!el || !cv || !tracker) return;
    const ctx = cv.getContext("2d")!;
    const mirrored = facing === "user"; // selfie view: show it like a mirror
    let pose: WristPose | null = null;
    let lastSeen = 0;
    let lastVideoTime = -1;
    let wasTracking = false;

    const tick = () => {
      const w = el.videoWidth;
      const h = el.videoHeight;
      if (w && h) {
        if (cv.width !== w || cv.height !== h) {
          cv.width = w;
          cv.height = h;
        }
        const now = performance.now();
        if (el.currentTime !== lastVideoTime) {
          lastVideoTime = el.currentTime;
          const hand = tracker.detectForVideo(el, now).landmarks[0];
          if (hand) {
            const points = hand.map((p) => ({ x: (mirrored ? 1 - p.x : p.x) * w, y: p.y * h }));
            const next = wristPose(points);
            if (next) {
              pose = smooth(pose, next);
              lastSeen = now;
            }
          }
        }
        // Draw the (mirrored) frame and the watch on one canvas, so the watch text is never mirrored.
        ctx.save();
        if (mirrored) {
          ctx.translate(w, 0);
          ctx.scale(-1, 1);
        }
        ctx.drawImage(el, 0, 0, w, h);
        ctx.restore();
        const visible = pose !== null && now - lastSeen < LOST_AFTER_MS;
        if (visible) drawWatch(ctx, pose!, spec, new Date());
        else pose = null;
        if (visible !== wasTracking) {
          wasTracking = visible;
          setTracking(visible);
        }
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [phase, facing, spec]);

  const flip = () => {
    const next = facing === "user" ? "environment" : "user";
    setFacing(next);
    void start(next);
  };

  return (
    <div>
      <div className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-black">
        <video ref={video} playsInline muted className="hidden" />
        <canvas ref={canvas} role="img" aria-label={t("try_on_alt", { title })} className={phase === "live" ? "h-full w-full object-contain" : "hidden"} />

        {phase === "intro" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-surface-2 p-6 text-center">
            <ShieldCheck className="h-8 w-8 text-brand" aria-hidden />
            <p className="max-w-sm text-sm text-muted">{t("try_on_privacy")}</p>
            <Button onClick={() => void start(facing)}>
              <Camera className="h-4 w-4" aria-hidden /> {t("try_on_start")}
            </Button>
          </div>
        )}
        {phase === "starting" && (
          <div className="absolute inset-0 flex items-center justify-center gap-2 bg-surface-2 text-sm text-muted" aria-live="polite">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {t("try_on_loading")}
          </div>
        )}
        {(phase === "denied" || phase === "no_camera" || phase === "failed") && (
          <div role="alert" className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-surface-2 p-6 text-center text-sm text-muted">
            <TriangleAlert className="h-6 w-6 text-warn" aria-hidden />
            {t(phase === "denied" ? "try_on_denied" : phase === "no_camera" ? "try_on_no_camera" : "try_on_failed")}
            {phase !== "no_camera" && (
              <Button variant="secondary" size="sm" onClick={() => void start(facing)}>
                {t("retry")}
              </Button>
            )}
          </div>
        )}
        {phase === "live" && !tracking && (
          <div className="pointer-events-none absolute inset-x-3 bottom-3 flex items-center gap-2 rounded-xl bg-black/60 px-3 py-2 text-sm text-white" aria-live="polite">
            <Hand className="h-4 w-4 shrink-0" aria-hidden /> {t("try_on_hint")}
          </div>
        )}
        {phase === "live" && canFlip && (
          <button
            type="button"
            onClick={flip}
            className="absolute right-3 top-3 rounded-full bg-black/60 p-2 text-white hover:bg-black/75"
            aria-label={t("try_on_flip")}
          >
            <SwitchCamera className="h-5 w-5" />
          </button>
        )}
      </div>
      <p className="mt-2 text-xs text-muted">{t("try_on_scale", { mm: spec.case_mm })}</p>
    </div>
  );
}
