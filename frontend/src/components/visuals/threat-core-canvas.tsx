"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

export interface ThreatCoreCounts {
  safe: number;
  suspicious: number;
  highRisk: number;
}

export interface ThreatCoreCanvasProps {
  /**
   * Visual mode matching the cybersecurity design system:
   * - "hero": 3D particle globe + tilted orbital rings + glowing holographic Shield + wave horizon
   * - "auth": Large cinematic rotating 3D threat sphere + radar sweep wedge + dual orbital rings + ambient particles
   * - "radar": Concentric Live Threat Radar with sweeping beam, central shield & real-data blips
   * - "scanning": Dual rotating scan rings + inner reticle for live scan analysis
   * - "command": Compact 3D neural core
   */
  mode?: "hero" | "auth" | "radar" | "scanning" | "command";
  /** Real threat proportion (0..1) from live scan history; never randomized. */
  threatRatio?: number;
  /** Real scan counts used strictly to color radar blips proportionally; 0 total => 0 blips. */
  counts?: ThreatCoreCounts;
  /** Elevates sweep speed slightly while a real scan request is in flight. */
  active?: boolean;
  className?: string;
}

interface Point3D {
  x: number;
  y: number;
  z: number;
  ring: number;
}

function buildFibonacciSphere(count: number): Point3D[] {
  const pts: Point3D[] = [];
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / Math.max(1, count - 1)) * 2;
    const radius = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = goldenAngle * i;
    pts.push({
      x: Math.cos(theta) * radius,
      y,
      z: Math.sin(theta) * radius,
      ring: i / count,
    });
  }
  return pts;
}

const HERO_NODES = buildFibonacciSphere(76);
const AUTH_NODES = buildFibonacciSphere(92);
const CORE_NODES = buildFibonacciSphere(46);

