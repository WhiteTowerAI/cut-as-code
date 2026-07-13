// themes.ts — 第 1 层:主题数据 + 开关。加一种新风格 = 往 THEMES 加一个条目。
// 组件与 anim 积木只读当前主题 T,不写死样式值。与 anim.tsx 的 ANCHOR 正交。
import { loadFont as loadArchivo } from "@remotion/google-fonts/Archivo";
import { loadFont as loadNewsreader } from "@remotion/google-fonts/Newsreader";
import { loadFont as loadSilkscreen } from "@remotion/google-fonts/Silkscreen";
import { loadFont as loadSpaceMono } from "@remotion/google-fonts/SpaceMono";
import { loadFont as loadTitillium } from "@remotion/google-fonts/TitilliumWeb";

export type ThemeName = "editorial" | "teal" | "almanac" | "dotgrid" | "apex";

// 小卡片(LowerThird/Stat/Keypoint)的实心底板;editorial 为 null(无卡片)。
// 尺寸用 u 单位(画布高度%),由 <Surface> 乘以 useUnit() 落地为像素——不写死 px。
export type CardStyle = {
  bg: string;
  borderColor: string;
  borderWidthU: number;             // 边宽(u)
  borderSide: "left" | "bottom";    // 强调边在左(LowerThird/Keypoint)或下(Stat)
  radiusU: number;                  // 圆角(u)
  shadow: string;
  // borderAll:整框细边(dotgrid 的发丝盒边),而非单侧强调边。设了此值时 <Surface> 用
  // borderColor/borderWidthU 画四边、并忽略组件传入的 side——这样 dotgrid 把黄色只留给那颗点,
  // 卡边是中性灰。不设(teal/almanac)→ 照旧走单侧强调边,逐帧零回归。
  borderAll?: boolean;
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
  // fontBody:正文/次要文字用的第二字族(dotgrid = Space Mono,与像素显示字 Silkscreen 分工)。
  // 不设→undefined→组件的 bodyFont() 回退到 T.font→单字族主题逐帧零回归。见 anim bodyFont。
  fontBody?: string;
  weight: { heavy: number; med: number; light: number };
  color: { text: string; textMuted: string; accent: string; scrimBase: string };
  card: CardStyle | null;
  scrimPlate?: ScrimPlate;   // 仅 card=null 主题用;有卡的主题(teal)留空。
  // fullBleed:全幅组件(片头/片尾/章节/列表)铺一层不透明底板(= color.scrimBase),
  // 画面被完全盖住——almanac 的"整屏标题接管"。深色主题不设此字段→undefined→假→照旧走
  // <Scrim> 渐变路径,逐帧零回归。见 anim.tsx 的 <Backdrop>。
  fullBleed?: boolean;
  rule: "bar" | "hairline" | "dot";
  // displayItalic:标题/数字/金句等"显示"角色用斜体(apex 的赛事重斜体);kicker/正文保持直立。
  // 不设→undefined→React 省略 fontStyle→非斜体主题零回归。见 anim dispItalic。
  displayItalic?: boolean;
  // listNumColors:ListReveal 列表序号按位置取色(apex 的功能性扇区色 紫/绿/黄)。越界或不设→
  // 回退到 T.color.accent(现状)。仅 ListReveal 读它。
  listNumColors?: string[];
  // ruleSkewDeg:强调条/片尾标记的 skewX 角度(apex = -18)。不设→不倾斜→零回归。见 anim Rule / Outro。
  ruleSkewDeg?: number;
  kicker: { case: "upper" | "none"; spacingEm: number; weight: number };
  motion: "fade" | "stagger";
  // 非标题元素(kicker/sub/小卡标签)入场的失焦半径(px):从 blurIn→0 聚焦,叠在淡入+上浮上做
  // "镜头对焦"揭示。仅 stagger 主题、且设了此值才生效;标题永不受影响(仍走 clipPath 擦入,不叠)。
  // 不设→undefined→filter 属性省略→teal/almanac 逐帧零回归。见 anim.tsx useEntrance。
  blurIn?: number;
  // pop:信息高光卡(Stat 数字 / LowerThird 名条)的 spring 弹入(带 bounce)。这是全仓唯一带回弹的
  // 动效,刻意与 stagger 家族的"纪录片不 bounce"分开——只有 opt-in 此字段的主题才弹。不设(teal/almanac)
  // → usePop 返回 1 → 无缩放 → 逐帧零回归。config 传给 spring();fromScale 是起始缩放(如 0.7→1)。
  pop?: { config: { damping: number; stiffness?: number; mass?: number; overshootClamping?: boolean }; fromScale: number };
};

// editorial 用 Archivo(顶层加载;只有被选中的主题真正用到其 family)。
const archivo = loadArchivo();
const ARCHIVO = `${archivo.fontFamily}, system-ui, sans-serif`;

