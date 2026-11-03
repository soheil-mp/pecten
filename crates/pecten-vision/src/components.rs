//! Fixed thresholds and connected-component labelling.
//!
//! The thin slice detects warm targets with a fixed threshold over the sky and groups the hot
//! pixels into blobs (ROADMAP M1.3). Labelling uses the classic two-pass algorithm with a
//! union-find table, so it runs in linear time and its output depends only on the input:
//! blobs are numbered in raster order of their first pixel.

use std::fmt;

/// An error from building an image view or a mask.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VisionError {
    /// The pixel buffer does not hold `width * height` values.
    SizeMismatch {
        /// Expected number of pixels.
        expected: usize,
        /// Number of pixels in the buffer.
        actual: usize,
    },
}

impl fmt::Display for VisionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::SizeMismatch { expected, actual } => {
                write!(f, "image buffer holds {actual} pixels, expected {expected}")
            }
        }
    }
}

impl std::error::Error for VisionError {}

/// A borrowed single-channel image in row-major order.
#[derive(Debug, Clone, Copy)]
pub struct ImageView<'a> {
    width: usize,
    height: usize,
    pixels: &'a [f32],
}

impl<'a> ImageView<'a> {
    /// Wrap a row-major buffer of `width * height` pixels.
    ///
    /// # Errors
    ///
    /// [`VisionError::SizeMismatch`] if the buffer has the wrong length.
    pub fn new(width: usize, height: usize, pixels: &'a [f32]) -> Result<Self, VisionError> {
        let expected = width * height;
        if pixels.len() == expected {
            Ok(Self {
                width,
                height,
                pixels,
            })
        } else {
            Err(VisionError::SizeMismatch {
                expected,
                actual: pixels.len(),
            })
        }
    }

    /// Image width in pixels.
    #[must_use]
    pub const fn width(&self) -> usize {
        self.width
    }

    /// Image height in pixels.
    #[must_use]
    pub const fn height(&self) -> usize {
        self.height
    }

    /// Value at column `x`, row `y`.
    ///
    /// # Panics
    ///
    /// If `(x, y)` is outside the image.
    #[must_use]
    pub fn get(&self, x: usize, y: usize) -> f32 {
        assert!(
            x < self.width && y < self.height,
            "pixel ({x}, {y}) is outside the image"
        );
        self.pixels[y * self.width + x]
    }

    /// All pixels in row-major order.
    #[must_use]
    pub const fn pixels(&self) -> &'a [f32] {
        self.pixels
    }
}

/// Which neighbours count as connected.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Connectivity {
    /// Left, right, up and down.
    Four,
    /// The four edge neighbours and the four corner neighbours.
    #[default]
    Eight,
}

/// A binary image: `true` marks a foreground pixel.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Mask {
    width: usize,
    height: usize,
    bits: Vec<bool>,
}

impl Mask {
    /// Build a mask from row-major bits.
    ///
    /// # Errors
    ///
    /// [`VisionError::SizeMismatch`] if `bits` does not hold `width * height` values.
    pub fn new(width: usize, height: usize, bits: Vec<bool>) -> Result<Self, VisionError> {
        let expected = width * height;
        if bits.len() == expected {
            Ok(Self {
                width,
                height,
                bits,
            })
        } else {
            Err(VisionError::SizeMismatch {
                expected,
                actual: bits.len(),
            })
        }
    }

    /// Number of foreground pixels.
    #[must_use]
    pub fn count(&self) -> usize {
        self.bits.iter().filter(|&&b| b).count()
    }

    /// Whether the pixel at column `x`, row `y` is foreground.
    #[must_use]
    pub fn get(&self, x: usize, y: usize) -> bool {
        self.bits[y * self.width + x]
    }
}

/// Mark every pixel whose value is strictly above `level`. NaN pixels are never foreground.
#[must_use]
pub fn threshold_above(image: &ImageView<'_>, level: f32) -> Mask {
    Mask {
        width: image.width,
        height: image.height,
        bits: image.pixels.iter().map(|&v| v > level).collect(),
    }
}

/// One connected group of foreground pixels and its measurements.
#[derive(Debug, Clone, PartialEq)]
pub struct Blob {
    /// Label, from 1 in raster order of each blob's first pixel.
    pub label: u32,
    /// Number of pixels.
    pub area_px: u32,
    /// Centroid column, weighted by each pixel's excess over the background (pixel centres at
    /// `x + 0.5`).
    pub centroid_x: f64,
    /// Centroid row, weighted the same way (pixel centres at `y + 0.5`).
    pub centroid_y: f64,
    /// Sum of each pixel's excess over the background.
    pub excess_sum: f64,
    /// Largest pixel value.
    pub peak: f32,
    /// Bounding box `(min_x, min_y, max_x, max_y)`, inclusive.
    pub bbox: (usize, usize, usize, usize),
}

/// Labels of a mask: 0 for background, 1.. for components.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Labels {
    width: usize,
    height: usize,
    ids: Vec<u32>,
    count: u32,
}

