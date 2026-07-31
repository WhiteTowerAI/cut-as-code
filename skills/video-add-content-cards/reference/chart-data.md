# Content Card Chart Data

## Scope

Charts are layouts of the canonical `stat` card. The supported layouts are
`bar-chart`, `pie-chart`, and `line-chart`; they are not a separate card type.
Use a chart only when the retained transcript contains every value, label, unit,
and relationship required by the chart. Otherwise use `metric-spotlight` or a
normal stat card.

## Data Object

Store chart data on the card so the composition can be regenerated without its
cached HTML:

```json
{
  "status": "approved",
  "dimension_label": "Quarter",
  "metric_label": "Revenue",
  "unit": "USD millions",
  "period": "FY2025",
  "points": [
    {
      "label": "Q1",
      "value": 12,
      "evidence_refs": ["segment:12"]
    },
    {
      "label": "Q2",
      "value": 18,
      "evidence_refs": ["segment:13"]
    }
  ]
}
```

`dimension_label`, `metric_label`, `unit`, and `period` are required non-empty
strings. `points` order is presentation order and, for a line chart, X-axis
order. Every point label is non-empty and unique. Every value is a finite JSON
number; booleans, NaN, and Infinity are invalid.

Each point has at least one non-empty evidence reference, and every point
reference belongs to the parent card's `evidence_refs`. This structural check
does not replace reading the referenced transcript segment. The Agent must
confirm that the segment contains that exact value and meaning.

`copy.display` owns concise visible headings, supporting context, and
interpretation. Compress longer source explanations without changing their
meaning, and do not enumerate or restate values, labels, periods, or units
already visible in the chart. `data` owns the structured dimension, metric,
unit, period, point order, values, and point evidence. The renderer configuration
remains under `renderer` and `renderer_recipe`.

## Layout Rules

### Bar chart

- Use 2 to 6 points from one categorical dimension and one metric.
- Values are non-negative, with at least one value greater than zero.
- Every bar begins at the same zero baseline. Never truncate the axis to
  exaggerate a difference.

### Pie chart

- Use 2 to 6 mutually exclusive parts of one proven whole.
- Values are non-negative and sum to more than zero.
- Percentage units (`%`, `percent`, `percentage`, or `pct`) sum to 100 within a
  floating-point tolerance of `0.000001`.
- If the transcript does not establish a complete whole, use a bar chart or
  text instead.

### Line chart

- Use 3 to 8 ordered points from one metric and unit.
- Prefer explicit time order. The point array is the X-axis order.
- Do not interpolate missing values, use a second axis, or present unordered
  categories as a trend.

## Evidence Decisions

The Agent reads the retained transcript evidence and manually authors draft
chart data during editorial choices. Never infer values from an analyzer
summary. Never combine points from different source videos. External CSV,
webpage, or report values are out of scope unless that source already exists as
an audited project input.

If any category, denominator, time point, metric, or unit is missing, do not
invent it. Downgrade as follows:

1. Use `metric-spotlight` for one supported value with context.
2. Use a normal stat card for a short textual claim.
3. Omit the card when neither expression is supported.

## Valid And Invalid Examples

Valid bar data:

```json
{"status":"draft","dimension_label":"Quarter","metric_label":"Revenue","unit":"USD millions","period":"FY2025","points":[{"label":"Q1","value":12,"evidence_refs":["segment:12"]},{"label":"Q2","value":18,"evidence_refs":["segment:13"]}]}
```

Invalid examples include:

- a bar chart with one point, a negative value, or all-zero values;
- a pie chart with overlapping categories, an unknown whole, a zero total, or
  percentages totaling 90;
- a line chart with two points, duplicate labels, or no meaningful order;
- any point with an empty label, non-finite value, empty evidence, or evidence
  outside the parent card's scope.

## Review And Approval

The candidate review shows chart fields only for a chart layout. It may add or
remove points within that layout's count range and emits deterministic compact
JSON after the card's normal summary line. The apply script validates every
review entry before copying the plan. Selected chart data becomes `approved`;
switching to a non-chart layout removes unused draft chart data.

Chart data approval is separate from visual clearance. After the user approves
the card and placement, the Agent authors the composition and checks real
composited frames for face and caption collisions.
