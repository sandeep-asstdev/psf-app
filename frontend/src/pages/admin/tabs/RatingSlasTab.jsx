import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function RatingSlasTab() {
  const [ratingScales, setRatingScales] = useState([]);

  const loadRatingScales = async () => {
    try {
      const res = await api.get('/masters/rating-scales');
      setRatingScales(res.data);
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadRatingScales();
  }, []);

  const handleToggleComplaintTrigger = async (scaleId, band) => {
    try {
      await api.put(`/masters/rating-scales/${scaleId}/bands/${band.id}`, {
        is_complaint_trigger: !band.is_complaint_trigger,
      });
      toast.success(`Updated band '${band.label}': Complaint trigger set to ${!band.is_complaint_trigger}`);
      loadRatingScales();
    } catch (err) {
      toast.error('Failed to update rating band trigger');
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-background-surface p-4 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-foreground">Brand Rating Scales & Complaint Triggers</h2>
          <p className="text-xs text-foreground-subtle">
            Rating bands partition CSAT outcomes. Toggle the complaint trigger to automatically escalate low ratings (including Hyundai score 9).
          </p>
        </div>

        <div className="space-y-4">
          {ratingScales.map((scale) => (
            <div key={scale.id} className="p-4 rounded-lg border border-border bg-background-base space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-foreground">{scale.name}</span>
                  <span className="text-[11px] text-foreground-subtle ml-2">Brand: {scale.brand_name} (Max {scale.max_rating})</span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                {(scale.bands || []).map((band) => (
                  <div key={band.id} className="p-2.5 rounded-lg border border-border bg-background-surface space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-foreground">{band.label}</span>
                      <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-background-base">
                        {band.min_score === band.max_score ? band.min_score : `${band.min_score}-${band.max_score}`}
                      </span>
                    </div>
                    <div className="text-[10px] text-foreground-subtle">
                      Derived Status: <span className="font-semibold">{band.derived_case_status}</span>
                    </div>
                    <div className="pt-1 flex items-center justify-between border-t border-border/50 text-[10px]">
                      <span className={band.is_complaint_trigger ? 'text-status-danger font-bold' : 'text-foreground-subtle'}>
                        {band.is_complaint_trigger ? 'Triggers Complaint' : 'No Complaint'}
                      </span>
                      <button
                        onClick={() => handleToggleComplaintTrigger(scale.id, band)}
                        className="px-2 py-0.5 rounded text-[10px] font-semibold bg-accent-subtle text-accent hover:bg-accent hover:text-accent-foreground transition-colors"
                      >
                        Toggle Trigger
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
