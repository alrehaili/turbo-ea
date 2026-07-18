/**
 * NORA EA Viewpoints Library — hub for all 67 NORA/DGA viewpoints.
 * Grouped by domain → level → type, each card shows progress badge + navigation link.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Paper,
  TextField,
  Typography,
  Alert,
} from '@mui/material';
import { MaterialSymbol } from '@/components/MaterialSymbol';
import { api } from '@/api/client';

interface Viewpoint {
  code: string;
  name_en: string;
  name_ar: string;
  domain: string;
  level: string;
  type: string;
  description_en?: string;
  description_ar?: string;
  target_route?: string;
  status: 'available' | 'partial' | 'missing' | 'done';
  sort_order: number;
}

const DOMAIN_LABELS: Record<string, { en: string; ar: string; icon: string; color: string }> = {
  strategic_alignment: {
    en: 'Strategic Alignment',
    ar: 'المحاذاة الاستراتيجية',
    icon: 'trending_up',
    color: '#c7527d',
  },
  business: {
    en: 'Business',
    ar: 'الأعمال',
    icon: 'business',
    color: '#2889ff',
  },
  beneficiary_experience: {
    en: 'Beneficiary Experience',
    ar: 'تجربة المستفيد',
    icon: 'face',
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
    ar: 'التكنولوجيا',
    icon: 'memory',
    color: '#d29270',
  },
  security: {
    en: 'Security',
    ar: 'الأمان',
    icon: 'security',
    color: '#a6566d',
  },
};

const STATUS_BADGE: Record<
  string,
  { label: string; icon: string; bgColor: string; textColor: string }
> = {
  done: {
    label: '✅ Done',
    icon: 'check_circle',
    bgColor: '#c8e6c9',
    textColor: '#1b5e20',
  },
  available: {
    label: '🟢 Available',
    icon: 'check',
    bgColor: '#c8f5e0',
    textColor: '#00695c',
  },
  partial: {
    label: '🟡 Partial',
    icon: 'schedule',
    bgColor: '#ffe0b2',
    textColor: '#e65100',
  },
  missing: {
    label: '❌ Missing',
    icon: 'build',
    bgColor: '#ffccbc',
    textColor: '#bf360c',
  },
};

export default function ViewLibraryPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [viewpoints, setViewpoints] = useState<Viewpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterDomain, setFilterDomain] = useState<string>('');
  const [filterLevel, setFilterLevel] = useState<string>('');

  // Fetch viewpoints on mount
  React.useEffect(() => {
    (async () => {
      try {
        const resp = await api.get('/viewpoints?page=1&page_size=100');
        setViewpoints(resp.data);
      } catch (err: any) {
        setError(err.detail || 'Failed to load viewpoints');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Group and filter viewpoints
  const grouped = useMemo(() => {
    let filtered = viewpoints;

    if (filterDomain) {
      filtered = filtered.filter((vp) => vp.domain === filterDomain);
    }
    if (filterLevel) {
      filtered = filtered.filter((vp) => vp.level === filterLevel);
    }

    const groups: Record<string, Record<string, Viewpoint[]>> = {};
    filtered.forEach((vp) => {
      if (!groups[vp.domain]) {
        groups[vp.domain] = {};
      }
      if (!groups[vp.domain][vp.level]) {
        groups[vp.domain][vp.level] = [];
      }
      groups[vp.domain][vp.level].push(vp);
    });

    return groups;
  }, [viewpoints, filterDomain, filterLevel]);

  const handleNavigate = (vp: Viewpoint) => {
    if (vp.status === 'missing') {
      alert(
        `"${vp[i18n.language === 'ar' ? 'name_ar' : 'name_en']}" is not yet implemented.`
      );
      return;
    }
    if (vp.target_route) {
      navigate(vp.target_route);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
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

  const isRtl = i18n.language === 'ar';

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        {t('nav:viewLibrary', 'View Library')}
      </Typography>
      <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary' }}>
        NORA/DGA EA Viewpoints — 67 viewpoints across 7 domains
      </Typography>

      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          select
          SelectProps={{ native: true }}
          label="Domain"
          value={filterDomain}
          onChange={(e) => setFilterDomain(e.target.value)}
          sx={{ minWidth: 200 }}
          size="small"
        >
          <option value="">All Domains</option>
          {Object.entries(DOMAIN_LABELS).map(([key, { en }]) => (
            <option key={key} value={key}>
              {en}
            </option>
          ))}
        </TextField>

        <TextField
          select
          SelectProps={{ native: true }}
          label="Level"
          value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value)}
          sx={{ minWidth: 200 }}
          size="small"
        >
          <option value="">All Levels</option>
          <option value="conceptual">Conceptual</option>
          <option value="logical">Logical</option>
          <option value="physical">Physical</option>
        </TextField>
      </Box>

      {/* Domain sections */}
      {Object.entries(grouped).map(([domain, levels]) => {
        const domainInfo = DOMAIN_LABELS[domain];
        const domainName = isRtl ? domainInfo.ar : domainInfo.en;

        return (
          <Box key={domain} sx={{ mb: 4 }}>
            {/* Domain header */}
            <Paper
              sx={{
                p: 2,
                mb: 2,
                backgroundColor: domainInfo.color,
                color: 'white',
                borderRadius: 1,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <MaterialSymbol icon={domainInfo.icon} />
                <Typography variant="h6">{domainName}</Typography>
                <Chip
                  label={`${Object.values(levels).reduce((sum, vps) => sum + vps.length, 0)}`}
                  size="small"
                  sx={{ ml: 'auto', backgroundColor: 'rgba(255,255,255,0.3)', color: 'white' }}
                />
              </Box>
            </Paper>

            {/* Level groups */}
            {Object.entries(levels).map(([level, vps]) => (
              <Box key={level} sx={{ mb: 3, ml: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1.5, textTransform: 'capitalize' }}>
                  {level}
                </Typography>

                {/* Viewpoint cards grid */}
                <Grid container spacing={2}>
                  {vps.map((vp) => {
                    const badge = STATUS_BADGE[vp.status];
                    const vpName = isRtl ? vp.name_ar : vp.name_en;
                    const vpDesc = isRtl ? vp.description_ar : vp.description_en;

                    return (
                      <Grid item xs={12} sm={6} md={4} key={vp.code}>
                        <Card
                          sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            cursor:
                              vp.status === 'missing' ? 'not-allowed' : 'pointer',
                            opacity: vp.status === 'missing' ? 0.6 : 1,
                            transition: 'all 0.2s',
                            '&:hover': {
                              boxShadow: vp.status === 'missing' ? 2 : 4,
                              transform: vp.status === 'missing' ? 'none' : 'translateY(-2px)',
                            },
                          }}
                          onClick={() => handleNavigate(vp)}
                        >
                          <CardActionArea sx={{ flex: 1 }}>
                            <CardContent>
                              {/* Status badge */}
                              <Box sx={{ mb: 1 }}>
                                <Chip
                                  size="small"
                                  label={badge.label}
                                  icon={<MaterialSymbol icon={badge.icon} />}
                                  sx={{
                                    backgroundColor: badge.bgColor,
                                    color: badge.textColor,
                                    fontWeight: 600,
                                  }}
                                />
                              </Box>

                              {/* Viewpoint name */}
                              <Typography
                                variant="subtitle1"
                                sx={{
                                  mb: 1,
                                  fontWeight: 600,
                                  textAlign: isRtl ? 'right' : 'left',
                                }}
                              >
                                {vpName}
                              </Typography>

                              {/* Viewpoint code */}
                              <Typography
                                variant="caption"
                                sx={{
                                  display: 'block',
                                  mb: 1,
                                  color: 'text.secondary',
                                  textAlign: isRtl ? 'right' : 'left',
                                }}
                              >
                                {vp.code}
                              </Typography>

                              {/* Type badge */}
                              <Box sx={{ mb: 1 }}>
                                <Chip
                                  size="small"
                                  label={vp.type}
                                  variant="outlined"
                                  sx={{ textTransform: 'capitalize' }}
                                />
                              </Box>

                              {/* Description */}
                              {vpDesc && (
                                <Typography
                                  variant="body2"
                                  sx={{
                                    mb: 1,
                                    color: 'text.secondary',
                                    textAlign: isRtl ? 'right' : 'left',
                                  }}
                                >
                                  {vpDesc}
                                </Typography>
                              )}

                              {/* Building blocks */}
                              {vp.building_blocks && vp.building_blocks.length > 0 && (
                                <Box sx={{ mt: 1.5 }}>
                                  <Typography
                                    variant="caption"
                                    sx={{ display: 'block', mb: 0.5 }}
                                  >
                                    Blocks:
                                  </Typography>
                                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                    {vp.building_blocks.map((block) => (
                                      <Chip
                                        key={block}
                                        label={block}
                                        size="small"
                                        variant="filled"
                                        sx={{
                                          fontSize: '0.7rem',
                                          height: '20px',
                                          backgroundColor: 'primary.light',
                                          color: 'primary.dark',
                                        }}
                                      />
                                    ))}
                                  </Box>
                                </Box>
                              )}
                            </CardContent>
                          </CardActionArea>

                          {/* Route info footer */}
                          {vp.target_route && vp.status !== 'missing' && (
                            <Box
                              sx={{
                                p: 1,
                                backgroundColor: 'background.default',
                                borderTop: '1px solid',
                                borderColor: 'divider',
                                fontSize: '0.75rem',
                                color: 'text.secondary',
                              }}
                            >
                              {vp.target_route}
                            </Box>
                          )}
                        </Card>
                      </Grid>
                    );
                  })}
                </Grid>
              </Box>
            ))}
          </Box>
        );
      })}

      {/* No results */}
      {Object.keys(grouped).length === 0 && (
        <Alert severity="info">No viewpoints match your filters.</Alert>
      )}
    </Box>
  );
}
