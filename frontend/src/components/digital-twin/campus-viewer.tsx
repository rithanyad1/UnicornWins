"use client";

import { useEffect, useRef, useState } from "react";
import type { Object3D, Mesh, Material, Texture, Vector3 } from "three";
import mapLayout from "@/lib/facility-map-layout.json";
import { teamMembers } from "@/lib/team-members";

const labels = { A: "A · Heat", B: "B · Servers", C: "C · Network", D: "D · Water" };

function disposeModel(root: Object3D) {
  const materials = new Set<Material>();
  const textures = new Set<Texture>();
  root.traverse(object => {
    const mesh = object as Mesh;
    mesh.geometry?.dispose();
    if (mesh.material) (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).forEach(material => materials.add(material));
  });
  materials.forEach(material => {
    Object.values(material).forEach(value => { if (value && typeof value === "object" && "isTexture" in value) textures.add(value as Texture); });
    material.dispose();
  });
  textures.forEach(texture => texture.dispose());
}

export default function CampusViewer({ room, selectRoom, focusRequest = 0, emergencies = {} }: { room: string; selectRoom: (id: string) => void; focusRequest?: number; emergencies?: Record<string, string> }) {
  const host = useRef<HTMLDivElement>(null);
  const canvasHost = useRef<HTMLDivElement>(null);
  const markerRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const teammateRefs = useRef<Record<string, HTMLSpanElement | null>>({});
  const focusRoom = useRef<((id: string) => void) | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [expanded, setExpanded] = useState(false);


  useEffect(() => {
    if (loaded && focusRequest > 0) focusRoom.current?.(room);
  }, [room, focusRequest, loaded]);

  useEffect(() => {
    if (!expanded) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setExpanded(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [expanded]);

  useEffect(() => {
    let disposed = false;
    let teardown = () => {};
    const init = async () => {
      const [THREE, { OrbitControls }, { GLTFLoader }, { createTeamNpcs }] = await Promise.all([
        import("three"), import("three/addons/controls/OrbitControls.js"), import("three/addons/loaders/GLTFLoader.js"),
        import("@/components/digital-twin/team-npcs"),
      ]);
      const unicornModels = await new GLTFLoader().loadAsync("/models/unicorn-npcs.glb");
      if (disposed || !host.current || !canvasHost.current) { disposeModel(unicornModels.scene); return; }
      const container = host.current;
      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false, powerPreference: "low-power" });
      renderer.setPixelRatio(1);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.NoToneMapping;
      renderer.setClearColor(0xf4f7ea, 0);
      const canvas = renderer.domElement;
      canvas.tabIndex = 0;
      canvas.setAttribute("role", "img");
      canvas.setAttribute("aria-label", "Open data-center campus with illustrative voxel unicorn NPCs walking through the corridor and campus paths. Drag to rotate, Shift-drag or right-drag to pan, scroll to zoom. Double-tap or double-click the map to reset the view. Arrow keys rotate; plus and minus zoom; zero resets.");
      canvasHost.current.appendChild(canvas);
      const scene = new THREE.Scene();
      const camera = new THREE.OrthographicCamera(-29, 29, 20, -20, .1, 250);
      // Raise the framing slightly so the campus sits lower, preserving the viewing angle.
      const framingOffset = new THREE.Vector3(0, 2.5, 0);
      const home = new THREE.Vector3(36, 48, 46).add(framingOffset);
      const target = new THREE.Vector3(-1.5, .3, 0).add(framingOffset);
      camera.position.copy(home);
      const controls = new OrbitControls(camera, canvas);
      controls.target.copy(target);
      const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
      controls.enableDamping = !motionPreference.matches;
      let walking = !motionPreference.matches;
      controls.dampingFactor = .12;
      controls.minPolarAngle = .25;
      controls.maxPolarAngle = Math.PI / 2.25;
      controls.minZoom = .65;
      controls.maxZoom = 3.5;
      controls.screenSpacePanning = true;
      controls.zoomSpeed = .75;
      scene.add(new THREE.HemisphereLight(0xf4f7ea, 0x91b7a1, 2.1));
      const sunlight = new THREE.DirectionalLight(0xffffff, 2.2);
      sunlight.position.set(-16, 30, 18);
      scene.add(sunlight);
      let model: Object3D | null = null;
      let meadow: Mesh | null = null;
      let frame = 0;
      const team = createTeamNpcs(unicornModels.scene);
      let elapsed = 0;
      let lastTime = 0;
      const projected = new THREE.Vector3();
      let focusTransition: {
        started: number;
        fromPosition: Vector3;
        toPosition: Vector3;
        fromTarget: Vector3;
        toTarget: Vector3;
        fromZoom: number;
      } | null = null;
      const cancelFocus = () => { focusTransition = null; };
      const render = (time: number) => {
        frame = 0;
        if (disposed) return;
        const delta = lastTime ? Math.min((time - lastTime) / 1000, .05) : 0;
        lastTime = time;
        if (walking && model) elapsed += delta;
        controls.update();
        if (focusTransition) {
          const progress = motionPreference.matches ? 1 : Math.min((time - focusTransition.started) / 650, 1);
          const eased = progress * progress * (3 - 2 * progress);
          camera.position.lerpVectors(focusTransition.fromPosition, focusTransition.toPosition, eased);
          controls.target.lerpVectors(focusTransition.fromTarget, focusTransition.toTarget, eased);
          camera.zoom = THREE.MathUtils.lerp(focusTransition.fromZoom, 2.2, eased);
          camera.updateProjectionMatrix();
          camera.lookAt(controls.target);
          if (progress === 1) focusTransition = null;
        }
        team.update(elapsed, walking);
        // Keep the meadow beneath the camera target, including while panning.
        if (meadow) meadow.position.set(controls.target.x, -.449, controls.target.z);
        renderer.render(scene, camera);
        Object.entries(mapLayout).forEach(([id, anchor]) => {
          const button = markerRefs.current[id];
          if (!button || !model) return;
          const position = (anchor as typeof anchor & { position?: number[] }).position;
          if (!position) return;
          projected.set(position[0], position[1], position[2]).project(camera);
          button.style.left = `${(projected.x + 1) * 50}%`;
          button.style.top = `${(1 - projected.y) * 50}%`;
          button.style.visibility = projected.z < -1 || projected.z > 1 || Math.abs(projected.x) > 1.05 || Math.abs(projected.y) > 1.05 ? "hidden" : "visible";
        });
        team.npcs.forEach(npc => {
          const label = teammateRefs.current[npc.member.id];
          if (!label || !model) return;
          projected.copy(npc.anchor).project(camera);
          label.style.left = `${(projected.x + 1) * 50}%`;
          label.style.top = `${(1 - projected.y) * 50}%`;
          label.style.visibility = projected.z < -1 || projected.z > 1 || Math.abs(projected.x) > 1 || Math.abs(projected.y) > 1 ? "hidden" : "visible";
        });
        if ((walking && model) || focusTransition) requestRender();
      };
      const requestRender = () => { if (!frame && !disposed && !document.hidden) frame = requestAnimationFrame(render); };
      const resize = () => {
        const { width, height } = container.getBoundingClientRect();
        if (!width || !height) return;
        const aspect = width / height;
        const span = Math.max(58, 40 * aspect);
        camera.left = -span / 2;
        camera.right = span / 2;
        camera.top = span / aspect / 2;
        camera.bottom = -span / aspect / 2;
        camera.updateProjectionMatrix();
        // Small, crisp pixels retain the illustrated style without losing room details.
        renderer.setSize(Math.max(1, Math.round(width * .85)), Math.max(1, Math.round(height * .85)), false);
        requestRender();
      };
      focusRoom.current = (id: string) => {
        const anchor = mapLayout[id as keyof typeof mapLayout];
        if (!anchor) return;
        controls.update();
        const toTarget = new THREE.Vector3().fromArray(anchor.position);
        focusTransition = {
          started: performance.now(),
          fromPosition: camera.position.clone(),
          toPosition: camera.position.clone().add(toTarget.clone().sub(controls.target)),
          fromTarget: controls.target.clone(),
          toTarget,
          fromZoom: camera.zoom,
        };
        requestRender();
      };
      const zoom = (factor: number) => {
        cancelFocus();
        camera.zoom = THREE.MathUtils.clamp(camera.zoom * factor, .65, 3.5);
        camera.updateProjectionMatrix();
        requestRender();
      };
      const reset = () => {
        cancelFocus();
        // Clear any remaining orbit momentum before restoring the overview.
        controls.enableDamping = false;
        controls.update();
        camera.position.copy(home);
        controls.target.copy(target);
        camera.zoom = 1;
        camera.updateProjectionMatrix();
        controls.update();
        controls.enableDamping = !motionPreference.matches;
        requestRender();
      };
      let tapStart: { id: number; x: number; y: number; time: number } | null = null;
      let lastTap: { x: number; y: number; time: number; pointerType: string } | null = null;
      let suppressClickUntil = 0;
      const isMapTarget = (target: EventTarget | null) => target instanceof Element && !!target.closest("canvas, .map-room-marker");
      const cancelTap = () => { tapStart = null; lastTap = null; };
      const onPointerDown = (event: PointerEvent) => {
        if (!isMapTarget(event.target) || !event.isPrimary || event.button !== 0) { cancelTap(); return; }
        tapStart = { id: event.pointerId, x: event.clientX, y: event.clientY, time: performance.now() };
      };
      const onPointerMove = (event: PointerEvent) => {
        if (tapStart?.id === event.pointerId && Math.hypot(event.clientX - tapStart.x, event.clientY - tapStart.y) > 16) cancelTap();
      };
      const onPointerUp = (event: PointerEvent) => {
        const start = tapStart;
        tapStart = null;
        const now = performance.now();
        if (!start || start.id !== event.pointerId || now - start.time > 350 || Math.hypot(event.clientX - start.x, event.clientY - start.y) > 16) {
          lastTap = null;
          return;
        }
        if (lastTap && lastTap.pointerType === event.pointerType && now - lastTap.time < 480 && Math.hypot(event.clientX - lastTap.x, event.clientY - lastTap.y) < 40) {
          lastTap = null;
          suppressClickUntil = now + 400;
          reset();
        } else {
          lastTap = { x: event.clientX, y: event.clientY, time: now, pointerType: event.pointerType };
        }
      };
      const onMapClick = (event: MouseEvent) => {
        if (!isMapTarget(event.target)) return;
        if (performance.now() < suppressClickUntil || event.detail >= 2) {
          event.preventDefault();
          event.stopPropagation();
          cancelTap();
          reset();
        }
      };
      const onDoubleClick = (event: MouseEvent) => {
        if (!isMapTarget(event.target)) return;
        event.preventDefault();
        event.stopPropagation();
        cancelTap();
        reset();
      };
      const onMotionChange = () => {
        controls.enableDamping = !motionPreference.matches;
        walking = !motionPreference.matches;
        lastTime = 0;
        requestRender();
      };
      const onVisibility = () => {
        cancelAnimationFrame(frame);
        frame = 0;
        lastTime = 0;
        requestRender();
      };
      motionPreference.addEventListener("change", onMotionChange);
      document.addEventListener("visibilitychange", onVisibility);
      const onKey = (event: KeyboardEvent) => {
        if (["+", "=", "-", "0", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) event.preventDefault();
        if (event.key === "+" || event.key === "=") zoom(1.2);
        if (event.key === "-") zoom(1 / 1.2);
        if (event.key === "0") reset();
        if (event.key.startsWith("Arrow")) {
          cancelFocus();
          const offset = camera.position.clone().sub(controls.target);
          const spherical = new THREE.Spherical().setFromVector3(offset);
          if (event.key === "ArrowLeft") spherical.theta -= .15;
          if (event.key === "ArrowRight") spherical.theta += .15;
          if (event.key === "ArrowUp") spherical.phi -= .1;
          if (event.key === "ArrowDown") spherical.phi += .1;
          spherical.phi = THREE.MathUtils.clamp(spherical.phi, controls.minPolarAngle, controls.maxPolarAngle);
          camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));
          controls.update();
          requestRender();
        }
      };
      const onContextLost = (event: Event) => {
        event.preventDefault();
        walking = false;
        cancelAnimationFrame(frame);
        frame = 0;
        if (!disposed) setFailed(true);
      };
      canvas.addEventListener("keydown", onKey);
      container.addEventListener("pointerdown", onPointerDown, true);
      container.addEventListener("pointermove", onPointerMove, true);
      container.addEventListener("pointerup", onPointerUp, true);
      container.addEventListener("pointercancel", cancelTap, true);
      container.addEventListener("click", onMapClick, true);
      container.addEventListener("dblclick", onDoubleClick, true);
      canvas.addEventListener("webglcontextlost", onContextLost);
      controls.addEventListener("change", requestRender);
      controls.addEventListener("start", cancelFocus);
      const observer = new ResizeObserver(resize);
      observer.observe(container);
      controls.update();
      resize();
      teardown = () => {
        observer.disconnect();
        cancelAnimationFrame(frame);
        focusRoom.current = null;
        controls.removeEventListener("change", requestRender);
        controls.removeEventListener("start", cancelFocus);
        controls.dispose();
        motionPreference.removeEventListener("change", onMotionChange);
        document.removeEventListener("visibilitychange", onVisibility);
        canvas.removeEventListener("keydown", onKey);
        container.removeEventListener("pointerdown", onPointerDown, true);
        container.removeEventListener("pointermove", onPointerMove, true);
        container.removeEventListener("pointerup", onPointerUp, true);
        container.removeEventListener("pointercancel", cancelTap, true);
        container.removeEventListener("click", onMapClick, true);
        container.removeEventListener("dblclick", onDoubleClick, true);
        canvas.removeEventListener("webglcontextlost", onContextLost);
        if (model) disposeModel(model);
        if (meadow) disposeModel(meadow);
        disposeModel(team.group);
        renderer.dispose();
        renderer.forceContextLoss();
        canvas.remove();
      };
      new GLTFLoader().load("/models/facility-campus.glb", gltf => {
        if (disposed) { disposeModel(gltf.scene); return; }
        model = gltf.scene;
        scene.add(model);
        scene.add(team.group);
        model.traverse(object => {
          const mesh = object as Mesh;
          if (!mesh.isMesh) return;
          const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          const grass = materials.find(material => material.name === "Campus meadow green");
          if (!grass || meadow) return;
          meadow = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000), grass.clone());
          meadow.rotation.x = -Math.PI / 2;
          scene.add(meadow);
        });
        setLoaded(true);
        requestRender();
      }, undefined, () => { if (!disposed) setFailed(true); });
    };
    init().catch(() => { if (!disposed) { teardown(); setFailed(true); } });
    return () => { disposed = true; teardown(); };
  }, []);

  const live = loaded && !failed;
  return <div ref={host} className={`campus-viewer ${expanded ? "is-expanded" : ""}`}>
    <div ref={canvasHost} className="campus-canvas" style={{ visibility: live ? "visible" : "hidden" }} />
    {!live && <div className="campus-fallback"><img src="/models/facility-map-pixel.png" width="480" height="336" alt="Open-roof data center surrounded by green land, trees and pathways" /></div>}
    <div className={`campus-markers ${live ? "" : "fallback-markers"}`}>
      {Object.entries(mapLayout).map(([id, position]) => <button key={id} ref={node => { markerRefs.current[id] = node; }}
        className={`map-marker map-room-marker ${room === id ? "selected" : ""}`}
        style={!live ? { left: `${position.left}%`, top: `${position.top}%` } : undefined}
        aria-pressed={room === id}
        aria-label={emergencies[id] ? `${labels[id as keyof typeof labels]} — Emergency: ${emergencies[id]}` : undefined}
        title={emergencies[id] ? `Emergency · ${emergencies[id]}` : undefined}
        onClick={() => selectRoom(id)}>
        {emergencies[id] && <span className="emergency-pointer" aria-hidden="true"><svg width="32" height="42" viewBox="0 0 32 42" fill="none"><path d="M16 40S2 25 2 16a14 14 0 0 1 28 0c0 9-14 24-14 24Z" fill="#e44f65" stroke="white" strokeWidth="2" strokeLinejoin="round"/><path d="M16 9v9" stroke="white" strokeWidth="3" strokeLinecap="round"/><circle cx="16" cy="24" r="1.8" fill="white"/></svg></span>}
        {labels[id as keyof typeof labels]}</button>)}
    </div>
    {live && <div className="campus-teammates" aria-label="Illustrative unicorn NPCs">
      {teamMembers.map(member => <span key={member.id} ref={node => { teammateRefs.current[member.id] = node; }} className="campus-teammate" title={`${member.role} (illustrative)`}><i style={{ background: member.color }} />{member.role}</span>)}
    </div>}
    {!live && <div className="campus-load-status" role="status">{failed ? "3D unavailable · map preview" : "Loading 3D campus…"}</div>}
    <div className="campus-view-label">OPEN-ROOF VIEW <span>DC-01</span></div>
    <button className="campus-expand" onClick={() => setExpanded(!expanded)} aria-label={expanded ? "Close expanded map" : "Expand map"}>{expanded ? "↙" : "⤢"}</button>
  </div>;
}
