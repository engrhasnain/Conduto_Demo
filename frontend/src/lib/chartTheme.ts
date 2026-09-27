// Reference palette (dataviz skill): categorical slots in fixed order, status colors
// reserved for state, blue<->red diverging with a gray midpoint. Light theme only.
export const C = {
  s1: "#2a78d6", // blue
  s2: "#eb6834", // orange
  s3: "#1baf7a", // aqua
  blue300: "#6da7ec",
  blue550: "#1c5cab",
  red: "#e34948",
  divNeutral: "#f0efec",
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
  ink: "#0b0b0b",
  ink2: "#52514e",
  muted: "#898781",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  surface: "#ffffff",
  bidGray: "#b9b7ae",
};

export const TERRAIN_COLOR: Record<string, string> = { coast: C.s1, highlands: C.s2, rainforest: C.s3 };

export const axisBase = {
  axisLine: { lineStyle: { color: C.axis } },
  axisTick: { show: false },
  axisLabel: { color: C.muted, fontSize: 11 },
  splitLine: { lineStyle: { color: C.grid, type: "solid" as const } },
};

export const tooltipBase = {
  backgroundColor: "#ffffff",
  borderColor: "rgba(11,11,11,0.10)",
  borderWidth: 1,
  padding: [8, 10],
  textStyle: { color: C.ink, fontSize: 12 },
  extraCssText: "box-shadow: 0 4px 16px rgba(0,0,0,0.08); border-radius: 8px;",
};

export const legendBase = {
  top: 0,
  left: 0,
  icon: "roundRect",
  itemWidth: 12,
  itemHeight: 4,
  textStyle: { color: C.ink2, fontSize: 12 },
};
