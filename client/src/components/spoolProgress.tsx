import { Progress, Tooltip } from "antd";
import { ISpool } from "../pages/spools/model";

const SPOOLMAN_PRIMARY_COLOR = "#dc7734";

interface SpoolProgressProps {
  spool: ISpool;
  size?: "default" | "small";
  showInfo?: boolean;
  width?: number | string;
}

/**
 * Returns the total (initial) filament weight for a spool, falling back to the
 * filament's default weight when no per-spool initial weight is configured.
 */
function getInitialWeight(spool: ISpool): number | undefined {
  if (spool.initial_weight !== undefined && spool.initial_weight > 0) {
    return spool.initial_weight;
  }
  if (spool.filament?.weight !== undefined && spool.filament.weight > 0) {
    return spool.filament.weight;
  }
  return undefined;
}

/**
 * Compute the remaining filament percentage (0-100) for a spool, or undefined
 * if not enough information is available.
 */
export function getSpoolRemainingPercent(spool: ISpool): number | undefined {
  const initial = getInitialWeight(spool);
  if (initial === undefined) return undefined;
  if (spool.remaining_weight === undefined) return undefined;
  const pct = (spool.remaining_weight / initial) * 100;
  if (Number.isNaN(pct)) return undefined;
  return Math.max(0, Math.min(100, pct));
}

/**
 * Renders a progress bar showing the percentage of filament remaining on a spool.
 */
export function SpoolProgress({ spool, size = "small", showInfo = true, width = 120 }: SpoolProgressProps) {
  const percent = getSpoolRemainingPercent(spool);
  if (percent === undefined) {
    return <span>—</span>;
  }
  const rounded = Math.round(percent);
  const tooltip =
    spool.remaining_weight !== undefined
      ? `${spool.remaining_weight.toFixed(0)} g (${rounded}%)`
      : `${rounded}%`;
  return (
    <Tooltip title={tooltip}>
      <Progress
        percent={rounded}
        size={size}
        showInfo={showInfo}
        style={{ width, marginBottom: 0 }}
        strokeColor={SPOOLMAN_PRIMARY_COLOR}
        status="normal"
      />
    </Tooltip>
  );
}
