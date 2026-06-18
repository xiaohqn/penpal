import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createUserLetter,
  fetchAssignedUserLetters,
  fetchUserLetters,
  submitCounselorReply,
  updateUserLetterStatus,
} from "./api";
import type { CreateUserLetterPayload } from "./types";

export function useUserLetters() {
  return useQuery({
    queryKey: ["user-letters"],
    queryFn: fetchUserLetters,
  });
}

export function useAssignedUserLetters() {
  return useQuery({
    queryKey: ["assigned-user-letters"],
    queryFn: fetchAssignedUserLetters,
  });
}

export function useCreateUserLetter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateUserLetterPayload) => createUserLetter(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["user-letters"] });
    },
  });
}

export function useUpdateUserLetterStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ letterId, status }: { letterId: number; status: string }) =>
      updateUserLetterStatus(letterId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["user-letters"] });
    },
  });
}

export function useSubmitCounselorReply() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ letterId, replyText }: { letterId: number; replyText: string }) =>
      submitCounselorReply(letterId, replyText),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["assigned-user-letters"] });
    },
  });
}
