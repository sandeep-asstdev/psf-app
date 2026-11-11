/**
 * ============================================================================
 * FILE PURPOSE: Redirect/Adapter to UserActivityPage.
 * Attendance feature has been replaced with App Usage & Audit Logs.
 * ============================================================================
 */
import React from 'react';
import UserActivityPage from './UserActivityPage';

export default function AttendanceLogsPage() {
  return <UserActivityPage />;
}
