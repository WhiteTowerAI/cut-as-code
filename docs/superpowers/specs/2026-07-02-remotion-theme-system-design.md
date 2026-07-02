# video-to-remotion 可扩展主题系统 — 设计文档

- 日期:2026-07-02
- 状态:待评审(实现前)
- 范围:`skills/video-to-remotion/`
- 相关记忆:[[remotion-scrim-card-legibility]]、[[remotion-overlay-two-pass]]

## 1. 背景与目标

`video-to-remotion` 目前只有**一套**设计语言(青色 `#26CAA8` + 深色卡片 +
系统字体 + 平淡淡入)。所有视觉决定散落在 `anim.tsx` 的常量和 7 个组件的内联
样式里。要"换个更高级的外观",今天只能逐个改组件——每加一种风格就重写一遍。

**目标(按优先级):**

1. **可扩展的主题系统**:新增一种风格 = 新增一份"风格数据",**不改组件代码**。
   用户明确表示后续会加入多种风格,不接受"重复造轮子"。
2. **第一个新主题:`editorial`**(纪录片风,Vox / Johnny Harris 血统)——
   暖色调、精选无衬线字体、细金线分隔、编排式入场动画、**无颗粒**。
3. **保留现有青色风为 `teal` 主题**,像素级不变,零回归。
4. 一个开关切换,内容不变。主题与现有 `ANCHOR`(上/下锚定)开关正交。

**非目标:** 不改 `analyze_content.py` / `draft_cues.py` / `probe.py`(图形*类型*
不变);不改 cue sheet 的字段结构;不加胶片颗粒(已决定去掉)。

## 2. 三条不可动摇的规则

主题系统怎么变,这三条(本 skill 的立身之本)必须在**每一个主题**下都成立:

1. **在任意画面上可读** —— 卡片/遮罩自带背景,不做深色文字浮在深色画面上。
2. **锚定到边、不挡脸** —— 沿用 `ANCHOR`,默认底部安全区。
3. **分辨率无关** —— 尺寸用画布高度的百分比(`useUnit`),不写死像素。

任何新主题的数据都不允许破坏这三条;自检环节逐条验收。

## 3. 架构:三层,让"加风格 = 填数据"

把今天散在各处的视觉决定收拢成三层。组件变"哑巴",只读当前主题;风格变
"数据"。

```
第 1 层  主题数据 (themes.ts)   ← 加新风格只动这里
   THEME 开关 → 从 THEMES 表选出当前主题对象 T
        │
第 2 层  通用积木 (anim.tsx)     ← 造一次,所有主题共用
   <Surface> <Rule> <Kicker> 等原始组件 + 动画预设,全部读 T
        │
第 3 层  7 个图形组件 (components/*)  ← 只管布局与锚定,不含具体样式值
   Intro / SectionCard / LowerThird / StatCallout / KeypointCallout /
   ListReveal / Outro —— 用第 2 层积木拼装,主题无关
```

**关键结果:** `FinalEdit.tsx` 的 cue sheet(`line1/line2`、`kicker/title`、
`value/label`)完全不变;老项目的 cue sheet 在任意主题下都能渲染。

### 3.1 一个开关

`themes.ts` 顶部:

```ts
export const THEME: ThemeName = "editorial";   // "editorial" | "teal" | 以后新增
```

与 `anim.tsx` 里的 `ANCHOR` 是**两个独立开关**:主题管"长什么样",锚点管
"贴哪条边",4 种组合(editorial/teal × top/bottom)都要能工作。

### 3.2 主题数据的形状(Theme 契约)

这就是"填表"的那张表。字段覆盖两种风格间**真实存在**的差异,而非只有颜色:

```ts
export type Theme = {
  name: ThemeName;
  // — 字体 —
  font: string;              // CSS font-family;'editorial' 用 Archivo,'teal' 用 system-ui
  weight: { heavy: number; med: number; light: number };
  // — 调色板 —
  color: { text; textMuted; accent; scrimBase: string };
  // — 小卡片(LowerThird/Stat/Keypoint)的底板处理 —
  //   对象 = 实心卡片(teal);null = 无卡片、文字骑在局部遮罩上(editorial)
  card: { bg; border; radius; shadow: string } | null;
  // — 分隔/强调元件 —
  rule: "bar" | "hairline";  // 粗左/下竖条(teal) | 细线+强调色小段(editorial)
  // — kicker 排版 —
  kicker: { case: "upper" | "none"; spacingEm: number };
  // — 入场动画预设(见 3.4)—
  motion: "fade" | "stagger";
};
```

