import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

import { EASE_COLORS } from "./easeColors";
import { easeLevel, landmarks, torsoProfile, circAt, type Body, type Garment } from "./fitModel";

const TWO_PI = Math.PI * 2;
// Torso cross-sections are ellipses, wider than deep (keeps the same circumference within ~1%).
const WIDE = 1.18;
const DEEP = 0.82;
const SKIN = 0xc9ced6; // neutral mannequin grey (works in light and dark themes)

function lathe(rings: { y: number; circ: number }[], segments = 48) {
  return new THREE.LatheGeometry(
    rings.map((r) => new THREE.Vector2(r.circ / TWO_PI, r.y)),
    segments,
  );
}

function buildMannequin(body: Body, garment: Garment | null): THREE.Group {
  const group = new THREE.Group();
  const y = landmarks(body);
  const skin = new THREE.MeshStandardMaterial({ color: SKIN, roughness: 0.7 });

  // Torso: a smooth lathe through the body profile.
  const profile = torsoProfile(body);
  const bottom = profile[0].y;
  const top = profile[profile.length - 1].y;
  const torsoRings = Array.from({ length: 49 }, (_, i) => {
    const ry = bottom + ((top - bottom) * i) / 48;
    return { y: ry, circ: circAt(profile, ry) };
  });
  const torso = new THREE.Mesh(lathe(torsoRings), skin);
  torso.scale.set(WIDE, 1, DEEP);
  group.add(torso);

  // Neck and head.
  const neckR = (body.chest * 0.4) / TWO_PI;
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(neckR * 0.9, neckR, body.height * 0.05, 24), skin);
  neck.position.y = y.neck + body.height * 0.02;
  group.add(neck);
  const head = new THREE.Mesh(new THREE.SphereGeometry(body.height * 0.062, 32, 24), skin);
  head.scale.set(0.85, 1, 0.95);
  head.position.y = y.neck + body.height * 0.085;
  group.add(head);

  // Legs.
  const hipRx = (body.hip / TWO_PI) * WIDE;
  const legLen = y.crotch;
  for (const side of [-1, 1]) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry((body.hip * 0.58) / TWO_PI, 3.8, legLen, 24), skin);
    leg.position.set(side * hipRx * 0.48, legLen / 2 + 2, 0);
    group.add(leg);
    const foot = new THREE.Mesh(new THREE.BoxGeometry(8, 5, 22), skin);
    foot.position.set(side * hipRx * 0.5, 2.5, 5);
    group.add(foot);
  }

  // Arms (slight A-pose) with optional sleeves.
  const shoulderX = ((body.chest * 0.97) / TWO_PI) * WIDE;
  const armTopR = (body.chest * 0.31) / TWO_PI;
  const garmentColor = garment ? new THREE.Color(EASE_COLORS[easeLevel(garment.rings[garment.rings.length - 1].ease)]) : null;
  for (const side of [-1, 1]) {
    const arm = new THREE.Group();
    arm.position.set(side * (shoulderX - 1), y.shoulder - 4, 0);
    arm.rotation.z = side * 0.2;
    const limb = new THREE.Mesh(new THREE.CylinderGeometry(armTopR, 2.6, y.armLength, 20), skin);
    limb.position.y = -y.armLength / 2;
    arm.add(limb);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(4, 16, 12), skin);
    hand.scale.set(0.8, 1.3, 0.6);
    hand.position.y = -y.armLength - 3;
    arm.add(hand);
    if (garment?.sleeve && garmentColor) {
      const len = Math.min(garment.sleeve, y.armLength + 6);
      const endR = armTopR + (2.6 - armTopR) * (len / y.armLength);
      const sleeve = new THREE.Mesh(
        new THREE.CylinderGeometry(armTopR + 2.2, endR + 2.2, len, 24, 1, true),
        new THREE.MeshStandardMaterial({ color: garmentColor, roughness: 0.85, side: THREE.DoubleSide }),
      );
      sleeve.position.y = -len / 2 + 2;
      arm.add(sleeve);
    }
    group.add(arm);
  }

  // Garment shell, coloured ring by ring by how much room it leaves.
  if (garment) {
    const geometry = lathe(garment.rings, 64);
    const perRing = garment.rings.map((r) => new THREE.Color(EASE_COLORS[easeLevel(r.ease)]));
    const colors: number[] = [];
    const count = geometry.attributes.position.count;
    for (let v = 0; v < count; v++) {
      const c = perRing[v % garment.rings.length];
      colors.push(c.r, c.g, c.b);
    }
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    const shell = new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide }),
    );
    shell.scale.set(WIDE, 1, DEEP);
    group.add(shell);
  }

  // Soft floor shadow.
  const shadow = new THREE.Mesh(
    new THREE.CircleGeometry(body.height * 0.22, 48),
    new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.12 }),
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = 0.1;
  group.add(shadow);
  return group;
}

function disposeGroup(group: THREE.Object3D) {
  group.traverse((obj) => {
    if (obj instanceof THREE.Mesh) {
      obj.geometry.dispose();
      (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach((m) => m.dispose());
    }
  });
}

/** Rotatable 3D mannequin wearing the chosen size. */
export default function FitCanvas({ body, garment, label }: { body: Body; garment: Garment | null; label: string }) {
  const host = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<{ scene: THREE.Scene; model: THREE.Group | null; frame: (h: number) => void } | null>(null);

  // One renderer per open dialog.
  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    renderer.domElement.style.touchAction = "none";

    const scene = new THREE.Scene();
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8f99, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.8);
    sun.position.set(120, 300, 220);
    scene.add(sun);

    const camera = new THREE.PerspectiveCamera(30, 1, 1, 5000);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.enablePan = false;
    controls.autoRotate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    controls.autoRotateSpeed = 1.5;
    controls.addEventListener("start", () => (controls.autoRotate = false));

    const frame = (height: number) => {
      controls.target.set(0, height * 0.52, 0);
      camera.position.set(0, height * 0.6, height * 3.1);
      controls.minDistance = height * 1.1;
      controls.maxDistance = height * 5;
      controls.update();
    };
    sceneRef.current = { scene, model: null, frame };

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = el;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(el);
    resize();

    let raf = 0;
    const loop = () => {
      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    loop();

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      controls.dispose();
      if (sceneRef.current?.model) disposeGroup(sceneRef.current.model);
      renderer.dispose();
      renderer.domElement.remove();
      sceneRef.current = null;
    };
  }, []);

  // Rebuild the mannequin when the body or the size changes (cheap: a few thousand vertices).
  const height = body.height;
  useEffect(() => {
    const ctx = sceneRef.current;
    if (!ctx) return;
    if (ctx.model) {
      ctx.scene.remove(ctx.model);
      disposeGroup(ctx.model);
    }
    ctx.model = buildMannequin(body, garment);
    ctx.scene.add(ctx.model);
  }, [body, garment]);

  // Re-frame only when the height changes, so a rotated view stays put while comparing sizes.
  useEffect(() => {
    sceneRef.current?.frame(height);
  }, [height]);

  return <div ref={host} role="img" aria-label={label} className="h-full w-full cursor-grab active:cursor-grabbing" />;
}
