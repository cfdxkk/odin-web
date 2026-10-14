import type { TourId } from './odin-tour'

export type OdinLocale = 'zh' | 'en'
export function resolveOdinLocale(value: string | null | undefined): OdinLocale { return value === 'en' ? 'en' : 'zh' }
export const SITE_COPY = {
  zh: {
    pageTitle: 'ODIN — 舰体与武备图册', description: 'Anvil Odin 战列巡洋舰的交互式粉丝图册。分章节探索舰体与武备，浏览官方概念艺术。',
    home: 'ODIN 首页', brandSub: 'Anvil / 舰船研究', navLabel: '主导航', navTour: '舰船导览', navArt: '概念艺术', navAbout: '创作与来源',
    language: '选择语言', languageName: '中文', switchLanguage: '切换为英文', independent: '独立项目', fanArt: '非官方 · 粉丝作品',
    guide: '舰船图册', guideSub: '舰体 · 武备 · 结构', chapter: '章节', chapterNav: '章节索引', previousChapter: '上一章节', nextChapter: '下一章节', scrollHint: '向下滚动，逐章查看',
    vehicleClass: '战列巡洋舰', manufacturer: 'Anvil Aerospace', overviewLine: '近距离，了解奥丁。', document: '舰船图册', realTime: '实时三维模型', thisSideUp: '此面向上', stow: '收纳 84S',
    loading: '正在载入', loadingModel: '正在加载三维模型', unavailable: '场景不可用', errorTitle: '三维场景暂时无法启动', errorBody: '请使用支持 WebGL 2 的浏览器，并启用硬件加速。', reload: '重新载入', errorDetails: '错误详情',
    canvasLabel: 'Odin 战列巡洋舰实时三维展示；自由视角时可左键旋转、右键平移、滚轮缩放', manual: '自由视角', returnGuide: '返回导览镜头', controlsHint: '左键旋转 · 右键平移 · 滚轮缩放',
    changingView: '正在切换视角', paused: '已暂停', playing: '自动播放', manualView: '自由视角', navConfig: 'NAV / 航行配置', scmConfig: 'SCM / 战斗配置', config: '配置', switchNav: 'NAV 航行配置', switchScm: 'SCM 战斗配置',
    photo: '拍照', capturing: '正在导出', play: '播放动画', pause: '暂停动画', animationTime: '动画时间', sequence: '武备展开与收起', highQuality: '高画质', lowQuality: '流畅', enableHigh: '开启高画质', enableLow: '开启流畅模式',
    exterior: '舰船外观', combat: '武备展开', navigation: '武备收起', shortcuts: '空格 / 暂停 · R / 复位', guideStatus: '导览镜头', detailMode: '动作查看', viewArchive: '进入概念图画廊', sourceConcept: 'RSI 官方概念与资料',
    conceptNotice: '本图册为粉丝制作。舰船配置以 RSI 官方最终发布为准。', artArchive: '官方壁纸', artTitle: '概念艺术', artBody: 'RSI 官方横版舰船壁纸。',
    artSource: '查看官方页面', previousArt: '上一张艺术图', nextArt: '下一张艺术图', selectArt: '查看艺术图', artThumbnails: '艺术图缩略图索引', originalArt: '查看原始图片', gallery: '官方概念艺术画廊',
    artCategory: '分类', footerTag: '图册 / 完', footerTitle: '感谢来访', footerThanks: '感谢来访。', footerCreator: '制作 / cfdxkk', footerBody: '感谢每一位帮助完善这份图册的人。',
    footerTour: '舰船导览', footerProject: '关于项目', footerSources: '官方资料', footerTop: '返回舰船总览', footerMain: '主炮组', footerSecondary: '副炮与舰桥', footerBridge: '舰桥与武备', footerPropulsion: '推进系统', footerGallery: '概念艺术图',
    review: '武备动画预览', sourceNotes: '创作与来源', community: 'Star Citizen 社区', founder: 'Odin 创始人俱乐部勋章',
    legal: '独立粉丝艺术项目，与 Cloud Imperium Games 无隶属关系。Star Citizen、Anvil、Odin 及官方概念艺术的权利归各自权利人所有。',
    communityAlt: 'Star Citizen 社区制作徽章', footerImageAlt: '细密网点印刷的 Odin 与群山', edition: '版本 020.0', end: '图册结束',
    aboutTitle: '关于这份图册', aboutIntro: '本项目基于 Odin 模型制作，展示舰体结构，并补充武备展开、收起与推进器效果。模型的机构动画由页面实时驱动。',
    aboutDesign: '全屏模型配合四段介绍，武备段可连续滚动，沿舰体查看并环绕各项武器。悬停官方视频即可播放，自由视角支持透明背景拍照。页尾采用黑底印刷风格的舰船与群山插画。',
    closeAbout: '关闭创作说明', projectNotes: '项目说明', inspiration: '动画灵感 / Space Tech', developerShow: '官方开发者展示 / Star Citizen Live', shipSource: '舰船概念与资料 / RSI', badgeSource: '网站徽章 / Odin 创始人俱乐部勋章', nasaSource: '页脚参考 / NASA 规范手册', starfieldSource: '界面参考 / 星空官方展示', modelNotice: '粉丝艺术外观模型，非官方生产级模型。',
    reviewTitle: '武备与舰桥', reviewKicker: '机构预览', returnSite: '返回舰船导览', reviewCanvas: 'Odin 武备动画预览，左键旋转、右键平移、滚轮缩放', reviewSelect: '查看部位', reviewLoading: '正在载入高精度模型', reviewPlay: '播放展开 / 收回', reviewNav: 'NAV / 完全收起', reviewScm: 'SCM / 完全展开', reviewProgress: '武备展开进度',
    angleOblique: '斜视', angleSide: '侧视', angleTop: '俯视', angleFront: '正视', single: '单联装', twin: '双联装', quad: '四联装', starboard: '右舷', port: '左舷', bow: '舰艏', stern: '舰艉', keel: '舰腹', seam: '接缝', hullCover: '船壳盖板', bridge: '舰桥', front: '前部', rear: '后部', paint: '底部涂装', mainGun: '主炮', hullSeam: '船体接缝', radar: '雷达与桁架', glass: '下层玻璃', upperArmor: '上方五块护甲', lowerArmor: '下方五块护甲',
  },
  en: {
    pageTitle: 'ODIN — Vehicle & Armament Study', description: 'An interactive fan study of the Anvil Odin battlecruiser. Explore its hull and armament chapter by chapter, then browse the official concept artwork.',
    home: 'ODIN home', brandSub: 'Anvil / Vehicle Study', navLabel: 'Main navigation', navTour: 'Vehicle tour', navArt: 'Concept art', navAbout: 'Project & sources',
    language: 'Choose language', languageName: 'English', switchLanguage: 'Switch to Chinese', independent: 'Independent project', fanArt: 'Unofficial fan study',
    guide: 'Vehicle field guide', guideSub: 'Hull / Armament / Structure', chapter: 'Chapter', chapterNav: 'Chapter index', previousChapter: 'Previous chapter', nextChapter: 'Next chapter', scrollHint: 'Scroll to explore, chapter by chapter',
    vehicleClass: 'Battlecruiser', manufacturer: 'Anvil Aerospace', overviewLine: 'A closer look at Odin.', document: 'Vehicle study', realTime: 'Real-time 3D model', thisSideUp: 'This side up', stow: 'STOW 84S',
    loading: 'Loading', loadingModel: 'Loading the 3D model', unavailable: 'Display unavailable', errorTitle: 'The 3D scene could not start', errorBody: 'Use a WebGL 2 browser with hardware acceleration enabled.', reload: 'Reload', errorDetails: 'Error details',
    canvasLabel: 'Live 3D view of the Odin battlecruiser. In free view, drag to orbit, right-drag to pan and scroll to zoom.', manual: 'Free view', returnGuide: 'Return to guided view', controlsHint: 'Drag to orbit / Right-drag to pan / Scroll to zoom',
    changingView: 'Changing view', paused: 'Paused', playing: 'Autoplay', manualView: 'Free view', navConfig: 'NAV / Navigation', scmConfig: 'SCM / Combat', config: 'Configuration', switchNav: 'NAV / Navigation', switchScm: 'SCM / Combat',
    photo: 'Photo', capturing: 'Exporting', play: 'Play animation', pause: 'Pause animation', animationTime: 'Animation time', sequence: 'Deploy & stow', highQuality: 'High quality', lowQuality: 'Low power', enableHigh: 'Enable high quality', enableLow: 'Enable low power',
    exterior: 'Exterior', combat: 'Deploy armament', navigation: 'Stow armament', shortcuts: 'SPACE / Pause · R / Reset', guideStatus: 'Guided view', detailMode: 'Articulation sequence', viewArchive: 'Continue to the art archive', sourceConcept: 'Official RSI concept & specifications',
    conceptNotice: 'An independent fan study. Final ship specifications are subject to RSI releases.', artArchive: 'Official wallpapers', artTitle: 'Concept art', artBody: 'Landscape ship wallpapers from RSI.',
    artSource: 'Visit the official page', previousArt: 'Previous artwork', nextArt: 'Next artwork', selectArt: 'View artwork', artThumbnails: 'Artwork thumbnail index', originalArt: 'View original image', gallery: 'Official concept art gallery',
    artCategory: 'Category', footerTag: 'End of field guide', footerTitle: 'Thank you', footerThanks: 'Thanks for visiting.', footerCreator: 'Created by cfdxkk', footerBody: 'Thank you to everyone who helped bring this study of Odin to life.',
    footerTour: 'Explore', footerProject: 'The project', footerSources: 'Official sources', footerTop: 'Vehicle overview', footerMain: 'Main batteries', footerSecondary: 'Secondary guns & bridge', footerBridge: 'Bridge & armament', footerPropulsion: 'Propulsion', footerGallery: 'Concept artwork',
    review: 'Articulation review', sourceNotes: 'Project & sources', community: 'Star Citizen community', founder: 'Odin Founders Club badge',
    legal: 'An independent fan art project, unaffiliated with Cloud Imperium Games. Star Citizen, Anvil, Odin and official concept artwork belong to their respective rights holders.',
    communityAlt: 'Star Citizen Made by the Community badge', footerImageAlt: 'Odin among mountains, printed with a fine halftone screen', edition: 'Edition 020.0', end: 'End of document',
    aboutTitle: 'About this field guide', aboutIntro: 'Based on the Odin model, this study presents the hull structure, weapon deployment and stowage, and engine effects. The page drives the articulation in real time.',
    aboutDesign: 'A full-screen model accompanies four chapters. Continuous scrolling moves along and around the ship during weapon inspection. Hover official clips to play them, or export a transparent image in free view. The footer uses a dark print illustration of the ship and mountains.',
    closeAbout: 'Close project notes', projectNotes: 'Project notes', inspiration: 'Animation inspiration / Space Tech', developerShow: 'Official developer presentation / Star Citizen Live', shipSource: 'Ship concept & specifications / RSI', badgeSource: 'Site emblem / Odin Founders Club badge', nasaSource: 'Footer reference / NASA Graphics Standards Manual', starfieldSource: 'Interface reference / Starfield official reveal', modelNotice: 'Fan art exterior model, not an official production model.',
    reviewTitle: 'Armament & bridge', reviewKicker: 'Articulation review', returnSite: 'Return to vehicle tour', reviewCanvas: 'Odin articulation review. Drag to orbit, right-drag to pan, scroll to zoom.', reviewSelect: 'Inspect station', reviewLoading: 'Loading the detailed model', reviewPlay: 'Play deploy / stow', reviewNav: 'NAV / Fully stowed', reviewScm: 'SCM / Fully deployed', reviewProgress: 'Armament deployment',
    angleOblique: 'Oblique', angleSide: 'Side', angleTop: 'Top', angleFront: 'Front', single: 'Single gun', twin: 'Twin guns', quad: 'Quad guns', starboard: 'Starboard', port: 'Port', bow: 'Bow', stern: 'Stern', keel: 'Keel', seam: 'Seam', hullCover: 'Hull cover', bridge: 'Bridge', front: 'Forward', rear: 'Aft', paint: 'Lower paintwork', mainGun: 'Main gun', hullSeam: 'Hull seam', radar: 'Radar & trusses', glass: 'Lower glazing', upperArmor: 'Five upper armor panels', lowerArmor: 'Five lower armor panels',
  },
} as const

