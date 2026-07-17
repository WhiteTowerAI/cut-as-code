# Caption Style Themes

Themes are semantic options layered on top of official presets. Do not make each
color combination an official preset.

## Background Themes

Background color is configured with `background.theme`.

Supported values:

- `gray`
- `yellow`
- `blue`
- `pink`
- `green`

Agents should map natural language to `preset` plus `background.theme`:

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

Use `preset: "pill"` for a large rounded/capsule background and `preset: "boxed"`
for a small-radius rectangular background.

Examples:

- "yellow rounded background" -> `preset: "pill"`, `background.theme = "yellow"`
- "green background" -> keep the current preset shape, set `background.theme = "green"`
- "blue small rounded background bar" -> `preset: "boxed"`, `background.theme = "blue"`

Do not create official presets such as `pill-yellow` or `boxed-green`. Names like
`pill-yellow` are preview candidate ids only.

## Stroke Themes

Text stroke is configured with `stroke.theme`.

Supported values:

- `black`
- `yellow`
- `blue`
- `pink`
- `green`

Agents should map natural language to `preset: "stroked"` plus `stroke.theme`:

```ts
{
  preset: "stroked",
  overrides: {
    background: { enabled: false },
    stroke: {
      enabled: true,
      theme: "black"
    }
  }
}
```

Examples:

- "no background, black outline" -> `preset: "stroked"`, `stroke.theme = "black"`
- "yellow outline captions" -> `preset: "stroked"`, `stroke.theme = "yellow"`
- "white text with green stroke" -> `preset: "stroked"`, `background.enabled = false`, `stroke.theme = "green"`

Do not create official presets such as `stroked-yellow` or `stroked-blue`. Names
like `stroked-yellow` are preview candidate ids only.

## Shorts Highlight Colors

`shorts` uses its own highlight colors. These are options, not official presets.

Supported values:

- `yellow`: `#F8F54F`
- `green`: `#21D32E`
- `orange`: `#F8BD6D`
- `black`: `#000000`
- `blue`: `#2563EB`
- `pink`: `#DB2777`

Map them by overriding `wordHighlight.activeColor` and `wordHighlight.backgroundColor`:

```ts
{
  preset: "shorts",
  karaoke: true,
  overrides: {
    wordHighlight: {
      activeColor: "#F8F54F",
      backgroundColor: "#F8F54F"
    }
  }
}
```

Do not create official presets such as `shorts-yellow`. Names like
`shorts-yellow` are preview candidate ids only.
