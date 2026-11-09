export interface User {
  id: number;
  username: string;
  email: string;
  role: "admin" | "user";
  is_verified: boolean;
  is_active?: boolean;
  full_name: string;
  avatar_url: string;
  bio?: string;
  website?: string;
  created_at: string;
}

export interface UserStats {
  total_blogs: number;
  approved_blogs: number;
  pending_blogs: number;
  rejected_blogs: number;
  draft_blogs: number;
  total_views: number;
  total_likes_received: number;
  total_comments_received: number;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string;
  created_by_id?: number | null;
  created_at: string;
  blog_count?: number;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
  description?: string;
  blog_count?: number;
  created_at?: string;
}

export interface Blog {
  id: number;
  title: string;
  slug: string;
  content: string;
  summary: string;
  featured_image: string;
  author_id: number;
  publication_status: "draft" | "published";
  approval_status: "pending" | "approved" | "rejected";
  rejection_reason?: string;
  views_count: number;
  created_at: string;
  updated_at: string;
  author?: {
    id: number;
    username: string;
    full_name: string;
    avatar_url: string;
    is_verified: boolean;
    bio?: string;
    website?: string;
  };
  categories?: Category[];
  tags?: Tag[];
  likes_count?: number;
  comments_count?: number;
  replies_count?: number;
  has_liked?: boolean;
}

export interface Comment {
  id: number;
  blog_id: number;
  user_id: number;
  parent_id: number | null;
  content: string;
  is_approved: boolean;
  created_at: string;
  updated_at: string;
  user?: {
    id: number;
    username: string;
    full_name: string;
    avatar_url: string;
    is_verified: boolean;
  };
  likes_count?: number;
  has_liked?: boolean;
  replies?: Comment[];
}

export interface Notification {
  id: number;
  user_id: number;
  sender_id: number;
  type: "comment" | "reply" | "like_blog" | "like_comment" | "blog_approved" | "blog_rejected";
  title: string;
  message: string;
  target_id: number | null;
  target_slug: string;
  is_read: boolean;
  created_at: string;
  sender?: {
    id: number;
    username: string;
    full_name: string;
    avatar_url: string;
  };
}

export interface AdminOverview {
  total_users: number;
  total_blogs: number;
  total_visits: number;
  total_interactions: number;
  breakdown: {
    likes: number;
    comments: number;
    pending_blogs: number;
    approved_blogs: number;
  };
}

export interface AnalyticsSeries {
  date: string;
  [key: string]: string | number;
}

export interface TopBlog {
  id: number;
  title: string;
  slug: string;
  author?: string;
  author_name?: string;
  author_username?: string;
  views_count?: number;
  total_views?: number;
  likes_count?: number;
  total_likes?: number;
  comments_count?: number;
  total_comments?: number;
  replies_count?: number;
  total_replies?: number;
  publication_status?: string;
  publication_date?: string;
  approval_status: string;
  created_at: string;
  engagement_score?: number;
}

export interface TopAuthor {
  id: number;
  name?: string;
  author_name?: string;
  username: string;
  avatar_url?: string;
  profile_image?: string;
  total_blogs: number;
  approved_blogs: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_replies: number;
  total_engagement?: number;
}

export interface ApiResponse<T> {
  status: boolean;
  message: string;
  data: T;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
