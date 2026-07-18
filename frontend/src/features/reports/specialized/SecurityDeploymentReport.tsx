/**
 * Security Deployment Report
 * Visualizes security controls, functions, and components across infrastructure
 */

import { useEffect, useState, useMemo } from 'react';
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
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  LinearProgress,
} from '@mui/material';
import { api } from '@/api/client';
import ReportShell from '../ReportShell';

interface SecurityFunction {
  id: string;
  name: string;
  subtype?: string;
  description?: string;
  attributes?: Record<string, any>;
}

interface SecurityMetrics {
  totalFunctions: number;
  byType: Record<string, number>;
  coverage: number;
}

export default function SecurityDeploymentReport() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [functions, setFunctions] = useState<SecurityFunction[]>([]);
  const [services, setServices] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const funcResp = await api.get('/cards?type=SecurityFunction&page_size=200');
        const servResp = await api.get('/cards?type=SecurityService&page_size=200');

        setFunctions(funcResp.data);
        setServices(servResp.data);
        setLoading(false);
      } catch (err: any) {
        setError(err.detail || 'Failed to load security data');
        setLoading(false);
      }
    })();
  }, []);

  const metrics = useMemo(() => {
    const byType: Record<string, number> = {};

    functions.forEach((f) => {
      const type = f.subtype || 'unknown';
      byType[type] = (byType[type] || 0) + 1;
    });

    // Estimate coverage based on control types
    const preventive = byType['preventive'] || 0;
    const detective = byType['detective'] || 0;
    const corrective = byType['corrective'] || 0;
    const total = preventive + detective + corrective;

    // Coverage is based on having all three types of controls
    const coverage = total > 0 ? Math.min(100, (preventive + detective + corrective) * 10) : 0;

    return {
      totalFunctions: functions.length,
      byType,
      coverage: Math.min(100, coverage),
    };
  }, [functions]);

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

  const CONTROL_COLORS: Record<string, string> = {
    preventive: '#4caf50',
    detective: '#2196f3',
    corrective: '#ff9800',
    unknown: '#9e9e9e',
  };

  const CONTROL_ICONS: Record<string, string> = {
    preventive: '🛡️',
    detective: '🔍',
    corrective: '🔧',
  };

  return (
    <ReportShell
      title="Security Deployment"
      description="Security controls and functions across infrastructure"
    >
      {/* Security posture overview */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Security Posture Overview
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {metrics.totalFunctions}
            </Typography>
            <Typography variant="caption">Security Functions</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h6" color="primary">
              {services.length}
            </Typography>
            <Typography variant="caption">Security Services</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="caption" sx={{ fontWeight: 500 }}>
                Coverage
              </Typography>
              <Typography variant="caption" sx={{ fontWeight: 600, color: 'primary.main' }}>
                {metrics.coverage}%
              </Typography>
            </Box>
            <LinearProgress variant="determinate" value={metrics.coverage} sx={{ height: 8, borderRadius: 1 }} />
          </Paper>
        </Grid>
      </Grid>

      {/* Control types breakdown */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Security Control Types
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {Object.entries(metrics.byType).map(([type, count]) => (
          <Grid item xs={12} sm={6} md={4} key={type}>
            <Card
              sx={{
                borderLeft: `4px solid ${CONTROL_COLORS[type]}`,
              }}
            >
              <CardContent sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 1 }}>
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {CONTROL_ICONS[type] || '◆'} {type.charAt(0).toUpperCase() + type.slice(1)}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      Controls
                    </Typography>
                  </Box>
                  <Chip
                    label={`${count}`}
                    sx={{
                      backgroundColor: CONTROL_COLORS[type],
                      color: 'white',
                      fontWeight: 600,
                    }}
                  />
                </Box>

                <Box sx={{ mt: 1.5 }}>
                  <Box
                    sx={{
                      height: 6,
                      backgroundColor: '#e0e0e0',
                      borderRadius: 1,
                      overflow: 'hidden',
                    }}
                  >
                    <Box
                      sx={{
                        height: '100%',
                        width: `${(count / Math.max(...Object.values(metrics.byType))) * 100}%`,
                        backgroundColor: CONTROL_COLORS[type],
                      }}
                    />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Three-tier defense */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Defense Strategy — Three Layers
      </Typography>

      <Paper sx={{ p: 3, mb: 3, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, backgroundColor: '#c8e6c9', borderRadius: 1 }}>
              <Typography sx={{ fontWeight: 600, mb: 1 }}>
                🛡️ Layer 1: Preventive
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mb: 1, color: 'text.secondary' }}>
                Stop threats before they occur
              </Typography>
              <Typography variant="h6" sx={{ color: '#2e7d32' }}>
                {metrics.byType['preventive'] || 0}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary' }}>
                Active controls
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, backgroundColor: '#bbdefb', borderRadius: 1 }}>
              <Typography sx={{ fontWeight: 600, mb: 1 }}>
                🔍 Layer 2: Detective
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mb: 1, color: 'text.secondary' }}>
                Identify threats in action
              </Typography>
              <Typography variant="h6" sx={{ color: '#1565c0' }}>
                {metrics.byType['detective'] || 0}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary' }}>
                Monitoring systems
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2, backgroundColor: '#ffe0b2', borderRadius: 1 }}>
              <Typography sx={{ fontWeight: 600, mb: 1 }}>
                🔧 Layer 3: Corrective
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mb: 1, color: 'text.secondary' }}>
                Respond to confirmed threats
              </Typography>
              <Typography variant="h6" sx={{ color: '#e65100' }}>
                {metrics.byType['corrective'] || 0}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary' }}>
                Incident response
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Paper>

      {/* Security functions table */}
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Security Functions Inventory
      </Typography>

      <TableContainer component={Paper} sx={{ maxHeight: 500 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell sx={{ fontWeight: 600 }}>Function Name</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Control Type</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {functions.map((func) => (
              <TableRow key={func.id} hover>
                <TableCell sx={{ fontWeight: 500 }}>{func.name}</TableCell>
                <TableCell>
                  <Chip
                    label={func.subtype || 'Unknown'}
                    size="small"
                    icon={<Typography>{CONTROL_ICONS[func.subtype || 'unknown']}</Typography>}
                    sx={{
                      backgroundColor: CONTROL_COLORS[func.subtype || 'unknown'],
                      color: 'white',
                    }}
                  />
                </TableCell>
                <TableCell sx={{ fontSize: '0.85rem', color: 'text.secondary' }}>
                  {func.description?.substring(0, 50)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Security services summary */}
      {services.length > 0 && (
        <>
          <Typography variant="h6" sx={{ mt: 4, mb: 2, fontWeight: 600 }}>
            Managed Security Services
          </Typography>

          <Grid container spacing={2}>
            {services.slice(0, 6).map((service) => (
              <Grid item xs={12} sm={6} md={4} key={service.id}>
                <Card sx={{ height: '100%' }}>
                  <CardContent sx={{ p: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {service.name}
                    </Typography>
                    <Chip
                      label={service.subtype || 'Service'}
                      size="small"
                      sx={{ mb: 1 }}
                      variant="outlined"
                    />
                    <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary' }}>
                      {service.description?.substring(0, 60)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}
    </ReportShell>
  );
}
