"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Comment } from "@/types";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { LikeButton } from "./LikeButton";
import { formatDate } from "@/lib/utils";
import { Avatar } from "@/components/ui/Avatar";
import {
  MessageSquare,
  CornerDownRight,
  Trash2,
  Edit2,
  CheckCircle,
  AlertCircle,
  Reply,
  Send,
  X,
} from "lucide-react";

interface CommentSectionProps {
  blogId: number;
  initialComments: Comment[];
}

export function CommentSection({ blogId, initialComments }: CommentSectionProps) {
  const { user, isAuthenticated, isAdmin } = useAuth();
  const [comments, setComments] = useState<Comment[]>(initialComments);
  const [newContent, setNewContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [replyContent, setReplyContent] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  const totalCount = comments.reduce(
    (acc, c) => acc + 1 + (c.replies?.length || 0),
    0
  );

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.comments.create(blogId, {
        content: newContent.trim(),
        parent_id: null,
      });
      const commentWithUser: Comment = {
        ...created,
        user: {
          id: user!.id,
          username: user!.username,
          full_name: user!.full_name,
          avatar_url: user!.avatar_url,
          is_verified: user!.is_verified,
        },
        replies: [],
        likes_count: 0,
        has_liked: false,
      };
      setComments([commentWithUser, ...comments]);
      setNewContent("");
    } catch (err: any) {
      setError(err?.message || "Failed to post comment");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePostReply = async (parentId: number) => {
    if (!replyContent.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.comments.create(blogId, {
        content: replyContent.trim(),
        parent_id: parentId,
      });
      const replyWithUser: Comment = {
        ...created,
        user: {
          id: user!.id,
          username: user!.username,
          full_name: user!.full_name,
          avatar_url: user!.avatar_url,
          is_verified: user!.is_verified,
        },
        replies: [],
        likes_count: 0,
        has_liked: false,
      };

      setComments((prev) =>
        prev.map((c) => {
          if (c.id === parentId) {
            return {
              ...c,
              replies: [...(c.replies || []), replyWithUser],
            };
          }
          return c;
        })
      );
      setReplyingToId(null);
      setReplyContent("");
    } catch (err: any) {
      setError(err?.message || "Failed to post reply");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async (id: number) => {
    if (!editContent.trim()) return;
    try {
      await api.comments.update(id, { content: editContent.trim() });
      setComments((prev) =>
        prev.map((c) => {
          if (c.id === id) return { ...c, content: editContent.trim() };
          if (c.replies) {
            return {
              ...c,
              replies: c.replies.map((r) =>
                r.id === id ? { ...r, content: editContent.trim() } : r
              ),
            };
          }
          return c;
        })
      );
      setEditingId(null);
      setEditContent("");
    } catch (err: any) {
      setError(err?.message || "Failed to update comment");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this comment?")) return;
    try {
      await api.comments.delete(id);
      setComments((prev) =>
        prev
          .filter((c) => c.id !== id)
          .map((c) => ({
            ...c,
            replies: (c.replies || []).filter((r) => r.id !== id),
          }))
      );
    } catch (err: any) {
      setError(err?.message || "Failed to delete comment");
    }
  };

  return (
    <div className="space-y-12 mt-12">
      {/* ============================================================ */}
      {/* 1. Comments List (Stand Blog .sidebar-item.comments)          */}
      {/* ============================================================ */}
      <div className="bg-white p-7 sm:p-10 border border-[#eee] shadow-xs">
        <h2 className="stand-heading-rule">
          {totalCount} {totalCount === 1 ? "Comment" : "Comments"}
        </h2>

        {error && (
          <div className="mb-6 flex items-center gap-2 border-l-4 border-rose-500 bg-rose-50 p-4 text-xs text-rose-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {comments.length === 0 ? (
          <p className="text-sm text-[#7a7a7a] py-4 italic">
            No comments on this article yet. Be the first to share your thoughts!
          </p>
        ) : (
          <ul className="divide-y divide-[#eee]">
            {comments.map((comment) => (
              <li key={comment.id} className="py-6 first:pt-2 last:pb-2">
                {/* Top Level Comment */}
                <div className="flex items-start gap-4 sm:gap-6">
                  {/* Author Thumb */}
                  <div className="shrink-0">
                    <Avatar
                      src={comment.user?.avatar_url}
                      name={comment.user?.full_name || comment.user?.username}
                      size="lg"
                    />
                  </div>

                  {/* Right Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <h4 className="text-sm sm font-bold text-[#20232e] flex items-center gap-1.5">
                          <span>{comment.user?.full_name || comment.user?.username || "Anonymous"}</span>
                          {comment.user?.is_verified && (
                            <CheckCircle className="h-3.5 w-3.5 fill-[#f48840] text-white" />
                          )}
                        </h4>
                        <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wide">
                          {formatDate(comment.created_at)}
                        </span>
                      </div>

                      {/* Comment Actions (Edit / Delete) */}
                      {(user?.id === comment.user_id || isAdmin) && (
                        <div className="flex items-center gap-1">
                          {user?.id === comment.user_id && (
                            <button
                              onClick={() => {
                                setEditingId(comment.id);
                                setEditContent(comment.content);
                              }}
                              className="p-1 text-[#aaa] hover:text-[#f48840] transition-colors cursor-pointer"
                              title="Edit comment"
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(comment.id)}
                            className="p-1 text-[#aaa] hover:text-[#f48840] transition-colors cursor-pointer"
                            title="Delete comment"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Content or Edit Form */}
                    {editingId === comment.id ? (
                      <div className="mt-3 space-y-2">
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="w-full border border-[#eee] bg-[#f7f7f7] p-3 text-sm text-[#20232e] focus:border-[#f48840] focus:outline-none focus:ring-1 focus:ring-[#f48840]"
                          rows={3}
                        />
                        <div className="flex items-center gap-2 justify-end">
                          <button
                            onClick={() => setEditingId(null)}
                            className="px-3 py-1.5 text-xs text-[#7a7a7a] hover:text-[#f48840] cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleUpdate(comment.id)}
                            className="bg-[#f48840] hover:bg-[#e0752d] text-white px-4 py-1.5 text-xs font-bold uppercase tracking-wider transition-colors cursor-pointer"
                          >
                            Save
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="mt-2 text-sm text-[#7a7a7a] leading-relaxed whitespace-pre-line">
                        {comment.content}
                      </p>
                    )}

                    {/* Like & Reply Action bar */}
                    <div className="mt-3 flex items-center gap-4 text-xs">
                      <LikeButton
                        targetType="comment"
                        targetId={comment.id}
                        initialLiked={comment.has_liked}
                        initialCount={comment.likes_count || 0}
                        size="sm"
                      />

                      {isAuthenticated && (
                        <button
                          onClick={() => {
                            setReplyingToId(
                              replyingToId === comment.id ? null : comment.id
                            );
                            setReplyContent("");
                          }}
                          className="inline-flex items-center gap-1 font-bold text-xs uppercase tracking-wider text-[#aaa] hover:text-[#f48840] transition-colors cursor-pointer"
                        >
                          <Reply className="h-3 w-3" />
                          {replyingToId === comment.id ? "Cancel Reply" : "Reply"}
                        </button>
                      )}
                    </div>

                    {/* Inline Reply Form */}
                    {replyingToId === comment.id && (
                      <div className="mt-4 border-l-2 border-[#f48840] pl-4 space-y-2">
                        <textarea
                          placeholder={`Reply to ${comment.user?.full_name || comment.user?.username}...`}
                          value={replyContent}
                          onChange={(e) => setReplyContent(e.target.value)}
                          className="w-full border border-[#eee] bg-[#f7f7f7] p-3 text-sm text-[#20232e] focus:border-[#f48840] focus:outline-none focus:ring-1 focus:ring-[#f48840]"
                          rows={3}
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setReplyingToId(null)}
                            className="px-3 py-1.5 text-xs text-[#7a7a7a] hover:text-[#f48840] cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handlePostReply(comment.id)}
                            disabled={submitting || !replyContent.trim()}
                            className="bg-[#f48840] hover:bg-[#e0752d] disabled:opacity-50 text-white px-4 py-1.5 text-xs font-bold uppercase tracking-wider transition-colors cursor-pointer"
                          >
                            {submitting ? "Posting..." : "Post Reply"}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* ============================================================ */}
                    {/* Threaded Replies (Stand Blog li.replied style)               */}
                    {/* ============================================================ */}
                    {comment.replies && comment.replies.length > 0 && (
                      <ul className="mt-6 space-y-4 border-l-2 border-[#eee] pl-4 sm:pl-8">
                        {comment.replies.map((reply) => (
                          <li key={reply.id} className="pt-2">
                            <div className="flex items-start gap-3 sm:gap-4">
                              <div className="shrink-0">
                                <Avatar
                                  src={reply.user?.avatar_url}
                                  name={reply.user?.full_name || reply.user?.username}
                                  size="md"
                                />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap items-center justify-between gap-1">
                                  <div>
                                    <h5 className="text-xs sm font-bold text-[#20232e] flex items-center gap-1">
                                      <span>{reply.user?.full_name || reply.user?.username || "Anonymous"}</span>
                                      {reply.user?.is_verified && (
                                        <CheckCircle className="h-3 w-3 fill-[#f48840] text-white" />
                                      )}
                                    </h5>
                                    <span className="text-[10px] font-semibold text-[#aaa] uppercase tracking-wide">
                                      {formatDate(reply.created_at)}
                                    </span>
                                  </div>

                                  {(user?.id === reply.user_id || isAdmin) && (
                                    <div className="flex items-center gap-1">
                                      {user?.id === reply.user_id && (
                                        <button
                                          onClick={() => {
                                            setEditingId(reply.id);
                                            setEditContent(reply.content);
                                          }}
                                          className="p-1 text-[#aaa] hover:text-[#f48840] transition-colors cursor-pointer"
                                          title="Edit reply"
                                        >
                                          <Edit2 className="h-3 w-3" />
                                        </button>
                                      )}
                                      <button
                                        onClick={() => handleDelete(reply.id)}
                                        className="p-1 text-[#aaa] hover:text-[#f48840] transition-colors cursor-pointer"
                                        title="Delete reply"
                                      >
                                        <Trash2 className="h-3 w-3" />
                                      </button>
                                    </div>
                                  )}
                                </div>

                                {editingId === reply.id ? (
                                  <div className="mt-2 space-y-2">
                                    <textarea
                                      value={editContent}
                                      onChange={(e) => setEditContent(e.target.value)}
                                      className="w-full border border-[#eee] bg-[#f7f7f7] p-2.5 text-xs text-[#20232e] focus:border-[#f48840] focus:outline-none focus:ring-1 focus:ring-[#f48840]"
                                      rows={2}
                                    />
                                    <div className="flex items-center gap-2 justify-end">
                                      <button
                                        onClick={() => setEditingId(null)}
                                        className="px-2 py-1 text-xs text-[#7a7a7a] cursor-pointer"
                                      >
                                        Cancel
                                      </button>
                                      <button
                                        onClick={() => handleUpdate(reply.id)}
                                        className="bg-[#f48840] hover:bg-[#e0752d] text-white px-3 py-1 text-xs font-bold uppercase transition-colors cursor-pointer"
                                      >
                                        Save
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <p className="mt-1.5 text-xs sm:text-sm text-[#7a7a7a] leading-relaxed whitespace-pre-line">
                                    {reply.content}
                                  </p>
                                )}

                                <div className="mt-2">
                                  <LikeButton
                                    targetType="comment"
                                    targetId={reply.id}
                                    initialLiked={reply.has_liked}
                                    initialCount={reply.likes_count || 0}
                                    size="sm"
                                  />
                                </div>
                              </div>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* ============================================================ */}
      {/* 2. Submit Comment Form (.sidebar-item.submit-comment)         */}
      {/* ============================================================ */}
      <div className="bg-white p-7 sm:p-10 border border-[#eee] shadow-xs">
        <h2 className="stand-heading-rule">Your Comment</h2>

        {isAuthenticated ? (
          <form onSubmit={handlePostComment} className="space-y-4">
            <div className="flex items-center gap-3 pb-2 text-xs text-[#7a7a7a]">
              <span>Signed in as <b>{user?.full_name || user?.username}</b></span>
            </div>

            <div>
              <textarea
                name="message"
                rows={5}
                placeholder="Type your comment here..."
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                required
                className="w-full border border-[#eee] bg-[#f7f7f7] p-4 text-sm text-[#20232e] placeholder-[#aaa] focus:border-[#f48840] focus:outline-none focus:ring-1 focus:ring-[#f48840] transition-colors"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={submitting || !newContent.trim()}
                className="inline-block bg-[#f48840] hover:bg-[#e0752d] disabled:opacity-50 text-white font-black text-xs uppercase tracking-widest px-8 py-3.5 transition-colors cursor-pointer"
              >
                {submitting ? "Submitting..." : "Submit Comment"}
              </button>
            </div>
          </form>
        ) : (
          <div className="p-6 text-center border border-dashed border-[#eee]">
            <p className="text-sm text-[#7a7a7a] mb-4">
              Please sign in to participate in the discussion and leave a comment.
            </p>
            <Link
              href="/login"
              className="inline-block bg-[#f48840] hover:bg-[#e0752d] text-white text-xs font-black uppercase tracking-wider px-6 py-3 transition-colors"
            >
              Sign In to Comment
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
