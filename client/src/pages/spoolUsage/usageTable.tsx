import { EditOutlined, EyeOutlined } from "@ant-design/icons";
import { useTranslate } from "@refinedev/core";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Modal, Select, Table, Typography } from "antd";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { useState } from "react";
import { useNavigate } from "react-router";
import { getAPIURL } from "../../utils/url";
import { ISpoolUsage } from "./model";
import { useSpoolSelectOptions } from "./spoolSelect";

dayjs.extend(utc);

const { Title } = Typography;

interface SpoolUsageTableProps {
  spoolId: number;
}

export const SpoolUsageTable: React.FC<SpoolUsageTableProps> = ({ spoolId }) => {
  const t = useTranslate();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const spoolOptions = useSpoolSelectOptions();

  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ISpoolUsage | null>(null);
  const [selectedSpoolId, setSelectedSpoolId] = useState<number | undefined>(undefined);

  const { data, isLoading } = useQuery<ISpoolUsage[]>({
    queryKey: ["spool_usage", spoolId],
    queryFn: async () => {
      const response = await fetch(`${getAPIURL()}/spool/${spoolId}/usage`);
      if (!response.ok) {
        throw new Error("Failed to fetch usage history");
      }
      return response.json();
    },
  });

  const handleEditSpool = (record: ISpoolUsage) => {
    setEditingRecord(record);
    setSelectedSpoolId(record.spool_id);
    setEditModalOpen(true);
  };

  const handleEditModalOk = async () => {
    if (!editingRecord || selectedSpoolId === undefined) return;
    const response = await fetch(`${getAPIURL()}/spool_usage/${editingRecord.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spool_id: selectedSpoolId }),
    });
    if (response.ok) {
      setEditModalOpen(false);
      setEditingRecord(null);
      queryClient.invalidateQueries({ queryKey: ["spool_usage", spoolId] });
    }
  };

  return (
    <>
      <Title level={4} style={{ marginTop: 24 }}>
        {t("spoolUsage.titles.list")}
      </Title>
      <Table
        dataSource={data ?? []}
        loading={isLoading}
        rowKey="id"
        size="small"
        pagination={{ pageSize: 10 }}
        scroll={{ x: "max-content" }}
      >
        <Table.Column
          dataIndex="id"
          title={t("spoolUsage.fields.id")}
          width={60}
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
          defaultSortOrder="descend"
          sorter={(a: ISpoolUsage, b: ISpoolUsage) =>
            dayjs(a.timestamp).unix() - dayjs(b.timestamp).unix()
          }
        />
        <Table.Column
          dataIndex="used_weight"
          title={t("spoolUsage.fields.used_weight")}
          width={120}
          render={(value: number) => `${value.toFixed(2)} g`}
          sorter={(a: ISpoolUsage, b: ISpoolUsage) => a.used_weight - b.used_weight}
        />
        <Table.Column
          dataIndex="used_length"
          title={t("spoolUsage.fields.used_length")}
          width={120}
          render={(value: number | null) => (value != null ? `${(value / 1000).toFixed(2)} m` : "-")}
          sorter={(a: ISpoolUsage, b: ISpoolUsage) =>
            (a.used_length ?? 0) - (b.used_length ?? 0)
          }
        />
        <Table.Column
          title=""
          width={50}
          render={(_: unknown, record: ISpoolUsage) => (
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditSpool(record)}
            />
          )}
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
    </>
  );
};
