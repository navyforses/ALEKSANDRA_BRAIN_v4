import Image from "next/image";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "მინიმალისტური ვერსია | ALEKSANDRA_BRAIN",
  description:
    "ALEKSANDRA_BRAIN-ის დამოუკიდებელი მინიმალისტური ვერსია: მშვიდი სივრცე, პროპორციული ტიპოგრაფია და ექიმთან განხილვაზე ორიენტირებული სტრუქტურა.",
  robots: { index: true, follow: true },
  alternates: { canonical: "/minimal" },
  openGraph: {
    title: "მინიმალისტური ვერსია | ALEKSANDRA_BRAIN",
    description:
      "მშვიდი, დამოუკიდებელი და ოჯახისზე ორიენტირებული ვერსია ალექსანდრას დაკვირვებების დასალაგებლად.",
    url: "/minimal",
    siteName: "ALEKSANDRA_BRAIN",
    type: "website",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "ALEKSANDRA_BRAIN" }],
  },
};

const principles = [
  {
    number: "01",
    title: "მთავარი კითხვა",
    text: "გვერდი იწყება ერთი მშვიდი კითხვით და მხოლოდ შემდეგ აჩვენებს დაკვირვებებს, წყაროებსა და ჰიპოთეზებს.",
  },
  {
    number: "02",
    title: "ნაკლები ხმაური",
    text: "ვიყენებთ თეთრ სივრცეს, მოკლე ტექსტს და თხელ ხაზებს, რათა ვიზუალმა არ დაამძიმოს ოჯახის გამოცდილება.",
  },
  {
    number: "03",
    title: "ექიმთან განხილვა",
    text: "სისტემა აწესრიგებს ინფორმაციას, მაგრამ საბოლოო გადაწყვეტილება ყოველთვის რჩება კლინიკურ გუნდთან.",
  },
];

const flow = ["დაკვირვება", "წყარო", "ჰიპოთეზა", "ექიმთან განხილვა"];

export default function StandaloneMinimalPage() {
  return (
    <main className="min-h-screen bg-[#f7f5f0] text-zinc-950">
      <section className="mx-auto grid min-h-screen w-full max-w-[1420px] grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <div className="min-w-0 flex min-h-[54vh] flex-col justify-between border-zinc-200 px-5 py-6 sm:px-10 sm:py-10 lg:min-h-screen lg:border-r lg:px-16 lg:py-14">
          <header className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="h-2.5 w-2.5 rounded-full bg-zinc-950" />
              <span className="font-mono text-[0.66rem] uppercase tracking-[0.24em] text-zinc-600">ALEKSANDRA_BRAIN</span>
            </div>
            <span className="rounded-full border border-zinc-300 px-4 py-2 font-mono text-[0.6rem] uppercase tracking-[0.16em] text-zinc-500">
              permanent minimal site
            </span>
          </header>

          <div className="py-14 sm:py-20 lg:py-16">
            <p className="max-w-xl font-mono text-[0.72rem] uppercase tracking-[0.24em] text-zinc-500">
              დამოუკიდებელი მინიმალისტური ვერსია
            </p>
            <h1 className="mt-8 max-w-3xl text-[clamp(2.15rem,4.2vw,4.9rem)] font-medium leading-[1.04] tracking-[-0.045em] text-zinc-950">
              მშვიდი სივრცე ალექსანდრას დაკვირვებებისთვის.
            </h1>
            <p className="mt-8 max-w-2xl text-base leading-8 text-zinc-600 sm:text-lg">
              ეს ვერსია შეგნებულად არ იყენებს დიდ, მძიმე სათაურებს. მთავარი აქ არის სისუფთავე, მოკლე ტექსტი და ისეთი ვიზუალური ტონი, რომელიც ეხმარება ოჯახს ინფორმაციის დალაგებაში — ზედმეტი დატვირთვის გარეშე.
            </p>
          </div>

          <div className="grid gap-4 border-t border-zinc-300 pt-6 sm:grid-cols-3">
            <div>
              <p className="font-mono text-xs text-zinc-400">რეჟიმი</p>
              <p className="mt-2 text-sm font-semibold text-zinc-900">ოჯახზე ორიენტირებული</p>
            </div>
            <div>
              <p className="font-mono text-xs text-zinc-400">ტონი</p>
              <p className="mt-2 text-sm font-semibold text-zinc-900">მშვიდი და ზუსტი</p>
            </div>
            <div>
              <p className="font-mono text-xs text-zinc-400">საზღვარი</p>
              <p className="mt-2 text-sm font-semibold text-zinc-900">ექიმთან განხილული</p>
            </div>
          </div>
        </div>

        <aside className="min-w-0 px-5 py-6 sm:px-10 sm:py-10 lg:px-14 lg:py-14">
          <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(18rem,0.9fr)]">
            <div className="min-w-0 rounded-[2rem] border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="font-mono text-xs uppercase tracking-[0.2em] text-zinc-400">Digital twin</p>
                  <h2 className="mt-3 max-w-md text-2xl font-medium leading-tight tracking-[-0.035em] text-zinc-950 sm:text-3xl">
                    ტვინი, როგორც მშვიდი სიგნალი
                  </h2>
                </div>
                <span className="rounded-full bg-[#f6f4ef] px-3 py-1 font-mono text-[0.62rem] uppercase tracking-[0.16em] text-zinc-500">visual</span>
              </div>

              <div className="mt-8 flex justify-center">
                <div className="relative aspect-square w-full max-w-[25rem] overflow-hidden rounded-full border border-zinc-200 bg-[#efede6]">
                  <Image
                    src="/assets/generated_digital_twin_brain.webp"
                    alt="გენერირებული ციფრული ტვინის მინიმალისტური ვიზუალი"
                    fill
                    sizes="(min-width: 1280px) 400px, (min-width: 1024px) 42vw, 88vw"
                    className="object-contain p-8 opacity-95 mix-blend-multiply sm:p-10"
                    priority
                  />
                </div>
              </div>

              <div className="mt-8 grid grid-cols-2 gap-2 text-center text-xs text-zinc-500 sm:grid-cols-4">
                {flow.map((item) => (
                  <span key={item} className="min-w-0 rounded-full bg-zinc-100 px-2 py-2.5 leading-snug">
                    {item}
                  </span>
                ))}
              </div>
            </div>

            <div className="min-w-0 rounded-[2rem] bg-zinc-950 p-6 text-white sm:p-8">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-zinc-400">კლინიკური საზღვარი</p>
              <p className="mt-5 text-[clamp(1.35rem,2.1vw,2rem)] font-medium leading-tight tracking-[-0.035em]">
                პლატფორმა აწყობს ინფორმაციას და კითხვებს; მკურნალობის გადაწყვეტილება რჩება კლინიკურ გუნდთან.
              </p>
            </div>
          </div>

          <div className="mt-5 grid min-w-0 gap-4 sm:grid-cols-3">
            {principles.map((item) => (
              <article key={item.number} className="min-w-0 rounded-[1.5rem] border border-zinc-200 bg-white p-5">
                <p className="font-mono text-xs text-zinc-400">{item.number}</p>
                <h3 className="mt-5 text-xl font-medium leading-tight tracking-[-0.04em] text-zinc-950">{item.title}</h3>
                <p className="mt-4 text-sm leading-7 text-zinc-600">{item.text}</p>
              </article>
            ))}
          </div>
        </aside>
      </section>
    </main>
  );
}
