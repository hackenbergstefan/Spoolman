import { EditOutlined, EyeOutlined, FilterOutlined, PlusSquareOutlined, SwapOutlined } from "@ant-design/icons";
import { List, useSelect, useTable } from "@refinedev/antd";
import { useInvalidate, useNavigation, useTranslate, useUpdate } from "@refinedev/core";
import { Button, Dropdown, Modal, Select, Table } from "antd";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
    ActionsColumn,
    CustomFieldColumn,
    DateColumn,
    RichColumn,
    SortedColumn,
} from "../../components/column";
import { useLiveify } from "../../components/liveify";
import { removeUndefined } from "../../utils/filtering";
import { EntityType, useGetFields } from "../../utils/queryFields";
import { TableState, useInitialTableState, useStoreInitialState } from "../../utils/saveload";
import { ISpool } from "../spools/model";
import { IPrinter } from "./model";

dayjs.extend(utc);

const namespace = "printerList-v1";

const allColumns: (keyof IPrinter & string)[] = ["id", "name", "spool", "registered", "comment"];

export const PrinterList = () => {
  const t = useTranslate();
  const invalidate = useInvalidate();
  const navigate = useNavigate();
  const extraFields = useGetFields(EntityType.printer);

  const allColumnsWithExtraFields = [...allColumns, ...(extraFields.data?.map((field) => "extra." + field.key) ?? [])];

  // Load initial state
  const initialState = useInitialTableState(namespace);

  // Fetch data from the API
  const { tableProps, sorters, setSorters, filters, setFilters, currentPage, pageSize, setCurrentPage } =
    useTable<IPrinter>({
      syncWithLocation: false,
      pagination: {
        mode: "server",
        currentPage: initialState.pagination.currentPage,
        pageSize: initialState.pagination.pageSize,
      },
      sorters: {
        mode: "server",
        initial: initialState.sorters,
      },
      filters: {
        mode: "server",
        initial: initialState.filters,
      },
      liveMode: "manual",
      onLiveEvent(event) {
        if (event.type === "created" || event.type === "deleted") {
          // updated is handled by the liveify
          invalidate({
            resource: "printer",
            invalidates: ["list"],
          });
        }
      },
    });

  // Create state for the columns to show
  const [showColumns, setShowColumns] = useState<string[]>(initialState.showColumns ?? allColumns);

  // Store state in local storage
  const tableState: TableState = {
    sorters,
    filters,
    pagination: { currentPage, pageSize },
    showColumns,
  };
  useStoreInitialState(namespace, tableState);

  // Collapse the dataSource to a mutable list
  const queryDataSource: IPrinter[] = useMemo(() => {
    return (tableProps.dataSource || []).map((record) => ({ ...record }));
  }, [tableProps.dataSource]);
  const dataSource = useLiveify(
    "printer",
    queryDataSource,
    useCallback((record: IPrinter) => record, []),
  );

  if (tableProps.pagination) {
    tableProps.pagination.showSizeChanger = true;
  }

  // Set-spool modal state
  const [spoolModalOpen, setSpoolModalOpen] = useState(false);
  const [spoolModalPrinter, setSpoolModalPrinter] = useState<IPrinter | null>(null);
  const [spoolModalValue, setSpoolModalValue] = useState<number | undefined>(undefined);
  const { mutate: updatePrinter } = useUpdate();
  const { query: spoolQuery } = useSelect<ISpool>({
    resource: "spool",
    optionLabel: "id",
    optionValue: "id",
    pagination: { mode: "off" },
  });
  const spoolOptions = spoolQuery.data?.data?.map((spool: ISpool) => {
    const filamentName = spool.filament?.name ?? "";
    const vendorName = spool.filament?.vendor?.name ?? "";
    const label = [vendorName, filamentName].filter(Boolean).join(" - ");
    return {
      value: spool.id,
      label: label ? `#${spool.id} - ${label}` : `#${spool.id}`,
    };
  }) ?? [];

  const openSpoolModal = (record: IPrinter) => {
    setSpoolModalPrinter(record);
    setSpoolModalValue(record.spool?.id);
    setSpoolModalOpen(true);
  };

  const handleSpoolModalOk = () => {
    if (!spoolModalPrinter) return;
    updatePrinter(
      {
        resource: "printer",
        id: spoolModalPrinter.id,
        values: { spool_id: spoolModalValue ?? null },
      },
      {
        onSuccess: () => {
          setSpoolModalOpen(false);
          invalidate({ resource: "printer", invalidates: ["list"] });
        },
      },
    );
  };

  const { editUrl, showUrl, cloneUrl } = useNavigation();
  const actions = (record: IPrinter) => [
    { name: t("buttons.show"), icon: <EyeOutlined />, link: showUrl("printer", record.id) },
    { name: t("buttons.edit"), icon: <EditOutlined />, link: editUrl("printer", record.id) },
    { name: t("buttons.clone"), icon: <PlusSquareOutlined />, link: cloneUrl("printer", record.id) },
    { name: t("printer.buttons.set_spool"), icon: <SwapOutlined />, onClick: () => openSpoolModal(record) },
  ];

  const commonProps = {
    t,
    navigate,
    actions,
    dataSource,
    tableState,
    sorter: true,
  };

  return (
    <List
      headerButtons={({ defaultButtons }) => (
        <>
          <Button
            type="primary"
            icon={<FilterOutlined />}
            onClick={() => {
              setFilters([], "replace");
              setSorters([{ field: "id", order: "asc" }]);
              setCurrentPage(1);
            }}
          >
            {t("buttons.clearFilters")}
          </Button>
          <Dropdown
            trigger={["click"]}
            menu={{
              items: allColumnsWithExtraFields.map((column_id) => {
                if (column_id.indexOf("extra.") === 0) {
                  const extraField = extraFields.data?.find((field) => "extra." + field.key === column_id);
                  return {
                    key: column_id,
                    label: extraField?.name ?? column_id,
                  };
                }

                return {
                  key: column_id,
                  label: t(`printer.fields.${column_id}`),
                };
              }),
              selectedKeys: showColumns,
              selectable: true,
              multiple: true,
              onDeselect: (keys) => {
                setShowColumns(keys.selectedKeys);
              },
              onSelect: (keys) => {
                setShowColumns(keys.selectedKeys);
              },
            }}
          >
            <Button type="primary" icon={<EditOutlined />}>
              {t("buttons.hideColumns")}
            </Button>
          </Dropdown>
          {defaultButtons}
        </>
      )}
    >
      <Table
        {...tableProps}
        sticky
        tableLayout="auto"
        scroll={{ x: "max-content" }}
        dataSource={dataSource}
        rowKey="id"
        columns={removeUndefined([
          SortedColumn({
            ...commonProps,
            id: "id",
            i18ncat: "printer",
            width: 70,
          }),
          SortedColumn({
            ...commonProps,
            id: "name",
            i18ncat: "printer",
          }),
          {
            title: t("printer.fields.spool"),
            dataIndex: "spool",
            key: "spool",
            render: (spool: IPrinter["spool"]) => {
              if (!spool) return "—";
              const filamentName = spool.filament?.name ?? "";
              const vendorName = spool.filament?.vendor?.name ?? "";
              const label = [vendorName, filamentName].filter(Boolean).join(" - ");
              return label || `Spool #${spool.id}`;
            },
            hidden: !showColumns.includes("spool"),
          },
          DateColumn({
            ...commonProps,
            id: "registered",
            i18ncat: "printer",
            width: 200,
          }),
          ...(extraFields.data?.map((field) => {
            return CustomFieldColumn({
              ...commonProps,
              field,
            });
          }) ?? []),
          RichColumn({
            ...commonProps,
            id: "comment",
            i18ncat: "printer",
          }),
          ActionsColumn<IPrinter>(t("table.actions"), actions),
        ])}
      />
      <Modal
        title={t("printer.buttons.set_spool")}
        open={spoolModalOpen}
        onOk={handleSpoolModalOk}
        onCancel={() => setSpoolModalOpen(false)}
      >
        <Select
          options={spoolOptions}
          value={spoolModalValue}
          onChange={(val) => setSpoolModalValue(val)}
          allowClear
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

export default PrinterList;
