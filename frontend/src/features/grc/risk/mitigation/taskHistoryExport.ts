/**
 * Workbook builders for mitigation tasks and their occurrence history.
 *
 * Two entry points:
 *
 * * ``exportTaskHistory(task)`` — single-sheet workbook with one row per
 *   occurrence of one task. Triggered from the Risk Detail page's
 *   per-task "Export history" button.
 * * ``exportRegister(risks, allTasks)`` — two-sheet workbook for the
 *   register-level export. Sheet 1 carries the risk grid (same columns
 *   as the legacy CSV export). Sheet 2 carries one row per occurrence
 *   across all tasks, joined back to risks via ``risk_reference``.
 *
 * ``flattenTasksForExport`` is the shared row-builder used by both, so
 * the column shape stays in sync.
 */
import * as XLSX from "xlsx";
import type { MitigationTask, Risk } from "@/types";

export interface OccurrenceRow {
  risk_reference: string;
  task_reference: string;
  task_title: string;
  task_owner: string;
  recurrence: string;
  is_active: string;
  cycle: number;
  assigned_owner: string;
  due_date: string;
  status: string;
  completed_at: string;
  completed_by: string;
  owner_at_completion: string;
  completion_notes: string;
}

function recurrenceLabel(task: MitigationTask): string {
  if (task.recurrence_unit === "none") return "one-shot";
  return `every ${task.recurrence_interval} ${task.recurrence_unit}`;
}

/**
 * Flatten tasks to one row per occurrence. Tasks with no occurrences
 * (shouldn't happen — every task gets a first cycle on create) drop out
 * silently so the spreadsheet doesn't show empty rows.
 */
export function flattenTasksForExport(
  tasks: MitigationTask[],
  riskReferenceById: Map<string, string>,
): OccurrenceRow[] {
  const rows: OccurrenceRow[] = [];
  for (const task of tasks) {
    const riskRef = riskReferenceById.get(task.risk_id) ?? "";
    for (const occ of task.occurrences) {
      rows.push({
        risk_reference: riskRef,
        task_reference: task.reference,
        task_title: task.title,
        task_owner: task.owner_name ?? "",
        recurrence: recurrenceLabel(task),
        is_active: task.is_active ? "yes" : "no",
        cycle: occ.sequence,
        assigned_owner: occ.assigned_owner_name ?? "",
        due_date: occ.due_date ?? "",
        status: occ.status,
        completed_at: occ.completed_at ?? "",
        completed_by: occ.completed_by_name ?? "",
        owner_at_completion: occ.owner_at_completion_name ?? "",
        completion_notes: occ.completion_notes ?? "",
      });
    }
  }
  return rows;
}

function timestamp(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `_${pad(now.getHours())}${pad(now.getMinutes())}`
  );
}

function autoFitColumns(rows: Record<string, unknown>[]): XLSX.ColInfo[] {
  if (rows.length === 0) return [];
  const headers = Object.keys(rows[0]);
  return headers.map((h) => {
    const longest = rows.reduce((max, row) => {
      const v = String(row[h] ?? "");
      return Math.max(max, v.length);
    }, h.length);
    return { wch: Math.min(Math.max(longest + 2, 8), 60) };
  });
}

export function exportTaskHistory(task: MitigationTask, riskReference: string): void {
  const rows = flattenTasksForExport([task], new Map([[task.risk_id, riskReference]]));
  const ws = XLSX.utils.json_to_sheet(rows);
  ws["!cols"] = autoFitColumns(rows as unknown as Record<string, unknown>[]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "History");
  XLSX.writeFile(wb, `mitigation-task-${task.reference}-${timestamp()}.xlsx`);
}

interface RiskRow {
  reference: string;
  title: string;
  category: string;
  initial_level: string;
  residual_level: string;
  status: string;
  owner: string;
  target_resolution_date: string;
  cards: string;
  updated_at: string;
}

function risksToRows(risks: Risk[]): RiskRow[] {
  return risks.map((r) => ({
    reference: r.reference,
    title: r.title,
    category: r.category,
    initial_level: r.initial_level,
    residual_level: r.residual_level ?? "",
    status: r.status,
    owner: r.owner_name ?? "",
    target_resolution_date: r.target_resolution_date ?? "",
    cards: r.cards.map((c) => c.card_name).join("; "),
    updated_at: r.updated_at ?? "",
  }));
}

export function exportRegister(risks: Risk[], allTasks: MitigationTask[]): void {
  const riskRefById = new Map(risks.map((r) => [r.id, r.reference] as const));
  const riskRows = risksToRows(risks);
  const taskRows = flattenTasksForExport(allTasks, riskRefById);

  const risksSheet = XLSX.utils.json_to_sheet(riskRows);
  risksSheet["!cols"] = autoFitColumns(riskRows as unknown as Record<string, unknown>[]);
  const tasksSheet = XLSX.utils.json_to_sheet(taskRows);
  tasksSheet["!cols"] = autoFitColumns(taskRows as unknown as Record<string, unknown>[]);

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, risksSheet, "Risks");
  XLSX.utils.book_append_sheet(wb, tasksSheet, "Mitigation tasks");
  XLSX.writeFile(wb, `risk-register-${timestamp()}.xlsx`);
}
