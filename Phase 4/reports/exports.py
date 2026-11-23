"""CSV downloads for every report (opens in Excel / Google Sheets)."""
import csv
import io

from flask import Response


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


def inventory_csv(data, report_time):
    return csv_response("inventory-report.csv",
                        ["Product", "Product ID", "Category", "Available quantity", "Low-stock limit", "Level", "Last restocked"],
                        [[p["name"], p["id"], p["category"], p["in_stock"], p["low_limit"], p["stock_level"],
                          report_time(p["last_received_at"])] for p in data["products"]])


def sales_csv(data, period, table="products"):
    name = f"sales-{period.start}-to-{period.end}"
    if table == "daily":
        return csv_response(name + "-daily.csv", ["Date", "Orders", "Total paid"],
                            [[d["date"], d["orders"], f"{d['total']:.2f}"] for d in data["daily"]])
    return csv_response(name + ".csv", ["Product", "Product ID", "Category", "Sold quantity", "Sales before discounts", "Period"],
                        [[p["name"], p["id"], p["category"], p["units"], f"{p['gross']:.2f}", f"{period.start} to {period.end}"]
                         for p in data["products"]])


def customers_csv(data, period):
    return csv_response(f"customer-activity-{period.start}-to-{period.end}.csv",
                        ["Date", "Customers who purchased", "Orders", "Guest orders"],
                        [[d["date"], d["buyers"], d["orders"], d["guest_orders"]] for d in data["daily"]])


def purchases_csv(data, report_time, period):
    return csv_response(f"my-purchases-{period.start}-to-{period.end}.csv",
                        ["Date and time", "Receipt", "Product", "Quantity", "Unit price", "Line total"],
                        [[report_time(i["created_at"]), i["receipt_number"], i["product_name"], i["quantity"],
                          f"{i['unit_price']:.2f}", f"{i['line_total']:.2f}"] for i in data["matches"]])
