import {
  CANVAS_CONFETTI_RECIPES,
  METEOCONS_ICONS,
  MOJS_RECIPES,
  TSPARTICLES_RECIPES,
} from "./sticker_recipe_catalog.mjs";

export const STICKER_CATEGORIES = Object.freeze([
  "sticker-celebration",
  "sticker-reaction",
  "sticker-success",
  "sticker-warning",
  "sticker-notification",
  "sticker-communication",
  "sticker-action",
  "sticker-navigation",
  "sticker-business",
  "sticker-technology",
  "sticker-media",
  "sticker-time",
  "sticker-weather",
  "sticker-people-lifestyle",
  "sticker-object",
  "sticker-emphasis",
]);

const CATEGORY_DETAILS = Object.freeze({
  "sticker-celebration": {
    tags: ["celebration", "festive", "positive"],
    english: ["celebration", "celebrate", "achievement", "milestone", "launch", "won", "festive reveal"],
    chinese: ["庆祝", "赢了", "喜庆揭晓", "成就", "里程碑", "发布"],
    use: "a win, launch, milestone, or earned celebratory reveal",
    best: "A genuine positive achievement or announcement deserves a festive visual payoff",
    avoid: "The event is neutral, negative, sensitive, or not genuinely celebratory",
  },
  "sticker-reaction": {
    tags: ["reaction", "affection", "positive"],
    english: ["love", "appreciation", "favorite", "thank you", "star", "audience reaction", "rating"],
    chinese: ["喜欢", "感谢", "爱心回应", "收藏", "五星好评", "观众反应"],
    use: "affection, appreciation, a favorite, or a positive audience reaction",
    best: "The narration expresses affection, appreciation, approval, or a favorite",
    avoid: "The cue is a formal completion status rather than an emotional reaction",
  },
  "sticker-success": {
    tags: ["success", "confirmation", "positive"],
    english: ["completed", "successful", "approved", "confirmed", "done", "passed", "check mark"],
    chinese: ["完成", "成功", "确认", "通过", "搞定", "无误"],
    use: "completion, approval, confirmation, or a verified successful result",
    best: "A task, verification, transaction, or decision has clearly succeeded",
    avoid: "The outcome is still pending, uncertain, failed, or merely being discussed",
  },
  "sticker-warning": {
    tags: ["warning", "urgent", "caution"],
    english: ["warning", "danger", "risk", "hazard", "urgent", "critical", "problem", "caution"],
    chinese: ["警告", "危险", "风险", "隐患", "紧急", "严重问题", "注意"],
    use: "danger, risk, failure, caution, or an urgent problem",
    best: "The spoken point identifies a real risk, failure, hazard, or urgent exception",
    avoid: "The message is neutral, routine, positive, or too speculative to justify alarm",
  },
  "sticker-notification": {
    tags: ["notification", "reminder", "attention"],
    english: ["notifications", "subscribe", "bell", "reminder", "incoming", "update", "received"],
    chinese: ["通知", "订阅", "铃铛", "提醒", "更新", "收到"],
    use: "a notification, reminder, subscription prompt, or incoming update",
    best: "A speaker asks viewers to subscribe, enable notifications, or notice a reminder",
    avoid: "The cue communicates immediate physical danger rather than a routine notification",
  },
  "sticker-communication": {
    tags: ["communication", "message", "contact"],
    english: ["email", "reply", "message", "conversation", "call", "chat", "incoming"],
    chinese: ["邮件", "回复", "消息", "聊天", "电话", "私信"],
    use: "email, chat, calling, messaging, or direct contact",
    best: "The narration explicitly mentions sending, receiving, or replying to a message or call",
    avoid: "The communication channel is incidental and does not carry the narrative point",
  },
  "sticker-action": {
    tags: ["action", "control", "instruction"],
    english: ["download", "upload", "play", "pause", "start", "action", "continue"],
    chinese: ["下载文件", "上传文档", "播放", "暂停", "操作", "开始"],
    use: "a concrete viewer action, command, or media control",
    best: "The speaker gives a clear instruction or names a specific control action",
    avoid: "The verb is metaphorical or the audience is not expected to perform the action",
  },
  "sticker-navigation": {
    tags: ["navigation", "direction", "movement"],
    english: ["next", "previous", "back", "location", "left", "scroll", "direction"],
    chinese: ["下一步", "返回", "向左", "向下滚动", "位置", "上一页"],
    use: "direction, location, movement, or progression through steps",
    best: "The narration points to a direction, destination, location, or next step",
    avoid: "No spatial or sequential relationship needs to be communicated",
  },
  "sticker-business": {
    tags: ["business", "professional", "work"],
    english: ["business opportunity", "professional work", "job offer", "career", "company", "project", "office"],
    chinese: ["商业机会", "职场工作", "职位", "公司项目", "办公业务"],
    use: "business, professional work, a company, career, or office activity",
    best: "The spoken point concerns work, a company, a job, or a professional opportunity",
    avoid: "The object appears literally but the topic has no business or professional meaning",
  },
  "sticker-technology": {
    tags: ["technology", "digital", "system"],
    english: ["cloud computing", "digital folder", "computer monitor", "technology infrastructure", "online data", "storage", "platform"],
    chinese: ["云计算", "数据存储", "数字文件夹", "电脑显示器", "技术", "基础设施"],
    use: "software, devices, cloud systems, files, data, or digital infrastructure",
    best: "The narration names a digital system, device, file, cloud service, or technical process",
    avoid: "A similarly named object is being discussed in a physical or weather context",
  },
  "sticker-media": {
    tags: ["media", "audio", "playback"],
    english: ["sound", "mute", "audio", "video playback", "music", "volume", "media control"],
    chinese: ["音量", "声音", "音频", "视频播放", "音乐", "播放控制"],
    use: "audio, video, music, volume, or media playback",
    best: "The narration directly discusses sound, music, video, volume, or playback",
    avoid: "Media controls are visible in the footage but not relevant to the spoken meaning",
  },
  "sticker-time": {
    tags: ["time", "schedule", "deadline"],
    english: ["schedule", "date", "calendar", "time", "deadline", "appointment", "running time"],
    chinese: ["安排日期", "日历", "时间", "截止时间", "预约"],
    use: "time, dates, schedules, appointments, or deadlines",
    best: "A date, deadline, appointment, duration, or schedule is central to the cue",
    avoid: "Timing is incidental and no date, duration, or deadline needs emphasis",
  },
  "sticker-weather": {
    tags: ["weather", "forecast", "environment"],
    english: ["thunderstorm forecast", "rain", "sunny weather", "snow", "clear night", "weather", "sky"],
    chinese: ["雷暴天气预报", "下大雨", "晴朗天气", "下雪", "晴朗夜空"],
    use: "literal weather, a forecast, climate, or an environmental condition",
    best: "The speaker literally refers to current weather, a forecast, or an environmental condition",
    avoid: "Weather language is metaphorical, such as a storm of criticism or a sunny outlook",
  },
  "sticker-people-lifestyle": {
    tags: ["people", "profile", "social"],
    english: ["person", "user profile", "people", "community", "personal account", "speaker", "contact"],
    chinese: ["人物", "联系人", "用户资料", "社区", "个人账户", "讲者"],
    use: "a person, profile, account, contact, speaker, or community",
    best: "A person, user, contact, account, or community role is explicitly discussed",
    avoid: "The cue concerns an organization or abstract audience rather than an identifiable person role",
  },
  "sticker-object": {
    tags: ["object", "literal", "everyday"],
    english: ["home", "coffee", "car light", "bright idea", "everyday object", "literal object", "physical item"],
    chinese: ["日常物品", "家里", "咖啡", "车灯", "主意"],
    use: "a literal physical object, place, food, vehicle, or everyday item",
    best: "The named object itself is visually useful and immediately recognizable in context",
    avoid: "The object name is metaphorical or a more specific semantic category communicates the point better",
  },
  "sticker-emphasis": {
    tags: ["emphasis", "impact", "abstract"],
    english: ["impact beat", "attention pulse", "energy burst", "ripple emphasis", "shockwave", "abstract energy", "dramatic impact"],
    chinese: ["强调", "强烈冲击", "脉冲强调", "能量爆发", "涟漪提示", "冲击波", "抽象能量"],
    use: "an abstract impact, pulse, energy accent, or non-literal emphasis beat",
    best: "The edit needs a compact abstract hit without introducing a literal icon or new information",
    avoid: "A literal status, object, or action would communicate the spoken meaning more precisely",
  },
});

