export type Incident = {
  id: string;
  type: string;
  severity: "Warning" | "Critical";
  time: string;
  status: "Open" | "Responding" | "Resolved" | "Unresolved";
  description: string;
};