impl Labels {
    /// Number of components.
    #[must_use]
    pub const fn count(&self) -> u32 {
        self.count
    }

    /// Label at column `x`, row `y` (0 for background).
    #[must_use]
    pub fn get(&self, x: usize, y: usize) -> u32 {
        self.ids[y * self.width + x]
    }
}

fn find(parent: &mut [u32], mut i: u32) -> u32 {
    while parent[i as usize] != i {
        let grand = parent[parent[i as usize] as usize];
        parent[i as usize] = grand;
        i = grand;
    }
    i
}

fn union(parent: &mut [u32], a: u32, b: u32) {
    let (ra, rb) = (find(parent, a), find(parent, b));
    if ra != rb {
        let (low, high) = if ra < rb { (ra, rb) } else { (rb, ra) };
        parent[high as usize] = low;
    }
}

/// Label the connected components of a mask.
#[must_use]
pub fn label(mask: &Mask, connectivity: Connectivity) -> Labels {
    let (w, h) = (mask.width, mask.height);
    let mut labels = vec![0_u32; w * h];
    let mut parent: Vec<u32> = vec![0];
    for y in 0..h {
        for x in 0..w {
            if !mask.bits[y * w + x] {
                continue;
            }
            let mut neighbours = [0_u32; 4];
            let mut n = 0;
            let mut push = |label: u32| {
                if label != 0 {
                    neighbours[n] = label;
                    n += 1;
                }
            };
            if x > 0 {
                push(labels[y * w + x - 1]);
            }
            if y > 0 {
                push(labels[(y - 1) * w + x]);
                if connectivity == Connectivity::Eight {
                    if x > 0 {
                        push(labels[(y - 1) * w + x - 1]);
                    }
                    if x + 1 < w {
                        push(labels[(y - 1) * w + x + 1]);
                    }
                }
            }
            let current = if n == 0 {
                let next = u32::try_from(parent.len()).unwrap_or(u32::MAX);
                parent.push(next);
                next
            } else {
                let smallest = *neighbours[..n].iter().min().unwrap_or(&0);
                for &other in &neighbours[..n] {
                    union(&mut parent, smallest, other);
                }
                smallest
            };
            labels[y * w + x] = current;
        }
    }
    // Second pass: resolve to roots and renumber densely in raster order.
    let mut dense = vec![0_u32; parent.len()];
    let mut count = 0_u32;
    for value in &mut labels {
        if *value == 0 {
            continue;
        }
        let root = find(&mut parent, *value) as usize;
        if dense[root] == 0 {
            count += 1;
            dense[root] = count;
        }
        *value = dense[root];
    }
    Labels {
        width: w,
        height: h,
        ids: labels,
        count,
    }
}

