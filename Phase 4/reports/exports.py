"""CSV and Excel downloads for reports."""
import csv
from decimal import Decimal
import io
import re

from flask import Response
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell


FORMATS = ("csv", "xlsx")
_INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def _safe(cell):
    """Stop spreadsheet formulas: a cell starting with = + - @ would be run by Excel."""
    if isinstance(cell, str) and cell[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + cell
    return cell


def csv_response(filename, header, table):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    for row in table:
        writer.writerow([_safe(c) for c in row])
    # utf-8 BOM so Excel shows accents (é, ç) correctly
    return Response("﻿" + out.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def _xlsx_cell(sheet, value):
    if isinstance(value, str):
        cell = WriteOnlyCell(sheet, value=_INVALID_XML.sub("", value))
        cell.data_type = "s"  # Keep user-entered text literal, including formula-like values.
        return cell
    if isinstance(value, Decimal):
        cell = WriteOnlyCell(sheet, value=value)
        cell.number_format = "0.00"
        return cell
    return value


def _xlsx_response(filename, sheets):
    workbook = Workbook(write_only=True)
    for title, header, rows in sheets:
        sheet = workbook.create_sheet(title)
        sheet.freeze_panes = "A2"
        sheet.append(header)
        for row in rows:
            sheet.append([_xlsx_cell(sheet, value) for value in row])
    output = io.BytesIO()
    workbook.save(output)
    return Response(output.getvalue(),
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'})


def _single_table(fmt, filename, title, header, rows):
    if fmt == "xlsx":
        return _xlsx_response(filename, [(title, header, rows)])
    return csv_response(filename + ".csv", header, rows)


def inventory_export(fmt, data, report_time):
    header = ["Product", "Product ID", "Category", "Available quantity", "Low-stock limit", "Level", "Last restocked"]
    rows = ([p["name"], p["id"], p["category"], p["in_stock"], p["low_limit"], p["stock_level"],
             report_time(p["last_received_at"])] for p in data["products"])
    return _single_table(fmt, "inventory-report", "Inventory", header, rows)


def sales_export(fmt, data, period, table):
    name = f"sales-{period.start}-to-{period.end}"
    products_header = ["Product", "Product ID", "Category", "Sold quantity", "Sales before discounts", "Period"]
    products = ([p["name"], p["id"], p["category"], p["units"], Decimal(f"{p['gross']:.2f}"),
                 f"{period.start} to {period.end}"] for p in data["products"])
    daily_header = ["Date", "Orders", "Total paid"]
    daily = ([d["date"], d["orders"], Decimal(f"{d['total']:.2f}")] for d in data["daily"])
    if fmt == "xlsx":
        return _xlsx_response(name, [("Products", products_header, products), ("Daily sales", daily_header, daily)])
    if table == "daily":
        return csv_response(name + "-daily.csv", daily_header, daily)
    return csv_response(name + ".csv", products_header, products)


def customers_export(fmt, data, period):
    header = ["Date", "Customers who purchased", "Orders", "Guest orders"]
    rows = ([d["date"], d["buyers"], d["orders"], d["guest_orders"]] for d in data["daily"])
    return _single_table(fmt, f"customer-activity-{period.start}-to-{period.end}",
                         "Customer activity", header, rows)


def purchases_export(fmt, data, report_time, period):
    header = ["Date and time", "Receipt", "Product", "Quantity", "Unit price", "Line total"]
    rows = ([report_time(i["created_at"]), i["receipt_number"], i["product_name"], i["quantity"],
             Decimal(f"{i['unit_price']:.2f}"), Decimal(f"{i['line_total']:.2f}")] for i in data["matches"])
    return _single_table(fmt, f"my-purchases-{period.start}-to-{period.end}", "My purchases", header, rows)
