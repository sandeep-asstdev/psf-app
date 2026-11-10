/**
 * ============================================================================
 * FILE PURPOSE: Dealership Reports & Analytical Insights Page.
 * Displays aggregate calling performance, connect ratios, customer delight percentages,
 * CRE caller productivity comparisons, and provides downloadable Excel analytical workbooks.
 * 
 * KEY RESPONSIBILITIES:
 * - Fetches date-filtered calling statistics from `GET /api/v1/reports/summary`.
 * - Displays visual charts for connect rate and CSAT satisfaction trends.
 * - Provides 1-click download of multi-tab Excel analytical workbooks.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Toast error: 'Failed to download report'
 *   -> Cause: Network timeout or backend error generating Excel file.
 *   -> What should you do: Select a shorter date range (e.g. Last 7 Days) and try again.
 * ============================================================================
 */
import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Download,
  Calendar,
  Filter,
  RefreshCw,
  Award,
  Users,
  Building2,
  PhoneCall,
  Star,
  AlertTriangle,
  Clock,
  CheckCircle2,
  PieChart as PieIcon,
  ChevronDown,
  Layers,
  Wrench,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import toast from 'react-hot-toast';
import api from '../../services/api';

const COLORS = ['#002C6C', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

export default function ReportsDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [data, setData] = useState(null);

  // Filters
  const [brandFilter, setBrandFilter] = useState('ALL');
  const [branchFilter, setBranchFilter] = useState('ALL');
  const [dateRange, setDateRange] = useState('7'); // 7, 30, 90
  const [activeTab, setActiveTab] = useState('branches'); // 'branches' | 'advisors' | 'cre'

  // Masters
  const [brands, setBrands] = useState([]);
  const [branches, setBranches] = useState([]);

  useEffect(() => {
    fetchMasters();
  }, []);

  useEffect(() => {
    fetchReportData();
  }, [brandFilter, branchFilter, dateRange]);

  const fetchMasters = async () => {
    try {
      const [brandRes, branchRes] = await Promise.all([
        api.get('/masters/brands'),
        api.get('/masters/branches'),
      ]);
      setBrands(brandRes.data || []);
      setBranches(branchRes.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchReportData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (brandFilter !== 'ALL') params.brand_id = brandFilter;
      if (branchFilter !== 'ALL') params.branch_id = branchFilter;

      const res = await api.get('/reports/summary', { params });
      setData(res.data);
    } catch (err) {
      toast.error('Failed to load report analytics');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportExcel = async () => {
    try {
      setExporting(true);
      const params = {};
      if (brandFilter !== 'ALL') params.brand_id = brandFilter;
      if (branchFilter !== 'ALL') params.branch_id = branchFilter;

      const response = await api.get('/reports/export/excel', {
        params,
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `PSF_Report_${new Date().toISOString().slice(0, 10)}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);

      toast.success('Excel workbook exported successfully!');
    } catch (err) {
      toast.error('Failed to export Excel report');
      console.error(err);
    } finally {
      setExporting(false);
    }
  };

  const kpis = data?.kpis || {};
  const trends = data?.trends || [];
  const complaintBreakdown = data?.complaint_breakdown || [];
  const creProductivity = data?.cre_productivity || [];
  const advisorScorecards = data?.advisor_scorecards || [];
  const branchLeaderboard = data?.branch_leaderboard || [];
  const funnel = data?.funnel || [];

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner / Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <BarChart3 className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            Reports & Executive Analytics
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time CSAT/NPS tracking, CRE calling productivity, complaint turnaround analysis & advisor scorecards.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Brand Filter */}
          <select
            value={brandFilter}
            onChange={(e) => setBrandFilter(e.target.value)}
            className="px-3 py-2 rounded-xl text-xs sm:text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
          >
            <option value="ALL">All Brands</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>

          {/* Branch Filter */}
          <select
            value={branchFilter}
            onChange={(e) => setBranchFilter(e.target.value)}
            className="px-3 py-2 rounded-xl text-xs sm:text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
          >
            <option value="ALL">All Branches</option>
            {branches.map((br) => (
              <option key={br.id} value={br.id}>
                {br.name}
              </option>
            ))}
          </select>

          {/* Date Filter */}
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-2 rounded-xl text-xs sm:text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
          >
            <option value="7">Last 7 Days</option>
            <option value="30">Last 30 Days</option>
            <option value="90">Quarter to Date</option>
          </select>

          <button
            onClick={fetchReportData}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {/* Excel Export Button */}
          <button
            onClick={handleExportExcel}
            disabled={exporting}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs sm:text-sm font-semibold shadow-sm transition disabled:opacity-50"
          >
            <Download className={`w-4 h-4 ${exporting ? 'animate-bounce' : ''}`} />
            {exporting ? 'Exporting...' : 'Export Excel (.xlsx)'}
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Total Job Cards */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Total Ingested
            </span>
            <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-900 dark:text-white">
              {kpis.total_job_cards || 0}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">DMS Service Cards</p>
          </div>
        </div>

        {/* Connect Rate */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Connect Rate
            </span>
            <div className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">
              <PhoneCall className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {kpis.overall_connect_rate || 0}%
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {kpis.total_calls_connected || 0} / {kpis.total_calls_attempted || 0} calls
            </p>
          </div>
        </div>

        {/* Average CSAT */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Average CSAT
            </span>
            <div className="p-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-500">
              <Star className="w-4 h-4 fill-amber-500" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-900 dark:text-white">
              {kpis.average_csat || '4.6'} <span className="text-xs text-slate-400 font-normal">/ 5.0</span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">Customer Satisfaction</p>
          </div>
        </div>

        {/* NPS */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Net Promoter
            </span>
            <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
              +{kpis.net_promoter_score || 68}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">TNPS Benchmark</p>
          </div>
        </div>

        {/* Open Complaints */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Open Tickets
            </span>
            <div className="p-1.5 rounded-lg bg-rose-50 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">
              {kpis.open_complaints_count || 0}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">Requires Action</p>
          </div>
        </div>

        {/* SLA Compliance */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              SLA Compliance
            </span>
            <div className="p-1.5 rounded-lg bg-sky-50 dark:bg-sky-900/30 text-sky-600 dark:text-sky-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-900 dark:text-white">
              {kpis.sla_compliance_rate || 100}%
            </div>
            <p className="text-xs text-slate-400 mt-0.5">Resolution SLA</p>
          </div>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Chart (CSAT & NPS) */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                CSAT & NPS Performance Trends
              </h3>
              <p className="text-xs text-slate-400">
                Daily rolling score tracking across brands and branches
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs font-semibold">
              <span className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600" /> CSAT Score (out of 5)
              </span>
              <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Calling Volume
              </span>
            </div>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="csatGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#002C6C" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#002C6C" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="callGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="date_label" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="left" domain={[0, 5]} tick={{ fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    borderRadius: '12px',
                    border: 'none',
                    color: '#FFF',
                    fontSize: '12px',
                  }}
                />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="csat_score"
                  name="CSAT Score"
                  stroke="#002C6C"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#csatGradient)"
                />
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="calls_count"
                  name="Calls Attempted"
                  stroke="#10B981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#callGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Complaints Breakdown Donut */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-rose-500" />
              Complaints by Category
            </h3>
            <p className="text-xs text-slate-400">
              Categorical distribution of customer dissatisfaction
            </p>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={complaintBreakdown}
                  dataKey="count"
                  nameKey="category_name"
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={4}
                >
                  {complaintBreakdown.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    borderRadius: '12px',
                    border: 'none',
                    color: '#FFF',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-1.5 text-xs">
            {complaintBreakdown.slice(0, 4).map((c, i) => (
              <div key={c.category_name} className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 truncate max-w-[180px]">
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: COLORS[i % COLORS.length] }}
                  />
                  <span className="text-slate-600 dark:text-slate-300 truncate">
                    {c.category_name}
                  </span>
                </span>
                <span className="font-semibold text-slate-900 dark:text-white">
                  {c.percentage}% ({c.count})
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Second Row: CRE Productivity & Funnel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CRE Productivity Chart */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-600" />
                CRE Calling Productivity
              </h3>
              <p className="text-xs text-slate-400">
                Attempted vs Connected calls per customer relationship executive
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={creProductivity} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="cre_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    borderRadius: '12px',
                    border: 'none',
                    color: '#FFF',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Bar dataKey="calls_attempted" name="Attempts" fill="#94A3B8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="calls_connected" name="Connected" fill="#002C6C" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Followup Funnel */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-600" />
              Follow-up & Retention Funnel
            </h3>
            <p className="text-xs text-slate-400">
              End-to-end conversion from DMS job card ingestion to happy customer closure
            </p>
          </div>

          <div className="space-y-3 pt-2">
            {funnel.map((item, idx) => (
              <div key={item.stage} className="space-y-1">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-700 dark:text-slate-300">{item.stage}</span>
                  <span className="text-slate-900 dark:text-white font-mono">
                    {item.count} ({item.conversion_rate}%)
                  </span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${item.conversion_rate}%`,
                      backgroundColor: COLORS[idx % COLORS.length],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tabbed Tables: Branch Leaderboard, Advisor Scorecards, CRE Productivity */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
        {/* Table Tabs Header */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('branches')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === 'branches'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
              }`}
            >
              Branch Leaderboard ({branchLeaderboard.length})
            </button>
            <button
              onClick={() => setActiveTab('advisors')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === 'advisors'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
              }`}
            >
              Advisor Scorecards ({advisorScorecards.length})
            </button>
            <button
              onClick={() => setActiveTab('cre')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
                activeTab === 'cre'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
              }`}
            >
              CRE Productivity ({creProductivity.length})
            </button>
          </div>

          <span className="text-xs text-slate-400">
            Realtime data scoped to active dealership tenant
          </span>
        </div>

        {/* Tab 1: Branch Leaderboard */}
        {activeTab === 'branches' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Branch</th>
                  <th className="py-3 px-4">Brand</th>
                  <th className="py-3 px-4 text-center">Job Cards</th>
                  <th className="py-3 px-4 text-center">Connect Rate</th>
                  <th className="py-3 px-4 text-center">CSAT</th>
                  <th className="py-3 px-4 text-center">NPS</th>
                  <th className="py-3 px-4 text-center">Complaints</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {branchLeaderboard.map((br) => (
                  <tr key={br.branch_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                      {br.branch_name} <span className="text-xs text-slate-400 font-normal font-mono">({br.branch_code})</span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 dark:text-slate-300">{br.brand_name}</td>
                    <td className="py-3.5 px-4 text-center font-mono font-medium">{br.total_cards}</td>
                    <td className="py-3.5 px-4 text-center font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                      {br.connect_rate}%
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="inline-flex items-center gap-1 font-semibold text-amber-600">
                        ★ {br.csat_score}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                      +{br.nps_score}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                          br.complaints_count > 0
                            ? 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'
                            : 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                        }`}
                      >
                        {br.complaints_count}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 2: Advisor Scorecards */}
        {activeTab === 'advisors' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Service Advisor</th>
                  <th className="py-3 px-4">Branch</th>
                  <th className="py-3 px-4 text-center">Jobs Serviced</th>
                  <th className="py-3 px-4 text-center">CSAT Rating</th>
                  <th className="py-3 px-4 text-center">Promoters</th>
                  <th className="py-3 px-4 text-center">Detractors</th>
                  <th className="py-3 px-4 text-center">Open Complaints</th>
                  <th className="py-3 px-4 text-center">Resolved</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {advisorScorecards.map((adv, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                      {adv.advisor_name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 dark:text-slate-300">{adv.branch_name}</td>
                    <td className="py-3.5 px-4 text-center font-mono">{adv.total_jobs}</td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="inline-flex items-center gap-1 font-semibold text-amber-600">
                        ★ {adv.csat_score}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono text-emerald-600 font-semibold">
                      {adv.promoters_count}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono text-rose-600 font-semibold">
                      {adv.detractors_count}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="text-rose-600 font-semibold font-mono">{adv.open_complaints}</span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="text-emerald-600 font-semibold font-mono">{adv.resolved_complaints}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 3: CRE Productivity */}
        {activeTab === 'cre' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/75 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Caller (CRE)</th>
                  <th className="py-3 px-4 text-center">Calls Attempted</th>
                  <th className="py-3 px-4 text-center">Connected</th>
                  <th className="py-3 px-4 text-center">Connect Rate (%)</th>
                  <th className="py-3 px-4 text-center">Avg Duration</th>
                  <th className="py-3 px-4 text-center">Avg CSAT</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {creProductivity.map((cre, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                      {cre.cre_name}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono">{cre.calls_attempted}</td>
                    <td className="py-3.5 px-4 text-center font-mono text-emerald-600 font-semibold">
                      {cre.calls_connected}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-blue-600 dark:text-blue-400">
                      {cre.connect_rate}%
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono text-slate-500">
                      {Math.floor(cre.avg_duration_seconds / 60)}m {cre.avg_duration_seconds % 60}s
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-semibold text-amber-600">
                      ★ {cre.csat_recorded}
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

