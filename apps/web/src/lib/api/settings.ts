/**
 * Settings API: notification settings, model catalog, model preferences, per-task model preferences.
 */

import type {
  ModelProviderCatalog,
  ModelPreferences,
  ModelRuntimeTestResponse,
  NotificationSettings,
  NotificationSettingsUpdate,
  NotificationPreviewRequest,
  NotificationPreviewResponse,
  TaskType,
  TaskModelPreference,
  TaskModelPreferenceCreate,
  TaskModelPreferenceUpdate,
  TaskModelPreferenceListResponse,
  SystemDefaultsResponse,
  ModelCostEstimate,
} from '../types';

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';
export { ApiError } from './client';

export async function getNotificationSettings(): Promise<NotificationSettings> {
  const response = await safeFetch(`${getApiUrl()}/settings/notifications`, {
    method: 'GET',
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<NotificationSettings>(response);
}

export async function updateNotificationSettings(
  settings: NotificationSettingsUpdate
): Promise<NotificationSettings> {
  const response = await fetch(`${getApiUrl()}/settings/notifications`, {
    method: 'PUT',
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(settings),
  });
  return handleResponse<NotificationSettings>(response);
}

export async function sendNotificationPreview(
  request: NotificationPreviewRequest
): Promise<NotificationPreviewResponse> {
  const response = await fetch(`${getApiUrl()}/settings/notifications/preview`, {
    method: 'POST',
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(request),
  });
  return handleResponse<NotificationPreviewResponse>(response);
}

export async function unsubscribeByToken(
  token: string,
  notificationType?: string
): Promise<{ success: boolean; message: string }> {
  const url = notificationType
    ? `${getApiUrl()}/settings/notifications/unsubscribe/${token}?notification_type=${encodeURIComponent(notificationType)}`
    : `${getApiUrl()}/settings/notifications/unsubscribe/${token}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<{ success: boolean; message: string }>(response);
}

export async function getModelsCatalog(): Promise<ModelProviderCatalog[]> {
  const response = await fetch(`${getApiUrl()}/settings/models`, {
    method: 'GET',
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<ModelProviderCatalog[]>(response);
}

export async function testModelRuntime(provider: string): Promise<ModelRuntimeTestResponse> {
  const response = await fetch(
    `${getApiUrl()}/settings/test-runtime?provider=${encodeURIComponent(provider)}`,
    {
      method: 'GET',
      headers: {
        ...buildHeaders(),
      },
    }
  );
  return handleResponse<ModelRuntimeTestResponse>(response);
}

export async function getModelPreferences(): Promise<ModelPreferences> {
  const response = await fetch(`${getApiUrl()}/settings/model-preferences`, {
    method: 'GET',
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<ModelPreferences>(response);
}

export async function updateModelPreferences(
  payload: Partial<ModelPreferences>
): Promise<ModelPreferences> {
  const response = await fetch(`${getApiUrl()}/settings/model-preferences`, {
    method: 'PUT',
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<ModelPreferences>(response);
}

// =============================================================================
// Task #87: Per-Task Model Preferences API
// =============================================================================

export async function getTaskModelPreferences(): Promise<TaskModelPreferenceListResponse> {
  const response = await fetch(`${getApiUrl()}/model-preferences`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<TaskModelPreferenceListResponse>(response);
}

export async function getTaskModelPreference(taskType: TaskType): Promise<TaskModelPreference> {
  const response = await fetch(`${getApiUrl()}/model-preferences/${encodeURIComponent(taskType)}`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<TaskModelPreference>(response);
}

export async function createTaskModelPreference(
  data: TaskModelPreferenceCreate
): Promise<TaskModelPreference> {
  const response = await fetch(`${getApiUrl()}/model-preferences`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<TaskModelPreference>(response);
}

export async function updateTaskModelPreference(
  preferenceId: string,
  data: TaskModelPreferenceUpdate
): Promise<TaskModelPreference> {
  const response = await fetch(
    `${getApiUrl()}/model-preferences/${encodeURIComponent(preferenceId)}`,
    {
      method: 'PUT',
      headers: buildHeaders(),
      body: JSON.stringify(data),
    }
  );
  return handleResponse<TaskModelPreference>(response);
}

export async function deleteTaskModelPreference(preferenceId: string): Promise<void> {
  const response = await fetch(
    `${getApiUrl()}/model-preferences/${encodeURIComponent(preferenceId)}`,
    {
      method: 'DELETE',
      headers: buildHeaders(),
    }
  );
  // 204 No Content - no body to parse
  if (!response.ok) {
    await handleResponse<void>(response);
  }
}

export async function getSystemModelDefaults(): Promise<SystemDefaultsResponse> {
  const response = await fetch(`${getApiUrl()}/model-preferences/system/defaults`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<SystemDefaultsResponse>(response);
}

export async function getModelCostEstimate(
  provider: string,
  modelName: string,
  estimatedTokens: number = 1000
): Promise<ModelCostEstimate> {
  const params = new URLSearchParams({
    provider,
    model_name: modelName,
    estimated_tokens: estimatedTokens.toString(),
  });
  const response = await fetch(
    `${getApiUrl()}/model-preferences/system/cost-estimate?${params.toString()}`,
    {
      method: 'GET',
      headers: buildHeaders(),
    }
  );
  return handleResponse<ModelCostEstimate>(response);
}
