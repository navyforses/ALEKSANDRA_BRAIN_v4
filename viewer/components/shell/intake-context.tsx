"use client";

// The intake console is the heart of the interface, so it must be
// reachable from anywhere with one gesture. This context lets any client
// component (the Today hero, the header "+", a keyboard shortcut) open the
// single shared console without each surface re-implementing it.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

interface IntakeContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
}

const IntakeContext = createContext<IntakeContextValue | null>(null);

export function IntakeProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const toggle = useCallback(() => setOpen((v) => !v), []);

  // Cmd/Ctrl-K opens the console; Escape closes it. The shortcut is a
  // quiet convenience for a returning user, never required.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const value = useMemo(() => ({ open, setOpen, toggle }), [open, toggle]);
  return <IntakeContext.Provider value={value}>{children}</IntakeContext.Provider>;
}

export function useIntake(): IntakeContextValue {
  const ctx = useContext(IntakeContext);
  if (!ctx) {
    throw new Error("useIntake must be used within an IntakeProvider");
  }
  return ctx;
}
