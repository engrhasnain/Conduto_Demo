"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { BarChart, CustomChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart, LineChart, ScatterChart, HeatmapChart, CustomChart,
  GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, MarkAreaComponent, VisualMapComponent,
  CanvasRenderer,
]);

export type ChartOption = echarts.EChartsCoreOption;

interface Props {
  option: ChartOption;
  height?: number;
  onClick?: (params: { dataIndex: number; seriesIndex: number; name: string; data: unknown }) => void;
  ariaLabel?: string;
}

export default function Chart({ option, height = 300, onClick, ariaLabel }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const inst = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const chart = echarts.init(el, undefined, { renderer: "canvas" });
    inst.current = chart;
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.dispose();
      inst.current = null;
    };
  }, []);

  useEffect(() => {
    inst.current?.setOption({ textStyle: { fontFamily: "inherit" }, animationDuration: 400, ...option }, true);
  }, [option]);

  useEffect(() => {
    const chart = inst.current;
    if (!chart) return;
    chart.off("click");
    if (onClick) chart.on("click", (p) => onClick(p as unknown as Parameters<NonNullable<Props["onClick"]>>[0]));
  }, [onClick]);

  return <div ref={ref} role="img" aria-label={ariaLabel} style={{ height, width: "100%" }} />;
}
