# SENTINEL Hi-Fi frontend

Next.js, TypeScript and Tailwind CSS implementation of the Figma Hi-Fi page.

## Run locally

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

```sh
npm run typecheck
npm run build
```

## Screens

- `/`: Your Data Center / unicorn meadow
- `/facility`: interactive facility cutaway and room inspector
- `/overview`: facility metrics, trends and AI analysis
- `/incidents`: searchable and filterable incident history
- `/incidents/1042`: incident detail and recovery chart
- `/devices`: illustrative connectivity and service states

The facility map includes four illustrative pixel-art teammates walking along the
central corridor and exterior campus paths. Name labels follow the 3D camera;
Pause team freezes their movement. Reduced-motion preferences start the team
paused, and animation stops while the browser tab is hidden. Edit names, roles,
appearance colors and route offsets in `src/lib/team-members.ts` to represent
your team. Characters are illustrative and do not track real locations.

All readings, acknowledgments and incident records are illustrative fixtures. Authentication, FastAPI, Supabase and firmware remain unimplemented. Original Figma SVG assets are stored in `public/figma`. Charts reproduce the static design; they are not live sensor charts.

Design reference: https://www.figma.com/design/niKJ6kHKJcLuu2cwvtMNTi/UnicornWins?node-id=20-2
