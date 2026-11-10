import React, { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function ImportTemplatesTab() {
  const [importTemplates, setImportTemplates] = useState([]);
  const [importTemplateModal, setImportTemplateModal] = useState(false);
  const [newTemplateForm, setNewTemplateForm] = useState({
    brand_id: '',
    template_name: '',
    file_type: 'CSV',
    is_default: true,
    mapping_json: '{\n  "job_card_no": "Job Card No",\n  "customer_name": "Customer Name",\n  "customer_phone": "Customer Mobile",\n  "vehicle_reg_no": "Reg No",\n  "vehicle_model": "Model",\n  "service_type": "Service Type"\n}',
  });

  const loadImportTemplates = async () => {
    try {
      const res = await api.get('/admin/import-templates');
      setImportTemplates(res.data);
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadImportTemplates();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-foreground">DMS Import Column Mapping Templates</h2>
        <button
          onClick={() => setImportTemplateModal(true)}
          className="flex items-center space-x-1.5 rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Add Template</span>
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {importTemplates.map((tmpl) => (
          <div key={tmpl.id} className="p-4 rounded-lg border border-border bg-background-surface space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-foreground">{tmpl.template_name}</span>
              {tmpl.is_default && (
                <span className="rounded bg-accent px-2 py-0.5 text-[10px] font-bold text-accent-foreground">Default</span>
              )}
            </div>
            <div className="text-[11px] text-foreground-subtle">File Type: {tmpl.file_type}</div>
            <pre className="p-2 rounded bg-background-base text-[10px] font-mono overflow-x-auto max-h-36">
              {JSON.stringify(tmpl.mapping, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}

