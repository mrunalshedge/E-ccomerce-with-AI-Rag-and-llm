import type { EaseLevel } from "./fitModel";

/** Shared by the WebGL mannequin and its legend. WebGL needs literal colours (it can't read the
 *  theme's CSS variables), so these mid-tones were picked to read well on light and dark backgrounds. */
export const EASE_COLORS: Record<EaseLevel, string> = {
  tight: "#dc2626",
  snug: "#d97706",
  comfortable: "#16a34a",
  loose: "#2563eb",
};
