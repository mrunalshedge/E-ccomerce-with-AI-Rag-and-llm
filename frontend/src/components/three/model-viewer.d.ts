// JSX typing for Google's <model-viewer> web component (only the attributes we use).
import type { DetailedHTMLProps, HTMLAttributes } from "react";

export interface ModelViewerElement extends HTMLElement {
  canActivateAR: boolean;
  activateAR(): Promise<void>;
  getDimensions(): { x: number; y: number; z: number };
}

type ModelViewerProps = DetailedHTMLProps<HTMLAttributes<ModelViewerElement>, ModelViewerElement> & {
  src: string;
  alt: string;
  poster?: string;
  ar?: boolean;
  "ar-modes"?: string;
  "ar-scale"?: "auto" | "fixed";
  "ar-placement"?: "floor" | "wall";
  "camera-controls"?: boolean;
  "auto-rotate"?: boolean;
  "touch-action"?: string;
  "shadow-intensity"?: string;
  "environment-image"?: string;
  exposure?: string;
  loading?: "auto" | "lazy" | "eager";
};

declare module "react" {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      "model-viewer": ModelViewerProps;
    }
  }
}
