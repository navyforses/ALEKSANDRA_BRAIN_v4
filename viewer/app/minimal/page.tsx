import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "ALEKSANDRA_BRAIN | Portal",
  description: "This path redirects to the real-data portal.",
  robots: { index: false, follow: true },
  alternates: { canonical: "/ka" },
};

export default function StandaloneMinimalPage() {
  redirect("/ka");
}
