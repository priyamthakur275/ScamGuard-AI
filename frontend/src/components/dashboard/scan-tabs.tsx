"use client";

import { useState, useRef } from "react";
import { FileText, Link as LinkIcon, Mail, Image as ImageIcon, File, QrCode, Camera, Mic } from "lucide-react";
import { FileUploadZone } from "./file-upload-zone";
import { CameraScanner } from "./camera-scanner";
import { VoiceScanner } from "./voice-scanner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";

import { useAuth } from "@/lib/auth/auth-context";
import { useModKeyLabel } from "@/lib/platform";

interface ScanTabsProps {
  onScan: (texts: string[], files: File[], inputType: string) => void;
  isScanning?: boolean;
}

const TABS = [
  { id: "text", label: "Text", icon: FileText, type: "text" },
  { id: "url", label: "URL", icon: LinkIcon, type: "url" },
  { id: "email", label: "Email", icon: Mail, type: "email" },
  { id: "image", label: "Image / OCR", icon: ImageIcon, type: "image" },
  { id: "camera", label: "Live Camera", icon: Camera, type: "camera" },
  { id: "voice", label: "Voice Call", icon: Mic, type: "voice" },
  { id: "pdf", label: "PDF", icon: File, type: "pdf" },
  { id: "qr", label: "QR Code", icon: QrCode, type: "qr" },
];

export function ScanTabs({ onScan, isScanning = false }: ScanTabsProps) {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(() => {
    const preferred = String(user?.preferences?.default_channel || "text");
    return TABS.some(t => t.id === preferred) ? preferred : "text";
  });
  const [textValue, setTextValue] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const modKey = useModKeyLabel();

  const isFileTab = ["image", "pdf", "qr"].includes(activeTab);
  const isCameraTab = activeTab === "camera";
  const isVoiceTab = activeTab === "voice";

  const handleScan = () => {
    if (isScanning) return;
    if (isFileTab) {
      if (selectedFiles.length > 0) {
        onScan([], selectedFiles, activeTab);
      }
    } else if (!isCameraTab && !isVoiceTab) {
      if (textValue.trim()) {
        onScan([textValue.trim()], [], activeTab);
      }
    }
  };

  useKeyboardShortcuts({
    "mod+enter": (e) => {
      e.preventDefault();
      handleScan();
    },
  });

  return (
    <div className="scanner-panel w-full overflow-hidden rounded-lg border border-border bg-card">
      <div className="border-b border-border bg-muted/30 px-3 pt-4 pb-2"><p className="console-kicker px-2 pb-3">Investigation input</p><div className="scanner-tabs">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              aria-pressed={isActive}
              disabled={isScanning}
              onClick={() => {
                setActiveTab(tab.id);
                setTextValue("");
                setSelectedFiles([]);
              }}
                className={`flex items-center space-x-2 whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                isActive
                  ? "border-primary bg-primary/5 font-semibold text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              </button>
          );
        })}
      </div></div>

      <div className="p-4 md:p-7">
        {isCameraTab ? (
          <CameraScanner
            onCapture={(file) => onScan([], [file], "image")}
            isScanning={isScanning}
          />
        ) : isVoiceTab ? (
          <VoiceScanner
            onSubmitTranscript={(transcript) => onScan([transcript], [], "voice")}
            onSubmitAudioFile={(file) => onScan([], [file], "voice")}
            isScanning={isScanning}
          />
        ) : isFileTab ? (
          <div className="space-y-4">
            <FileUploadZone key={activeTab}
              onFilesSelected={setSelectedFiles}
              maxFiles={10}
              acceptedTypes={activeTab === "image" || activeTab === "qr" ? "image/*" : activeTab === "pdf" ? ".pdf" : "*/*"}
            />
          </div>
        ) : (
          <div className="space-y-4">
            <Textarea
              ref={textAreaRef}
              aria-label={`${activeTab} evidence`}
              maxLength={4000}
              placeholder={
                activeTab === "url"
                  ? "Paste the link to check, e.g. https://secure-bank-login.xyz"
                  : activeTab === "email"
                  ? "Paste the full email, including headers (From, Reply-To, Subject) if you have them"
                  : "Paste the suspicious SMS, WhatsApp message, or chat text"
              }
              className="min-h-[240px] resize-y border-border bg-background text-base leading-7 placeholder:text-muted-foreground"
              value={textValue}
              onChange={(e) => setTextValue(e.target.value)}
            />
          </div>
        )}

        {!isCameraTab && !isVoiceTab && (
          <div className="mt-5 flex justify-end border-t border-border pt-5">
            <Button
              onClick={handleScan}
              disabled={isScanning || (isFileTab ? selectedFiles.length === 0 : !textValue.trim())}
              size="lg"
              className="w-full sm:w-auto"
            >
              {isScanning ? "Scanning..." : (
                <>
                  Analyze evidence <kbd className="ml-2 hidden sm:inline-block rounded bg-primary-foreground/20 px-1.5 py-0.5 text-[10px] font-mono font-medium">{modKey} ↵</kbd>
                </>
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
