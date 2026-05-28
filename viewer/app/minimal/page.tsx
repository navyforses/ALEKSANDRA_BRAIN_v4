import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "ALEKSANDRA_BRAIN | Portal",
  description:
    "This path redirects to the existing portal infrastructure. No standalone mock or invented data is rendered here.",
  robots: { index: false, follow: true },
  alternates: { canonical: "/ka" },
};

export default function StandaloneMinimalPage() {
  redirect("/ka");
}