> **扩展性边界(如实说明):** 绝大多数未来风格 = 纯填上面的值,零组件改动。
> 只有当某个新风格需要一种**全新的结构原语**(例如毛玻璃模糊、整帧擦除、
> 动态描边框)时,才需要:①给 `Theme` 加一个字段,②在对应的第 2 层积木里加
> 一个分支。这是一次性的、共享的小改动,不是每加一个风格重来一遍。设计已把
> "换皮肤"和"换结构"分开,常见情况落在纯数据。

### 3.3 通用积木(第 2 层,造一次)

放进 `anim.tsx`,全部从当前主题 `T` 取值,组件不再写死样式:

- **`<Surface>`** —— 包裹文字的底板。`T.card` 是对象就渲染实心卡片(圆角+投影+
  强调边),是 `null` 就渲染透明容器(文字靠共享 `Scrim` 保证可读)。
  一处收敛 LowerThird/Stat/Keypoint 今天各自重复的卡片样式。
- **`<Rule>`** —— 分隔/强调线。`T.rule === "bar"` 渲染粗竖条(青色风的左边条),
  `=== "hairline"` 渲染细线+强调色小段(纪录片风那条)。
- **`<Kicker>`** —— 小标题文字,按 `T.kicker` 决定大写与字间距、按 `T.color.accent`
  上色。
- 现有的 `Scrim`、`useFade`、`useUnit`、`anchorJustify/anchorPad` 保留;`Scrim`
  的底色改读 `T.color.scrimBase`。

### 3.4 动画预设(第 2 层)

`T.motion` 选择**入场家族**,组件按它分支:

- **`"fade"`(teal):不是"统一淡入"——而是逐组件保留今天各自的入场。**
  现有 7 个组件的入场本就不同(Intro 上滑淡入、LowerThird 左滑、SectionCard
  描条+内容淡入、Keypoint 上浮、StatCallout 数字滚动、ListReveal 逐条错峰、
  Outro 纯淡入)。teal 路径**原样保留这些**,不得压平成单一动画——否则违反
  §4.1 的零回归承诺。实现上:各组件把现有入场代码留作 `T.motion !== "stagger"`
  的分支。
- **`"stagger"`(editorial):新增的编排式登场** —— kicker 淡入上浮 → 名字
  `clip-path` 从左到右擦出 → `<Rule>` 宽度 0→满(描线)→ 头衔淡入上浮,各错开
  几帧。统一用现有的克制 `EASE_OUT`,**不弹跳**(纪录片规矩)。
- **`useEntrance(role)`** 封装 `"stagger"` 家族:传入元素角色(kicker/title/
  rule/sub),返回该帧的 `{opacity, transform, clipPath?}`。配套辅助
  `useDraw()`(宽 0→满,给 `<Rule>` 描线)、`useClipReveal()`(inset 擦除)。
- 新主题若要全新入场:给 `T.motion` 增一个枚举值 + 加一个 `useEntrance` 家族
  分支,组件里多一条 `else if`。常见的换色/换字体主题直接复用 `"fade"` 或
  `"stagger"`,无需新动画。

## 4. 两个起始主题的数据

### 4.1 `teal`（保留现状，零回归）

数值直接搬今天 `anim.tsx` 的常量，确保像素级一致：

- `font: "system-ui, ..."`,weight heavy/med/light = 800/600/500
- color:text `#F5F8F9`、textMuted `#B7C6CE`、accent `#26CAA8`、scrimBase `#0C141C`
- `card: { bg:"rgba(12,20,28,0.82)", border:"0.8u solid accent(左)", radius:"1.2u", shadow:"0 6px 24px rgba(0,0,0,0.4)" }`(数值照搬今天各组件)
- `rule: "bar"`、`kicker: { case:"upper", spacingEm:0.04 }`、`motion: "fade"`

验收标准：切到 `teal` 后，与改动前的渲染逐帧一致。

### 4.2 `editorial`（本次新增，用户选定的"选项 1"）

- `font`：**Archivo**，经 `@remotion/google-fonts/Archivo` 加载（免费、OFL、
  Remotion 惯用做法）。weight heavy/med/light = 800/600/500。
