// themes.ts — 第 1 层:主题数据 + 开关。加一种新风格 = 往 THEMES 加一个条目。
// 组件与 anim 积木只读当前主题 T,不写死样式值。与 anim.tsx 的 ANCHOR 正交。
import { loadFont as loadArchivo } from "@remotion/google-fonts/Archivo";

export type ThemeName = "editorial" | "teal";

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

export type Theme = {
  name: ThemeName;
  font: string;
  weight: { heavy: number; med: number; light: number };
  color: { text: string; textMuted: string; accent: string; scrimBase: string };
  card: CardStyle | null;
  rule: "bar" | "hairline";
  kicker: { case: "upper" | "none"; spacingEm: number };
  motion: "fade" | "stagger";
};

// editorial 用 Archivo(顶层加载;只有被选中的主题真正用到其 family)。
const archivo = loadArchivo();
const ARCHIVO = `${archivo.fontFamily}, system-ui, sans-serif`;

const editorial: Theme = {
  name: "editorial",
  font: ARCHIVO,
  weight: { heavy: 800, med: 600, light: 500 },
  color: { text: "#F4F1EA", textMuted: "#C7C2B6", accent: "#E0B252", scrimBase: "#0B0D10" },
  card: null,
  rule: "hairline",
  kicker: { case: "upper", spacingEm: 0.28 },
  motion: "stagger",
};

// teal 复刻今天的常量,确保零回归(数值取自现 anim.tsx 与各组件)。
const teal: Theme = {
  name: "teal",
  font: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
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
  kicker: { case: "upper", spacingEm: 0.04 },
  motion: "fade",
};

export const THEMES: Record<ThemeName, Theme> = { editorial, teal };

// —— 唯一的风格开关。改这一行切换整套外观。——
export const THEME: ThemeName = "editorial";

export const T: Theme = THEMES[THEME];
