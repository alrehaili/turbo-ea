import * as XLSX from "xlsx";

import { api } from "@/api/client";
import i18n from "@/i18n";
import { resolveMetaLabel } from "@/hooks/useResolveLabel";
import type { Card, CardType, Relation, RelationType } from "@/types";

/**
 * Excel export — LeanIX-style multi-sheet workbook.
 *
 * For a single-type selection, only that type's card sheet is produced
 * (plus an optional `Relations` sheet if any of its relation types carry
 * attributes). For mixed selections, every card type present produces its
 * own sheet, and the workbook can be edited and re-imported in one shot.
 *
 * Card sheets carry:
 *   - core columns (id, type, name, parent_path, …)
 *   - `attr_<key>` columns derived from `fields_schema`
 *   - `rel:<relation_type_key>` columns for relation types whose source is
 *     this card type and whose `attributes_schema` is empty (the simple
 *     case that fits in a comma-separated cell)
 *
 * The `Relations` sheet captures relation rows for relation types that
 * carry attributes (cost, description, etc.) — these need a column per
 * attribute and so can't live inline on the card sheet.
 *
 * Reference encoding for relation cells and the Relations sheet: the
 * target card's `name` when unique within `(target_type, name)` across
 * the live set, otherwise the full `parent_path/name` (with `/` and `\\`
 * escapes mirroring `parent_path`). This matches the backend's
 * `CardResolver.resolve()` matching rules.
 */
const FORMAT_VERSION = "2";
const LIFECYCLE_PHASES = ["plan", "phaseIn", "active", "phaseOut", "endOfLife"] as const;
const MAX_PATH_DEPTH = 8;
const META_SHEET_NAME = "_Meta";
const RELATIONS_SHEET_NAME = "Relations";

export function encodePathSegment(name: string): string {
  return name.replace(/\\/g, "\\\\").replace(/\//g, "\\/");
}

function buildParentPath(card: Card, byId: Map<string, Card>): string {
  const segments: string[] = [];
  const seen = new Set<string>();
  let current = card.parent_id ? byId.get(card.parent_id) : undefined;
  while (current && !seen.has(current.id) && segments.length < MAX_PATH_DEPTH) {
    seen.add(current.id);
    segments.unshift(encodePathSegment(current.name));
    current = current.parent_id ? byId.get(current.parent_id) : undefined;
  }
  return segments.join(" / ");
}

/** Build the human-readable reference (`name` or `parent_path/name`) for a
 * relation target. Returns `name` alone when no other card of the same type
 * shares that name, the full path otherwise. */
function buildCardRef(
  card: Card,
  byId: Map<string, Card>,
  nameAmbiguity: Set<string>,
): string {
  const key = `${card.type}|${card.name.trim().toLowerCase()}`;
  const ambiguous = nameAmbiguity.has(key);
  if (!ambiguous && !card.parent_id) return card.name;
  if (!ambiguous) return card.name;
  const parentPath = buildParentPath(card, byId);
  if (!parentPath) return encodePathSegment(card.name);
  return `${parentPath} / ${encodePathSegment(card.name)}`;
}

function exportTimestamp(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `_${pad(now.getHours())}${pad(now.getMinutes())}`
  );
}

function autoSizeColumns(rows: Record<string, unknown>[]): XLSX.ColInfo[] | undefined {
  if (rows.length === 0) return undefined;
  const headers = Object.keys(rows[0]);
  return headers.map((h) => {
    let maxLen = h.length;
    for (const r of rows) {
      const v = String(r[h] ?? "");
      if (v.length > maxLen) maxLen = v.length;
    }
    return { wch: Math.min(maxLen + 2, 60) };
  });
}

interface ExportOptions {
  canViewCosts?: boolean;
  /** Public-facing tenant URL written to `_Meta` for debugging cross-tenant imports. */
  tenantUrl?: string;
}

/**
 * Sheet-name → CardType. Spreadsheet sheet names are capped at 31 chars by
 * Excel and can't contain certain symbols; we use the type label, fall
 * back to the key if the label is too long or duplicates an existing name.
 */
