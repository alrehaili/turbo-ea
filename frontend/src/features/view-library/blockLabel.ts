import type { CardType } from "@/types";
import { typeLabel } from "@/hooks/useResolveLabel";

/**
 * Building blocks a viewpoint names by a type the NORA profile hides in
 * favour of another (NORAreadiness.md B-8): the chip shows the visible type.
 */
const HIDDEN_BLOCK_REPLACEMENT: Record<string, string> = {
  Organization: "OrganizationalUnit",
  BeneficiaryPersona: "Persona",
};

/** "DataTerm" → "Data Term", for a block that names no card type. */
export function humanizeBlockKey(key: string): string {
  return key.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
}

/**
 * Display name of a viewpoint's building block: the translated name of the
 * card type it names (or of the visible type that replaces a hidden one),
 * else the key split into words, never the raw key (NORAreadiness.md E4).
 */
export function blockLabel(block: string, types: CardType[], locale: string): string {
  const replacement = HIDDEN_BLOCK_REPLACEMENT[block];
  const type =
    (replacement && types.find((t) => t.key === replacement)) ||
    types.find((t) => t.key === block);
  return type ? typeLabel(type, locale) : humanizeBlockKey(block);
}
