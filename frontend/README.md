# UN1C0RN^2 Hi-Fi frontend

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

The `/overview` dashboard polls its own `/api/hardware` route every three
seconds. That server route fetches the FastAPI Pico endpoint, avoiding browser
CORS and localhost issues. Local development defaults to `http://127.0.0.1:8000`;
production defaults to `https://un1c0rn-2.onrender.com`. Set server variable
`API_BASE_URL` in `frontend/.env.local` or the frontend host environment to
override it. Restart/redeploy after changing configuration. The former
`NEXT_PUBLIC_API_BASE_URL` is accepted as a fallback. Connection failures are
shown on the dashboard; disconnected hardware continues to show null values.

Deploy this as a Next.js server app, not a static export. See
[deployment setup](../docs/deployment.md) for Render settings and verification.

Dashboard metrics start as `null` and remain null until a fresh hardware report
arrives. Stale reports (15 seconds by default, configured by the backend's
`DEVICE_TIMEOUT_SECONDS`), a disconnected Pico, and backend errors clear the
current values and chart. Null sensor measurements stay null even while connected.
Temperature is shown in Fahrenheit and vibration in g, matching the Pico. Charts
and recent activity use actual hardware reports; they do not use simulated data.

Incident pages and the facility map still contain illustrative fixtures. Original
Figma SVG assets are stored in `public/figma`.

Design reference: https://www.figma.com/design/niKJ6kHKJcLuu2cwvtMNTi/UnicornWins?node-id=20-2
