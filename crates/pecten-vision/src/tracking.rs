//! Nearest-neighbour tracking in image coordinates for the thin slice (ROADMAP M1.3).
//!
//! Per frame:
//!
//! 1. Every live track predicts its position at the frame time from its velocity.
//! 2. Track-measurement pairs within `gate_px` are assigned greedily, closest first; ties go to
//!    the lower track index, then the lower measurement index.
//! 3. A track's position is its latest measurement; its velocity is the least-squares slope of
//!    its last `velocity_window` positions.
//! 4. Unassigned measurements start tentative tracks, confirmed after `confirm_hits` hits. A
//!    confirmed track without a measurement coasts; after `max_misses` consecutive misses it is
//!    lost and reported one last time. Tentative tracks that miss are dropped silently.
//!
//! Track identifiers count up from 1 per tracker, so identical input gives identical output.
//! Kalman filtering and global assignment replace this in M6.

use std::collections::VecDeque;

/// A measured target position in one frame.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Measurement {
    /// Column in pixels.
    pub x_px: f64,
    /// Row in pixels.
    pub y_px: f64,
}

/// Parameters of the tracker.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TrackerConfig {
    /// Largest distance between a prediction and a measurement that may be associated.
    pub gate_px: f64,
    /// Hits after which a track is confirmed.
    pub confirm_hits: u32,
    /// Consecutive misses after which a confirmed track is lost.
    pub max_misses: u32,
    /// Positions used for the velocity estimate (at least 2).
    pub velocity_window: usize,
}

impl Default for TrackerConfig {
    fn default() -> Self {
        Self {
            gate_px: 8.0,
            confirm_hits: 3,
            max_misses: 5,
            velocity_window: 8,
        }
    }
}

/// Lifecycle state of a track.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TrackStatus {
    /// Seen, but not yet confirmed.
    Tentative,
    /// Confirmed and associated with a measurement in this frame.
    Confirmed,
    /// Confirmed, predicted forward without a measurement.
    Coasting,
    /// Ended; no further updates follow.
    Lost,
}

/// One state of one track, emitted per frame.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TrackUpdate {
    /// Identifier, unique per tracker.
    pub track_id: u64,
    /// Lifecycle state.
    pub status: TrackStatus,
    /// Frame time in seconds.
    pub time_s: f64,
    /// Estimated column.
    pub x_px: f64,
    /// Estimated row.
    pub y_px: f64,
    /// Estimated horizontal velocity, pixels per second.
    pub vx_px_s: f64,
    /// Estimated vertical velocity, pixels per second.
    pub vy_px_s: f64,
    /// Measurements associated with the track so far.
    pub hits: u32,
}

#[derive(Debug, Clone)]
struct Track {
    id: u64,
    history: VecDeque<(f64, f64, f64)>,
    velocity: (f64, f64),
    hits: u32,
    misses: u32,
    confirmed: bool,
}

impl Track {
    fn last(&self) -> (f64, f64, f64) {
        *self.history.back().unwrap_or(&(0.0, 0.0, 0.0))
    }

    fn predict(&self, time_s: f64) -> (f64, f64) {
        let (t, x, y) = self.last();
        let dt = time_s - t;
        (x + self.velocity.0 * dt, y + self.velocity.1 * dt)
    }

    fn update(&mut self, time_s: f64, m: Measurement, config: &TrackerConfig) {
        if self.history.len() == config.velocity_window.max(2) {
            self.history.pop_front();
        }
        self.history.push_back((time_s, m.x_px, m.y_px));
        self.hits += 1;
        self.misses = 0;
        self.confirmed |= self.hits >= config.confirm_hits;
        self.velocity = least_squares_velocity(&self.history);
    }

    fn state(&self, time_s: f64, status: TrackStatus) -> TrackUpdate {
        let (x, y) = match status {
            TrackStatus::Coasting | TrackStatus::Lost => self.predict(time_s),
            TrackStatus::Tentative | TrackStatus::Confirmed => {
                let (_, x, y) = self.last();
                (x, y)
            }
        };
        TrackUpdate {
            track_id: self.id,
            status,
            time_s,
            x_px: x,
            y_px: y,
            vx_px_s: self.velocity.0,
            vy_px_s: self.velocity.1,
            hits: self.hits,
        }
    }
}

