# video-to-remotion 可扩展主题系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `skills/video-to-remotion/` 加一套 token 驱动的可扩展主题系统:一个 `THEME` 开关从 `THEMES` 表选出当前主题,共享积木读主题、7 个图形组件与主题解耦;首发两个主题 `editorial`(新纪录片风)与 `teal`(现状,零回归)。

**Architecture:** 三层 —— 第 1 层 `themes.ts`(主题数据 + 开关,加风格只动这里);第 2 层 `anim.tsx`(共享积木 `<Surface>/<Rule>/<Kicker>` + 动画 hooks,全部读当前主题 `T`);第 3 层 `components/*.tsx`(只管布局与锚定,样式值来自积木)。cue sheet 字段与 `ANCHOR` 开关都不变,主题与锚点正交。

**Tech Stack:** Remotion 4.x(React/TypeScript)、`@remotion/google-fonts`、ffmpeg。验证靠 `tsc --noEmit` + `npx remotion still` 抽帧,无单元测试框架。

## Global Constraints

以下为项目级约束,**每个任务隐含包含**(值逐字取自 spec 与仓库 CLAUDE.md):

- **React 锁 `18.3.1`**、`react-dom` 锁 `18.3.1`(不得被 npm 拉到 19)。
- **Remotion 锁一个 4.x**(本计划用 `4.0.230`);`@remotion/google-fonts` 用**同一** 4.x 版本。
- **三条不可动摇规则**,每个主题都必须成立:① 卡片/遮罩自带背景,任意画面可读;② 沿用 `ANCHOR`,锚定到边不挡脸(默认 bottom);③ 尺寸用 `useUnit()`(画布高度百分比),不写死像素。
- **`teal` 零回归**:切到 `teal` 时逐帧等于改动前;7 个组件各自的入场动画**原样保留**,不得压平成单一动画。
- **无胶片颗粒**(已决定)。editorial 质感只靠字体/字距/细金线/暖色调。
- **editorial 不用 bounce**:入场统一用现有克制的 `EASE_OUT`。
- **cue sheet 字段不变**:`line1/line2`、`kicker/title`、`value/label`、`items` 保持;`FinalEdit.tsx`/`Root.tsx`/`reference/graphic-types.md` 不改。
- **Windows/PowerShell 开发**:命令给 Bash 工具(POSIX)版本;`npx` 命令跨平台一致。
- **`work/` 为可弃中间物**,已 gitignore;真身是 `skills/video-to-remotion/examples/` 下的文件。

## 验证策略(为何不是传统 TDD)

`examples/*.tsx` 是**拷进真实 Remotion 项目**才能编译的样板,repo 里没有可独立跑的项目、也没有测试框架。因此每个任务的"红-绿"是:

1. **红**:改动前 `tsc --noEmit` 因引用未定义符号报错,或抽帧显示旧样子(基线)。
2. **绿**:改动后 `tsc --noEmit` 通过,抽帧显示预期样子。

Task 1 一次性搭一个 **gitignored 验证脚手架** `work/theme-harness/`(提供 package.json/tsconfig/entry/demo composition),后续每个任务用它做 `tsc` + 抽帧。编辑始终发生在 `examples/`,验证前用一条 `cp` 把最新 `examples` 同步进脚手架 `src/`。

---

## File Structure

改动落点(真身)在 `skills/video-to-remotion/`:

| 文件 | 职责 | 本计划 |
|---|---|---|
| `examples/themes.ts` | 第 1 层:`Theme` 类型、`THEMES` 表、`THEME` 开关、当前主题 `T`、字体加载 | **新建**(Task 2) |
| `examples/anim.tsx` | 第 2 层:计时/缓动/`useUnit`/anchor 助手/`Scrim`(保留)+ 积木 `<Surface>/<Rule>/<Kicker>` + hooks `useEntrance/useDraw/useClipReveal` | 改(Task 3/4/5、Task 13 清理) |
| `examples/components/LowerThird.tsx` | 卡片类:实体名条 | 改(Task 6) |
| `examples/components/StatCallout.tsx` | 卡片类:数字 callout | 改(Task 7) |
| `examples/components/KeypointCallout.tsx` | 卡片类:金句 | 改(Task 8) |
| `examples/components/SectionCard.tsx` | scrim 类:章节卡 | 改(Task 9) |
| `examples/components/Intro.tsx` | scrim 类:片头 | 改(Task 10) |
| `examples/components/Outro.tsx` | scrim 类:片尾 | 改(Task 11) |
| `examples/components/ListReveal.tsx` | scrim 类:列表 | 改(Task 12) |
| `SKILL.md` | 记 `THEME` 开关、依赖、加主题配方、新自检项 | 改(Task 13) |
| `work/theme-harness/**` | gitignored 验证脚手架 | 新建(Task 1) |

`FinalEdit.tsx`、`Root.tsx`、`reference/graphic-types.md`、脚本 `*.py` **不改**。

---

## Task 1: 验证脚手架 + teal 基线快照

**Files:**
- Create: `work/theme-harness/package.json`
- Create: `work/theme-harness/tsconfig.json`
- Create: `work/theme-harness/src/index.ts`
- Create: `work/theme-harness/src/Root.tsx`
- Create: `work/theme-harness/src/DemoAll.tsx`
- Create: `work/theme-harness/.gitignore`
- Sync-in(拷贝,不手改): `work/theme-harness/src/anim.tsx`, `work/theme-harness/src/components/*` from `skills/video-to-remotion/examples/`

**Interfaces:**
- Produces: 一个可 `tsc --noEmit` 和 `npx remotion still` 的脚手架;`DemoAll` composition(id `DemoAll`,1920×1080,32s@24fps),7 个组件在已知帧窗展示;`work/theme-harness/baseline/` 下的 teal 基线 PNG(改动前的样子)。

- [ ] **Step 1: 建脚手架目录与 .gitignore**

Run(Bash 工具):
```bash
mkdir -p work/theme-harness/src/components work/theme-harness/out work/theme-harness/baseline
printf 'node_modules/\nout/\n' > work/theme-harness/.gitignore
```
（`work/` 已被仓库根 `.gitignore` 覆盖；此文件让脚手架自身的 node_modules/out 也忽略。）

- [ ] **Step 2: 写 package.json（锁版本）**

`work/theme-harness/package.json`：
```json
{
  "name": "theme-harness",
  "private": true,
  "version": "0.0.0",
  "scripts": {
    "tsc": "tsc --noEmit"
  },
  "dependencies": {
    "@remotion/cli": "4.0.230",
    "@remotion/google-fonts": "4.0.230",
    "remotion": "4.0.230",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "typescript": "5.5.4",
    "@types/react": "18.3.3"
  }
}
```

- [ ] **Step 3: 写 tsconfig.json**

`work/theme-harness/tsconfig.json`：
```json
{
  "compilerOptions": {
    "target": "ES2018",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "noEmit": true,
    "lib": ["ES2019", "DOM"]
  },
  "include": ["src"]
}
```

