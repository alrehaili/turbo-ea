import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import Tooltip from "@mui/material/Tooltip";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

interface CardBrief {
  id: string;
  name: string;
  type: string;
}
interface Review {
  id: string;
  title: string;
  subject: CardBrief | null;
  summary: string | null;
  status: string;
  decision_notes: string | null;
  decided_at: string | null;
}
interface ReviewDetail extends Review {
  context: {
    impact: { total_affected: number; critical_count: number; risk_count: number } | null;
    risks: { id: string; reference: string; title: string; level: string; status: string }[];
    adrs: { id: string; title: string; status: string }[];
    exceptions: { id: string; standard: string; status: string; expiry_date: string | null }[];
  };
}

const STATUS_COLOR: Record<string, "default" | "info" | "success" | "error" | "warning"> = {
  scheduled: "info",
  approved: "success",
  rejected: "error",
  deferred: "warning",
};

export default function ArchitectureReviewBoard() {
  const { t } = useTranslation(["reports", "common"]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [card, setCard] = useState<CardBrief | null>(null);
  const [options, setOptions] = useState<CardBrief[]>([]);
  const [editOpen, setEditOpen] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editSummary, setEditSummary] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setReviews(await api.get<Review[]>("/arb"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const open = async (id: string) => setDetail(await api.get<ReviewDetail>(`/arb/${id}`));

  const searchCards = async (q: string) => {
    const query = q.trim();
    const res = await api.get<{ items: CardBrief[] }>(
      `/cards?page_size=20${query ? `&search=${encodeURIComponent(query)}` : ""}`,
    );
    setOptions(res.items ?? []);
  };

  const create = async () => {
    if (!title.trim()) return;
    const r = await api.post<Review>("/arb", {
      title,
      subject_card_id: card?.id ?? null,
    });
    setDialogOpen(false);
    setTitle("");
    setCard(null);
    await load();
    await open(r.id);
  };

  const decide = async (status: string) => {
    if (!detail) return;
    await api.patch(`/arb/${detail.id}`, { status });
    await open(detail.id);
    await load();
  };

  const saveEdit = async () => {
    if (!detail || !editTitle.trim()) return;
    await api.patch(`/arb/${detail.id}`, { title: editTitle, summary: editSummary || null });
    setEditOpen(false);
    await open(detail.id);
    await load();
  };

  const remove = async () => {
    if (!detail) return;
    if (!window.confirm(t("arb.confirmDelete", { name: detail.title }))) return;
    await api.delete(`/arb/${detail.id}`);
    setDetail(null);
    await load();
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: "auto", p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
        <MaterialSymbol icon="gavel" size={26} color="#003399" />
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          {t("arb.title")}
        </Typography>
        <Button
          variant="contained"
          startIcon={<MaterialSymbol icon="add" size={18} />}
          onClick={() => setDialogOpen(true)}
        >
          {t("arb.newReview")}
        </Button>
      </Box>

      {reviews.length === 0 ? (
        <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
          <MaterialSymbol icon="gavel" size={48} />
          <Typography sx={{ mt: 2 }}>{t("arb.emptyState")}</Typography>
        </Box>
      ) : (
        reviews.map((r) => (
          <Paper
            key={r.id}
            variant="outlined"
            sx={{ p: 2, mb: 1.5, cursor: "pointer", display: "flex", alignItems: "center", gap: 2 }}
            onClick={() => open(r.id)}
          >
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {r.title}
              </Typography>
              {r.subject && (
                <Typography variant="caption" color="text.secondary">
                  {r.subject.name}
                </Typography>
              )}
            </Box>
            <Chip size="small" label={t(`arb.status.${r.status}`)} color={STATUS_COLOR[r.status]} />
            <MaterialSymbol icon="chevron_right" size={20} />
          </Paper>
        ))
      )}

      {/* Detail dialog with governance context */}
      <Dialog open={!!detail} onClose={() => setDetail(null)} fullWidth maxWidth="md">
        {detail && (
          <>
            <DialogTitle>
              {detail.title}
              {detail.subject && (
                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                  {detail.subject.name}
                </Typography>
              )}
            </DialogTitle>
            <DialogContent dividers>
              {/* Impact */}
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {t("arb.changeImpact")}
              </Typography>
              {detail.context.impact ? (
                <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
                  <Chip
                    size="small"
                    label={`${t("arb.affected")}: ${detail.context.impact.total_affected}`}
                  />
                  <Chip
                    size="small"
                    color="error"
                    label={`${t("arb.critical")}: ${detail.context.impact.critical_count}`}
                  />
                  <Chip
                    size="small"
                    label={`${t("arb.risks")}: ${detail.context.impact.risk_count}`}
                  />
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {t("arb.noSubject")}
                </Typography>
              )}

              <Divider sx={{ my: 1.5 }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {t("arb.risks")} ({detail.context.risks.length})
              </Typography>
              {detail.context.risks.map((rk) => (
                <Box key={rk.id} sx={{ display: "flex", gap: 1, alignItems: "center", py: 0.25 }}>
                  <Chip size="small" label={rk.level} />
                  <Typography variant="body2">
                    {rk.reference} — {rk.title}
                  </Typography>
                </Box>
              ))}

              <Divider sx={{ my: 1.5 }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {t("arb.adrs")} ({detail.context.adrs.length})
              </Typography>
              {detail.context.adrs.map((a) => (
                <Typography key={a.id} variant="body2" sx={{ py: 0.25 }}>
                  {a.title} <Chip size="small" label={a.status} sx={{ ml: 1 }} />
                </Typography>
              ))}

              <Divider sx={{ my: 1.5 }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {t("arb.exceptions")} ({detail.context.exceptions.length})
              </Typography>
              {detail.context.exceptions.map((e) => (
                <Typography key={e.id} variant="body2" sx={{ py: 0.25 }}>
                  {e.standard} <Chip size="small" label={e.status} sx={{ ml: 1 }} />
                </Typography>
              ))}
            </DialogContent>
            <DialogActions sx={{ justifyContent: "space-between", px: 3 }}>
              <Chip
                label={t(`arb.status.${detail.status}`)}
                color={STATUS_COLOR[detail.status]}
              />
              <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                <Button color="success" onClick={() => decide("approved")}>
                  {t("arb.approve")}
                </Button>
                <Button color="error" onClick={() => decide("rejected")}>
                  {t("arb.reject")}
                </Button>
                <Button onClick={() => decide("deferred")}>{t("arb.defer")}</Button>
                <Tooltip title={t("common:actions.edit")}>
                  <IconButton
                    onClick={() => {
                      setEditTitle(detail.title);
                      setEditSummary(detail.summary || "");
                      setEditOpen(true);
                    }}
                  >
                    <MaterialSymbol icon="edit" size={20} />
                  </IconButton>
                </Tooltip>
                <Tooltip title={t("common:actions.delete")}>
                  <IconButton color="error" onClick={remove}>
                    <MaterialSymbol icon="delete" size={20} />
                  </IconButton>
                </Tooltip>
                <IconButton onClick={() => setDetail(null)}>
                  <MaterialSymbol icon="close" size={20} />
                </IconButton>
              </Box>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Create dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t("arb.newReview")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("arb.reviewTitle")}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            fullWidth
          />
          <Autocomplete
            options={options}
            value={card}
            getOptionLabel={(o) => o.name}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            onChange={(_, v) => setCard(v)}
            onOpen={() => searchCards("")}
            onInputChange={(_, v) => searchCards(v)}
            filterOptions={(x) => x}
            renderInput={(p) => <TextField {...p} label={t("arb.subjectCard")} />}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={create}>
            {t("common:actions.create")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm" disableRestoreFocus>
        <DialogTitle>{t("arb.editReview")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("arb.reviewTitle")}
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            fullWidth
          />
          <TextField
            label={t("arb.summary")}
            value={editSummary}
            onChange={(e) => setEditSummary(e.target.value)}
            fullWidth
            multiline
            minRows={2}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={saveEdit}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
