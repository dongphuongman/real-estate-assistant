'use client';

import React, { useState } from 'react';
import { Loader2, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { createFilterPreset, ApiError } from '@/lib/api';
import type { FilterPreset } from '@/lib/types';

interface SavePresetDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  filters: Record<string, unknown>;
  onSuccess?: (preset: FilterPreset) => void;
}

export function SavePresetDialog({
  isOpen,
  onOpenChange,
  filters,
  onSuccess,
}: SavePresetDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleClose = () => {
    onOpenChange(false);
    setName('');
    setDescription('');
    setIsDefault(false);
    setError(null);
    setSuccess(false);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Please enter a name for this preset');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const preset = await createFilterPreset({
        name: name.trim(),
        description: description.trim() || undefined,
        filters,
        is_default: isDefault,
      });
      setSuccess(true);
      setTimeout(() => {
        handleClose();
        onSuccess?.(preset);
      }, 1000);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.category === 'auth') {
          setError('Please log in to save filter presets');
        } else if (err.status === 400) {
          setError(err.message);
        } else {
          setError(err.message);
        }
      } else {
        setError(err instanceof Error ? err.message : 'Failed to save preset');
      }
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-preset-title"
    >
      <div className="bg-background rounded-lg p-6 max-w-md w-full mx-4 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold" id="save-preset-title">
            Save Filter Preset
          </h2>
          <button
            onClick={handleClose}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {success ? (
          <div className="text-center py-4">
            <div className="text-green-600 mb-2">Preset saved successfully!</div>
            <p className="text-sm text-muted-foreground">
              You can quickly apply these filters from the presets menu.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label htmlFor="preset-name" className="block text-sm font-medium mb-1">
                Preset Name <span className="text-destructive">*</span>
              </label>
              <input
                id="preset-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Budget Apartments in Berlin"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                maxLength={255}
                autoFocus
              />
            </div>

            <div>
              <label htmlFor="preset-description" className="block text-sm font-medium mb-1">
                Description (optional)
              </label>
              <textarea
                id="preset-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of this preset..."
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                rows={2}
                maxLength={1000}
              />
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isDefault}
                onChange={(e) => setIsDefault(e.target.checked)}
                className="rounded border-input"
              />
              <span className="text-sm">Set as default preset</span>
            </label>

            <div className="text-sm text-muted-foreground">
              Saves your current filter settings for quick access later.
            </div>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={handleClose} disabled={saving}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" aria-hidden="true" />
                    Saving...
                  </>
                ) : (
                  'Save Preset'
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
