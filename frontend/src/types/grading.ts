export interface Annotation {
  x: number;
  y: number;
  w: number;
  h: number;
  type?: string;
  content?: string;
  page_index?: number;
}

export interface Exam {
  id: string;
  name: string;
  grading_structure: any[]; // À préciser selon la structure JSON
}

export interface Copy {
  id: string;
  status: 'STAGING' | 'READY' | 'LOCKED' | 'GRADED';
  exam: Exam;
  booklets: Array<{
    id: string;
    pages_images: string[];
  }>;
}
