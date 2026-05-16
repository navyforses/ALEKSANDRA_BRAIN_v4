"use server";

import { revalidatePath } from "next/cache";
import { updateHypothesisReview } from "@/lib/supabase";

const allowed = new Set(["confirmed", "under_review", "rejected"]);

export async function reviewHypothesis(formData: FormData) {
  const id = String(formData.get("id") || "");
  const status = String(formData.get("status") || "");
  const title = String(formData.get("title") || "hypothesis");

  if (!id || !allowed.has(status)) {
    return;
  }

  const outcome =
    status === "confirmed"
      ? `Phase 2.5D curator action: evidence links confirmed for research follow-up; not a clinical recommendation. ${title}`
      : `Phase 2.5D curator action: moved to ${status} for research review. ${title}`;

  await updateHypothesisReview(
    id,
    status as "confirmed" | "under_review" | "rejected",
    outcome,
  );
  revalidatePath("/hypotheses");
  revalidatePath("/dashboard");
}
