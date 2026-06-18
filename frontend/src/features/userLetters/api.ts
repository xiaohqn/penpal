import { getStoredUserId } from "../../app/auth";
import { request } from "../../lib/request";
import type { CreateUserLetterPayload, UserLetter, UserLetterListResponse } from "./types";

const userHeaders = () => ({
  "X-User-Id": getStoredUserId(),
});

export function fetchUserLetters() {
  return request<UserLetterListResponse>("/user-letters", {
    headers: userHeaders(),
  });
}

export function fetchAssignedUserLetters() {
  return request<UserLetterListResponse>("/user-letters/assigned/mine");
}

export function createUserLetter(payload: CreateUserLetterPayload) {
  return request<UserLetter>("/user-letters", {
    method: "POST",
    headers: userHeaders(),
    body: JSON.stringify(payload),
  });
}

export function updateUserLetterStatus(letterId: number, status: string) {
  return request<UserLetter>(`/user-letters/${letterId}/status`, {
    method: "PATCH",
    headers: userHeaders(),
    body: JSON.stringify({ status }),
  });
}

export function submitCounselorReply(letterId: number, replyText: string) {
  return request<UserLetter>(`/user-letters/assigned/${letterId}/reply`, {
    method: "POST",
    body: JSON.stringify({ reply_text: replyText }),
  });
}
