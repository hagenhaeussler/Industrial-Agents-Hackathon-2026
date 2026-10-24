# Human steps to finish the physical demo and submission

Use the factory fallback now. It is real kit data and a working on-screen demo;
its coordinates do not describe the venue. Do not place its position codes in
the venue and call them calibrated.

## 1. Choose a small real demo area

Choose 5–8 real objects and a short walk. Prefer two floors connected by both a
lift and stairs so closing the lift has a real alternative for walking. A
single-floor area with two door routes also works. Record the building/area name
and the people who measured it. Keep the demo within areas the team can access.

## 2. Make one dimensioned sketch per floor

Use a tape measure or laser. All dimensions must be in metres.

- Mark a common origin, for example the same structural corner on each floor.
  Draw +X and +Y arrows. Align floors to the same building frame; do not give each
  floor an unrelated rotation or origin.
- Draw room outlines and write each room's name, number and use. Add the lengths
  needed to reconstruct every polygon, including corridor widths and offsets.
- Mark doors on their walls. Record which two spaces they connect, clear opening
  width, and whether they are step-free. Identify the entrance from outside.
- Mark each lift/stair landing and the room it opens into. Record floor
  elevations relative to the ground floor, plus lift/stair names and accessibility.
- Mark the real location and name of each demo object. If an exact point is
  uncertain, identify the correct room and label the uncertainty.

Save the sketches and a note of measurement accuracy under `demo/hero/input/`.
A legible dimensioned PDF/image plus the tables below is sufficient; you do not
need to hand-author `building.json`. Do not supply an unscaled picture alone.

Useful CSV column sets:

```text
floors.csv: floor,level,elevation_m,origin_description,axis_description
doors.csv: door,floor,space_a,space_b,x_m,y_m,width_m,step_free
connectors.csv: connector,kind,floor,space,x_m,y_m,step_free
objects.csv: name,type,floor,space,x_m,y_m,accuracy_note
```

Leave unknown measurements blank and describe what is missing. Never fill gaps
with plausible numbers. Tell the builder where you saved the files. The builder
will construct and validate the venue model, check routes and the closure
scenario, and return any specific missing dimensions.

## 3. Calibrate and print real position markers

Do this **after** the measured model validates. Choose a standing point at the
start, each important turn, and both sides of the lift/stairs. Record the floor,
room, X/Y standing point and the direction a person faces toward the printed code.
Heading uses the contract's building XY frame: 0° along +X, 90° along +Y.

Ask the builder to generate matching marker records and a print sheet for that
building. Print codes at least 12 cm wide. Put a footprint and facing arrow at
the measured standing point. Scan each code on a phone and check that the app
shows the correct building, floor and room before walking. A changed location
needs an updated marker record. No marker is proof of continuous phone location.

## 4. Run the real-phone acceptance checks

Bring an Android phone with Chrome/ARCore and an iPhone with Safari. Open the
[preview](https://hagen-core-test-testing.up.railway.app/desk?demo=hero) on the laptop.
Until the venue model is ready, test the factory journey on screen only.

On each phone, record its model, OS/browser version, the `/health` commit, and:

1. Plan three parts on the laptop; scan **Send to phone**. Check the same stops
   appear, confirm the start, and measure time to the tour screen.
2. Collect one stop; reload and confirm progress is retained. If there is a final
   destination, confirm it does not complete before explicit arrival.
3. Have an authorized teammate preview/confirm a lift closure. Time the route
   update in three trials. Check collected stops survive. Undo the closure.
4. Repeat with wheelchair travel: show the honest no-step-free-route state and
   verify stairs are used only after explicit agreement.
5. Deny mic/camera permissions and complete the journey with Map/Directions.
   Disconnect the network for 10 seconds, reconnect, and check the latest state.
6. Try voice in a quiet area: an exact lookup, an ambiguous lookup, one multi-stop
   plan, **next**, and an admin preview/confirm/undo. Verify map changes match the
   spoken tools. Never speak a key or admin code to the agent.

Voice agents currently allow two 60-second conversations daily each. Coordinate
the test window with the service owner before the ten-utterance, three-model A/B
test so limits and the remaining shared budget are set deliberately. Save timed
results and failures, not just a video of a successful token request.

Camera/AR is a separate optional test. Start only from the correctly registered
marker's standing point and facing direction. Check the first waypoint, a turn,
tracking loss and returning to the map. Measure route alignment over 10 metres
on Android. On iPhone the camera arrow indicates direction; it does not track
walking position. Cut AR from the pitch if alignment or permissions are unreliable.

## 5. Obtain the organizer's actual Sunday inputs

Save the unseen building and questions in a **new** folder outside read-only
`data/`, preserving original files. Include any equipment CSV, format example and
the organizer message/link stating the expected output, allowed runtime and
deadline. Ask whether answers are JSON or CSV and how unreachable routes are
represented. Tell the builder the folder path.

The builder will run the documented `bench.run_benchmark` command, validate IDs,
schema and answer formatting, load the building through authenticated JSON upload,
and record the exact release SHA. Dev rehearsals cannot certify this unseen run.

## 6. Rehearse, record and submit

Follow `demo/SCRIPT.md`: rehearse the three-minute pitch, then record the required
one-minute demo and one-minute technical explanation. Use phone mirroring if
available; label simulated movement and omit unverified AR or venue claims.
Run the demo/reset rehearsal twice in an isolated local environment, not by
resetting coworkers' shared preview state.

The account holder uploads the videos, architecture notes, repository link and
validated answer files on Hack & More. Verify the remote files and final Git SHA
before the organizer's deadline. Give the builder the submission requirements and
file locations in advance; a prepared script or CSV does not mean it was uploaded.
