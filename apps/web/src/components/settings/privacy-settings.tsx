'use client';

import React, { useEffect, useState } from 'react';
import { Shield, Download, Loader2, Eye, EyeOff, Mail, Phone, MessageSquare, FileText, Clock } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import {
  getProfile,
  updatePrivacySettings,
  requestDataExport,
  getExportStatus,
} from '@/lib/api';
import {
  ProfileResponse,
  PrivacySettings as PrivacySettingsType,
  DataExportRequest,
  DataExportStatusResponse,
} from '@/lib/types';

export function PrivacySettings() {
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Privacy settings state
  const [settings, setSettings] = useState<PrivacySettingsType>({
    profile_visible: true,
    activity_visible: false,
    show_email: false,
    show_phone: false,
    allow_contact: true,
  });

  // Export state
  const [exporting, setExporting] = useState(false);
  const [exportJob, setExportJob] = useState<DataExportStatusResponse | null>(null);
  const [pollingExport, setPollingExport] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, []);

  // Poll export status when job is processing
  useEffect(() => {
    if (!pollingExport || !exportJob || exportJob.status === 'completed' || exportJob.status === 'failed') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const status = await getExportStatus(exportJob.export_id);
        setExportJob(status);

        if (status.status === 'completed' || status.status === 'failed') {
          setPollingExport(false);
        }
      } catch {
        setPollingExport(false);
        setError('Failed to check export status.');
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [pollingExport, exportJob]);

  const fetchProfile = async () => {
    try {
      const data = await getProfile();
      setProfile(data);
      if (data.privacy_settings) {
        setSettings({
          profile_visible: data.privacy_settings.profile_visible ?? true,
          activity_visible: data.privacy_settings.activity_visible ?? false,
          show_email: data.privacy_settings.show_email ?? false,
          show_phone: data.privacy_settings.show_phone ?? false,
          allow_contact: data.privacy_settings.allow_contact ?? true,
        });
      }
      setError(null);
    } catch {
      setError('Failed to load privacy settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4 text-center">Loading privacy settings...</div>;
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updated = await updatePrivacySettings(settings);
      setProfile(updated);
      setSuccess('Privacy settings saved successfully.');
    } catch {
      setError('Failed to save privacy settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const toggleSetting = (key: keyof PrivacySettingsType) => {
    setSettings({ ...settings, [key]: !settings[key] });
  };

  const handleExportData = async () => {
    setExporting(true);
    setError(null);
    setExportJob(null);

    try {
      const request: DataExportRequest = {
        format: 'json',
        include_favorites: true,
        include_search_history: true,
        include_documents: true,
      };
      const response = await requestDataExport(request);
      setExportJob({
        export_id: response.export_id,
        status: response.status,
        progress_percent: 0,
        download_url: null,
        expires_at: null,
        error_message: null,
        created_at: response.created_at,
        completed_at: null,
      });
      setPollingExport(true);
      setSuccess('Data export started. You will be able to download shortly.');
    } catch {
      setError('Failed to start data export. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const handleDownload = () => {
    if (exportJob?.download_url) {
      window.open(exportJob.download_url, '_blank');
    }
  };

  return (
    <div className="grid gap-6">
      {/* Privacy Controls Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <CardTitle>Privacy Controls</CardTitle>
          </div>
          <CardDescription>Control what information is visible to others.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="profile_visible" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                {settings.profile_visible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                <span>Public Profile</span>
              </div>
              <span className="font-normal text-muted-foreground">
                Allow others to see your profile information.
              </span>
            </Label>
            <input
              type="checkbox"
              id="profile_visible"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.profile_visible}
              onChange={() => toggleSetting('profile_visible')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="activity_visible" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                {settings.activity_visible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                <span>Activity Visibility</span>
              </div>
              <span className="font-normal text-muted-foreground">
                Show your activity (searches, favorites) to others.
              </span>
            </Label>
            <input
              type="checkbox"
              id="activity_visible"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.activity_visible}
              onChange={() => toggleSetting('activity_visible')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="show_email" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                <span>Show Email</span>
              </div>
              <span className="font-normal text-muted-foreground">
                Display your email address on your public profile.
              </span>
            </Label>
            <input
              type="checkbox"
              id="show_email"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.show_email}
              onChange={() => toggleSetting('show_email')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="show_phone" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4" />
                <span>Show Phone</span>
              </div>
              <span className="font-normal text-muted-foreground">
                Display your phone number on your public profile.
              </span>
            </Label>
            <input
              type="checkbox"
              id="show_phone"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.show_phone}
              onChange={() => toggleSetting('show_phone')}
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="allow_contact" className="flex flex-col space-y-1">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                <span>Allow Contact</span>
              </div>
              <span className="font-normal text-muted-foreground">
                Allow other users to send you messages.
              </span>
            </Label>
            <input
              type="checkbox"
              id="allow_contact"
              className="h-4 w-4 rounded border-gray-300"
              checked={settings.allow_contact}
              onChange={() => toggleSetting('allow_contact')}
            />
          </div>
        </CardContent>
      </Card>

      {/* GDPR Data Export Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <CardTitle>Data Export (GDPR)</CardTitle>
          </div>
          <CardDescription>
            Request a copy of your personal data in compliance with GDPR regulations.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-sm text-muted-foreground">
            <p className="mb-2">
              You can request an export of all your personal data stored in our system.
              This includes:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Profile information</li>
              <li>Saved favorites</li>
              <li>Search history</li>
              <li>Uploaded documents</li>
            </ul>
            <p className="mt-2">
              Export requests are processed in the background and may take a few minutes.
              Download links expire after 24 hours.
            </p>
          </div>

          {/* Export Status */}
          {exportJob && (
            <div className="rounded-md bg-muted p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Export Status</span>
                <span className={`text-sm ${
                  exportJob.status === 'completed' ? 'text-green-600' :
                  exportJob.status === 'failed' ? 'text-red-600' :
                  'text-yellow-600'
                }`}>
                  {exportJob.status.charAt(0).toUpperCase() + exportJob.status.slice(1)}
                </span>
              </div>

              {exportJob.status === 'processing' && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Progress</span>
                    <span>{exportJob.progress_percent}%</span>
                  </div>
                  <div className="h-2 bg-muted-foreground/20 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${exportJob.progress_percent}%` }}
                    />
                  </div>
                </div>
              )}

              {exportJob.status === 'completed' && exportJob.download_url && (
                <Button onClick={handleDownload} className="w-full">
                  <Download className="mr-2 h-4 w-4" />
                  Download Your Data
                </Button>
              )}

              {exportJob.status === 'failed' && exportJob.error_message && (
                <p className="text-sm text-red-600">{exportJob.error_message}</p>
              )}

              {exportJob.expires_at && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>
                    Link expires: {new Date(exportJob.expires_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Export Button */}
          <Button
            variant="outline"
            onClick={handleExportData}
            disabled={exporting || pollingExport}
          >
            {exporting || pollingExport ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            {exporting ? 'Starting Export...' : pollingExport ? 'Processing...' : 'Request Data Export'}
          </Button>

          {profile?.gdpr_consent_at && (
            <p className="text-xs text-muted-foreground">
              GDPR consent given on {new Date(profile.gdpr_consent_at).toLocaleDateString()}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex items-center justify-end gap-4">
        {success && <span className="text-green-600 text-sm">{success}</span>}
        {error && <span className="text-red-600 text-sm">{error}</span>}
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Privacy Settings'}
        </Button>
      </div>
    </div>
  );
}
