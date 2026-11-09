"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { AlertCircle, Lock, Mail, ArrowRight } from "lucide-react";

const loginSchema = z.object({
  identifier: z.string().min(1, "Username or email is required"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type LoginFormData = z.infer<typeof loginSchema>;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/dashboard";
  const { login } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null);
    try {
      await login({
        identifier: data.identifier,
        password: data.password,
      });
      router.push(redirect);
    } catch (err: any) {
      setServerError(err?.message || "Invalid credentials. Please try again.");
    }
  };

  return (
    <>
      {serverError && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase text-slate-600">
            Email or Username
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              {...register("identifier")}
              placeholder="admin or user@domain.com"
              className="pl-9"
              autoComplete="username"
            />
          </div>
          {errors.identifier && (
            <p className="text-xs text-red-600">{errors.identifier.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold uppercase text-slate-600">
              Password
            </label>
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              {...register("password")}
              type="password"
              placeholder="••••••••"
              className="pl-9"
              autoComplete="current-password"
            />
          </div>
          {errors.password && (
            <p className="text-xs text-red-600">{errors.password.message}</p>
          )}
        </div>

        <Button
          type="submit"
          className="w-full gap-2 mt-2"
          isLoading={isSubmitting}
        >
          <span>Sign In</span>
          <ArrowRight className="h-4 w-4" />
        </Button>
      </form>

      <div className="mt-6 text-center text-xs text-slate-500">
        Don't have an account yet?{" "}
        <Link
          href="/register"
          className="font-bold text-[#f48840] hover:text-[#e0752d] hover:underline"
          style={{ color: "#f48840" }}
        >
          Create an account
        </Link>
      </div>
    </>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md shadow-lg border-slate-200">
        <CardHeader className="space-y-1 text-center">
          <div
            className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-[#f48840] text-white font-extrabold text-2xl mb-2 shadow-sm"
            style={{ backgroundColor: "#f48840" }}
          >
            R
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Welcome Back</CardTitle>
          <CardDescription>
            Enter your credentials to access your author dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<div className="p-8 text-center text-xs text-slate-400">Loading form...</div>}>
            <LoginForm />
          </Suspense>
        </CardContent>
      </Card>
    </div>
  );
}
