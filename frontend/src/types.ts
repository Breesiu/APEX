export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  error?: string;
}

export interface PosterConfig {
  text_model: string;
  vision_model: string;
  poster_width: number | string;
  poster_height: number | string;
}

export interface UploadedFiles {
  pdf_file: File | null;
  // logo_file and aff_logo_file removed as they are for generation
}
