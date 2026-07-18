/**
 * Beneficiary Journey Map Renderer
 * Visualizes customer/beneficiary journey with stages, touchpoints, and pain points
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Paper,
  Chip,
  Typography,
  Grid,
} from '@mui/material';
import { MaterialSymbol } from '@/components/MaterialSymbol';
import { api } from '@/api/client';
import { ReportShell } from '../ReportShell';

interface JourneyStage {
  id: string;
  name: string;
  description?: string;
  order: number;
  touchpoints: string[];
  painPoints: string[];
}

interface Journey {
  id: string;
  name: string;
  description?: string;
  stages: JourneyStage[];
}

export const BeneficiaryJourneyMapReport = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [journeys, setJourneys] = useState<Journey[]>([]);
  const [selectedJourney, setSelectedJourney] = useState<Journey | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const resp = await api.get('/cards?type=BeneficiaryJourney&page_size=100');
        if (resp.data.length > 0) {
          // Create mock stages for demo (in production, these would come from nested journey structures)
          const journeysWithStages = resp.data.map((j) => ({
            ...j,
            stages: [
              { id: '1', name: 'Awareness', order: 1, touchpoints: ['Website', 'Social Media'], painPoints: ['Unclear navigation'] },
              { id: '2', name: 'Engagement', order: 2, touchpoints: ['Application', 'Support Chat'], painPoints: ['Long wait times'] },
              { id: '3', name: 'Decision', order: 3, touchpoints: ['Comparison Tool', 'Reviews'], painPoints: ['Too many options'] },
              { id: '4', name: 'Service', order: 4, touchpoints: ['Portal', 'Mobile App'], painPoints: ['Technical issues'] },
              { id: '5', name: 'Support', order: 5, touchpoints: ['Help Center', 'Contact Center'], painPoints: ['Limited hours'] },
            ],
          }));
          setJourneys(journeysWithStages);
          setSelectedJourney(journeysWithStages[0]);
        }
        setLoading(false);
      } catch (err: any) {
        setError(err.detail || 'Failed to load journeys');
        setLoading(false);
      }
    })();
  }, []);

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

  if (!selectedJourney) {
    return <Alert severity="info">No journeys found. Create a BeneficiaryJourney card first.</Alert>;
  }

  const stages = selectedJourney.stages.sort((a, b) => a.order - b.order);

  return (
    <ReportShell
      title="Beneficiary Journey Map"
      description="Stages, touchpoints, and pain points in the customer experience"
    >
      <Box sx={{ mb: 3, display: 'flex', gap: 2, overflowX: 'auto', pb: 1 }}>
        {journeys.map((j) => (
          <Chip
            key={j.id}
            label={j.name}
            onClick={() => setSelectedJourney(j)}
            color={selectedJourney.id === j.id ? 'primary' : 'default'}
            variant={selectedJourney.id === j.id ? 'filled' : 'outlined'}
          />
        ))}
      </Box>

      {/* Timeline visualization */}
      <Box sx={{ position: 'relative', mb: 4 }}>
        {/* Timeline connector line */}
        <Box
          sx={{
            position: 'absolute',
            top: '40px',
            left: '0',
            right: '0',
            height: '4px',
            backgroundColor: '#e0e0e0',
            zIndex: 0,
          }}
        />

        {/* Stages */}
        <Grid container spacing={2} sx={{ position: 'relative', zIndex: 1 }}>
          {stages.map((stage, idx) => (
            <Grid item xs={12} sm={6} md={4} lg={2.4} key={stage.id}>
              <Card
                sx={{
                  backgroundColor: `hsl(${(idx * 60) % 360}, 70%, 90%)`,
                  borderTop: `4px solid hsl(${(idx * 60) % 360}, 70%, 50%)`,
                  textAlign: 'center',
                  minHeight: 200,
                  position: 'relative',
                }}
              >
                {/* Stage number circle */}
                <Box
                  sx={{
                    position: 'absolute',
                    top: '-20px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    backgroundColor: `hsl(${(idx * 60) % 360}, 70%, 50%)`,
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 600,
                    boxShadow: 2,
                  }}
                >
                  {idx + 1}
                </Box>

                <CardContent sx={{ pt: 4 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                    {stage.name}
                  </Typography>

                  {/* Touchpoints */}
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="caption" sx={{ display: 'block', fontWeight: 500, mb: 0.5 }}>
                      💬 Touchpoints
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      {stage.touchpoints.map((tp, i) => (
                        <Chip key={i} label={tp} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </Box>

                  {/* Pain points */}
                  {stage.painPoints.length > 0 && (
                    <Box>
                      <Typography variant="caption" sx={{ display: 'block', fontWeight: 500, mb: 0.5, color: '#c7527d' }}>
                        ⚠️ Pain Points
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                        {stage.painPoints.map((pp, i) => (
                          <Chip
                            key={i}
                            label={pp}
                            size="small"
                            sx={{ backgroundColor: '#fce4ec', color: '#c7527d' }}
                          />
                        ))}
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Summary */}
      <Paper sx={{ p: 2, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          Journey Summary
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ p: 1, backgroundColor: 'white', borderRadius: 1, textAlign: 'center' }}>
              <Typography variant="h6" color="primary">
                {stages.length}
              </Typography>
              <Typography variant="caption">Stages</Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ p: 1, backgroundColor: 'white', borderRadius: 1, textAlign: 'center' }}>
              <Typography variant="h6" color="primary">
                {stages.reduce((sum, s) => sum + s.touchpoints.length, 0)}
              </Typography>
              <Typography variant="caption">Touchpoints</Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ p: 1, backgroundColor: 'white', borderRadius: 1, textAlign: 'center' }}>
              <Typography variant="h6" color="error">
                {stages.reduce((sum, s) => sum + s.painPoints.length, 0)}
              </Typography>
              <Typography variant="caption">Pain Points</Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </ReportShell>
  );
};
