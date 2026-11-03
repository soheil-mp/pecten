//! The minimal edge pipeline of the thin slice: frames in, track updates out (ROADMAP M1.3).
//!
//! ```text
//! frame → sky level (median) → threshold (sky + k · NETD) → connected components → blobs
//!       → nearest-neighbour tracker → track updates
//! ```
//!
//! The sky is uniform in the thin slice, so its median is a good background estimate and a
//! fixed multiple of the NETD above it separates warm targets from noise. Background models
//! arrive in M5.

use pecten_vision::components::{
    Blob, Connectivity, ImageView, VisionError, label, measure, threshold_above,
};
use pecten_vision::tracking::{
    Measurement, NearestNeighbourTracker, TrackStatus, TrackUpdate, TrackerConfig,
};

use crate::frames::{CameraInfo, Frame};

/// Parameters of the minimal detector.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DetectorConfig {
    /// Threshold in multiples of the NETD above the sky level.
    pub threshold_sigma: f32,
    /// Smallest blob that becomes a measurement.
    pub min_area_px: u32,
}

impl Default for DetectorConfig {
    fn default() -> Self {
        Self {
            threshold_sigma: 5.0,
            min_area_px: 1,
        }
    }
}

/// What the pipeline found in one frame.
#[derive(Debug, Clone, PartialEq)]
pub struct FrameResult {
    /// Frame the result belongs to.
    pub frame_id: u64,
    /// Estimated sky level in kelvin.
    pub sky_k: f32,
    /// Warm blobs above the threshold.
    pub blobs: Vec<Blob>,
    /// Track updates of this frame.
    pub updates: Vec<TrackUpdate>,
}

/// Detection and tracking for one camera.
#[derive(Debug)]
pub struct EdgePipeline {
    camera: CameraInfo,
    detector: DetectorConfig,
    tracker: NearestNeighbourTracker,
    start_ns: Option<i64>,
    last_ns: i64,
}

/// Median of the finite values; `NaN` if there are none.
fn median(values: &[f32]) -> f32 {
    let mut finite: Vec<f32> = values.iter().copied().filter(|v| v.is_finite()).collect();
    if finite.is_empty() {
        return f32::NAN;
    }
    let middle = finite.len() / 2;
    let (_, value, _) = finite.select_nth_unstable_by(middle, f32::total_cmp);
    *value
}

impl EdgePipeline {
    /// A pipeline for a camera.
    #[must_use]
    pub const fn new(camera: CameraInfo, detector: DetectorConfig, tracker: TrackerConfig) -> Self {
        Self {
            camera,
            detector,
            tracker: NearestNeighbourTracker::new(tracker),
            start_ns: None,
            last_ns: 0,
        }
    }

    #[expect(
        clippy::cast_precision_loss,
        reason = "nanosecond offsets within a run fit f64"
    )]
    fn seconds(&self, timestamp_ns: i64) -> f64 {
        (timestamp_ns - self.start_ns.unwrap_or(timestamp_ns)) as f64 / 1e9
    }

    /// Process one frame.
    ///
    /// # Errors
    ///
    /// [`VisionError`] if the frame does not match the camera's image size.
    pub fn process(&mut self, frame: &Frame) -> Result<FrameResult, VisionError> {
        let image = ImageView::new(self.camera.width_px, self.camera.height_px, &frame.temp_k)?;
        self.start_ns.get_or_insert(frame.timestamp_ns);
        self.last_ns = frame.timestamp_ns;
        let sky = median(&frame.temp_k);
        let level = sky + self.detector.threshold_sigma * self.camera.netd_k;
        let labels = label(&threshold_above(&image, level), Connectivity::Eight);
        let blobs: Vec<Blob> = measure(&labels, &image, sky)
            .into_iter()
            .filter(|b| b.area_px >= self.detector.min_area_px)
            .collect();
        let measurements: Vec<Measurement> = blobs
            .iter()
            .map(|b| Measurement {
                x_px: b.centroid_x,
                y_px: b.centroid_y,
            })
            .collect();
        let updates = self
            .tracker
            .step(self.seconds(frame.timestamp_ns), &measurements);
        Ok(FrameResult {
            frame_id: frame.frame_id,
            sky_k: sky,
            blobs,
            updates,
        })
    }

    /// End every live track after the last frame.
    pub fn finish(&mut self) -> Vec<TrackUpdate> {
        let time = self.seconds(self.last_ns);
        self.tracker.finish(time)
    }

    /// Absolute UTC time in nanoseconds of a tracker time.
    #[must_use]
    #[expect(
        clippy::cast_possible_truncation,
        reason = "times within a run fit i64 nanoseconds"
    )]
    pub fn timestamp_ns(&self, time_s: f64) -> i64 {
        self.start_ns.unwrap_or(0) + (time_s * 1e9).round() as i64
    }
}

