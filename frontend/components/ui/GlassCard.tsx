"use client";
import clsx from "clsx";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  flat?: boolean;
  onClick?: () => void;
}

export default function GlassCard({ children, className, flat, onClick }: GlassCardProps) {
  return (
    <div
      className={clsx(flat ? "glass-flat" : "glass", "p-6", onClick && "cursor-pointer", className)}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
