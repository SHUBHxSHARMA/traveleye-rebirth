import type { Metadata } from "next";
import { SettingsPanel } from "@/components/SettingsPanel";

export const metadata: Metadata = {
  title: "Settings",
  description: "Name, narration language, and progress stored on this device.",
};

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-14 md:px-8 md:py-20">
      <p className="text-xs uppercase tracking-[0.2em] text-accent">Preferences</p>
      <h1 className="mt-3 font-display text-5xl leading-tight text-primary md:text-6xl">Settings</h1>
      <p className="mt-4 max-w-xl text-lg leading-relaxed">
        Choices on this phone. Nothing here creates an account.
      </p>
      <div className="mt-10">
        <SettingsPanel />
      </div>
    </div>
  );
}
