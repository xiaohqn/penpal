import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { fetchPersonaCatalog, generateFromPlan, streamGenerations } from "./api";
import type { DraftCandidate, DraftState, PlannerOutput } from "./types";

export function usePersonas() {
  return useQuery({
    queryKey: ["personas"],
    queryFn: fetchPersonaCatalog,
  });
}

export function useGenerationWorkspace() {
  const [drafts, setDrafts] = useState<Record<string, DraftState>>({});
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (payload: { user_input: string; persona_names: string[]; compare_sources?: boolean; source_mode?: string }) => {
      setJobLoading(true);
      setJobError(null);
      setDrafts({});
      setSelectedPersona(null);
      let completedDrafts: DraftCandidate[] = [];

      await streamGenerations(payload, (eventName, data) => {
        if (eventName === "draft_started") {
          const draftId = data.draft_id ?? `${data.persona_name}::${data.source ?? "unknown"}`;
          setDrafts((current) => ({
            ...current,
            [draftId]: {
              draft_id: draftId,
              persona_name: data.persona_name,
              source: data.source ?? "",
              source_label: data.source_label ?? "",
              planner_output: {},
              raw_response: "",
              response: "",
              style_config: {},
              status: "streaming",
            },
          }));
          setSelectedPersona((current) => current ?? draftId);
        }

        if (eventName === "planner_ready") {
          const draftId = data.draft_id ?? `${data.persona_name}::${data.source ?? "unknown"}`;
          setDrafts((current) => ({
            ...current,
            [draftId]: {
              ...(current[draftId] ?? {
                draft_id: draftId,
                persona_name: data.persona_name,
                source: data.source ?? "",
                source_label: data.source_label ?? "",
                response: "",
                raw_response: "",
                style_config: {},
                status: "streaming",
              }),
              planner_output: data.planner_output,
            },
          }));
        }

        if (eventName === "draft_delta") {
          const draftId = data.draft_id ?? `${data.persona_name}::${data.source ?? "unknown"}`;
          setDrafts((current) => {
            const existing = current[draftId];
            if (!existing) {
              return current;
            }
            return {
              ...current,
              [draftId]: {
                ...existing,
                response: `${existing.response}${data.delta ?? ""}`,
              },
            };
          });
        }

        if (eventName === "draft_done") {
          const draftId = data.draft_id ?? `${data.persona_name}::${data.source ?? "unknown"}`;
          setDrafts((current) => {
            const existing = current[draftId];
            if (!existing) {
              return current;
            }
            return {
              ...current,
              [draftId]: {
                ...existing,
                response: data.response,
                status: "done",
              },
            };
          });
        }

        if (eventName === "error") {
          const draftId = data.draft_id ?? `${data.persona_name}::${data.source ?? "unknown"}`;
          setDrafts((current) => ({
            ...current,
            [draftId]: {
              ...(current[draftId] ?? {
                draft_id: draftId,
                persona_name: data.persona_name,
                source: data.source ?? "",
                source_label: data.source_label ?? "",
                response: "",
                raw_response: "",
                planner_output: {},
                style_config: {},
                status: "error",
              }),
              status: "error",
              error: data.message,
            },
          }));
        }

        if (eventName === "job_done") {
          completedDrafts = (data.drafts ?? []) as DraftCandidate[];
          setDrafts((current) => {
            const next = { ...current };
            for (const draft of completedDrafts) {
              next[draft.draft_id] = {
                ...draft,
                status: "done",
              };
            }
            return next;
          });
          setSelectedPersona((current) => current ?? completedDrafts[0]?.draft_id ?? null);
          setJobLoading(false);
        }
      });

      setJobLoading(false);
      return completedDrafts;
    },
    onError: (error) => {
      setJobLoading(false);
      setJobError(error instanceof Error ? error.message : "生成失败");
    },
  });

  const planMutation = useMutation({
    mutationFn: async (payload: {
      user_input: string;
      persona_name: string;
      planner_output: PlannerOutput;
      source_mode?: string;
    }) => {
      setJobLoading(true);
      setJobError(null);
      const draft = await generateFromPlan(payload);
      setDrafts((current) => ({
        ...current,
        [draft.draft_id]: {
          ...draft,
          raw_response: draft.raw_response ?? "",
          status: "done",
        },
      }));
      setSelectedPersona(draft.draft_id);
      setJobLoading(false);
      return draft;
    },
    onError: (error) => {
      setJobLoading(false);
      setJobError(error instanceof Error ? error.message : "按 Planner 重生成失败");
    },
  });

  const orderedDrafts = Object.values(drafts);
  const activeDraft =
    orderedDrafts.find((item) => item.draft_id === selectedPersona) ?? orderedDrafts[0] ?? null;

  const resetWorkspace = useCallback(() => {
    setDrafts({});
    setSelectedPersona(null);
    setJobLoading(false);
    setJobError(null);
  }, []);

  const hydrateWorkspace = useCallback(
    (payload: { drafts: DraftCandidate[]; selectedPersona?: string | null }) => {
      const nextDrafts = payload.drafts.reduce<Record<string, DraftState>>((accumulator, draft) => {
        accumulator[draft.draft_id] = {
          ...draft,
          raw_response: draft.raw_response ?? "",
          status: "done",
        };
        return accumulator;
      }, {});
      setDrafts(nextDrafts);
      setSelectedPersona(payload.selectedPersona ?? payload.drafts[0]?.draft_id ?? null);
      setJobLoading(false);
      setJobError(null);
    },
    [],
  );

  const updateDraftPlanner = useCallback((draftId: string, plannerOutput: PlannerOutput) => {
    setDrafts((current) => {
      const existing = current[draftId];
      if (!existing) {
        return current;
      }
      return {
        ...current,
        [draftId]: {
          ...existing,
          planner_output: plannerOutput,
        },
      };
    });
  }, []);

  return {
    drafts: orderedDrafts,
    activeDraft,
    selectedPersona,
    setSelectedPersona,
    jobLoading,
    jobError,
    startGeneration: mutation.mutateAsync,
    generateDraftFromPlan: planMutation.mutateAsync,
    updateDraftPlanner,
    resetWorkspace,
    hydrateWorkspace,
  };
}
