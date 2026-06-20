import { EditOutlined, EyeOutlined } from "@ant-design/icons";
import { List, useTable } from "@refinedev/antd";
import { useTranslate, useUpdate } from "@refinedev/core";
import { Button, Modal, Select, Space, Table } from "antd";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { useState } from "react";
import { useNavigate } from "react-router";
import { ISpoolUsage } from "./model";
import { useSpoolSelectOptions } from "./spoolSelect";

dayjs.extend(utc);

export const SpoolUsageList = () => {
  const t = useTranslate();
  const navigate = useNavigate();
  const spoolOptions = useSpoolSelectOptions();

  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ISpoolUsage | null>(null);
  const [selectedSpoolId, setSelectedSpoolId] = useState<number | undefined>(undefined);

  const { mutate: updateUsage } = useUpdate();

  const { tableProps } = useTable<ISpoolUsage>({
    resource: "spool_usage",
    syncWithLocation: true,
    pagination: {
      mode: "server",
      pageSize: 25,
    },
    sorters: {
      initial: [{ field: "timestamp", order: "desc" }],
    },
  });

  const handleEditSpool = (record: ISpoolUsage) => {
    setEditingRecord(record);
    setSelectedSpoolId(record.spool_id);
    setEditModalOpen(true);
  };

  const handleEditModalOk = () => {
    if (!editingRecord || selectedSpoolId === undefined) return;
    updateUsage(
      {
        resource: "spool_usage",
        id: editingRecord.id,
        values: { spool_id: selectedSpoolId },
      },
      {
        onSuccess: () => {
          setEditModalOpen(false);
          setEditingRecord(null);
        },
      },
    );
  };

  return (
    <List title={t("spoolUsage.titles.list")}>
      <Table
        {...tableProps}
        rowKey="id"
        sticky
        tableLayout="fixed"
        scroll={{ x: "max-content" }}
      >
        <Table.Column
          dataIndex="id"
          title={t("spoolUsage.fields.id")}
          width={80}
        />
        <Table.Column
          dataIndex="spool_id"
          title={t("spoolUsage.fields.spool_id")}
          width={250}
          render={(_value: number, record: ISpoolUsage) => (
            <Space>
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/spool/show/${record.spool_id}`)}
              >
                #{record.spool_id} {record.spool_name ? `- ${record.spool_name}` : ""}
              </Button>
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEditSpool(record)}
              />
            </Space>
          )}
        />
        <Table.Column
          dataIndex="printer_id"
          title={t("spoolUsage.fields.printer_id")}
          width={100}
          render={(value: number | null) =>
            value ? (
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/printer/show/${value}`)}
              >
                #{value}
              </Button>
            ) : (
              "-"
            )
          }
        />
        <Table.Column
          dataIndex="timestamp"
          title={t("spoolUsage.fields.timestamp")}
          width={180}
          render={(value: string) => dayjs.utc(value).local().format("YYYY-MM-DD HH:mm:ss")}
          sorter
        />
        <Table.Column
          dataIndex="used_weight"
          title={t("spoolUsage.fields.used_weight")}
          width={120}
          render={(value: number) => `${value.toFixed(2)} g`}
          sorter
        />
        <Table.Column
          dataIndex="used_length"
          title={t("spoolUsage.fields.used_length")}
          width={120}
          render={(value: number | null) => (value != null ? `${(value / 1000).toFixed(2)} m` : "-")}
          sorter
        />
      </Table>
      <Modal
        title={t("spoolUsage.titles.change_spool")}
        open={editModalOpen}
        onOk={handleEditModalOk}
        onCancel={() => setEditModalOpen(false)}
      >
        <Select
          options={spoolOptions}
          value={selectedSpoolId}
          onChange={(val) => setSelectedSpoolId(val)}
          showSearch
          filterOption={(input, option) =>
            String(option?.label ?? "")
              .toLowerCase()
              .includes(input.toLowerCase())
          }
          style={{ width: "100%" }}
        />
      </Modal>
    </List>
  );
};

export default SpoolUsageList;
