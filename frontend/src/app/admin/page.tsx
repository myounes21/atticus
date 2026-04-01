"use client";

import { useState } from "react";
import Image from "next/image";
import CasesPanel from "@/components/cases/CasesPanel";
import DocumentsPanel from "@/components/documents/DocumentsPanel";
import { useAuthGuard } from "@/lib/useAuthGuard";

export default function AdminPage() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const { loading, user, logout } = useAuthGuard({ allowedRoles: ["admin"] });

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <section className="rounded-xl border border-outline-variant/30 bg-white px-6 py-4 shadow-sm">
          <p className="text-sm text-on-surface-variant">Loading admin workspace...</p>
        </section>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen bg-surface font-body text-on-surface antialiased">
      <aside className="fixed left-0 top-0 z-50 flex h-screen w-64 flex-col space-y-2 border-r border-outline-variant/20 bg-surface-container p-6 text-sm font-medium">
        <div className="mb-10 flex items-center gap-3">
          <div className="signature-gradient flex h-10 w-10 items-center justify-center rounded-xl text-white shadow-md">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: '"FILL" 1' }}>
              gavel
            </span>
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight text-primary">Atticus</h1>
            <p className="text-[9px] font-bold uppercase tracking-[0.2em] opacity-50">Admin Portal</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1.5">
          <button type="button" className="flex w-full items-center gap-3 rounded-lg bg-white px-4 py-3 text-primary shadow-sm">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: '"FILL" 1' }}>
              dashboard
            </span>
            <span className="font-semibold">Dashboard</span>
          </button>
          <button type="button" className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-on-surface-variant transition-all hover:bg-white/50 hover:text-primary">
            <span className="material-symbols-outlined">work</span>
            <span>Cases</span>
          </button>
          <button type="button" className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-on-surface-variant transition-all hover:bg-white/50 hover:text-primary">
            <span className="material-symbols-outlined">description</span>
            <span>Documents</span>
          </button>
          <button type="button" className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-on-surface-variant transition-all hover:bg-white/50 hover:text-primary">
            <span className="material-symbols-outlined">group</span>
            <span>Clients</span>
          </button>
          <button type="button" className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-on-surface-variant transition-all hover:bg-white/50 hover:text-primary">
            <span className="material-symbols-outlined">analytics</span>
            <span>Analytics</span>
          </button>
        </nav>

        <div className="mt-auto space-y-1 border-t border-outline-variant/20 pt-6">
          <button className="signature-gradient mb-4 flex w-full items-center justify-center gap-2 rounded-xl py-3.5 font-bold text-white shadow-lg transition-all hover:scale-[0.99] hover:shadow-xl">
            <span className="material-symbols-outlined text-sm">add</span>
            Initiate Case
          </button>
          <button type="button" className="flex w-full items-center gap-3 px-4 py-2 text-on-surface-variant transition-all hover:text-primary">
            <span className="material-symbols-outlined">help</span>
            <span>Help Center</span>
          </button>
          <button type="button" onClick={logout} className="flex w-full items-center gap-3 px-4 py-2 text-on-surface-variant transition-all hover:text-primary">
            <span className="material-symbols-outlined">logout</span>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <section className="ml-64 flex min-h-screen flex-1 flex-col bg-surface">
        <header className="sticky top-0 z-40 flex w-full items-center justify-between border-b border-outline-variant/10 bg-surface/80 px-10 py-6 backdrop-blur-md">
          <div>
            <h2 className="font-headline text-xl font-extrabold text-on-surface">The Informed Architect</h2>
            <p className="text-xs font-medium text-outline">Firm Administration &amp; Operations</p>
          </div>

          <div className="flex items-center gap-8">
            <label className="group relative">
              <span className="material-symbols-outlined absolute inset-y-0 left-3 flex items-center text-outline transition-colors group-focus-within:text-primary">
                search
              </span>
              <input
                className="w-72 rounded-full border-none bg-surface-container pl-10 pr-6 py-2.5 text-sm placeholder:text-outline/60 focus:ring-2 focus:ring-primary/20"
                placeholder="Search cases, docs, or lawyers..."
              />
            </label>

            <div className="flex items-center gap-5 border-l border-outline-variant/30 pl-8 text-outline">
              <button type="button" className="relative transition-colors hover:text-primary" aria-label="Notifications">
                <span className="material-symbols-outlined">notifications</span>
                <span className="absolute right-0 top-0 h-2 w-2 rounded-full border-2 border-surface bg-red-600" />
              </button>
              <button type="button" className="transition-colors hover:text-primary" aria-label="Settings">
                <span className="material-symbols-outlined">settings</span>
              </button>
            </div>

            <div className="flex items-center gap-4 pl-8">
              <div className="text-right">
                <p className="text-sm font-bold text-on-surface leading-tight">Admin</p>
                <p className="text-[11px] font-semibold uppercase tracking-tight text-outline">{user?.email ?? "Mr. Finch"}</p>
              </div>
              <Image
                alt="Admin profile"
                className="h-10 w-10 rounded-full object-cover ring-2 ring-primary/5 shadow-sm"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBAAAlvlgfi6TBj_xxCe0mQuuD1ldiVQMVB_fAOR955O8fXQqT53wiu55B29oLpkhzwnpEwAowLfOQ7hXsecqxHJziq6FTdqgKcYZnchVyXvpwdhBjcuvDvrliXnbVU7g-LeOM56gWADEMhSofQhq8AovRip3mN7mZBbk3X-kyl8KBR61GgEqHuc6pNtB5CEkIU-kbNvh-bJGHlzwh5K3msb417Zho2fKkIvLBeTX710ziXCZ5byN1CEEWRytwQ_QBV3qxO4wZw9j4"
                width={40}
                height={40}
              />
            </div>
          </div>
        </header>

        <div className="space-y-10 p-10">
          <div className="grid grid-cols-12 gap-8">
            <article className="col-span-12 flex flex-col justify-center rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-10 shadow-sm lg:col-span-7">
              <div className="space-y-4">
                <h3 className="font-headline text-3xl font-black tracking-tight text-on-surface">Administrative Overview</h3>
                <p className="max-w-2xl text-sm leading-relaxed text-on-surface-variant">
                  Infrastructure operational. Your workspace leverages a production-minded stack of
                  <span className="font-bold text-primary"> FastAPI</span>,
                  <span className="font-bold text-primary"> Next.js</span>, and
                  <span className="font-bold text-primary"> Celery</span>. Document ingestion and hybrid vector search are
                  currently active across all assigned matters.
                </p>
                <div className="flex flex-wrap gap-3 pt-4">
                  <div className="flex items-center gap-2 rounded-full bg-primary/5 px-3 py-1.5">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                    <span className="text-[11px] font-bold uppercase tracking-wider text-primary">Engine: Qdrant + ES</span>
                  </div>
                  <div className="flex items-center gap-2 rounded-full bg-primary/5 px-3 py-1.5">
                    <span className="material-symbols-outlined text-sm text-primary">security</span>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-primary">RBAC Hardened</span>
                  </div>
                </div>
              </div>
            </article>

            <article className="signature-gradient col-span-12 flex flex-col justify-between rounded-2xl border border-primary/20 p-10 text-white shadow-xl lg:col-span-5">
              <div className="flex items-start justify-between">
                <h3 className="font-headline text-xl font-bold">Live Firm Pulse</h3>
                <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/15 px-3 py-1 backdrop-blur-sm">
                  <span className="h-1.5 w-1.5 rounded-full bg-white" />
                  <span className="text-[10px] font-black uppercase tracking-widest italic">Operational</span>
                </div>
              </div>

              <div className="mt-8 grid grid-cols-2 gap-10">
                <div>
                  <p className="mb-2 text-[10px] font-black uppercase tracking-widest text-white/60">Aggregate Win Rate</p>
                  <div className="flex items-end gap-2">
                    <span className="font-headline text-5xl font-black tracking-tighter">94.2%</span>
                    <span className="mb-2 text-xs font-bold text-on-primary-container">+2.1%</span>
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-[10px] font-black uppercase tracking-widest text-white/60">Case Velocity</p>
                  <div className="flex items-end gap-2">
                    <span className="font-headline text-5xl font-black tracking-tighter">+12.4%</span>
                    <span className="material-symbols-outlined mb-2 text-on-primary-container">trending_up</span>
                  </div>
                </div>
              </div>

              <div className="mt-10 space-y-2">
                <div className="flex justify-between text-[10px] font-bold uppercase text-white/70">
                  <span>Ingestion Pipeline Throughput</span>
                  <span>89%</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/20">
                  <div className="h-full w-[89%] rounded-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.5)]" />
                </div>
              </div>
            </article>
          </div>

          <div className="grid grid-cols-12 gap-8">
            <div className="col-span-12 lg:col-span-4">
              <DocumentsPanel caseId={selectedCaseId} allowUpload autoRefresh />
            </div>
            <div className="col-span-12 lg:col-span-8">
              <CasesPanel allowCreate autoRefresh onSelectCase={setSelectedCaseId} />
            </div>
          </div>
        </div>
      </section>

      <button
        type="button"
        className="group signature-gradient fixed bottom-10 right-10 z-50 flex h-16 w-16 items-center justify-center rounded-full text-white shadow-2xl transition-all hover:scale-110 active:scale-95"
        aria-label="Open AI Operational Assistant"
      >
        <span className="material-symbols-outlined text-3xl">chat_bubble</span>
        <span className="pointer-events-none absolute right-full mr-4 whitespace-nowrap rounded-lg bg-on-surface px-3 py-1.5 text-[10px] font-bold text-white opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
          AI OPERATIONAL ASSISTANT
        </span>
      </button>
    </main>
  );
}