/// Measure every component of `labels` in `image`, ordered by label.
///
/// Centroids are weighted by each pixel's excess over `background`, which gives sub-pixel
/// accuracy for small warm targets; a blob whose pixels are all at or below the background
/// falls back to the plain mean of its pixel centres.
///
/// # Panics
///
/// If `labels` and `image` differ in size.
#[must_use]
#[expect(
    clippy::cast_precision_loss,
    reason = "pixel coordinates are far below 2^52"
)]
pub fn measure(labels: &Labels, image: &ImageView<'_>, background: f32) -> Vec<Blob> {
    assert!(
        labels.width == image.width && labels.height == image.height,
        "labels and image must have the same size"
    );
    let n = labels.count as usize;
    let mut area = vec![0_u32; n];
    let mut sum = vec![0.0_f64; n];
    let mut sum_x = vec![0.0_f64; n];
    let mut sum_y = vec![0.0_f64; n];
    let mut plain_x = vec![0.0_f64; n];
    let mut plain_y = vec![0.0_f64; n];
    let mut peak = vec![f32::NEG_INFINITY; n];
    let mut bbox = vec![(usize::MAX, usize::MAX, 0_usize, 0_usize); n];
    for y in 0..labels.height {
        for x in 0..labels.width {
            let l = labels.ids[y * labels.width + x];
            if l == 0 {
                continue;
            }
            let i = (l - 1) as usize;
            let value = image.pixels[y * image.width + x];
            let weight = f64::from((value - background).max(0.0));
            let (cx, cy) = (x as f64 + 0.5, y as f64 + 0.5);
            area[i] += 1;
            sum[i] += weight;
            sum_x[i] += weight * cx;
            sum_y[i] += weight * cy;
            plain_x[i] += cx;
            plain_y[i] += cy;
            peak[i] = peak[i].max(value);
            let b = &mut bbox[i];
            *b = (b.0.min(x), b.1.min(y), b.2.max(x), b.3.max(y));
        }
    }
    (0..n)
        .map(|i| {
            let count = f64::from(area[i]);
            let (centroid_x, centroid_y) = if sum[i] > 0.0 {
                (sum_x[i] / sum[i], sum_y[i] / sum[i])
            } else {
                (plain_x[i] / count, plain_y[i] / count)
            };
            Blob {
                label: u32::try_from(i + 1).unwrap_or(u32::MAX),
                area_px: area[i],
                centroid_x,
                centroid_y,
                excess_sum: sum[i],
                peak: peak[i],
                bbox: bbox[i],
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::{Connectivity, ImageView, Mask, VisionError, label, measure, threshold_above};

    fn mask(rows: &[&str]) -> Mask {
        let width = rows[0].len();
        let bits = rows
            .iter()
            .flat_map(|r| r.chars().map(|c| c == '#'))
            .collect();
        Mask::new(width, rows.len(), bits).expect("rows have equal length")
    }

    #[test]
    fn rejects_buffers_of_the_wrong_size() {
        let pixels = [0.0_f32; 5];
        let err = ImageView::new(2, 3, &pixels).expect_err("5 != 6");
        assert_eq!(
            err,
            VisionError::SizeMismatch {
                expected: 6,
                actual: 5
            }
        );
        assert_eq!(err.to_string(), "image buffer holds 5 pixels, expected 6");
        assert!(Mask::new(2, 2, vec![true]).is_err());
    }

    #[test]
    fn threshold_is_strict_and_ignores_nan() {
        let pixels = [1.0, 2.0, 3.0, f32::NAN];
        let image = ImageView::new(2, 2, &pixels).expect("4 pixels");
        let m = threshold_above(&image, 2.0);
        assert_eq!(
            (m.get(0, 0), m.get(1, 0), m.get(0, 1), m.get(1, 1)),
            (false, false, true, false)
        );
        assert_eq!(m.count(), 1);
    }

    #[test]
    fn diagonal_pixels_join_only_with_eight_connectivity() {
        let m = mask(&["#..", ".#.", "..#"]);
        assert_eq!(label(&m, Connectivity::Eight).count(), 1);
        assert_eq!(label(&m, Connectivity::Four).count(), 3);
    }

    #[test]
    fn u_shapes_merge_into_one_component() {
        // The two arms get different provisional labels that the bottom row joins.
        let m = mask(&["#...#", "#...#", "#####"]);
        let labels = label(&m, Connectivity::Four);
        assert_eq!(labels.count(), 1);
        assert_eq!(labels.get(4, 0), 1);
    }

    #[test]
    fn labels_are_numbered_in_raster_order() {
        let m = mask(&["..#.", "....", "#..#"]);
        let labels = label(&m, Connectivity::Eight);
        assert_eq!(labels.count(), 3);
        assert_eq!(
            (labels.get(2, 0), labels.get(0, 2), labels.get(3, 2)),
            (1, 2, 3)
        );
        assert_eq!(labels.get(1, 1), 0);
    }

    #[test]
    fn empty_and_full_masks() {
        assert_eq!(
            label(&mask(&["...", "..."]), Connectivity::Eight).count(),
            0
        );
        assert_eq!(label(&mask(&["###", "###"]), Connectivity::Four).count(), 1);
    }

    #[test]
    fn measures_area_bbox_peak_and_weighted_centroid() {
        // A 3 x 1 blob with excess 1, 2, 1 over the background: centroid at the middle pixel.
        #[rustfmt::skip]
        let pixels = [
            0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 2.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 9.0,
        ];
        let image = ImageView::new(5, 3, &pixels).expect("15 pixels");
        let labels = label(&threshold_above(&image, 0.5), Connectivity::Four);
        let blobs = measure(&labels, &image, 0.0);
        assert_eq!(blobs.len(), 2);
        let first = &blobs[0];
        assert_eq!(
            (first.label, first.area_px, first.bbox),
            (1, 3, (1, 1, 3, 1))
        );
        assert!((first.centroid_x - 2.5).abs() < 1e-12);
        assert!((first.centroid_y - 1.5).abs() < 1e-12);
        assert!((first.excess_sum - 4.0).abs() < 1e-12);
        assert!((blobs[1].peak - 9.0).abs() < f32::EPSILON);
    }

    #[test]
    fn weighted_centroid_finds_sub_pixel_positions() {
        let pixels = [0.0, 3.0, 1.0, 0.0];
        let image = ImageView::new(4, 1, &pixels).expect("4 pixels");
        let blobs = measure(
            &label(&threshold_above(&image, 0.5), Connectivity::Four),
            &image,
            0.0,
        );
        // (1.5 * 3 + 2.5 * 1) / 4 = 1.75
        assert!((blobs[0].centroid_x - 1.75).abs() < 1e-12);
    }

    #[test]
    fn centroid_falls_back_to_pixel_centres_without_excess() {
        let pixels = [5.0, 5.0];
        let image = ImageView::new(2, 1, &pixels).expect("2 pixels");
        let labels = label(&threshold_above(&image, 1.0), Connectivity::Four);
        let blobs = measure(&labels, &image, 10.0);
        assert!((blobs[0].centroid_x - 1.0).abs() < 1e-12);
        assert!(blobs[0].excess_sum.abs() < 1e-12);
    }
}
