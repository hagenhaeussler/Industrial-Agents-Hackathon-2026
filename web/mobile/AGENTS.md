# Building guide prototype

- Use React, strict TypeScript, Vite, pnpm and Vitest.
- Keep the live camera full screen. Put white floating controls with black text above it.
- Use Manrope. Keep the route at the top, the floor minimap at the upper right and the agent at the bottom.
- Use Blobatar `alain00` with `animate="always"`. Do not pin appearance axes. Respect reduced-motion preferences.
- Keep camera lifecycle, demo navigation and agent interactions in separate modules.
- Label demo data as a demo. Do not claim a feature works until it is connected. Route, position and chat are demo data until the backend and agent are connected.
- Do not record, store or upload camera frames. Exception, planned for later: in AR mode the phone may send frames to our own localization service (hloc, MegaLoc). The service does not store them.
- Check the production build, camera failure states, route interactions, keyboard access and the mobile layout.
