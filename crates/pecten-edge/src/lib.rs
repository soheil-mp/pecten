//! `pecten-edge`: one process per camera or camera pair.
//!
//! It turns frames into detections, tracks and counts and publishes only those events
//! (ADR-0004). The thin slice (ROADMAP M1.3) reads thermal frames from an Arrow IPC stream,
//! detects warm blobs and tracks them; publishing `CloudEvents` over MQTT follows.

pub mod frames;
pub mod pipeline;
