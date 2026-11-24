"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

export interface ThreatCoreCanvasProps {
  /** Visual framing preset: hero backdrop, dashboard command deck, or compact live scan indicator. */
  mode?: "hero" | "command" | "scanning";
  /** Real threat proportion (0..1) from live scan history; never randomized. */
  threatRatio?: number;
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

const SPHERE_NODES = buildFibonacciSphere(46);

export function ThreatCoreCanvas({
  mode = "command",
  threatRatio = 0,
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
      pointerRef.current.targetX = Math.max(-1, Math.min(1, nx)) * 0.28;
      pointerRef.current.targetY = Math.max(-1, Math.min(1, ny)) * 0.22;
    };

    const onPointerLeave = () => {
      pointerRef.current.targetX = 0;
      pointerRef.current.targetY = 0;
    };

    canvas.addEventListener("pointermove", onPointerMove, { passive: true });
    canvas.addEventListener("pointerleave", onPointerLeave, { passive: true });

    let rafId = 0;
    let startTime = performance.now();

    const renderFrame = (now: number) => {
      const isDark = document.documentElement.classList.contains("dark");
      const elapsed = reduceMotion ? 0 : (now - startTime) / 1000;

      // Damped pointer tilt
      const p = pointerRef.current;
      p.x += (p.targetX - p.x) * 0.06;
      p.y += (p.targetY - p.y) * 0.06;

      ctx.clearRect(0, 0, width, height);

      const cx = width * 0.5;
      const cy = height * 0.5;
      const minDim = Math.min(width, height);
      const radiusScale = mode === "scanning" ? 0.36 : mode === "hero" ? 0.37 : 0.34;
      const R = minDim * radiusScale;

      // Palette tokens matching Obsidian Sentinel
      const cyanRGB = isDark ? "34, 211, 238" : "8, 145, 178";
      const tealRGB = isDark ? "45, 212, 191" : "13, 148, 136";
      const warnRGB = isDark ? "245, 158, 11" : "217, 119, 6";
      const alertRGB = isDark ? "244, 63, 94" : "220, 38, 38";

      // 1. Atmospheric core bloom
      const glow = ctx.createRadialGradient(cx, cy, R * 0.05, cx, cy, R * 1.45);
      glow.addColorStop(0, `rgba(${cyanRGB}, ${isDark ? 0.22 : 0.14})`);
      glow.addColorStop(0.45, `rgba(${tealRGB}, ${isDark ? 0.08 : 0.05})`);
      glow.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, R * 1.45, 0, Math.PI * 2);
      ctx.fill();

      // 2. Outer calibrated range rings
      const outerR = R * 1.24;
      ctx.save();
      ctx.strokeStyle = `rgba(${cyanRGB}, ${isDark ? 0.14 : 0.18})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
      ctx.stroke();

      // Cardinal ticks on outer ring
      for (let i = 0; i < 24; i++) {
        const ang = (i / 24) * Math.PI * 2;
        const len = i % 6 === 0 ? 7 : 3;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(ang) * (outerR - len), cy + Math.sin(ang) * (outerR - len));
        ctx.lineTo(cx + Math.cos(ang) * outerR, cy + Math.sin(ang) * outerR);
        ctx.strokeStyle = `rgba(${cyanRGB}, ${i % 6 === 0 ? (isDark ? 0.42 : 0.48) : (isDark ? 0.16 : 0.22)})`;
        ctx.stroke();
      }

      // 3. Radar sweep wedge
      const sweepSpeed = active || mode === "scanning" ? 1.55 : 0.55;
      const sweepAngle = elapsed * sweepSpeed;
      const wedgeSpan = Math.PI * 0.36;
      const wedgeSteps = 14;
      for (let s = 0; s < wedgeSteps; s++) {
        const t0 = sweepAngle - (s / wedgeSteps) * wedgeSpan;
        const t1 = sweepAngle - ((s + 1) / wedgeSteps) * wedgeSpan;
        const alpha = (1 - s / wedgeSteps) * (active ? 0.16 : 0.09);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, outerR * 0.99, t1, t0);
        ctx.closePath();
        ctx.fillStyle = `rgba(${cyanRGB}, ${alpha})`;
        ctx.fill();
      }
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(sweepAngle) * outerR, cy + Math.sin(sweepAngle) * outerR);
      ctx.strokeStyle = `rgba(${cyanRGB}, ${active ? 0.68 : 0.42})`;
      ctx.lineWidth = 1.25;
      ctx.stroke();

      // Active scanning pulse ring
      if ((active || mode === "scanning") && !reduceMotion) {
        const pulseT = (elapsed * 0.75) % 1;
        const pulseR = R * 0.25 + pulseT * (outerR - R * 0.25);
        ctx.beginPath();
        ctx.arc(cx, cy, pulseR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${tealRGB}, ${(1 - pulseT) * 0.45})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      ctx.restore();

      // 4. 3D Lattice projection
      const speedY = active || mode === "scanning" ? 0.48 : 0.22;
      const rotY = elapsed * speedY + p.x;
      const rotX = 0.28 + Math.sin(elapsed * 0.3) * 0.08 - p.y;
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);

      const fov = 3.1;
      const projected = SPHERE_NODES.map((pt) => {
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
          perspective,
          ring: pt.ring,
        };
      });

      // Synaptic links between neighboring 3D nodes
      const maxDistSq = 0.62 * 0.62;
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
            const distFactor = 1 - Math.sqrt(dSq) / 0.62;
            const depthAlpha = Math.max(0.06, (depthAvg + 1.2) * 0.5);
            const alpha = distFactor * depthAlpha * (isDark ? 0.34 : 0.38);
            ctx.strokeStyle = `rgba(${cyanRGB}, ${alpha.toFixed(3)})`;
            ctx.beginPath();
            ctx.moveTo(a.sx, a.sy);
            ctx.lineTo(b.sx, b.sy);
            ctx.stroke();
          }
        }
      }

      // Draw tilted orbital ring (3D projected ellipse)
      ctx.save();
      ctx.beginPath();
      const ringSegs = 64;
      for (let i = 0; i <= ringSegs; i++) {
        const t = (i / ringSegs) * Math.PI * 2;
        const rx = Math.cos(t) * 1.12;
        const ry = Math.sin(t) * 0.36;
        const rz = Math.sin(t) * 1.06;
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
      ctx.strokeStyle = `rgba(${tealRGB}, ${isDark ? 0.28 : 0.32})`;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();

      // Sort nodes back-to-front so front nodes render crisply over back nodes
      const sorted = [...projected].sort((a, b) => a.z3 - b.z3);
      for (const node of sorted) {
        const depthNorm = (node.z3 + 1) * 0.5; // 0 (back) .. 1 (front)
        const alpha = 0.24 + depthNorm * 0.72;
        const size = (1.6 + depthNorm * 2.0) * (mode === "scanning" ? 0.85 : 1);

        // Proportional semantic coloring strictly driven by real threatRatio
        let rgb = cyanRGB;
        if (clampedThreat > 0 && node.ring < clampedThreat * 0.75) {
          rgb = clampedThreat >= 0.45 ? alertRGB : warnRGB;
        } else if (node.ring > 0.72) {
          rgb = tealRGB;
        }

        if (depthNorm > 0.65) {
          ctx.beginPath();
          ctx.arc(node.sx, node.sy, size * 2.3, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${rgb}, ${(alpha * 0.2).toFixed(3)})`;
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(node.sx, node.sy, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${alpha.toFixed(3)})`;
        ctx.fill();
      }

      // Inner core focal shield node
      ctx.beginPath();
      ctx.arc(cx, cy, mode === "scanning" ? 4.5 : 5.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${cyanRGB}, ${isDark ? 0.92 : 0.85})`;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(cx, cy, mode === "scanning" ? 11 : 14, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${cyanRGB}, 0.35)`;
      ctx.lineWidth = 1;
      ctx.stroke();
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
  }, [mode, threatRatio, active]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={cn("block h-full w-full touch-none select-none", className)}
    />
  );
}
