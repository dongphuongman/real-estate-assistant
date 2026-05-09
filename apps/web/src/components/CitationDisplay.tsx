'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import type { CitationConfidence, CitationStats, EnhancedCitation, SourceType } from '@/lib/types';

interface CitationDisplayProps {
  citations: EnhancedCitation[];
  stats?: CitationStats | null;
  truncated?: boolean;
  defaultExpanded?: boolean;
}

// Source type icons and colors
const SOURCE_TYPE_CONFIG: Record<SourceType, { icon: string; color: string; label: string }> = {
  pdf: { icon: '📄', color: 'text-red-500', label: 'PDF' },
  docx: { icon: '📝', color: 'text-blue-500', label: 'DOCX' },
  web: { icon: '🌐', color: 'text-green-500', label: 'Web' },
  database: { icon: '🗄️', color: 'text-purple-500', label: 'Database' },
  api: { icon: '🔌', color: 'text-orange-500', label: 'API' },
  unknown: { icon: '📎', color: 'text-gray-500', label: 'Source' },
};

// Confidence colors
const CONFIDENCE_COLORS: Record<CitationConfidence, string> = {
  high: 'bg-green-100 text-green-800 border-green-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-red-100 text-red-800 border-red-200',
};

function SourceTypeIcon({ type, label }: { type: SourceType; label: string }) {
  const config = SOURCE_TYPE_CONFIG[type] || SOURCE_TYPE_CONFIG.unknown;
  return (
    <span className={config.color} title={label}>
      {config.icon}
    </span>
  );
}

function ConfidenceBadge({
  confidence,
  score,
  t,
}: {
  confidence: CitationConfidence;
  score: number;
  t: (key: string, params?: Record<string, string | number | Date>) => string;
}) {
  const colorClass = CONFIDENCE_COLORS[confidence] || CONFIDENCE_COLORS.medium;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colorClass}`}
      title={t('confidenceScore', { score: (score * 100).toFixed(0) })}
    >
      {confidence}
    </span>
  );
}

function SingleCitation({ citation, index }: { citation: EnhancedCitation; index: number }) {
  const t = useTranslations('chat.sources');
  const [expanded, setExpanded] = useState(false);

  const title = citation.source_title || citation.source || `${t('source')} ${index + 1}`;
  const hasSnippet = citation.content_snippet && citation.content_snippet.length > 0;
  const snippetLength = citation.content_snippet?.length || 0;

  return (
    <li className="space-y-1 py-2 border-b border-gray-100 last:border-b-0">
      {/* Header row */}
      <div className="flex items-start gap-2">
        <span className="text-gray-400 text-xs mt-0.5">[{index + 1}]</span>
        <div className="flex-1 min-w-0">
          {/* Title and type */}
          <div className="flex items-center gap-2 flex-wrap">
            <SourceTypeIcon
              type={citation.source_type}
              label={t('types.' + citation.source_type)}
            />
            <span className="text-sm font-medium break-words">{title}</span>
            {citation.is_duplicate && (
              <span className="text-xs text-gray-400 italic">({t('duplicate')})</span>
            )}
            {citation.validated && (
              <span className="text-xs text-green-600" title={t('validated')}>
                ✓
              </span>
            )}
          </div>

          {/* Confidence and metadata */}
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <ConfidenceBadge
              confidence={citation.confidence}
              score={citation.confidence_score}
              t={t}
            />
            {citation.page_number && (
              <span className="text-xs text-gray-500">
                {t('page', { page: citation.page_number })}
              </span>
            )}
            {citation.chunk_index !== undefined && citation.chunk_index !== null && (
              <span className="text-xs text-gray-500">
                {t('chunk', { index: citation.chunk_index })}
              </span>
            )}
          </div>

          {/* Source URL for web sources */}
          {citation.source_url && (
            <a
              href={citation.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline mt-1 block truncate"
            >
              {citation.source_url}
            </a>
          )}
        </div>
      </div>

      {/* Content snippet */}
      {hasSnippet && (
        <div className="ml-6 mt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
            aria-expanded={expanded}
          >
            {expanded ? '▼' : '▶'}
            {expanded ? t('hideSnippet') : t('showSnippet')}
            {snippetLength > 200 && t('snippetLength', { chars: snippetLength })}
          </button>
          {expanded && (
            <div className="mt-1 text-xs text-gray-600 bg-gray-50 rounded p-2 font-mono break-words">
              {citation.content_snippet}
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function CitationSummary({ stats }: { stats: CitationStats }) {
  const t = useTranslations('chat.sources');
  return (
    <div className="flex flex-wrap gap-3 text-xs text-gray-600 mb-2">
      <span>{t('summary.total', { count: stats.total })}</span>
      <span>{t('summary.unique', { count: stats.unique })}</span>
      {stats.duplicates > 0 && (
        <span className="text-gray-400">
          {t('summary.duplicates', { count: stats.duplicates })}
        </span>
      )}
      <span>{t('summary.avgConfidence', { score: (stats.avg_confidence * 100).toFixed(0) })}</span>
      {Object.entries(stats.by_type).map(([type, count]) => (
        <span key={type} className="text-gray-500">
          {t('types.' + type)}: <strong>{count}</strong>
        </span>
      ))}
    </div>
  );
}

export function CitationDisplay({
  citations,
  stats,
  truncated = false,
  defaultExpanded = false,
}: CitationDisplayProps) {
  const t = useTranslations('chat.sources');
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <details
      className="rounded-md border bg-muted/30 px-3 py-2 text-xs"
      open={isOpen}
      onToggle={() => setIsOpen(!isOpen)}
    >
      <summary className="cursor-pointer select-none font-medium flex items-center gap-2">
        <span>{t('titleWithCount', { count: citations.length })}</span>
        {truncated && <span className="text-gray-400 italic">({t('truncated')})</span>}
      </summary>

      {/* Stats summary */}
      {stats && <CitationSummary stats={stats} />}

      {/* Citation list */}
      <ol className="mt-2 list-none pl-0 space-y-0">
        {citations.map((citation, i) => (
          <SingleCitation
            key={citation.citation_hash || `${citation.source}-${i}`}
            citation={citation}
            index={i}
          />
        ))}
      </ol>
    </details>
  );
}

export default CitationDisplay;