#[expect(
    clippy::cast_precision_loss,
    reason = "a window holds a handful of points"
)]
fn least_squares_velocity(points: &VecDeque<(f64, f64, f64)>) -> (f64, f64) {
    let n = points.len() as f64;
    if points.len() < 2 {
        return (0.0, 0.0);
    }
    let mean_t = points.iter().map(|p| p.0).sum::<f64>() / n;
    let mean_x = points.iter().map(|p| p.1).sum::<f64>() / n;
    let mean_y = points.iter().map(|p| p.2).sum::<f64>() / n;
    let var_t: f64 = points.iter().map(|p| (p.0 - mean_t).powi(2)).sum();
    if var_t == 0.0 {
        return (0.0, 0.0);
    }
    let cov_x: f64 = points.iter().map(|p| (p.0 - mean_t) * (p.1 - mean_x)).sum();
    let cov_y: f64 = points.iter().map(|p| (p.0 - mean_t) * (p.2 - mean_y)).sum();
    (cov_x / var_t, cov_y / var_t)
}

/// A greedy nearest-neighbour multi-target tracker.
#[derive(Debug, Clone)]
pub struct NearestNeighbourTracker {
    config: TrackerConfig,
    tracks: Vec<Track>,
    next_id: u64,
}

impl NearestNeighbourTracker {
    /// A tracker with the given parameters and no tracks.
    #[must_use]
    pub const fn new(config: TrackerConfig) -> Self {
        Self {
            config,
            tracks: Vec::new(),
            next_id: 1,
        }
    }

    /// Number of tracks that are not lost.
    #[must_use]
    pub fn live_tracks(&self) -> usize {
        self.tracks.len()
    }

    /// Process the measurements of one frame; returns one update per reported track, in
    /// track order, followed by the tracks started in this frame.
    pub fn step(&mut self, time_s: f64, measurements: &[Measurement]) -> Vec<TrackUpdate> {
        let cfg = self.config;
        let mut pairs: Vec<(f64, usize, usize)> = Vec::new();
        for (ti, track) in self.tracks.iter().enumerate() {
            let (px, py) = track.predict(time_s);
            for (mi, m) in measurements.iter().enumerate() {
                let distance = (m.x_px - px).hypot(m.y_px - py);
                if distance <= cfg.gate_px {
                    pairs.push((distance, ti, mi));
                }
            }
        }
        pairs.sort_by(|a, b| a.0.total_cmp(&b.0).then(a.1.cmp(&b.1)).then(a.2.cmp(&b.2)));
        let mut track_of_measurement = vec![None; measurements.len()];
        let mut measurement_of_track = vec![None; self.tracks.len()];
        for (_, ti, mi) in pairs {
            if measurement_of_track[ti].is_none() && track_of_measurement[mi].is_none() {
                measurement_of_track[ti] = Some(mi);
                track_of_measurement[mi] = Some(ti);
            }
        }

        let mut updates = Vec::new();
        let mut survivors = Vec::with_capacity(self.tracks.len());
        for (ti, mut track) in std::mem::take(&mut self.tracks).into_iter().enumerate() {
            if let Some(mi) = measurement_of_track[ti] {
                track.update(time_s, measurements[mi], &cfg);
                let status = if track.confirmed {
                    TrackStatus::Confirmed
                } else {
                    TrackStatus::Tentative
                };
                updates.push(track.state(time_s, status));
                survivors.push(track);
                continue;
            }
            track.misses += 1;
            if !track.confirmed {
                continue;
            }
            if track.misses >= cfg.max_misses {
                updates.push(track.state(time_s, TrackStatus::Lost));
            } else {
                updates.push(track.state(time_s, TrackStatus::Coasting));
                survivors.push(track);
            }
        }
        for (mi, m) in measurements.iter().enumerate() {
            if track_of_measurement[mi].is_none() {
                let mut track = Track {
                    id: self.next_id,
                    history: VecDeque::with_capacity(cfg.velocity_window.max(2)),
                    velocity: (0.0, 0.0),
                    hits: 0,
                    misses: 0,
                    confirmed: false,
                };
                self.next_id += 1;
                track.update(time_s, *m, &cfg);
                let status = if track.confirmed {
                    TrackStatus::Confirmed
                } else {
                    TrackStatus::Tentative
                };
                updates.push(track.state(time_s, status));
                survivors.push(track);
            }
        }
        self.tracks = survivors;
        updates
    }