const VARIANT_SUFFIXES = new Set(["filled", "outline", "twotone", "loop"]);
const STYLE_LABELS = Object.freeze({ filled: "Filled", outline: "Outline", twotone: "Twotone", loop: "Loop" });
const NON_SEMANTIC_TOKENS = new Set(["alt", "md", "simple"]);

const SUBJECT_TRANSLATIONS = Object.freeze({
  account: "账户", alert: "警告", arrow: "箭头", bell: "铃铛", briefcase: "公文包", calendar: "日历",
  car: "汽车", chat: "聊天", check: "勾选", chevron: "方向箭头", cloud: "云",
  coffee: "咖啡", confirm: "确认", download: "下载", email: "邮件", file: "文件",
  filter: "筛选", folder: "文件夹", heart: "爱心", home: "家", lightbulb: "灯泡",
  home: "家里", map: "地图", marker: "位置标记", monitor: "显示器", moon: "月亮", pause: "暂停",
  people: "人物", person: "人物", phone: "电话", play: "播放", profile: "个人资料", star: "星星", sunny: "晴天", user: "用户",
  upload: "上传", volume: "音量", watch: "手表", hazard: "危险", lights: "灯",
  document: "文档", clipboard: "剪贴板", lock: "锁", key: "钥匙", shield: "盾牌",
  cookie: "饼干", beer: "啤酒", compass: "指南针", location: "位置", message: "消息",
});

