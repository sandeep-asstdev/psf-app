/**
 * ============================================================================
 * FILE PURPOSE: Custom Dealership Terminology React Hook.
 * Allows replacing fixed terms (CRE, Delight, TNPS, Job Card, Complaint, etc.)
 * with dealer-configured labels.
 * Usage:
 *   const cre = useLabel("CRE", "CRE");
 *   const { t } = useLabel();
 * ============================================================================
 */
import { useEffect } from 'react';
import { useLabelStore, DEFAULT_SYSTEM_LABELS } from '../store/labelStore';

export function useLabel(term = null, defaultFallback = null) {
  const { labels, getLabel, fetchLabels, updateLabels, isLoading } = useLabelStore();

  useEffect(() => {
    if (Object.keys(labels).length <= Object.keys(DEFAULT_SYSTEM_LABELS).length) {
      fetchLabels();
    }
  }, [fetchLabels, labels]);

  if (term !== null) {
    return getLabel(term, defaultFallback);
  }

  return {
    t: (key, fallback = null) => getLabel(key, fallback),
    labels,
    fetchLabels,
    updateLabels,
    isLoading,
  };
}

export default useLabel;
