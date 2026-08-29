import type { ButtonHTMLAttributes, InputHTMLAttributes, LabelHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  const base =
    "inline-flex items-center justify-center rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const variants: Record<string, string> = {
    primary: "bg-emerald-600 text-white hover:bg-emerald-700",
    secondary: "bg-slate-100 text-slate-900 hover:bg-slate-200",
    danger: "bg-red-50 text-red-700 hover:bg-red-100",
  };
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 ${className}`}
      {...props}
    />
  );
}

export function Select({ className = "", children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}

export function Label({ className = "", ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={`mb-1 block text-sm font-medium text-slate-700 ${className}`} {...props} />;
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function PageHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-8">
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    DRAFT: "bg-slate-100 text-slate-700",
    CALCULATED: "bg-blue-100 text-blue-700",
    FEE_PAID: "bg-amber-100 text-amber-700",
    SUBMITTED: "bg-purple-100 text-purple-700",
    ACCEPTED: "bg-emerald-100 text-emerald-700",
    REJECTED: "bg-red-100 text-red-700",
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${colors[status] ?? "bg-slate-100 text-slate-700"}`}>
      {status}
    </span>
  );
}
