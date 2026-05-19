import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import TagPicker from "@/components/TagPicker";
import type { TagGroup, TagRef } from "@/types";

interface Params {
  value: TagRef[] | undefined;
  groups: TagGroup[];
  typeKey?: string;
  stopEditing?: (cancel?: boolean) => void;
}

const TagsCellEditor = forwardRef<{ getValue: () => TagRef[] }, Params>(
  (props, ref) => {
    const { t } = useTranslation(["common", "inventory"]);

    const initialIds = useMemo(
      () => (props.value || []).map((t) => t.id),
      [props.value],
    );
    const [ids, setIds] = useState<string[]>(initialIds);

    // Mirror state into a ref so AG Grid's getValue() always reads the latest
    // selection, regardless of when it grabs the imperative handle.
    const idsRef = useRef(ids);
    useEffect(() => {
      idsRef.current = ids;
    }, [ids]);

    const refsById = useMemo(() => {
      const map = new Map<string, TagRef>();
      for (const g of props.groups) {
        for (const t of g.tags) {
          map.set(t.id, {
            id: t.id,
            name: t.name,
            color: t.color,
            group_name: g.name,
          });
        }
      }
      return map;
    }, [props.groups]);

    useImperativeHandle(ref, () => ({
      getValue: () =>
        idsRef.current
          .map((id) => refsById.get(id))
          .filter((tag): tag is TagRef => Boolean(tag)),
    }));

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        props.stopEditing?.(true);
      }
    };

    return (
      <Box
        sx={{ p: 1.5, minWidth: 340, bgcolor: "background.paper" }}
        onMouseDown={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <TagPicker
          groups={props.groups}
          value={ids}
          onChange={setIds}
          typeKey={props.typeKey}
          size="small"
          disablePortal
        />
        <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ mt: 1.5 }}>
          <Button
            size="small"
            onClick={() => props.stopEditing?.(true)}
            startIcon={<MaterialSymbol icon="close" size={16} />}
          >
            {t("common:actions.cancel")}
          </Button>
          <Button
            size="small"
            variant="contained"
            onClick={() => props.stopEditing?.()}
            startIcon={<MaterialSymbol icon="check" size={16} />}
          >
            {t("common:actions.save")}
          </Button>
        </Stack>
      </Box>
    );
  },
);

TagsCellEditor.displayName = "TagsCellEditor";

export default TagsCellEditor;
