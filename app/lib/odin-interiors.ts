// Verified concept information and media from RSI and Star Citizen Live.
// Claim-level sources and media provenance: docs/review/v0.18.0/sources.json.
export interface OdinInteriorImage {
  src: string
  width: number
  height: number
  zh: string
  en: string
  source: string
  timestamp?: string
  // Pixel bounds within the untouched source, used by both thumbnail and lightbox.
  crop?: { x: number; y: number; width: number; height: number }
}

export interface OdinInteriorSection {
  zh: { body: string; specs: string[] }
  en: { body: string; specs: string[] }
  images: OdinInteriorImage[]
}

export const INTERIOR_SECTIONS: Record<'torpedoes' | 'bridge' | 'aft', OdinInteriorSection> = {
  torpedoes: {
    zh: {
      body: '主炮后方设有 S12 垂直发射系统。备用鱼雷经货舱输送带送至控制室，由船员装填。',
      specs: ['20 个 S12 发射筒', '约 40 枚待装填鱼雷（概念）', '可从货舱继续补充备用弹药'],
    },
    en: {
      body: 'S12 vertical launch tubes sit behind the main battery. Spare torpedoes travel from the cargo hold to the control room by conveyor for manual loading.',
      specs: ['20 S12 launch tubes', 'About 40 torpedoes queued for loading (concept)', 'Additional reloads supplied from the cargo hold'],
    },
    images: [
      {
        src: '/images/odin-interiors/torpedo-conveyor.webp', width: 1105, height: 622,
        zh: '鱼雷输送与装填区域。输送带将备用鱼雷送到控制室。',
        en: 'Torpedo transport and loading area. The conveyor brings reloads to the control room.',
        source: 'https://www.youtube.com/watch?v=CFoQp6wRjPo&t=1412s', timestamp: '23:32',
        crop: { x: 16, y: 12, width: 1024, height: 576 },
      },
    ],
  },
  bridge: {
    zh: {
      body: '舰桥下方规划有食堂、医院和船员舱室。战术室与简报空间用于舰队协调和船员集合。',
      specs: ['舰桥与火控分区', '舰内循环轨道交通', '医院与生活区域仍处概念设计'],
    },
    en: {
      body: 'A mess hall, hospital and crew quarters are planned below the bridge. Tactical and briefing spaces support fleet coordination and crew gatherings.',
      specs: ['Separate bridge and fire-control areas', 'Ship-wide tram loop', 'Medical and living areas remain in concept design'],
    },
    images: [
      {
        src: '/images/odin-interiors/bridge-command.webp', width: 1106, height: 622,
        zh: '舰桥指挥平台；舰长席位位于前方中央。',
        en: 'Bridge command platform, with the captain positioned at the front center.',
        source: 'https://www.youtube.com/watch?v=CFoQp6wRjPo&t=2124s', timestamp: '35:24',
        crop: { x: 16, y: 12, width: 1024, height: 576 },
      },
      {
        src: '/images/odin-interiors/briefing-room.webp', width: 2400, height: 1350,
        zh: '供船员集合、讨论行动计划的简报室。',
        en: 'The briefing room provides space for crew gatherings and operational planning.',
        source: 'https://media.robertsspaceindustries.com/seyogl9pfjzgz/source.jpg',
      },
      {
        src: '/images/odin-interiors/schematic-overview.webp', width: 3600, height: 1204,
        zh: '官方剖面图标出食堂、医院和船员舱室的位置；这些区域当时尚未完成内部设计。',
        en: 'The official cutaway locates the mess hall, hospital and crew quarters, whose interiors were still being designed.',
        source: 'https://media.robertsspaceindustries.com/6lpt2i7q80sdz/source.jpg',
      },
    ],
  },
  aft: {
    zh: {
      body: '中央机库与六座侧机库连通，便于回收、补给和再次出动。多引擎布局以巡洋舰速度为设计目标，并分散推进负载。',
      specs: ['6 个小型机库 + 1 个中型机库', '中型机库 68 × 100 × 44 米（概念）', '6000 SCU 主货舱 + 2000 SCU 升降平台', '机库支持维修、加油与换装'],
    },
    en: {
      body: 'The central hangar connects to six side hangars for recovery, servicing and relaunch. Multiple engines distribute thrust, with cruiser speed as a design goal.',
      specs: ['6 small hangars + 1 medium hangar', 'Medium hangar: 68 × 100 × 44 m (concept)', '6000 SCU main hold + 2000 SCU cargo lift', 'Hangar repair, refueling and rearming'],
    },
    images: [
      {
        src: '/images/odin-interiors/hangar-cargo-deck.webp', width: 2400, height: 1350,
        zh: '中央机库、两侧小型机库与后方的货物升降平台。',
        en: 'The central hangar, small hangars on either side and the cargo lift at the rear.',
        source: 'https://media.robertsspaceindustries.com/d8q6m2h9ecdeo/source.jpg',
      },
    ],
  },
}