// almanac 用 Newsreader(Google Fonts 免费)——一款克制、偏窄、适合正文标题的"报道体"衬线。
// 若日后要换成某个自托管专有衬线体,只改这一行的加载与 family 即可(注意其许可)。
// 与 anim.tsx 里 teal 的 "serif" 不同,这里显式加载真实字族,避免落到系统 Georgia。
const newsreader = loadNewsreader();
const NEWSREADER = `${newsreader.fontFamily}, Georgia, "Times New Roman", serif`;

// dotgrid 用两款:Silkscreen(点阵像素体,免费,≈ Nothing 私有 NDot 的替身)做显示字;
// Space Mono(等宽,≈ NType 82 Mono 的替身)做正文。apex 用 Titillium Web(免费替身——
// 真实赛事字体私有且其品牌指南禁止第三方关联使用;loadFont() 不带参数会加载全部字重与斜体)。
const silkscreen = loadSilkscreen();
const SILKSCREEN = `${silkscreen.fontFamily}, "Courier New", monospace`;
const spacemono = loadSpaceMono();
const SPACEMONO = `${spacemono.fontFamily}, ui-monospace, monospace`;
const titillium = loadTitillium();
const TITILLIUM = `${titillium.fontFamily}, system-ui, sans-serif`;

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
  // 副标题/kicker/small 失焦→聚焦揭示(纪录片"对焦"感,不带 bounce)。标题仍走 clipPath 擦入,不叠。
  // 只有叙事书挡(Intro/Outro)的次要文字用它;信息卡(名条/数字/金句/列表)保持即时清晰。见 anim useEntrance。
  blurIn: 24,
  // Stat 数字卡 / LowerThird 名条的 spring 弹入(带回弹)。damping:9 → 明显过冲再落定。见 anim usePop。
  pop: { config: { damping: 9 }, fromScale: 0.7 },
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

// dotgrid — "点阵实用主义"卡片语言:像素显示字(Silkscreen)+ 等宽正文(Space Mono)+
// 纯黑白 + 严格克制的一点黄(#FFE600,只给片头/章节标题下那颗方点与列表序号)。整屏黑接管
// (fullBleed),小卡是近黑透明底 + 中性发丝盒边(borderAll,黄色不上边框,只留给那颗点)。
// 灵感与色值来自 refs2/nothing 的真实产品卡研究;Silkscreen 只有 400/700 两档字重。
const dotgrid: Theme = {
  name: "dotgrid",
  font: SILKSCREEN,
  fontBody: SPACEMONO,
  weight: { heavy: 700, med: 400, light: 400 },   // Silkscreen 仅 400/700;med/light 都落 400
  color: { text: "#F4F4F2", textMuted: "#8C8C90", accent: "#FFE600", scrimBase: "#0A0A0B" },
  card: {
    bg: "rgba(10,10,11,0.92)",
    borderColor: "#2A2A2E",      // 中性灰盒边(不是黄!黄只留给那颗点)
    borderWidthU: 0.2,
    borderSide: "left",          // borderAll 生效时此值被忽略,仅为满足类型
    borderAll: true,
    radiusU: 0,                  // 0 圆角(像素直角)
    shadow: "none",
  },
  fullBleed: true,               // 全幅组件铺不透明黑底(整屏接管)——见 anim <Backdrop>
  rule: "dot",                   // 那颗克制的黄方点
  kicker: { case: "upper", spacingEm: 0.16, weight: 400 },
  motion: "fade",
};

// apex — "赛事遥测"卡片语言:重斜体显示字(Titillium Web)+ 碳黑底 + 严格克制的红(#E10600)+
// 功能性扇区色列表序号(紫/绿/黄,呼应赛车三段计时)+ 斜切强调条。碳卡半透 + 红色左强调边。
// 非 fullBleed:走 Scrim 渐变,画面透气。灵感与色值来自 refs2/f1 的真实转播帧研究。
const apex: Theme = {
  name: "apex",
  font: TITILLIUM,
  displayItalic: true,           // 标题/数字/金句斜体;kicker/正文直立
  weight: { heavy: 900, med: 600, light: 600 },
  color: { text: "#FFFFFF", textMuted: "#B0B0B8", accent: "#E10600", scrimBase: "#15151E" },
  card: {
    bg: "#1F1F2A",
    borderColor: "#E10600",
    borderWidthU: 1.2,
    borderSide: "left",
    radiusU: 0.6,
    shadow: "0 6px 24px rgba(0,0,0,0.5)",
  },
  rule: "bar",
  ruleSkewDeg: -18,              // 斜切强调条/片尾标记
  listNumColors: ["#B300B3", "#00D06E", "#FFD500"],   // 功能性扇区色:紫/绿/黄
  kicker: { case: "upper", spacingEm: 0.22, weight: 700 },
  motion: "fade",
};

export const THEMES: Record<ThemeName, Theme> = { editorial, teal, almanac, dotgrid, apex };

// —— 唯一的风格开关。改这一行切换整套外观。——
export const THEME: ThemeName = "almanac";

export const T: Theme = THEMES[THEME];
