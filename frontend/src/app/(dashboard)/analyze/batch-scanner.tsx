"use client";

import { useState, useCallback, useEffect, memo } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";

const ScanTabs = dynamic(() => import("@/components/dashboard/scan-tabs").then(mod => mod.ScanTabs), { ssr: false });
const VerdictCard = dynamic(() => import("@/components/analysis/verdict-card").then(mod => mod.VerdictCard), { ssr: false });
import { scanFile, submitFeedback, ApiError } from "@/lib/api/messages";
import { useToast } from "@/hooks/use-toast";
import { Alert } from "@/components/ui/alert";
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

  return (
    <div className="flex flex-col gap-8">
      <ScanTabs onScan={handleScan} isScanning={isScanning} />

      {isScanning && (
        <div className="flex items-center gap-4 bg-card border border-border px-6 py-4 rounded-xl">
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 animate-spin rounded-full border-b-2 border-primary" />
            <span className="font-medium" role="status">Analyzing evidence…</span>
          </div>
          <span className="text-sm font-medium text-muted-foreground ml-auto">
            Item {currentIndex + 1} of {items.length}
          </span>
        </div>
      )}

      {items.some((i) => i.status === "done" || i.status === "error") && (
        <div className="space-y-6">
          <h2 className="text-xl font-semibold tracking-tight border-b pb-2">Results</h2>
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
                    <div className="text-sm font-medium text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-md inline-block w-fit">
                      Input: {item.file ? item.file.name : item.text ? (item.text.length > 50 ? item.text.substring(0, 50) + "..." : item.text) : "Scanned message"}
                    </div>

                    {item.status === "error" && (
                      <Alert variant="error">{item.error || "This item could not be scanned."}</Alert>
                    )}

                    {item.status === "done" && item.result && (
                      <VerdictCard 
                        result={item.result} 
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
