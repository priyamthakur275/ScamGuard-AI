"use client";

import Link from "next/link";
import { Compass, Search, Home } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { motion } from "framer-motion";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 text-center bg-background relative overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px] -z-10 pointer-events-none" />
      
      <motion.div 
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="relative"
      >
        <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full" />
        <div className="relative bg-background/80 backdrop-blur-xl p-8 rounded-full border border-white/10 shadow-2xl">
          <Compass className="h-20 w-20 text-primary animate-pulse" />
        </div>
      </motion.div>

      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1, type: "spring" }}
        className="space-y-3 max-w-md"
      >
        <h1 className="text-5xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/50">
          404
        </h1>
        <h2 className="text-2xl font-semibold text-foreground">Page not found</h2>
        <p className="text-muted-foreground text-lg">
          The page you&apos;re looking for has drifted into the void or doesn&apos;t exist anymore.
        </p>
      </motion.div>

      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, type: "spring" }}
      >
        <Link 
          href="/" 
          className={buttonVariants({ variant: "primary", size: "lg", className: "rounded-full px-8 gap-2 group" })}
        >
          <Home className="w-4 h-4 group-hover:scale-110 transition-transform" />
          Return Home
        </Link>
      </motion.div>
    </div>
  );
}
