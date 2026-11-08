import * as THREE from "three";
import { teamMembers } from "@/lib/team-members";

// The corridor is the clear east–west aisle in the Blender model. Campus
// waypoints follow its exterior paths. Coordinates are in exported GLB space.
const routes = {
  // The wall faces are at z = ±.855. Stay on the centerline so the
  // character's full width clears them, including when the camera rotates.
  corridor: [[-9, .35, 0], [9, .35, 0]],
  campus: [[-19, -.35, 10], [16, -.35, 10], [16, -.35, -10], [-19, -.35, -10]],
};

export function createTeamNpcs(models: THREE.Object3D) {
  const group = new THREE.Group();
  group.name = "Illustrative unicorn NPCs";
  const npcs = teamMembers.map(member => {
    const root = new THREE.Group();
    root.name = member.name;
    const prototype = models.getObjectByName(`Unicorn_${member.modelVariant}`);
    if (!prototype) throw new Error(`Missing unicorn model: ${member.modelVariant}`);
    const model = prototype.clone(true);
    model.position.set(0, 0, 0);
    const legs: THREE.Object3D[] = [];
    let tail: THREE.Object3D | undefined;
    model.traverse(part => {
      if (part.name.startsWith("Leg_") && !(part as THREE.Mesh).isMesh) legs.push(part);
      if (part.name.startsWith("Tail") && !(part as THREE.Mesh).isMesh) tail = part;
    });
    root.add(model);
    group.add(root);
    const points = routes[member.route].map(point => new THREE.Vector3(...point as [number, number, number]));
    const lengths = points.map((point, index) => point.distanceTo(points[(index + 1) % points.length]));
    const total = lengths.reduce((sum, length) => sum + length, 0);
    const anchor = new THREE.Vector3();
    return { member, root, legs, tail, points, lengths, total, anchor };
  });
  const update = (elapsed: number, walking: boolean) => {
    npcs.forEach(npc => {
      let distance = (elapsed * .85 + npc.member.offset * npc.total) % npc.total;
      let segment = 0;
      while (distance > npc.lengths[segment] && segment < npc.lengths.length - 1) distance -= npc.lengths[segment++];
      const start = npc.points[segment];
      const end = npc.points[(segment + 1) % npc.points.length];
      npc.root.position.lerpVectors(start, end, distance / npc.lengths[segment]);
      const heading = Math.atan2(end.x - start.x, end.z - start.z);
      npc.root.rotation.y = heading;
      const phase = elapsed * 7 + npc.member.offset * Math.PI * 2;
      npc.legs.forEach(leg => {
        const diagonal = leg.name.startsWith("Leg_Front_L") || leg.name.startsWith("Leg_Back_R");
        leg.rotation.x = walking ? Math.sin(phase + (diagonal ? 0 : Math.PI)) * .32 : 0;
      });
      if (npc.tail) npc.tail.rotation.z = walking ? Math.sin(phase * .5) * .12 : 0;
      npc.anchor.copy(npc.root.position).y += 2.05;
    });
  };
  update(0, false);
  return { group, npcs, update };
}
