import type { GraphNodeType } from "../types/api";

export const NODE_TYPE_LABEL: Record<GraphNodeType, string> = {
  central: "Core Concept",
  prerequisite: "Prerequisite",
  related: "Related Concept",
  knowledge_gap: "Possible Knowledge Gap",
  supporting: "Supporting Concept",
};

export const NODE_TYPE_COLOR_VAR: Record<GraphNodeType, string> = {
  central: "var(--color-central)",
  prerequisite: "var(--color-prerequisite)",
  related: "var(--color-related)",
  knowledge_gap: "var(--color-gap)",
  supporting: "var(--color-supporting)",
};

export const CONFIDENCE_COLOR: Record<string, string> = {
  High: "#dc2626",
  Medium: "#d97706",
  Low: "#6b7280",
};
