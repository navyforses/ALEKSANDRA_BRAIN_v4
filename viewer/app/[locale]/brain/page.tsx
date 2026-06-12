import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { buildPageMetadata, type Locale } from "@/lib/seo";
import MriViewer from "./MriViewer";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "brain");
}

export default async function BrainPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const isKa = locale === "ka";

  return (
    <div className="space-y-6">
      {/* Privacy lock banner */}
      <div className="flex items-start gap-3 border border-medical-green bg-medical-green/5 p-4 rounded text-xs leading-relaxed text-medical-green">
        <span className="text-base select-none">🔒</span>
        <div>
          <p className="font-bold">
            {isKa 
              ? "ლოკალური და დაცული: ფაილები ბრაუზერს არ ტოვებს" 
              : "Private & Localized: MRI files never leave your computer"
            }
          </p>
          <p className="mt-1 opacity-90">
            {isKa 
              ? "NIfTI (.nii / .nii.gz) ფაილის დამუშავება ხდება მხოლოდ თქვენს ბრაუზერში WebGL-ის მეშვეობით. სერვერზე ატვირთვა ან მესამე მხარისთვის გადაცემა არ ხდება." 
              : "Your MRI files are parsed 100% client-side inside the browser using WebGL2. There are zero uploads, zero server processing, and zero telemetry."
            }
          </p>
        </div>
      </div>

      {/* Main MRI Viewer Canvas Container */}
      <div className="border border-border rounded bg-background p-4 sm:p-6">
        <MriViewer />
      </div>
    </div>
  );
}