    /// End every confirmed live track, for example at the end of a stream.
    pub fn finish(&mut self, time_s: f64) -> Vec<TrackUpdate> {
        std::mem::take(&mut self.tracks)
            .into_iter()
            .filter(|t| t.confirmed)
            .map(|t| t.state(time_s, TrackStatus::Lost))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::{Measurement, NearestNeighbourTracker, TrackStatus, TrackUpdate, TrackerConfig};

    const DT: f64 = 1.0 / 8.7;

    fn at(x: f64, y: f64) -> Measurement {
        Measurement { x_px: x, y_px: y }
    }

    fn run(frames: &[Vec<Measurement>], config: TrackerConfig) -> Vec<Vec<TrackUpdate>> {
        let mut tracker = NearestNeighbourTracker::new(config);
        #[expect(clippy::cast_precision_loss, reason = "test frame counts are small")]
        let mut out: Vec<_> = frames
            .iter()
            .enumerate()
            .map(|(k, m)| tracker.step(k as f64 * DT, m))
            .collect();
        #[expect(clippy::cast_precision_loss, reason = "test frame counts are small")]
        out.push(tracker.finish(frames.len() as f64 * DT));
        out
    }

    #[expect(clippy::cast_precision_loss, reason = "test frame counts are small")]
    fn line(frames: usize, vx: f64) -> Vec<Vec<Measurement>> {
        (0..frames)
            .map(|k| vec![at(10.0 + vx * k as f64 * DT, 60.0)])
            .collect()
    }

    #[test]
    fn a_steady_target_is_confirmed_with_its_velocity() {
        let steps = run(&line(12, 20.0), TrackerConfig::default());
        let statuses: Vec<_> = steps.iter().flatten().map(|u| u.status).collect();
        assert_eq!(
            &statuses[..3],
            &[
                TrackStatus::Tentative,
                TrackStatus::Tentative,
                TrackStatus::Confirmed
            ]
        );
        assert_eq!(statuses.last(), Some(&TrackStatus::Lost));
        assert!(steps.iter().flatten().all(|u| u.track_id == 1));
        let last = steps[11][0];
        assert!((last.vx_px_s - 20.0).abs() < 1e-9);
        assert!(last.vy_px_s.abs() < 1e-9);
        assert_eq!(last.hits, 12);
    }

    #[test]
    fn a_missed_target_coasts_then_is_lost() {
        let mut frames = line(5, 20.0);
        frames.extend(std::iter::repeat_n(Vec::new(), 3));
        let config = TrackerConfig {
            max_misses: 3,
            ..TrackerConfig::default()
        };
        let steps = run(&frames, config);
        assert_eq!(steps[5][0].status, TrackStatus::Coasting);
        assert_eq!(steps[6][0].status, TrackStatus::Coasting);
        assert_eq!(steps[7][0].status, TrackStatus::Lost);
        let expected_x = 10.0 + 20.0 * 5.0 * DT;
        assert!((steps[5][0].x_px - expected_x).abs() < 1e-9);
        assert_eq!(steps[8], Vec::new());
    }

    #[test]
    fn unconfirmed_tracks_vanish_silently() {
        let steps = run(
            &[vec![at(1.0, 1.0)], vec![], vec![]],
            TrackerConfig::default(),
        );
        assert_eq!(
            steps.iter().map(Vec::len).collect::<Vec<_>>(),
            vec![1, 0, 0, 0]
        );
    }

    #[test]
    fn two_targets_keep_their_identities() {
        let frames: Vec<_> = (0..8)
            .map(|k| {
                let t = f64::from(k) * DT;
                vec![at(10.0 + 20.0 * t, 30.0), at(150.0 - 20.0 * t, 90.0)]
            })
            .collect();
        let steps = run(&frames, TrackerConfig::default());
        for step in &steps[..8] {
            let rows: Vec<_> = step.iter().map(|u| (u.track_id, u.y_px)).collect();
            assert_eq!(rows, vec![(1, 30.0), (2, 90.0)]);
        }
    }

    #[test]
    fn jumps_outside_the_gate_start_a_new_track() {
        let steps = run(
            &[vec![at(0.0, 0.0)], vec![at(50.0, 0.0)]],
            TrackerConfig::default(),
        );
        assert_eq!(steps[1][0].track_id, 2);
    }

    #[test]
    fn identical_input_gives_identical_output() {
        let frames = line(10, 15.0);
        assert_eq!(
            run(&frames, TrackerConfig::default()),
            run(&frames, TrackerConfig::default())
        );
    }

    #[test]
    fn live_track_count() {
        let mut tracker = NearestNeighbourTracker::new(TrackerConfig::default());
        tracker.step(0.0, &[at(0.0, 0.0), at(100.0, 100.0)]);
        assert_eq!(tracker.live_tracks(), 2);
        assert_eq!(tracker.finish(1.0), Vec::new());
        assert_eq!(tracker.live_tracks(), 0);
    }
}
