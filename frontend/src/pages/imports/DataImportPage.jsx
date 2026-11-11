/**
 * ============================================================================
 * FILE PURPOSE: DMS Data Import & Automatic Call Allocation Page.
 * Allows CRE Admins and Super Admins to upload dealer management system (DMS) Excel/CSV files.
 * Automatically divides imported customer calls EQUALLY among active present CREs in 1 click.
 * 
 * KEY RESPONSIBILITIES:
 * - Provides drag-and-drop file upload supporting `.xlsx`, `.xls`, and `.csv`.
 * - Provides downloadable 13-column Standard DMS sample templates (Excel and CSV).
 * - Submits file to `POST /api/v1/imports/upload-and-process`.
 * - Displays instant import summary: job cards created, duplicates skipped, and caller allocation breakdown.
 * - Provides downloadable Excel error reports for rows with bad data.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Toast error: 'Unknown Branch [NAME]'
 *   -> Cause: The branch name in the Excel file does not match any branch in the database.
 *   -> What should you do: Create the Branch in Enterprise Admin under Masters, or correct the branch spelling in the Excel file.
 * - Error: Toast error: 'Duplicate file upload'
 *   -> Cause: The exact same file was already imported.
 *   -> What should you do: Check the recent import batches table below to see when it was imported.
 * ============================================================================
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Users,
  Download,
  XCircle,
  FileText,
  Clock,
  UserCheck,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function DataImportPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  // Fallback masters (if file lacks Brand/Branch headers)
  const [brands, setBrands] = useState([]);
  const [branches, setBranches] = useState([]);
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [selectedBranchId, setSelectedBranchId] = useState('');
  const [loadingMasters, setLoadingMasters] = useState(true);
  const [duplicateAction, setDuplicateAction] = useState('SKIP');

  // Ingestion Result
  const [importResult, setImportResult] = useState(null);
  const [recentBatches, setRecentBatches] = useState([]);
  const [loadingBatches, setLoadingBatches] = useState(false);

  useEffect(() => {
    fetchMasters();
    fetchRecentBatches();
  }, []);

  const fetchMasters = async () => {
    try {
      setLoadingMasters(true);
      const [brandsRes, branchesRes] = await Promise.all([
        api.get('/masters/brands'),
        api.get('/masters/branches'),
      ]);
      setBrands(brandsRes.data || []);
      setBranches(branchesRes.data || []);
      if (brandsRes.data?.length > 0) setSelectedBrandId(brandsRes.data[0].id);
      if (branchesRes.data?.length > 0) setSelectedBranchId(branchesRes.data[0].id);
    } catch (err) {
      console.error('Failed to load masters:', err);
    } finally {
      setLoadingMasters(false);
    }
  };

  const fetchRecentBatches = async () => {
    try {
      setLoadingBatches(true);
      const res = await api.get('/imports/batches?limit=10');
      setRecentBatches(res.data || []);
    } catch (err) {
      console.error('Failed to load recent batches:', err);
    } finally {
      setLoadingBatches(false);
    }
  };

  // File selection
  const handleFileDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    const validExts = ['.xlsx', '.xls', '.csv'];
    const lowerName = file.name.toLowerCase();
    if (!validExts.some((ext) => lowerName.endsWith(ext))) {
      toast.error('Please upload an Excel (.xlsx/.xls) or CSV file.');
      return;
    }
    setSelectedFile(file);
    setImportResult(null);
  };

  // 1-Click Import & Assign
  const handleImport = async () => {
    if (!selectedFile) {
      toast.error('Please select a file to import');
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (selectedBrandId) formData.append('brand_id', selectedBrandId);
      if (selectedBranchId) formData.append('branch_id', selectedBranchId);
      formData.append('duplicate_action', duplicateAction);
      formData.append('confirm_duplicate_hash', 'true');

      const res = await api.post('/imports/upload-and-process', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setImportResult(res.data);
      toast.success(
        `Successfully imported ${res.data.success_rows} job cards and assigned calls!`,
        { duration: 5000 }
      );
      fetchRecentBatches();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : detail?.message || 'Failed to import file';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // Download Sample Template
  const handleDownloadTemplate = async (format) => {
    try {
      const res = await api.get(`/imports/template/sample?format=${format}`, {
        responseType: 'blob',
      });
      const blob = new Blob([res.data], {
        type: format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Standard_DMS_Template.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      toast.success(`Downloaded ${format.toUpperCase()} sample template`);
    } catch (err) {
      toast.error('Failed to download template');
    }
  };

  // Download Error Report
  const handleDownloadErrorReport = async (batchId) => {
    try {
      const res = await api.get(`/imports/batches/${batchId}/error-report`, {
        responseType: 'blob',
      });
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Import_Errors_${batchId.substring(0, 8)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      toast.error('Failed to download error report');
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <UploadCloud className="h-6 w-6 text-blue-600" />
            <span>DMS Data Import</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Upload workshop job cards to automatically create follow-up queues and assign customers equally to present CREs.
          </p>
        </div>

        {/* Download Template Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleDownloadTemplate('xlsx')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition shadow-sm"
          >
            <Download className="h-3.5 w-3.5 text-blue-600" />
            Sample Template (.xlsx)
          </button>
          <button
            type="button"
            onClick={() => handleDownloadTemplate('csv')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition shadow-sm"
          >
            <Download className="h-3.5 w-3.5 text-emerald-600" />
            Sample CSV
          </button>
        </div>
      </div>

      {/* Main Import Card */}
      {!importResult ? (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
          {/* Drag & Drop File Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
              isDragOver
                ? 'border-blue-500 bg-blue-50/60 dark:bg-blue-950/30'
                : selectedFile
                ? 'border-emerald-500 bg-emerald-50/30 dark:bg-emerald-950/20'
                : 'border-slate-300 dark:border-slate-700 hover:border-blue-400 bg-slate-50/50 dark:bg-slate-800/40'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => e.target.files?.[0] && handleFileSelected(e.target.files[0])}
              accept=".xlsx,.xls,.csv"
              className="hidden"
            />

            {selectedFile ? (
              <div className="flex flex-col items-center gap-2">
                <div className="p-3 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-300">
                  <CheckCircle2 className="h-8 w-8" />
                </div>
                <div className="font-bold text-sm text-slate-900 dark:text-white">
                  {selectedFile.name}
                </div>
                <div className="text-xs text-slate-500">
                  {(selectedFile.size / 1024).toFixed(1)} KB • Ready for import
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                  }}
                  className="mt-2 text-xs text-red-600 hover:underline font-semibold"
                >
                  Choose a different file
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300">
                  <UploadCloud className="h-8 w-8" />
                </div>
                <div className="font-semibold text-sm text-slate-800 dark:text-slate-200">
                  Drop your DMS file here, or <span className="text-blue-600 underline">browse</span>
                </div>
                <p className="text-xs text-slate-400">
                  Supports Excel (.xlsx, .xls) and CSV with standard columns
                </p>
              </div>
            )}
          </div>

          {/* Quick Fallback Options */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Default Brand (if not in file)
              </label>
              <select
                value={selectedBrandId}
                onChange={(e) => setSelectedBrandId(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
              >
                {brands.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name} ({b.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Default Branch (if not in file)
              </label>
              <select
                value={selectedBranchId}
                onChange={(e) => setSelectedBranchId(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
              >
                {branches.map((br) => (
                  <option key={br.id} value={br.id}>
                    {br.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Duplicate Job Cards
              </label>
              <select
                value={duplicateAction}
                onChange={(e) => setDuplicateAction(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
              >
                <option value="SKIP">Skip Already Imported (Recommended)</option>
                <option value="UPDATE">Update Existing Customer/Phone</option>
              </select>
            </div>
          </div>

          {/* Big Action Button */}
          <div className="flex justify-end pt-2">
            <button
              type="button"
              disabled={!selectedFile || loading || loadingMasters}
              onClick={handleImport}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Importing & Assigning to CREs...
                </>
              ) : (
                <>
                  <UserCheck className="h-4 w-4" />
                  Import & Assign Calls to CREs
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* Immediate Result Card Showing Assigned CREs */
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-300">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Import Complete & Calls Assigned!
                </h2>
                <p className="text-xs text-slate-500">
                  {importResult.file_name} • {importResult.total_rows} rows processed
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                setSelectedFile(null);
                setImportResult(null);
              }}
              className="text-xs font-semibold text-blue-600 hover:underline"
            >
              Import Another File
            </button>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-center">
              <div className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400">
                {importResult.success_rows}
              </div>
              <div className="text-xs font-semibold text-slate-600 dark:text-slate-300 mt-0.5">
                Job Cards Created
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-center">
              <div className="text-2xl font-extrabold text-blue-600 dark:text-blue-400">
                {importResult.queues_created}
              </div>
              <div className="text-xs font-semibold text-slate-600 dark:text-slate-300 mt-0.5">
                Calling Queues Created
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-center">
              <div className="text-2xl font-extrabold text-slate-600 dark:text-slate-400">
                {importResult.skipped_rows}
              </div>
              <div className="text-xs font-semibold text-slate-600 dark:text-slate-300 mt-0.5">
                Duplicates Skipped
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-center">
              <div
                className={`text-2xl font-extrabold ${
                  importResult.error_rows > 0 ? 'text-red-600' : 'text-slate-400'
                }`}
              >
                {importResult.error_rows}
              </div>
              <div className="text-xs font-semibold text-slate-600 dark:text-slate-300 mt-0.5">
                Row Errors Flagged
              </div>
            </div>
          </div>

          {/* FOR WHOM IT IS ASSIGNED: Highlighted Allocation Breakdown */}
          <div className="p-5 rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-800 dark:to-slate-800/80 border border-blue-200 dark:border-blue-900/50 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Users className="h-4 w-4 text-blue-600" />
                <span>Calls Assigned to Present CREs</span>
              </h3>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-600 text-white">
                Equal Split
              </span>
            </div>

            {(() => {
              const assigned = importResult.allocation_summary?.assigned_cres?.length
                ? importResult.allocation_summary.assigned_cres
                : importResult.allocation_summary?.per_cre
                ? Object.values(importResult.allocation_summary.per_cre)
                    .filter((d) => d.count > 0)
                    .map((d) => ({ user_name: d.name, count: d.count }))
                : [];
              return assigned.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {assigned.map((cre, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-blue-200 dark:border-slate-700 shadow-sm flex items-center justify-between"
                    >
                      <div>
                        <div className="font-bold text-xs text-slate-900 dark:text-white flex items-center gap-1.5">
                          <UserCheck className="h-3.5 w-3.5 text-emerald-600" />
                          <span>{cre.user_name}</span>
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">Assigned CRE</div>
                      </div>
                      <div className="text-right">
                        <span className="text-lg font-black text-blue-600 dark:text-blue-400">
                          {cre.count}
                        </span>
                        <span className="text-[10px] text-slate-400 block font-medium">calls assigned</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-600 dark:text-slate-300 py-1">
                  Calls were generated and queued for assignment in the PSF workspace.
                </div>
              );
            })()}
          </div>

          {/* Error Report if any errors */}
          {importResult.error_rows > 0 && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-red-800 dark:text-red-300 font-semibold">
                <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />
                <span>
                  {importResult.error_rows} row(s) had formatting errors and were skipped (valid rows imported successfully).
                </span>
              </div>
              <button
                type="button"
                onClick={() => handleDownloadErrorReport(importResult.batch_id)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold transition flex-shrink-0"
              >
                <Download className="h-3.5 w-3.5" />
                Download Error Report (.xlsx)
              </button>
            </div>
          )}

          {/* Navigation Action */}
          <div className="flex justify-between items-center pt-2">
            <button
              type="button"
              onClick={() => {
                setSelectedFile(null);
                setImportResult(null);
              }}
              className="text-xs font-semibold text-slate-600 dark:text-slate-400 hover:underline"
            >
              ← Import Another Batch
            </button>

            <button
              type="button"
              onClick={() => navigate('/psf')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md transition"
            >
              <span>View Calling Line Items</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Recent Import Batches Table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Clock className="h-4 w-4 text-slate-500" />
            <span>Recent DMS Import History</span>
          </h2>
          <button
            type="button"
            onClick={fetchRecentBatches}
            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
            title="Refresh history"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingBatches ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {recentBatches.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">
            No previous import batches found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 font-semibold uppercase tracking-wider border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">File Name</th>
                  <th className="py-2.5 px-3">Uploaded By</th>
                  <th className="py-2.5 px-3">Date & Time</th>
                  <th className="py-2.5 px-3 text-center">Total Rows</th>
                  <th className="py-2.5 px-3 text-center">Created</th>
                  <th className="py-2.5 px-3 text-center">Errors</th>
                  <th className="py-2.5 px-3 text-right">Error Report</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                {recentBatches.map((batch) => (
                  <tr key={batch.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">
                      {batch.file_name}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500">
                      {batch.uploader_name || 'System'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500">
                      {batch.created_at ? new Date(batch.created_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono">{batch.total_rows}</td>
                    <td className="py-2.5 px-3 text-center font-mono text-emerald-600 font-bold">
                      {batch.success_rows}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono">
                      {batch.error_rows > 0 ? (
                        <span className="text-red-600 font-bold">{batch.error_rows}</span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {batch.error_rows > 0 ? (
                        <button
                          type="button"
                          onClick={() => handleDownloadErrorReport(batch.id)}
                          className="text-xs font-semibold text-red-600 hover:underline"
                        >
                          Download .xlsx
                        </button>
                      ) : (
                        <span className="text-slate-400 text-[11px]">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
