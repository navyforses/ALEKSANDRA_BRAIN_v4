// Phase 5 BRAIN panel.
// Day 0: scaffold + inert input.
// Day 5: live activity feed via /api/manager/audit polling.

import ActivityFeed from '@/components/BrainPanel/ActivityFeed'

export default function BrainPanel() {
  return (
    <>
      <div className="h-14 border-b border-slate-200 flex items-center px-4 justify-between bg-slate-50">
        <h2 className="font-semibold text-slate-800 text-sm tracking-tight">BRAIN</h2>
        <div className="flex items-center space-x-2 text-xs text-medical-green font-medium">
          <span className="w-2 h-2 rounded-full bg-medical-green animate-pulse"></span>
          <span>Active</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="text-xs text-center text-slate-400 my-4 uppercase tracking-wider font-medium">
          Activity Log
        </div>
        <ActivityFeed />
      </div>

      <div className="p-4 bg-slate-50 border-t border-slate-200">
        <div className="rounded-md border border-slate-300 bg-white shadow-sm flex items-center p-2">
          <input
            type="text"
            placeholder="Ask BRAIN or drop file..."
            className="flex-1 px-2 py-1 text-sm bg-transparent outline-none border-none placeholder:text-slate-400 text-slate-800"
          />
        </div>
      </div>
    </>
  )
}