- color：text `#F4F1EA`、textMuted `#C7C2B6`、accent 金 `#E0B252`、
  scrimBase `#0B0D10`。**无青色**。
- `card: null` → 文字骑在柔和局部遮罩上（不是实心卡片）。
- `rule: "hairline"` → 2px 细线，左端一小段金色、其余淡白。
- `kicker: { case:"upper", spacingEm:0.28 }`。
- `motion: "stagger"`。
- **无颗粒**（已决定）。质感全靠字体、字距、细金线、暖色调承担。

## 5. 字体加载

- `editorial` 在其主题模块里 `import { loadFont } from "@remotion/google-fonts/Archivo"`
  并在模块顶层调用，拿到的 family 填进 `font`。
- `teal` 用系统字体栈，无需加载。
- 只有**当前选中**主题需要其字体可用；`@remotion/google-fonts` 版本与
  `remotion` 同一 4.x。
- SKILL.md 的"依赖/脚手架"补一句：装 `@remotion/google-fonts`（与 remotion 同版本）。

## 6. 涉及的文件

| 文件 | 改动 |
|---|---|
| `examples/themes.ts` | **新增**。`Theme` 类型、`THEMES` 表（editorial + teal）、`THEME` 开关、导出当前主题 `T`。加新风格只动这里。 |
| `examples/anim.tsx` | 保留 TIMING/EASE/useUnit/anchor 助手/Scrim；新增第 2 层积木 `<Surface> <Rule> <Kicker>`、`useEntrance/useDraw/useClipReveal`；常量改为从 `T` 读。 |
| `examples/components/*.tsx`（7 个） | 去掉写死的颜色/字体/卡片样式，改用第 2 层积木拼装；保留各自的**布局与锚定**逻辑。 |
| `examples/FinalEdit.tsx` | 不变（cue sheet 字段不变）。 |
| `examples/Root.tsx` | 不变。 |
| `reference/graphic-types.md` | 不变（图形类型不变）。 |
| `SKILL.md` | 记录 `THEME` 开关（挨着 `ANCHOR` 讲）、`@remotion/google-fonts` 依赖、"加新主题"配方（见 §7）、两条新自检项（字体已加载；主题在任意画面/锚点下都符合三条规则）。 |

## 7. 以后加一种新风格的配方（写进 SKILL.md）

1. 在 `themes.ts` 的 `THEMES` 表里加一个条目，填 `Theme` 的各字段。
2. 若用新字体：在该主题模块加一次 `loadFont`。
3. 把 `THEME` 开关改成新名字，渲染自检。
4. **仅当**需要全新结构（毛玻璃/整帧擦除等）：给 `Theme` 加一个字段 + 在对应的
   第 2 层积木加一个分支——这是唯一会碰到组件层的情况，且一次加好后续复用。

> 常见情况（换字体/换色/换卡片或细线/换入场预设）**只动第 1 步**。

## 8. 测试与自检

无既有测试框架，沿用本 repo"渲染 + 截图肉眼验收"的自检方式：

- **teal 零回归**：切 `teal`，抽几帧与改动前对比，确认一致。
- **editorial 通过三条规则**：在真实画面上抽帧，逐条验收可读/不挡脸/分辨率无关。
- **字体已生效**：截图确认是 Archivo 而非系统字体。
- **动画**：`stagger` 入场顺序正确、克制不弹跳；`teal` 的 `fade` 行为不变。
- **4 种组合**：editorial/teal × top/bottom 各抽一帧，确认主题与锚点正交。
- 用 `npx remotion still ... FinalEdit` 抽帧（在真实画面上看图形）。

## 9. 风险

- **低**：主题/积木重构是直接的 token 化，`teal` 用原值兜底防回归。
- **中**：`editorial` 的 `stagger` 入场需要在实机上调时序手感（`clip-path` 擦入 +
  描线 + 交错），实现时抽帧微调。
- 字体加载失败会静默回退系统字体——自检里显式截图确认，避免"看起来像没换"。

## 10. 待评审确认点

1. 三层架构与 `Theme` 契约字段是否够用（尤其"扩展性边界"那段说明可接受吗）。
2. `editorial` 的具体数值（金色 `#E0B252`、字体 Archivo）就这么定，还是实现时再调。
3. 是否现在就想预留未来风格的名字（可选，不影响架构）。


