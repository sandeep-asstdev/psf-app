import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function TemplatesSettingsTab() {
  const [settingsForm, setSettingsForm] = useState({
    sms_satisfaction: 'Dear Customer, thank you for servicing your vehicle with us.',
    whatsapp_complaint_opened: 'Hello {{customer_name}}, your complaint {{ticket_no}} has been registered.',
    dealer_name: 'Apex Automotive Group',
    primary_color: '#2563EB',
    logo_url: '',
  });

  useEffect(() => {
    api.get('/masters/settings').then((res) => {
      if (res.data?.theme) {
        setSettingsForm((prev) => ({
          ...prev,
          dealer_name: res.data.theme.dealer_name || prev.dealer_name,
          primary_color: res.data.theme.primary_color || prev.primary_color,
          logo_url: res.data.theme.logo_url || prev.logo_url,
        }));
      }
      if (res.data?.templates) {
        setSettingsForm((prev) => ({
          ...prev,
          sms_satisfaction: res.data.templates.sms_satisfaction || prev.sms_satisfaction,
          whatsapp_complaint_opened: res.data.templates.whatsapp_complaint_opened || prev.whatsapp_complaint_opened,
        }));
      }
    }).catch(() => {});
  }, []);

  const handleSaveSettings = async () => {
    try {
      await api.put('/masters/settings', {
        config_key: 'templates',
        config_value: {
          sms_satisfaction: settingsForm.sms_satisfaction,
          whatsapp_complaint_opened: settingsForm.whatsapp_complaint_opened,
        },
      });
      await api.put('/masters/settings', {
        config_key: 'theme',
        config_value: {
          dealer_name: settingsForm.dealer_name,
          primary_color: settingsForm.primary_color,
        },
      });
      toast.success('App branding & templates updated successfully.');
    } catch (err) {
      toast.error('Failed to update settings');
    }
  };

  return (
    <div className="space-y-4 max-w-xl">
      <div>
        <h2 className="text-sm font-bold text-foreground">App Branding & Notification Templates</h2>
        <p className="text-xs text-foreground-subtle">Configure dealer white-label appearance and automated customer SMS/WhatsApp messages.</p>
      </div>

      <div className="p-4 rounded-lg border border-border bg-background-surface space-y-4">
        <div>
          <label className="block text-xs font-semibold text-foreground mb-1">Dealership Display Name</label>
          <input
            type="text"
            value={settingsForm.dealer_name}
            onChange={(e) => setSettingsForm((prev) => ({ ...prev, dealer_name: e.target.value }))}
            className="w-full rounded-lg border border-border bg-background-base px-3 py-1.5 text-xs text-foreground"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-foreground mb-1">Primary Brand Hex Color</label>
          <div className="flex items-center space-x-2">
            <input
              type="color"
              value={settingsForm.primary_color}
              onChange={(e) => setSettingsForm((prev) => ({ ...prev, primary_color: e.target.value }))}
              className="h-8 w-8 rounded border-0 cursor-pointer"
            />
            <input
              type="text"
              value={settingsForm.primary_color}
              onChange={(e) => setSettingsForm((prev) => ({ ...prev, primary_color: e.target.value }))}
              className="w-28 rounded-lg border border-border bg-background-base px-2 py-1 text-xs text-foreground font-mono"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-foreground mb-1">SMS Post-Service Satisfaction Template</label>
          <textarea
            rows={3}
            value={settingsForm.sms_satisfaction}
            onChange={(e) => setSettingsForm((prev) => ({ ...prev, sms_satisfaction: e.target.value }))}
            className="w-full rounded-lg border border-border bg-background-base p-2 text-xs text-foreground"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-foreground mb-1">WhatsApp Escalated Complaint Opened Template</label>
          <textarea
            rows={3}
            value={settingsForm.whatsapp_complaint_opened}
            onChange={(e) => setSettingsForm((prev) => ({ ...prev, whatsapp_complaint_opened: e.target.value }))}
            className="w-full rounded-lg border border-border bg-background-base p-2 text-xs text-foreground"
          />
        </div>

        <button
          onClick={handleSaveSettings}
          className="w-full rounded-lg bg-accent px-3 py-2 text-xs font-bold text-accent-foreground hover:bg-accent/90"
        >
          Save Branding & Templates
        </button>
      </div>
    </div>
  );
}

