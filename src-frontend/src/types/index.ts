/** Task processing status — mirrors Python TaskStatus enum */
export type TaskStatus =
  | 'pending'
  | 'extracting'
  | 'ocr_running'
  | 'saving'
  | 'completed'
  | 'failed'
  | 'cancelled'

/** OCR options sent to Python backend */
export interface OcrOptions {
  model_name: string
  use_gpu: boolean
  dpi: number
  max_pages?: number
  angle_cls: boolean
  show_confidence: boolean
}

/** Progress event emitted by Python during processing */
export interface TaskProgress {
  status: TaskStatus
  current_page: number
  total_pages: number
  message: string
  elapsed: number
}

/** Final result returned by Python after processing */
export interface TaskResult {
  success: boolean
  input_path: string | null
  output_pdf_path: string | null
  output_txt_path: string | null
  total_pages: number
  total_lines: number
  avg_confidence: number
  elapsed_seconds: number
  error: string | null
}

/** Model info from Python backend */
export interface ModelInfo {
  name: string
  desc: string
  lang: string
  model_type: string
  note: string
  cached: boolean
}

/** GPU info from Python backend */
export interface GpuInfo {
  available: boolean
  cuda_version: string | null
  cuda_root: string | null
  device_count: number
  error: string | null
}

/** Task tracked in the frontend store */
export interface Task {
  id: string
  fileName: string
  filePath: string
  status: TaskStatus
  options: OcrOptions
  progress: TaskProgress | null
  result: TaskResult | null
  error: string | null
  createdAt: number
}
