import { Edit, useForm, useSelect } from "@refinedev/antd";
import { HttpError, useTranslate } from "@refinedev/core";
import { Alert, DatePicker, Form, Input, message, Select, Typography } from "antd";
import TextArea from "antd/es/input/TextArea";
import dayjs from "dayjs";
import { useState } from "react";
import { ExtraFieldFormItem, ParsedExtras, StringifiedExtras } from "../../components/extraFields";
import { EntityType, useGetFields } from "../../utils/queryFields";
import { ISpool } from "../spools/model";
import { IPrinter, IPrinterParsedExtras } from "./model";

/*
The API returns the extra fields as JSON values, but we need to parse them into their real types
in order for Ant design's form to work properly. ParsedExtras does this for us.
We also need to stringify them again before sending them back to the API, which is done by overriding
the form's onFinish method.
*/

export const PrinterEdit = () => {
  const t = useTranslate();
  const [messageApi, contextHolder] = message.useMessage();
  const [hasChanged, setHasChanged] = useState(false);
  const extraFields = useGetFields(EntityType.printer);

  const { formProps, saveButtonProps } = useForm<IPrinter, HttpError, IPrinter, IPrinter>({
    liveMode: "manual",
    onLiveEvent() {
      // Warn the user if the printer has been updated since the form was opened
      messageApi.warning(t("printer.form.printer_updated"));
      setHasChanged(true);
    },
  });

  // Parse the extra fields from string values into real types
  if (formProps.initialValues) {
    formProps.initialValues = ParsedExtras(formProps.initialValues);
    // Map nested spool object to spool_id for the form
    if (formProps.initialValues.spool) {
      formProps.initialValues.spool_id = formProps.initialValues.spool.id;
    }
  }

  // Override the form's onFinish method to stringify the extra fields
  const originalOnFinish = formProps.onFinish;
  formProps.onFinish = (allValues: IPrinterParsedExtras) => {
    if (allValues !== undefined && allValues !== null) {
      const stringifiedAllValues = StringifiedExtras<IPrinterParsedExtras>(allValues);
      originalOnFinish?.({
        extra: {},
        ...stringifiedAllValues,
      });
    }
  };

  const { selectProps: spoolSelect, query: spoolQuery } = useSelect<ISpool>({
    resource: "spool",
    optionLabel: "id",
    optionValue: "id",
    pagination: { mode: "off" },
  });

  // Transform spool options to show meaningful labels
  const spoolOptions = spoolQuery.data?.data?.map((spool: ISpool) => {
    const filamentName = spool.filament?.name ?? "";
    const vendorName = spool.filament?.vendor?.name ?? "";
    const label = [vendorName, filamentName].filter(Boolean).join(" - ");
    return {
      value: spool.id,
      label: label ? `#${spool.id} - ${label}` : `#${spool.id}`,
    };
  }) ?? [];

  return (
    <Edit saveButtonProps={saveButtonProps}>
      {contextHolder}
      <Form {...formProps} layout="vertical">
        <Form.Item
          label={t("printer.fields.id")}
          name={["id"]}
          rules={[
            {
              required: true,
            },
          ]}
        >
          <Input readOnly disabled />
        </Form.Item>
        <Form.Item
          label={t("printer.fields.registered")}
          name={["registered"]}
          rules={[
            {
              required: true,
            },
          ]}
          getValueProps={(value) => ({
            value: value ? dayjs(value) : undefined,
          })}
        >
          <DatePicker disabled showTime format="YYYY-MM-DD HH:mm:ss" />
        </Form.Item>
        <Form.Item
          label={t("printer.fields.name")}
          name={["name"]}
          rules={[
            {
              required: true,
            },
          ]}
        >
          <Input maxLength={64} />
        </Form.Item>
        <Form.Item
          label={t("printer.fields.spool")}
          help={t("printer.fields_help.spool")}
          name={["spool_id"]}
          rules={[
            {
              required: false,
            },
          ]}
        >
          <Select
            {...spoolSelect}
            options={spoolOptions}
            allowClear
            showSearch
            filterOption={(input, option) =>
              String(option?.label ?? "")
                .toLowerCase()
                .includes(input.toLowerCase())
            }
          />
        </Form.Item>
        <Form.Item
          label={t("printer.fields.comment")}
          name={["comment"]}
          rules={[
            {
              required: false,
            },
          ]}
        >
          <TextArea maxLength={1024} />
        </Form.Item>
        <Form.Item
          label={t("printer.fields.external_id")}
          name={["external_id"]}
          rules={[
            {
              required: false,
            },
          ]}
        >
          <Input maxLength={64} />
        </Form.Item>
        <Form.Item
          label={t("printer.fields.prusaconnect_printer_uuid")}
          help={t("printer.fields_help.prusaconnect_printer_uuid")}
          name={["prusaconnect_printer_uuid"]}
          rules={[
            {
              required: false,
            },
          ]}
        >
          <Input maxLength={256} placeholder="pMwjAJYBRnOmqLdB" />
        </Form.Item>
        <Typography.Title level={5}>{t("settings.extra_fields.tab")}</Typography.Title>
        {extraFields.data?.map((field, index) => (
          <ExtraFieldFormItem key={index} field={field} />
        ))}
      </Form>
      {hasChanged && <Alert description={t("printer.form.printer_updated")} type="warning" showIcon />}
    </Edit>
  );
};

export default PrinterEdit;
