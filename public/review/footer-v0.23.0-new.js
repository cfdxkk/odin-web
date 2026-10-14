// app/lib/odin-footer-screen.ts
var FOOTER_SCREEN_MATRIX = [
  0,
  8,
  2,
  10,
  12,
  4,
  14,
  6,
  3,
  11,
  1,
  9,
  15,
  7,
  13,
  5
];
var FOOTER_SCREEN_PITCH = 3.8;
var FOOTER_SCREEN_MARK_RATIO = 0.84;
var FOOTER_SCREEN_INKS = [0, 78, 143, 208];
function footerInkLevel(tone, column, row) {
  const scaled = Math.max(0, Math.min(1, tone)) * (FOOTER_SCREEN_INKS.length - 1);
  const base = Math.floor(scaled);
  const threshold = (FOOTER_SCREEN_MATRIX[(row & 3) * 4 + (column & 3)] + 0.5) / 16;
  return Math.min(FOOTER_SCREEN_INKS.length - 1, base + Number(scaled - base > threshold));
}
function cleanFooterTones(tones, width, height) {
  const clean = tones.slice();
  const visited = new Uint8Array(tones.length);
  const queue = new Int32Array(tones.length);
  for (let start = 0; start < tones.length; start++) {
    if (visited[start] || tones[start] < 0.01) continue;
    let head = 0, tail = 1, peak = 0;
    queue[0] = start;
    visited[start] = 1;
    while (head < tail) {
      const index = queue[head++], x = index % width, y = Math.floor(index / width);
      peak = Math.max(peak, tones[index]);
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy || x + dx < 0 || x + dx >= width || y + dy < 0 || y + dy >= height) continue;
        const neighbor = (y + dy) * width + x + dx;
        if (!visited[neighbor] && tones[neighbor] >= 0.01) {
          visited[neighbor] = 1;
          queue[tail++] = neighbor;
        }
      }
    }
    if (tail < 24 && peak < 0.32) for (let i = 0; i < tail; i++) clean[queue[i]] = 0;
  }
  const supported = clean.slice();
  const threshold = 1 / 96;
  for (let y = 1; y < height - 1; y++) for (let x = 1; x < width - 1; x++) {
    const index = y * width + x;
    if (clean[index] < threshold || clean[index] >= 0.04) continue;
    const neighbors = [
      clean[index - width - 1],
      clean[index - width],
      clean[index - width + 1],
      clean[index - 1],
      clean[index + 1],
      clean[index + width - 1],
      clean[index + width],
      clean[index + width + 1]
    ].map((tone) => tone >= threshold);
    const areaSupport = neighbors.filter(Boolean).length >= 4;
    const ridgeSupport = neighbors[0] && neighbors[7] || neighbors[1] && neighbors[6] || neighbors[2] && neighbors[5] || neighbors[3] && neighbors[4];
    if (!areaSupport && !ridgeSupport) supported[index] = 0;
  }
  return supported;
}