function sheetNameForType(type: CardType, taken: Set<string>): string {
  const stripped = (
    resolveMetaLabel(type.key, type.translations, "label", i18n.language) || type.label || type.key
  ).replace(/[\\/?*[\]:]/g, "_");
  const candidates = [stripped.slice(0, 31), type.key.slice(0, 31)];
  for (const c of candidates) {
    if (c && !taken.has(c)) {
      taken.add(c);
      return c;
    }
  }
  // Last resort: append a numeric suffix.
  let i = 2;
  while (taken.has(`${type.key.slice(0, 28)} ${i}`)) i++;
  const name = `${type.key.slice(0, 28)} ${i}`;
  taken.add(name);
  return name;
}

/**
 * Fetch relations for the given source cards in one network call. Falls back
 * to an empty list on failure so a transient API hiccup never blocks export
 * entirely — the user still gets a card-only workbook.
 */
async function fetchRelationsForSources(sourceIds: string[]): Promise<Relation[]> {
  if (sourceIds.length === 0) return [];
  try {
    // The `card_id=` endpoint returns relations where the card is *either*
    // source or target. We filter to outgoing-only locally so the
    // exporter only emits each relation once (from the source side).
    const all: Relation[] = [];
    const seen = new Set<string>();
    for (const sid of sourceIds) {
      const rels = await api.get<Relation[]>(`/relations?card_id=${sid}`);
      for (const r of rels) {
        if (r.source_id === sid && !seen.has(r.id)) {
          seen.add(r.id);
          all.push(r);
        }
      }
    }
    return all;
  } catch {
    return [];
  }
}

/**
 * Build a row representation for a single card sheet. Pulls in core
 * columns, `attr_*`, `lifecycle_*`, and `rel:<key>` columns for each
 * applicable simple relation type.
 */
function buildCardRowForType(
  card: Card,
  type: CardType,
  byId: Map<string, Card>,
  outgoingByRelType: Map<string, Card[]>,
  inlineRelTypes: RelationType[],
  nameAmbiguity: Set<string>,
  attrFieldKeys: string[],
  attrIsCost: Map<string, boolean>,
  canViewCosts: boolean,
): Record<string, unknown> {
  const row: Record<string, unknown> = {
    id: card.id,
    type: card.type,
    name: card.name,
    description: card.description ?? "",
    subtype: card.subtype ?? "",
    parent_path: buildParentPath(card, byId),
    external_id: card.external_id ?? "",
    alias: card.alias ?? "",
    approval_status: card.approval_status ?? "",
    tags: (card.tags || [])
      .map((tg) => (tg.group_name ? `${tg.group_name}: ${tg.name}` : tg.name))
      .join(", "),
  };

  for (const phase of LIFECYCLE_PHASES) {
    row[`lifecycle_${phase}`] = (card.lifecycle || {})[phase] ?? "";
  }

  for (const fieldKey of attrFieldKeys) {
    if (attrIsCost.get(fieldKey) && !canViewCosts) continue;
    const val = (card.attributes || {})[fieldKey];
    row[`attr_${fieldKey}`] = Array.isArray(val) ? val.join(", ") : (val ?? "");
  }

  for (const rt of inlineRelTypes) {
    const targets = outgoingByRelType.get(rt.key) || [];
    row[`rel:${rt.key}`] = targets
      .map((t) => buildCardRef(t, byId, nameAmbiguity))
      .join(", ");
  }

  // Type is the same across the sheet; keep the column for clarity but
  // make sure each row has it.
  void type;
  return row;
}

/**
 * Public entry point used by the Inventory page export buttons.
 *
 * Multi-sheet workbook with one sheet per card type present in `cards`,
 * plus a `Relations` sheet for relation types that carry attributes, plus
 * an `_Meta` sheet with format version + tenant URL.
 */
