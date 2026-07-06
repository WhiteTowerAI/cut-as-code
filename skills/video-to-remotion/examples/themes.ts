// themes.ts — 第 1 层:主题数据 + 开关。加一种新风格 = 往 THEMES 加一个条目。
// 组件与 anim 积木只读当前主题 T,不写死样式值。与 anim.tsx 的 ANCHOR 正交。
import { loadFont as loadArchivo } from "@remotion/google-fonts/Archivo";
import { loadFont as loadNewsreader } from "@remotion/google-fonts/Newsreader";

export type ThemeName = "editorial" | "teal" | "almanac";

// 小卡片(LowerThird/Stat/Keypoint)的实心底板;editorial 为 null(无卡片)。
// 尺寸用 u 单位(画布高度%),由 <Surface> 乘以 useUnit() 落地为像素——不写死 px。
export type CardStyle = {
  bg: string;
  borderColor: string;
  borderWidthU: number;             // 边宽(u)
  borderSide: "left" | "bottom";    // 强调边在左(LowerThird/Keypoint)或下(Stat)
  radiusU: number;                  // 圆角(u)
  shadow: string;
};

// scrimPlate:card=null 的主题(如 editorial)给"小组件"(名条/数字/金句)文字底下
// 垫的一层局部半透暗板。全宽组件(片头/章节/列表/片尾)用整条 Scrim,不需要它。
// 为什么需要:实测无卡+全宽 scrim 在高光画面上小组件文字对比度仅 ~1.2-2:1(看不清),
// 违反"任意画面可读"铁律;局部暗板贴着文字,实测 5.7:1 过 WCAG。<Surface> 在
// T.card===null 且 scrimPlate 有值时渲染它——只有用 <Surface> 的 3 个小组件会命中。
export type ScrimPlate = {
  bg: string;        // 半透暗色(如 rgba(11,13,16,0.62))
  radiusU: number;   // 圆角(u)
};

export type Theme = {
  name: ThemeName;
  font: string;
  weight: { heavy: number; med: number; light: number };
  color: { text: string; textMuted: string; accent: string; scrimBase: string };
  card: CardStyle | null;
  scrimPlate?: ScrimPlate;   // 仅 card=null 主题用;有卡的主题(teal)留空。
  // fullBleed:全幅组件(片头/片尾/章节/列表)铺一层不透明底板(= color.scrimBase),
  // 画面被完全盖住——almanac 的"整屏标题接管"。深色主题不设此字段→undefined→假→照旧走
  // <Scrim> 渐变路径,逐帧零回归。见 anim.tsx 的 <Backdrop>。
  fullBleed?: boolean;
  rule: "bar" | "hairline";
  kicker: { case: "upper" | "none"; spacingEm: number; weight: number };
  motion: "fade" | "stagger";
};

// editorial 用 Archivo(顶层加载;只有被选中的主题真正用到其 family)。
const archivo = loadArchivo();
const ARCHIVO = `${archivo.fontFamily}, system-ui, sans-serif`;

// almanac 用 Newsreader(Google Fonts 免费)——一款克制、偏窄、适合正文标题的"报道体"衬线。
// 若日后要换成某个自托管专有衬线体,只改这一行的加载与 family 即可(注意其许可)。
// 与 anim.tsx 里 teal 的 "serif" 不同,这里显式加载真实字族,避免落到系统 Georgia。
const newsreader = loadNewsreader();
const NEWSREADER = `${newsreader.fontFamily}, Georgia, "Times New Roman", serif`;

const editorial: Theme = {
  name: "editorial",
  font: ARCHIVO,
  weight: { heavy: 800, med: 600, light: 500 },
  color: { text: "#F4F1EA", textMuted: "#C7C2B6", accent: "#E0B252", scrimBase: "#0B0D10" },
  card: null,
  // 无实心卡,但小组件文字底下垫一层局部暗板保证任意画面可读(实测 5.7:1)。
  scrimPlate: { bg: "rgba(11,13,16,0.62)", radiusU: 0.8 },
  rule: "hairline",
  kicker: { case: "upper", spacingEm: 0.28, weight: 600 },
  motion: "stagger",
};

// teal 复刻今天的常量,确保零回归(数值取自现 anim.tsx 与各组件)。
const teal: Theme = {
  name: "teal",
  // font 必须是 "serif":旧组件从不设 fontFamily,浏览器默认用衬线体渲染文字,
  // 所以"今天的 teal 外观"实际是衬线体(Windows 上 = Times New Roman)。迁移后
  // 组件显式设 fontFamily: T.font,唯有 "serif" 能逐帧复刻旧样子(已验证 0 像素差)。
  // 不要改成 sans-serif/system-ui——那会让 teal 文字变无衬线,破坏零回归铁律。
  font: "serif",
  weight: { heavy: 800, med: 600, light: 500 },
  color: { text: "#F5F8F9", textMuted: "#B7C6CE", accent: "#26CAA8", scrimBase: "#0C141C" },
  card: {
    bg: "rgba(12,20,28,0.82)",
    borderColor: "#26CAA8",
    borderWidthU: 0.8,
    borderSide: "left",
    radiusU: 1.2,
    shadow: "0 6px 24px rgba(0,0,0,0.4)",
  },
  rule: "bar",
  kicker: { case: "upper", spacingEm: 0.1538, weight: 700 },   // = 旧 letterSpacing u*0.4 / fontSize u*2.6
  motion: "fade",
};

// almanac — 暖奶油"出版物"卡片语言:奶油卡 + 近黑衬线墨字 + 陶土珊瑚强调 + 追踪大写
// kicker + 整屏衬线标题接管。灵感与色值来自一段发布视频的截帧研究
// (docs/design-research/…/launch-video/cards),珊瑚强调用陶土色 #C15F3C
// (名条上采样偏暖 ~#C46B4C,以此值为准)。极性与深色主题相反:
// 深色主题 = 暗卡/亮字骑 Scrim;almanac = 奶油卡/暗字 + fullBleed 整屏接管。
const almanac: Theme = {
  name: "almanac",
  font: NEWSREADER,
  weight: { heavy: 600, med: 500, light: 400 },   // 衬线尺度——800 对显示衬线太重
  color: {
    text: "#14120E",       // 近黑墨字(取自标题 bumper 文字)
    textMuted: "#5C574E",  // 暖灰,用于 line2 / 标签
    accent: "#C15F3C",     // 陶土珊瑚强调
    scrimBase: "#F9F7F3",  // 暖奶油——almanac 的 fullBleed 底板色;深色主题此字段是暗 scrim 色
  },
  card: {                  // 小组件(名条/数字/金句)的实心奶油卡 + 珊瑚左边
    bg: "#F9F7F3",
    borderColor: "#C15F3C",
    borderWidthU: 0.9,
    borderSide: "left",
    radiusU: 1.0,
    shadow: "0 10px 30px rgba(0,0,0,0.28)",   // 在深色画面上柔和抬起
  },
  rule: "bar",             // 珊瑚短强调条(视频里的短 accent bar)
  kicker: { case: "upper", spacingEm: 0.18, weight: 600 },  // 追踪大写珊瑚 kicker
  motion: "stagger",       // 分部依次入场,不是一次平淡淡入
  fullBleed: true,         // 全幅组件铺不透明奶油底板(整屏接管)——见 anim.tsx <Backdrop>
};

export const THEMES: Record<ThemeName, Theme> = { editorial, teal, almanac };

// —— 唯一的风格开关。改这一行切换整套外观。——
export const THEME: ThemeName = "almanac";

export const T: Theme = THEMES[THEME];