- [ ] **Step 4: 同步当前 examples 源码进脚手架**

Run(Bash 工具):
```bash
cp skills/video-to-remotion/examples/anim.tsx work/theme-harness/src/anim.tsx
cp skills/video-to-remotion/examples/components/*.tsx work/theme-harness/src/components/
```
（Task 1 时 `themes.ts` 尚不存在，`DemoAll` 只引用现有组件。后续任务每次验证前重跑本步，并追加拷贝 `themes.ts`——见各任务的“同步”步骤。）

- [ ] **Step 5: 写 entry `src/index.ts`**

`work/theme-harness/src/index.ts`：
```ts
import { registerRoot } from "remotion";
import { HarnessRoot } from "./Root";
registerRoot(HarnessRoot);
```

- [ ] **Step 6: 写 demo composition `src/DemoAll.tsx`**

`work/theme-harness/src/DemoAll.tsx`（7 组件排在不重叠的已知帧窗，便于抽帧；透明背景，只看图形本身）：
```tsx
import * as React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { Intro } from "./components/Intro";
import { SectionCard } from "./components/SectionCard";
import { LowerThird } from "./components/LowerThird";
import { StatCallout } from "./components/StatCallout";
import { KeypointCallout } from "./components/KeypointCallout";
import { ListReveal } from "./components/ListReveal";
import { Outro } from "./components/Outro";

// [at秒, 时长秒, 组件, props] —— 窗口互不重叠，抽帧点取窗口中段
const DEMO = [
  [0.5, 4.0, Intro, { kicker: "EPISODE 14", title: "HS TOP 200", sub: "with Herschel Fruean" }],
  [5.0, 4.0, SectionCard, { kicker: "PART 1", title: "The Christchurch Trip" }],
  [9.5, 3.5, LowerThird, { line1: "Herschel Fruean", line2: "NZ Schoolboy Rugby analyst" }],
  [13.5, 3.0, StatCallout, { value: "62", label: "points — a blowout" }],
  [17.0, 3.0, KeypointCallout, { text: "Which schools actually develop players?" }],
  [20.5, 6.0, ListReveal, { title: "Three takeaways", items: ["Depth over hype", "Coaching wins", "Play the calendar"] }],
  [27.5, 4.0, Outro, { title: "HS TOP 200", sub: "Thanks for watching", small: "Monday Morning Meeting" }],
] as const;

export const DemoAll: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      {DEMO.map(([at, dur, C, props], i) => {
        const durFrames = Math.round((dur as number) * fps);
        return (
          <Sequence key={i} from={Math.round((at as number) * fps)} durationInFrames={durFrames}>
            {React.createElement(C as React.FC<any>, { ...(props as object), durFrames })}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 7: 写脚手架 `src/Root.tsx`**

`work/theme-harness/src/Root.tsx`：
```tsx
import * as React from "react";
import { Composition } from "remotion";
import { DemoAll } from "./DemoAll";

export const HarnessRoot: React.FC = () => (
  <Composition
    id="DemoAll"
    component={DemoAll}
    durationInFrames={768}
    fps={24}
    width={1920}
    height={1080}
  />
);
```

- [ ] **Step 8: 安装依赖**

Run(Bash 工具，cwd 脚手架)：
```bash
cd work/theme-harness && npm install
```
Expected: 装好 remotion 4.0.230 / react 18.3.1，无 React 19 被拉入（`npm ls react` 显示 `react@18.3.1`）。

- [ ] **Step 9: 类型检查（绿）**

Run：
```bash
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS，无报错（验证当前 examples 组件在脚手架里类型自洽）。

- [ ] **Step 10: 抽 teal 基线帧（改动前的样子）**

Run（每个组件窗口中段一帧）：
```bash
cd work/theme-harness
npx remotion still src/index.ts DemoAll baseline/01-intro.png     --frame=48
npx remotion still src/index.ts DemoAll baseline/02-section.png   --frame=156
npx remotion still src/index.ts DemoAll baseline/03-lowerthird.png --frame=252
npx remotion still src/index.ts DemoAll baseline/04-stat.png      --frame=348
npx remotion still src/index.ts DemoAll baseline/05-keypoint.png  --frame=444
npx remotion still src/index.ts DemoAll baseline/06-list.png      --frame=576
npx remotion still src/index.ts DemoAll baseline/07-outro.png     --frame=684
```
Expected: 7 张 PNG 落在 `baseline/`，显示当前 teal 外观（青色卡片/竖条、系统字体）。**这组是零回归的对照基准。**

- [ ] **Step 11: 肉眼确认基线**

Read `baseline/03-lowerthird.png` 与 `baseline/04-stat.png`：确认是当前青色卡片样子（深色半透卡 + 左/下青色边）。若空白，检查 `--frame` 是否落在窗口内。

- [ ] **Step 12: 不提交脚手架，仅确认已忽略**

Run：
```bash
git status --porcelain work/theme-harness
```
Expected: 空输出（脚手架被 `work/` 的 gitignore 覆盖，不进版本库）。

（Task 1 无源码改动可提交；deliverable 是能编译能抽帧的脚手架 + 基线。进入 Task 2 开始改真身。）

## Task 2: 第 1 层 — `themes.ts`（Theme 契约 + 两主题 + 开关）

**Files:**
- Create: `skills/video-to-remotion/examples/themes.ts`
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Produces:
  - `type ThemeName = "editorial" | "teal"`
  - `type CardStyle = { bg: string; borderColor: string; borderWidthU: number; borderSide: "left" | "bottom"; radiusU: number; shadow: string }`
  - `type Theme = { name; font; weight:{heavy;med;light}; color:{text;textMuted;accent;scrimBase}; card: CardStyle | null; rule:"bar"|"hairline"; kicker:{case:"upper"|"none"; spacingEm:number}; motion:"fade"|"stagger" }`
  - `const THEME: ThemeName`（开关，默认 `"editorial"`）
  - `const T: Theme`（当前主题对象，供 anim/组件读取）

- [ ] **Step 1: 写 `themes.ts`（类型 + 两主题数据 + 开关 + 字体加载）**

`skills/video-to-remotion/examples/themes.ts`：
```ts
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
```

- [ ] **Step 2: 同步进脚手架并类型检查（红→绿）**

