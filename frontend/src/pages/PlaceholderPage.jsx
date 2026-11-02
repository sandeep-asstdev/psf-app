import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function PlaceholderPage({ title, description, phase }) {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="rounded-2xl border border-border bg-background-card p-8 shadow-card max-w-lg">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-accent-subtle text-accent font-bold">
          {phase || 'P'}
        </div>
        <h2 className="mt-4 text-xl font-bold text-foreground">{title}</h2>
        <p className="mt-2 text-sm text-foreground-muted leading-relaxed">
          {description}
        </p>
        <div className="mt-6">
          <button
            onClick={() => navigate('/')}
            className="inline-flex items-center space-x-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Return to Home Dashboard</span>
          </button>
        </div>
      </div>
    </div>
  );
}
