import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
});

export const apiService = {
  // === Poster Edit API ===
  
  getPptxUrl(jobId: string): string {
    return `${API_BASE}/pptx/${jobId}`;
  },

  async uploadPptxPreview(file: File): Promise<{ preview_id: string; url: string; fallback: boolean; fallback_type: string; pptx_download_url: string }>{ 
    const form = new FormData();
    form.append('file', file);
    const res = await api.post('/edit/upload_pptx_preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return { preview_id: res.data.preview_id, url: `${API_BASE}${res.data.url}`, fallback: !!res.data.fallback, fallback_type: res.data.fallback_type, pptx_download_url: `${API_BASE}${res.data.pptx_download_url}` };
  },
  
  getPreviewPptxDownloadUrl(previewId: string){
    return `${API_BASE}/edit/download_pptx/${previewId}`;
  },

  async submitEditJob(
    pptxFile?: File,
    previewId?: string,
    jobId?: string,
    instruction?: string,
    pdfFile?: File
  ): Promise<{ job_id: string; status: string; progress: number; message: string }> {
    if (!instruction || !instruction.trim()) {
      throw new Error('编辑指令不能为空');
    }

    const formData = new FormData();
    formData.append('instruction', instruction);

    if (pptxFile) {
      formData.append('pptx_file', pptxFile);
    } else if (previewId) {
      formData.append('preview_id', previewId);
    } else if (jobId) {
      formData.append('job_id', jobId);
    } else {
      throw new Error('必须提供 pptx 文件、preview_id 或 job_id');
    }

    if (pdfFile) {
      formData.append('pdf_file', pdfFile);
    }

    const res = await api.post('/edit/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return res.data;
  },

  async getEditStatus(jobId: string): Promise<{
    job_id: string;
    status: string;
    progress: number;
    message: string;
    error?: string;
    output_pptx?: string;
    output_png?: string;
  }> {
    const res = await api.get(`/edit/status/${jobId}`);
    return res.data;
  },

  async getEditLogs(jobId: string): Promise<string[]> {
    const res = await api.get(`/edit/logs/${jobId}`);
    return res.data.logs;
  },

  getEditedPreviewUrl(jobId: string): string {
    return `${API_BASE}/edit/preview/${jobId}`;
  },

  getEditedPptxDownloadUrl(jobId: string): string {
    return `${API_BASE}/edit/download_edited_pptx/${jobId}`;
  },
};