const CLASSIFIERS = Object.freeze([
  ["sticker-business", /(?:^|-)(?:briefcase|business|office|work|job|career|bank|wallet|cart|store|receipt|invoice|currency|money|cash)(?:-|$)/u],
  ["sticker-success", /(?:^|-)(?:confirm|check-all|check-list|success|verified|approved)(?:-|$)/u],
  ["sticker-notification", /(?:^|-)(?:bell|alarm|notification|reminder)(?:-|$)/u],
  ["sticker-warning", /(?:^|-)(?:alert|hazard|warning|error|danger|brake-alert)(?:-|$)/u],
  ["sticker-communication", /(?:^|-)(?:email|chat|phone|message|comment|contact|send)(?:-|$)/u],
  ["sticker-people-lifestyle", /(?:^|-)(?:person|people|user|account|profile|baby|group|community)(?:-|$)/u],
  ["sticker-action", /(?:^|-)(?:download|upload|play|pause|stop|search|filter|edit|save|refresh|reload|undo|redo|login|logout|menu|add|remove|delete|trash|power|switch|zoom|enter|exit|share)(?:-|$)/u],
  ["sticker-navigation", /(?:^|-)(?:arrow|arrows|chevron|map|marker|compass|direction|navigation|location|pin)(?:-|$)/u],
  ["sticker-media", /(?:^|-)(?:volume|music|microphone|audio|video|camera|image|photo|headphone|speaker)(?:-|$)/u],
  ["sticker-time", /(?:^|-)(?:calendar|watch|clock|timer|hourglass|time|date)(?:-|$)/u],
  ["sticker-weather", /(?:^|-)(?:sunny|moon|rain|snow|weather|wind|fog|tornado|lightning|rainbow)(?:-|$)/u],
  ["sticker-reaction", /(?:^|-)(?:heart|star|emoji|smile|favorite|like|thumb|rating)(?:-|$)/u],
  ["sticker-technology", /(?:^|-)(?:cloud|file|folder|monitor|laptop|desktop|tablet|cellphone|computer|cog|settings|wifi|bluetooth|code|braces|database|server|security|shield|lock|key|bug|cookie|gauge)(?:-|$)/u],
  ["sticker-celebration", /(?:^|-)(?:gift|trophy|party|celebrate|firework|champagne|cake)(?:-|$)/u],
  ["sticker-emphasis", /(?:^|-)(?:circle|square|spark|pulse|loading|spinner|burst|ripple|wave)(?:-|$)/u],
]);

