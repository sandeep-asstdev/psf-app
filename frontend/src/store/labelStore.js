/**
 * ============================================================================
 * FILE PURPOSE: Multi-Tenant Configurable Labels & Terminology Store.
 * Provides custom dealership terminology overrides (CRE, Delight, TNPS, Job Card, Complaint).
 * ============================================================================
 */
import { create } from 'zustand';
import api from '../services/api';

export const DEFAULT_SYSTEM_LABELS = {
  CRE: 'Customer Relationship Executive',
  DELIGHT: 'Delight',
  TNPS: 'Follow-up Program',
  JOB_CARD: 'Job Card',
  COMPLAINT: 'Customer Complaint',
  CUSTOMER: 'Customer',
  ADVISOR: 'Service Advisor',
  BRANCH: 'Branch',
  BRAND: 'Brand',
  SURVEY: 'Survey',
};

export const useLabelStore = create((set, get) => ({
  labels: {
    ...DEFAULT_SYSTEM_LABELS,
    ...JSON.parse(localStorage.getItem('psf_labels') || '{}'),
  },
  isLoading: false,

  fetchLabels: async () => {
    try {
      set({ isLoading: true });
      const res = await api.get('/config/labels');
      if (res.data) {
        const merged = { ...DEFAULT_SYSTEM_LABELS, ...res.data };
        localStorage.setItem('psf_labels', JSON.stringify(merged));
        set({ labels: merged, isLoading: false });
      }
    } catch (err) {
      // Fallback silently to defaults
      set({ isLoading: false });
    }
  },

  updateLabels: async (labelsMap) => {
    try {
      set({ isLoading: true });
      const res = await api.post('/config/labels', { labels: labelsMap, language: 'en' });
      if (res.data) {
        const merged = { ...DEFAULT_SYSTEM_LABELS, ...res.data };
        localStorage.setItem('psf_labels', JSON.stringify(merged));
        set({ labels: merged, isLoading: false });
        return { success: true };
      }
    } catch (err) {
      set({ isLoading: false });
      return { success: false, error: err };
    }
  },

  getLabel: (key, fallback = null) => {
    const { labels } = get();
    if (!key) return '';
    const upperKey = key.toUpperCase().trim();
    if (labels[upperKey]) return labels[upperKey];
    if (labels[key]) return labels[key];
    if (fallback !== null) return fallback;
    if (DEFAULT_SYSTEM_LABELS[upperKey]) return DEFAULT_SYSTEM_LABELS[upperKey];
    return key;
  },
}));
