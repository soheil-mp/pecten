# pecten-sim

Physics-based sensor twin: renders thermal, visible-light, stereo and drone imagery with ground truth.

Part of [Pecten](https://github.com/soheil-mp/pecten); see the repository README and ROADMAP.md.

## Minimal thermal scenario (thin slice)

`pecten_sim.thermal` simulates a Lepton-class radiometric core (160 × 120 pixels, 8.7 Hz,
50 mK NETD) looking at a uniform sky while one warm disc crosses the view on a straight line.
Pixels hold temperatures in kelvin; the disc's sub-pixel coverage is computed by supersampling.

```sh
uv run pecten-sim thermal --seed 7 --duration-s 60 --target 127.0.0.1:7600 --truth truth.jsonl
uv run pecten-sim thermal --seed 7 --duration-s 5 --speed 0 --out frames.arrows --truth truth.jsonl
```

Frames travel as an Arrow IPC stream, one record batch per frame (`frame_id`, `timestamp`,
`temp_k` as a fixed-size list in row-major order; image size, frame rate and NETD in the schema
metadata). Ground truth (`pecten_sim.truth`) goes to a separate JSON Lines file and never into
the frame stream.
