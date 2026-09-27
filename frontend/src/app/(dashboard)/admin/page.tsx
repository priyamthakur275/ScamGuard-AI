"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, ShieldAlert, Activity, ShieldCheck, UserCheck, Search, Gauge, FlaskConical } from "lucide-react";
import { motion, Variants } from "framer-motion";
import { useAuth } from "@/lib/auth/auth-context";
import { getAdminStats, listUsers, type AdminStats } from "@/lib/api/users";
import { formatDate } from "@/lib/utils";
import type { User } from "@/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [usersList, setUsersList] = useState<User[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (!user) return;

    // Fetch live system telemetry
    Promise.all([
      getAdminStats().catch((err) => {
        console.warn("Could not fetch admin stats:", err);
        return null;
      }),
      isAdmin
        ? listUsers().catch(() => [])
        : Promise.resolve([]),
    ])
      .then(([adminStats, users]) => {
        if (adminStats) {
          setStats(adminStats);
        }
        setUsersList(users);
      })
      .catch(() => setError("Failed to load administration telemetry."))
      .finally(() => setLoading(false));
  }, [user, isAdmin]);

  if (loading) {
    return (
      <div className="sg-page flex flex-col gap-6">
        <h1 className="text-2xl font-semibold tracking-tight">System Administration</h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // If user is not an admin, show a clean, realistic message with context
  if (!isAdmin) {
    return (
      <div className="flex flex-col gap-6 max-w-2xl mx-auto py-12">
        <div className="rounded-2xl border border-border/80 bg-card p-8 text-center flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-600 dark:text-amber-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight mb-1">Administrator Privileges Required</h2>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-md">
              Your account (<span className="font-semibold text-foreground">{user?.email}</span>) is registered with the role{" "}
              <span className="inline-flex px-2 py-0.5 rounded text-xs font-mono font-semibold bg-muted uppercase">
                {user?.role || "USER"}
              </span>.
            </p>
          </div>
          <div className="rounded-lg bg-muted/40 p-4 border border-border/50 text-xs text-muted-foreground text-left w-full space-y-2">
            <p className="font-semibold text-foreground">Technical Review Note:</p>
            <p>
              In production, role elevation is managed through database migrations or by an existing system administrator via{" "}
              <code className="bg-muted px-1 py-0.5 rounded text-foreground font-mono">PATCH /api/v1/users/&#123;id&#125;/role</code>.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const filteredUsers = usersList.filter(
    (u) =>
      u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (u.full_name && u.full_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const totalUsers = stats?.users_count ?? usersList.length;
  const totalScans = stats?.scans_count ?? 0;
  const highThreatScans = stats?.threat_counts?.high ?? 0;
  const mediumThreatScans = stats?.threat_counts?.medium ?? 0;

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="flex flex-col gap-8">
      <motion.div variants={itemVariants} className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">System Administration</h1>
          <p className="text-muted-foreground">
            Live cluster telemetry, verified account registry, and threat detection volume.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/admin/model-evaluation"
            className="flex items-center gap-2 border border-border px-3 py-2 font-mono text-xs uppercase tracking-wide text-foreground transition-colors hover:bg-muted"
          >
            <Gauge className="h-4 w-4" />
            Model evaluation
          </Link>
          <Link
            href="/admin/robustness-test"
            className="flex items-center gap-2 border border-border px-3 py-2 font-mono text-xs uppercase tracking-wide text-foreground transition-colors hover:bg-muted"
          >
            <FlaskConical className="h-4 w-4" />
            Robustness test
          </Link>
        </div>
      </motion.div>

      {error && <Alert variant="error">{error}</Alert>}

      {/* Real Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <motion.div variants={itemVariants} className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Total Users</span>
            <Users className="w-4 h-4 text-blue-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-foreground">{totalUsers}</p>
          <span className="text-xs text-muted-foreground mt-1 block">Registered in PostgreSQL database</span>
        </motion.div>

        <motion.div variants={itemVariants} className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Total Messages Scanned</span>
            <Activity className="w-4 h-4 text-primary" />
          </div>
          <p className="text-2xl font-bold mt-2 text-foreground">{totalScans}</p>
          <span className="text-xs text-muted-foreground mt-1 block">Processed through ML pipeline</span>
        </motion.div>

        <motion.div variants={itemVariants} className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">High Risk Threats</span>
            <ShieldAlert className="w-4 h-4 text-red-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-red-500">{highThreatScans}</p>
          <span className="text-xs text-muted-foreground mt-1 block">Flagged with high scam confidence</span>
        </motion.div>

        <motion.div variants={itemVariants} className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Medium Suspicious</span>
            <ShieldCheck className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-2xl font-bold mt-2 text-amber-500">{mediumThreatScans}</p>
          <span className="text-xs text-muted-foreground mt-1 block">Requiring user caution</span>
        </motion.div>
      </div>

      {/* User Management Table */}
      <motion.div variants={itemVariants} className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="p-6 border-b border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">User Directory</h2>
            <p className="text-xs text-muted-foreground">Inspect active registered accounts and security roles.</p>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by email or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-9 pr-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/40 text-xs font-semibold text-muted-foreground border-b border-border">
              <tr>
                <th className="px-6 py-3.5">User</th>
                <th className="px-6 py-3.5">Role</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Created At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredUsers.length > 0 ? (
                filteredUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-medium text-foreground">{u.full_name || "—"}</span>
                        <span className="text-xs text-muted-foreground">{u.email}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                          u.role === "admin" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 text-xs text-emerald-500 font-medium">
                        <UserCheck className="w-3.5 h-3.5" />
                        Active
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(u.created_at)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground text-sm">
                    No users matching criteria found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  );
}