const CANONICAL_LINE_MD = Object.freeze({
  "sticker-celebration": /^(?:gift|trophy|cake|champagne)(?:-|$)/u,
  "sticker-reaction": /^(?:heart|star)(?:-|$)/u,
  "sticker-success": /^(?:confirm|check-all)(?:-|$)/u,
  "sticker-warning": /^(?:alert|hazard-lights|warning)(?:-|$)/u,
  "sticker-notification": /^bell(?:-|$)/u,
  "sticker-communication": /^(?:email|chat|phone|message)(?:-|$)/u,
  "sticker-action": /^(?:download|upload|play|pause)(?:-|$)/u,
  "sticker-navigation": /^(?:arrow|chevron|map-marker|location)(?:-|$)/u,
  "sticker-business": /^briefcase(?:-|$)/u,
  "sticker-technology": /^(?:cloud|folder|monitor)(?:-|$)/u,
  "sticker-media": /^volume(?:-|$)/u,
  "sticker-time": /^(?:calendar|watch)(?:-|$)/u,
  "sticker-weather": /^(?:sunny|moon)(?:-|$)/u,
  "sticker-people-lifestyle": /^person(?:-|$)/u,
  "sticker-object": /^(?:home|coffee|car|lightbulb)(?:-|$)/u,
});

