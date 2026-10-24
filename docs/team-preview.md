# Team preview and iteration

The shared HTTPS test app is [Talk to Your Building](https://hagen-core-test-testing.up.railway.app/).
For the prepared factory scenario, [open the desk](https://hagen-core-test-testing.up.railway.app/desk?demo=hero).
No account is needed to browse, plan a tour, or open its phone link.

## Home, teams and uploads

Open the preview root, click the orb, then choose your team. Its building picker slides in beside the team list. Select a building to open its desk; the desk's building icon returns to that team's list. Teams are organizational groups for this shared preview, not separate authorization boundaries.

Choose **Create a new building** for two upload boxes: an equipment CSV and a structured JSON floor plan. Both files are required. The private access code is requested when needed; browsing and route planning remain open. Upload validation reports mismatched rooms or coordinates before creation. A successful import persists in the selected team and offers **Open building**. See [building-import.md](building-import.md) for formats and limits. PDF/image plans are deferred until a geometry and scale review can establish measured routes.

The desktop keeps parts, conversation, position and mobility on the left. The selected isometric floor is enlarged in the map, with smaller floor controls at the upper right. The extra order/end controls, repeated floor labels and floating equipment card are removed. Phone guidance and explicit final arrival for existing end-destination tours retain their behavior.

## Try the journey

1. Open the prepared desk scenario. It selects the 3D printer, tool cabinet and UPS on two floors. Confirm your starting room and travel profile.
2. Choose **Plan collection tour**. Inspect the route, collection order, distance and calculation explanation.
3. Choose **Send to phone** and scan its QR code, or copy the link into another browser. Confirm the starting room on the phone. The phone uses this confirmation, position markers and manual progress; it does not automatically know your indoor location.
4. Follow the map/directions and mark each part collected. Reload once to check that progress survives. A selected final destination requires its own explicit arrival after the collection stops.
5. To try a building change, an authorized teammate opens [Admin](https://hagen-core-test-testing.up.railway.app/admin?demo=hero), enters the private admin code, previews a closure, and confirms it. An active phone tour should replan. Undo the test change afterwards. A wheelchair tour must stay blocked when no step-free alternative exists; stairs require an explicit profile change.

Admin codes and provider credentials are shared through the team's private channel or environment manager. Never put them in a URL, issue, commit, screenshot or this document. The admin code is stored only in the browser tab's session storage. Ask the service owner for access; ordinary coworker previews need no admin code.

## Chat, voice and camera

Text chat uses real Anthropic calls when its shared process budget has funds. Buttons, search and deterministic routing also work without a language model. The written smoke-test budget is **$5 total**, shared across all prior and current tests. A redeploy does not authorize another full allocation. When the app reports that chat is unavailable, use search and the tour controls and ask the service owner to reconcile the budget.

The Navigator allows 10 calls/day, up to three minutes per call, with one concurrent call. Admin retains two calls/day and a 60-second limit. Both use authenticated tokens. Click the small orb to talk; the inline conversation shows real replies, listening/speaking, mute, End and Retry. While connected, typing continues the same ElevenLabs conversation. The Navigator can select parts, focus floors and plan a visible tour. A real provider test verified generated speech and these tool actions against Railway using typed input; physical microphone/ASR and device tests remain for a person to perform. Mic permission belongs to the person using the preview.

Camera mode is optional. Camera denial, missing marker registration, unsupported AR or unavailable motion permissions must leave map/directions usable. Never treat an arrow or an untested AR overlay as proof of real indoor localization. No camera frames are uploaded or recorded.

## Iterate together

This is one shared persistent test building state. A confirmed admin edit affects other teammates' tours. Undo your test closures and moves; use a separately uploaded building for independent edit experiments. Demo reset is disabled on this public preview to avoid erasing someone else's work.

Develop on your assigned builder branch/worktree. Fetch `origin`, merge current `origin/main`, run `scripts/check.sh`, and push normally. Preserve the C9 state identity, authenticated admin sessions, explicit final arrival, strict provider schemas and stale-response guards. Never force-push or reset another builder's checkout.

The Railway test service is deliberately pinned to a verified commit. A GitHub push does not silently deploy it. After a green integration merge, the release owner reconnects the service to that exact main SHA with Railway MCP/CLI, waits for deployment success, checks `/health` for the same SHA, then runs the smoke checks. Record the SHA, deployment ID, outcomes and remaining limits in the release PR. This gives everyone a stable preview between integrations.

See [live-provider-setup.md](live-provider-setup.md) for server-only variables and the one-time budget ledger, and [project-readiness.md](project-readiness.md) for the remaining release gates.