function drawShield(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  size: number,
  cyanRGB: string,
  blueRGB: string,
  isDark: boolean,
  withCheck: boolean,
) {
  const topY = cy - size * 0.62;
  const shoulderY = cy - size * 0.36;
  const midY = cy + size * 0.14;
  const tipY = cy + size * 0.68;
  const halfW = size * 0.54;

  const traceShield = (scale = 1) => {
    const w = halfW * scale;
    const ty = cy - size * 0.62 * scale;
    const sy = cy - size * 0.36 * scale;
    const my = cy + size * 0.14 * scale;
    const by = cy + size * 0.68 * scale;
    ctx.beginPath();
    ctx.moveTo(cx, ty);
    ctx.bezierCurveTo(cx + w * 0.45, ty + size * 0.08 * scale, cx + w * 0.85, sy, cx + w, sy);
    ctx.bezierCurveTo(cx + w, my, cx + w * 0.55, by - size * 0.16 * scale, cx, by);
    ctx.bezierCurveTo(cx - w * 0.55, by - size * 0.16 * scale, cx - w, my, cx - w, sy);
    ctx.bezierCurveTo(cx - w * 0.85, sy, cx - w * 0.45, ty + size * 0.08 * scale, cx, ty);
    ctx.closePath();
  };

  ctx.save();
  // Soft shield backlight
  const aura = ctx.createRadialGradient(cx, cy, size * 0.08, cx, cy, size * 1.15);
  aura.addColorStop(0, `rgba(${cyanRGB}, ${isDark ? 0.36 : 0.22})`);
  aura.addColorStop(0.6, `rgba(${blueRGB}, ${isDark ? 0.14 : 0.08})`);
  aura.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = aura;
  ctx.beginPath();
  ctx.arc(cx, cy, size * 1.15, 0, Math.PI * 2);
  ctx.fill();

  // Outer shield glass fill + glowing border
  traceShield(1);
  const grad = ctx.createLinearGradient(cx - halfW, topY, cx + halfW, tipY);
  grad.addColorStop(0, `rgba(${cyanRGB}, ${isDark ? 0.24 : 0.2})`);
  grad.addColorStop(0.55, `rgba(${blueRGB}, ${isDark ? 0.22 : 0.16})`);
  grad.addColorStop(1, `rgba(${cyanRGB}, ${isDark ? 0.12 : 0.1})`);
  ctx.fillStyle = grad;
  ctx.shadowColor = `rgba(${cyanRGB}, ${isDark ? 0.85 : 0.45})`;
  ctx.shadowBlur = size * 0.32;
  ctx.fill();

  ctx.lineWidth = Math.max(1.8, size * 0.038);
  ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.95 : 0.9})`;
  ctx.stroke();

  // Inner bevel hairline
  ctx.shadowBlur = 0;
  traceShield(0.84);
  ctx.lineWidth = 1;
  ctx.strokeStyle = `rgba(255, 255, 255, ${isDark ? 0.28 : 0.42})`;
  ctx.stroke();

  // Central luminous checkmark
  if (withCheck) {
    ctx.beginPath();
    ctx.moveTo(cx - size * 0.21, cy + size * 0.02);
    ctx.lineTo(cx - size * 0.04, cy + size * 0.19);
    ctx.lineTo(cx + size * 0.24, cy - size * 0.16);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = Math.max(2.6, size * 0.075);
    ctx.strokeStyle = `rgba(${cyanRGB}, 1)`;
    ctx.shadowColor = `rgba(${cyanRGB}, 0.9)`;
    ctx.shadowBlur = size * 0.22;
    ctx.stroke();
  }
  ctx.restore();
  void shoulderY;
  void midY;
}

export function ThreatCoreCanvas({
  mode = "command",
  threatRatio = 0,
  counts,
  active = false,
  className,
}: ThreatCoreCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointerRef = useRef({ targetX: 0, targetY: 0, x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const clampedThreat = Math.max(0, Math.min(1, Number.isFinite(threatRatio) ? threatRatio : 0));
    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    let width = 320;
    let height = 320;
    let dpr = 1;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;
      width = rect.width;
      height = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null;
    ro?.observe(canvas);

    const onPointerMove = (e: PointerEvent) => {
      if (reduceMotion) return;
      const rect = canvas.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;
      const nx = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      const ny = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
      pointerRef.current.targetX = Math.max(-1, Math.min(1, nx)) * 0.26;
      pointerRef.current.targetY = Math.max(-1, Math.min(1, ny)) * 0.2;
    };

    const onPointerLeave = () => {
      pointerRef.current.targetX = 0;
      pointerRef.current.targetY = 0;
    };

    canvas.addEventListener("pointermove", onPointerMove, { passive: true });
    canvas.addEventListener("pointerleave", onPointerLeave, { passive: true });

    let rafId = 0;
    let startTime = performance.now();

    const drawScanning = (elapsed: number, isDark: boolean, cyanRGB: string, tealRGB: string) => {
      const cx = width * 0.5;
      const cy = height * 0.5;
      const R = Math.min(width, height) * 0.34;

      // Ambient radial cyan glow
      const glow = ctx.createRadialGradient(cx, cy, R * 0.08, cx, cy, R * 1.65);
      glow.addColorStop(0, `rgba(${cyanRGB}, ${isDark ? 0.3 : 0.16})`);
      glow.addColorStop(0.55, `rgba(${tealRGB}, ${isDark ? 0.11 : 0.06})`);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.65, 0, Math.PI * 2);
      ctx.fill();

      // Symmetrical horizontal dotted cyber wave across wings (Panel 05)
      if (width > height * 1.35) {
        const rows = 4;
        const cols = 42;
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const nx = c / (cols - 1);
            const x = nx * width;
            const centerClearance = Math.abs(nx - 0.5) * 2;
            const edgeFade = Math.sin(nx * Math.PI) * Math.min(1, centerClearance * 1.6);
            if (edgeFade < 0.05) continue;
            const wave = Math.sin(nx * 7 + elapsed * 1.6 + r * 0.8) * 12 + Math.cos(nx * 4 - elapsed) * 6;
            const y = cy + (r - 1.5) * 8 + wave;
            ctx.beginPath();
            ctx.arc(x, y, 1.3, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${cyanRGB}, ${(edgeFade * (isDark ? 0.42 : 0.28)).toFixed(3)})`;
            ctx.fill();
          }
        }
      }

      // Subtle dashed outer baseline ring
      ctx.save();
      ctx.setLineDash([4, 6]);
      ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.24 : 0.28})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.24, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Rotating segmented outer ring
      const a1 = elapsed * 1.4;
      ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.9 : 0.85})`;
      ctx.lineWidth = 2.6;
      ctx.lineCap = "round";
      ctx.shadowColor = `rgba(${cyanRGB}, 0.75)`;
      ctx.shadowBlur = 12;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.02, a1, a1 + Math.PI * 0.65);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.02, a1 + Math.PI, a1 + Math.PI * 1.65);
      ctx.stroke();

      // Counter-rotating inner ring
      const a2 = -elapsed * 1.05;
      ctx.shadowBlur = 6;
      ctx.lineWidth = 1.6;
      ctx.strokeStyle = `rgba(${tealRGB}, ${isDark ? 0.72 : 0.7})`;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 0.82, a2, a2 + Math.PI * 0.78);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx, cy, R * 0.82, a2 + Math.PI * 1.05, a2 + Math.PI * 1.75);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Pulse wave expanding outward
      if (!reduceMotion) {
        const pulse = (elapsed * 0.75) % 1;
        const pr = R * 0.48 + pulse * R * 0.85;
        ctx.beginPath();
        ctx.arc(cx, cy, pr, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${cyanRGB}, ${(1 - pulse) * 0.34})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }
      ctx.restore();

      // Luminous center Shield inside scanning rings (Panel 05)
      drawShield(ctx, cx, cy, R * 0.56, cyanRGB, "59, 130, 246", isDark, true);
    };

    const drawRadar = (elapsed: number, isDark: boolean, cyanRGB: string, safeRGB: string, warnRGB: string, alertRGB: string) => {
      const cx = width * 0.5;
      const cy = height * 0.5;
      const R = Math.min(width, height) * 0.41;

      const glow = ctx.createRadialGradient(cx, cy, R * 0.05, cx, cy, R * 1.15);
      glow.addColorStop(0, `rgba(${cyanRGB}, ${isDark ? 0.2 : 0.12})`);
      glow.addColorStop(0.65, `rgba(${cyanRGB}, ${isDark ? 0.05 : 0.03})`);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.15, 0, Math.PI * 2);
      ctx.fill();

      // Concentric radar rings
      for (const mult of [0.32, 0.56, 0.78, 1]) {
        ctx.beginPath();
        ctx.arc(cx, cy, R * mult, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${cyanRGB}, ${mult === 1 ? (isDark ? 0.28 : 0.34) : (isDark ? 0.14 : 0.18)})`;
        ctx.lineWidth = mult === 1 ? 1.25 : 1;
        ctx.stroke();
      }

      // Crosshairs + diagonals
      ctx.save();
      ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.11 : 0.15})`;
      ctx.lineWidth = 1;
      for (let a = 0; a < 4; a++) {
        const ang = (a * Math.PI) / 4;
        ctx.beginPath();
        ctx.moveTo(cx - Math.cos(ang) * R, cy - Math.sin(ang) * R);
        ctx.lineTo(cx + Math.cos(ang) * R, cy + Math.sin(ang) * R);
        ctx.stroke();
      }

      // Rotating radar sweep wedge
      const sweepAngle = elapsed * 0.9;
      const span = Math.PI * 0.42;
      for (let s = 0; s < 16; s++) {
        const a0 = sweepAngle - (s / 16) * span;
        const a1 = sweepAngle - ((s + 1) / 16) * span;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, R, a1, a0);
        ctx.closePath();
        ctx.fillStyle = `rgba(${cyanRGB}, ${(1 - s / 16) * (isDark ? 0.18 : 0.13)})`;
        ctx.fill();
      }
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(sweepAngle) * R, cy + Math.sin(sweepAngle) * R);
      ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.8 : 0.7})`;
      ctx.lineWidth = 1.6;
      ctx.stroke();

      // Real-data blips (zero blips when total === 0)
      const total = counts ? counts.safe + counts.suspicious + counts.highRisk : 0;
      if (total > 0 && counts) {
        const blipCap = Math.min(18, total);
        const hiCount = Math.round((counts.highRisk / total) * blipCap);
        const suspCount = Math.round((counts.suspicious / total) * blipCap);
        const blipColors: string[] = [];
        for (let i = 0; i < blipCap; i++) {
          if (i < hiCount) blipColors.push(alertRGB);
          else if (i < hiCount + suspCount) blipColors.push(warnRGB);
          else blipColors.push(safeRGB);
        }
        blipColors.forEach((rgb, i) => {
          const ang = i * 2.39996 + 0.4;
          const dist = R * (0.4 + ((i * 37) % 52) / 100);
          const bx = cx + Math.cos(ang) * dist;
          const by = cy + Math.sin(ang) * dist;
          const angDiff = Math.abs((((sweepAngle - ang) % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2));
          const highlight = angDiff < 0.65 ? 1 : 0.48;
          ctx.beginPath();
          ctx.arc(bx, by, 6.5 * highlight, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${rgb}, ${(0.22 * highlight).toFixed(2)})`;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(bx, by, 3, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${rgb}, ${Math.min(1, 0.55 + 0.45 * highlight).toFixed(2)})`;
          ctx.fill();
        });
      }
      ctx.restore();

      // Center holographic shield
      drawShield(ctx, cx, cy, R * 0.34, cyanRGB, "59, 130, 246", isDark, true);
    };

    const drawAuthSphere = (
      elapsed: number,
      isDark: boolean,
      cyanRGB: string,
      tealRGB: string,
      blueRGB: string,
    ) => {
      const cx = width * 0.5;
      const cy = height * 0.5;
      const R = Math.min(width, height) * 0.35;

      const p = pointerRef.current;
      p.x += (p.targetX - p.x) * 0.06;
      p.y += (p.targetY - p.y) * 0.06;

      // Deep volumetric radial illumination behind sphere
      const glow = ctx.createRadialGradient(cx, cy, R * 0.05, cx, cy, R * 1.55);
      glow.addColorStop(0, `rgba(${cyanRGB}, ${isDark ? 0.28 : 0.16})`);
      glow.addColorStop(0.45, `rgba(${blueRGB}, ${isDark ? 0.14 : 0.08})`);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.55, 0, Math.PI * 2);
      ctx.fill();

      // Subtle precision radar compass perimeter + degree tick marks
      const outerR = R * 1.32;
      ctx.beginPath();
      ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.14 : 0.18})`;
      ctx.lineWidth = 1;
      ctx.stroke();

      for (let t = 0; t < 36; t++) {
        const ang = (t / 36) * Math.PI * 2 + elapsed * 0.03;
        const innerTick = outerR - (t % 3 === 0 ? 7 : 3);
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(ang) * innerTick, cy + Math.sin(ang) * innerTick);
        ctx.lineTo(cx + Math.cos(ang) * outerR, cy + Math.sin(ang) * outerR);
        ctx.strokeStyle = `rgba(${cyanRGB}, ${t % 3 === 0 ? (isDark ? 0.36 : 0.4) : (isDark ? 0.15 : 0.18)})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Sweeping radar beam wedge around perimeter
      const sweep = elapsed * 0.55;
      const wedge = Math.PI * 0.34;
      for (let s = 0; s < 14; s++) {
        const a0 = sweep - (s / 14) * wedge;
        const a1 = sweep - ((s + 1) / 14) * wedge;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, outerR, a1, a0);
        ctx.closePath();
        ctx.fillStyle = `rgba(${cyanRGB}, ${(1 - s / 14) * (isDark ? 0.085 : 0.06)})`;
        ctx.fill();
      }
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(sweep) * outerR, cy + Math.sin(sweep) * outerR);
      ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.52 : 0.45})`;
      ctx.lineWidth = 1.25;
      ctx.stroke();

      // Ambient drifting micro-particles around outer orbital zone
      for (let k = 0; k < 22; k++) {
        const baseA = k * 2.39996 + elapsed * (k % 2 === 0 ? 0.05 : -0.04);
        const dist = outerR * (1.06 + ((k * 17) % 24) / 100);
        const px = cx + Math.cos(baseA) * dist;
        const py = cy + Math.sin(baseA) * dist;
        const pulse = 0.4 + 0.6 * Math.abs(Math.sin(elapsed * 0.8 + k));
        ctx.beginPath();
        ctx.arc(px, py, 1.3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${k % 3 === 0 ? tealRGB : cyanRGB}, ${(pulse * (isDark ? 0.48 : 0.36)).toFixed(3)})`;
        ctx.fill();
      }

      // Smooth 3D rotation
      const rotY = elapsed * 0.16 + p.x;
      const rotX = 0.24 + Math.sin(elapsed * 0.26) * 0.05 - p.y;
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);
      const fov = 3.2;

      const projectPoint = (px: number, py: number, pz: number) => {
        const x1 = px * cosY - pz * sinY;
        const z1 = px * sinY + pz * cosY;
        const y2 = py * cosX - z1 * sinX;
        const z2 = py * sinX + z1 * cosX;
        const persp = fov / (fov - z2);
        return { sx: cx + x1 * R * persp, sy: cy + y2 * R * persp, x3: x1, y3: y2, z3: z2 };
      };

      const projected = AUTH_NODES.map((pt) => ({ ...projectPoint(pt.x, pt.y, pt.z), ring: pt.ring }));

      // Synaptic links weighted cleanly by depth
      const linkDist = 0.46;
      const maxDistSq = linkDist * linkDist;
      ctx.lineWidth = 0.8;
      for (let i = 0; i < projected.length; i++) {
        const a = projected[i]!;
        for (let j = i + 1; j < projected.length; j++) {
          const b = projected[j]!;
          const dx = a.x3 - b.x3;
          const dy = a.y3 - b.y3;
          const dz = a.z3 - b.z3;
          const dSq = dx * dx + dy * dy + dz * dz;
          if (dSq < maxDistSq) {
            const depthAvg = (a.z3 + b.z3) * 0.5;
            const distFactor = 1 - Math.sqrt(dSq) / linkDist;
            const depthAlpha = Math.max(0.05, (depthAvg + 1.15) * 0.5);
            const alpha = distFactor * depthAlpha * (isDark ? 0.3 : 0.32);
            ctx.strokeStyle = `rgba(${cyanRGB}, ${alpha.toFixed(3)})`;
            ctx.beginPath();
            ctx.moveTo(a.sx, a.sy);
            ctx.lineTo(b.sx, b.sy);
            ctx.stroke();
          }
        }
      }

      // Dual tilted luminous orbital rings with orbiting satellite beacons
      const drawOrbitWithBeacon = (tiltX: number, tiltZ: number, scaleR: number, speed: number, rgb: string, alpha: number) => {
        ctx.save();
        ctx.beginPath();
        const segs = 80;
        for (let i = 0; i <= segs; i++) {
          const t = (i / segs) * Math.PI * 2;
          const rx = Math.cos(t) * scaleR;
          const ry = Math.sin(t) * tiltX + Math.cos(t) * tiltZ;
          const rz = Math.sin(t) * scaleR;
          const p3 = projectPoint(rx, ry, rz);
          if (i === 0) ctx.moveTo(p3.sx, p3.sy);
          else ctx.lineTo(p3.sx, p3.sy);
        }
        ctx.strokeStyle = `rgba(${rgb}, ${alpha})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Orbiting satellite pulse
        const bt = elapsed * speed;
        const bx = Math.cos(bt) * scaleR;
        const by = Math.sin(bt) * tiltX + Math.cos(bt) * tiltZ;
        const bz = Math.sin(bt) * scaleR;
        const bp = projectPoint(bx, by, bz);
        ctx.beginPath();
        ctx.arc(bp.sx, bp.sy, 5.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${isDark ? 0.25 : 0.2})`;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(bp.sx, bp.sy, 2.3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, 0.95)`;
        ctx.fill();
        ctx.restore();
      };

      drawOrbitWithBeacon(0.42, 0.14, 1.18, 0.65, cyanRGB, isDark ? 0.36 : 0.36);
      drawOrbitWithBeacon(-0.36, 0.22, 1.24, -0.45, "139, 92, 246", isDark ? 0.28 : 0.28);

      // Back hemisphere nodes
      const sorted = [...projected].sort((a, b) => a.z3 - b.z3);
      for (const node of sorted) {
        if (node.z3 >= 0.04) continue;
        const depthNorm = (node.z3 + 1) * 0.5;
        const alpha = 0.2 + depthNorm * 0.62;
        const size = 1.4 + depthNorm * 1.7;
        const rgb = node.ring > 0.62 ? tealRGB : cyanRGB;
        ctx.beginPath();
        ctx.arc(node.sx, node.sy, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${alpha.toFixed(3)})`;
        ctx.fill();
      }

      // Centered holographic shield nested inside the 3D sphere
      drawShield(ctx, cx, cy, R * 0.56, cyanRGB, blueRGB, isDark, true);

      // Front hemisphere nodes passing cleanly in front of the shield
      for (const node of sorted) {
        if (node.z3 < 0.04) continue;
        const depthNorm = (node.z3 + 1) * 0.5;
        const alpha = 0.3 + depthNorm * 0.65;
        const size = 1.6 + depthNorm * 2.0;
        const rgb = node.ring > 0.62 ? tealRGB : cyanRGB;
        ctx.beginPath();
        ctx.arc(node.sx, node.sy, size * 2.0, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${(alpha * 0.2).toFixed(3)})`;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(node.sx, node.sy, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${alpha.toFixed(3)})`;
        ctx.fill();
      }
    };

    const drawGlobeHeroOrCommand = (
      elapsed: number,
      isDark: boolean,
      cyanRGB: string,
      tealRGB: string,
      blueRGB: string,
      warnRGB: string,
      alertRGB: string,
    ) => {
      const isHero = mode === "hero";
      const cx = width * 0.5;
      const cy = isHero ? height * 0.46 : height * 0.5;
      const minDim = Math.min(width, height);
      const R = minDim * (isHero ? 0.36 : 0.34);

      const p = pointerRef.current;
      p.x += (p.targetX - p.x) * 0.06;
      p.y += (p.targetY - p.y) * 0.06;

      // Flowing cyan particle wave floor on Hero mode
      if (isHero) {
        const rows = 5;
        const cols = 38;
        const baseY = height * 0.84;
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const nx = c / (cols - 1);
            const x = nx * width;
            const wave = Math.sin(nx * 6.5 + elapsed * 0.9 + r * 0.7) * 10 + Math.cos(nx * 3.2 - elapsed * 0.5) * 6;
            const y = baseY + r * 7 + wave;
            const edgeFade = Math.sin(nx * Math.PI);
            const alpha = edgeFade * (1 - r / rows) * (isDark ? 0.48 : 0.3);
            ctx.beginPath();
            ctx.arc(x, y, 1.35, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${cyanRGB}, ${alpha.toFixed(3)})`;
            ctx.fill();
          }
        }
      }

      // Atmospheric sphere bloom
      const glow = ctx.createRadialGradient(cx, cy, R * 0.06, cx, cy, R * 1.5);
      glow.addColorStop(0, `rgba(${cyanRGB}, ${isDark ? 0.28 : 0.16})`);
      glow.addColorStop(0.5, `rgba(${blueRGB}, ${isDark ? 0.13 : 0.07})`);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.5, 0, Math.PI * 2);
      ctx.fill();

      // Outer faint halo ring
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.18, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.16 : 0.2})`;
      ctx.lineWidth = 1;
      ctx.stroke();

      // 3D sphere rotation
      const speedY = active ? 0.45 : isHero ? 0.19 : 0.24;
      const rotY = elapsed * speedY + p.x;
      const rotX = 0.26 + Math.sin(elapsed * 0.3) * 0.06 - p.y;
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);
      const fov = 3.1;

      const nodes = isHero ? HERO_NODES : CORE_NODES;
      const projected = nodes.map((pt) => {
        const x1 = pt.x * cosY - pt.z * sinY;
        const z1 = pt.x * sinY + pt.z * cosY;
        const y2 = pt.y * cosX - z1 * sinX;
        const z2 = pt.y * sinX + z1 * cosX;
        const perspective = fov / (fov - z2);
        return {
          sx: cx + x1 * R * perspective,
          sy: cy + y2 * R * perspective,
          x3: x1,
          y3: y2,
          z3: z2,
          ring: pt.ring,
        };
      });

      // Synaptic links
      const linkDist = isHero ? 0.5 : 0.62;
      const maxDistSq = linkDist * linkDist;
      ctx.lineWidth = 0.85;
      for (let i = 0; i < projected.length; i++) {
        const a = projected[i]!;
        for (let j = i + 1; j < projected.length; j++) {
          const b = projected[j]!;
          const dx = a.x3 - b.x3;
          const dy = a.y3 - b.y3;
          const dz = a.z3 - b.z3;
          const dSq = dx * dx + dy * dy + dz * dz;
          if (dSq < maxDistSq) {
            const depthAvg = (a.z3 + b.z3) * 0.5;
            const distFactor = 1 - Math.sqrt(dSq) / linkDist;
            const depthAlpha = Math.max(0.06, (depthAvg + 1.2) * 0.5);
            const alpha = distFactor * depthAlpha * (isDark ? 0.32 : 0.35);
            ctx.strokeStyle = `rgba(${cyanRGB}, ${alpha.toFixed(3)})`;
            ctx.beginPath();
            ctx.moveTo(a.sx, a.sy);
            ctx.lineTo(b.sx, b.sy);
            ctx.stroke();
          }
        }
      }

      // Tilted orbital rings
      const drawOrbit = (tilt: number, scaleR: number, rgb: string, alpha: number) => {
        ctx.save();
        ctx.beginPath();
        const segs = 72;
        for (let i = 0; i <= segs; i++) {
          const t = (i / segs) * Math.PI * 2;
          const rx = Math.cos(t) * scaleR;
          const ry = Math.sin(t) * tilt;
          const rz = Math.sin(t) * scaleR;
          const x1 = rx * cosY - rz * sinY;
          const z1 = rx * sinY + rz * cosY;
          const y2 = ry * cosX - z1 * sinX;
          const z2 = ry * sinX + z1 * cosX;
          const persp = fov / (fov - z2);
          const sx = cx + x1 * R * persp;
          const sy = cy + y2 * R * persp;
          if (i === 0) ctx.moveTo(sx, sy);
          else ctx.lineTo(sx, sy);
        }
        ctx.strokeStyle = `rgba(${rgb}, ${alpha})`;
        ctx.lineWidth = 1.15;
        ctx.stroke();
        ctx.restore();
      };

      drawOrbit(0.35, 1.14, cyanRGB, isDark ? 0.34 : 0.38);
      if (isHero) drawOrbit(-0.32, 1.22, "139, 92, 246", isDark ? 0.28 : 0.28);

      // Back half of sphere nodes
      const sorted = [...projected].sort((a, b) => a.z3 - b.z3);
      for (const node of sorted) {
        if (isHero && node.z3 >= 0.05) continue;
        const depthNorm = (node.z3 + 1) * 0.5;
        const alpha = 0.22 + depthNorm * 0.68;
        const size = 1.5 + depthNorm * 1.9;
        let rgb = cyanRGB;
        if (clampedThreat > 0 && node.ring < clampedThreat * 0.72) {
          rgb = clampedThreat >= 0.45 ? alertRGB : warnRGB;
        } else if (node.ring > 0.66) {
          rgb = tealRGB;
        }
        ctx.beginPath();
        ctx.arc(node.sx, node.sy, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${alpha.toFixed(3)})`;
        ctx.fill();
      }

      // Holographic Shield centerpiece inside Hero globe
      if (isHero) {
        drawShield(ctx, cx, cy, R * 0.62, cyanRGB, blueRGB, isDark, true);
      }

      // Front half of sphere nodes (passes in front of shield for true 3D depth)
      for (const node of sorted) {
        if (!isHero) break;
        if (node.z3 < 0.05) continue;
        const depthNorm = (node.z3 + 1) * 0.5;
        const alpha = 0.28 + depthNorm * 0.68;
        const size = 1.7 + depthNorm * 2.1;
        const rgb = node.ring > 0.66 ? tealRGB : cyanRGB;
        ctx.beginPath();
        ctx.arc(node.sx, node.sy, size * 2.1, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${(alpha * 0.22).toFixed(3)})`;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(node.sx, node.sy, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${alpha.toFixed(3)})`;
        ctx.fill();
      }
    };

    const renderFrame = (now: number) => {
      const isDark = document.documentElement.classList.contains("dark");
      const elapsed = reduceMotion ? 0 : (now - startTime) / 1000;
      ctx.clearRect(0, 0, width, height);

      const cyanRGB = isDark ? "0, 229, 255" : "8, 145, 178";
      const tealRGB = isDark ? "45, 212, 191" : "13, 148, 136";
      const blueRGB = isDark ? "59, 130, 246" : "37, 99, 235";
      const safeRGB = isDark ? "34, 197, 94" : "22, 163, 74";
      const warnRGB = isDark ? "245, 158, 11" : "217, 119, 6";
      const alertRGB = isDark ? "239, 68, 68" : "220, 38, 38";

      if (mode === "scanning") {
        drawScanning(elapsed, isDark, cyanRGB, tealRGB);
      } else if (mode === "radar") {
        drawRadar(elapsed, isDark, cyanRGB, safeRGB, warnRGB, alertRGB);
      } else if (mode === "auth") {
        drawAuthSphere(elapsed, isDark, cyanRGB, tealRGB, blueRGB);
      } else {
        drawGlobeHeroOrCommand(elapsed, isDark, cyanRGB, tealRGB, blueRGB, warnRGB, alertRGB);
      }
    };

    const loop = (now: number) => {
      if (document.visibilityState === "visible") {
        renderFrame(now);
      }
      if (!reduceMotion) {
        rafId = requestAnimationFrame(loop);
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        startTime = performance.now();
        renderFrame(startTime);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    renderFrame(startTime);
    if (!reduceMotion) {
      rafId = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(rafId);
      ro?.disconnect();
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerleave", onPointerLeave);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [mode, threatRatio, counts, active]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={cn("block h-full w-full touch-none select-none", className)}
    />
  );
}
