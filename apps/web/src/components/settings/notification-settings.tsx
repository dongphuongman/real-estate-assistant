'use client';

import React, { useEffect, useState } from 'react';
import { Bell, Smartphone, Mail, Monitor, Clock, Send } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import {
  getNotificationSettings,
  updateNotificationSettings,
  sendNotificationPreview,
} from '@/lib/api';
import {
  NotificationSettings as SettingsType,
  NotificationSettingsUpdate,
  NotificationPreviewRequest,
} from '@/lib/types';
import { isPushSupported, requestNotificationPermission, getNotificationPermission } from '@/lib/push';

const DAYS_OF_WEEK = [
  'sunday',
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
];

export function NotificationSettings() {
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [pushPermissionStatus, setPushPermissionStatus] =
    useState<NotificationPermission | null>(null);
  const [sendingPreview, setSendingPreview] = useState(false);

  useEffect(() => {
    fetchSettings();
    checkPushStatus();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await getNotificationSettings();
      setSettings(data);
      setError(null);
    } catch {
      setError('Failed to load settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const checkPushStatus = async () => {
    if (isPushSupported()) {
      const status = await getNotificationPermission();
      setPushPermissionStatus(status);
    }
  };

  if (loading) {
    return <div className="p-4 text-center">Loading settings...</div>;
  }

  if (!settings) {
    return (
      <div className="p-4 text-center text-red-500">
        {error || 'Something went wrong.'}
        <Button onClick={fetchSettings} className="ml-4">
          Retry
        </Button>
      </div>
    );
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updateData: NotificationSettingsUpdate = {
        price_alerts_enabled: settings.price_alerts_enabled,
        new_listings_enabled: settings.new_listings_enabled,
        saved_search_enabled: settings.saved_search_enabled,
        market_updates_enabled: settings.market_updates_enabled,
        alert_frequency: settings.alert_frequency,
        email_enabled: settings.email_enabled,
        push_enabled: settings.push_enabled,
        in_app_enabled: settings.in_app_enabled,
        quiet_hours_start: settings.quiet_hours_start,
        quiet_hours_end: settings.quiet_hours_end,
        price_drop_threshold: settings.price_drop_threshold,
        daily_digest_time: settings.daily_digest_time,
        weekly_digest_day: settings.weekly_digest_day,
        expert_mode: settings.expert_mode,
        marketing_emails: settings.marketing_emails,
      };
      const updated = await updateNotificationSettings(updateData);
      setSettings(updated);
      setSuccess('Settings saved successfully.');
    } catch {
      setError('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const toggleSetting = (key: keyof SettingsType) => {
    if (key === 'unsubscribe_token' || key === 'unsubscribed_at' || key === 'unsubscribed_types') {
      return;
    }
    setSettings({ ...settings, [key]: !settings[key] } as SettingsType);
  };

  const updateSetting = <K extends keyof SettingsType>(key: K, value: SettingsType[K]) => {
    setSettings({ ...settings, [key]: value });
  };

  const handleEnablePush = async () => {
    const permission = await requestNotificationPermission();
    setPushPermissionStatus(permission);
    if (permission === 'granted') {
      setSettings({ ...settings, push_enabled: true });
    }
  };

  const handleSendPreview = async (channel: 'email' | 'push' | 'in_app') => {
    setSendingPreview(true);
    setError(null);
    setSuccess(null);

    try {
      const request: NotificationPreviewRequest = {
        channel,
        notification_type: 'price_alert',
      };
      const result = await sendNotificationPreview(request);
      if (result.success) {
        setSuccess(result.message);
      } else {
        setError(result.message);
      }
    } catch {
      setError('Failed to send preview notification.');
    } finally {
      setSendingPreview(false);
    }
  };

  return (
    <div className="grid gap-6">
      {/* Notification Types Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-primary" />
            <CardTitle>Notification Types</CardTitle>
          </div>
          <CardDescription>Choose which notifications you want to receive.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="price_alerts" className="flex flex-col space-y-1">
              <span>Price Alerts</span>
              <span className="font-normal text-muted-foreground">
                Get notified when property prices drop.
              </span>
            </Label>
            <input
              type="checkbox"
              id="price_alerts"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.price_alerts_enabled}
              onChange={() => toggleSetting('price_alerts_enabled')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="new_listings" className="flex flex-col space-y-1">
              <span>New Listings</span>
              <span className="font-normal text-muted-foreground">
                Get notified about new properties matching your criteria.
              </span>
            </Label>
            <input
              type="checkbox"
              id="new_listings"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.new_listings_enabled}
              onChange={() => toggleSetting('new_listings_enabled')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="saved_search" className="flex flex-col space-y-1">
              <span>Saved Search Updates</span>
              <span className="font-normal text-muted-foreground">
                Get updates about changes to your saved searches.
              </span>
            </Label>
            <input
              type="checkbox"
              id="saved_search"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.saved_search_enabled}
              onChange={() => toggleSetting('saved_search_enabled')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="market_updates" className="flex flex-col space-y-1">
              <span>Market Updates</span>
              <span className="font-normal text-muted-foreground">
                Receive market trends and analysis updates.
              </span>
            </Label>
            <input
              type="checkbox"
              id="market_updates"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.market_updates_enabled}
              onChange={() => toggleSetting('market_updates_enabled')}
            />
          </div>
        </CardContent>
      </Card>

      {/* Notification Channels Card */}
      <Card>
        <CardHeader>
          <CardTitle>Notification Channels</CardTitle>
          <CardDescription>Choose how you want to receive notifications.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="email_channel" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                <span>Email</span>
              </div>
              <span className="font-normal text-muted-foreground">
                Receive notifications via email.
              </span>
            </Label>
            <input
              type="checkbox"
              id="email_channel"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.email_enabled}
              onChange={() => toggleSetting('email_enabled')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="push_channel" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Smartphone className="h-4 w-4" />
                <span>Push Notifications</span>
              </div>
              <span className="font-normal text-muted-foreground">
                Get instant alerts on your device.
              </span>
            </Label>
            <input
              type="checkbox"
              id="push_channel"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.push_enabled}
              onChange={() => toggleSetting('push_enabled')}
              disabled={pushPermissionStatus === 'denied'}
            />
          </div>

          {pushPermissionStatus === 'default' && settings.push_enabled && (
            <div className="rounded-md bg-muted p-3 text-sm">
              <p className="mb-2">Enable push notifications in your browser to receive alerts.</p>
              <Button size="sm" onClick={handleEnablePush}>
                <Bell className="mr-2 h-4 w-4" />
                Enable Push
              </Button>
            </div>
          )}

          {pushPermissionStatus === 'denied' && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              Push notifications are blocked. Please enable them in your browser settings.
            </div>
          )}

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="in_app_channel" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Monitor className="h-4 w-4" />
                <span>In-App Notifications</span>
              </div>
              <span className="font-normal text-muted-foreground">
                Show notifications within the app.
              </span>
            </Label>
            <input
              type="checkbox"
              id="in_app_channel"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.in_app_enabled}
              onChange={() => toggleSetting('in_app_enabled')}
            />
          </div>
        </CardContent>
      </Card>

      {/* Frequency & Digest Card */}
      <Card>
        <CardHeader>
          <CardTitle>Frequency & Digest</CardTitle>
          <CardDescription>Configure how often you receive notification digests.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="alert_frequency">Alert Frequency</Label>
            <select
              id="alert_frequency"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={settings.alert_frequency}
              onChange={(e) =>
                updateSetting(
                  'alert_frequency',
                  e.target.value as 'instant' | 'daily' | 'weekly'
                )
              }
            >
              <option value="instant">Instant</option>
              <option value="daily">Daily Digest</option>
              <option value="weekly">Weekly Digest</option>
            </select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="daily_digest_time">Daily Digest Time</Label>
            <input
              type="time"
              id="daily_digest_time"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={settings.daily_digest_time}
              onChange={(e) => updateSetting('daily_digest_time', e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="weekly_digest_day">Weekly Digest Day</Label>
            <select
              id="weekly_digest_day"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={settings.weekly_digest_day}
              onChange={(e) => updateSetting('weekly_digest_day', e.target.value)}
            >
              {DAYS_OF_WEEK.map((day) => (
                <option key={day} value={day}>
                  {day.charAt(0).toUpperCase() + day.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Settings Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary" />
            <CardTitle>Advanced Settings</CardTitle>
          </div>
          <CardDescription>Fine-tune your notification preferences.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="quiet_hours_start">Quiet Hours Start</Label>
              <input
                type="time"
                id="quiet_hours_start"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={settings.quiet_hours_start || ''}
                onChange={(e) => updateSetting('quiet_hours_start', e.target.value || null)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="quiet_hours_end">Quiet Hours End</Label>
              <input
                type="time"
                id="quiet_hours_end"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={settings.quiet_hours_end || ''}
                onChange={(e) => updateSetting('quiet_hours_end', e.target.value || null)}
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="price_drop_threshold">Price Drop Threshold (%)</Label>
            <input
              type="number"
              id="price_drop_threshold"
              min="1"
              max="50"
              step="0.5"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={settings.price_drop_threshold}
              onChange={(e) => updateSetting('price_drop_threshold', parseFloat(e.target.value))}
            />
            <span className="text-xs text-muted-foreground">
              Only notify when price drops by at least this percentage.
            </span>
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="expert_mode" className="flex flex-col space-y-1">
              <span>Expert Mode</span>
              <span className="font-normal text-muted-foreground">
                Include market trends, indices, and yield analysis.
              </span>
            </Label>
            <input
              type="checkbox"
              id="expert_mode"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.expert_mode}
              onChange={() => toggleSetting('expert_mode')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="marketing_emails" className="flex flex-col space-y-1">
              <span>Product Updates</span>
              <span className="font-normal text-muted-foreground">
                Receive occasional emails about new features.
              </span>
            </Label>
            <input
              type="checkbox"
              id="marketing_emails"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.marketing_emails}
              onChange={() => toggleSetting('marketing_emails')}
            />
          </div>
        </CardContent>
      </Card>

      {/* Test Notifications Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Send className="h-5 w-5 text-primary" />
            <CardTitle>Test Notifications</CardTitle>
          </div>
          <CardDescription>Send a test notification to verify your settings.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSendPreview('email')}
              disabled={sendingPreview || !settings.email_enabled}
            >
              <Mail className="mr-2 h-4 w-4" />
              Test Email
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSendPreview('push')}
              disabled={sendingPreview || !settings.push_enabled}
            >
              <Smartphone className="mr-2 h-4 w-4" />
              Test Push
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSendPreview('in_app')}
              disabled={sendingPreview || !settings.in_app_enabled}
            >
              <Monitor className="mr-2 h-4 w-4" />
              Test In-App
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Unsubscribe Info */}
      {settings.unsubscribe_token && (
        <Card>
          <CardHeader>
            <CardTitle>Unsubscribe</CardTitle>
            <CardDescription>Manage your subscription preferences.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Use this link to unsubscribe from all notifications:{' '}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">
                /unsubscribe/{settings.unsubscribe_token}
              </code>
            </p>
            {settings.unsubscribed_at && (
              <p className="mt-2 text-sm text-destructive">
                You unsubscribed on {new Date(settings.unsubscribed_at).toLocaleDateString()}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Save Button */}
      <div className="flex items-center justify-end gap-4">
        {success && <span className="text-green-600 text-sm">{success}</span>}
        {error && <span className="text-red-600 text-sm">{error}</span>}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Preferences'}
        </Button>
      </div>
    </div>
  );
}
