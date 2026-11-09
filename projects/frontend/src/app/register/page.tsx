"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { AlertCircle, Lock, Mail, User as UserIcon, ArrowRight } from "lucide-react";

const registerSchema = z
  .object({
    full_name: z.string().min(2, "Full name must be at least 2 characters"),
    username: z
      .string()
      .min(3, "Username must be at least 3 characters")
      .regex(/^[a-zA-Z0-9_-]+$/, "Username can only contain letters, numbers, hyphens and underscores"),
    email: z.string().email("Please enter a valid email address"),
    password: z.string().min(6, "Password must be at least 6 characters"),
    confirm_password: z.string().min(6, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { register: registerUser } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setServerError(null);
    try {
      await registerUser({
        full_name: data.full_name,
        username: data.username,
        email: data.email,
        password: data.password,
      });
      router.push("/dashboard");
    } catch (err: any) {
      setServerError(err?.message || "Registration failed. Please try again.");
    }
  };

  return (
    <div className="flex min-h-[85vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md shadow-lg border-slate-200">
        <CardHeader className="space-y-1 text-center">
          <div
            className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-[#f48840] text-white font-extrabold text-2xl mb-2 shadow-sm"
            style={{ backgroundColor: "#f48840" }}
          >
            R
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Create an Account</CardTitle>
          <CardDescription>
            Join RaftBlog to write articles, engage in discussions, and get real-time notifications
          </CardDescription>
        </CardHeader>
        <CardContent>
          {serverError && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{serverError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-slate-600">
                Full Name
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  {...register("full_name")}
                  placeholder="e.g. Grace Hopper"
                  className="pl-9"
                />
              </div>
              {errors.full_name && (
                <p className="text-xs text-red-600">{errors.full_name.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-slate-600">
                Username
              </label>
              <Input
                {...register("username")}
                placeholder="ghopper"
                autoComplete="username"
              />
              {errors.username && (
                <p className="text-xs text-red-600">{errors.username.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-slate-600">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  {...register("email")}
                  type="email"
                  placeholder="grace@compiler.org"
                  className="pl-9"
                  autoComplete="email"
                />
              </div>
              {errors.email && (
                <p className="text-xs text-red-600">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-slate-600">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  {...register("password")}
                  type="password"
                  placeholder="••••••••"
                  className="pl-9"
                  autoComplete="new-password"
                />
              </div>
              {errors.password && (
                <p className="text-xs text-red-600">{errors.password.message}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-slate-600">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  {...register("confirm_password")}
                  type="password"
                  placeholder="••••••••"
                  className="pl-9"
                  autoComplete="new-password"
                />
              </div>
              {errors.confirm_password && (
                <p className="text-xs text-red-600">{errors.confirm_password.message}</p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full gap-2 mt-4"
              isLoading={isSubmitting}
            >
              <span>Create Account</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-bold text-[#f48840] hover:text-[#e0752d] hover:underline"
              style={{ color: "#f48840" }}
            >
              Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

