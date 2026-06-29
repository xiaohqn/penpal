import { CheckCircle2 } from "lucide-react";

import type { PersonaCatalogItem } from "../features/generation/types";

type Props = {
  personas: PersonaCatalogItem[];
  selected: string[];
  onToggle: (personaName: string) => void;
  displayName?: (personaName: string) => string;
};

export function PersonaSelector({ personas, selected, onToggle, displayName = (personaName) => personaName }: Props) {
  const persona = personas[0];
  if (!persona) {
    return null;
  }
  const active = selected.includes(persona.name);
  const personaLabel = displayName(persona.name);

  return (
    <section className="rounded-[22px] border border-line bg-white/82 p-4 shadow-card backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.18em] text-amber">暂定人格</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <h2 className="font-serif text-2xl text-ink">{personaLabel}</h2>
            <span className="inline-flex items-center gap-1 rounded-full bg-amber px-3 py-1 text-xs text-white">
              <CheckCircle2 size={14} />
              已启用
            </span>
          </div>
          <p className="mt-2 max-h-12 overflow-hidden text-sm leading-6 text-ink/66">{persona.blurb}</p>
        </div>
        {!active ? (
          <button
            type="button"
            onClick={() => onToggle(persona.name)}
            className="w-fit rounded-full border border-line bg-paper/75 px-4 py-2 text-sm text-ink transition hover:border-amber/60"
          >
            启用人格
          </button>
        ) : null}
      </div>
    </section>
  );
}
