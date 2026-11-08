type TeamMember = {
  id: string;
  name: string;
  role: string;
  color: string;
  modelVariant: number;
  route: "corridor" | "campus";
  offset: number;
};

// Variants match the four Blender unicorn models. Offsets spread the NPCs
// along their existing corridor and campus routes (0–1).
export const teamMembers: TeamMember[] = [
  { id: "team-1", name: "Unicorn 1", role: "Operations Lead", color: "#e692c2", modelVariant: 0, route: "corridor", offset: 0 },
  { id: "team-2", name: "Unicorn 2", role: "Infrastructure Engineer", color: "#a58be0", modelVariant: 1, route: "corridor", offset: .5 },
  { id: "team-3", name: "Unicorn 3", role: "Network Engineer", color: "#75cdb0", modelVariant: 2, route: "campus", offset: .15 },
  { id: "team-4", name: "Unicorn 4", role: "Hardware Technician", color: "#edaaa0", modelVariant: 3, route: "campus", offset: .65 },
];