const NON_LINE_SPECS = Object.freeze({
  "confetti-side-cannons": ["sticker-celebration", "Side Confetti Cannons", "confetti cannons firing inward from both edges", ["side cannons", "edge celebration"], ["双侧彩带", "庆祝礼炮"], ["confetti", "cannons", "side-entry", "full-frame"]],
  "confetti-center-burst": ["sticker-celebration", "Center Confetti Burst", "a compact confetti explosion from the frame center", ["center confetti burst", "celebration pop"], ["中心彩带", "庆祝爆发"], ["confetti", "center-burst", "particles", "compact"]],
  "confetti-top-rain": ["sticker-celebration", "Falling Confetti Rain", "confetti falling across the frame from above", ["confetti rain", "falling celebration"], ["彩带飘落", "庆祝彩雨"], ["confetti", "falling", "top-entry", "full-frame"]],
  "confetti-bottom-fountain": ["sticker-celebration", "Rising Confetti Fountain", "confetti spraying upward from the lower frame", ["confetti fountain", "rising celebration"], ["彩带喷泉", "向上庆祝"], ["confetti", "fountain", "bottom-entry", "full-frame"]],
  "confetti-star-burst": ["sticker-reaction", "Star Confetti Burst", "star-shaped confetti bursting from the center", ["star burst", "five star reaction"], ["星星爆发", "五星回应"], ["stars", "confetti", "center-burst", "playful"]],
  "confetti-heart-burst": ["sticker-reaction", "Heart Confetti Burst", "heart-shaped confetti bursting outward with affection", ["heart burst", "love reaction"], ["爱心爆发", "喜欢回应"], ["hearts", "confetti", "center-burst", "affection"]],
  "confetti-firework-triple": ["sticker-celebration", "Triple Confetti Firework", "three timed confetti explosions creating a large festive payoff", ["triple firework", "big celebration"], ["三连烟花", "大型庆祝"], ["confetti", "firework", "triple-burst", "high-impact"]],
  "confetti-realistic": ["sticker-celebration", "Realistic Confetti Celebration", "layered confetti spreading and falling like a physical celebration", ["realistic confetti", "earned celebration"], ["真实彩带", "庆祝时刻"], ["confetti", "layered", "falling", "full-frame"]],
  "confetti-mini-pop": ["sticker-celebration", "Mini Confetti Pop", "a small quick confetti pop for a modest positive beat", ["mini confetti", "small celebration"], ["迷你彩带", "小型庆祝"], ["confetti", "mini-pop", "compact", "light"]],
  "confetti-slow-fall": ["sticker-celebration", "Slow Falling Confetti", "gentle confetti drifting down for a sustained celebratory hold", ["slow confetti", "gentle celebration"], ["缓慢彩带", "柔和庆祝"], ["confetti", "slow-fall", "full-frame", "gentle"]],
  "mojs-spark-ring": ["sticker-emphasis", "Spark Emphasis Ring", "short sparks radiating around one compact focal point", ["spark ring", "attention ring"], ["火花环", "注意提示"], ["sparks", "ring", "radial", "compact"]],
  "mojs-shockwave": ["sticker-emphasis", "Expanding Shockwave Rings", "concentric rings expanding rapidly from an impact point", ["shockwave", "impact rings"], ["冲击波", "冲击圆环"], ["rings", "shockwave", "expanding", "impact"]],
  "mojs-orbit-burst": ["sticker-emphasis", "Orbiting Particle Burst", "particles sweeping around an arc before dispersing", ["orbit burst", "orbital accent"], ["轨道爆发", "环绕强调"], ["particles", "orbit", "arc", "dynamic"]],
  "mojs-celebration-burst": ["sticker-celebration", "Celebration Particle Burst", "colorful particles expanding in a compact celebratory burst", ["celebration burst", "party particles"], ["庆祝爆发", "派对粒子"], ["particles", "celebration", "radial", "compact"]],
  "mojs-star-burst": ["sticker-reaction", "Star Polygon Burst", "small star polygons radiating from a reaction point", ["star reaction", "rating burst"], ["星星回应", "评分爆发"], ["stars", "polygon", "radial", "reaction"]],
  "mojs-ripple-ring": ["sticker-emphasis", "Soft Ripple Rings", "multiple soft rings expanding like ripples around a focal point", ["ripple emphasis", "soft pulse"], ["涟漪强调", "柔和脉冲"], ["rings", "ripple", "expanding", "soft"]],
  "mojs-comet-trail": ["sticker-emphasis", "Directional Comet Trail", "a fast spark trail sweeping diagonally through one beat", ["comet trail", "directional energy"], ["彗星轨迹", "方向能量"], ["sparks", "trail", "directional", "fast"]],
  "mojs-success-pop": ["sticker-success", "Success Confirmation Pop", "a compact green burst reinforcing a completed or approved result", ["success pop", "confirmation burst"], ["成功弹出", "确认爆发"], ["success", "burst", "confirmation", "compact"]],
  "mojs-warning-pulse": ["sticker-warning", "Warning Triangle Pulse", "urgent triangular particles pulsing around a warning point", ["warning pulse", "danger triangle"], ["警告脉冲", "危险三角"], ["warning", "triangle", "pulse", "urgent"]],
  "mojs-corner-sparks": ["sticker-emphasis", "Four Corner Sparks", "spark accents firing inward from all four frame corners", ["corner sparks", "frame emphasis"], ["四角火花", "画面强调"], ["sparks", "corners", "inward", "full-frame"]],
  "tsparticles-fireworks": ["sticker-celebration", "Multi-Burst Fireworks", "multiple colorful fireworks launching and bursting across a wide field", ["fireworks", "festival celebration"], ["烟花", "节日庆祝"], ["fireworks", "multi-burst", "full-frame", "high-impact"]],
  "tsparticles-fountain": ["sticker-emphasis", "Particle Energy Fountain", "a continuous particle fountain rising from the lower frame", ["particle fountain", "rising energy"], ["粒子喷泉", "上升能量"], ["particles", "fountain", "bottom-entry", "continuous"]],
  "tsparticles-fireflies": ["sticker-emphasis", "Ambient Firefly Field", "small glowing particles drifting gently across a wide area", ["firefly field", "gentle particles"], ["萤火虫", "柔和粒子"], ["particles", "fireflies", "drifting", "gentle"]],
  "tsparticles-linked-field": ["sticker-emphasis", "Linked Particle Network", "moving particles connecting into a responsive network field", ["linked particles", "network field"], ["连接粒子", "网络场"], ["particles", "links", "network", "full-frame"]],
});

