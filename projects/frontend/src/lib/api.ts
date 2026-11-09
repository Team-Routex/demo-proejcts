import { ApiResponse, Blog, Category, Tag, Comment, Notification, PaginatedResponse, User, UserStats, AdminOverview, TopBlog, TopAuthor } from "@/types";

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
}

export class ApiError extends Error {
  status: number;
  errors?: string[];
  constructor(message: string, status: number = 400, errors?: string[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("raft_auth_token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem("raft_auth_token", token);
    document.cookie = `raft_auth_token=${token}; path=/; max-age=604800; SameSite=Lax`;
  } else {
    localStorage.removeItem("raft_auth_token");
    document.cookie = "raft_auth_token=; path=/; max-age=0; SameSite=Lax";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const baseUrl = getApiBase();
  const url = endpoint.startsWith("http") ? endpoint : `${baseUrl}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type");
  let data: any = null;
  if (contentType && contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = { message: await response.text() };
  }

  if (!response.ok) {
    const errorMsg = data?.message || response.statusText || "Request failed";
    const errors = data?.errors || [];
    throw new ApiError(errorMsg, response.status, errors);
  }

  return (data?.data !== undefined ? data.data : data) as T;
}

export const api = {
  // Upload
  async uploadFile(file: File): Promise<string> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await request<{ url: string }>("/api/upload", {
      method: "POST",
      body: formData,
    });

    return res.url;
  },

  // Auth
  auth: {
    async register(data: { username: string; email: string; password: string; full_name?: string }) {
      return request<{ user: User; token: string }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async login(data: { identifier?: string; email?: string; username?: string; password: string }) {
      return request<{ user: User; token: string }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async me() {
      return request<{ user: User; stats: UserStats }>("/api/auth/me");
    },
    async updateProfile(data: Partial<User>) {
      return request<User>("/api/auth/profile", {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    async logout() {
      try {
        await request("/api/auth/logout", { method: "POST" });
      } catch {
        // ignore
      } finally {
        setToken(null);
      }
    },
  },

  // Categories
  categories: {
    async list() {
      return request<Category[]>("/api/categories");
    },
    async get(slug: string) {
      return request<Category>(`/api/categories/${slug}`);
    },
    async create(data: { name: string; description?: string }) {
      return request<Category>("/api/categories", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  },

  // Tags
  tags: {
    async list() {
      return request<Tag[]>("/api/tags");
    },
    async get(slug: string) {
      return request<Tag>(`/api/tags/${slug}`);
    },
    async create(data: { name: string; slug?: string; description?: string }) {
      return request<Tag>("/api/tags", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async update(id: number, data: { name?: string; slug?: string; description?: string }) {
      return request<Tag>(`/api/tags/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    async delete(id: number) {
      return request<{ message: string }>(`/api/tags/${id}`, {
        method: "DELETE",
      });
    },
  },

  // Blogs
  blogs: {
    async list(params: {
      search?: string;
      category?: string;
      tag?: string;
      author?: string;
      sort?: string;
      page?: number;
      limit?: number;
    } = {}) {
      const sp = new URLSearchParams();
      if (params.search) sp.set("search", params.search);
      if (params.category) sp.set("category", params.category);
      if (params.tag) sp.set("tag", params.tag);
      if (params.author) sp.set("author", params.author);
      if (params.sort) sp.set("sort", params.sort);
      if (params.page) sp.set("page", String(params.page));
      if (params.limit) sp.set("limit", String(params.limit));

      const query = sp.toString() ? `?${sp.toString()}` : "";
      return request<PaginatedResponse<Blog>>(`/api/blogs${query}`);
    },
    async get(slug: string) {
      return request<Blog>(`/api/blogs/${slug}`);
    },
    async create(data: {
      title: string;
      content: string;
      summary?: string;
      featured_image?: string;
      category_ids?: number[];
      tag_ids?: number[];
      action?: "draft" | "submit";
    }) {
      return request<Blog>("/api/blogs", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async update(
      id: number,
      data: {
        title?: string;
        content?: string;
        summary?: string;
        featured_image?: string;
        category_ids?: number[];
        tag_ids?: number[];
        action?: "draft" | "submit";
      }
    ) {
      return request<Blog>(`/api/blogs/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    async delete(id: number) {
      return request<{ message: string }>(`/api/blogs/${id}`, {
        method: "DELETE",
      });
    },
    async submit(id: number) {
      return request<Blog>(`/api/blogs/${id}/submit`, {
        method: "POST",
      });
    },
    async myBlogs(params: { status?: string; page?: number; limit?: number } = {}) {
      const sp = new URLSearchParams();
      if (params.status) sp.set("status", params.status);
      if (params.page) sp.set("page", String(params.page));
      if (params.limit) sp.set("limit", String(params.limit));
      const query = sp.toString() ? `?${sp.toString()}` : "";
      return request<PaginatedResponse<Blog>>(`/api/blogs/user/me${query}`);
    },
  },

  // Comments
  comments: {
    async list(blogId: number) {
      return request<Comment[]>(`/api/blogs/${blogId}/comments`);
    },
    async create(blogId: number, data: { content: string; parent_id?: number | null }) {
      return request<Comment>(`/api/blogs/${blogId}/comments`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async update(id: number, data: { content: string }) {
      return request<Comment>(`/api/comments/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    async delete(id: number) {
      return request<{ message: string }>(`/api/comments/${id}`, {
        method: "DELETE",
      });
    },
  },

  // Reactions
  reactions: {
    async toggle(targetType: "blog" | "comment", targetId: number) {
      return request<{
        liked: boolean;
        likes_count: number;
        target_type: string;
        target_id: number;
      }>("/api/reactions/toggle", {
        method: "POST",
        body: JSON.stringify({ target_type: targetType, target_id: targetId }),
      });
    },
    async status(targetType: "blog" | "comment", targetId: number) {
      return request<{
        liked: boolean;
        likes_count: number;
        target_type: string;
        target_id: number;
      }>(`/api/reactions/status?target_type=${targetType}&target_id=${targetId}`);
    },
  },

  // Notifications
  notifications: {
    async list(params: { page?: number; limit?: number; unread_only?: boolean } = {}) {
      const sp = new URLSearchParams();
      if (params.page) sp.set("page", String(params.page));
      if (params.limit) sp.set("limit", String(params.limit));
      if (params.unread_only) sp.set("unread_only", "true");
      const query = sp.toString() ? `?${sp.toString()}` : "";
      return request<PaginatedResponse<Notification>>(`/api/notifications${query}`);
    },
    async unreadCount() {
      return request<{ unread_count: number }>("/api/notifications/unread-count");
    },
    async markRead(id: number) {
      return request<Notification>(`/api/notifications/${id}/read`, {
        method: "POST",
      });
    },
    async markAllRead() {
      return request<{ marked_count: number }>("/api/notifications/read-all", {
        method: "POST",
      });
    },
  },

  // Admin
  admin: {
    async overview() {
      return request<AdminOverview>("/api/admin/overview");
    },
    async analytics(days: number = 30) {
      return request<{
        user_registrations: Array<{ day: string; count: number }>;
        blog_publishing: Array<{ day: string; approved_count: number; pending_count: number }>;
        user_interactions: Array<{ day: string; likes: number; comments: number; replies: number; total: number }>;
      }>(`/api/admin/analytics?days=${days}`);
    },
    async topBlogs(limit: number = 5) {
      return request<TopBlog[]>(`/api/admin/top-blogs?limit=${limit}`);
    },
    async topAuthors(limit: number = 5) {
      return request<TopAuthor[]>(`/api/admin/top-authors?limit=${limit}`);
    },
    async users(params: { search?: string; role?: string; is_verified?: string; is_active?: string; page?: number; limit?: number } = {}) {
      const sp = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== "") sp.set(k, String(v));
      });
      return request<PaginatedResponse<User>>(`/api/admin/users?${sp.toString()}`);
    },
    async updateUser(id: number, data: Partial<User>) {
      return request<User>(`/api/admin/users/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    async deleteUser(id: number) {
      return request<{ message: string }>(`/api/admin/users/${id}`, {
        method: "DELETE",
      });
    },
    async blogs(params: { status?: string; search?: string; page?: number; limit?: number } = {}) {
      const sp = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== "") sp.set(k, String(v));
      });
      return request<PaginatedResponse<Blog>>(`/api/admin/blogs?${sp.toString()}`);
    },
    async moderateBlog(id: number, action: "approve" | "reject", rejection_reason?: string) {
      return request<Blog>(`/api/admin/blogs/${id}/moderate`, {
        method: "POST",
        body: JSON.stringify({ action, rejection_reason }),
      });
    },
    async deleteBlog(id: number) {
      return request<{ message: string }>(`/api/admin/blogs/${id}`, {
        method: "DELETE",
      });
    },
    async comments(params: { search?: string; page?: number; limit?: number } = {}) {
      const sp = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== "") sp.set(k, String(v));
      });
      return request<PaginatedResponse<Comment>>(`/api/admin/comments?${sp.toString()}`);
    },
    async deleteComment(id: number) {
      return request<{ message: string }>(`/api/admin/comments/${id}`, {
        method: "DELETE",
      });
    },
    async categories() {
      return request<Category[]>("/api/admin/categories");
    },
    async updateCategory(id: number, data: { name: string; description?: string }) {
      return request<Category>(`/api/admin/categories/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    async deleteCategory(id: number) {
      return request<{ message: string }>(`/api/admin/categories/${id}`, {
        method: "DELETE",
      });
    },
    async tags() {
      return request<Tag[]>("/api/admin/tags");
    },
    async createTag(data: { name: string; slug?: string; description?: string }) {
      return request<Tag>("/api/admin/tags", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async updateTag(id: number, data: { name?: string; slug?: string; description?: string }) {
      return request<Tag>(`/api/admin/tags/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    async deleteTag(id: number) {
      return request<{ message: string }>(`/api/admin/tags/${id}`, {
        method: "DELETE",
      });
    },
  },
};

