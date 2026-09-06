"use client";
import clsx from "clsx";

export default function LoadingSpinner({ size = "md", className }: { size?: "sm" | "md" | "lg"; className?: string }) {
  const sizeClass = { sm: "w-4 h-4 border-2", md: "w-8 h-8 border-2", lg: "w-12 h-12 border-[3px]" }[size];
  return (
    <div
      className={clsx(
        sizeClass,
        "rounded-full border-white/20 border-t-white animate-spin",
        className
      )}
    />
  );
}

export function PageLoader() {
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <LoadingSpinner size="lg" />
        <p className="text-white/60 text-sm">Loading...</p>
      </div>
    </div>
  );
}
