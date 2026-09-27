"use client";

import { useState, useCallback } from "react";
import { UploadCloud, X, File as FileIcon } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface FileUploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  acceptedTypes?: string;
  maxFiles?: number;
}

export function FileUploadZone({ onFilesSelected, acceptedTypes = "*/*", maxFiles = 10 }: FileUploadZoneProps) {
  const [error, setError] = useState<string | null>(null);
  const validate = useCallback((files: File[]) => {
    const accepted = files.filter(file => file.size <= 8 * 1024 * 1024 && (acceptedTypes === "image/*" ? file.type.startsWith("image/") : acceptedTypes === ".pdf" ? file.name.toLowerCase().endsWith(".pdf") : true));
    setError(accepted.length !== files.length ? "Some files were rejected. Choose the matching file type, up to 8 MB each." : null);
    return accepted;
  }, [acceptedTypes]);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const files = validate(Array.from(e.dataTransfer.files).slice(0, maxFiles));
        setSelectedFiles(files);
        onFilesSelected(files);
      }
    },
    [maxFiles, onFilesSelected, validate]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        const files = validate(Array.from(e.target.files).slice(0, maxFiles));
        setSelectedFiles(files);
        onFilesSelected(files);
      }
    },
    [maxFiles, onFilesSelected, validate]
  );

  const removeFile = useCallback(
    (index: number) => {
      const newFiles = [...selectedFiles];
      newFiles.splice(index, 1);
      setSelectedFiles(newFiles);
      onFilesSelected(newFiles);
    },
    [selectedFiles, onFilesSelected]
  );

  return (
    <div className="w-full space-y-4">
      <div
        className={`relative border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center transition-all duration-500 overflow-hidden ${
          isDragging
            ? "border-primary bg-primary/10 "
            : "border-muted-foreground/25 hover:border-primary/60 bg-card  hover:bg-primary/5"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="absolute inset-0 bg-gradient-to-tr from-primary/0 via-primary/5 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
        <UploadCloud className={`w-12 h-12 mb-4 transition-all duration-300 ${isDragging ? "text-primary scale-110 " : "text-muted-foreground"}`} />
        <p className="text-lg font-medium text-foreground mb-1">
          Drag and drop your files here
        </p>
        <p className="text-sm text-muted-foreground mb-4">
          or click to browse from your computer
        </p>
        <label>
          <span className="inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80 border border-border/50 h-10 px-4 text-sm cursor-pointer">
            Browse Files
          </span>
          <input
            type="file"
            className="mt-3 block w-full max-w-xs text-xs"
            aria-label="Evidence files"
            multiple={maxFiles > 1}
            accept={acceptedTypes}
            onChange={handleFileInput}
          />
        </label>
      </div>

      {error && <Alert variant="error">{error}</Alert>}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">Selected Files ({selectedFiles.length})</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {selectedFiles.map((file, idx) => (
              <div key={`${file.name}-${idx}`} className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg border border-border">
                <div className="flex items-center space-x-3 overflow-hidden">
                  <FileIcon className="w-5 h-5 text-primary flex-shrink-0" />
                  <span className="text-sm truncate font-medium">{file.name}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive flex-shrink-0"
                  aria-label={`Remove ${file.name}`}
                  onClick={() => removeFile(idx)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
