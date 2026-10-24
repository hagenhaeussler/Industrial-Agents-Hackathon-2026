# Building guide prototype

- Use React, strict TypeScript, Vite and Bun.
- Keep the live camera full screen. Put white floating controls with black text above it.
- Use Manrope. Keep the route at the top, the floor minimap at the upper right and the agent at the bottom.
- Use Blobatar `alain00` with `animate="always"`. Do not pin appearance axes. Respect reduced-motion preferences.
- Keep camera lifecycle, demo navigation and agent interactions in separate modules.
- Label route and location data as a demo. Do not claim real localization or a connected language model.
- Do not record, store or upload camera frames.
- Check the production build, camera failure states, route interactions, keyboard access and the mobile layout.