Run：
```bash
cp skills/video-to-remotion/examples/themes.ts work/theme-harness/src/themes.ts
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。若报 `@remotion/google-fonts/Archivo` 找不到类型，确认 Step 依赖已装（Task 1 Step 8）。这验证了主题层类型自洽、字体子包可解析。

- [ ] **Step 3: 提交**

```bash
git add skills/video-to-remotion/examples/themes.ts
git commit -m "feat(video-to-remotion): add themes.ts theme registry (editorial + teal)"
```

---

## Task 3: 第 2 层 — `anim.tsx` 常量改读 `T`（向后兼容，零回归）

把 `anim.tsx` 里写死的调色板常量改为从 `T` 派生，并**保留同名导出**，这样 7 个组件此刻 import 不变、仍能编译。此任务先在 `THEME="teal"` 下验证逐帧等于基线。

**Files:**
- Modify: `skills/video-to-remotion/examples/anim.tsx`（palette 区 + `Scrim` 底色）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T` from `./themes`（Task 2）
- Produces（保持旧名，值改为从 `T` 派生，供未迁移组件继续用）:
  - `INK, ACCENT, WHITE, MUTED, CARD: string`
  - `TIMING, EASE_OUT, useUnit, ANCHOR, anchorJustify, anchorPad, useFade, Scrim`（签名不变）

- [ ] **Step 1: 抽当前基线复核（红：仍是旧写死值）**

（基线已在 Task 1 Step 10 生成；此步只是确认脚手架仍能 tsc + 抽帧，作为改动前对照。）
Run：
```bash
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 2: 改 `anim.tsx` 顶部 import + palette 区**

编辑 `skills/video-to-remotion/examples/anim.tsx`。在文件顶部的 `import ... from "remotion";` 之后加：
```ts
import { T } from "./themes";
```
把现有 palette 常量块（`export const INK ... export const CARD ...`，第 30–34 行附近）整段替换为从 `T` 派生的**同名**导出：
```ts
// --- palette: 由当前主题 T 提供(themes.ts)。保留旧常量名,组件无需改 import。
export const INK    = T.color.scrimBase;   // 深色卡/scrim 底
export const ACCENT = T.color.accent;      // 强调色
export const WHITE  = T.color.text;         // 主文字
export const MUTED  = T.color.textMuted;    // 次文字
// CARD: teal 为半透卡填色;editorial(card=null)退化为透明——迁移后组件不再用它。
export const CARD   = T.card ? T.card.bg : "transparent";
```

- [ ] **Step 3: `Scrim` 底色改读 `T`**

`Scrim` 组件里两处硬编码 `rgba(12,20,28,...)` 改为用 `T.color.scrimBase`。替换 `Scrim` 实现为：
```tsx
export const Scrim: React.FC<{ heightPct?: number; maxOpacity?: number }> = ({
  heightPct = 45, maxOpacity = 0.88,
}) => {
  const base = T.color.scrimBase;
  const grad = (op: number) =>
    ANCHOR === "top"
      ? `linear-gradient(to top, ${hexA(base, 0)}, ${hexA(base, op)})`
      : `linear-gradient(to bottom, ${hexA(base, 0)}, ${hexA(base, op)})`;
  return (
    <AbsoluteFill style={
      ANCHOR === "top"
        ? { top: 0, bottom: "auto", height: `${heightPct}%`, background: grad(maxOpacity) }
        : { top: `${100 - heightPct}%`, background: grad(maxOpacity) }
    } />
  );
};
```
并在 `Scrim` 上方加一个小工具（把 `#RRGGBB` + alpha 转成 `rgba()`）：
```ts
// #RRGGBB + alpha(0..1) → rgba(),供渐变用(scrimBase 是 hex)。
const hexA = (hex: string, a: number): string => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
};
```

- [ ] **Step 4: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/anim.tsx work/theme-harness/src/anim.tsx
cp skills/video-to-remotion/examples/themes.ts work/theme-harness/src/themes.ts
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 5: teal 零回归抽帧对比**

先把开关切到 teal 再抽帧（editorial 尚未接入组件）：
```bash
# 临时切 teal:改 src/themes.ts 里 THEME 值为 "teal"(只在脚手架副本改,验证用)
cd work/theme-harness
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx remotion still src/index.ts DemoAll out/t3-lowerthird.png --frame=252
npx remotion still src/index.ts DemoAll out/t3-stat.png       --frame=348
npx remotion still src/index.ts DemoAll out/t3-intro.png      --frame=48
```
Read `out/t3-lowerthird.png`、`out/t3-stat.png`、`out/t3-intro.png` 并与 `baseline/03-lowerthird.png`、`baseline/04-stat.png`、`baseline/01-intro.png` 对比。
Expected: **视觉一致**（同青色卡片/竖条、同字体、同位置）。像素级差异应为零或仅抗锯齿噪声。若不同，说明常量派生值与原写死值不符——修 `themes.ts` 的 teal 数据。

- [ ] **Step 6: 提交**

```bash
git add skills/video-to-remotion/examples/anim.tsx
git commit -m "refactor(video-to-remotion): source anim palette + Scrim from active theme (teal parity)"
```

---

## Task 4: 第 2 层积木 — `<Surface>` / `<Rule>` / `<Kicker>`

在 `anim.tsx` 新增三个读 `T` 的原始组件，收敛今天各组件重复的卡片/竖条/kicker 样式。此任务只**新增**，不改组件；用脚手架临时 demo 验证两主题分支都渲染。

**Files:**
- Modify: `skills/video-to-remotion/examples/anim.tsx`（追加三个组件）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T`（Task 2）、`useUnit`、`ANCHOR`、`Scrim`（本文件已有）
- Produces：
  - `Surface: React.FC<{ side?: "left"|"bottom"; children; style? }>` — `T.card` 为对象渲染实心卡（按 `side` 覆盖 `borderSide`），为 `null` 渲染透明容器（调用方另配 `Scrim`）。
  - `Rule: React.FC<{ widthU?: number; progress?: number }>` — `T.rule==="bar"` 渲染粗竖条；`"hairline"` 渲染细线 + 左端 accent 小段；`progress`(0..1) 控制绘出比例。
  - `Kicker: React.FC<{ children }>` — 按 `T.kicker` + `T.color.accent` + `T.font` 渲染小标题。

- [ ] **Step 1: 追加三个组件到 `anim.tsx` 末尾**

```tsx
// --- 第 2 层积木:组件只用这些拼装,样式值全来自 T ------------------------

// Surface: 文字底板。实心卡(teal)或透明(editorial,靠 Scrim 保证可读)。
// 只管主题化的卡片外观(底色/圆角/投影/强调边)+ card=null 的透明退化。
// padding 与其它布局由调用方经 `style` 传入(那是第 3 层组件的职责),这样每个
// 组件都能保留自己今天的精确 padding/边宽,teal 零回归。side/widthU 可覆盖,
// 因为各卡片的强调边位置与粗细本就不同(LowerThird 0.8u左、Stat 0.6u下)。
export const Surface: React.FC<{
  side?: "left" | "bottom"; widthU?: number;
  style?: React.CSSProperties; children: React.ReactNode;
}> = ({ side, widthU, style, children }) => {
  const u = useUnit();
  const c = T.card;
  if (!c) return <div style={style}>{children}</div>;   // editorial:透明,靠 Scrim
  const s = side ?? c.borderSide;
  const w = u * (widthU ?? c.borderWidthU);
  const border =
    s === "left"
      ? { borderLeft: `${w}px solid ${c.borderColor}` }
      : { borderBottom: `${w}px solid ${c.borderColor}` };
  return (
    <div style={{
      background: c.bg, borderRadius: u * c.radiusU, boxShadow: c.shadow,
      ...border, ...style,
    }}>{children}</div>
  );
};

