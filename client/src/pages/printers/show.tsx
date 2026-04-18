import { DateField, NumberField, Show, TextField } from "@refinedev/antd";
import { useShow, useTranslate } from "@refinedev/core";
import { Typography } from "antd";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { ExtraFieldDisplay } from "../../components/extraFields";
import { enrichText } from "../../utils/parsing";
import { EntityType, useGetFields } from "../../utils/queryFields";
import { IPrinter } from "./model";

dayjs.extend(utc);

const { Title } = Typography;

export const PrinterShow = () => {
  const t = useTranslate();
  const extraFields = useGetFields(EntityType.printer);

  const { query } = useShow<IPrinter>({
    liveMode: "auto",
  });
  const { data, isLoading } = query;

  const record = data?.data;

  const formatTitle = (item: IPrinter) => {
    return t("printer.titles.show_title", { id: item.id, name: item.name, interpolation: { escapeValue: false } });
  };

  const formatSpool = (item: IPrinter) => {
    if (!item.spool) return "—";
    const filamentName = item.spool.filament?.name ?? "";
    const vendorName = item.spool.filament?.vendor?.name ?? "";
    const label = [vendorName, filamentName].filter(Boolean).join(" - ");
    return label ? `#${item.spool.id} - ${label}` : `#${item.spool.id}`;
  };

  return (
    <Show isLoading={isLoading} title={record ? formatTitle(record) : ""}>
      <Title level={5}>{t("printer.fields.id")}</Title>
      <NumberField value={record?.id ?? ""} />
      <Title level={5}>{t("printer.fields.registered")}</Title>
      <DateField
        value={dayjs.utc(record?.registered).local()}
        title={dayjs.utc(record?.registered).local().format()}
        format="YYYY-MM-DD HH:mm:ss"
      />
      <Title level={5}>{t("printer.fields.name")}</Title>
      <TextField value={record?.name} />
      <Title level={5}>{t("printer.fields.spool")}</Title>
      <TextField value={record ? formatSpool(record) : ""} />
      <Title level={5}>{t("printer.fields.comment")}</Title>
      <TextField value={enrichText(record?.comment)} />
      <Title level={5}>{t("printer.fields.external_id")}</Title>
      <TextField value={record?.external_id} />
      <Title level={4}>{t("settings.extra_fields.tab")}</Title>
      {extraFields?.data?.map((field, index) => (
        <ExtraFieldDisplay key={index} field={field} value={record?.extra[field.key]} />
      ))}
    </Show>
  );
};

export default PrinterShow;
