import React, { useState } from 'react';
import { apiService } from '../api';

interface PosterEditPanelProps {
  // Removed props that depended on generation
  initialJobId?: string;
}

const PosterEditPanel: React.FC<PosterEditPanelProps> = ({ initialJobId }) => {
  const [jobId, setJobId] = useState<string | undefined>(initialJobId);

  // 仅支持 PPTX 上传替换海报
  const [customPosterFile, setCustomPosterFile] = useState<File | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [localPreviewUrl, setLocalPreviewUrl] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [usedFallback, setUsedFallback] = useState(false);
  const [fallbackType, setFallbackType] = useState<string | null>(null);

  // 编辑功能状态
  const [editInstruction, setEditInstruction] = useState<string>('');
  const [editJobId, setEditJobId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState<'idle' | 'submitting' | 'processing' | 'completed' | 'failed'>('idle');
  const [editLogs, setEditLogs] = useState<string[]>([]);
  const [editError, setEditError] = useState<string | null>(null);
  const [editedPreviewUrl, setEditedPreviewUrl] = useState<string | null>(null);

  const pptxUrl = jobId ? apiService.getPptxUrl(jobId) : undefined;

  // 优先显示编辑后的预览图，然后是本地上传的
  const posterImg = editedPreviewUrl || localPreviewUrl;

  const customDownloadUrl = previewId ? apiService.getPreviewPptxDownloadUrl(previewId) : null;
  const canDownloadCustom = !!customPosterFile && !!posterImg && !!customDownloadUrl;
  const editedDownloadUrl = editJobId && editStatus === 'completed' ? apiService.getEditedPptxDownloadUrl(editJobId) : null;
  const canDownloadEdited = !!editedDownloadUrl;

  const canDownload = canDownloadEdited || canDownloadCustom;

  const logsEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [editLogs]);

  // 轮询编辑任务状态
  React.useEffect(() => {
    if (!editJobId || editStatus === 'completed' || editStatus === 'failed') {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const [status, logs] = await Promise.all([
          apiService.getEditStatus(editJobId),
          apiService.getEditLogs(editJobId)
        ]);

        setEditLogs(logs);

        if (status.status === 'failed') {
          setEditStatus('failed');
          setEditError(status.error || '编辑失败');
        } else if (status.status === 'completed') {
          setEditStatus('completed');
          // 加载编辑后的预览图
          if (status.output_png) {
            setEditedPreviewUrl(`${apiService.getEditedPreviewUrl(editJobId)}?t=${new Date().getTime()}`);
          }
        } else if (status.status === 'processing') {
          setEditStatus('processing');
        }
      } catch (err) {
        console.error('Failed to check edit status:', err);
        setEditStatus('failed');
        setEditError('无法获取编辑状态');
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [editJobId, editStatus]);

  const requestPreviewFromServer = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    setUsedFallback(false);
    setFallbackType(null);
    try {
      const { url, fallback, fallback_type, preview_id } = await (async () => {
        const r = await apiService.uploadPptxPreview(file);
        return { url: r.url, fallback: r.fallback, fallback_type: r.fallback_type, preview_id: r.preview_id };
      })();
      setLocalPreviewUrl(url);
      setPreviewId(preview_id);
      setUsedFallback(fallback);
      setFallbackType(fallback_type);
    } catch (e: any) {
      console.error('Upload PPTX preview failed', e);
      setLocalPreviewUrl(null);
      setPreviewId(null);
      setUploadError(e?.response?.data?.detail || '预览生成失败');
      setFallbackType(null);
    } finally {
      setUploading(false);
    }
  };

  const handleCustomPosterChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pptx')) { setUploadError('仅支持 .pptx 文件'); return; }
    setCustomPosterFile(file);
    await requestPreviewFromServer(file);
  };
  const triggerFileDialog = () => {
    const input = document.getElementById('customPosterInput');
    input?.click();
  };

  const handleEditSubmit = async () => {
    if (!editInstruction.trim()) {
      setEditError('请输入编辑指令');
      return;
    }

    // Determine the source for the edit (Chaining preference: New Edit > Uploaded PPTX > URL JobID)
    // 1. If we have a completed edit, use that result as the base for the next edit
    const chainedJobId = (editStatus === 'completed' && editJobId) ? editJobId : jobId;

    // 2. Or use the uploaded preview ID
    const sourcePreviewId = (!chainedJobId && previewId) ? previewId : undefined;

    // 3. Or use the uploaded file object (fallback, worst case as it re-uploads)
    // Only use file if we don't have a previewId and don't have a chained job
    const sourceFile = (!chainedJobId && !sourcePreviewId && customPosterFile) ? customPosterFile : undefined;

    if (!sourceFile && !sourcePreviewId && !chainedJobId) {
      setEditError('请先上传 PPTX 文件');
      return;
    }

    setEditStatus('submitting');
    setEditError(null);
    setEditLogs([]);

    try {
      const result = await apiService.submitEditJob(
        sourceFile || undefined,
        sourcePreviewId,
        chainedJobId || undefined,
        editInstruction,
        pdfFile || undefined
      );

      setEditJobId(result.job_id);
      setEditStatus('processing');
      setEditInstruction('');
    } catch (err: any) {
      console.error('Failed to submit edit job:', err);
      setEditStatus('failed');
      setEditError(err?.response?.data?.detail || err.message || '提交编辑任务失败');
    }
  };

  return (
    <div className="edit-panel-wrapper" style={{ flex: 1, minHeight: 0, width: '100%', display: 'flex' }}>
      <div className="edit-panel" style={{ display: 'flex', gap: 24, alignItems: 'stretch', width: '100%', height: '100%' }}>
        {/* 左侧：Poster 预览卡片（2/3） */}
        <div className="card main-card" style={{ flex: '2 1 0' }}>
          <h3 className="section-title">🖼️ Poster Preview</h3>
          <div className="preview-container elevated" style={{ marginTop: 8, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', flexDirection: 'column', gap: 16, padding: 16, width: '100%', overflowY: 'auto' }}>
            {posterImg ? (
              <>
                <img src={posterImg} alt="Poster" style={{ maxWidth: '75%', height: 'auto', borderRadius: 6, boxShadow: 'var(--shadow-sm)' }} />
                <div style={{ width: '100%', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <label htmlFor="customPosterInput" style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text-secondary)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" /></svg>
                    {customPosterFile ? '已选择 PPTX：' + customPosterFile.name : '上传新的 PPTX 以替换(可选)'}
                  </label>
                  {usedFallback && fallbackType && (
                    <div style={{ fontSize: 12, color: '#5a6078' }}>
                      预览来源: {fallbackType === 'synthetic' ? '文本合成' : fallbackType === 'libreoffice' ? 'LibreOffice 渲染' : fallbackType === 'placeholder' ? '占位图' : '内置缩略图'}
                    </div>
                  )}
                  {uploading && (
                    <div style={{ fontSize: 12, color: '#4d89ff' }}>正在生成预览...</div>
                  )}
                  {uploadError && (
                    <div style={{ fontSize: 12, color: '#c53d3d' }}>{uploadError === 'Not Found' ? '无法生成预览: PPTX 无内容或缺少依赖' : uploadError}</div>
                  )}
                  <input id="customPosterInput" type="file" accept=".pptx" onChange={handleCustomPosterChange} style={{ display: 'none' }} />
                </div>
              </>
            ) : (
              <div onClick={triggerFileDialog} style={{ width: '100%', textAlign: 'center', cursor: 'pointer' }}>
                <div className="empty-state" style={{ margin: 0, padding: 32, borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
                  <div style={{ fontSize: 14, color: 'var(--color-text-secondary)' }}>
                    Upload a PPTX file to start editing
                  </div>
                  <button type="button" className="button" style={{ padding: '8px 16px', fontSize: 13 }}>Select PPTX File</button>
                  {uploading && <div style={{ fontSize: 12, color: '#4d89ff' }}>上传处理中...</div>}
                  {uploadError && <div style={{ fontSize: 12, color: '#c53d3d' }}>{uploadError}</div>}
                </div>
                <input id="customPosterInput" type="file" accept=".pptx" onChange={handleCustomPosterChange} style={{ display: 'none' }} />
              </div>
            )}
          </div>

          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
            <a
              href={canDownloadEdited ? editedDownloadUrl! : (canDownloadCustom ? customDownloadUrl! : undefined)}
              download={canDownload ? (canDownloadEdited ? `edited_poster_${editJobId?.substring(0, 8)}.pptx` : (canDownloadCustom ? `uploaded_poster_${previewId}.pptx` : 'generated_poster.pptx')) : undefined}
              className="button"
              style={{
                background: canDownload ? 'linear-gradient(135deg,#6aa8ff 0%, #4d89ff 50%, #3d6dce 100%)' : '#d1d9e2',
                boxShadow: canDownload ? '0 2px 6px rgba(77,137,255,0.25)' : 'none',
                cursor: canDownload ? 'pointer' : 'not-allowed',
                opacity: canDownload ? 1 : 0.6,
                width: 'auto',
                padding: '10px 20px',
                fontSize: 14,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                borderRadius: 8,
                whiteSpace: 'nowrap',
                textDecoration: 'none',
                pointerEvents: canDownload ? 'auto' : 'none'
              }}
              aria-disabled={!canDownload}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: canDownload ? 1 : 0.7 }}>
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <path d="M7 10l5 5 5-5" />
                <path d="M12 15V3" />
              </svg>
              {canDownload ? (canDownloadEdited ? 'Download edited PPTX' : 'Download uploaded PPTX') : 'Poster not ready'}
            </a>

            {/* PDF Paper 上传按钮 */}
            <label
              className="button"
              style={{
                background: pdfFile ? 'linear-gradient(135deg,#6aa8ff 0%, #4d89ff 50%, #3d6dce 100%)' : '#d1d9e2',
                boxShadow: pdfFile ? '0 2px 6px rgba(77,137,255,0.25)' : 'none',
                cursor: 'pointer',
                opacity: 1,
                width: 'auto',
                padding: '10px 20px',
                fontSize: 14,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                borderRadius: 8,
                whiteSpace: 'nowrap'
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <path d="M17 8l-5-5-5 5" />
                <path d="M12 3v12" />
              </svg>
              {pdfFile ? `${pdfFile.name}` : 'PDF Paper'}
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setPdfFile(e.target.files[0]);
                  }
                }}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        </div>

        {/* 右侧：AI 编辑侧栏（1/3） */}
        <div className="card main-card" style={{ flex: '1 1 0' }}>
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            <span aria-hidden>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
            </span>
            <span>Poster Edit</span>
          </h3>

          {/* 顶部：滚动区域（自适应高度，最小 200px） */}
          <div style={{ flex: '1 1 auto', overflowY: 'auto', marginTop: 12, border: '1px solid var(--border-color)', background: '#F8FAFC', borderRadius: 12, padding: 16, minHeight: '200px', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)' }}>
            {editLogs.length > 0 ? (
              <>
                {editLogs.map((log, idx) => (
                  <div key={idx} className="log-line">{log}</div>
                ))}
                <div ref={logsEndRef} />
              </>
            ) : (
              <div className="log-line" style={{ color: '#94A3B8', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16 }}>📝</span> AI Agent logs will appear here...
              </div>
            )}
          </div>

          {/* 中部：状态说明（固定高度） */}
          <div style={{ flexShrink: 0, marginTop: 12, color: editStatus === 'processing' ? '#2563EB' : editError ? '#DC2626' : '#64748B', height: '24px', fontSize: '13px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6 }}>
            {editStatus === 'idle' && 'Waiting for instructions...'}
            {editStatus === 'submitting' && '🚀 Sending request...'}
            {editStatus === 'processing' && '⚡ AI Agent is working...'}
            {editStatus === 'completed' && '✨ Editing completed successfully!'}
            {editStatus === 'failed' && `🛑 ${editError || 'Edit failed'}`}
          </div>

          {/* 底部：输入与按钮（固定高度区域） */}
          <div style={{ flexShrink: 0, marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12, borderTop: '1px solid var(--border-color)', paddingTop: 16, height: '180px' }}>
            <textarea
              value={editInstruction}
              onChange={(e) => setEditInstruction(e.target.value)}
              placeholder="Describe your changes... (e.g., 'Make the title bigger', 'Change the layout to 3 columns')"
              style={{ width: '100%', flex: 1, resize: 'none', padding: 12, fontSize: 14, lineHeight: 1.6 }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleEditSubmit();
                }
              }}
            />
            <button
              onClick={handleEditSubmit}
              disabled={editStatus === 'processing' || editStatus === 'submitting'}
              className="button"
              style={{ height: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, flexShrink: 0, fontSize: 15, fontWeight: 600, letterSpacing: '0.01em' }}
            >
              {editStatus === 'processing' || editStatus === 'submitting' ? (
                <>
                  <div className="spinner" style={{ width: 16, height: 16, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                  Processing...
                </>
              ) : (
                <>
                  <span>Submit Edit</span>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default PosterEditPanel;
