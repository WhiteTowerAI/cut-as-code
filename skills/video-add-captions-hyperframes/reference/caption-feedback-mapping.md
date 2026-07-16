# Caption Feedback Mapping

This skill is agent-facing. Users describe caption style in natural language; the
agent maps that request to an official preset, theme flags, and optional JSON
overrides accepted by `scripts/generate_caption_project.mjs`.

## Safe Edit Points

- Use `scripts/caption-styles.json` as the source of official preset and theme names.
- Pass the final preset and themes with `--preset`, `--highlight-theme`,
  `--background-theme`, and `--stroke-theme`.
- Put only requested property overrides in a JSON file passed with `--overrides`.
- Edit caption cue JSON only when correcting subtitle text or timing data.

Write the final style only after the user confirms a preview, unless the user
explicitly asks to skip preview.

## Official Style Vocabulary

Official presets:

- `clean`
- `minimal`
- `social-bold`
- `pill`
- `boxed`
- `stroked`
- `shorts`

Background themes:

- `gray`
- `yellow`
- `blue`
- `pink`
- `green`

Stroke themes:

- `black`
- `yellow`
- `blue`
- `pink`
- `green`

Shorts highlight colors:

- `yellow` -> `#F8F54F`
- `green` -> `#21D32E`
- `orange` -> `#F8BD6D`
- `black` -> `#000000`
- `blue` -> `#2563EB`
- `pink` -> `#DB2777`

Karaoke is an option, not a preset. Preview ids such as `pill-yellow`,
`boxed-green`, `stroked-blue`, `shorts-yellow`, and `social-bold-karaoke` are
preset/config combinations, not official presets.

## Feedback Rules

Font and visual intensity:

- "make the text bigger" -> increase `font.sizeRatio`
- "make the text smaller" -> decrease `font.sizeRatio`
- "cleaner" -> move toward `clean` or `minimal`
- "more subtle" -> move toward `minimal`
- "more eye-catching" -> move toward `social-bold`
- "more like TikTok", "big short-video captions" -> move toward `social-bold`
- "vertical shorts style", "Reels style", "YouTube Shorts style" -> use `shorts`

Background:

- "no background" -> `background.enabled = false`
- "add a background" -> choose `pill` or `boxed`
- "rounded background", "capsule background" -> `preset = "pill"` or `background.shape = "pill"`
- "small rounded background", "rectangle background bar" -> `preset = "boxed"` or `background.shape = "rounded"`
- "make the background more transparent" -> decrease `background.opacity`
- "make the background stronger" -> increase `background.opacity`
- "gray background" -> `background.theme = "gray"`
- "yellow background" -> `background.theme = "yellow"`
- "blue background" -> `background.theme = "blue"`
- "pink background" -> `background.theme = "pink"`
- "green background" -> `background.theme = "green"`

Stroke:

- "no background, add text outline" -> `preset = "stroked"` and `background.enabled = false`
- "black outline" -> `stroke.theme = "black"`
- "yellow outline" -> `stroke.theme = "yellow"`
- "blue outline" -> `stroke.theme = "blue"`
- "pink outline" -> `stroke.theme = "pink"`
- "green outline" -> `stroke.theme = "green"`
- "make the outline thicker" -> increase `stroke.widthRatio`
- "make the outline thinner" -> decrease `stroke.widthRatio`
- "remove the outline" -> `stroke.enabled = false`

Karaoke / word highlight:

- "enable word-by-word highlight", "karaoke" -> `karaoke = true` or `wordHighlight.enabled = true`
- "disable word-by-word highlight" -> `karaoke = false` or `wordHighlight.enabled = false`
- "do not enlarge the active word" -> `wordHighlight.activeScale = 1`
- "yellow highlight" -> choose a yellow `wordHighlight.activeColor`
- "blue highlight" -> choose a blue `wordHighlight.activeColor`
- "pink highlight" -> choose a pink `wordHighlight.activeColor`
- "green highlight" -> choose a green `wordHighlight.activeColor`

Shorts highlight:

- "shorts with green highlight" -> `preset = "shorts"`, `wordHighlight.activeColor = "#21D32E"`
- "shorts with orange highlight" -> `preset = "shorts"`, `wordHighlight.activeColor = "#F8BD6D"`
- "shorts with yellow highlight" -> `preset = "shorts"`, `wordHighlight.activeColor = "#F8F54F"`
- "shorts with black highlight" -> `preset = "shorts"`, `wordHighlight.activeColor = "#000000"`
- "shorts with blue highlight" -> `preset = "shorts"`, `wordHighlight.activeColor = "#2563EB"`
- "shorts with pink highlight" -> `preset = "shorts"`, `wordHighlight.activeColor = "#DB2777"`
- "shorts, no karaoke" -> `preset = "shorts"`, `karaoke = false`

If a user only says "I do not like it", do not ask an open-ended question first.
Offer a small set of directions:

- cleaner
- more eye-catching
- bigger text
- stronger background
- change background color
- switch to outline text
- switch to shorts style
- enable or disable word-by-word highlight
- generate another preview set

## Examples

Clean no-background captions:

```ts
{
  preset: "clean",
  overrides: {
    background: { enabled: false }
  }
}
```

Yellow capsule background:

```ts
{
  preset: "pill",
  overrides: {
    background: {
      enabled: true,
      shape: "pill",
      theme: "yellow"
    }
  }
}
```

Blue small rounded background bar:

```ts
{
  preset: "boxed",
  overrides: {
    background: {
      enabled: true,
      shape: "rounded",
      theme: "blue"
    }
  }
}
```

White text with green outline and no background:

```ts
{
  preset: "stroked",
  overrides: {
    background: { enabled: false },
    stroke: {
      enabled: true,
      theme: "green"
    }
  }
}
```

Social bold with karaoke:

```ts
{
  preset: "social-bold",
  karaoke: true
}
```

Vertical shorts with green highlight:

```ts
{
  preset: "shorts",
  karaoke: true,
  overrides: {
    wordHighlight: {
      activeColor: "#21D32E",
      backgroundColor: "#21D32E"
    }
  }
}
```
