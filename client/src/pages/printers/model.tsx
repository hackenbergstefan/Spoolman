import { ISpool } from "../spools/model";

export interface IPrinter {
  id: number;
  registered: string;
  name: string;
  spool?: ISpool;
  comment?: string;
  external_id?: string;
  prusaconnect_printer_uuid?: string;
  extra: { [key: string]: string };
}

// IPrinterParsedExtras is the same as IPrinter, but with the extra field parsed into its real types
export type IPrinterParsedExtras = Omit<IPrinter, "extra"> & { extra?: { [key: string]: unknown } };