// Rule: 分隔/强调线。bar=粗竖条(teal 的左边条);hairline=细线+accent 小段(editorial)。
// progress(0..1):stagger 入场时由 useDraw 传入,做 0→满宽的描线;fade 主题默认 1。
export const Rule: React.FC<{ widthU?: number; progress?: number }> = ({
  widthU = 36, progress = 1,
}) => {
  const u = useUnit();
  if (T.rule === "bar") {
    // teal:细高的一段(SectionCard 用作 title 下的强调条)。
    return <div style={{ height: u * 0.6, width: u * widthU * progress,
      background: T.color.accent, borderRadius: u * 0.3 }} />;
  }
  // editorial hairline:整条细线(淡文字色) + 左端一小段 accent。淡色由 T 派生,
  // 不写死(hexA 在本文件 Task 3 已定义)。
  const seg = u * 6; // accent 段长(u=6)
  const full = u * widthU * progress;
  return (
    <div style={{ position: "relative", height: u * 0.35, width: full,
      background: hexA(T.color.text, 0.32) }}>
      <div style={{ position: "absolute", left: 0, top: 0, height: "100%",
        width: Math.min(seg, full), background: T.color.accent }} />
    </div>
  );
};

// Kicker: 小标题(EPISODE 14 / PART 1 …)。大小写与字距来自 T.kicker。
export const Kicker: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children, style,
}) => {
  const u = useUnit();
  return (
    <div style={{
      color: T.color.accent, fontFamily: T.font, fontSize: u * 2.6, fontWeight: T.weight.med,
      letterSpacing: T.kicker.case === "upper" ? `${T.kicker.spacingEm}em` : u * 0.2,
      textTransform: T.kicker.case === "upper" ? "uppercase" : "none",
      ...style,
    }}>{children}</div>
  );
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/anim.tsx work/theme-harness/src/anim.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 3: 提交**

```bash
git add skills/video-to-remotion/examples/anim.tsx
git commit -m "feat(video-to-remotion): add Surface/Rule/Kicker building blocks reading active theme"
```

---

## Task 5: 第 2 层动画 — `useEntrance` / `useDraw` / `useClipReveal`

新增 stagger 家族的入场编排 hooks。只**新增**，组件下一批任务才接入。

**Files:**
- Modify: `skills/video-to-remotion/examples/anim.tsx`（追加 hooks）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `TIMING`、`EASE_OUT`、`useCurrentFrame`、`interpolate`、`useUnit`
- Produces：
  - `useDraw(delay?: number): number` — 返回 0..1 的绘出进度（宽度用），起始帧可延迟。
  - `useClipReveal(delay?: number): string` — 返回 `clip-path: inset(...)` 字符串，做左→右擦入。
  - `type EntranceRole = "kicker" | "title" | "rule" | "sub"`
  - `useEntrance(role: EntranceRole): { opacity: number; transform: string; clipPath?: string }` — stagger 家族按角色返回该帧样式；错峰顺序 kicker→title→rule→sub。

- [ ] **Step 1: 追加 hooks 到 `anim.tsx`**

```tsx
// --- 第 2 层:stagger 入场编排(editorial)。fade 主题的组件不调用这些。------
// 统一用 EASE_OUT,不 bounce(纪录片规矩)。所有位移用 useUnit 派生,分辨率无关。

// 0→1 绘出进度,delay 帧后开始,历时 TIMING.overlayIn。
export const useDraw = (delay = 0): number => {
  const f = useCurrentFrame();
  return interpolate(f, [delay, delay + TIMING.overlayIn], [0, 1],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
};

// 左→右擦入:inset(0 <right>% 0 0),right 从 100→0。
export const useClipReveal = (delay = 0): string => {
  const f = useCurrentFrame();
  const p = interpolate(f, [delay, delay + TIMING.reveal], [100, 0],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return `inset(0 ${p}% 0 0)`;
};

export type EntranceRole = "kicker" | "title" | "rule" | "sub";

// stagger 家族:每个角色错开 TIMING.stagger 帧登场。返回该帧的样式片段。
// title 用 clipPath 擦入,其余用 淡入+上浮。
export const useEntrance = (role: EntranceRole): {
  opacity: number; transform: string; clipPath?: string;
} => {
  const f = useCurrentFrame();
  const u = useUnit();
  const order: Record<EntranceRole, number> = { kicker: 0, title: 1, rule: 2, sub: 3 };
  const delay = order[role] * TIMING.stagger;
  const p = interpolate(f, [delay, delay + TIMING.reveal], [0, 1],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (role === "title") {
    return { opacity: p, transform: "none", clipPath: useClipReveal(delay) };
  }
  const rise = interpolate(p, [0, 1], [u * 1.2, 0]);
  return { opacity: p, transform: `translateY(${rise}px)` };
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/anim.tsx work/theme-harness/src/anim.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。（注意 `useClipReveal` 在 `useEntrance` 内条件前调用——它本身也调 hook；确保放在 `title` 分支的 return 里不违反 hook 规则：改为在函数体顶层无条件先算，见下修正。）

- [ ] **Step 3: 修正 hook 调用顺序（避免条件内调 hook）**

将 `useEntrance` 改为顶层无条件计算 clipPath：
```tsx
export const useEntrance = (role: EntranceRole): {
  opacity: number; transform: string; clipPath?: string;
} => {
  const f = useCurrentFrame();
  const u = useUnit();
  const order: Record<EntranceRole, number> = { kicker: 0, title: 1, rule: 2, sub: 3 };
  const delay = order[role] * TIMING.stagger;
  const clip = useClipReveal(delay);            // 无条件调用,满足 hook 规则
  const p = interpolate(f, [delay, delay + TIMING.reveal], [0, 1],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (role === "title") return { opacity: p, transform: "none", clipPath: clip };
  const rise = interpolate(p, [0, 1], [u * 1.2, 0]);
  return { opacity: p, transform: `translateY(${rise}px)` };
};
```
Run：
```bash
cp skills/video-to-remotion/examples/anim.tsx work/theme-harness/src/anim.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 4: 提交**

```bash
git add skills/video-to-remotion/examples/anim.tsx
git commit -m "feat(video-to-remotion): add stagger entrance hooks (useEntrance/useDraw/useClipReveal)"
```

---

## Task 6: 迁移 `LowerThird`（卡片类，树立组件迁移范式）

这是 7 个组件迁移的**范式任务**：读 `T`、用 `<Surface>` 包裹、`T.motion` 分两条入场路径（teal 保留原样、editorial 走 stagger + `<Scrim>` 保可读）、hooks 无条件调用/有条件使用。后续组件照此模式。

**Files:**
- Modify: `skills/video-to-remotion/examples/components/LowerThird.tsx`（整文件替换）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T`、`Surface`、`Scrim`、`useUnit`、`useFade`、`useEntrance`、`TIMING`、`EASE_OUT`、`anchorJustify`、`anchorPad`
- Produces: `LowerThird`（props 不变：`{ line1; line2?; durFrames? }`）

- [ ] **Step 1: 整文件替换 `LowerThird.tsx`**

```tsx
// LowerThird.tsx — 实体名条。props 不变:line1(实体) + line2(编辑体注解)。
// 样式全来自当前主题 T:teal=实心卡+左accent+左滑入;editorial=无卡骑 Scrim+stagger。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Surface, Scrim, useUnit, useFade, useEntrance, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const LowerThird: React.FC<{ line1: string; line2?: string; durFrames?: number }> = ({
  line1, line2, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const slide = interpolate(f, [0, TIMING.overlayIn], [u * 1.8, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  const e1 = useEntrance("title");   // 无条件调用(hook 规则);仅 stagger 用
  const e2 = useEntrance("sub");

  // 卡外层:fade=整卡淡入+左滑;stagger=整卡只淡入(元素各自动画)。
  const cardStyle: React.CSSProperties = stagger
    ? { opacity: o }
    : { opacity: o, transform: `translateX(${slide}px)` };

  const line1Style: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 6, fontWeight: T.weight.heavy,
    letterSpacing: -0.5, lineHeight: 1.05,
    ...(stagger ? { opacity: e1.opacity, clipPath: e1.clipPath } : null),
  };
  const line2Style: React.CSSProperties = {
    color: T.color.textMuted, fontFamily: T.font, fontSize: u * 3.6, fontWeight: T.weight.light,
    marginTop: u * 0.8,
    ...(stagger ? { opacity: e2.opacity, transform: e2.transform } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 5) }}>
      {!T.card ? <Scrim heightPct={40} maxOpacity={0.9} /> : null}
      <Surface side="left" style={{ ...cardStyle, padding: `${u * 2.2}px ${u * 3}px` }}>
        <div style={line1Style}>{line1}</div>
        {line2 ? <div style={line2Style}>{line2}</div> : null}
      </Surface>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/anim.tsx work/theme-harness/src/anim.tsx
cp skills/video-to-remotion/examples/themes.ts work/theme-harness/src/themes.ts
cp skills/video-to-remotion/examples/components/LowerThird.tsx work/theme-harness/src/components/LowerThird.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 3: teal 零回归 + editorial 观感抽帧**

```bash
cd work/theme-harness
# teal:与基线对比
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx remotion still src/index.ts DemoAll out/lt-teal.png --frame=252
# editorial:看新样子(金色 hairline 会在其它任务体现;此处看名条骑 scrim + Archivo)
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"editorial\"'))"
npx remotion still src/index.ts DemoAll out/lt-editorial.png --frame=252
```
Read `out/lt-teal.png`（应等于 `baseline/03-lowerthird.png`：青卡+左青边）与 `out/lt-editorial.png`（应为暖白 Archivo 文字骑在柔和 scrim 上、无青色卡片）。
Expected: teal 一致；editorial 明显不同且可读、不挡脸、贴底。

- [ ] **Step 4: 提交**

```bash
git add skills/video-to-remotion/examples/components/LowerThird.tsx
git commit -m "refactor(video-to-remotion): migrate LowerThird to theme tokens + stagger path"
```

---

## Task 7: 迁移 `StatCallout`（卡片类，下边 accent，数字滚动保留）

**Files:**
- Modify: `skills/video-to-remotion/examples/components/StatCallout.tsx`（整文件替换）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T`、`Surface`（用 `side="bottom"` `widthU={0.6}`）、`Scrim`、`useUnit`、`useFade`、`useEntrance`、`TIMING`、`EASE_OUT`、`anchorJustify`、`anchorPad`
- Produces: `StatCallout`（props 不变：`{ value; label?; durFrames? }`）

- [ ] **Step 1: 整文件替换 `StatCallout.tsx`**

```tsx
// StatCallout.tsx — 数字 callout。props 不变:value(数字串) + label。
// 数字入场滚动(两主题都保留)。teal=实心卡+下accent;editorial=无卡骑 scrim。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Surface, Scrim, useUnit, useFade, useEntrance, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const StatCallout: React.FC<{ value: string; label?: string; durFrames?: number }> = ({
  value, label, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const p = interpolate(f, [0, TIMING.reveal], [0, 1], { easing: EASE_OUT, extrapolateRight: "clamp" });
  const num = parseFloat(value.replace(/[^\d.]/g, ""));
  const prefix = (value.match(/^\D*/) ?? [""])[0];
  const suffix = (value.match(/\D*$/) ?? [""])[0];
  const display = isNaN(num) ? value : prefix + Math.round(num * p).toLocaleString() + suffix;
  const eLabel = useEntrance("sub");

  const valueStyle: React.CSSProperties = {
    color: T.color.accent, fontFamily: T.font, fontSize: u * 9, fontWeight: T.weight.heavy,
    letterSpacing: -1, lineHeight: 1,
  };
  const labelStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 3.4, fontWeight: T.weight.med,
    ...(stagger ? { opacity: eLabel.opacity, transform: eLabel.transform } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-end",
                           padding: anchorPad(u * 8, 0, u * 5) }}>
      {!T.card ? <Scrim heightPct={40} maxOpacity={0.9} /> : null}
      <Surface side="bottom" widthU={0.6} style={{
        opacity: o, display: "flex", alignItems: "baseline", gap: u * 1.6,
        padding: `${u * 1.8}px ${u * 3}px`,
      }}>
        <div style={valueStyle}>{display}</div>
        {label ? <div style={labelStyle}>{label}</div> : null}
      </Surface>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/components/StatCallout.tsx work/theme-harness/src/components/StatCallout.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 3: teal 零回归抽帧**

```bash
cd work/theme-harness
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx remotion still src/index.ts DemoAll out/stat-teal.png --frame=348
```
Read `out/stat-teal.png` 与 `baseline/04-stat.png` 对比。
Expected: 一致（青色大数字 + 下青边卡，数字滚动到 62）。

- [ ] **Step 4: 提交**

```bash
git add skills/video-to-remotion/examples/components/StatCallout.tsx
git commit -m "refactor(video-to-remotion): migrate StatCallout to theme tokens"
```

---

## Task 8: 迁移 `KeypointCallout`（卡片类）

**Files:**
- Modify: `skills/video-to-remotion/examples/components/KeypointCallout.tsx`（整文件替换）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T`、`Surface`（`side="left"`）、`Scrim`、`useUnit`、`useFade`、`useEntrance`、`TIMING`、`EASE_OUT`、`anchorJustify`、`anchorPad`
- Produces: `KeypointCallout`（props 不变：`{ text; durFrames? }`）

- [ ] **Step 1: 整文件替换 `KeypointCallout.tsx`**

```tsx
// KeypointCallout.tsx — 金句/问题卡。props 不变:text。
// teal=实心卡+左accent+上浮;editorial=无卡骑 scrim + title 擦入。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Surface, Scrim, useUnit, useFade, useEntrance, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const KeypointCallout: React.FC<{ text: string; durFrames?: number }> = ({ text, durFrames }) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const rise = interpolate(f, [0, TIMING.reveal], [u * 1.4, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  const e = useEntrance("title");

  const cardStyle: React.CSSProperties = stagger
    ? { opacity: o, maxWidth: "72%" }
    : { opacity: o, transform: `translateY(${rise}px)`, maxWidth: "72%" };
  const textStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 5, fontWeight: T.weight.med, lineHeight: 1.18,
    ...(stagger ? { opacity: e.opacity, clipPath: e.clipPath } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 5, u * 8) }}>
      {!T.card ? <Scrim heightPct={45} maxOpacity={0.9} /> : null}
      <Surface side="left" style={{ ...cardStyle, padding: `${u * 2.4}px ${u * 3}px` }}>
        <div style={textStyle}>{text}</div>
      </Surface>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/components/KeypointCallout.tsx work/theme-harness/src/components/KeypointCallout.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 3: teal 零回归抽帧**

