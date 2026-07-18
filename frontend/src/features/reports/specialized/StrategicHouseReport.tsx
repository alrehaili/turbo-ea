/**
 * Strategic House Renderer
 * Visualizes strategic alignment: Vision → Mission → Pillars → Objectives → KPIs
 */

import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  TextField,
  Typography,
  Alert,
  Paper,
} from '@mui/material';
import { api } from '@/api/client';
import ReportShell from '../ReportShell';

interface ObjectiveCard {
  id: string;
  name: string;
  description?: string;
  parent_id?: string;
  attributes?: Record<string, any>;
}

const LEVEL_COLORS = {
  vision: '#c7527d',
  mission: '#c7527d',
  pillar: '#2889ff',
  objective: '#0f7eb5',
  kpi: '#028f00',
};

const LevelBox = ({ title, items, color }: { title: string; items: ObjectiveCard[]; color: string }) => (
  <Box sx={{ mb: 3 }}>
    <Paper sx={{ p: 2, backgroundColor: color, color: 'white', mb: 1, borderRadius: 1 }}>
      <Typography variant="h6" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
    </Paper>
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: 2,
      }}
    >
      {items.map((item) => (
        <Card
          key={item.id}
          sx={{
            backgroundColor: `${color}15`,
            borderLeft: `4px solid ${color}`,
            '&:hover': { boxShadow: 3 },
          }}
        >
          <CardContent sx={{ p: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
              {item.name}
            </Typography>
            {item.description && (
              <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary' }}>
                {item.description.substring(0, 60)}...
              </Typography>
            )}
          </CardContent>
        </Card>
      ))}
    </Box>
  </Box>
);

export default function StrategicHouseReport() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [objectives, setObjectives] = useState<ObjectiveCard[]>([]);
  const [selectedPillar, setSelectedPillar] = useState<string>('');

  useEffect(() => {
    (async () => {
      try {
        const resp = await api.get('/cards?type=Objective&page_size=500');
        setObjectives(resp.data);
        setLoading(false);
      } catch (err: any) {
        setError(err.detail || 'Failed to load objectives');
        setLoading(false);
      }
    })();
  }, []);

  const { vision, mission, pillars, children } = useMemo(() => {
    const vision = objectives.find((o) =>
      o.name.toLowerCase().includes('vision')
    );
    const mission = objectives.find((o) =>
      o.name.toLowerCase().includes('mission')
    );
    const pillars = objectives.filter(
      (o) => o.parent_id === vision?.id && o.id !== vision.id && o.id !== mission?.id
    );

    const childMap: Record<string, ObjectiveCard[]> = {};
    objectives.forEach((o) => {
      if (o.parent_id && o.parent_id !== vision?.id) {
        if (!childMap[o.parent_id]) childMap[o.parent_id] = [];
        childMap[o.parent_id].push(o);
      }
    });

    return { vision, mission, pillars, children: childMap };
  }, [objectives]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  const displayedPillars = selectedPillar
    ? pillars.filter((p) => p.id === selectedPillar)
    : pillars.slice(0, 4);

  return (
    <ReportShell
      title="Strategic House"
      description="Vision → Mission → Pillars → Objectives"
    >
      <Box sx={{ mb: 2 }}>
        <TextField
          select
          SelectProps={{ native: true }}
          label="Filter by Pillar"
          value={selectedPillar}
          onChange={(e) => setSelectedPillar(e.target.value)}
          size="small"
          sx={{ minWidth: 200 }}
        >
          <option value="">All Pillars ({pillars.length})</option>
          {pillars.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </TextField>
      </Box>

      {vision && (
        <LevelBox
          title="Vision"
          items={[vision]}
          color={LEVEL_COLORS.vision}
        />
      )}

      {mission && (
        <LevelBox
          title="Mission"
          items={[mission]}
          color={LEVEL_COLORS.mission}
        />
      )}

      <LevelBox
        title={`Pillars (${displayedPillars.length})`}
        items={displayedPillars}
        color={LEVEL_COLORS.pillar}
      />

      {displayedPillars.map((pillar) => (
        <LevelBox
          key={pillar.id}
          title={`Objectives under ${pillar.name}`}
          items={(children[pillar.id] || []).slice(0, 6)}
          color={LEVEL_COLORS.objective}
        />
      ))}
    </ReportShell>
  );
}
