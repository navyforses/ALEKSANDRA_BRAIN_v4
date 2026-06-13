// Hand-drawn, thin-stroke icons. Kept in-house rather than pulled from a
// library so the mark set feels of-a-piece with the rest of the system —
// quiet, even-weight, never decorative for its own sake.

import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function base(props: IconProps) {
  return {
    width: 20,
    height: 20,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    ...props,
  };
}

export function IconToday(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
    </svg>
  );
}

export function IconResearch(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="11" cy="11" r="6" />
      <path d="M20 20l-3.5-3.5" />
    </svg>
  );
}

export function IconBrain(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 5.5a2.5 2.5 0 0 0-4.6-1.3A2.4 2.4 0 0 0 4.7 7 2.6 2.6 0 0 0 4 11a2.5 2.5 0 0 0 .8 4 2.5 2.5 0 0 0 4.8 1V5.5Z" />
      <path d="M12 5.5a2.5 2.5 0 0 1 4.6-1.3A2.4 2.4 0 0 1 19.3 7a2.6 2.6 0 0 1 .7 4 2.5 2.5 0 0 1-.8 4 2.5 2.5 0 0 1-4.8 1" />
      <path d="M12 5.5V16" />
    </svg>
  );
}

export function IconBrief(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 3h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
      <path d="M14 3v4h4M8.5 12.5h7M8.5 16h7M8.5 9h3" />
    </svg>
  );
}

export function IconHistory(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
      <path d="M5 3v4h4" />
      <path d="M12 8v4l3 2" />
    </svg>
  );
}

export function IconPlus(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function IconArrowUp(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 19V5M6 11l6-6 6 6" />
    </svg>
  );
}

export function IconClose(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function IconMic(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </svg>
  );
}

export function IconStop(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="6" y="6" width="12" height="12" rx="2.5" />
    </svg>
  );
}

export function IconAttach(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M20 11.5l-7.6 7.6a4.5 4.5 0 0 1-6.4-6.4l8-8a3 3 0 0 1 4.3 4.3l-8 8a1.5 1.5 0 0 1-2.2-2.1l7.1-7.2" />
    </svg>
  );
}

export function IconPrint(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 9V3h12v6" />
      <path d="M6 18H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2h-2" />
      <rect x="6" y="14" width="12" height="7" rx="1" />
    </svg>
  );
}

export function IconUndo(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M3 8h11a6 6 0 0 1 0 12H8" />
      <path d="M6.5 4.5 3 8l3.5 3.5" />
    </svg>
  );
}

export function IconSun(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
    </svg>
  );
}

export function IconMoon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5Z" />
    </svg>
  );
}

export function IconPaper(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 3h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
      <path d="M14 3v4h4" />
    </svg>
  );
}

export function IconHypothesis(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M9 3h6M10 3v5l-4 9a2 2 0 0 0 1.8 3h8.4a2 2 0 0 0 1.8-3l-4-9V3" />
      <path d="M7.5 14h9" />
    </svg>
  );
}

export function IconTherapy(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3v18M3 12h18" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

export function IconLock(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

export type IconComponent = (props: IconProps) => React.ReactElement;
