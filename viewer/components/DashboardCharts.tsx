"use client";

import React, { useState } from "react";
import { TrendingUp, Coins, BookOpen, Lightbulb, Calendar, AlertCircle } from "lucide-react";

type HypothesisCount = {
  status: string;
  count: number;
};

type DailySpend = {
  date: string;
  cost: number;
  tokens: number;
};

type DailyIngestion = {
  date: string;
  count: number;
  avgRelevance: number;
};

type DashboardChartsProps = {
  hypothesisCounts: HypothesisCount[];
  dailySpends: DailySpend[];
  dailyIngestion: DailyIngestion[];
  totalSpendLimitDaily: number;
  totalSpendLimitMonthly: number;
};

export default function DashboardCharts({
  hypothesisCounts,
  dailySpends,
  dailyIngestion,
  totalSpendLimitDaily = 10.0,
  totalSpendLimitMonthly = 60.0,
}: DashboardChartsProps) {
  const [timeframe, setTimeframe] = useState<"7d" | "30d">("7d");

  // Spend calculations
  const todaySpend = dailySpends[dailySpends.length - 1]?.cost ?? 0;
  const monthlySpendTotal = dailySpends.reduce((acc, curr) => acc + curr.cost, 0);

  const dailyPercentage = Math.min(100, (todaySpend / totalSpendLimitDaily) * 100);
  const monthlyPercentage = Math.min(100, (monthlySpendTotal / totalSpendLimitMonthly) * 100);

  // Filter trends based on timeframe
  const limitDays = timeframe === "7d" ? 7 : 30;
  const filteredSpends = dailySpends.slice(-limitDays);
  const filteredIngestion = dailyIngestion.slice(-limitDays);

  // SVG Chart Dimensions
  const chartWidth = 500;
  const chartHeight = 180;
  const padding = { top: 15, right: 15, bottom: 25, left: 40 };

  // Generate Ingestion Area Points
  const maxIngestionCount = Math.max(3, ...filteredIngestion.map((d) => d.count));
  const ingestionPoints = filteredIngestion.map((d, index) => {
    const x = padding.left + (index * (chartWidth - padding.left - padding.right)) / Math.max(1, filteredIngestion.length - 1);
    const y = chartHeight - padding.bottom - (d.count * (chartHeight - padding.top - padding.bottom)) / maxIngestionCount;
    return { x, y, data: d };
  });

  const ingestionPath = ingestionPoints.length > 0
    ? `M ${ingestionPoints[0].x} ${ingestionPoints[0].y} ` +
      ingestionPoints.slice(1).map((p) => `L ${p.x} ${p.y}`).join(" ")
    : "";

  const ingestionArea = ingestionPoints.length > 0
    ? `${ingestionPath} L ${ingestionPoints[ingestionPoints.length - 1].x} ${chartHeight - padding.bottom} L ${ingestionPoints[0].x} ${chartHeight - padding.bottom} Z`
    : "";

  // Generate Spend Bar positions
  const maxSpendCost = Math.max(0.1, ...filteredSpends.map((d) => d.cost));
  const spendBars = filteredSpends.map((d, index) => {
    const barWidth = Math.max(4, (chartWidth - padding.left - padding.right) / (filteredSpends.length * 1.5));
    const x = padding.left + (index * (chartWidth - padding.left - padding.right)) / Math.max(1, filteredSpends.length) + barWidth / 4;
    const h = (d.cost * (chartHeight - padding.top - padding.bottom)) / maxSpendCost;
    const y = chartHeight - padding.bottom - h;
    return { x, y, w: barWidth, h, cost: d.cost, date: d.date };
  });

  // Donut chart calculations
  const totalHypotheses = hypothesisCounts.reduce((acc, curr) => acc + curr.count, 0);
  const statusColors: Record<string, string> = {
    confirmed: "#059669", // emerald-600
    promising: "#06b6d4", // cyan-500
    pursuing: "#0891b2", // cyan-600
    under_review: "#eab308", // yellow-500
    rejected: "#dc2626", // red-600
    new: "#78716c", // stone-500
  };

  let accumulatedAngle = 0;
  const donutSegments = hypothesisCounts.map((item) => {
    const percentage = totalHypotheses > 0 ? (item.count / totalHypotheses) * 100 : 0;
    const angle = (item.count / (totalHypotheses || 1)) * 360;
    const startAngle = accumulatedAngle;
    accumulatedAngle += angle;

    // Convert polar coordinates to Cartesian
    const polarToCartesian = (centerX: number, centerY: number, radius: number, angleInDegrees: number) => {
      const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
      return {
        x: centerX + radius * Math.cos(angleInRadians),
        y: centerY + radius * Math.sin(angleInRadians),
      };
    };

    const cx = 90;
    const cy = 90;
    const r = 60;
    const start = polarToCartesian(cx, cy, r, startAngle);
    const end = polarToCartesian(cx, cy, r, startAngle + angle);
    const largeArcFlag = angle <= 180 ? "0" : "1";

    const pathData = percentage === 100
      ? `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r}`
      : `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;

    return {
      status: item.status,
      count: item.count,
      percentage,
      pathData,
      color: statusColors[item.status] || statusColors.new,
    };
  });

  return (
    <div className="grid gap-6">
      {/* Timeframe selector header */}
      <div className="flex items-center justify-between border-b border-stone-200 pb-3">
        <h2 className="text-lg font-semibold tracking-tight text-stone-900 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-cyan-600" />
          სტატისტიკა და ანალიტიკა
        </h2>
        <div className="inline-flex rounded-md bg-stone-100 p-0.5 ring-1 ring-stone-200">
          <button
            onClick={() => setTimeframe("7d")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
              timeframe === "7d"
                ? "bg-white text-stone-900 shadow-sm"
                : "text-stone-500 hover:text-stone-900"
            }`}
          >
            7 დღე
          </button>
          <button
            onClick={() => setTimeframe("30d")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
              timeframe === "30d"
                ? "bg-white text-stone-900 shadow-sm"
                : "text-stone-500 hover:text-stone-900"
            }`}
          >
            30 დღე
          </button>
        </div>
      </div>

      {/* Main grids */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">

        {/* Card 1: API Budget Gauge */}
        <div className="rounded-md border border-stone-200 bg-white p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase text-stone-500">ბიუჯეტის კონტროლი</span>
              <Coins className="h-4 w-4 text-amber-500" />
            </div>
            <h3 className="mt-3 text-lg font-semibold text-stone-900">დღიური და ყოველთვიური Spend</h3>

            {/* Daily Spend Gauge */}
            <div className="mt-4 space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-stone-600">დღევანდელი ხარჯი</span>
                <span className="font-semibold text-stone-950">
                  {todaySpend.toFixed(4)} / ${totalSpendLimitDaily.toFixed(2)}
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-stone-100 overflow-hidden ring-1 ring-stone-200/50">
                <div
                  className="h-full bg-cyan-600 transition-all duration-500"
                  style={{ width: `${dailyPercentage}%` }}
                />
              </div>
            </div>

            {/* Monthly Spend Gauge */}
            <div className="mt-4 space-y-1.5 border-t border-stone-100 pt-4">
              <div className="flex justify-between text-xs">
                <span className="text-stone-600">თვიური ჯამი</span>
                <span className="font-semibold text-stone-950">
                  {monthlySpendTotal.toFixed(4)} / ${totalSpendLimitMonthly.toFixed(2)}
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-stone-100 overflow-hidden ring-1 ring-stone-200/50">
                <div
                  className="h-full bg-emerald-600 transition-all duration-500"
                  style={{ width: `${monthlyPercentage}%` }}
                />
              </div>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-2 rounded bg-cyan-50/50 p-2 text-xs text-cyan-800 ring-1 ring-cyan-100">
            <AlertCircle className="h-4 w-4 shrink-0 text-cyan-600" />
            <span>ავტომატური budget-gate აქტიურია, დღიური ლიმიტი დაცულია.</span>
          </div>
        </div>

        {/* Card 2: Ingestion Rate Chart */}
        <div className="rounded-md border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase text-stone-500">ლიტერატურა (Ingestion rate)</span>
            <BookOpen className="h-4 w-4 text-cyan-500" />
          </div>
          <h3 className="mt-3 text-lg font-semibold text-stone-900">ნაშრომების შემოდინება</h3>

          {/* SVG Area Chart */}
          <div className="mt-4 flex justify-center">
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-auto overflow-visible">
              {/* Y Grid lines */}
              {[0, 0.5, 1].map((ratio) => {
                const y = padding.top + ratio * (chartHeight - padding.top - padding.bottom);
                const label = Math.round(maxIngestionCount * (1 - ratio));
                return (
                  <g key={ratio} className="opacity-40">
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={chartWidth - padding.right}
                      y2={y}
                      stroke="#e7e5e4"
                      strokeWidth="1"
                      strokeDasharray="4 4"
                    />
                    <text x={padding.left - 8} y={y + 4} textAnchor="end" className="text-[10px] fill-stone-400 font-mono">
                      {label}
                    </text>
                  </g>
                );
              })}

              {/* Area path */}
              {ingestionArea && (
                <path d={ingestionArea} fill="url(#ingestion-gradient)" className="opacity-20" />
              )}

              {/* Line path */}
              {ingestionPath && (
                <path d={ingestionPath} fill="none" stroke="#0891b2" strokeWidth="2" strokeLinecap="round" />
              )}

              {/* Scatter dots */}
              {ingestionPoints.map((p, idx) => (
                <g key={idx} className="group cursor-pointer">
                  <circle cx={p.x} cy={p.y} r="3.5" fill="#0891b2" stroke="#ffffff" strokeWidth="1.5" />
                  <title>{`${p.data.date}: ${p.data.count} ნაშრომი (Avg Rel: ${p.data.avgRelevance.toFixed(2)})`}</title>
                </g>
              ))}

              {/* X Axis Labels */}
              {filteredIngestion.length > 0 && (
                <g className="opacity-60">
                  <text x={padding.left} y={chartHeight - 6} textAnchor="start" className="text-[10px] fill-stone-500 font-mono">
                    {filteredIngestion[0].date}
                  </text>
                  <text x={chartWidth - padding.right} y={chartHeight - 6} textAnchor="end" className="text-[10px] fill-stone-500 font-mono">
                    {filteredIngestion[filteredIngestion.length - 1].date}
                  </text>
                </g>
              )}

              {/* Gradients */}
              <defs>
                <linearGradient id="ingestion-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0891b2" />
                  <stop offset="100%" stopColor="#0891b2" stopOpacity="0" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>

        {/* Card 3: Spend dynamics Bar chart */}
        <div className="rounded-md border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase text-stone-500">ხარჯვის დინამიკა (USD)</span>
            <Coins className="h-4 w-4 text-emerald-500" />
          </div>
          <h3 className="mt-3 text-lg font-semibold text-stone-900">ხარჯი დღეების მიხედვით</h3>

          {/* SVG Bar Chart */}
          <div className="mt-4 flex justify-center">
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-auto overflow-visible">
              {/* Y Grid lines */}
              {[0, 0.5, 1].map((ratio) => {
                const y = padding.top + ratio * (chartHeight - padding.top - padding.bottom);
                const label = (maxSpendCost * (1 - ratio)).toFixed(3);
                return (
                  <g key={ratio} className="opacity-40">
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={chartWidth - padding.right}
                      y2={y}
                      stroke="#e7e5e4"
                      strokeWidth="1"
                      strokeDasharray="4 4"
                    />
                    <text x={padding.left - 8} y={y + 4} textAnchor="end" className="text-[10px] fill-stone-400 font-mono">
                      ${label}
                    </text>
                  </g>
                );
              })}

              {/* Bars */}
              {spendBars.map((bar, idx) => (
                <g key={idx} className="group cursor-pointer">
                  <rect
                    x={bar.x}
                    y={bar.y}
                    width={bar.w}
                    height={Math.max(2, bar.h)}
                    fill="#059669"
                    rx="1.5"
                    className="hover:fill-emerald-700 transition-colors"
                  />
                  <title>{`${bar.date}: $${bar.cost.toFixed(5)}`}</title>
                </g>
              ))}

              {/* X Axis Labels */}
              {filteredSpends.length > 0 && (
                <g className="opacity-60">
                  <text x={padding.left} y={chartHeight - 6} textAnchor="start" className="text-[10px] fill-stone-500 font-mono">
                    {filteredSpends[0].date}
                  </text>
                  <text x={chartWidth - padding.right} y={chartHeight - 6} textAnchor="end" className="text-[10px] fill-stone-500 font-mono">
                    {filteredSpends[filteredSpends.length - 1].date}
                  </text>
                </g>
              )}
            </svg>
          </div>
        </div>

      </div>

      {/* Row 2: Hypothesis Donuts and Details */}
      <div className="grid gap-6 md:grid-cols-3">

        {/* Donut Chart */}
        <div className="rounded-md border border-stone-200 bg-white p-5 shadow-sm md:col-span-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase text-stone-500">ჰიპოთეზები</span>
              <Lightbulb className="h-4 w-4 text-cyan-500" />
            </div>
            <h3 className="mt-3 text-lg font-semibold text-stone-900">სტატუსების განაწილება</h3>
          </div>

          <div className="my-4 flex items-center justify-center">
            {totalHypotheses > 0 ? (
              <svg width="180" height="180" className="overflow-visible">
                {donutSegments.map((seg, idx) => (
                  <path
                    key={idx}
                    d={seg.pathData}
                    fill="none"
                    stroke={seg.color}
                    strokeWidth="18"
                    className="transition-all hover:stroke-[22px] cursor-pointer"
                  />
                ))}
                {/* Center Text */}
                <circle cx="90" cy="90" r="46" fill="#ffffff" />
                <text x="90" y="85" textAnchor="middle" className="text-xs font-mono fill-stone-400 uppercase tracking-wider">
                  ჯამი
                </text>
                <text x="90" y="108" textAnchor="middle" className="text-2xl font-bold fill-stone-900">
                  {totalHypotheses}
                </text>
              </svg>
            ) : (
              <div className="h-[180px] flex items-center justify-center text-xs text-stone-400">
                მონაცემები არ არის
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-x-3 gap-y-1.5 justify-center border-t border-stone-100 pt-3">
            {donutSegments.map((seg) => (
              <div key={seg.status} className="flex items-center gap-1.5 text-xs text-stone-600">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: seg.color }} />
                <span>
                  {seg.status}: <strong>{seg.count}</strong> ({seg.percentage.toFixed(0)}%)
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Dynamic Insights Panel */}
        <div className="rounded-md border border-stone-200 bg-white p-5 shadow-sm md:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase text-stone-500">ავტომატური ანალიტიკა</span>
              <Calendar className="h-4 w-4 text-cyan-600" />
            </div>
            <h3 className="mt-3 text-lg font-semibold text-stone-900">სისტემური დაკვირვებები</h3>

            <div className="mt-4 space-y-4">
              <div className="flex gap-3 text-sm leading-6">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-cyan-100 text-xs font-semibold text-cyan-800">
                  1
                </span>
                <div>
                  <h4 className="font-semibold text-stone-900">პერცეფციის ინტენსივობა</h4>
                  <p className="text-stone-600">
                    ბოლო {limitDays} დღეში შემოსულია და დამუშავებულია{" "}
                    <strong>{filteredIngestion.reduce((acc, curr) => acc + curr.count, 0)}</strong> სამეცნიერო ნაშრომი.
                    საშუალო შესაბამისობის ქულამ Aleksandra-ს დაზიანების რუკასთან შეადგინა{" "}
                    <strong>
                      {(
                        filteredIngestion.reduce((acc, curr) => acc + curr.avgRelevance, 0) /
                          Math.max(1, filteredIngestion.filter((i) => i.count > 0).length)
                      ).toFixed(2)}
                    </strong>
                    .
                  </p>
                </div>
              </div>

              <div className="flex gap-3 text-sm leading-6 border-t border-stone-100 pt-4">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs font-semibold text-emerald-800">
                  2
                </span>
                <div>
                  <h4 className="font-semibold text-stone-900">ბიუჯეტის მდგრადობა</h4>
                  <p className="text-stone-600">
                    ბოლო {limitDays} დღის განმავლობაში AI აგენტების ჯამური ხარჯი არის{" "}
                    <strong>${monthlySpendTotal.toFixed(4)}</strong>, რაც ყოველთვიური მაქსიმალური ლიმიტის (
                    ${totalSpendLimitMonthly.toFixed(2)}) დაახლოებით{" "}
                    <strong>{monthlyPercentage.toFixed(1)}%</strong>-ს შეადგენს.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 text-xs text-stone-400 text-right">
            სტატისტიკა განახლდა: {new Date().toLocaleDateString()} · {new Date().toLocaleTimeString()}
          </div>
        </div>

      </div>
    </div>
  );
}
