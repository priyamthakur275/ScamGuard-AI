"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Camera, CameraOff, RefreshCw, Shield, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

interface CameraScannerProps {
  onCapture: (file: File) => void;
  isScanning?: boolean;
}

export function CameraScanner({ onCapture, isScanning = false }: CameraScannerProps) {
  const [isActive, setIsActive] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [hasCamera, setHasCamera] = useState<boolean | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Check camera support on mount
  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") {
      setHasCamera(true);
    } else {
      setHasCamera(false);
    }
  }, []);

  // Stop camera helper
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsActive(false);
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  useEffect(() => {
    if (isActive && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      void videoRef.current.play().catch(() => setPermissionError("Camera playback failed. Stop and try again."));
    }
  }, [isActive]);

  // Start camera
  const startCamera = async () => {
    setPermissionError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      setIsActive(true);
    } catch (err: unknown) {
      const error = err as Error;
      if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
        setPermissionError(
          "Camera access was denied. Please allow camera permissions in your browser's address bar to use live scanning."
        );
      } else if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
        setPermissionError("No camera device was detected on your system.");
      } else {
        setPermissionError(`Could not access camera: ${error.message || "Unknown error"}`);
      }
      setIsActive(false);
    }
  };

  // Capture frame & submit to scan pipeline
  const handleCapture = () => {
    if (!videoRef.current || isScanning) return;

    const video = videoRef.current;
    if (!video.videoWidth || video.readyState < 2) {
      setPermissionError("The camera is still starting. Wait for a live frame before capturing.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], `camera-scan-${Date.now()}.png`, { type: "image/png" });
        onCapture(file);
        stopCamera();
      },
      "image/png",
      0.95
    );
  };

  if (hasCamera === false) {
    return (
      <div className="rounded-xl border border-border/80 bg-muted/20 p-8 text-center">
        <CameraOff className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
        <h3 className="font-semibold text-base mb-1">Camera Not Supported</h3>
        <p className="text-sm text-muted-foreground max-w-sm mx-auto">
          Your current browser environment does not support media device capture. You can still upload images directly using the Image tab.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {permissionError && (
        <Alert variant="error" className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{permissionError}</span>
        </Alert>
      )}

      {!isActive ? (
        <div className="rounded-xl border border-dashed border-border/80 bg-muted/10 p-8 text-center flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
            <Camera className="w-6 h-6" />
          </div>
          <div className="max-w-md">
            <h3 className="font-semibold text-base mb-1">Live Optical / QR Scanner</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Use your device camera to scan physical letters, printed QR codes, or SMS text displayed on another phone or screen.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3 mt-2">
            <Button type="button" onClick={startCamera} className="gap-2">
              <Camera className="w-4 h-4" />
              Enable Camera & Start
            </Button>
          </div>

          <div className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground text-left max-w-md flex items-start gap-2 mt-2 border border-border/40">
            <Shield className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
            <span>
              <strong>Privacy Assurance:</strong> Live video is rendered strictly inside your local browser. Frames are only sent to the server when you explicitly click Capture, and are processed in-memory for OCR text extraction without biometric storage.
            </span>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">
          {/* Viewfinder Frame */}
          <div className="relative w-full max-w-lg aspect-video rounded-xl overflow-hidden bg-black border-2 border-primary">
            <video
              ref={videoRef}
              playsInline
              muted
              className="w-full h-full object-cover"
            />
            {/* Viewfinder Target Overlay */}
            <div className="absolute inset-0 pointer-events-none flex items-center justify-center p-6">
              <div className="w-3/4 h-3/4 border-2 border-dashed border-white/70 rounded-xl relative">
                <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-primary -translate-x-1 -translate-y-1" />
                <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-primary translate-x-1 -translate-y-1" />
                <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-primary -translate-x-1 translate-y-1" />
                <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-primary translate-x-1 translate-y-1" />
              </div>
            </div>
            <div className="absolute bottom-3 left-3 bg-black/60 backdrop-blur-sm text-white px-2.5 py-1 rounded-full text-xs flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              Live Camera Feed
            </div>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={stopCamera}
              disabled={isScanning}
              className="gap-1.5"
            >
              <CameraOff className="w-4 h-4" />
              Stop Camera
            </Button>
            <Button
              type="button"
              size="md"
              onClick={handleCapture}
              isLoading={isScanning}
              className="gap-2 bg-primary text-primary-foreground font-semibold px-6 shadow-md"
            >
              <RefreshCw className="w-4 h-4" />
              Capture & Scan Text
            </Button>
          </div>
          <span className="text-xs text-muted-foreground">
            Align the document, letter, or screen within the viewfinder, then click Capture.
          </span>
        </div>
      )}
    </div>
  );
}
