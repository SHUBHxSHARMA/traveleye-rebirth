import type { Metadata } from "next";
import { StartForm } from "@/components/StartForm";

export const metadata: Metadata = {
  title: "Begin",
  description: "Choose the name Travel Eye should use on this device.",
};

export default function StartPage() {
  return <StartForm />;
}