const WEATHER_SPECS = Object.freeze({
  "clear-day": ["Clear Day Weather", "a bright sun representing clear daytime weather", ["clear day", "sunny forecast"], ["晴天", "白天晴朗"], ["sun", "clear", "daytime"]],
  "clear-night": ["Clear Night Weather", "a clear moonlit sky representing calm nighttime weather", ["clear night", "night forecast"], ["晴朗夜晚", "夜间天气"], ["moon", "clear", "night"]],
  "partly-cloudy-day": ["Partly Cloudy Day", "sun and clouds showing a partly cloudy daytime forecast", ["partly cloudy", "mixed clouds"], ["多云间晴", "局部多云"], ["clouds", "sun", "daytime"]],
  rain: ["Rain Shower Weather", "a rain cloud producing a clear literal rainfall cue", ["rain", "rainy forecast"], ["下雨", "降雨预报"], ["rain", "cloud", "falling"]],
  thunderstorms: ["Thunderstorm Cloud", "a storm cloud flashing with lightning for severe weather", ["thunderstorm", "storm forecast"], ["雷暴", "暴风雨预报"], ["storm", "lightning", "cloud"]],
  snow: ["Falling Snow Weather", "a cloud releasing snow for a literal winter forecast", ["snow", "snowy weather"], ["下雪", "降雪天气"], ["snow", "cloud", "falling"]],
  snowflake: ["Single Snowflake", "a rotating snowflake marking cold or snowy conditions", ["snowflake", "cold weather"], ["雪花", "寒冷天气"], ["snowflake", "cold", "rotation"]],
  "lightning-bolt": ["Lightning Bolt Weather", "a bright lightning bolt marking an electrical storm", ["lightning", "storm warning"], ["闪电", "雷雨警告"], ["lightning", "bolt", "electric"]],
  wind: ["Strong Wind Weather", "flowing wind marks showing a literal windy condition", ["wind", "windy forecast"], ["大风", "刮风预报"], ["wind", "flowing", "air"]],
  fog: ["Dense Fog Weather", "layered mist representing fog and reduced visibility", ["fog", "low visibility"], ["大雾", "低能见度"], ["fog", "mist", "visibility"]],
  rainbow: ["Rainbow Weather", "a colorful rainbow appearing after changing weather", ["rainbow", "weather clearing"], ["彩虹", "雨后放晴"], ["rainbow", "colorful", "clearing"]],
  tornado: ["Tornado Weather", "a rotating funnel cloud communicating dangerous severe weather", ["tornado", "severe wind"], ["龙卷风", "极端大风"], ["tornado", "funnel", "rotation"]],
});

function unique(items) {
  return [...new Set(items.filter(Boolean).map((item) => String(item).trim()).filter(Boolean))];
}

