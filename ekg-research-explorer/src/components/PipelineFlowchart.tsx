import React, { useState } from 'react';
import { PIPELINE_STAGES, PipelineStage } from '../data/researchData';
import { GitBranch, ArrowDown, FileCode, AlertOctagon, CheckCircle2, ChevronRight } from 'lucide-react';

export const PipelineFlowchart: React.FC = () => {
  const [activePipeline, setActivePipeline] = useState<'All' | 'rule_v3' | 'kgx_v2' | 'kgx_v2_hybrid'>('All');
  const [selectedStageId, setSelectedStageId] = useState<string>('stage-5');

  const filteredStages = PIPELINE_STAGES.filter(
    s => s.pipeline === 'All' || activePipeline === 'All' || s.pipeline === activePipeline
  );

  const selectedStage = PIPELINE_STAGES.find(s => s.id === selectedStageId) || PIPELINE_STAGES[0];

  return (
    <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>Interactive Pipeline Flowchart & Stage Inspector</span>
            <span className="badge badge-primary">7 Stages</span>
          </h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '13.5px' }}>
            Select an architectural view and click any stage to inspect its underlying Python source code, inputs, outputs, and empirical failure modes.
          </p>
        </div>

        {/* Pipeline Tab Switcher */}
        <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-subtle)', padding: '4px', borderRadius: 'var(--radius-md)' }}>
          <button
            onClick={() => setActivePipeline('All')}
            className={`btn-icon ${activePipeline === 'All' ? 'active' : ''}`}
            style={{ width: 'auto', padding: '6px 12px', fontSize: '12px', fontWeight: 600, borderRadius: 'var(--radius-sm)', background: activePipeline === 'All' ? 'var(--primary)' : 'none', color: activePipeline === 'All' ? '#fff' : 'var(--text-secondary)' }}
          >
            Complete Architecture
          </button>
          <button
            onClick={() => setActivePipeline('rule_v3')}
            style={{ width: 'auto', padding: '6px 12px', fontSize: '12px', fontWeight: 600, borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer', background: activePipeline === 'rule_v3' ? 'var(--primary)' : 'none', color: activePipeline === 'rule_v3' ? '#fff' : 'var(--text-secondary)' }}
          >
            rule_v3 (Symbolic)
          </button>
          <button
            onClick={() => setActivePipeline('kgx_v2')}
            style={{ width: 'auto', padding: '6px 12px', fontSize: '12px', fontWeight: 600, borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer', background: activePipeline === 'kgx_v2' ? 'var(--primary)' : 'none', color: activePipeline === 'kgx_v2' ? '#fff' : 'var(--text-secondary)' }}
          >
            kgx_v2 (Local LLM)
          </button>
          <button
            onClick={() => setActivePipeline('kgx_v2_hybrid')}
            style={{ width: 'auto', padding: '6px 12px', fontSize: '12px', fontWeight: 600, borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer', background: activePipeline === 'kgx_v2_hybrid' ? 'var(--primary)' : 'none', color: activePipeline === 'kgx_v2_hybrid' ? '#fff' : 'var(--text-secondary)' }}
          >
            kgx_v2_hybrid (Neuro-Symbolic)
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 360px) 1fr', gap: '24px' }}>
        {/* Interactive Linear Flow List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filteredStages.map((stage, idx) => {
            const isSelected = stage.id === selectedStageId;
            return (
              <React.Fragment key={stage.id}>
                <div
                  onClick={() => setSelectedStageId(stage.id)}
                  style={{
                    padding: '14px 16px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid',
                    borderColor: isSelected ? 'var(--primary)' : 'var(--border-color)',
                    backgroundColor: isSelected ? 'var(--primary-light)' : 'var(--bg-surface)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    boxShadow: isSelected ? 'var(--shadow-sm)' : 'none',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ width: '22px', height: '22px', borderRadius: '50%', backgroundColor: isSelected ? '#2563eb' : 'var(--bg-subtle)', color: isSelected ? '#fff' : 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: 700 }}>
                      {idx + 1}
                    </div>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: isSelected ? 'var(--primary)' : 'var(--text-primary)' }}>
                      {stage.name.split('. ')[1]}
                    </span>
                  </div>
                  <ChevronRight size={15} style={{ color: isSelected ? 'var(--primary)' : 'var(--text-dim)' }} />
                </div>

                {idx < filteredStages.length - 1 && (
                  <div style={{ display: 'flex', justifyContent: 'center', margin: '-4px 0' }}>
                    <ArrowDown size={14} style={{ color: 'var(--text-dim)' }} />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Selected Stage Detail Inspector */}
        <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-primary">{selectedStage.pipeline === 'All' ? 'Common Stage' : selectedStage.pipeline}</span>
            </div>
            <h4 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)', margin: '4px 0' }}>
              {selectedStage.name}
            </h4>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              {selectedStage.purpose}
            </p>
          </div>

          <div>
            <h5 style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Processing Logic & Architecture
            </h5>
            <div style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6, backgroundColor: 'var(--bg-subtle)', padding: '12px 14px', borderRadius: 'var(--radius-md)' }}>
              {selectedStage.logic}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <h5 style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Inputs
              </h5>
              <ul style={{ paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                {selectedStage.inputs.map((inItem, i) => (
                  <li key={i}>{inItem}</li>
                ))}
              </ul>
            </div>
            <div>
              <h5 style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Outputs
              </h5>
              <ul style={{ paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                {selectedStage.outputs.map((outItem, i) => (
                  <li key={i}>{outItem}</li>
                ))}
              </ul>
            </div>
          </div>

          <div>
            <h5 style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <FileCode size={13} /> Source Implementation Files
            </h5>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {selectedStage.sourceFiles.map((file, i) => (
                <code key={i} style={{ fontSize: '12px', padding: '3px 8px', borderRadius: '4px', backgroundColor: 'var(--bg-subtle)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>
                  {file}
                </code>
              ))}
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '14px' }}>
            <h5 style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--danger)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertOctagon size={13} /> Empirical Failure Modes
            </h5>
            <ul style={{ paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
              {selectedStage.failureModes.map((fm, i) => (
                <li key={i}>{fm}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
