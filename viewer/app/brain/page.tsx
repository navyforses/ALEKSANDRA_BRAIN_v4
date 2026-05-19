import React from 'react'
import { Maximize, SlidersHorizontal, Layers, Play } from 'lucide-react'

// Phase 5 placeholder. Real NiiVue/R3F canvas mounts in VIS-* phase.
// All MRI data is client-side only (FND-01/FND-02) — no remote fetch
// from this route or any sibling route under viewer/app.

export default function BrainViewerPage() {
  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex flex-col space-y-4 border-b border-slate-200 pb-4 shrink-0">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Digital Twin / 3D Model
          </h1>
          <div className="flex space-x-2">
            <button className="flex items-center justify-center px-3 py-1.5 text-sm font-medium bg-slate-100 text-slate-600 rounded-md hover:bg-slate-200 transition-colors">
              <SlidersHorizontal className="h-4 w-4 mr-1.5" />
              Controls
            </button>
            <button className="flex items-center justify-center px-3 py-1.5 text-sm font-medium bg-white border border-slate-200 text-slate-700 rounded-md hover:bg-slate-50 transition-colors shadow-sm">
              <Maximize className="h-4 w-4 mr-1.5" />
              Fullscreen
            </button>
          </div>
        </div>

        <div className="flex space-x-2 overflow-x-auto pb-1">
          <button className="px-3 py-1.5 text-sm font-medium bg-slate-900 text-white rounded-md shadow-sm whitespace-nowrap">
            Doctor View (Clinical)
          </button>
          <button className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-md transition-colors whitespace-nowrap">
            Parent View (Simplified)
          </button>
          <button className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-md transition-colors whitespace-nowrap flex items-center">
            Researcher View (TVB) <Play className="w-3 h-3 ml-1.5" />
          </button>
        </div>
      </div>

      <div className="flex-1 relative bg-slate-50 border border-slate-200 rounded-lg overflow-hidden shadow-inner flex flex-col min-h-[500px]">
        <div className="absolute top-4 left-4 z-10 flex flex-col space-y-2">
          <button
            className="p-2 bg-white/90 backdrop-blur-sm border border-slate-200 rounded-md shadow-sm text-slate-600 hover:text-medical-purple transition-colors"
            title="Toggle Layers"
          >
            <Layers className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md mx-auto px-6">
            <div className="text-xs font-medium uppercase tracking-wider text-slate-400 mb-3">
              3D Viewer
            </div>
            <h3 className="text-base font-medium text-slate-900">In development</h3>
            <p className="text-sm text-slate-500 mt-2 leading-relaxed">
              Drop an MRI file (.nii or .nii.gz) here to render Aleksandra&apos;s
              brain in three dimensions. Mount point is wired; the viewer is
              under construction.
            </p>
          </div>
        </div>

        <div className="absolute bottom-4 left-0 right-0 z-10 flex justify-center pointer-events-none">
          <div className="bg-white/90 backdrop-blur-sm border border-slate-200 rounded-md shadow-sm px-4 py-2 flex space-x-6 text-xs font-medium pointer-events-auto">
            <div className="flex items-center">
              <span className="w-2.5 h-2.5 rounded-full bg-medical-red mr-2 border border-medical-red/20"></span>
              <span className="text-slate-700">Damaged (HIE)</span>
            </div>
            <div className="flex items-center">
              <span className="w-2.5 h-2.5 rounded-full bg-medical-green mr-2 border border-medical-green/20"></span>
              <span className="text-slate-700">Preserved</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