```bash
cd work/theme-harness
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx remotion still src/index.ts DemoAll out/kp-teal.png --frame=444
```
Read `out/kp-teal.png` 与 `baseline/05-keypoint.png` 对比。Expected: 一致。

- [ ] **Step 4: 提交**

```bash
git add skills/video-to-remotion/examples/components/KeypointCallout.tsx
git commit -m "refactor(video-to-remotion): migrate KeypointCallout to theme tokens"
```

---

## Task 9: 迁移 `SectionCard`（scrim 类，`<Kicker>` + `<Rule>` 描线）

**Files:**
- Modify: `skills/video-to-remotion/examples/components/SectionCard.tsx`（整文件替换）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T`、`Scrim`、`Kicker`、`Rule`、`useUnit`、`useFade`、`useEntrance`、`useDraw`、`TIMING`、`EASE_OUT`、`anchorJustify`、`anchorPad`
- Produces: `SectionCard`（props 不变：`{ kicker?; title; durFrames? }`）

- [ ] **Step 1: 整文件替换 `SectionCard.tsx`**

```tsx
// SectionCard.tsx — 章节卡。props 不变:kicker + title。scrim 类(两主题都骑 Scrim)。
// teal:title 下青色条按 overlayIn 描出;editorial:kicker→title 擦入→hairline 描出。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Scrim, Kicker, Rule, useUnit, useFade, useEntrance, useDraw, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const SectionCard: React.FC<{ kicker?: string; title: string; durFrames?: number }> = ({
  kicker, title, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const pFade = interpolate(f, [0, TIMING.overlayIn], [0, 1], { easing: EASE_OUT, extrapolateRight: "clamp" });
  const eKicker = useEntrance("kicker");
  const eTitle = useEntrance("title");
  const drawStagger = useDraw(2 * TIMING.stagger);          // rule 在第 3 拍描出

  const kickerExtra = stagger ? { opacity: eKicker.opacity, transform: eKicker.transform } : null;
  const titleStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 8.5, fontWeight: T.weight.heavy,
    letterSpacing: -1, lineHeight: 1.0,
    ...(stagger ? { opacity: eTitle.opacity, clipPath: eTitle.clipPath } : null),
  };
  const ruleProgress = stagger ? drawStagger : pFade;        // teal 用旧的 overlayIn 描出

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Scrim heightPct={46} maxOpacity={0.9} />
      <div style={{ opacity: o, padding: anchorPad(u * 9, u * 6) }}>
        {kicker ? <Kicker style={{ marginBottom: u * 1.2, ...kickerExtra }}>{kicker}</Kicker> : null}
        <div style={titleStyle}>{title}</div>
        <div style={{ marginTop: u * 2 }}><Rule widthU={36} progress={ruleProgress} /></div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/components/SectionCard.tsx work/theme-harness/src/components/SectionCard.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 3: teal 零回归 + editorial 抽帧**

