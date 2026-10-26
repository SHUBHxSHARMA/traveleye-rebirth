import Link from "next/link";
import type { ComponentProps } from "react";

type Variant = "primary" | "secondary" | "quiet";

const variantClass: Record<Variant, string> = {
  primary: "bg-primary px-5 text-ivory hover:bg-primary-dark",
  secondary:
    "border border-primary/80 bg-transparent px-5 text-primary hover:bg-primary hover:text-ivory",
  quiet: "text-primary underline-offset-4 hover:underline",
};

const base =
  "inline-flex min-h-11 items-center justify-center gap-2 text-sm font-medium transition-colors motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-50";

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ComponentProps<"button"> & { variant?: Variant }) {
  return (
    <button
      type={type}
      className={`${base} ${variantClass[variant]} ${className}`}
      {...props}
    />
  );
}

export function ButtonLink({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant }) {
  return <Link className={`${base} ${variantClass[variant]} ${className}`} {...props} />;
}