type ChapterCopy = { label: string; title: string; body?: string; specs: [string, string][] }
export const CHAPTER_COPY: Record<OdinLocale, Record<TourId, ChapterCopy>> = {
  zh: {
    overview: { label: '舰船总览', title: 'ODIN', specs: [] },
    batteries: { label: '武备导览', title: '武备导览', specs: [] },
    bridge: { label: '舰桥', title: '舰桥', body: '高位舰桥提供开阔视野，观察窗上方布置雷达与桁架结构。', specs: [['观察位置', '上层舰桥'], ['顶部结构', '雷达与桁架']] },
    engines: { label: '后部舰体', title: '后部舰体', body: '从舰桥下方延伸至舰艉，可以看到分层的舰体结构与主推进器布局。', specs: [['配置', 'NAV'], ['观察位置', '侧后方']] },
  },
  en: {
    overview: { label: 'Vehicle overview', title: 'ODIN', specs: [] },
    batteries: { label: 'Armament tour', title: 'Armament tour', specs: [] },
    bridge: { label: 'Bridge', title: 'Bridge', body: 'An elevated bridge provides a clear view over the hull. Radar and truss structures sit above the observation windows.', specs: [['View', 'Upper bridge'], ['Upper structure', 'Radar & trusses']] },
    engines: { label: 'Aft hull', title: 'Aft hull', body: 'The rear quarter reveals the layered hull and main engine layout beneath the bridge.', specs: [['Configuration', 'NAV'], ['View', 'Rear quarter']] },
  },
}