// <stdin>
var watch = (refs, callback) => callback(refs.map((ref) => ref.value));
var onBeforeUnmount = (callback) => window.addEventListener("pagehide", callback);
var SOURCE = "/images/odin-mountain-footer-v0.23.0.webp";
var BACKGROUND = "#070b10";
var root = { value: document.querySelector(".footer-print") };
var canvas = { value: document.querySelector("canvas") };
var resizeObserver;
var intersectionObserver;
var resolutionQuery;
var timer;
var sourceImage;
var loading;
var visible = false;
var disposed = false;
var dirty = true;
var rendering = false;
var lastSize = "";
var renderCount = 0;
var clamp = (value) => Math.max(0, Math.min(1, value));
var smooth = (value) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};
function loadSource() {
  if (sourceImage?.complete && sourceImage.naturalWidth) return Promise.resolve(sourceImage);
  if (loading) return loading;
  const image = new Image();
  image.decoding = "async";
  sourceImage = image;
  loading = new Promise((resolve, reject) => {
    image.onload = () => {
      image.onload = image.onerror = null;
      resolve(image);
    };
    image.onerror = () => {
      image.onload = image.onerror = null;
      reject(new Error("Footer plate could not load"));
    };
    image.src = SOURCE;
  }).finally(() => {
    loading = void 0;
  });
  return loading;
}
function cancelTimer() {
  if (timer !== void 0) {
    clearTimeout(timer);
    timer = void 0;
  }
}
function schedule(delay = 120) {
  cancelTimer();
  if (disposed || !visible || document.hidden || !dirty) return;
  timer = setTimeout(() => {
    timer = void 0;
    void render();
  }, delay);
}
function invalidate() {
  dirty = true;
  if (canvas.value) canvas.value.dataset.ready = "false";
  schedule();
}
async function render() {
  if (disposed || !visible || document.hidden || !dirty || rendering) return;
  rendering = true;
  try {
    const image = await loadSource();
    const target = canvas.value, host = root.value;
    if (disposed || !visible || document.hidden || !target || !host) return;
    const { width, height } = host.getBoundingClientRect();
    if (width < 1 || height < 1) return;
    const dpr = window.devicePixelRatio || 1;
    const mobile = window.matchMedia("(max-width: 700px)").matches;
    const pitch = FOOTER_SCREEN_PITCH;
    const size = `${width}:${height}:${dpr}:${mobile}`;
    if (size === lastSize) {
      dirty = false;
      target.dataset.ready = "true";
      return;
    }
    const started = performance.now();
    const artHeight = mobile ? Math.max(300, height * 0.55) : Math.min(height * 0.75, width * 0.43);
    const artTop = height - artHeight;
    const columns = Math.ceil(width / pitch), rows = Math.ceil(artHeight / pitch);
    const plate = document.createElement("canvas");
    plate.width = Math.ceil(width);
    plate.height = Math.ceil(artHeight);
    const plateContext = plate.getContext("2d");
    const samples = document.createElement("canvas");
    samples.width = columns;
    samples.height = rows;
    const sampleContext = samples.getContext("2d", { willReadFrequently: true });
    const context = target.getContext("2d", { alpha: false });
    if (!sampleContext || !context || !plateContext) throw new Error("Footer canvas is unavailable");
    sampleContext.fillStyle = BACKGROUND;
    sampleContext.fillRect(0, 0, columns, rows);
    sampleContext.imageSmoothingEnabled = true;
    sampleContext.imageSmoothingQuality = "high";
    const scale = Math.max(width / image.naturalWidth, artHeight / image.naturalHeight);
    const sourceWidth = width / scale, sourceHeight = artHeight / scale;
    const sourceX = (image.naturalWidth - sourceWidth) * (mobile ? 0.53 : 0.5);
    const sourceY = (image.naturalHeight - sourceHeight) * (mobile ? 0.5 : 0.55);
    plateContext.filter = "blur(2.2px) grayscale(1)";
    plateContext.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, width, artHeight);
    sampleContext.drawImage(plate, 0, 0, columns, rows);
    const pixels = sampleContext.getImageData(0, 0, columns, rows).data;
    const rawTones = new Float32Array(columns * rows);
    for (let i = 0; i < rawTones.length; i++) {
      const offset = i * 4;
      const luminance = 0.2126 * pixels[offset] + 0.7152 * pixels[offset + 1] + 0.0722 * pixels[offset + 2];
      rawTones[i] = Math.pow(clamp((luminance - 15) / 110), 1.1) * 0.95;
    }
    const tones = cleanFooterTones(rawTones, columns, rows);
    target.width = Math.round(width * dpr);
    target.height = Math.round(height * dpr);
    const print = context.createImageData(target.width, target.height);
    const ink = print.data;
    for (let index = 0; index < ink.length; index += 4) {
      ink[index] = 7;
      ink[index + 1] = 11;
      ink[index + 2] = 16;
      ink[index + 3] = 255;
    }
    const scaleX = target.width / width, scaleY = target.height / height;
    const markSize = pitch * FOOTER_SCREEN_MARK_RATIO;
    let marks = 0;
    for (let row = 0; row < rows; row++) {
      const localY = (row + 0.5) * pitch, fraction = localY / artHeight;
      const y = artTop + localY;
      const fade = smooth((fraction + 0.12) / 0.6) * (1 - 0.3 * smooth((fraction - 0.85) / 0.15));
      if (fade === 0) continue;
      for (let column = 0; column < columns; column++) {
        const tone = tones[row * columns + column];
        const inkLevel = footerInkLevel(tone, column, row);
        if (!inkLevel) continue;
        const gray = FOOTER_SCREEN_INKS[inkLevel];
        const x = (column + 0.5) * pitch;
        const x0 = (x - markSize / 2) * scaleX, x1 = (x + markSize / 2) * scaleX;
        const y0 = (y - markSize / 2) * scaleY, y1 = (y + markSize / 2) * scaleY;
        const left = Math.max(0, Math.floor(x0)), right = Math.min(target.width - 1, Math.ceil(x1) - 1);
        const top = Math.max(0, Math.floor(y0)), bottom = Math.min(target.height - 1, Math.ceil(y1) - 1);
        for (let py = top; py <= bottom; py++) {
          for (let px = left; px <= right; px++) {
            const coverage = Math.max(0, Math.min(px + 1, x1) - Math.max(px, x0)) * Math.max(0, Math.min(py + 1, y1) - Math.max(py, y0)) * fade;
            const index = (py * target.width + px) * 4;
            ink[index] = Math.round(7 + (gray - 7) * coverage);
            ink[index + 1] = Math.round(11 + (gray - 11) * coverage);
            ink[index + 2] = Math.round(16 + (gray - 16) * coverage);
          }
        }
        marks++;
      }
    }
    context.putImageData(print, 0, 0);
    samples.width = samples.height = plate.width = plate.height = 1;
    dirty = false;
    lastSize = size;
    renderCount++;
    Object.assign(target.dataset, {
      ready: "true",
      source: SOURCE,
      gridPitch: String(pitch),
      screenCount: "1",
      renderCount: String(renderCount),
      renderMs: (performance.now() - started).toFixed(1),
      dpr: String(dpr),
      marks: String(marks),
      raster: "native-pixels",
      descreenBlur: "2.2",
      screen: "ordered-4x4",
      markShape: "square",
      markSize: String(markSize),
      inkLevels: "4",
      atmosphericFade: "ink-only",
      speckFilter: "connected-tones"
    });
    delete target.dataset.error;
  } catch {
    if (!disposed && canvas.value) {
      canvas.value.dataset.ready = "false";
      canvas.value.dataset.error = "print-unavailable";
    }
    dirty = false;
  } finally {
    rendering = false;
  }
}
function visibilityChanged() {
  if (document.hidden) cancelTimer();
  else schedule(0);
}
function watchResolution() {
  resolutionQuery?.removeEventListener("change", resolutionChanged);
  resolutionQuery = window.matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`);
  resolutionQuery.addEventListener("change", resolutionChanged);
}
function resolutionChanged() {
  watchResolution();
  invalidate();
}
watch([root, canvas], ([host, target]) => {
  if (!host || !target || disposed || resizeObserver) return;
  resizeObserver = new ResizeObserver(invalidate);
  resizeObserver.observe(host);
  intersectionObserver = new IntersectionObserver((entries) => {
    visible = entries.some((entry) => entry.isIntersecting);
    if (visible) {
      if (!lastSize) dirty = true;
      schedule(0);
    } else cancelTimer();
  }, { threshold: 0 });
  intersectionObserver.observe(host);
  window.addEventListener("resize", invalidate, { passive: true });
  document.addEventListener("visibilitychange", visibilityChanged);
  watchResolution();
  target.dataset.observing = "true";
}, { flush: "post" });
onBeforeUnmount(() => {
  disposed = true;
  cancelTimer();
  resizeObserver?.disconnect();
  intersectionObserver?.disconnect();
  resolutionQuery?.removeEventListener("change", resolutionChanged);
  window.removeEventListener("resize", invalidate);
  document.removeEventListener("visibilitychange", visibilityChanged);
  if (sourceImage && !sourceImage.complete) sourceImage.src = "";
  sourceImage = void 0;
  if (canvas.value) canvas.value.width = canvas.value.height = 1;
});
