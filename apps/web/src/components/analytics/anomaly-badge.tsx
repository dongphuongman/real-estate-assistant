'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import type { AnomalySeverity, AnomalyType } from '@/lib/types';

const anomalySeverityVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      severity: {
        low: 'border-transparent bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
        medium:
          'border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        high: 'border-transparent bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
        critical: 'border-transparent bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      },
    },
    defaultVariants: {
      severity: 'low',
    },
  }
);

const anomalyTypeVariants = cva(
  'inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium',
  {
    variants: {
      type: {
        price_spike: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
        price_drop: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
        volume_spike: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
        volume_drop: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
        unusual_pattern: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
      },
    },
    defaultVariants: {
      type: 'unusual_pattern',
    },
  }
);

export interface AnomalySeverityBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof anomalySeverityVariants> {
  severity: AnomalySeverity;
}

export function AnomalySeverityBadge({ severity, className, ...props }: AnomalySeverityBadgeProps) {
  const labels: Record<AnomalySeverity, string> = {
    low: 'Low',
    medium: 'Medium',
    high: 'High',
    critical: 'Critical',
  };

  return (
    <span className={cn(anomalySeverityVariants({ severity }), className)} {...props}>
      {labels[severity]}
    </span>
  );
}

export interface AnomalyTypeBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof anomalyTypeVariants> {
  type: AnomalyType;
}

export function AnomalyTypeBadge({ type, className, ...props }: AnomalyTypeBadgeProps) {
  const labels: Record<AnomalyType, string> = {
    price_spike: 'Price Spike',
    price_drop: 'Price Drop',
    volume_spike: 'Volume Spike',
    volume_drop: 'Volume Drop',
    unusual_pattern: 'Unusual Pattern',
  };

  const icons: Record<AnomalyType, React.ReactNode> = {
    price_spike: (
      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
        />
      </svg>
    ),
    price_drop: (
      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"
        />
      </svg>
    ),
    volume_spike: (
      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
    volume_drop: (
      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2zm6 0v-4a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
    unusual_pattern: (
      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
  };

  return (
    <span className={cn(anomalyTypeVariants({ type }), className)} {...props}>
      {icons[type]}
      {labels[type]}
    </span>
  );
}

export { anomalySeverityVariants, anomalyTypeVariants };