export async function exportToExcel(
  cards: Card[],
  typeConfig: CardType | undefined,
  allTypes: CardType[],
  relationTypes: RelationType[],
  options: ExportOptions = {},
): Promise<void> {
  const { canViewCosts = true, tenantUrl } = options;

  // Index all cards (across types) by id so relation targets are resolvable
  // even when they belong to a different type than the row being written.
  const byId = new Map<string, Card>();
  for (const card of cards) byId.set(card.id, card);

  // Detect (type, name) ambiguity across the *exported* set so the relation
  // cells can default to bare names when unique. Same logic the importer
  // uses on the way back in: unique → bare; ambiguous → full path.
  const nameCounts = new Map<string, number>();
  for (const card of cards) {
    const key = `${card.type}|${card.name.trim().toLowerCase()}`;
    nameCounts.set(key, (nameCounts.get(key) ?? 0) + 1);
  }
  const nameAmbiguity = new Set<string>();
  for (const [key, count] of nameCounts) {
    if (count > 1) nameAmbiguity.add(key);
  }

  // Fetch every outgoing relation for the cards in the export, in one
  // network round per card. The cards endpoint doesn't bulk-fetch by id,
  // so this is the fastest we can go without a new endpoint.
  const allRelations = await fetchRelationsForSources(cards.map((c) => c.id));

  // Group relations by source_id then by relation_type_key for fast lookup
  // during row building.
  const outgoingBySource = new Map<string, Map<string, Card[]>>();
  for (const rel of allRelations) {
    const target = byId.get(rel.target_id);
    if (!target) continue;
    let perType = outgoingBySource.get(rel.source_id);
    if (!perType) {
      perType = new Map();
      outgoingBySource.set(rel.source_id, perType);
    }
    const list = perType.get(rel.type) || [];
    list.push(target);
    perType.set(rel.type, list);
  }

  const wb = XLSX.utils.book_new();
  const takenSheetNames = new Set<string>();

  // Determine which types to emit. When a single typeConfig is provided,
  // restrict to that type; otherwise group the cards by their own `type`
  // and produce one sheet per group.
  const typesInExport: CardType[] = typeConfig
    ? [typeConfig]
    : (() => {
        const present = new Set(cards.map((c) => c.type));
        return allTypes.filter((t) => present.has(t.key));
      })();

  // Cache cost-field detection per type for the canViewCosts filter.
  const costKeysByType = new Map<string, Set<string>>();
  for (const t of allTypes) {
    const set = new Set<string>();
    for (const sec of t.fields_schema) {
      for (const f of sec.fields) {
        if (f.type === "cost") set.add(f.key);
      }
    }
    costKeysByType.set(t.key, set);
  }

  // Inline vs Relations-sheet split for relation types.
  // Inline: cardinality permits multiple sources/targets *and* no attributes.
  // Relations sheet: attribute-bearing relation types.
  const inlineRelTypes = relationTypes.filter(
    (rt) =>
      !rt.is_hidden && (!rt.attributes_schema || rt.attributes_schema.length === 0),
  );
  const attributeRelTypes = relationTypes.filter(
    (rt) =>
      !rt.is_hidden && rt.attributes_schema && rt.attributes_schema.length > 0,
  );

  // Per-type card sheets.
  for (const type of typesInExport) {
    const cardsOfType = cards.filter((c) => c.type === type.key);
    const attrFields = type.fields_schema.flatMap((s) => s.fields);
    const attrFieldKeys = attrFields.map((f) => f.key);
    const attrIsCost = new Map<string, boolean>();
    const costSet = costKeysByType.get(type.key) ?? new Set();
    for (const k of attrFieldKeys) attrIsCost.set(k, costSet.has(k));

    // Relation types whose forward direction starts from this type. Hidden
    // types and attribute-bearing types are excluded.
    const inlineForType = inlineRelTypes.filter((rt) => rt.source_type_key === type.key);

    const rows: Record<string, unknown>[] = [];
    for (const card of cardsOfType) {
      const outgoing = outgoingBySource.get(card.id) ?? new Map();
      rows.push(
        buildCardRowForType(
          card,
          type,
          byId,
          outgoing,
          inlineForType,
          nameAmbiguity,
          attrFieldKeys.filter((k) => !attrIsCost.get(k) || canViewCosts),
          attrIsCost,
          canViewCosts,
        ),
      );
    }

    // Ensure the sheet has at least a header row, even when the slice is
    // empty, so the re-import flow can still detect the type from the
    // sheet name and a clear column header set.
    const headerSeed = rows.length > 0
      ? rows
      : [
          buildCardRowForType(
            {
              id: "",
              type: type.key,
              name: "",
              description: "",
              subtype: "",
              status: "",
              approval_status: "",
              data_quality: 0,
              tags: [],
              stakeholders: [],
            } as Card,
            type,
            byId,
            new Map(),
            inlineForType,
            nameAmbiguity,
            attrFieldKeys,
            attrIsCost,
            canViewCosts,
          ),
        ];
    const ws = XLSX.utils.json_to_sheet(headerSeed);
    if (rows.length === 0) {
      // Strip the placeholder row but keep the header.
      const range = XLSX.utils.decode_range(ws["!ref"] || "A1");
      range.e.r = 0;
      ws["!ref"] = XLSX.utils.encode_range(range);
    }
    ws["!cols"] = autoSizeColumns(headerSeed);
    XLSX.utils.book_append_sheet(wb, ws, sheetNameForType(type, takenSheetNames));
  }

  // Relations sheet (attribute-bearing only). The card-sheet inline columns
  // already cover simple relations.
  if (attributeRelTypes.length > 0) {
    const relRows: Record<string, unknown>[] = [];
    const attrColumnSet = new Set<string>();
    for (const rt of attributeRelTypes) {
      for (const f of rt.attributes_schema) {
        if (f.type === "cost" && !canViewCosts) continue;
        attrColumnSet.add(`attr_${f.key}`);
      }
    }
    for (const rel of allRelations) {
      const rt = attributeRelTypes.find((r) => r.key === rel.type);
      if (!rt) continue;
      const sourceCard = byId.get(rel.source_id);
      const targetCard = byId.get(rel.target_id);
      if (!sourceCard || !targetCard) continue;
      const row: Record<string, unknown> = {
        action: "upsert",
        relation_type: rel.type,
        source_type: sourceCard.type,
        source_ref: buildCardRef(sourceCard, byId, nameAmbiguity),
        target_type: targetCard.type,
        target_ref: buildCardRef(targetCard, byId, nameAmbiguity),
        description: rel.description ?? "",
      };
      const costSet = new Set(
        (rt.attributes_schema || [])
          .filter((f) => f.type === "cost")
          .map((f) => f.key),
      );
      for (const colKey of attrColumnSet) {
        const fieldKey = colKey.slice(5);
        if (costSet.has(fieldKey) && !canViewCosts) continue;
        const val = (rel.attributes || {})[fieldKey];
        row[colKey] = Array.isArray(val) ? val.join(", ") : (val ?? "");
      }
      relRows.push(row);
    }
    if (relRows.length > 0) {
      const ws = XLSX.utils.json_to_sheet(relRows);
      ws["!cols"] = autoSizeColumns(relRows);
      XLSX.utils.book_append_sheet(wb, ws, RELATIONS_SHEET_NAME);
    }
  }

  // _Meta sheet — a small key/value table that helps the importer detect
  // older formats and a banner in the dialog when the source tenant differs.
  const metaRows: Record<string, unknown>[] = [
    { key: "format_version", value: FORMAT_VERSION },
    { key: "exported_at", value: new Date().toISOString() },
    { key: "card_count", value: cards.length },
    { key: "relation_count", value: allRelations.length },
  ];
  if (tenantUrl) metaRows.push({ key: "tenant_url", value: tenantUrl });
  const metaWs = XLSX.utils.json_to_sheet(metaRows);
  metaWs["!cols"] = autoSizeColumns(metaRows);
  XLSX.utils.book_append_sheet(wb, metaWs, META_SHEET_NAME);

  const typeLabel = typeConfig
    ? resolveMetaLabel(typeConfig.key, typeConfig.translations, "label", i18n.language)
    : "landscape";
  XLSX.writeFile(wb, `${typeLabel}_export_${exportTimestamp()}.xlsx`);
}
