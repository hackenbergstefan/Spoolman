export interface ISpoolUsage {
  id: number;
  spool_id: number;
  spool_name?: string;
  printer_id?: number;
  timestamp: string;
  used_weight: number;
  used_length?: number;
}
