import { Create, useForm, useSelect } from "@refinedev/antd";
import { HttpError, IResourceComponentsProps, useTranslate } from "@refinedev/core";
import { Button, Form, Input, Select, Typography } from "antd";
import TextArea from "antd/es/input/TextArea";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { useEffect } from "react";
import { ExtraFieldFormItem, ParsedExtras, StringifiedExtras } from "../../components/extraFields";
import { EntityType, useGetFields } from "../../utils/queryFields";
import { ISpool } from "../spools/model";
import { IPrinter, IPrinterParsedExtras } from "./model";

dayjs.extend(utc);

interface CreateOrCloneProps {
  mode: "create" | "clone";
}

export const PrinterCreate = (props: IResourceComponentsProps & CreateOrCloneProps) => {
  const t = useTranslate();
  const extraFields = useGetFields(EntityType.printer);

  const { form, formProps, formLoading, onFinish, redirect } = useForm<
    IPrinter,
    HttpError,
    IPrinterParsedExtras,
    IPrinterParsedExtras
  >();

  if (!formProps.initialValues) {
    formProps.initialValues = {};
  }

  if (props.mode === "clone") {
    // Parse the extra fields from string values into real types
    formProps.initialValues = ParsedExtras(formProps.initialValues);
    // Clear spool assignment on clone since it must be unique
    formProps.initialValues.spool_id = undefined;
  }

  const handleSubmit = async (redirectTo: "list" | "edit" | "create") => {
    const values = StringifiedExtras(await form.validateFields());
    await onFinish(values);
    redirect(redirectTo, (values as unknown as IPrinter).id);
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

  // Use useEffect to update the form's initialValues when the extra fields are loaded
  useEffect(() => {
    extraFields.data?.forEach((field) => {
      if (formProps.initialValues && field.default_value) {
        const parsedValue = JSON.parse(field.default_value as string);
        form.setFieldsValue({ extra: { [field.key]: parsedValue } });
      }
    });
  }, [form, extraFields.data, formProps.initialValues]);

  return (
    <Create
      title={props.mode === "create" ? t("printer.titles.create") : t("printer.titles.clone")}
      isLoading={formLoading}
      footerButtons={() => (
        <>
          <Button type="primary" onClick={() => handleSubmit("list")}>
            {t("buttons.save")}
          </Button>
          <Button type="primary" onClick={() => handleSubmit("create")}>
            {t("buttons.saveAndAdd")}
          </Button>
        </>
      )}
    >
      <Form {...formProps} layout="vertical">
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
    </Create>
  );
};

export default PrinterCreate;
