export interface Pose {
  id: number;
  oss_url: string;
  thumbnail_url?: string;
  title: string;
  description?: string;
  scene_category?: string;
  angle?: string;
  props?: string[];
  shooting_tips?: string;
  ai_tags?: string;
  view_count: number;
  created_at: string;
}

export interface SearchResponse {
  poses: Pose[];
  total: number;
  page: number;
  per_page: number;
  suggestions?: string[];
}

export interface Category {
  name: string;
  count: number;
}
