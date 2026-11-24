"use client";

import { ScanProgress } from "@/components/analysis/demo-polish";
import { useState, useCallback, memo } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import { RotateCcw } from "lucide-react";

const ScanTabs = dynamic(() => import("@/components/dashboard/scan-tabs").then(mod => mod.ScanTabs), { ssr: false });
const VerdictCard = dynamic(() => import("@/components/analysis/verdict-card").then(mod => mod.VerdictCard), { ssr: false });
import { scanFile, submitFeedback, ApiError } from "@/lib/api/messages";
import { useToast } from "@/hooks/use-toast";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { AnalysisResult } from "@/types";

interface ScanItem {
  id: string;
  file?: File;
  text?: string;
  inputType: string;
  status: "pending" | "scanning" | "done" | "error";
  result?: AnalysisResult;
  error?: string;
}

export const BatchScanner = memo(function BatchScanner() {
  const { toast } = useToast();
  const [items, setItems] = useState<ScanItem[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [channel, setChannel] = useState("text");

  const handleScan = useCallback(async (texts: string[], files: File[], inputType: string) => {
    const newItems: ScanItem[] = [];
    
    texts.forEach((text) => {
      newItems.push({
        id: crypto.randomUUID(),
        text,
        inputType,
        status: "pending",
      });
    });

    files.forEach((file) => {
      newItems.push({
        id: crypto.randomUUID(),
        file,
        inputType,
        status: "pending",
      });
    });

    if (newItems.length === 0) return;

    setItems(newItems);
    setIsScanning(true);
    setChannel(inputType);
    setCurrentIndex(0);

    let completed = 0;
    for (let i = 0; i < newItems.length; i++) {
      setCurrentIndex(i);
      const item = newItems[i]!;
      
      setItems((prev) => 
        prev.map((p, idx) => idx === i ? { ...p, status: "scanning" } : p)
      );

      try {
        const result = await scanFile(item.file || null, item.text || null, item.inputType);
        completed++;
        setItems((prev) => 
          prev.map((p, idx) => idx === i ? { ...p, status: "done", result } : p)
        );
      } catch (err) {
        // Show the real failure -- never substitute a fabricated result.
        const message =
          err instanceof ApiError
            ? err.message
            : "Scan failed. The scam-detection service may be temporarily unavailable.";
        setItems((prev) => 
          prev.map((p, idx) => idx === i ? { ...p, status: "error", error: message } : p)
        );
      }
    }

    setIsScanning(false);
    toast({ title: `${completed} of ${newItems.length} evidence items analyzed`, variant: completed === newItems.length ? "success" : "error" });
  }, [toast]);

  const handleFeedback = useCallback(async (itemId: string, predictionId: string, isAccurate: boolean) => {
    try {
      const updated = await submitFeedback(predictionId, isAccurate);
      setItems((prev) =>
        prev.map((item) =>
          item.id === itemId && item.result
            ? { ...item, result: updated }
            : item
        )
      );
      toast({ title: "Feedback saved", variant: "success" });
    } catch {
      toast({ title: "Feedback couldn't be saved. Please try again.", variant: "error" });
    }
  }, [toast]);

  const handleReset = useCallback(() => {
    setItems([]);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, []);

  const hasCompleted = items.some((i) => i.status === "done" || i.status === "error");

  return (
    <div className="flex flex-col gap-8">
      {!isScanning && !hasCompleted && <ScanTabs onScan={handleScan} isScanning={isScanning} />}

      {isScanning && (
        <ScanProgress channel={channel} label={items.length > 1 ? `Item ${currentIndex + 1} of ${items.length}` : undefined} />
      )}

      {hasCompleted && (
        <div className="space-y-6">
          <div className="flex flex-col gap-8">
            <AnimatePresence>
              {items.map((item) => {
                if (item.status === "pending" || item.status === "scanning") {
                  return null;
                }

                return (
                  <motion.div
                    key={item.id}
                    className="flex flex-col gap-3"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 300, damping: 24 }}
                  >
                    {item.status === "error" && (
                      <Alert variant="error">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <span>{item.error || "This item could not be scanned."}</span>
                          <Button variant="outline" size="sm" onClick={handleReset}>
                            <RotateCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                            Scan Another
                          </Button>
                        </div>
                      </Alert>
                    )}

                    {item.status === "done" && item.result && (
                      <VerdictCard
                        result={item.result}
                        onScanAnother={handleReset}
                        onFeedback={(isAccurate) => handleFeedback(item.id, item.result!.id, isAccurate)}
                      />
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
});
