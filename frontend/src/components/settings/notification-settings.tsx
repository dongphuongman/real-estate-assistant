"use client"

import React, { useEffect, useState } from "react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Label } from "../ui/label";
import { getNotificationSettings, updateNotificationSettings } from "@/lib/api";
import { NotificationSettings as SettingsType } from "@/lib/types";

export function NotificationSettings() {
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await getNotificationSettings();
      setSettings(data);
      setError(null);
    } catch (err) {
      console.error("Failed to load settings:", err);
      setError("Failed to load settings. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4 text-center">Loading settings...</div>;
  }

  if (!settings) {
    return (
      <div className="p-4 text-center text-red-500">
        {error || "Something went wrong."}
        <Button onClick={fetchSettings} className="ml-4">Retry</Button>
      </div>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updated = await updateNotificationSettings(settings);
      setSettings(updated);
      setSuccess("Settings saved successfully.");
    } catch (err) {
      console.error("Failed to save settings:", err);
      setError("Failed to save settings. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const toggleSetting = (key: Exclude<keyof SettingsType, "frequency">) => {
    setSettings({ ...settings, [key]: !settings[key] });
  };

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Email Digests</CardTitle>
          <CardDescription>
            Manage your property digest subscriptions and frequency.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="email_digest" className="flex flex-col space-y-1">
              <span>Consumer Digest</span>
              <span className="font-normal text-muted-foreground">
                Receive new matches and price drops for your saved searches.
              </span>
            </Label>
            <input
              type="checkbox"
              id="email_digest"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.email_digest}
              onChange={() => toggleSetting("email_digest")}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="expert_mode" className="flex flex-col space-y-1">
              <span>Expert Mode</span>
              <span className="font-normal text-muted-foreground">
                Include market trends, indices, and yield analysis in your digest.
              </span>
            </Label>
            <input
              type="checkbox"
              id="expert_mode"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.expert_mode}
              onChange={() => toggleSetting("expert_mode")}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="frequency">Digest Frequency</Label>
            <select
              id="frequency"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={settings.frequency}
              onChange={(e) =>
                setSettings({ ...settings, frequency: e.target.value as "daily" | "weekly" })
              }
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="marketing_emails" className="flex flex-col space-y-1">
              <span>Product Updates</span>
              <span className="font-normal text-muted-foreground">
                Receive occasional emails about new features and improvements.
              </span>
            </Label>
            <input
              type="checkbox"
              id="marketing_emails"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.marketing_emails}
              onChange={() => toggleSetting("marketing_emails")}
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-end gap-4">
        {success && <span className="text-green-600 text-sm">{success}</span>}
        {error && <span className="text-red-600 text-sm">{error}</span>}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Preferences"}
        </Button>
      </div>
    </div>
  );
}
