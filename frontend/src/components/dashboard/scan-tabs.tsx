"use client";

import { ExampleChips } from "@/components/analysis/demo-polish";
import { useState, useRef } from "react";
import { FileText, Link as LinkIcon, Mail, Image as ImageIcon, File, QrCode, Mic, ShieldCheck } from "lucide-react";
import { FileUploadZone } from "./file-upload-zone";
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
  { id: "text", label: "Message / Text", icon: FileText, type: "text" },
  { id: "url", label: "URL", icon: LinkIcon, type: "url" },
  { id: "email", label: "Email", icon: Mail, type: "email" },
  { id: "image", label: "Screenshot", icon: ImageIcon, type: "image" },
  { id: "voice", label: "Voice Call", icon: Mic, type: "voice" },
  { id: "pdf", label: "PDF", icon: File, type: "pdf" },
  { id: "qr", label: "QR Code", icon: QrCode, type: "qr" },
];

export function ScanTabs({ onScan, isScanning = false }: ScanTabsProps) {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(() => {
    const preferred = String(user?.preferences?.default_channel || "text");
    return TABS.some((t) => t.id === preferred) ? preferred : "text";
  });
  const [textValue, setTextValue] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const modKey = useModKeyLabel();

  const isFileTab = ["image", "pdf", "qr"].includes(activeTab);
  const isVoiceTab = activeTab === "voice";
  const isUrlTab = activeTab === "url";

  const handleScan = () => {
    if (isScanning) return;
    if (isFileTab) {
      if (selectedFiles.length > 0) {
        onScan([], selectedFiles, activeTab);
      }
    } else if (!isVoiceTab) {
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
    <div className="scanner-panel w-full overflow-hidden">
      <div className="border-b border-border bg-muted/25 px-3 pb-2 pt-3">
        <div className="scanner-tabs">
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
                className={`flex items-center space-x-2 whitespace-nowrap px-3.5 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "font-semibold text-foreground"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="p-4 md:p-7">
        {isVoiceTab ? (
          <VoiceScanner
            onSubmitTranscript={(transcript) => onScan([transcript], [], "voice")}
            isScanning={isScanning}
          />
        ) : isFileTab ? (
          <div className="space-y-4">
            <FileUploadZone
              key={activeTab}
              onFilesSelected={setSelectedFiles}
              maxFiles={10}
              acceptedTypes={activeTab === "image" || activeTab === "qr" ? "image/*" : activeTab === "pdf" ? ".pdf" : "*/*"}
            />
          </div>
        ) : isUrlTab ? (
          <div className="space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
              <input
                type="url"
                aria-label="URL evidence"
                maxLength={2000}
                placeholder="https://example-verify-login.xyz/claim-reward"
                className="h-12 flex-1 border border-border bg-background/85 px-4 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                value={textValue}
                onChange={(e) => setTextValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleScan();
                  }
                }}
              />
              <Button
                onClick={handleScan}
                disabled={isScanning || !textValue.trim()}
                size="lg"
                className="h-12 shrink-0 px-7"
              >
                <ShieldCheck className="mr-1.5 h-4 w-4" aria-hidden="true" />
                {isScanning ? "Scanning…" : "Scan Now"}
              </Button>
            </div>
            <ExampleChips
              channel="url"
              disabled={isScanning}
              onPick={(text) => {
                setTextValue(text);
                onScan([text], [], "url");
              }}
            />
          </div>
        ) : (
          <div className="space-y-4">
            <Textarea
              ref={textAreaRef}
              aria-label={`${activeTab} evidence`}
              maxLength={4000}
              placeholder={
                activeTab === "email"
                  ? "Paste the full email, including headers (From, Reply-To, Subject) if you have them"
                  : "Paste the suspicious SMS, WhatsApp message, or chat text"
              }
              className="min-h-[220px] resize-y border-border bg-background/85 text-base leading-7 placeholder:text-muted-foreground"
              value={textValue}
              onChange={(e) => setTextValue(e.target.value)}
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <ExampleChips
                channel={activeTab}
                disabled={isScanning}
                onPick={(text) => {
                  setTextValue(text);
                  onScan([text], [], activeTab);
                }}
              />
              <span className="ml-auto font-mono text-[11px] tabular-nums text-muted-foreground">
                {textValue.length}/4000
              </span>
            </div>
          </div>
        )}

        {!isVoiceTab && !isUrlTab && (
          <div className="mt-5 flex justify-end border-t border-border pt-5">
            <Button
              onClick={handleScan}
              disabled={isScanning || (isFileTab ? selectedFiles.length === 0 : !textValue.trim())}
              size="lg"
              className="w-full sm:w-auto"
            >
              <ShieldCheck className="mr-1.5 h-4 w-4" aria-hidden="true" />
              {isScanning ? "Scanning..." : (
                <>
                  Scan Now{" "}
                  <kbd className="ml-2 hidden rounded bg-primary-foreground/20 px-1.5 py-0.5 font-mono text-[10px] font-medium sm:inline-block">
                    {modKey} ↵
                  </kbd>
                </>
              )}
            </Button>
          </div>
        )}

        <p className="mt-6 border-t border-border/60 pt-4 text-center font-mono text-[11px] text-muted-foreground">
          Supported: websites, SMS, emails, screenshots, voice transcripts, PDFs, and QR codes
        </p>
      </div>
    </div>
  );
}