```bash
cd work/theme-harness
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx remotion still src/index.ts DemoAll out/sec-teal.png --frame=156
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"editorial\"'))"
npx remotion still src/index.ts DemoAll out/sec-editorial.png --frame=156
```
Read `out/sec-teal.png`（对比 `baseline/02-section.png`，应一致：青色描条）与 `out/sec-editorial.png`（金色 hairline + Archivo 大标题 + 大写宽字距 kicker）。
Expected: teal 一致；editorial 是细金线而非粗青条。

- [ ] **Step 4: 提交**

```bash
git add skills/video-to-remotion/examples/components/SectionCard.tsx
git commit -m "refactor(video-to-remotion): migrate SectionCard to Kicker/Rule + stagger"
```

---

## Task 10: 迁移 `Intro`（scrim 类，左竖条 + kicker/title/sub stagger）

**Files:**
- Modify: `skills/video-to-remotion/examples/components/Intro.tsx`（整文件替换）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T`、`Scrim`、`Kicker`、`useUnit`、`useFade`、`useEntrance`、`TIMING`、`EASE_OUT`、`anchorJustify`、`anchorPad`
- Produces: `Intro`（props 不变：`{ kicker?; title; sub?; durFrames? }`）

- [ ] **Step 1: 整文件替换 `Intro.tsx`**

```tsx
// Intro.tsx — 片头卡。props 不变:kicker + title + sub。scrim 类,左侧竖 accent 条。
// teal:整体上滑淡入;editorial:kicker→title 擦入→sub 依次登场,竖条着 accent 色。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Scrim, Kicker, useUnit, useFade, useEntrance, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const Intro: React.FC<{ kicker?: string; title: string; sub?: string; durFrames?: number }> = ({
  kicker, title, sub, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const slide = interpolate(f, [0, TIMING.overlayIn], [u * 1.6, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  const eKicker = useEntrance("kicker");
  const eTitle = useEntrance("title");
  const eSub = useEntrance("sub");

  const outer: React.CSSProperties = stagger
    ? { opacity: o, display: "flex", gap: u * 2.4, padding: anchorPad(u * 9, u * 6) }
    : { opacity: o, transform: `translateY(${slide}px)`, display: "flex", gap: u * 2.4, padding: anchorPad(u * 9, u * 6) };
  const titleStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 10, fontWeight: T.weight.heavy,
    letterSpacing: -1.5, lineHeight: 0.98,
    ...(stagger ? { opacity: eTitle.opacity, clipPath: eTitle.clipPath } : null),
  };
  const subStyle: React.CSSProperties = {
    color: T.color.textMuted, fontFamily: T.font, fontSize: u * 3.4, fontWeight: T.weight.light, marginTop: u * 1.4,
    ...(stagger ? { opacity: eSub.opacity, transform: eSub.transform } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Scrim heightPct={50} maxOpacity={0.92} />
      <div style={outer}>
        <div style={{ width: u * 0.8, background: T.color.accent, borderRadius: u * 0.4 }} />
        <div>
          {kicker ? <Kicker style={{ marginBottom: u * 1, ...(stagger ? { opacity: eKicker.opacity, transform: eKicker.transform } : null) }}>{kicker}</Kicker> : null}
          <div style={titleStyle}>{title}</div>
          {sub ? <div style={subStyle}>{sub}</div> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/components/Intro.tsx work/theme-harness/src/components/Intro.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 3: teal 零回归抽帧**

```bash
cd work/theme-harness
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx remotion still src/index.ts DemoAll out/intro-teal.png --frame=48
```
Read `out/intro-teal.png` 与 `baseline/01-intro.png` 对比。Expected: 一致。

- [ ] **Step 4: 提交**

```bash
git add skills/video-to-remotion/examples/components/Intro.tsx
git commit -m "refactor(video-to-remotion): migrate Intro to theme tokens + stagger"
```

---

## Task 11: 迁移 `Outro`（scrim 类，左竖条，纯淡入 + editorial stagger）

**Files:**
- Modify: `skills/video-to-remotion/examples/components/Outro.tsx`（整文件替换）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T`、`Scrim`、`useUnit`、`useFade`、`useEntrance`、`anchorJustify`、`anchorPad`
- Produces: `Outro`（props 不变：`{ title; sub?; small?; durFrames? }`）

- [ ] **Step 1: 整文件替换 `Outro.tsx`**

```tsx
// Outro.tsx — 片尾卡。props 不变:title + sub + small。scrim 类,左竖 accent 条。
// teal:纯淡入(原样);editorial:title 擦入 → sub/small 依次登场。
import * as React from "react";
import { AbsoluteFill } from "remotion";
import { T, Scrim, useUnit, useFade, useEntrance, anchorJustify, anchorPad } from "../anim";

export const Outro: React.FC<{ title: string; sub?: string; small?: string; durFrames?: number }> = ({
  title, sub, small, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const stagger = T.motion === "stagger";
  const eTitle = useEntrance("title");
  const eSub = useEntrance("sub");

  const titleStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 8.5, fontWeight: T.weight.heavy,
    letterSpacing: -1, lineHeight: 1,
    ...(stagger ? { opacity: eTitle.opacity, clipPath: eTitle.clipPath } : null),
  };
  const subStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 3.6, fontWeight: T.weight.med, marginTop: u * 1.4,
    ...(stagger ? { opacity: eSub.opacity, transform: eSub.transform } : null),
  };
  const smallStyle: React.CSSProperties = {
    color: T.color.textMuted, fontFamily: T.font, fontSize: u * 2.8, fontWeight: T.weight.light, marginTop: u * 0.8,
    ...(stagger ? { opacity: eSub.opacity, transform: eSub.transform } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Scrim heightPct={50} maxOpacity={0.92} />
      <div style={{ opacity: o, display: "flex", gap: u * 2.4, padding: anchorPad(u * 9, u * 6) }}>
        <div style={{ width: u * 0.8, background: T.color.accent, borderRadius: u * 0.4 }} />
        <div>
          <div style={titleStyle}>{title}</div>
          {sub ? <div style={subStyle}>{sub}</div> : null}
          {small ? <div style={smallStyle}>{small}</div> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/components/Outro.tsx work/theme-harness/src/components/Outro.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 3: teal 零回归抽帧**

```bash
cd work/theme-harness
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx remotion still src/index.ts DemoAll out/outro-teal.png --frame=684
```
Read `out/outro-teal.png` 与 `baseline/07-outro.png` 对比。Expected: 一致。

- [ ] **Step 4: 提交**

```bash
git add skills/video-to-remotion/examples/components/Outro.tsx
git commit -m "refactor(video-to-remotion): migrate Outro to theme tokens + stagger"
```

---

## Task 12: 迁移 `ListReveal`（scrim 类，自带逐条错峰保留）

`ListReveal` 本就有逐条错峰入场（两主题都保留），迁移只换色/字体、`title` 走 `<Kicker>`。

**Files:**
- Modify: `skills/video-to-remotion/examples/components/ListReveal.tsx`（整文件替换）
- Sync/Test: `work/theme-harness/`

**Interfaces:**
- Consumes: `T`、`Scrim`、`Kicker`、`useUnit`、`useFade`、`TIMING`、`EASE_OUT`、`anchorJustify`、`anchorPad`
- Produces: `ListReveal`（props 不变：`{ title?; items[]; durFrames? }`）

- [ ] **Step 1: 整文件替换 `ListReveal.tsx`**

```tsx
// ListReveal.tsx — 枚举列表。props 不变:title + items[]。scrim 类。
// 逐条错峰入场(两主题都保留);颜色/字体来自 T,title 用 <Kicker>。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Scrim, Kicker, useUnit, useFade, TIMING, EASE_OUT, anchorJustify, anchorPad,
} from "../anim";

export const ListReveal: React.FC<{ title?: string; items: string[]; durFrames?: number }> = ({
  title, items, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Scrim heightPct={62} maxOpacity={0.9} />
      <div style={{ opacity: o, padding: anchorPad(u * 8, u * 6),
                    display: "flex", flexDirection: "column", gap: u * 1.6 }}>
        {title ? <Kicker style={{ marginBottom: u * 1 }}>{title}</Kicker> : null}
        {items.map((it, i) => {
          const at = TIMING.reveal + i * TIMING.stagger;
          const p = interpolate(frame, [at, at + TIMING.reveal], [0, 1],
            { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ opacity: p, transform: `translateX(${interpolate(p, [0, 1], [u * 2, 0])}px)`,
                                  display: "flex", alignItems: "baseline", gap: u * 2 }}>
              <span style={{ color: T.color.accent, fontFamily: T.font, fontSize: u * 4, fontWeight: T.weight.heavy }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <span style={{ color: T.color.text, fontFamily: T.font, fontSize: u * 5, fontWeight: T.weight.med }}>{it}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: 同步 + 类型检查（绿）**

Run：
```bash
cp skills/video-to-remotion/examples/components/ListReveal.tsx work/theme-harness/src/components/ListReveal.tsx
cd work/theme-harness && npx tsc --noEmit
```
Expected: PASS。

- [ ] **Step 3: teal 零回归 + editorial 全组件抽帧（4 组合验收）**

```bash
cd work/theme-harness
# teal 全帧
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx remotion still src/index.ts DemoAll out/list-teal.png --frame=576
# editorial 全帧(顺带肉眼看整套新观感)
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"editorial\"'))"
for fr in 48 156 252 348 444 576 684; do npx remotion still src/index.ts DemoAll out/ed-$fr.png --frame=$fr; done
```
Read `out/list-teal.png`（对比 `baseline/06-list.png`，一致）与 `out/ed-*.png`（整套 editorial：Archivo、金 accent、hairline、暖白文字，全部可读/不挡脸/贴底）。
Expected: teal 全一致；editorial 全部符合三条规则。

- [ ] **Step 4: 提交**

```bash
git add skills/video-to-remotion/examples/components/ListReveal.tsx
git commit -m "refactor(video-to-remotion): migrate ListReveal to theme tokens"
```

---

## Task 13: 文档（SKILL.md）+ 收尾自检

在 `SKILL.md` 记录 `THEME` 开关、依赖、加主题配方、新自检项。不删 anim 的向后兼容导出（`INK/ACCENT/...` 仍被组件间接使用；保留无害且利于外部样板），但确认无残留写死青色。

**Files:**
- Modify: `skills/video-to-remotion/SKILL.md`
- Sync/Test: `work/theme-harness/`（终检）

**Interfaces:**
- Consumes: 全部前序任务
- Produces: 更新后的 SKILL.md（含 §"主题系统"）

- [ ] **Step 1: 在 SKILL.md 的 Dependencies 段加字体依赖**

在 `SKILL.md` 依赖列表中 Remotion 那条下补一行（紧跟 `react`/`react-dom` 说明）：
```markdown
  - **`@remotion/google-fonts`**（与 `remotion` 同一 4.x 版本）——`editorial` 主题
    用 `Archivo`（`themes.ts` 顶层 `loadFont()` 加载）。`teal` 主题用系统字体、无需它。
```

- [ ] **Step 2: 在 SKILL.md “One design language” 段后新增“主题系统”小节**

在 `## The one idea` 的 "One design language." 段落后插入：
```markdown
### 主题系统（换外观 = 换 THEME，不改组件）

外观由 `src/themes.ts` 的一个开关决定，与 `ANCHOR`（上/下锚定）正交：

​```ts
export const THEME = "editorial";   // "editorial"(纪录片风) | "teal"(旧青色风)
​```

- **`editorial`**（默认）：Archivo 字体、暖白文字、金色 accent、细金线（hairline）、
  编排式 stagger 入场。质感靠字体/字距/细线，无胶片颗粒。
- **`teal`**：原青色深卡外观，逐帧不变（零回归）。

三层架构：`themes.ts`（主题数据）→ `anim.tsx`（积木 `<Surface>/<Rule>/<Kicker>` +
入场 hooks，全读当前主题 `T`）→ `components/*`（只管布局与锚定）。cue sheet 字段不变。

**加一种新风格：**
1. 往 `themes.ts` 的 `THEMES` 加一个条目，填 `Theme` 各字段（字体、色、card 卡/scrim、
   rule 粗条/细线、kicker 大小写、motion 入场家族）。
2. 若用新字体：在 `themes.ts` 顶层多一次 `loadFont()`。
3. 改 `THEME` 开关为新名字，渲染自检。
4. 仅当需要**全新结构**（毛玻璃/整帧擦除等）：给 `Theme` 加一个字段 + 在对应积木
   （`<Surface>`/`<Rule>`）或 `useEntrance` 加一个分支——一次加好，后续复用。

常见的换色/换字体主题**只做第 1 步**。
​```
```
（注：上面代码围栏里的 `​` 零宽字符仅为在本 md 内嵌套围栏；落笔到 SKILL.md 时写成普通 ``` 三反引号。）

- [ ] **Step 3: 在 Self-check 段补两条**

在 `SKILL.md` 的 `## Self-check` 列表末尾追加：
```markdown
- **主题一致**:选定 `THEME` 后,字体确实是该主题的字体(editorial=Archivo,非系统
  默认——抽帧确认,字体加载失败会静默回退)。切 `teal` 应逐帧回到旧青色外观。
- **主题 × 锚点正交**:editorial/teal 各在 `ANCHOR="bottom"/"top"` 下抽一帧,四种组合
  都满足三条规则(可读/不挡脸/分辨率无关)。
```

- [ ] **Step 4: 终检——两主题 tsc 通过**

Run：
```bash
cp skills/video-to-remotion/examples/*.ts skills/video-to-remotion/examples/*.tsx work/theme-harness/src/ 2>/dev/null; true
cp skills/video-to-remotion/examples/components/*.tsx work/theme-harness/src/components/
cd work/theme-harness
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"editorial\"'))"
npx tsc --noEmit
node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"teal\"'))"
npx tsc --noEmit
```
Expected: 两次都 PASS。

- [ ] **Step 5: 确认无残留写死青色**

Run（在真身里搜旧硬编码色值，应只剩 themes.ts 的 teal 定义）：
```bash
cd skills/video-to-remotion
grep -rn "26CAA8\|0C141C\|F5F8F9\|B7C6CE" examples/ || echo "no stray hardcoded colors"
```
Expected: 命中仅在 `examples/themes.ts`（teal 主题定义）；`anim.tsx`/`components/*` 无命中。若组件里仍有，改为 `T.color.*`。

- [ ] **Step 6: 主题 × 锚点 4 组合抽帧（spec §8 正交性验收）**

在脚手架里对 editorial/teal × bottom/top 各抽一帧（用 LowerThird 窗口帧 252）。临时改 `anim.tsx` 的 `ANCHOR` 与 `themes.ts` 的 `THEME`：
```bash
cd work/theme-harness
set_theme(){ node -e "let f='src/themes.ts',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const THEME: ThemeName = \"[a-z]+\"/,'const THEME: ThemeName = \"'+process.argv[1]+'\"'))" "$1"; }
set_anchor(){ node -e "let f='src/anim.tsx',s=require('fs').readFileSync(f,'utf8');require('fs').writeFileSync(f,s.replace(/const ANCHOR = \"[a-z]+\" as \"bottom\" \| \"top\"/,'const ANCHOR = \"'+process.argv[1]+'\" as \"bottom\" | \"top\"'))" "$1"; }
for th in editorial teal; do for an in bottom top; do
  set_theme $th; set_anchor $an
  npx remotion still src/index.ts DemoAll out/combo-$th-$an.png --frame=252
done; done
# 抽完把 anim.tsx 的 ANCHOR 改回 bottom(真身未动,这里只动脚手架副本)
set_anchor bottom
```
Read `out/combo-editorial-bottom.png`、`combo-editorial-top.png`、`combo-teal-bottom.png`、`combo-teal-top.png`。
Expected: 四张都满足三条规则——名条随主题变外观(editorial 骑 scrim/Archivo,teal 青卡),随锚点贴对应边(top 时清出底部),都不挡脸中心、不出血。

- [ ] **Step 7: 提交**

```bash
git add skills/video-to-remotion/SKILL.md
git commit -m "docs(video-to-remotion): document THEME switch, fonts dep, add-a-theme recipe"
```

- [ ] **Step 8: 清理脚手架（可选）**

脚手架在 `work/`（gitignored），可留作下次调试。若要清：
```bash
rm -rf work/theme-harness
```

<!-- APPEND-MARKER -->
