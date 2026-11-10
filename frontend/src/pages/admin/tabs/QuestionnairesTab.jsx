import React, { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../../services/api';

export default function QuestionnairesTab() {
  const [questionnaires, setQuestionnaires] = useState([]);
  const [activeQuestionnaire, setActiveQuestionnaire] = useState(null);
  const [newQuestionModal, setNewQuestionModal] = useState(false);
  const [questionForm, setQuestionForm] = useState({
    key: '',
    label: '',
    type: 'RATING_10',
    section: 'Service Quality',
    is_required: true,
    weight: 10,
    show_if: null,
  });

  const loadQuestionnaires = async () => {
    try {
      const res = await api.get('/questionnaires');
      setQuestionnaires(res.data);
      if (res.data.length > 0) {
        const first = await api.get(`/questionnaires/${res.data[0].id}`);
        setActiveQuestionnaire(first.data);
      }
    } catch (err) {
      // ignore
    }
  };

  useEffect(() => {
    loadQuestionnaires();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-foreground">Dynamic Questionnaire Builder & Version Control</h2>
          <p className="text-[11px] text-foreground-subtle">Draft questions, bump versions, and publish templates per brand</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-1 space-y-2">
          <span className="text-xs font-bold text-foreground">Available Templates</span>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {questionnaires.map((q) => (
              <div
                key={q.id}
                onClick={async () => {
                  const det = await api.get(`/questionnaires/${q.id}`);
                  setActiveQuestionnaire(det.data);
                }}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  activeQuestionnaire?.id === q.id
                    ? 'border-accent bg-accent-subtle shadow-sm'
                    : 'border-border bg-background-surface hover:bg-background-hover'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground">{q.title}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-background-base">v{q.version}</span>
                </div>
                <div className="text-[10px] text-foreground-subtle mt-1">
                  Brand: {q.brand_name || 'All'} · Type: {q.type} · {q.questions_count || 0} questions
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="md:col-span-2 space-y-3 p-4 rounded-lg border border-border bg-background-surface">
          {activeQuestionnaire ? (
            <>
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h3 className="text-sm font-bold text-foreground">{activeQuestionnaire.title} (v{activeQuestionnaire.version})</h3>
                  <p className="text-[11px] text-foreground-subtle">
                    Brand: {activeQuestionnaire.brand_name || 'Generic'} · Campaign: {activeQuestionnaire.type}
                  </p>
                </div>
                <button
                  onClick={() => setNewQuestionModal(true)}
                  className="inline-flex items-center space-x-1 rounded bg-accent px-2.5 py-1 text-xs font-semibold text-accent-foreground hover:bg-accent/90"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Question</span>
                </button>
              </div>

              <div className="space-y-2 max-h-96 overflow-y-auto">
                {(activeQuestionnaire.questions || []).map((qItem, idx) => (
                  <div key={qItem.id || idx} className="p-3 rounded-lg border border-border bg-background-base flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-foreground">
                        {idx + 1}. {qItem.label}
                      </div>
                      <div className="text-[10px] font-mono text-foreground-subtle mt-0.5">
                        Key: <span className="text-accent">{qItem.key}</span> · Type: {qItem.type} · Section: {qItem.section} · Weight: {qItem.weight}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="py-8 text-center text-xs text-foreground-subtle">Select a questionnaire template to view details</div>
          )}
        </div>
      </div>
    </div>
  );
}
