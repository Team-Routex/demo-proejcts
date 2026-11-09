"use client";

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from "@tanstack/react-table";
import { api } from "@/lib/api";
import { User } from "@/types";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Dialog } from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/Skeleton";
import { Avatar } from "@/components/ui/Avatar";
import { formatDate } from "@/lib/utils";
import {
  Search,
  CheckCircle,
  XCircle,
  Shield,
  Trash2,
  Edit2,
  ChevronLeft,
  ChevronRight,
  UserCheck,
  UserX,
} from "lucide-react";

const columnHelper = createColumnHelper<User>();

export default function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [page, setPage] = useState(1);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [editFullName, setEditFullName] = useState("");
  const [editRole, setEditRole] = useState("user");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users-table", search, roleFilter, page],
    queryFn: () =>
      api.admin.users({
        search,
        role: roleFilter,
        page,
        limit: 10,
      }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<User> }) =>
      api.admin.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users-table"] });
      setEditUser(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.admin.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users-table"] });
    },
  });

  const columns = useMemo(
    () => [
      columnHelper.accessor("full_name", {
        header: "User",
        cell: (info) => {
          const u = info.row.original;
          return (
            <div className="flex items-center gap-2.5">
              <Avatar
                src={u.avatar_url}
                name={u.full_name || u.username}
                size="sm"
              />
              <div>
                <p className="font-semibold text-xs text-slate-900 flex items-center gap-1">
                  {u.full_name || u.username}
                  {u.is_verified && <CheckCircle className="h-3 w-3 fill-[#f48840] text-white" />}
                </p>
                <p className="text-[11px] text-slate-400">@{u.username}</p>
              </div>
            </div>
          );
        },
      }),
      columnHelper.accessor("email", {
        header: "Email",
        cell: (info) => <span className="text-xs text-slate-600">{info.getValue()}</span>,
      }),
      columnHelper.accessor("role", {
        header: "Role",
        cell: (info) => {
          const r = info.getValue();
          return r === "admin" ? (
            <Badge variant="warning" className="gap-1 text-[11px]">
              <Shield className="h-3 w-3" /> Admin
            </Badge>
          ) : (
            <Badge variant="secondary" className="text-[11px]">User</Badge>
          );
        },
      }),
      columnHelper.accessor("is_verified", {
        header: "Verified",
        cell: (info) => {
          const verified = info.getValue();
          const u = info.row.original;
          return (
            <button
              onClick={() => updateMutation.mutate({ id: u.id, data: { is_verified: !verified } })}
              className="cursor-pointer"
              title="Click to toggle verification status"
            >
              {verified ? (
                <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                  <CheckCircle className="h-4 w-4" /> Yes
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs text-slate-400 font-medium">
                  <XCircle className="h-4 w-4" /> No
                </span>
              )}
            </button>
          );
        },
      }),
      columnHelper.accessor("is_active", {
        header: "Status",
        cell: (info) => {
          const active = info.getValue();
          const u = info.row.original;
          return (
            <button
              onClick={() => updateMutation.mutate({ id: u.id, data: { is_active: !active } })}
              className="cursor-pointer"
              title="Click to toggle active status"
            >
              {active ? (
                <Badge variant="success" className="text-[10px]">Active</Badge>
              ) : (
                <Badge variant="destructive" className="text-[10px]">Disabled</Badge>
              )}
            </button>
          );
        },
      }),
      columnHelper.accessor("total_blogs" as any, {
        header: "Blogs",
        cell: (info) => {
          const val = info.getValue() as number;
          return (
            <span className="text-xs font-semibold text-slate-700">
              {val ?? 0}
            </span>
          );
        },
      }),
      columnHelper.accessor("total_interactions" as any, {
        header: "Interactions",
        cell: (info) => {
          const val = info.getValue() as number;
          return (
            <span className="text-xs font-semibold text-slate-700">
              {val ?? 0}
            </span>
          );
        },
      }),
      columnHelper.accessor("created_at", {
        header: "Joined",
        cell: (info) => (
          <span className="text-xs text-slate-500 whitespace-nowrap">
            {formatDate(info.getValue())}
          </span>
        ),
      }),
      columnHelper.display({
        id: "actions",
        header: () => <div className="text-right">Actions</div>,
        cell: (info) => {
          const u = info.row.original;
          return (
            <div className="flex items-center justify-end gap-1.5">
              <button
                onClick={() => {
                  setEditUser(u);
                  setEditFullName(u.full_name || "");
                  setEditRole(u.role);
                }}
                className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900"
                title="Edit user"
              >
                <Edit2 className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => {
                  if (confirm(`Delete user ${u.username}? This will remove all their blogs.`)) {
                    deleteMutation.mutate(u.id);
                  }
                }}
                className="rounded p-1 text-slate-400 hover:text-slate-600 hover:text-slate-900"
                title="Delete user"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        },
      }),
    ],
    [updateMutation, deleteMutation]
  );

  const items = useMemo(() => data?.items || [], [data]);

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            User Management
          </h1>
          <p className="text-sm text-slate-500">
            Manage permissions, author verification badges, and account activity
          </p>
        </div>
      </div>

      {/* Filter and search bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search by username, full name, or email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9 text-xs"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => {
            setRoleFilter(e.target.value);
            setPage(1);
          }}
          className="h-10 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700"
        >
          <option value="">All Roles</option>
          <option value="user">Regular User</option>
          <option value="admin">Administrator</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-700">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-4 py-3.5">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                      No users match your criteria.
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      className="hover:bg-slate-50 transition-colors"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-3.5">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
            <span className="text-xs text-slate-500">
              Page {data.page} of {data.total_pages} ({data.total} total users)
            </span>
            <div className="flex gap-1.5">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Edit User Dialog */}
      <Dialog
        open={!!editUser}
        onClose={() => setEditUser(null)}
        title="Edit User Account"
        description={`Modify properties for @${editUser?.username}`}
      >
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase text-slate-600">Full Name</label>
            <Input
              value={editFullName}
              onChange={(e) => setEditFullName(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase text-slate-600">Role</label>
            <select
              value={editRole}
              onChange={(e) => setEditRole(e.target.value)}
              className="w-full h-10 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setEditUser(null)}>
              Cancel
            </Button>
            <Button
              size="sm"
              isLoading={updateMutation.isPending}
              onClick={() => {
                if (editUser) {
                  updateMutation.mutate({
                    id: editUser.id,
                    data: { full_name: editFullName, role: editRole as any },
                  });
                }
              }}
            >
              Save Changes
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

