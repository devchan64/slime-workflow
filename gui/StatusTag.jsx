import React from "react";

const tones = new Set(["running", "pending", "completed", "failed", "cancelled", "unknown"]);

export default function StatusTag({tone="unknown", children}) {
  return <span className="status-tag" data-tone={tones.has(tone) ? tone : "unknown"}>{children}</span>;
}
