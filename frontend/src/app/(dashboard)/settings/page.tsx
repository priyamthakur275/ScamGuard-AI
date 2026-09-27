"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useDialogFocus } from "@/hooks/use-dialog-focus";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { motion, AnimatePresence } from "framer-motion";
import {
  User as UserIcon,
  Shield,
  Sliders,
  Bell,
  Database,
  AlertTriangle,
  Eye,
  EyeOff,
  CheckCircle2,
  Download,
  Trash2,
  Lock,
} from "lucide-react";
import { useAuth } from "@/lib/auth/auth-context";
import { useTheme } from "@/lib/theme/theme-context";
import { updateProfile, changePassword, deleteAccount, exportUserData } from "@/lib/api/users";
import { clearHistory } from "@/lib/api/messages";
import { ApiError } from "@/lib/api/client";
import { formatDate } from "@/lib/utils";

export default function SettingsPage() {
  const { toast } = useToast();
  const { user, refreshUser, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const [activeTab, setActiveTab] = useState("profile");

  // Profile Form State
  const [fullName, setFullName] = useState("");
  const [isSubmittingProfile, setIsSubmittingProfile] = useState(false);

  // Security Form State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmittingPassword, setIsSubmittingPassword] = useState(false);

  // Detection Preferences State
  const [autoSaveHistory, setAutoSaveHistory] = useState(true);
  const [defaultInputChannel, setDefaultInputChannel] = useState("text");
  const [highThreatAudio, setHighThreatAudio] = useState(true);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);

  // Notifications State
  const [securityAlerts, setSecurityAlerts] = useState(true);
  const [weeklyDigest, setWeeklyDigest] = useState(false);
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);

  // Privacy & Danger State
  const [isExporting, setIsExporting] = useState(false);
  const [showClearHistoryModal, setShowClearHistoryModal] = useState(false);
  const [isClearingHistory, setIsClearingHistory] = useState(false);

  const [showDangerModal, setShowDangerModal] = useState(false);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const clearRef = useRef<HTMLDivElement>(null);
  const deleteRef = useRef<HTMLDivElement>(null);
  const closeClear = useCallback(() => { if (!isClearingHistory) setShowClearHistoryModal(false); }, [isClearingHistory]);
  const closeDelete = useCallback(() => { if (!isDeleting) setShowDangerModal(false); }, [isDeleting]);
  useDialogFocus(showClearHistoryModal, clearRef, closeClear);
  useDialogFocus(showDangerModal, deleteRef, closeDelete);

  // Sync user data
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      if (user.preferences) {
        setAutoSaveHistory(true);
        setDefaultInputChannel(String(user.preferences.default_channel || "text"));
        setHighThreatAudio(user.preferences.high_threat_alerts !== false);
        setSecurityAlerts(user.preferences.security_alerts !== false);
        setWeeklyDigest(Boolean(user.preferences.weekly_digest));
      }
    }
  }, [user]);

  const TABS = [
    { id: "profile", label: "Profile", icon: UserIcon },
    { id: "security", label: "Security", icon: Shield },
    { id: "preferences", label: "Detection Preferences", icon: Sliders },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "privacy", label: "Privacy & Data", icon: Database },
    { id: "danger", label: "Danger Zone", icon: AlertTriangle, danger: true },
  ];

  // 1. Profile Update Handler
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingProfile(true);
    try {
      await updateProfile({
        full_name: fullName.trim(),
        preferences: {
          ...user?.preferences,
          theme,
        },
      });
      await refreshUser();
      toast({ title: "Profile updated successfully", variant: "success" });
    } catch (error) {
      const msg = error instanceof ApiError ? error.message : "Failed to update profile";
      toast({ title: msg, variant: "error" });
    } finally {
      setIsSubmittingProfile(false);
    }
  };

  // 2. Password Change Handler
  const hasMinLength = newPassword.length >= 8;
  const hasNumber = /\d/.test(newPassword);
  const hasUpper = /[A-Z]/.test(newPassword);
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast({ title: "Please fill in all password fields", variant: "error" });
      return;
    }
    if (!hasMinLength || !hasNumber || !hasUpper) {
      toast({ title: "New password does not meet security requirements", variant: "error" });
      return;
    }
    if (!passwordsMatch) {
      toast({ title: "New passwords do not match", variant: "error" });
      return;
    }

    setIsSubmittingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast({ title: "Password changed successfully", variant: "success" });
    } catch (error) {
      const msg = error instanceof ApiError ? error.message : "Failed to change password";
      toast({ title: msg, variant: "error" });
    } finally {
      setIsSubmittingPassword(false);
    }
  };

  // 3. Detection Preferences Handler
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingPreferences(true);
    try {
      await updateProfile({
        preferences: {
          ...user?.preferences,
          auto_save_history: autoSaveHistory,
          default_channel: defaultInputChannel,
          high_threat_alerts: highThreatAudio,
        },
      });
      await refreshUser();
      toast({ title: "Detection preferences saved", variant: "success" });
    } catch (error) {
      const msg = error instanceof ApiError ? error.message : "Failed to save preferences";
      toast({ title: msg, variant: "error" });
    } finally {
      setIsSavingPreferences(false);
    }
  };

  // 4. Notifications Handler
  const handleSaveNotifications = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingNotifications(true);
    try {
      await updateProfile({
        preferences: {
          ...user?.preferences,
          security_alerts: securityAlerts,
          weekly_digest: weeklyDigest,
        },
      });
      await refreshUser();
      toast({ title: "Notification settings saved", variant: "success" });
    } catch (error) {
      const msg = error instanceof ApiError ? error.message : "Failed to save notification settings";
      toast({ title: msg, variant: "error" });
    } finally {
      setIsSavingNotifications(false);
    }
  };

  // 5. Privacy & Data Export Handler
  const handleExportData = async () => {
    setIsExporting(true);
    try {
      const data = await exportUserData();
      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(data, null, 2))}`;
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", jsonString);
      downloadAnchor.setAttribute("download", `scamguard-export-${new Date().toISOString().slice(0, 10)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      toast({ title: "Data exported successfully", variant: "success" });
    } catch (error) {
      const msg = error instanceof ApiError ? error.message : "Failed to export data";
      toast({ title: msg, variant: "error" });
    } finally {
      setIsExporting(false);
    }
  };

  // Clear History
  const handleClearHistory = async () => {
    setIsClearingHistory(true);
    try {
      await clearHistory();
      setShowClearHistoryModal(false);
      toast({ title: "Analysis history cleared", variant: "success" });
    } catch (error) {
      const msg = error instanceof ApiError ? error.message : "Failed to clear history";
      toast({ title: msg, variant: "error" });
    } finally {
      setIsClearingHistory(false);
    }
  };

  // 6. Danger Zone: Delete Account Handler
  const handleDeleteAccount = async () => {
    if (deleteConfirmationText !== "DELETE") {
      toast({ title: "Please type DELETE to confirm", variant: "error" });
      return;
    }
    setIsDeleting(true);
    try {
      await deleteAccount();
      await logout();
      toast({ title: "Your account has been deleted", variant: "success" });
    } catch (error) {
      const msg = error instanceof ApiError ? error.message : "Failed to delete account";
      toast({ title: msg, variant: "error" });
      setIsDeleting(false);
      setShowDangerModal(false);
    }
  };

  const ToggleSwitch = ({
    checked,
    onChange,
    label,
    description,
  }: {
    checked: boolean;
    onChange: (c: boolean) => void;
    label: string;
    description: string;
  }) => (
    <div className="flex items-center justify-between py-3">
      <div className="flex flex-col gap-0.5">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span className="text-xs text-muted-foreground">{description}</span>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${
          checked ? "bg-primary" : "bg-muted-foreground/30"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );

  return (
    <div className="sg-page flex flex-col gap-8 animate-slide-up pb-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-2">Account Settings</h1>
        <p className="text-muted-foreground">Manage your profile, security credentials, preferences, and data privacy.</p>
      </div>

      <div className="flex flex-col md:flex-row gap-8 items-start">
        {/* Navigation Sidebar */}
        <div className="w-full md:w-64 flex flex-col gap-1 bg-card border border-border p-2 shrink-0">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? tab.danger
                      ? "bg-destructive/15 text-destructive font-semibold"
                      : "bg-primary/10 text-primary font-semibold"
                    : tab.danger
                    ? "text-destructive/70 hover:bg-destructive/10"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Content Box */}
        <div className="flex-1 w-full bg-card border border-border p-6 sm:p-8 min-h-[420px]">
          <AnimatePresence mode="wait">
            {/* 1. PROFILE TAB */}
            {activeTab === "profile" && (
              <motion.div key="profile" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <h2 className="text-xl font-semibold mb-1">Profile Details</h2>
                <p className="text-sm text-muted-foreground mb-6">Manage your public information and appearance.</p>

                <form onSubmit={handleUpdateProfile} className="flex flex-col gap-6 max-w-xl">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">Account Email</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={user?.email || ""}
                        disabled
                        className="flex-1 h-10 rounded-md border border-input bg-muted px-3 text-sm opacity-80 cursor-not-allowed text-muted-foreground"
                      />
                      <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-primary/10 text-primary font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Account email
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">Primary identity used for sign-in and security notifications.</span>
                  </div>

                  <div className="flex flex-col gap-2">
                    <label htmlFor="profile-name" className="text-sm font-medium">Display Name</label>
                    <input
                      type="text"
                      id="profile-name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Enter your name"
                      className="h-10 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4 py-3 border-y border-border/50 text-xs">
                    <div>
                      <span className="text-muted-foreground block">Account Role</span>
                      <span className="font-semibold uppercase tracking-wider text-foreground">{user?.role || "USER"}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Member Since</span>
                      <span className="font-semibold text-foreground">{user?.created_at ? formatDate(user.created_at) : "Recent"}</span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-3">
                    <h3 className="text-sm font-semibold">Appearance Theme</h3>
                    <div className="flex gap-3">
                      <button
                        type="button"
                        onClick={() => setTheme("dark")}
                        className={`flex-1 py-2.5 px-4 rounded-lg border text-sm font-medium text-center transition-all ${
                          theme === "dark" ? "border-primary bg-primary/10 text-primary" : "border-border hover:bg-muted"
                        }`}
                      >
                        Dark Mode
                      </button>
                      <button
                        type="button"
                        onClick={() => setTheme("light")}
                        className={`flex-1 py-2.5 px-4 rounded-lg border text-sm font-medium text-center transition-all ${
                          theme === "light" ? "border-primary bg-primary/10 text-primary" : "border-border hover:bg-muted"
                        }`}
                      >
                        Light Mode
                      </button>
                    </div>
                  </div>

                  <Button type="submit" isLoading={isSubmittingProfile} className="w-fit mt-2">
                    Save Profile Changes
                  </Button>
                </form>
              </motion.div>
            )}

            {/* 2. SECURITY TAB */}
            {activeTab === "security" && (
              <motion.div key="security" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <h2 className="text-xl font-semibold mb-1">Account Security</h2>
                <p className="text-sm text-muted-foreground mb-6">Update your password to keep your account safe.</p>

                <form onSubmit={handleUpdatePassword} className="flex flex-col gap-5 max-w-xl">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">Current Password</label>
                    <div className="relative">
                      <input
                        type={showCurrentPassword ? "text" : "password"}
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className="h-10 w-full rounded-md border border-input bg-background px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                        required
                      />
                      <button
                        type="button"
                        aria-label="Toggle current password visibility"
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                      >
                        {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">New Password</label>
                    <div className="relative">
                      <input
                        type={showNewPassword ? "text" : "password"}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="h-10 w-full rounded-md border border-input bg-background px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                        required
                      />
                      <button
                        type="button"
                        aria-label="Toggle new password visibility"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                      >
                        {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Password Strength Checklist */}
                  <div className="rounded-lg bg-muted/40 p-3 text-xs space-y-1.5 border border-border/50">
                    <span className="font-semibold text-foreground block mb-1">Password Requirements:</span>
                    <div className={`flex items-center gap-2 ${hasMinLength ? "text-emerald-500 font-medium" : "text-muted-foreground"}`}>
                      <span>{hasMinLength ? "✓" : "○"}</span> At least 8 characters
                    </div>
                    <div className={`flex items-center gap-2 ${hasUpper ? "text-emerald-500 font-medium" : "text-muted-foreground"}`}>
                      <span>{hasUpper ? "✓" : "○"}</span> At least one uppercase letter (A–Z)
                    </div>
                    <div className={`flex items-center gap-2 ${hasNumber ? "text-emerald-500 font-medium" : "text-muted-foreground"}`}>
                      <span>{hasNumber ? "✓" : "○"}</span> At least one number (0–9)
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium">Confirm New Password</label>
                    <div className="relative">
                      <input
                        type={showConfirmPassword ? "text" : "password"}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="h-10 w-full rounded-md border border-input bg-background px-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                        required
                      />
                      <button
                        type="button"
                        aria-label="Toggle confirm password visibility"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                      >
                        {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {confirmPassword && !passwordsMatch && (
                      <span className="text-xs text-destructive">Passwords do not match.</span>
                    )}
                  </div>

                  <Button
                    type="submit"
                    isLoading={isSubmittingPassword}
                    disabled={!passwordsMatch || !hasMinLength || !hasNumber || !hasUpper}
                    className="w-fit mt-2"
                  >
                    Update Password
                  </Button>
                </form>
              </motion.div>
            )}

            {/* 3. DETECTION PREFERENCES TAB */}
            {activeTab === "preferences" && (
              <motion.div key="preferences" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <h2 className="text-xl font-semibold mb-1">Detection Preferences</h2>
                <p className="text-sm text-muted-foreground mb-6">Customize how AI scam analysis operates for your account.</p>

                <form onSubmit={handleSavePreferences} className="flex flex-col gap-6 max-w-xl">
                  <fieldset disabled className="opacity-60">
                  <p className="mb-2 text-xs">Scans are always saved. History opt-out is not available.</p>
                  <ToggleSwitch
                    checked={autoSaveHistory}
                    onChange={setAutoSaveHistory}
                    label="Auto-Save Scans to History"
                    description="Automatically log scan results and extracted indicators to your account history."
                  /></fieldset>

                  <div className="flex flex-col gap-2 py-3 border-t border-border/50">
                    <label className="text-sm font-medium">Default Analysis Tab</label>
                    <select
                      value={defaultInputChannel}
                      onChange={(e) => setDefaultInputChannel(e.target.value)}
                      className="h-10 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                    >
                      <option value="text">Raw Text (SMS / Message)</option>
                      <option value="url">Web URL Analysis</option>
                      <option value="email">Email Analysis (.eml / Text)</option>
                      <option value="image">Screenshot / Image OCR</option>
                      <option value="pdf">Document PDF</option>
                      <option value="qr">QR Code Scanner</option>
                    </select>
                    <span className="text-xs text-muted-foreground">The tab selected by default when you open the Analyze page.</span>
                  </div>

                  <fieldset disabled className="opacity-60"><p className="text-xs">Severity indicators are always shown. Custom warning behavior is not available.</p>
                  <ToggleSwitch
                    checked={highThreatAudio}
                    onChange={setHighThreatAudio}
                    label="High Threat Visual Warnings"
                    description="Display evidence-based severity on every verdict."
                  /></fieldset>

                  <Button type="submit" isLoading={isSavingPreferences} className="w-fit mt-2">
                    Save Detection Preferences
                  </Button>
                </form>
              </motion.div>
            )}

            {/* 4. NOTIFICATIONS TAB */}
            {activeTab === "notifications" && (
              <motion.div key="notifications" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <h2 className="text-xl font-semibold mb-1">Notification Preferences</h2>
                <p className="text-sm text-muted-foreground mb-6">Choose how and when ScamGuard sends you security alerts.</p>

                <p className="mb-5 rounded-lg border border-border bg-muted p-4 text-sm">Notification delivery is not implemented in this deployment. These controls are unavailable.</p>
                <fieldset disabled className="opacity-50"><form onSubmit={handleSaveNotifications} className="flex flex-col gap-5 max-w-xl">
                  <ToggleSwitch
                    checked={securityAlerts}
                    onChange={setSecurityAlerts}
                    label="Critical Security Alerts"
                    description="Notify me when high-risk scam indicators or account security events are detected."
                  />

                  <ToggleSwitch
                    checked={weeklyDigest}
                    onChange={setWeeklyDigest}
                    label="Weekly Threat Summary"
                    description="Receive an aggregate summary of newly discovered phishing tactics and platform intelligence."
                  />

                  <Button type="submit" isLoading={isSavingNotifications} className="w-fit mt-3">
                    Save Notification Settings
                  </Button>
                </form></fieldset>
              </motion.div>
            )}

            {/* 5. PRIVACY & DATA TAB */}
            {activeTab === "privacy" && (
              <motion.div key="privacy" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <h2 className="text-xl font-semibold mb-1">Privacy & Data Management</h2>
                <p className="text-sm text-muted-foreground mb-6">Export or purge your analysis history and account telemetry.</p>

                <div className="flex flex-col gap-6 max-w-xl">
                  <div className="border border-border p-5 bg-card space-y-3">
                    <div className="flex items-center gap-3">
                      <Download className="w-5 h-5 text-primary" />
                      <div>
                        <h3 className="text-sm font-semibold">Export Account Data</h3>
                        <p className="text-xs text-muted-foreground">Download a complete JSON record of your account profile, settings, and prediction history.</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleExportData} isLoading={isExporting}>
                      Export Data (.json)
                    </Button>
                  </div>

                  <div className="border border-border p-5 bg-card space-y-3">
                    <div className="flex items-center gap-3">
                      <Trash2 className="w-5 h-5 text-destructive" />
                      <div>
                        <h3 className="text-sm font-semibold text-foreground">Clear Scan History</h3>
                        <p className="text-xs text-muted-foreground">Delete all previous scam prediction records and extracted telemetry from our database.</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => setShowClearHistoryModal(true)} className="text-destructive hover:bg-destructive/10">
                      Clear History
                    </Button>
                  </div>

                  <div className="rounded-lg bg-muted/40 p-4 border border-border/40 text-xs text-muted-foreground space-y-1.5">
                    <span className="font-semibold text-foreground block">Data Retention Notice</span>
                    <p>
                      Submitted text, extracted evidence, and analysis results are stored in your account history. You can export or delete them here. Browser speech recognition may send audio to your browser vendor for transcription.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* 6. DANGER ZONE TAB */}
            {activeTab === "danger" && (
              <motion.div key="danger" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <h2 className="text-xl font-semibold mb-1 text-destructive">Danger Zone</h2>
                <p className="text-sm text-muted-foreground mb-6">Irreversible actions that permanently impact your account.</p>

                <div className="border border-destructive/30 bg-destructive/5 p-6 max-w-xl">
                  <h3 className="font-semibold text-foreground mb-2 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-destructive" />
                    Delete Account Permanently
                  </h3>
                  <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
                    Once your account is deleted, all your profile details, session tokens, and saved detection history will be permanently deleted from our database. This action cannot be undone.
                  </p>
                  <Button variant="destructive" onClick={() => setShowDangerModal(true)}>
                    Delete My Account
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Clear History Confirmation Modal */}
      <AnimatePresence>
        {showClearHistoryModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              ref={clearRef} role="dialog" aria-modal="true" aria-label="Clear scan history" tabIndex={-1}
              className="rounded-lg bg-card border border-border p-6 max-w-md w-full"
            >
              <h3 className="text-lg font-bold mb-2">Clear Scan History?</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Are you sure you want to delete all saved scan records? This action cannot be reverted.
              </p>
              <div className="flex justify-end gap-3">
                <Button variant="outline" size="sm" onClick={() => setShowClearHistoryModal(false)} disabled={isClearingHistory}>
                  Cancel
                </Button>
                <Button variant="destructive" size="sm" onClick={handleClearHistory} isLoading={isClearingHistory}>
                  Yes, Clear All History
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Delete Account Modal with Strict Confirmation */}
      <AnimatePresence>
        {showDangerModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              ref={deleteRef} role="dialog" aria-modal="true" aria-label="Delete account" tabIndex={-1}
              className="rounded-lg bg-card border border-border p-6 sm:p-8 max-w-md w-full"
            >
              <div className="flex items-center gap-3 mb-4 text-destructive">
                <AlertTriangle className="w-7 h-7 shrink-0" />
                <h3 className="text-xl font-bold">Delete Account?</h3>
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                This will permanently delete your account and all associated prediction data. Please type{" "}
                <span className="font-mono font-bold text-foreground">DELETE</span> below to confirm.
              </p>
              <input
                type="text"
                aria-label="Type DELETE to confirm"
                placeholder="Type DELETE to confirm"
                value={deleteConfirmationText}
                onChange={(e) => setDeleteConfirmationText(e.target.value)}
                className="h-10 w-full rounded-md border border-destructive/40 bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-destructive/50 mb-6 font-mono"
              />
              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowDangerModal(false);
                    setDeleteConfirmationText("");
                  }}
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDeleteAccount}
                  disabled={deleteConfirmationText !== "DELETE" || isDeleting}
                  isLoading={isDeleting}
                >
                  Permanently Delete
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