function titleCase(value) {
  return String(value).split("-").filter(Boolean).map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

function categoryForLineMd(base) {
  for (const [category, pattern] of CLASSIFIERS) {
    if (pattern.test(base)) return category;
  }
  return "sticker-object";
}

function motionTags(body) {
  const tags = [];
  if (/stroke-dash(?:array|offset)/u.test(body)) tags.push("draw-in");
  if (/attributeName=["']d["']/u.test(body)) tags.push("morph");
  if (/type=["']rotate["']/u.test(body)) tags.push("rotation");
  if (/type=["']translate["']/u.test(body)) tags.push("movement");
  if (/attributeName=["']opacity["']/u.test(body)) tags.push("fade");
  if (/repeatCount=["']indefinite["']/u.test(body)) tags.push("looping");
  return tags.length ? tags : ["reveal"];
}

function subjectTokens(base) {
  return base.split("-").filter((token) => token && !VARIANT_SUFFIXES.has(token) && !NON_SEMANTIC_TOKENS.has(token));
}

function chineseSubject(base, fallback) {
  const translated = subjectTokens(base).map((token) => SUBJECT_TRANSLATIONS[token]).filter(Boolean);
  return translated.length ? translated.join("") : fallback;
}

function buildIntentKeywords(subject, category, english = [], chinese = [], includeCategory = false) {
  const details = CATEGORY_DETAILS[category];
  const chineseSubjectValue = chinese[0] || details.chinese[0];
  const englishCandidates = unique([
    ...english,
    subject,
    ...(includeCategory ? details.english : []),
    `${subject} icon`,
    `${subject} animation`,
    `${subject} visual cue`,
    `show ${subject}`,
    `animated ${subject}`,
  ]).filter((item) => /^[\x00-\x7f]+$/u.test(item));
  const chineseCandidates = unique([
    ...chinese,
    ...(includeCategory ? details.chinese : []),
    `${chineseSubjectValue}图标`,
    `${chineseSubjectValue}动画`,
    `${chineseSubjectValue}提示`,
  ]).filter((item) => /\p{Script=Han}/u.test(item));
  return [...englishCandidates.slice(0, 10), ...chineseCandidates.slice(0, 6)].slice(0, 16);
}

function makeProfile({ name, subject, description, category, tags = [], english = [], chinese = [], best = [], avoid = [], body = "", includeCategoryIntents = false }) {
  const details = CATEGORY_DETAILS[category];
  const subjectTagValues = subject.toLocaleLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  const tagValues = unique([
    ...tags,
    ...subjectTagValues,
    ...details.tags,
    ...motionTags(body),
    "compact",
  ]).filter((item) => !["sticker", "line-md", "meteocons", "mojs", "tsparticles", "svg", "js"].includes(item));
  while (tagValues.length < 6) tagValues.push(`semantic-${tagValues.length + 1}`);
  const words = name.trim().split(/\s+/u);
  const boundedName = words.length === 1 ? `${name} Reveal` : words.slice(0, 8).join(" ");
  return {
    name: boundedName,
    description: `${description.charAt(0).toUpperCase()}${description.slice(1).replace(/[.\s]+$/u, "")}.`,
    category,
    tags: unique(tagValues).slice(0, 8),
    intent_keywords: buildIntentKeywords(subject, category, english, chinese, includeCategoryIntents),
    best_for: unique([...best, `A spoken reference to ${subject} needs a compact, immediately recognizable cue`, details.best]).slice(0, 4),
    avoid_when: unique([...avoid, `The spoken meaning does not refer to ${subject} or a close synonym`, details.avoid]).slice(0, 4),
  };
}

function buildLineMdProfile(base, bodies) {
  const category = categoryForLineMd(base);
  const details = CATEGORY_DETAILS[category];
  const subject = base.replaceAll("-", " ");
  const visibleName = titleCase(base);
  const motion = motionTags(bodies.join("\n")).join(", ");
  return makeProfile({
    name: visibleName,
    subject,
    description: `A compact ${subject} icon uses ${motion} motion to illustrate ${details.use}`,
    category,
    tags: [...subjectTokens(base), ...motionTags(bodies.join("\n"))],
    english: [subject, `${subject} icon`, `${subject} symbol`],
    chinese: [chineseSubject(base, details.chinese[0])],
    body: bodies.join("\n"),
    includeCategoryIntents: CANONICAL_LINE_MD[category]?.test(base) || false,
  });
}

function buildExplicitProfile(spec) {
  const [category, name, description, english, chinese, tags] = spec;
  const subject = english[0];
  return makeProfile({ name, subject, description, category, english, chinese, tags, body: "", includeCategoryIntents: true });
}

export function semanticBaseForLineMd(name) {
  const tokens = String(name).split("-");
  const variants = [];
  while (tokens.length && VARIANT_SUFFIXES.has(tokens.at(-1))) variants.unshift(tokens.pop());
  return { base: tokens.join("-"), variants };
}

export function metadataForSticker(profile, variants = []) {
  if (!profile) throw new Error("missing semantic profile");
  const styleNames = variants.map((variant) => STYLE_LABELS[variant]).filter(Boolean);
  const metadata = {
    name: styleNames.length ? `${profile.name} (${styleNames.join(" ")})` : profile.name,
    description: profile.description,
    category: profile.category,
    tags: unique([...profile.tags, ...variants]).slice(0, 10),
    intent_keywords: [...profile.intent_keywords],
    best_for: [...profile.best_for],
    avoid_when: [...profile.avoid_when],
  };
  return metadata;
}

export function buildStickerProfiles(lineMdData) {
  const profiles = new Map();
  const grouped = new Map();
  for (const [name, icon] of Object.entries(lineMdData.icons || {})) {
    const { base } = semanticBaseForLineMd(name);
    const bodies = grouped.get(base) || [];
    bodies.push(icon.body || "");
    grouped.set(base, bodies);
  }
  for (const [name, alias] of Object.entries(lineMdData.aliases || {})) {
    const { base } = semanticBaseForLineMd(name);
    const parent = lineMdData.icons?.[alias.parent];
    const bodies = grouped.get(base) || [];
    bodies.push(parent?.body || "");
    grouped.set(base, bodies);
  }
  for (const [base, bodies] of [...grouped].sort(([left], [right]) => left.localeCompare(right))) {
    profiles.set(`line-md:${base}`, buildLineMdProfile(base, bodies));
  }

  for (const entry of CANVAS_CONFETTI_RECIPES) profiles.set(entry.id, buildExplicitProfile(NON_LINE_SPECS[entry.id]));
  for (const entry of MOJS_RECIPES) profiles.set(entry.id, buildExplicitProfile(NON_LINE_SPECS[entry.id]));
  for (const icon of METEOCONS_ICONS) {
    const [name, description, english, chinese, tags] = WEATHER_SPECS[icon];
    profiles.set(`meteocons-${icon}`, makeProfile({
      name,
      subject: english[0],
      description,
      category: "sticker-weather",
      english,
      chinese,
      tags,
      includeCategoryIntents: true,
    }));
  }
  for (const entry of TSPARTICLES_RECIPES) profiles.set(entry.id, buildExplicitProfile(NON_LINE_SPECS[entry.id]));
  return profiles;
}

export function validateStickerProfiles(profiles) {
  const errors = [];
  if (profiles.size !== 568) errors.push(`expected 568 semantic profiles, got ${profiles.size}`);
  const lineMdCount = [...profiles.keys()].filter((key) => key.startsWith("line-md:")).length;
  if (lineMdCount !== 532) errors.push(`expected 532 Line MD semantic bases, got ${lineMdCount}`);
  for (const [id, metadata] of profiles) {
    if (!STICKER_CATEGORIES.includes(metadata.category)) errors.push(`${id}: invalid category ${metadata.category}`);
    for (const field of ["name", "description"]) if (!metadata[field]) errors.push(`${id}: missing ${field}`);
    for (const field of ["tags", "intent_keywords", "best_for", "avoid_when"]) {
      if (!Array.isArray(metadata[field]) || metadata[field].length === 0) errors.push(`${id}: missing ${field}`);
    }
  }
  return errors;
}
