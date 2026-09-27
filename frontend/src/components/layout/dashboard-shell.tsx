"use client";

import { useState, useCallback, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Sidebar } from "@/components/layout/sidebar";
import { Navbar } from "@/components/layout/navbar";

export function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const handleOpen = useCallback(() => {
    setIsSidebarOpen(true);
  }, []);

  const handleClose = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  return (
    <div className="flex min-h-screen bg-background/95">
      <Sidebar isOpen={isSidebarOpen} onClose={handleClose} />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <Navbar onMenuClick={handleOpen} />
        <a className="skip-link" href="#main-content">Skip to content</a>
        <main id="main-content" tabIndex={-1} className="flex-1 overflow-x-hidden px-4 py-6 md:px-8 md:py-10 xl:px-10">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="route-shell mx-auto w-full max-w-7xl"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
