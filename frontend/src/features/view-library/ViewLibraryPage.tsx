/**
 * NORA EA Viewpoints Library — hub for all 67 NORA/DGA viewpoints.
 * Grouped by domain → level, each card shows a status badge, presentation
 * type, building blocks, and navigates to its target route.
 *
 * Bilingual (en/ar) via the viewpoint's own name_en/name_ar fields; UI
 * chrome strings follow the same inline en/ar pattern. Arabic renders in
 * the self-hosted Cairo font (see main.tsx).
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Card,
  CardActionArea,
  Chip,
  CircularProgress,
  InputAdornment,
  LinearProgress,
  MenuItem,
  Paper,
  TextField,
  Tooltip,
  Typography,
  alpha,
  useTheme,
} from '@mui/material';
import MaterialSymbol from '@/components/MaterialSymbol';
import { api } from '@/api/client';
import { STATUS_COLORS } from '@/theme';

interface Viewpoint {
  code: string;
  name_en: string;
  name_ar: string;
  domain: string;
  level: string;
  type: string;
  description_en?: string;
  description_ar?: string;
  building_blocks?: string[];
  target_route?: string;
  status: 'available' | 'partial' | 'missing' | 'done';
  sort_order: number;
}

const DOMAIN_LABELS: Record<string, { en: string; ar: string; icon: string; color: string }> = {
  strategic_alignment: {
    en: 'Strategic Alignment',
    ar: 'المواءمة الاستراتيجية',
    icon: 'flag',
    color: '#c7527d',
  },
  business: {
    en: 'Business',
    ar: 'الأعمال',
    icon: 'corporate_fare',
    color: '#2889ff',
  },
  beneficiary_experience: {
    en: 'Beneficiary Experience',
    ar: 'تجربة المستفيد',
    icon: 'sentiment_satisfied',
    color: '#fe6690',
  },
  data: {
    en: 'Data',
    ar: 'البيانات',
    icon: 'database',
    color: '#774fcc',
  },
  applications: {
    en: 'Applications',
    ar: 'التطبيقات',
    icon: 'apps',
    color: '#0f7eb5',
  },
  technology: {
    en: 'Technology',
    ar: 'التقنية',
    icon: 'memory',
    color: '#d29270',
  },
  security: {
    en: 'Security',
    ar: 'الأمن السيبراني',
    icon: 'security',
    color: '#a6566d',
  },
};

const STATUS_META: Record<
  Viewpoint['status'],
  { en: string; ar: string; icon: string; color: string }
> = {
  done: { en: 'Done', ar: 'مكتمل', icon: 'check_circle', color: STATUS_COLORS.success },
  available: { en: 'Available', ar: 'متاح', icon: 'check_circle', color: STATUS_COLORS.success },
  partial: { en: 'Partial', ar: 'جزئي', icon: 'schedule', color: STATUS_COLORS.warning },
  missing: { en: 'Missing', ar: 'غير متوفر', icon: 'construction', color: STATUS_COLORS.neutral },
};

const TYPE_META: Record<string, { en: string; ar: string; icon: string }> = {
  list: { en: 'List', ar: 'قائمة', icon: 'table_rows' },
  matrix: { en: 'Matrix', ar: 'مصفوفة', icon: 'grid_on' },
  diagram: { en: 'Diagram', ar: 'مخطط', icon: 'account_tree' },
};

const LEVEL_LABELS: Record<string, { en: string; ar: string }> = {
  conceptual: { en: 'Conceptual', ar: 'المستوى المفاهيمي' },
  logical: { en: 'Logical', ar: 'المستوى المنطقي' },
  physical: { en: 'Physical', ar: 'المستوى المادي' },
};

const DOMAIN_ORDER = Object.keys(DOMAIN_LABELS);
const LEVEL_ORDER = ['conceptual', 'logical', 'physical'];

export default function ViewLibraryPage() {
  const { i18n } = useTranslation();
  const theme = useTheme();
  const navigate = useNavigate();
  const [viewpoints, setViewpoints] = useState<Viewpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterDomain, setFilterDomain] = useState('');
  const [filterLevel, setFilterLevel] = useState('');
  const [filterType, setFilterType] = useState('');

  const isRtl = i18n.language === 'ar';
  const L = (obj: { en: string; ar: string }) => (isRtl ? obj.ar : obj.en);
  const isDark = theme.palette.mode === 'dark';

  useEffect(() => {
    (async () => {
      try {
        const resp = await api.get<{ data: Viewpoint[] }>('/viewpoints?page=1&page_size=100');
        setViewpoints(resp.data);
      } catch (err: any) {
        setError(err.detail || 'Failed to load viewpoints');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const readyCount = useMemo(
    () => viewpoints.filter((vp) => vp.status === 'available' || vp.status === 'done').length,
    [viewpoints]
  );

  const grouped = useMemo(() => {
    const q = search.trim().toLowerCase();
    let filtered = viewpoints;
    if (filterDomain) filtered = filtered.filter((vp) => vp.domain === filterDomain);
    if (filterLevel) filtered = filtered.filter((vp) => vp.level === filterLevel);
    if (filterType) filtered = filtered.filter((vp) => vp.type === filterType);
    if (q) {
      filtered = filtered.filter(
        (vp) =>
          vp.name_en.toLowerCase().includes(q) ||
          vp.name_ar.includes(search.trim()) ||
          vp.code.toLowerCase().includes(q) ||
          (vp.building_blocks || []).some((b) => b.toLowerCase().includes(q))
      );
    }

    const groups: Record<string, Record<string, Viewpoint[]>> = {};
    filtered.forEach((vp) => {
      if (!groups[vp.domain]) groups[vp.domain] = {};
      if (!groups[vp.domain][vp.level]) groups[vp.domain][vp.level] = [];
      groups[vp.domain][vp.level].push(vp);
    });
    Object.values(groups).forEach((levels) =>
      Object.values(levels).forEach((vps) => vps.sort((a, b) => a.sort_order - b.sort_order))
    );
    return groups;
  }, [viewpoints, search, filterDomain, filterLevel, filterType]);

  const handleNavigate = (vp: Viewpoint) => {
    if (vp.status !== 'missing' && vp.target_route) navigate(vp.target_route);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <Box dir={isRtl ? 'rtl' : 'ltr'} sx={{ p: { xs: 2, md: 3 }, maxWidth: 1400, mx: 'auto' }}>
      {/* ── Header ──────────────────────────────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, md: 3 },
          mb: 3,
          borderRadius: 2,
          border: `1px solid ${theme.palette.divider}`,
          background: isDark
            ? `linear-gradient(135deg, ${alpha('#2889ff', 0.12)}, ${alpha('#774fcc', 0.1)})`
            : `linear-gradient(135deg, ${alpha('#2889ff', 0.06)}, ${alpha('#774fcc', 0.05)})`,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
          <Box
            sx={{
              width: 44,
              height: 44,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: alpha('#2889ff', isDark ? 0.25 : 0.12),
              color: '#2889ff',
              flexShrink: 0,
            }}
          >
            <MaterialSymbol icon="grid_view" size={26} />
          </Box>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
              {isRtl ? 'مكتبة المناظير المعمارية' : 'View Library'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isRtl
                ? 'مناظير البنية المؤسسية وفق إطار "نورة" — ٦٧ منظورًا عبر ٧ نطاقات'
                : 'NORA/DGA EA viewpoints — 67 viewpoints across 7 domains'}
            </Typography>
          </Box>
        </Box>

        {/* Progress strip */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, flexWrap: 'wrap' }}>
          <Box sx={{ flex: 1, minWidth: 200 }}>
            <LinearProgress
              variant="determinate"
              value={viewpoints.length ? (readyCount / viewpoints.length) * 100 : 0}
              sx={{
                height: 8,
                borderRadius: 4,
                backgroundColor: alpha(STATUS_COLORS.success, 0.15),
                '& .MuiLinearProgress-bar': {
                  borderRadius: 4,
                  backgroundColor: STATUS_COLORS.success,
                },
              }}
            />
          </Box>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {readyCount}/{viewpoints.length} {isRtl ? 'جاهز' : 'ready'}
          </Typography>
        </Box>
      </Paper>

      {/* ── Filters ─────────────────────────────────────────────── */}
      <Box sx={{ display: 'flex', gap: 1.5, mb: 3, flexWrap: 'wrap' }}>
        <TextField
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={isRtl ? 'بحث بالاسم أو الرمز…' : 'Search name, code, or block…'}
          size="small"
          sx={{ minWidth: 240, flex: { xs: '1 1 100%', sm: '0 1 auto' } }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <MaterialSymbol icon="search" size={20} />
              </InputAdornment>
            ),
          }}
        />
        <TextField
          select
          label={isRtl ? 'النطاق' : 'Domain'}
          value={filterDomain}
          onChange={(e) => setFilterDomain(e.target.value)}
          size="small"
          sx={{ minWidth: 190 }}
        >
          <MenuItem value="">{isRtl ? 'كل النطاقات' : 'All domains'}</MenuItem>
          {DOMAIN_ORDER.map((key) => (
            <MenuItem key={key} value={key}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    backgroundColor: DOMAIN_LABELS[key].color,
                  }}
                />
                {L(DOMAIN_LABELS[key])}
              </Box>
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label={isRtl ? 'المستوى' : 'Level'}
          value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value)}
          size="small"
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">{isRtl ? 'كل المستويات' : 'All levels'}</MenuItem>
          {LEVEL_ORDER.map((key) => (
            <MenuItem key={key} value={key}>
              {L(LEVEL_LABELS[key])}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label={isRtl ? 'النوع' : 'Type'}
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          size="small"
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">{isRtl ? 'كل الأنواع' : 'All types'}</MenuItem>
          {Object.entries(TYPE_META).map(([key, meta]) => (
            <MenuItem key={key} value={key}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <MaterialSymbol icon={meta.icon} size={18} />
                {L(meta)}
              </Box>
            </MenuItem>
          ))}
        </TextField>
      </Box>

      {/* ── Domain sections ─────────────────────────────────────── */}
      {DOMAIN_ORDER.filter((d) => grouped[d]).map((domain) => {
        const domainInfo = DOMAIN_LABELS[domain];
        const levels = grouped[domain];
        const total = Object.values(levels).reduce((sum, vps) => sum + vps.length, 0);

        return (
          <Box key={domain} sx={{ mb: 4 }}>
            {/* Domain header */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                p: 1.5,
                mb: 2,
                borderRadius: 2,
                backgroundColor: alpha(domainInfo.color, isDark ? 0.16 : 0.07),
                borderInlineStart: `4px solid ${domainInfo.color}`,
              }}
            >
              <Box
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: 1.5,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: alpha(domainInfo.color, isDark ? 0.3 : 0.15),
                  color: domainInfo.color,
                  flexShrink: 0,
                }}
              >
                <MaterialSymbol icon={domainInfo.icon} size={22} />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 700, flex: 1 }}>
                {L(domainInfo)}
              </Typography>
              <Chip
                label={total}
                size="small"
                sx={{
                  fontWeight: 700,
                  backgroundColor: alpha(domainInfo.color, isDark ? 0.35 : 0.15),
                  color: isDark ? theme.palette.common.white : domainInfo.color,
                }}
              />
            </Box>

            {/* Level groups */}
            {LEVEL_ORDER.filter((lv) => levels[lv]).map((level) => (
              <Box key={level} sx={{ mb: 2.5 }}>
                <Typography
                  variant="overline"
                  sx={{
                    display: 'block',
                    mb: 1,
                    color: 'text.secondary',
                    fontWeight: 700,
                    letterSpacing: 1,
                  }}
                >
                  {L(LEVEL_LABELS[level] || { en: level, ar: level })}
                </Typography>

                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: {
                      xs: '1fr',
                      sm: 'repeat(2, 1fr)',
                      md: 'repeat(3, 1fr)',
                      lg: 'repeat(4, 1fr)',
                    },
                    gap: 1.5,
                  }}
                >
                  {levels[level].map((vp) => {
                    const status = STATUS_META[vp.status] || STATUS_META.available;
                    const typeMeta = TYPE_META[vp.type] || TYPE_META.list;
                    const vpName = isRtl ? vp.name_ar : vp.name_en;
                    const vpDesc = isRtl ? vp.description_ar : vp.description_en;
                    const clickable = vp.status !== 'missing' && !!vp.target_route;

                    return (
                      <Card
                        key={vp.code}
                        elevation={0}
                        sx={{
                          position: 'relative',
                          borderRadius: 2,
                          border: `1px solid ${theme.palette.divider}`,
                          overflow: 'hidden',
                          transition: 'box-shadow 0.2s, transform 0.2s, border-color 0.2s',
                          '&:hover': clickable
                            ? {
                                transform: 'translateY(-3px)',
                                boxShadow: `0 6px 20px ${alpha(domainInfo.color, 0.25)}`,
                                borderColor: alpha(domainInfo.color, 0.5),
                              }
                            : undefined,
                        }}
                      >
                        {/* Domain accent bar */}
                        <Box sx={{ height: 4, backgroundColor: domainInfo.color }} />
                        <CardActionArea
                          onClick={() => handleNavigate(vp)}
                          disabled={!clickable}
                          sx={{ height: '100%', alignItems: 'stretch' }}
                        >
                          <Box
                            sx={{
                              p: 1.75,
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 1,
                              height: '100%',
                            }}
                          >
                            {/* Top row: type + status */}
                            <Box
                              sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                gap: 1,
                              }}
                            >
                              <Chip
                                size="small"
                                icon={
                                  <MaterialSymbol
                                    icon={typeMeta.icon}
                                    size={14}
                                    style={{ color: domainInfo.color }}
                                  />
                                }
                                label={L(typeMeta)}
                                sx={{
                                  height: 22,
                                  fontSize: '0.7rem',
                                  fontWeight: 600,
                                  backgroundColor: alpha(domainInfo.color, isDark ? 0.22 : 0.09),
                                  color: isDark ? theme.palette.text.primary : domainInfo.color,
                                  '& .MuiChip-icon': { marginInlineStart: '6px' },
                                }}
                              />
                              <Tooltip title={L(status)}>
                                <Box
                                  sx={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    color: status.color,
                                  }}
                                >
                                  <MaterialSymbol icon={status.icon} size={18} />
                                </Box>
                              </Tooltip>
                            </Box>

                            {/* Name */}
                            <Typography
                              variant="subtitle2"
                              sx={{ fontWeight: 700, lineHeight: 1.35, minHeight: 38 }}
                            >
                              {vpName}
                            </Typography>

                            {/* Description */}
                            {vpDesc && (
                              <Typography
                                variant="caption"
                                sx={{
                                  color: 'text.secondary',
                                  display: '-webkit-box',
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: 'vertical',
                                  overflow: 'hidden',
                                  lineHeight: 1.5,
                                }}
                              >
                                {vpDesc}
                              </Typography>
                            )}

                            {/* Building blocks */}
                            {vp.building_blocks && vp.building_blocks.length > 0 && (
                              <Box
                                sx={{
                                  display: 'flex',
                                  gap: 0.5,
                                  flexWrap: 'wrap',
                                  mt: 'auto',
                                  pt: 0.5,
                                }}
                              >
                                {vp.building_blocks.slice(0, 3).map((block) => (
                                  <Chip
                                    key={block}
                                    label={block}
                                    size="small"
                                    variant="outlined"
                                    sx={{
                                      height: 20,
                                      fontSize: '0.65rem',
                                      color: 'text.secondary',
                                      borderColor: theme.palette.divider,
                                    }}
                                  />
                                ))}
                                {vp.building_blocks.length > 3 && (
                                  <Chip
                                    label={`+${vp.building_blocks.length - 3}`}
                                    size="small"
                                    sx={{
                                      height: 20,
                                      fontSize: '0.65rem',
                                      color: 'text.secondary',
                                      backgroundColor: alpha(theme.palette.text.primary, 0.06),
                                    }}
                                  />
                                )}
                              </Box>
                            )}

                            {/* Code footer */}
                            <Typography
                              variant="caption"
                              sx={{
                                fontFamily: 'monospace',
                                fontSize: '0.65rem',
                                color: alpha(theme.palette.text.secondary, 0.7),
                                direction: 'ltr',
                                textAlign: isRtl ? 'right' : 'left',
                              }}
                            >
                              {vp.code}
                            </Typography>
                          </Box>
                        </CardActionArea>
                      </Card>
                    );
                  })}
                </Box>
              </Box>
            ))}
          </Box>
        );
      })}

      {/* No results */}
      {Object.keys(grouped).length === 0 && (
        <Alert severity="info" icon={<MaterialSymbol icon="search_off" size={22} />}>
          {isRtl ? 'لا توجد مناظير مطابقة للبحث.' : 'No viewpoints match your filters.'}
        </Alert>
      )}
    </Box>
  );
}
