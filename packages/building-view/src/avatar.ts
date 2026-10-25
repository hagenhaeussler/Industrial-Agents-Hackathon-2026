/** Shared bot silhouette and eye color for profile pictures and building markers. */
export const BOT_OUTLINE = {
  start: [12, 12],
  curves: [
    [20, 2, 43, 3, 52, 15],
    [62, 26, 61, 44, 50, 53],
    [39, 63, 15, 59, 8, 47],
    [1, 34, 3, 22, 12, 12],
  ],
} as const;
export const BOT_BODY_PATH = `M${BOT_OUTLINE.start.join(" ")} ${BOT_OUTLINE.curves.map((curve) => `C${curve.join(" ")}`).join(" ")} Z`;
export const BOT_EYE_COLOR = "#20291e";
