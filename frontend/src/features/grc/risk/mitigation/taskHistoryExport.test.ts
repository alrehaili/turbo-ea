import { describe, expect, it } from "vitest";
import type { MitigationTask } from "@/types";
import { flattenTasksForExport } from "./taskHistoryExport";

function task(overrides: Partial<MitigationTask> = {}): MitigationTask {
  return {
    id: "task-1",
    reference: "T-000001",
    risk_id: "risk-1",
    title: "Apply MFA",
    description: null,
    owner_id: "u1",
    owner_name: "Jane Smith",
    recurrence_unit: "none",
    recurrence_interval: 1,
    is_active: true,
    created_by: "u1",
    created_at: "2026-05-14T10:00:00Z",
    updated_at: "2026-05-14T10:00:00Z",
    occurrences: [],
    ...overrides,
  };
}

describe("flattenTasksForExport", () => {
  it("produces one row per occurrence", () => {
    const t = task({
      occurrences: [
        {
          id: "o1",
          task_id: "task-1",
          sequence: 1,
          assigned_owner_id: "u1",
          assigned_owner_name: "Jane Smith",
          due_date: "2026-01-15",
          status: "done",
          completed_at: "2026-01-14T09:00:00Z",
          completed_by: "u1",
          completed_by_name: "Jane Smith",
          owner_at_completion: "u1",
          owner_at_completion_name: "Jane Smith",
          completion_notes: "All good",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-14T09:00:00Z",
        },
        {
          id: "o2",
          task_id: "task-1",
          sequence: 2,
          assigned_owner_id: "u1",
          assigned_owner_name: "Jane Smith",
          due_date: "2026-04-15",
          status: "open",
          completed_at: null,
          completed_by: null,
          completed_by_name: null,
          owner_at_completion: null,
          owner_at_completion_name: null,
          completion_notes: null,
          created_at: "2026-01-14T09:00:00Z",
          updated_at: "2026-01-14T09:00:00Z",
        },
      ],
    });
    const rows = flattenTasksForExport([t], new Map([["risk-1", "R-000123"]]));
    expect(rows).toHaveLength(2);
    expect(rows[0].risk_reference).toBe("R-000123");
    expect(rows[0].task_reference).toBe("T-000001");
    expect(rows[0].cycle).toBe(1);
    expect(rows[0].status).toBe("done");
    expect(rows[0].owner_at_completion).toBe("Jane Smith");
    expect(rows[1].cycle).toBe(2);
    expect(rows[1].status).toBe("open");
    expect(rows[1].completed_at).toBe("");
  });

  it("emits zero rows for a task with no occurrences", () => {
    const rows = flattenTasksForExport(
      [task({ occurrences: [] })],
      new Map([["risk-1", "R-000123"]]),
    );
    expect(rows).toEqual([]);
  });

  it("labels recurrence correctly", () => {
    const oneShot = task({ occurrences: [openOccurrence()] });
    const recurring = task({
      recurrence_unit: "months",
      recurrence_interval: 6,
      occurrences: [openOccurrence()],
    });
    const r1 = flattenTasksForExport([oneShot], new Map([["risk-1", "R-1"]]));
    const r2 = flattenTasksForExport([recurring], new Map([["risk-1", "R-1"]]));
    expect(r1[0].recurrence).toBe("one-shot");
    expect(r2[0].recurrence).toBe("every 6 months");
  });

  it("blank risk reference when not in the map", () => {
    const t = task({ occurrences: [openOccurrence()] });
    const rows = flattenTasksForExport([t], new Map());
    expect(rows[0].risk_reference).toBe("");
  });
});

function openOccurrence() {
  return {
    id: "o",
    task_id: "task-1",
    sequence: 1,
    assigned_owner_id: null,
    assigned_owner_name: null,
    due_date: null,
    status: "open" as const,
    completed_at: null,
    completed_by: null,
    completed_by_name: null,
    owner_at_completion: null,
    owner_at_completion_name: null,
    completion_notes: null,
    created_at: null,
    updated_at: null,
  };
}
