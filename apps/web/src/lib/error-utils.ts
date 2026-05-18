import { ApiError } from '@/lib/api';

export interface ErrorState {
  message: string;
  requestId?: string;
}

export const extractErrorState = (err: unknown): ErrorState => {
  if (err instanceof ApiError) {
    return { message: err.message, requestId: err.request_id };
  }
  if (err instanceof Error) {
    return { message: err.message };
  }
  return { message: String(err) };
};
