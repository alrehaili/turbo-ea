import type { ComponentProps, ReactElement } from "react";
import { Trans } from "react-i18next";

/**
 * A translation whose string carries markup (`<strong>{{name}}</strong>`)
 * with user-typed values in it, rendered as React elements — no
 * `dangerouslySetInnerHTML`.
 *
 * A bare `<Trans values={…}>` is not enough: it interpolates the values into
 * the string *before* parsing the markup, so a card named `x <strong>y</strong>`
 * or `R&D <i>pilot</i>` renders real bold / italic, because `strong` and `i`
 * are tags Trans keeps. Escaping the values first (`escapeValue: true`) keeps
 * them out of the parse, and `shouldUnescape` turns the entities back into the
 * characters typed, so every name shows exactly as written.
 */
export default function EscapedTrans({
  t,
  i18nKey,
  values,
  components = { strong: <strong /> },
}: {
  /** The caller's `t`, so its namespaces resolve the key. */
  t: ComponentProps<typeof Trans>["t"];
  i18nKey: string;
  values: Record<string, unknown>;
  components?: Record<string, ReactElement>;
}) {
  return (
    <Trans
      t={t}
      i18nKey={i18nKey}
      values={values}
      components={components}
      tOptions={{ interpolation: { escapeValue: true } }}
      shouldUnescape
    />
  );
}
