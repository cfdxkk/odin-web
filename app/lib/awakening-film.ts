export const AWAKENING_DURATION = 72

export const AWAKENING_CHAPTERS = [
  {
    id: 'revelation', title: '显影', en: 'REVELATION', start: 0, end: 16,
    line: '黑暗退去，轮廓先行。',
    description: '循着微光，辨认一艘战舰的尺度。',
  },
  {
    id: 'reconstruction', title: '重构', en: 'RECONSTRUCTION', start: 16, end: 32,
    line: '每一道线，都指向力量。',
    description: '掠过装甲与甲板，让结构逐层显现。',
  },
  {
    id: 'armament', title: '武备', en: 'ARMAMENT', start: 32, end: 54,
    line: '沉默的舰体，展开锋芒。',
    description: '从主炮到舰桥，见证机械苏醒的秩序。',
  },
  {
    id: 'transcendence', title: '跃迁', en: 'TRANSCENDENCE', start: 54, end: 72,
    line: '让星辰，退向身后。',
    description: '武备归位，尾焰点亮，驶向深空。',
  },
] as const

export type AwakeningPlaybackState = {
  userPaused: boolean
  scrubbing: boolean
  visible: boolean
  overlayOpen: boolean
  inspect: boolean
  reducedMotion: boolean
  started: boolean
}

// Transient blockers never modify the user's explicit playback preference.
export function shouldAdvanceFilm(state: AwakeningPlaybackState): boolean {
  return state.started && !state.userPaused && !state.scrubbing && state.visible
    && !state.overlayOpen && !state.inspect && !state.reducedMotion
}

export function clampFilmTime(time: number): number {
  return Math.max(0, Math.min(AWAKENING_DURATION, Number.isFinite(time) ? time : 0))
}

type Point3 = [number, number, number]
type CameraKey = { time: number; position: Point3; target: Point3 }

// World coordinates: +Y is up, -Z is the bow, +Z the stern. Every camera
// remains outside the hull's lateral extent, including the low defense pass.
// This is one continuous flight, with no cuts or phase resets at chapters.
const CAMERA_KEYS: CameraKey[] = [
  { time: 0, position: [-6.8, 2.65, -5.1], target: [0, .24, -.15] },
  { time: 8, position: [-7.25, 2.1, -3.2], target: [0, .22, -.3] },
  { time: 16, position: [-6.35, 1.35, -.65], target: [0, .22, -.35] },
  { time: 24, position: [-5.35, 2.3, .65], target: [0, .4, .05] },
  { time: 32, position: [-4.9, 2.75, -2.8], target: [0, .12, -.75] },
  // Main batteries open first in the frame, then the lens follows the flank.
  { time: 38.5, position: [-4.3, 2.1, -1.45], target: [0, .15, -.72] },
  { time: 42.5, position: [-4.5, 1, .1], target: [-.45, .2, .1] },
  { time: 46, position: [-4.05, -1.1, 2.6], target: [-.45, .02, .85] },
  { time: 49.5, position: [-3.95, 1.6, 4.4], target: [0, .76, .85] },
  { time: 54, position: [-3.1, 1.5, 6.2], target: [0, .3, 1.5] },
  { time: 60, position: [-2.7, .9, 7.2], target: [0, .12, 1.85] },
  { time: 64, position: [-3.2, 1.15, 8.5], target: [0, .15, 1.2] },
  { time: 68, position: [-6, 2.3, 14], target: [0, .2, .2] },
  { time: 72, position: [-10, 4, 25], target: [0, .25, -.4] },
]

const smooth = (start: number, end: number, time: number) => {
  const u = Math.max(0, Math.min(1, (time - start) / (end - start)))
  return u * u * (3 - 2 * u)
}

// Shape-preserving cubic Hermite tracks have continuous velocity and cannot
// overshoot their authored bounds. Unequal shot intervals keep real-time pace.
function createTrack(times: number[], values: number[]) {
  const intervals = times.slice(1).map((time, i) => time - times[i]!)
  const slopes = intervals.map((interval, i) => (values[i + 1]! - values[i]!) / interval)
  const endSlope = (h0: number, h1: number, d0: number, d1: number) => {
    const slope = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
    if (Math.sign(slope) !== Math.sign(d0)) return 0
    return Math.sign(d0) !== Math.sign(d1) && Math.abs(slope) > 3 * Math.abs(d0) ? 3 * d0 : slope
  }
  const tangents = values.map((_, i) => {
    if (i === 0) return endSlope(intervals[0]!, intervals[1]!, slopes[0]!, slopes[1]!)
    if (i === values.length - 1) {
      return endSlope(intervals[i - 1]!, intervals[i - 2]!, slopes[i - 1]!, slopes[i - 2]!)
    }
    const before = slopes[i - 1]!, after = slopes[i]!
    if (before * after <= 0) return 0
    const w1 = 2 * intervals[i]! + intervals[i - 1]!
    const w2 = intervals[i]! + 2 * intervals[i - 1]!
    return (w1 + w2) / (w1 / before + w2 / after)
  })
  return (time: number): number => {
    if (time <= times[0]!) return values[0]!
    if (time >= times[times.length - 1]!) return values[values.length - 1]!
    const i = times.findIndex(end => end > time) - 1
    const interval = intervals[i]!, u = (time - times[i]!) / interval
    const u2 = u * u, u3 = u2 * u
    return (2 * u3 - 3 * u2 + 1) * values[i]! + (u3 - 2 * u2 + u) * interval * tangents[i]!
      + (-2 * u3 + 3 * u2) * values[i + 1]! + (u3 - u2) * interval * tangents[i + 1]!
  }
}

const cameraTimes = CAMERA_KEYS.map(key => key.time)
const positionTracks = [0, 1, 2].map(axis => createTrack(cameraTimes, CAMERA_KEYS.map(key => key.position[axis]!)))
const targetTracks = [0, 1, 2].map(axis => createTrack(cameraTimes, CAMERA_KEYS.map(key => key.target[axis]!)))
const energyTrack = createTrack([0, 16, 32, 38.5, 47.5, 54, 64, 72], [.08, .25, .45, .8, .86, .48, .85, 1])

export type AwakeningFilmSample = {
  time: number
  chapter: number
  deployment: number
  thrust: number
  scan: number
  energy: number
  warp: number
  camera: { position: Point3; target: Point3 }
}

export function sampleAwakeningFilm(time: number): AwakeningFilmSample {
  const t = clampFilmTime(time)
  // Explicit phase boundaries give exact 0/1 poses at the interlocks. There is
  // no epsilon-based ignition while the final armor stroke is still closing.
  const deployment = t <= 32 || t >= 54 ? 0
    : t < 38.5 ? smooth(32, 38.5, t)
      : t <= 47.5 ? 1 : 1 - smooth(47.5, 54, t)
  const thrust = deployment === 0 && t > 54 ? smooth(54, 60, t) : 0
  return {
    time: t,
    chapter: t < 16 ? 0 : t < 32 ? 1 : t < 54 ? 2 : 3,
    deployment,
    thrust,
    scan: smooth(0, 32, t),
    energy: Math.max(0, Math.min(1, energyTrack(t))),
    warp: smooth(64, AWAKENING_DURATION, t),
    camera: {
      position: positionTracks.map(sample => sample(t)) as Point3,
      target: targetTracks.map(sample => sample(t)) as Point3,
    },
  }
}
