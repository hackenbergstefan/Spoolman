import { useSelect } from "@refinedev/antd";
import { ISpool } from "../spools/model";

export function useSpoolSelectOptions() {
  const { query } = useSelect<ISpool>({
    resource: "spool",
    optionLabel: "id",
    optionValue: "id",
    pagination: { mode: "off" },
  });

  return (
    query.data?.data?.map((spool: ISpool) => {
      const vendorName = spool.filament?.vendor?.name;
      const filamentName = spool.filament?.name;
      const parts = [vendorName, filamentName].filter(Boolean).join(" - ");
      return {
        value: spool.id,
        label: `#${spool.id} - ${parts || "Unknown"}`,
      };
    }) ?? []
  );
}