/// A track update as one line of JSON, with an absolute UTC timestamp.
#[must_use]
pub fn to_json_line(update: &TrackUpdate, timestamp_ns: i64) -> String {
    let status = match update.status {
        TrackStatus::Tentative => "tentative",
        TrackStatus::Confirmed => "confirmed",
        TrackStatus::Coasting => "coasting",
        TrackStatus::Lost => "lost",
    };
    format!(
        "{{\"track_id\":{},\"status\":\"{status}\",\"timestamp_ns\":{timestamp_ns},\"x_px\":{:.3},\"y_px\":{:.3},\"vx_px_s\":{:.3},\"vy_px_s\":{:.3},\"hits\":{}}}",
        update.track_id, update.x_px, update.y_px, update.vx_px_s, update.vy_px_s, update.hits
    )
}

#[cfg(test)]
mod tests {
    use pecten_vision::tracking::{TrackStatus, TrackerConfig};

    use super::{DetectorConfig, EdgePipeline, median, to_json_line};
    use crate::frames::{CameraInfo, Frame};

    const CAMERA: CameraInfo = CameraInfo {
        width_px: 160,
        height_px: 120,
        netd_k: 0.05,
    };
    const PERIOD_NS: i64 = 114_942_529;

    /// Deterministic Gaussian noise: xorshift64 and Box-Muller.
    struct Noise(u64);

    impl Noise {
        fn uniform(&mut self) -> f64 {
            self.0 ^= self.0 << 13;
            self.0 ^= self.0 >> 7;
            self.0 ^= self.0 << 17;
            #[expect(
                clippy::cast_precision_loss,
                reason = "53 bits are enough for a uniform"
            )]
            let value = (self.0 >> 11) as f64 / (1_u64 << 53) as f64;
            value
        }

        fn gaussian(&mut self) -> f64 {
            let (u1, u2) = (self.uniform().max(1e-12), self.uniform());
            (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
        }
    }

    #[expect(
        clippy::cast_possible_truncation,
        clippy::cast_precision_loss,
        reason = "test data"
    )]
    fn disc_frames(count: u64, vx: f64) -> Vec<Frame> {
        let mut noise = Noise(0x9E37_79B9_7F4A_7C15);
        (0..count)
            .map(|k| {
                let t = k as f64 * PERIOD_NS as f64 / 1e9;
                let (cx, cy) = (10.0 + vx * t, 60.0);
                let temp_k = (0..120 * 160)
                    .map(|i| {
                        let (x, y) = (f64::from(i % 160) + 0.5, f64::from(i / 160) + 0.5);
                        let warm = (x - cx).hypot(y - cy) <= 2.0;
                        let base = if warm { 303.15 } else { 253.15 };
                        (base + 0.05 * noise.gaussian()) as f32
                    })
                    .collect();
                Frame {
                    frame_id: k,
                    timestamp_ns: 1_000 + k.cast_signed() * PERIOD_NS,
                    temp_k,
                }
            })
            .collect()
    }

    #[test]
    fn median_ignores_non_finite_values() {
        assert!((median(&[3.0, f32::NAN, 1.0, 2.0]) - 2.0).abs() < f32::EPSILON);
        assert!(median(&[f32::NAN]).is_nan());
    }

    #[test]
    fn one_warm_disc_becomes_one_confirmed_track_at_the_right_speed() {
        let mut pipeline =
            EdgePipeline::new(CAMERA, DetectorConfig::default(), TrackerConfig::default());
        let mut updates = Vec::new();
        for frame in &disc_frames(40, 25.0) {
            let result = pipeline.process(frame).expect("frame matches the camera");
            assert!((result.sky_k - 253.15).abs() < 0.01);
            assert_eq!(
                result.blobs.len(),
                1,
                "frame {} has noise blobs",
                frame.frame_id
            );
            updates.extend(result.updates);
        }
        updates.extend(pipeline.finish());
        assert!(updates.iter().all(|u| u.track_id == 1));
        let last = updates
            .iter()
            .rev()
            .find(|u| u.status == TrackStatus::Confirmed)
            .expect("confirmed");
        assert!(
            (last.vx_px_s - 25.0).abs() < 25.0 * 0.05,
            "vx = {}",
            last.vx_px_s
        );
        assert!(last.vy_px_s.abs() < 1.0);
        assert_eq!(updates.last().map(|u| u.status), Some(TrackStatus::Lost));
    }

    #[test]
    fn frames_of_the_wrong_size_are_rejected() {
        let mut pipeline =
            EdgePipeline::new(CAMERA, DetectorConfig::default(), TrackerConfig::default());
        let frame = Frame {
            frame_id: 0,
            timestamp_ns: 0,
            temp_k: vec![0.0; 10],
        };
        assert!(pipeline.process(&frame).is_err());
    }

    #[test]
    fn json_lines_carry_every_field() {
        let mut pipeline =
            EdgePipeline::new(CAMERA, DetectorConfig::default(), TrackerConfig::default());
        let frames = disc_frames(1, 0.0);
        let result = pipeline.process(&frames[0]).expect("valid frame");
        let update = result.updates[0];
        let line = to_json_line(&update, pipeline.timestamp_ns(update.time_s));
        assert!(
            line.starts_with("{\"track_id\":1,\"status\":\"tentative\",\"timestamp_ns\":1000,")
        );
        assert!(line.ends_with("\"hits\":1}"));
    }
}
