"use server";

import { revalidatePath } from "next/cache";
import { updateHypothesisReview } from "@/lib/supabase";

const allowed = new Set(["confirmed", "under_review", "rejected"]);

export async function reviewHypothesis(formData: FormData) {
  const id = String(formData.get("id") || "");
  const status = String(formData.get("status") || "");
  const title = String(formData.get("title") || "hypothesis");
  const userOutcome = String(formData.get("outcome") || "").trim();

  if (!id || !allowed.has(status)) {
    return;
  }

  const autoOutcome =
    status === "confirmed"
      ? `Phase 2.5D curator action: evidence links confirmed for research follow-up; not a clinical recommendation. ${title}`
      : `Phase 2.5D curator action: moved to ${status} for research review. ${title}`;

  // User-supplied outcome wins when present; auto-generated string is the
  // fallback so a blank submission still records a meaningful audit note.
  const outcome = userOutcome
    ? `${userOutcome}  [auto: ${autoOutcome}]`
    : autoOutcome;

  await updateHypothesisReview(
    id,
    status as "confirmed" | "under_review" | "rejected",
    outcome,
  );
  revalidatePath("/hypotheses");
  revalidatePath(`/hypotheses/${id}`);
  revalidatePath("/dashboard");
}
